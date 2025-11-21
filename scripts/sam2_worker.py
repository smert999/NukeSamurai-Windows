"""
SAM2 Worker - выполняется в системном Python с рабочим torch
"""
import sys
import os
import json

# Получаем параметры
if len(sys.argv) < 2:
    print("ERROR: No parameters provided")
    sys.exit(1)

params = json.loads(sys.argv[1])

# Добавляем sam2_repo в path (должен быть в PYTHONPATH от parent process)
sam2_repo = params["sam2_repo"]
sam2_repo = os.path.abspath(sam2_repo)

# Ensure sam2_repo is in sys.path for imports
if sam2_repo not in sys.path:
    sys.path.insert(0, sam2_repo)

# Set Hydra full error for better debugging
os.environ['HYDRA_FULL_ERROR'] = '1'

print(f"[SAM2 Worker] sys.path includes: {sam2_repo}")
print(f"[SAM2 Worker] Attempting to import sam2 module...")

# Теперь импортируем torch и SAM2
try:
    import torch
    import cv2
    import numpy as np
    import tempfile
    import shutil
    from pathlib import Path
    from sam2.build_sam import build_sam2_video_predictor
    print(f"[SAM2 Worker] Successfully imported sam2 module")
except ImportError as e:
    print(f"[SAM2 Worker] ERROR: Failed to import sam2 module: {e}", file=sys.stderr)
    print(f"[SAM2 Worker] sam2_repo path: {sam2_repo}", file=sys.stderr)
    print(f"[SAM2 Worker] Check that sam2_repo contains 'sam2' folder", file=sys.stderr)
    sys.exit(1)

# NO nuke imports - worker runs in system Python!

print(f"[SAM2 Worker] torch {torch.__version__}, CUDA: {torch.cuda.is_available()}")

# Извлекаем параметры
video_path = params["video_path"]
output_path = params["output_path"]
bbox_coord = params["bbox_coord"]
frame_range = params["frame_range"]
reference_frame = params.get("reference_frame", frame_range[0])  # NEW: Selected frame for bbox
model_path = os.path.join(params["sam2_repo"], params["model_path"])  # checkpoints inside sam2_repo!
fps_original = params["fps_original"]
fps_target = params["fps_target"]
bits = params["bits"]

print(f"[SAM2 Worker] Frame Range: {frame_range[0]}-{frame_range[1]}")
print(f"[SAM2 Worker] Reference Frame: {reference_frame}")

# Validate reference frame
if reference_frame < frame_range[0] or reference_frame > frame_range[1]:
    print(f"[SAM2 Worker] ERROR: Reference frame {reference_frame} outside range {frame_range}", file=sys.stderr)
    sys.exit(1)

# Check if output is EXR - OpenCV needs special compilation for EXR support
is_exr_output = output_path.lower().endswith('.exr') or '.exr' in output_path.lower()
if is_exr_output:
    print("[SAM2 Worker] WARNING: EXR output requested")
    print("[SAM2 Worker] OpenCV pip version doesn't support EXR by default")
    print("[SAM2 Worker] Trying to save as EXR (requires OPENCV_IO_ENABLE_OPENEXR=1)")

# Создаем mapping для переупорядочивания кадров
def create_frame_mapping(frame_min, frame_max, reference_frame):
    """
    Creates a mapping: reading_index → actual_frame_number
    
    Reorders frames so reference_frame becomes index 0 for SAM2.
    
    Example:
        frame_range: 1001-1200
        reference: 1112
        
        Reading order: [1112, 1113, ..., 1200, 1001, 1002, ..., 1111]
        Indices:       [0,    1,    ..., 88,   89,   90,   ..., 199]
    
    Returns:
        index_to_frame: dict {0: 1112, 1: 1113, ..., 199: 1111}
        frame_to_index: dict {1112: 0, 1113: 1, ..., 1111: 199}
    """
    index_to_frame = {}
    frame_to_index = {}
    
    idx = 0
    
    # First: reference_frame to frame_max (forward)
    for frame in range(reference_frame, frame_max + 1):
        index_to_frame[idx] = frame
        frame_to_index[frame] = idx
        idx += 1
    
    # Then: frame_min to (reference_frame - 1) (wrap around)
    if reference_frame > frame_min:
        for frame in range(frame_min, reference_frame):
            index_to_frame[idx] = frame
            frame_to_index[frame] = idx
            idx += 1
    
    return index_to_frame, frame_to_index

# Create frame mapping for reordering
index_to_frame, frame_to_index = create_frame_mapping(
    frame_range[0], 
    frame_range[1], 
    reference_frame
)

