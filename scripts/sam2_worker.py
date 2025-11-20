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

# Добавляем sam2_repo в path
sam2_repo = params["sam2_repo"]
if sam2_repo not in sys.path:
    sys.path.insert(0, sam2_repo)

# Теперь импортируем torch и SAM2
import torch
import cv2
import numpy as np
from sam2.build_sam import build_sam2_video_predictor
# NO nuke imports - worker runs in system Python!

print(f"[SAM2 Worker] torch {torch.__version__}, CUDA: {torch.cuda.is_available()}")

# Извлекаем параметры
video_path = params["video_path"]
output_path = params["output_path"].replace('.exr', '.png')  # OpenCV не поддерживает EXR, используем PNG
bbox_coord = params["bbox_coord"]
frame_range = params["frame_range"]
reference_frame_idx = params.get("reference_frame_idx", 0)  # Default to 0 (first frame) if not provided
model_path = os.path.join(params["sam2_repo"], params["model_path"])  # checkpoints inside sam2_repo!
fps_original = params["fps_original"]
fps_target = params["fps_target"]
bits = params["bits"]

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
try:
    x, y, w, h = bbox_coord
    bbox = (x, y, x + w, y + h)
    
    model_cfg = determine_model_cfg(model_path)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    
    # STAGE 1: Model Loading
    print("STAGE:Loading Model...")
    print(f"[SAM2 Worker] Loading model: {model_path}")
    print(f"[SAM2 Worker] Device: {device}")
    
    predictor = build_sam2_video_predictor(model_cfg, model_path, device=device)
    print("STAGE:Initializing Video...")
    
    # Инициализация
    autocast_context = torch.autocast("cuda", dtype=torch.float16) if torch.cuda.is_available() else torch.autocast("cpu", enabled=False)
    
    print("STAGE:Reading Frames...")
    with torch.inference_mode(), autocast_context:
        state, images, frame_start = predictor.init_state(
            video_path,
            offload_video_to_cpu=True,
            frame_range_min=frame_range[0],
            frame_range_max=frame_range[1],
            original_fps=fps_original,
            target_fps=fps_target,
            bits=bits
        )
        
        ref_frame_num = frame_range[0] + reference_frame_idx
        print(f"STAGE:Detecting Object on Frame {ref_frame_num}...")
        print(f"[SAM2 Worker] Using reference frame: {ref_frame_num} (index {reference_frame_idx} in sequence)")
        _, _, masks = predictor.add_new_points_or_box(state, box=bbox, frame_idx=reference_frame_idx, obj_id=0)
    
    # Получаем размеры изображения
    input_file_name = os.path.splitext(os.path.basename(video_path))[0]
    if "%04d" in input_file_name:
        first_frame_path = video_path.replace('%04d', f"{frame_range[0]:04}")
    elif "%03d" in input_file_name:
        first_frame_path = video_path.replace('%03d', f"{frame_range[0]:03}")
    else:
        first_frame_path = video_path
    
    first_frame = cv2.imread(first_frame_path)
    if first_frame is None:
        print(f"[SAM2 Worker] ERROR: Cannot read first frame: {first_frame_path}", file=sys.stderr)
        sys.exit(1)
    
    height, width = first_frame.shape[:2]
    output_dir = os.path.dirname(output_path)
    output_basename = os.path.splitext(os.path.basename(output_path))[0]
    
    # Propagation
    print("STAGE:Propagating Masks...")
    print(f"[SAM2 Worker] Starting propagation...")
    print(f"PROGRESS:0")  # Для парсинга Nuke
    
    frame_count = frame_range[0]
    total_frames = frame_range[1] - frame_range[0] + 1
    color = [(255, 255, 255)]
    
    for frame_idx, object_ids, masks in predictor.propagate_in_video(state):
        progress = int(((frame_count - frame_range[0]) / total_frames) * 100)
        print(f"PROGRESS:{progress}")  # Для парсинга
        # Детальная информация о текущем кадре
        print(f"STAGE:Frame {frame_count}/{frame_range[1]} ({progress}%)")
        print(f"[SAM2 Worker] Processing frame {frame_count}/{frame_range[1]}")
        
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
        
        # Сохранение (PNG вместо EXR - OpenCV не поддерживает EXR в Windows wheels)
        if "%04d" in output_basename:
            save_path = os.path.join(output_dir, output_basename.replace('%04d', f"{frame_count:04}") + ".png")
        elif "%03d" in output_basename:
            save_path = os.path.join(output_dir, output_basename.replace('%03d', f"{frame_count:03}") + ".png")
        else:
            save_path = os.path.join(output_dir, f"{output_basename}_{frame_count:04}.png")
        
        # Сохраняем PNG (8-bit достаточно для масок 0/255)
        cv2.imwrite(save_path, mask_img)
        
        frame_count += 1
    
    print(f"PROGRESS:100")
    print("STAGE:Saving Complete!")
    print(f"[SAM2 Worker] All masks saved successfully!")
    # Заменяем .exr на .png для Read node
    output_path_png = output_path.replace('.exr', '.png')
    print(f"OUTPUT_PATH:{output_path_png}")  # Для создания Read node в Nuke
    sys.exit(0)
    
except Exception as e:
    print(f"[SAM2 Worker] ERROR: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

