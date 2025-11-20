"""
Обёртка для torch через subprocess
Позволяет использовать системный Python с рабочим torch
"""
import subprocess
import sys
import os
import json

SYSTEM_PYTHON = r"C:\Users\nfspr\AppData\Local\Programs\Python\Python310\python.exe"

def check_torch_available():
    """Проверка доступности torch в системном Python"""
    try:
        result = subprocess.run(
            [SYSTEM_PYTHON, "-c", "import torch; print(torch.__version__); print(torch.cuda.is_available())"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            version = lines[0] if len(lines) > 0 else "unknown"
            cuda = lines[1] if len(lines) > 1 else "False"
            return True, version, cuda == "True"
        return False, None, False
    except Exception as e:
        return False, str(e), False

def run_sam2_inference(
    video_path,
    output_path,
    bbox_coord,
    frame_range,
    model_path,
    fps_original,
    fps_target,
    bits
):
    """
    Запускает SAM2 inference через системный Python
    """
    # Создаём временный скрипт для выполнения
    script_dir = os.path.dirname(__file__)
    worker_script = os.path.join(script_dir, "sam2_worker.py")
    
    # Параметры в JSON
    params = {
        "video_path": video_path,
        "output_path": output_path,
        "bbox_coord": bbox_coord,
        "frame_range": frame_range,
        "model_path": model_path,
        "fps_original": fps_original,
        "fps_target": fps_target,
        "bits": bits,
        "sam2_repo": os.path.join(os.path.dirname(script_dir), "sam2_repo"),
    }
    
    params_json = json.dumps(params)
    
    # Запускаем worker в системном Python
    try:
        process = subprocess.Popen(
            [SYSTEM_PYTHON, worker_script, params_json],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return process
    except Exception as e:
        raise Exception(f"Failed to start SAM2 worker: {e}")