print(f"[SAM2 Worker] Frame mapping created:")
print(f"[SAM2 Worker]   Total frames: {len(index_to_frame)}")
print(f"[SAM2 Worker]   Reading index 0 = Frame {index_to_frame[0]} (reference)")
print(f"[SAM2 Worker]   Reading index 1 = Frame {index_to_frame[1]}")
print(f"[SAM2 Worker]   Reading index 50 = Frame {index_to_frame.get(50, 'N/A')}")
print(f"[SAM2 Worker]   Reading index 100 = Frame {index_to_frame.get(100, 'N/A')}")
print(f"[SAM2 Worker]   Reading index {len(index_to_frame)-1} = Frame {index_to_frame[len(index_to_frame)-1]}")

# Validate mapping
for idx, frame_num in index_to_frame.items():
    if frame_num < frame_range[0] or frame_num > frame_range[1]:
        print(f"[SAM2 Worker] ERROR: Invalid mapping! Index {idx} -> Frame {frame_num} (outside range {frame_range[0]}-{frame_range[1]})")
        sys.exit(1)

# Function to create reordered frame sequence
def create_reordered_sequence(video_path, index_to_frame, frame_range):
    """
    Creates temporary folder with frames in reordered sequence.
    
    SAM2 requires bbox to be on frame_idx=0, so we reorder frames
    so that reference_frame becomes the first frame physically.
    
    Returns:
        temp_dir: Path to temporary directory
        reordered_video_path: Path pattern for reordered sequence
    """
    # Parse input video path pattern
    input_file_name = os.path.basename(video_path)
    input_dir = os.path.dirname(video_path)
    file_ext = os.path.splitext(input_file_name)[1]  # .png, .exr, etc
    
    # Determine frame number pattern
    if "%04d" in input_file_name:
        frame_pattern = "%04d"
        frame_digits = 4
    elif "%03d" in input_file_name:
        frame_pattern = "%03d"
        frame_digits = 3
    else:
        # Single file or unsupported pattern
        return None, video_path
    
    print(f"[SAM2 Worker] Creating temporary reordered sequence...")
    print(f"[SAM2 Worker]   Original: {video_path}")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="sam2_reorder_")
    print(f"[SAM2 Worker]   Temp dir: {temp_dir}")
    
    # Create symlinks/copies in reordered sequence
    reordered_basename = f"frame_{frame_pattern}{file_ext}"
    
    created_count = 0
    for reading_idx, actual_frame in index_to_frame.items():
        # Source file (actual frame number)
        if frame_digits == 4:
            source_file = video_path.replace('%04d', f"{actual_frame:04}")
        else:
            source_file = video_path.replace('%03d', f"{actual_frame:03}")
        
        # Check if source file exists
        if not os.path.exists(source_file):
            print(f"[SAM2 Worker] ERROR: Source frame does not exist!")
            print(f"[SAM2 Worker]   Reading index: {reading_idx}")
            print(f"[SAM2 Worker]   Actual frame: {actual_frame}")
            print(f"[SAM2 Worker]   Source file: {source_file}")
            print(f"[SAM2 Worker]   Frame range: {frame_range[0]}-{frame_range[1]}")
            print(f"[SAM2 Worker]   Reference frame: {reference_frame}")
            raise FileNotFoundError(f"Frame {actual_frame} not found: {source_file}")
        
        # Destination file (reading index as frame number)
        dest_file = os.path.join(temp_dir, reordered_basename.replace(frame_pattern, f"{reading_idx:0{frame_digits}}"))
        
        # Try symlink first (fast), fallback to copy (slow but works)
        try:
            os.symlink(source_file, dest_file)
            created_count += 1
        except (OSError, NotImplementedError):
            # Symlink failed (no admin rights on Windows), use copy
            shutil.copy2(source_file, dest_file)
            created_count += 1
    
    reordered_video_path = os.path.join(temp_dir, reordered_basename)
    
    print(f"[SAM2 Worker]   Reordered: {reordered_video_path}")
    print(f"[SAM2 Worker]   Created {created_count}/{len(index_to_frame)} frame links/copies")
    
    return temp_dir, reordered_video_path

# Определяем конфигурацию модели
def determine_model_cfg(model_path):
    if "large" in model_path:
        return os.path.join(params["sam2_repo"], "sam2/configs/samurai/sam2.1_hiera_l.yaml")
    elif "base_plus" in model_path:
        return os.path.join(params["sam2_repo"], "sam2/configs/samurai/sam2.1_hiera_b+.yaml")
    elif "small" in model_path:
        return os.path.join(params["sam2_repo"], "sam2/configs/samurai/sam2.1_hiera_s.yaml")
    elif "tiny" in model_path:
        return os.path.join(params["sam2_repo"], "sam2/configs/samurai/sam2.1_hiera_t.yaml")
    else:
        raise ValueError("Unknown model!")

