import os
import os.path as osp
import numpy as np
import cv2
# torch imported lazily in main() to avoid load-time dependencies
import gc
import sys
import nuke
import threading

# sam2 imports moved to main() to avoid load-time torch dependency

color = [(255, 255, 255)]


def determine_model_cfg(model_path):
    if "large" in model_path:
        return "configs/samurai/sam2.1_hiera_l.yaml"
    elif "base_plus" in model_path:
        return "configs/samurai/sam2.1_hiera_b+.yaml"
    elif "small" in model_path:
        return "configs/samurai/sam2.1_hiera_s.yaml"
    elif "tiny" in model_path:
        return "configs/samurai/sam2.1_hiera_t.yaml"
    else:
        raise ValueError("Unknown model size in path!")

def main(
        video_path,
        video_output_path,
        bbox_coord, 
        save_to_file,
        frame_range,
        original_fps,                        
        target_fps,
        bits,
        model_path
    ):   
    # Lazy imports (DLL paths already registered in init.py)
    import torch
    print(f"[SAMURAI] torch {torch.__version__} loaded, CUDA: {torch.cuda.is_available()}")
    
    # Add sam2_repo to path
    current_dir = os.path.dirname(os.path.dirname(__file__))
    sam2_repo_path = os.path.join(current_dir, "sam2_repo")
    if sam2_repo_path not in sys.path:
        sys.path.insert(0, sam2_repo_path)
    
    from sam2.build_sam import build_sam2_video_predictor
    from sam2.utils.misc import create_reads

    nuke.tprint('Current thread : ' +str(threading.current_thread().name) )
   
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), model_path)

    x,y,w,h = bbox_coord
    bbox = (x, y, x + w, y + h)

    model_cfg = determine_model_cfg(model_path)
    # Use CPU device (torch CPU-only installed)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    predictor = build_sam2_video_predictor(model_cfg, model_path, device=device)
    frames_or_path = video_path
    input_file_name = str(os.path.splitext(os.path.basename(video_path))[0])
    
    # Get first frame name and shape
    if "%04d" in input_file_name :
        video_path = video_path.replace('%04d', str(f"{frame_range[0]:04}")) 
    elif "%03d" in input_file_name :
        video_path =  video_path.replace('%03d', str(f"{frame_range[0]:03}"))   
    first_frame = cv2.imread(video_path)
    height, width = first_frame.shape[:2]
            
    # Isolate name and folder
    output_video_path_folder = os.path.dirname(video_output_path) + "/"
    output_file_name = str(os.path.splitext(os.path.basename(video_output_path))[0])
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(os.path.join(output_video_path_folder,output_file_name + ".mp4"), fourcc, 30, (width, height))

    # Use autocast only if CUDA is available
    autocast_context = torch.autocast("cuda", dtype=torch.float16) if torch.cuda.is_available() else torch.autocast("cpu", enabled=False)
    
    with torch.inference_mode(), autocast_context:
        state, images, frame_start = predictor.init_state(
                                    frames_or_path,
                                    offload_video_to_cpu=True, 
                                    frame_range_min = frame_range[0],
                                    frame_range_max = frame_range[1],
                                    original_fps = original_fps,
                                    target_fps = target_fps,
                                    bits = bits)
    
        _, _, masks = predictor.add_new_points_or_box(state, box=bbox, frame_idx=0, obj_id=0)

    # Starting propagation
    renderProgress = nuke.ProgressTask('Propagate...')
    frame_count = frame_range[0]
    progress_count = 0
    for frame_idx, object_ids, masks in predictor.propagate_in_video(state):
        
        Step = 100 / (frame_range[1] - frame_range[0])    
        renderProgress.setProgress(int(progress_count * Step))
        renderProgress.setMessage("Propagate: (" + str(frame_count+1) + " of " + str(frame_range[1] - frame_range[0]) +")")
        if renderProgress.isCancelled():
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            del renderProgress
            raise Exception("Generation aborted") 
        
        mask_to_vis = {}
        bbox_to_vis = {}

        for obj_id, mask in zip(object_ids, masks):
            mask = mask[0].cpu().numpy()
            mask = mask > 0.0
            non_zero_indices = np.argwhere(mask)
            if len(non_zero_indices) == 0:
                bbox = [0, 0, 0, 0]
            else:
                y_min, x_min = non_zero_indices.min(axis=0).tolist()
                y_max, x_max = non_zero_indices.max(axis=0).tolist()
                bbox = [x_min, y_min, x_max - x_min, y_max - y_min]
            bbox_to_vis[obj_id] = bbox
            mask_to_vis[obj_id] = mask

            for obj_id, mask in mask_to_vis.items():
                mask_img = np.zeros((height, width, 3), np.uint8)
                mask_img[mask] = color[(obj_id + 1) % len(color)]

        ## Saving output
        # Save to exr
        if save_to_file == "exr":        
            try :        
                if "%04d" in video_output_path :
                    save_path = os.path.join(
                        
                        output_video_path_folder, output_file_name.replace('%04d', str(f"{frame_count:04}")))
                
                if "%03d" in video_output_path :
                    save_path = os.path.join(
                    output_video_path_folder, output_file_name.replace('%03d', str(f"{frame_count:03}")))
            except :
                raise TypeError("Image sequence should be path/to/img_#### or path/to/img_###")
            
            cv2.imwrite(r'%s' % save_path +".exr", mask_img.astype("float32"))
        # Save to mp4
        if save_to_file == "mp4" :

            out.write(mask_img) 

        progress_count += 1
        frame_count += 1 
    
    if save_to_file == "mp4" :
        out.release()
        
    # Create read nodes
    nuke.executeInMainThread(create_reads, args=(video_output_path, output_video_path_folder, output_file_name, save_to_file))
    
        
        
    del renderProgress
    del predictor, state
    gc.collect()
    torch.clear_autocast_cache()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


