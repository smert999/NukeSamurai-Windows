"""
Обёртка для torch через subprocess
Позволяет использовать системный Python с рабочим torch

NOTE: This file is kept for reference but is NOT used.
The main Python detection logic is in nuke_samurai.py
"""
import subprocess
import sys
import os
import json
import shutil


def find_system_python():
    """
    Автоматический поиск Python 3.10/3.11/3.12
    Returns: путь к python.exe или None
    """
    def is_compatible_python(python_path):
        try:
            result = subprocess.run([python_path, '--version'], capture_output=True, text=True, timeout=5)
            version_output = result.stdout + result.stderr
            for ver in ['Python 3.10', 'Python 3.11', 'Python 3.12']:
                if ver in version_output:
                    return True
        except:
            pass
        return False
    
    # Method 0: Environment variable
    env_python = os.getenv('SAMURAI_PYTHON')
    if env_python and os.path.exists(env_python):
        return env_python
    
    # Method 1: Try 'python' in PATH
    python_cmd = shutil.which('python')
    if python_cmd and is_compatible_python(python_cmd):
        return python_cmd
    
    # Method 2: Try 'python3' in PATH
    python3_cmd = shutil.which('python3')
    if python3_cmd and is_compatible_python(python3_cmd):
        return python3_cmd
    
    # Method 3: Try Python Launcher (py.exe)
    py_cmd = shutil.which('py')
    if py_cmd:
        for py_ver in ['-3.12', '-3.11', '-3.10']:
            try:
                result = subprocess.run([py_cmd, py_ver, '-c', 'import sys; print(sys.executable)'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    found_python = result.stdout.strip()
                    if found_python and os.path.exists(found_python):
                        return found_python
            except:
                pass
    
    # Method 4: Common installation paths
    username = os.getenv('USERNAME', 'User')
    common_paths = [
        rf"C:\Users\{username}\AppData\Local\Programs\Python\Python312\python.exe",
        rf"C:\Users\{username}\AppData\Local\Programs\Python\Python311\python.exe",
        rf"C:\Users\{username}\AppData\Local\Programs\Python\Python310\python.exe",
        r"C:\Python312\python.exe",
        r"C:\Python311\python.exe",
        r"C:\Python310\python.exe",
        r"C:\Program Files\Python312\python.exe",
        r"C:\Program Files\Python311\python.exe",
        r"C:\Program Files\Python310\python.exe",
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    # Method 5: Windows Registry
    try:
        import winreg
        for py_ver in ['3.12', '3.11', '3.10']:
            for hkey in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
                try:
                    key_path = rf"SOFTWARE\Python\PythonCore\{py_ver}\InstallPath"
                    with winreg.OpenKey(hkey, key_path) as key:
                        install_path = winreg.QueryValue(key, None)
                        python_exe = os.path.join(install_path, 'python.exe')
                        if os.path.exists(python_exe):
                            return python_exe
                except (FileNotFoundError, OSError):
                    pass
    except ImportError:
        pass
    
    return None


# Auto-detect Python on module load
SYSTEM_PYTHON = find_system_python()


def check_torch_available():
    """Проверка доступности torch в системном Python"""
    if not SYSTEM_PYTHON:
        return False, "Python not found", False
    
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
    if not SYSTEM_PYTHON:
        raise Exception("Python 3.10/3.11/3.12 not found!")
    
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