# Выполняем inference
temp_dir = None  # For cleanup
try:
    x, y, w, h = bbox_coord
    bbox = (x, y, x + w, y + h)
    
    model_cfg = determine_model_cfg(model_path)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    
    # STAGE 1: Model Loading
    print("STAGE:[1/7] Loading Model...")
    print("PROGRESS:0")
    print(f"[SAM2 Worker] Loading model: {model_path}")
    print(f"[SAM2 Worker] Device: {device}")
    
    predictor = build_sam2_video_predictor(model_cfg, model_path, device=device)
    print("PROGRESS:10")
    print("STAGE:[2/7] Reordering Frames...")
    
    # Create reordered sequence (reference frame becomes index 0)
    temp_dir, reordered_video_path = create_reordered_sequence(
        video_path, 
        index_to_frame, 
        frame_range
    )
    
    # If reordering failed (single file), use original path
    if reordered_video_path == video_path:
        print("[SAM2 Worker] WARNING: Could not reorder frames (single file?), using original sequence")
        print("[SAM2 Worker] Reference frame feature will not work correctly!")
        use_reordering = False
    else:
        use_reordering = True
        print(f"[SAM2 Worker] OK: Frames reordered successfully")
    
    print("PROGRESS:15")
    print("STAGE:[3/7] Initializing Video...")
    
    # Инициализация
    autocast_context = torch.autocast("cuda", dtype=torch.float16) if torch.cuda.is_available() else torch.autocast("cpu", enabled=False)
    
    total_frames = frame_range[1] - frame_range[0] + 1
    print("PROGRESS:20")
    print(f"STAGE:[4/7] Reading Frames (0/{total_frames})...")
    
    # NEW: Use reordered path for init_state
    # This makes SAM2 read frames in the order: [reference, reference+1, ..., max, min, ..., reference-1]
    # So reference frame becomes index 0 (SAM2 requirement!)
    init_video_path = reordered_video_path if use_reordering else video_path
    
    # For reordered sequence, frame range is now 0 to (total_frames-1)
    # IMPORTANT: SAM2 processes frames [frame_range_min, frame_range_max-1], not inclusive of max!
    # So we need to add +1 to get all frames processed
    init_frame_min = 0 if use_reordering else frame_range[0]
    init_frame_max = total_frames if use_reordering else (frame_range[1] + 1)
    
    print(f"[SAM2 Worker] Init state with frame range: {init_frame_min} - {init_frame_max-1} (requesting {init_frame_max} as max)")
    
    with torch.inference_mode(), autocast_context:
        state, images, frame_start = predictor.init_state(
            init_video_path,
            offload_video_to_cpu=True,
            frame_range_min=init_frame_min,
            frame_range_max=init_frame_max,
            original_fps=fps_original,
            target_fps=fps_target,
            bits=bits
        )
        
        print("PROGRESS:35")
        print(f"STAGE:[5/7] Detecting Object (Reference Frame {reference_frame})...")
        # frame_idx=0 now corresponds to reference_frame due to reordering!
        _, _, masks = predictor.add_new_points_or_box(state, box=bbox, frame_idx=0, obj_id=0)
        print("PROGRESS:40")
    
    # Получаем размеры изображения (from reference frame)
    input_file_name = os.path.splitext(os.path.basename(video_path))[0]
    if "%04d" in input_file_name:
        first_frame_path = video_path.replace('%04d', f"{reference_frame:04}")
    elif "%03d" in input_file_name:
        first_frame_path = video_path.replace('%03d', f"{reference_frame:03}")
    else:
        first_frame_path = video_path
    
    first_frame = cv2.imread(first_frame_path)
    if first_frame is None:
        print(f"[SAM2 Worker] ERROR: Cannot read reference frame: {first_frame_path}", file=sys.stderr)
        sys.exit(1)
    
    height, width = first_frame.shape[:2]
    print(f"[SAM2 Worker] Image size: {width}x{height}")
    
    output_dir = os.path.dirname(output_path)
    output_basename = os.path.splitext(os.path.basename(output_path))[0]
    
    # Propagation
    print(f"STAGE:[6/7] Propagating Masks (0/{total_frames})...")
    print(f"[SAM2 Worker] Starting propagation...")
    
    color = [(255, 255, 255)]
    
    # Track actual output format (may fallback to PNG)
    actual_output_path = output_path
    used_png_fallback = False
    
    # NEW: Frame counter for propagation
    # frame_idx from SAM2 is the READING index (0, 1, 2, ...)
    # We need to map it back to ACTUAL frame number using index_to_frame
    reading_idx = 0
    
    for frame_idx, object_ids, masks in predictor.propagate_in_video(state):
        # Map reading index to actual frame number
        if use_reordering:
            actual_frame_num = index_to_frame[reading_idx]
        else:
            actual_frame_num = frame_range[0] + reading_idx
        
        processed_frames = reading_idx + 1
        progress_base = 40  # Start from 40% (after detection)
        progress_range = 55  # Propagation takes 40-95%
        progress = int(progress_base + (processed_frames / total_frames) * progress_range)
        
        print(f"PROGRESS:{progress}")
        # Детальная информация с количеством кадров
        print(f"STAGE:[6/7] Processing Frame {processed_frames}/{total_frames} ({progress}%)")
        print(f"[SAM2 Worker] Reading index {reading_idx} -> Frame {actual_frame_num}")
        
        # Обработка масок
        mask_to_vis = {}
        for obj_id, mask in zip(object_ids, masks):
            mask = mask[0].cpu().numpy()
            mask = mask > 0.0
            mask_to_vis[obj_id] = mask
        
        # Создание изображения маски
        mask_img = np.zeros((height, width, 3), np.uint8)
        for obj_id, mask in mask_to_vis.items():
            mask_img[mask] = color[(obj_id + 1) % len(color)]
        
        # Determine file extension from output_path
        file_ext = os.path.splitext(output_path)[1]  # .png or .exr
        if not file_ext:
            file_ext = ".png"  # default to PNG
        
        # Build save path with correct extension
        # Use actual_frame_num (not reading_idx) for output file names
        if "%04d" in output_basename:
            save_path = os.path.join(output_dir, output_basename.replace('%04d', f"{actual_frame_num:04}") + file_ext)
        elif "%03d" in output_basename:
            save_path = os.path.join(output_dir, output_basename.replace('%03d', f"{actual_frame_num:03}") + file_ext)
        else:
            save_path = os.path.join(output_dir, f"{output_basename}_{actual_frame_num:04}{file_ext}")
        
        # Try to save in requested format
        try:
            success = cv2.imwrite(save_path, mask_img)
            if not success and file_ext.lower() == '.exr':
                # EXR failed, fallback to PNG
                save_path_png = save_path.replace('.exr', '.png').replace('.EXR', '.png')
                if not used_png_fallback:
                    # Update actual output path on first fallback
                    actual_output_path = output_path.replace('.exr', '.png').replace('.EXR', '.png')
                    used_png_fallback = True
                    print(f"[SAM2 Worker] WARNING: EXR not supported by OpenCV, using PNG")
                    print(f"[SAM2 Worker] Output format changed: {actual_output_path}")
                cv2.imwrite(save_path_png, mask_img)
        except Exception as e:
            # If saving failed, try PNG
            if file_ext.lower() != '.png':
                save_path_png = os.path.splitext(save_path)[0] + '.png'
                if not used_png_fallback:
                    # Update actual output path on first fallback
                    actual_output_path = os.path.splitext(output_path)[0] + '.png'
                    used_png_fallback = True
                    print(f"[SAM2 Worker] WARNING: {file_ext} save failed, using PNG")
                    print(f"[SAM2 Worker] Output format changed: {actual_output_path}")
                cv2.imwrite(save_path_png, mask_img)
        
        reading_idx += 1
    
    print(f"PROGRESS:95")
    print(f"STAGE:[7/7] Finalizing ({total_frames}/{total_frames} frames saved)...")
    print(f"[SAM2 Worker] All masks saved successfully!")
    
    # Cleanup temporary directory
    if temp_dir and os.path.exists(temp_dir):
        print(f"[SAM2 Worker] Cleaning up temporary directory: {temp_dir}")
        try:
            shutil.rmtree(temp_dir)
            print(f"[SAM2 Worker] OK: Temporary directory removed")
        except Exception as cleanup_error:
            print(f"[SAM2 Worker] WARNING: Failed to cleanup temp dir: {cleanup_error}")
    
    print(f"PROGRESS:100")
    print("STAGE:[COMPLETE] All Done!")
    if used_png_fallback:
        print(f"[SAM2 Worker] NOTE: Used PNG format (EXR not supported)")
    print(f"OUTPUT_PATH:{actual_output_path}")  # Для создания Read node в Nuke
    sys.exit(0)
    
except Exception as e:
    # Cleanup temporary directory even on error
    if temp_dir and os.path.exists(temp_dir):
        print(f"[SAM2 Worker] Cleaning up temporary directory after error: {temp_dir}")
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
    
    print(f"[SAM2 Worker] ERROR: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

