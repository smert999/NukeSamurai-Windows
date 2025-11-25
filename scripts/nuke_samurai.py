import nuke
import os
import threading
import gc
import subprocess
import json
import shutil
import sys

# NO torch or cv2 imports - using subprocess with system Python instead!
# cv2 is imported locally in getBbox() function

nuke.tprint('Current thread : ' +str(threading.current_thread().name) )


class BoundingBox :
    input_path = None
    x = None
    y = None
    w = None
    h = None
    bounding_box_coord = None
    selected_frame = None  # Store which frame was used for bbox selection


    @classmethod
    def getBbox(cls):
        # Import cv2 and numpy locally (not available in Nuke Python by default)
        import cv2
        import numpy as np
        
        file_path = InputInfos.path
        
        # Check if file path is set
        if file_path is None or file_path == '':
            nuke.message("⚠️ Ошибка!\n\nСначала укажите путь к файлу:\n1. Нажмите 'Update Path'\n2. Затем нажмите 'Create Bounding Box'")
            return
        
        # Get frame range from node
        frame_min = int(nuke.thisNode().knob('FrameRangeMin').value())
        frame_max = int(nuke.thisNode().knob('FrameRangeMax').value())
        
        input_file_name = str(os.path.splitext(os.path.basename(file_path))[0])
        base_file_path = file_path
        
        # Check if it's a sequence
        is_sequence = "%04d" in input_file_name or "%03d" in input_file_name
        
        if not is_sequence:
            # Single file - just load it
            cls.input_path = file_path
            img = cv2.imread(file_path, cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
            
            if img is None:
                error_msg = f"⚠️ Ошибка загрузки изображения!\n\n"
                error_msg += f"Файл не найден:\n{file_path}"
                nuke.message(error_msg)
                return
            
            # Simple mode - just select ROI
            cv2.namedWindow("BBOX - Press Enter or Space to validate", 0)
            cv2.setWindowProperty("BBOX - Press Enter or Space to validate", cv2.WND_PROP_TOPMOST, 1)
            cv2.resizeWindow("BBOX - Press Enter or Space to validate", 1280, 720)
            
            x, y, w, h = cv2.selectROI("BBOX - Press Enter or Space to validate", img, fromCenter=False, showCrosshair=False)
            cv2.destroyWindow("BBOX - Press Enter or Space to validate")
            
            cls.x = x
            cls.y = y
            cls.w = w
            cls.h = h
            cls.bounding_box_coord = x, y, w, h
            cls.selected_frame = frame_min
            nuke.tprint(f"[SAMURAI] Bbox: {x = } {y = } {w = } {h = }")
            return x, y, w, h, cls.bounding_box_coord
        
        # SEQUENCE MODE - with timeline UI
        nuke.tprint(f"[SAMURAI] Frame range: {frame_min}-{frame_max}")
        
        # State variables
        current_frame = [frame_min]  # Using list to make it mutable in nested function
        bbox_result = [None]  # Will store (x, y, w, h)
        selected_frame = [frame_min]  # Store which frame was used for bbox
        
        def load_frame(frame_num):
            """Load a specific frame from sequence"""
            if "%04d" in input_file_name:
                frame_path = base_file_path.replace('%04d', f"{frame_num:04}")
            elif "%03d" in input_file_name:
                frame_path = base_file_path.replace('%03d', f"{frame_num:03}")
            else:
                frame_path = base_file_path
            
            img = cv2.imread(frame_path, cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
            return img, frame_path
        
        # Load first frame to get dimensions
        initial_img, initial_path = load_frame(frame_min)
        
        if initial_img is None:
            error_msg = f"⚠️ Ошибка загрузки первого кадра!\n\n"
            error_msg += f"Файл не найден:\n{initial_path}"
            nuke.message(error_msg)
            return
        
        height, width = initial_img.shape[:2]
        
        # Create window with timeline controls
        window_name = "SAMURAI - Select Frame & Draw Bbox"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 800)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
        
        # Trackbar callback
        def on_trackbar(val):
            current_frame[0] = frame_min + val
        
        # Create trackbar for frame selection
        cv2.createTrackbar('Frame', window_name, 0, frame_max - frame_min, on_trackbar)
        cv2.setTrackbarPos('Frame', window_name, 0)
        
        # Display current image
        display_img = initial_img.copy()
        
        # Create instruction overlay
        def add_instructions(img, frame_num):
            """Add text overlay with instructions"""
            # Add SOLID background (100% opaque, very visible)
            cv2.rectangle(img, (10, 10), (750, 220), (240, 240, 240), -1)
            
            # Add green border
            cv2.rectangle(img, (10, 10), (750, 220), (0, 220, 0), 3)
            
            # Instructions with maximum contrast
            font = cv2.FONT_HERSHEY_DUPLEX  # More readable font
            
            # Current frame - large and bold
            cv2.putText(img, f"FRAME: {frame_num}", (25, 50), font, 1.1, (0, 0, 0), 4)
            
            # Section header
            cv2.putText(img, "CONTROLS:", (25, 95), font, 0.8, (200, 0, 0), 3)
            
            # Instructions - clear and bold
            cv2.putText(img, "A/D Keys = Previous/Next Frame", (35, 130), font, 0.65, (0, 0, 0), 2)
            cv2.putText(img, "Trackbar Above = Jump to Frame", (35, 160), font, 0.65, (0, 0, 0), 2)
            cv2.putText(img, "SPACE or ENTER = SELECT Frame", (35, 190), font, 0.7, (0, 150, 0), 3)
            
            # ESC warning in red corner
            cv2.putText(img, "ESC=Exit", (620, 210), font, 0.7, (0, 0, 255), 3)
            
            return img
        
        display_img = add_instructions(display_img, current_frame[0])
        cv2.imshow(window_name, display_img)
        
        # Main loop - navigate frames
        while True:
            key = cv2.waitKey(100) & 0xFF
            
            # ESC - cancel
            if key == 27:
                cv2.destroyWindow(window_name)
                nuke.message("❌ Bbox selection cancelled")
                return None
            
            # Space or Enter - select bbox
            if key == 32 or key == 13:
                break
            
            # A - previous frame
            if key == ord('a') or key == ord('A'):
                if current_frame[0] > frame_min:
                    current_frame[0] -= 1
                    cv2.setTrackbarPos('Frame', window_name, current_frame[0] - frame_min)
            
            # D - next frame
            if key == ord('d') or key == ord('D'):
                if current_frame[0] < frame_max:
                    current_frame[0] += 1
                    cv2.setTrackbarPos('Frame', window_name, current_frame[0] - frame_min)
            
            # Update from trackbar
            trackbar_pos = cv2.getTrackbarPos('Frame', window_name)
            new_frame = frame_min + trackbar_pos
            
            # Load new frame if changed
            if new_frame != current_frame[0]:
                current_frame[0] = new_frame
            
            # Always reload and display current frame
            current_img, current_path = load_frame(current_frame[0])
            
            if current_img is not None:
                display_img = current_img.copy()
                display_img = add_instructions(display_img, current_frame[0])
                cv2.imshow(window_name, display_img)
        
        # User pressed Space/Enter - select bbox on current frame
        selected_frame[0] = current_frame[0]
        final_img, final_path = load_frame(selected_frame[0])
        
        cv2.destroyWindow(window_name)
        
        if final_img is None:
            nuke.message(f"⚠️ Не удалось загрузить кадр {selected_frame[0]}")
            return None
        
        # Now show ROI selection on the selected frame
        roi_window = "SAMURAI - Draw Bounding Box (Enter to confirm)"
        cv2.namedWindow(roi_window, 0)
        cv2.setWindowProperty(roi_window, cv2.WND_PROP_TOPMOST, 1)
        cv2.resizeWindow(roi_window, 1280, 720)
        
        nuke.tprint(f"[SAMURAI] Selecting bbox on frame {selected_frame[0]}")
        
        x, y, w, h = cv2.selectROI(roi_window, final_img, fromCenter=False, showCrosshair=False)
        cv2.destroyWindow(roi_window)
        
        # Validate bbox
        if w == 0 or h == 0:
            nuke.message("⚠️ Bbox не выбран или имеет нулевой размер")
            return None
        
        # Save to class
        cls.x = x
        cls.y = y
        cls.w = w
        cls.h = h
        cls.bounding_box_coord = x, y, w, h
        cls.selected_frame = selected_frame[0]
        
        # Store the frame number in the node
        nuke.thisNode().knob('ReferenceFrame').setValue(selected_frame[0])
        
        nuke.tprint(f"[SAMURAI] ✅ Bbox selected: {x = } {y = } {w = } {h = } on frame {selected_frame[0]}")
        
        return x, y, w, h, cls.bounding_box_coord


class InputInfos :
    read = None
    path = None
    original_fps = None
    bits = None
    
    @classmethod
    def getInputInfos(cls):
        f = nuke.thisNode().dependencies()

        for i in f:
            cls.read = i

        # Get file path
        try :
            cls.path = cls.read.knob('file').getValue()
        except : 
            cls.path = ''

        # Get metadatas
        ## get input fps
        try :
            cls.original_fps = int(cls.read.metadata()['input/frame_rate'])  
        except :
            cls.original_fps = nuke.Root()['fps'].value()  

        ## Get input bit depth
        # Look for bitsperchannel into the metadatas 
        try : 
            cls.bits = cls.read.metadata()['input/bitsperchannel']   
        except :
            # Interpreting bit depth depending on the format
            nuke.tprint("No Bit Depth information in the input metadatas. Interpreting it from the input extension.")

            if cls.path.endswith("jpg") or cls.path.endswith("jpeg") or cls.path.endswith("png") or cls.path.endswith("tiff"):
                cls.bits = "8-bit fixed"
            elif cls.path.endswith("exr") :
                cls.bits = "32-bit float"
            else :
                TypeError("Cannot interpret bit depth from unsupported input format.")
       

def UpdatePath():
    InputInfos.getInputInfos()
    FilePath = InputInfos.path
    nuke.thisNode().knob('FilePath').setValue(FilePath)
    

def GenerateMask():
    # NEW: Use subprocess to run SAM2 in system Python (where torch WORKS with CUDA!)
    import subprocess
    import json
    
    Output_path = nuke.thisNode().knob('OutputPath').getValue()

    # Checks           
    if str(os.path.splitext(os.path.basename(Output_path))[0]) == '' :
        raise TypeError("You must assign a file name")
        
    if nuke.thisNode()['FilePath'].value().lower().endswith("mp4") :
        raise TypeError('Unsupported input format. Input must be an Image Sequence')
        
    file_type = nuke.thisNode().knob('FileType').value()
    if file_type in ["exr", "png"]:
        if ("%04d" not in Output_path) and ("%03d" not in Output_path):
            raise TypeError("Your file must contains '####' or '###'")
        

    # Get values
    video_path = nuke.thisNode().knob('FilePath').value()
    video_output_path = nuke.thisNode().knob('OutputPath').getValue()
    save_to_file = nuke.thisNode().knob('FileType').value()
    bbox_coord = BoundingBox.bounding_box_coord
    
    # Check all required fields
    frame_min = nuke.thisNode().knob('FrameRangeMin').value()
    frame_max = nuke.thisNode().knob('FrameRangeMax').value()
    fps_value = nuke.thisNode().knob('FPS').value()
    
    if frame_min is None or frame_max is None:
        nuke.message("⚠️ Ошибка!\n\nУкажите Frame Range (диапазон кадров)")
        return
    
    if fps_value is None or fps_value == 0:
        nuke.message("⚠️ Ошибка!\n\nУкажите Output Frame Rate (FPS)")
        return
    
    if InputInfos.original_fps is None:
        nuke.message("⚠️ Ошибка!\n\nНажмите 'Update Path' для получения информации о файле")
        return
    
    if bbox_coord is None:
        nuke.message("⚠️ Ошибка!\n\nСначала нажмите 'Create Bounding Box' и выделите объект")
        return
    
    frame_range = [int(frame_min), int(frame_max)]  # No +1, UI shows inclusive range
    original_fps = int(InputInfos.original_fps)                        
    target_fps = int(fps_value)
    bits = InputInfos.bits

    if nuke.thisNode().knob('ModelType').value() == 'Large' :
        model_path = "checkpoints/sam2.1_hiera_large.pt"
    elif nuke.thisNode().knob('ModelType').value() == 'Base+' :    
        model_path = "checkpoints/sam2.1_hiera_base_plus.pt"
    elif nuke.thisNode().knob('ModelType').value() == 'Small' :    
        model_path = "checkpoints/sam2.1_hiera_small.pt"
    elif nuke.thisNode().knob('ModelType').value() == 'Tiny' :    
        model_path = "checkpoints/sam2.1_hiera_tiny.pt"

    # NEW: Run SAM2 via subprocess in system Python
    script_dir = os.path.dirname(__file__)
    worker_script = os.path.join(script_dir, "sam2_worker.py")
    sam2_repo = os.path.join(os.path.dirname(script_dir), "sam2_repo")
    
    # Get reference frame (which frame was used for bbox selection)
    reference_frame = int(nuke.thisNode().knob('ReferenceFrame').value())
    
    # Prepare parameters
    params = {
        "video_path": video_path,
        "output_path": video_output_path,
        "bbox_coord": list(bbox_coord),
        "frame_range": frame_range,
        "reference_frame": reference_frame,  # NEW: Pass selected frame to worker
        "model_path": model_path,
        "fps_original": original_fps,
        "fps_target": target_fps,
        "bits": bits,
        "sam2_repo": sam2_repo,
    }
    
    nuke.tprint(f"[SAMURAI] Reference Frame: {reference_frame}")
    
    params_json = json.dumps(params)
    
    # Find system Python automatically
    # Helper function to check if Python version is compatible (3.10, 3.11, 3.12)
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
    
    system_python = None
    
    # Method 0: Check environment variable first (for advanced users)
    env_python = os.getenv('SAMURAI_PYTHON')
    if env_python and os.path.exists(env_python):
        system_python = env_python
    
    # Method 1: Try 'python' in PATH
    if not system_python:
        python_cmd = shutil.which('python')
        if python_cmd and is_compatible_python(python_cmd):
            system_python = python_cmd
    
    # Method 2: Try 'python3' in PATH
    if not system_python:
        python3_cmd = shutil.which('python3')
        if python3_cmd and is_compatible_python(python3_cmd):
            system_python = python3_cmd
    
    # Method 3: Try Python Launcher (py.exe) - common on Windows
    if not system_python:
        py_cmd = shutil.which('py')
        if py_cmd:
            # Try to get Python 3.10, 3.11, or 3.12 via py launcher
            for py_ver in ['-3.12', '-3.11', '-3.10']:
                try:
                    result = subprocess.run([py_cmd, py_ver, '-c', 'import sys; print(sys.executable)'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        found_python = result.stdout.strip()
                        if found_python and os.path.exists(found_python):
                            system_python = found_python
                            break
                except:
                    pass
    
    # Method 4: Try common installation paths
    if not system_python:
        username = os.getenv('USERNAME', 'User')
        common_paths = [
            # User-specific installations (most common)
            rf"C:\Users\{username}\AppData\Local\Programs\Python\Python312\python.exe",
            rf"C:\Users\{username}\AppData\Local\Programs\Python\Python311\python.exe",
            rf"C:\Users\{username}\AppData\Local\Programs\Python\Python310\python.exe",
            # System-wide installations
            r"C:\Python312\python.exe",
            r"C:\Python311\python.exe",
            r"C:\Python310\python.exe",
            r"C:\Program Files\Python312\python.exe",
            r"C:\Program Files\Python311\python.exe",
            r"C:\Program Files\Python310\python.exe",
            r"C:\Program Files (x86)\Python312\python.exe",
            r"C:\Program Files (x86)\Python311\python.exe",
            r"C:\Program Files (x86)\Python310\python.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                system_python = path
                break
    
    # Method 5: Search Windows Registry for Python installations
    if not system_python:
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
                                system_python = python_exe
                                break
                    except (FileNotFoundError, OSError):
                        pass
                if system_python:
                    break
        except ImportError:
            pass
    
    # If still not found, show error
    if not system_python:
        error_msg = "Python 3.10/3.11/3.12 not found!\n\n"
        error_msg += "Please install Python 3.10+ and add it to PATH:\n"
        error_msg += "https://www.python.org/downloads/\n\n"
        error_msg += "Make sure to check 'Add Python to PATH' during installation."
        nuke.message(error_msg)
        return
    
    nuke.tprint("[SAMURAI] Starting SAM2 inference via system Python...")
    nuke.tprint(f"[SAMURAI] Found Python: {system_python}")
    nuke.tprint(f"[SAMURAI] Using GPU: torch with CUDA")
    
    # Save node position for Read node creation
    node_x = nuke.thisNode().xpos()
    node_y = nuke.thisNode().ypos()
    
    def run_worker():
        try:
            # Prepare environment with sam2_repo in PYTHONPATH
            env = os.environ.copy()
            sam2_repo_path = os.path.join(os.path.dirname(worker_script), "..", "sam2_repo")
            sam2_repo_path = os.path.abspath(sam2_repo_path)
            
            # Add sam2_repo to PYTHONPATH so Python can import sam2 module
            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = sam2_repo_path + os.pathsep + env['PYTHONPATH']
            else:
                env['PYTHONPATH'] = sam2_repo_path
            
            nuke.tprint(f"[SAMURAI] PYTHONPATH: {sam2_repo_path}")
            
            process = subprocess.Popen(
                [system_python, worker_script, params_json],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )
            
            renderProgress = nuke.ProgressTask('SAM2 Propagation (GPU)')
            
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                
                line = line.strip()
                nuke.tprint(line)
                
                # Parse stage (current step)
                if line.startswith("STAGE:"):
                    try:
                        stage_name = line.split(":", 1)[1]
                        renderProgress.setMessage(stage_name)
                    except:
                        pass
                
                # Parse progress (percentage)
                if line.startswith("PROGRESS:"):
                    try:
                        progress = int(line.split(":")[1])
                        renderProgress.setProgress(progress)
                    except:
                        pass
                
                # Check cancellation
                if renderProgress.isCancelled():
                    process.kill()
                    del renderProgress
                    nuke.tprint("[SAMURAI] ❌ Cancelled by user")
                    return
            
            process.wait()
            del renderProgress
            
            if process.returncode == 0:
                nuke.tprint("[SAMURAI] ✅ Masks generated successfully!")
                
                # Capture frame range NOW (before executeInMainThread)
                captured_frame_min = int(frame_min)
                captured_frame_max = int(frame_max)
                captured_output_path = str(video_output_path)
                
                # Create Read node for masks in main thread
                def create_read_node():
                    try:
                        # Use captured values (not nuke.thisNode() which doesn't work here)
                        output_path_final = captured_output_path
                        
                        # Check if it's image sequence (supports %04d, %03d, ####, ###)
                        is_sequence = any(pattern in output_path_final for pattern in ["%04d", "%03d", "####", "###"])
                        
                        if is_sequence:
                            # Verify first frame exists
                            first_frame_path = output_path_final
                            if "%04d" in output_path_final:
                                first_frame_path = output_path_final.replace('%04d', f"{captured_frame_min:04}")
                            elif "%03d" in output_path_final:
                                first_frame_path = output_path_final.replace('%03d', f"{captured_frame_min:03}")
                            
                            if not os.path.exists(first_frame_path):
                                nuke.tprint(f"[SAMURAI] ⚠️ First frame not found: {first_frame_path}")
                                nuke.tprint(f"[SAMURAI] ℹ️  Masks path: {output_path_final}")
                                return
                            
                            # Create Read node with proper settings
                            read_node = nuke.nodes.Read(file=output_path_final)
                            
                            # Set frame range
                            read_node['first'].setValue(captured_frame_min)
                            read_node['last'].setValue(captured_frame_max)
                            read_node['origfirst'].setValue(captured_frame_min)
                            read_node['origlast'].setValue(captured_frame_max)
                            
                            # Set colorspace to linear (masks are linear data)
                            try:
                                read_node['colorspace'].setValue('linear')
                            except:
                                # If OCIO, try 'Linear' or 'Utility - Linear - sRGB'
                                try:
                                    read_node['colorspace'].setValue('Linear')
                                except:
                                    try:
                                        read_node['colorspace'].setValue('Utility - Linear - sRGB')
                                    except:
                                        nuke.tprint(f"[SAMURAI] ⚠️ Could not set colorspace, using default")
                            
                            # Position node
                            read_node.setXYpos(node_x + 200, node_y)
                            
                            nuke.tprint(f"[SAMURAI] ✅ Read node created: {output_path_final}")
                            nuke.tprint(f"[SAMURAI] ℹ️  Frame range: {captured_frame_min}-{captured_frame_max}")
                            nuke.tprint(f"[SAMURAI] ℹ️  Colorspace: {read_node['colorspace'].value()}")
                        else:
                            nuke.tprint(f"[SAMURAI] ⚠️ Read node not created: output must be image sequence (use %04d or ####)")
                    except Exception as e:
                        nuke.tprint(f"[SAMURAI] ⚠️ Could not create Read node: {e}")
                        import traceback
                        nuke.tprint(traceback.format_exc())
                
                nuke.executeInMainThread(create_read_node)
                
                # Show output path
                nuke.executeInMainThread(nuke.message, args=("✅ Генерация завершена!\n\nМаски сохранены в:\n" + video_output_path + "\n\nRead нода создана справа от узла SAMURAI!",))
            else:
                nuke.tprint(f"[SAMURAI] ❌ Worker failed with code {process.returncode}")
                nuke.executeInMainThread(nuke.message, args=("❌ Ошибка генерации!\n\nПроверьте консоль для деталей",))
                
        except Exception as e:
            nuke.tprint(f"[SAMURAI] ❌ Exception: {e}")
            nuke.executeInMainThread(nuke.message, args=(f"❌ Ошибка: {e}",))
    
    # Run in thread
    worker_thread = threading.Thread(target=run_worker)
    worker_thread.start()
    
    gc.collect()


def CreateSamuraiNode():

    # Creating node
    nuke.createNode('NoOp')
    s = nuke.selectedNode()

    # Adding knobs
    s.knob('name').setValue('SAMURAI')
    s.addKnob(nuke.File_Knob('FilePath', 'File Path'))
    s.addKnob(nuke.PyScript_Knob('UpdatePath', 'Update Path', 'UpdatePath()' ))
    s.addKnob(nuke.PyScript_Knob('CreateBoundingBox', 'Create Bounding Box', 'BoundingBox.getBbox()'))
   
    s.addKnob(nuke.Text_Knob(''))

    s.addKnob(nuke.Int_Knob("FPS", 'Output Frame Rate'))
    s.addKnob(nuke.Int_Knob("FrameRangeMin", 'Frame Range'))
    s.addKnob(nuke.Int_Knob("FrameRangeMax", ' '))
    
    # Reference frame (which frame was used for bbox selection)
    reference_frame_knob = nuke.Int_Knob("ReferenceFrame", 'Reference Frame')
    reference_frame_knob.setEnabled(False)  # Read-only, set by getBbox()
    reference_frame_knob.setTooltip("The frame number where bounding box was drawn (auto-set)")
    s.addKnob(reference_frame_knob)
    
    s.addKnob(nuke.Enumeration_Knob('ModelType', 'Model type', ['Base+','Large', 'Small', 'Tiny']))

    s.addKnob(nuke.Text_Knob(' ', ''))
    
    file_type_knob = nuke.Enumeration_Knob('FileType', 'File type', ['png', 'exr', 'mp4'])
    file_type_knob.setTooltip('PNG: Always works (recommended)\nEXR: Requires OpenCV with EXR support (may fallback to PNG)\nMP4: Not yet implemented')
    s.addKnob(file_type_knob)
    s.addKnob(nuke.File_Knob('OutputPath', 'Output Path'))
    s.addKnob(nuke.PyScript_Knob('GenerateMask', 'Generate Mask', 'GenerateMask()'))
    
    
    
    
### SETTING RANGES, DEFAULT VALUES, TOOLTIPS & FORMAT ###
    s['FPS'].setValue(int(nuke.root().knob('fps').getValue()))
    s['FrameRangeMin'].setValue(int(nuke.Root()['first_frame'].value())) 
    s['FrameRangeMax'].setValue(int(nuke.Root()['last_frame'].value())) 
    s['ReferenceFrame'].setValue(int(nuke.Root()['first_frame'].value()))


    s['FPS'].setFlag(nuke.STARTLINE)
    s['FrameRangeMax'].clearFlag(nuke.STARTLINE)
    s['ReferenceFrame'].clearFlag(nuke.STARTLINE)
    s['UpdatePath'].setFlag(nuke.STARTLINE)
    s['GenerateMask'].setFlag(nuke.STARTLINE)
    
    s['CreateBoundingBox'].setTooltip("Create a bounding box. Press Enter or space to validate. Press C to cancel.")
    s['FPS'].setTooltip("Target FPS for the output video")
    s['ModelType'].setTooltip("Choose your model type")
    s['OutputPath'].setTooltip("path/to/your/file_####.exr, to create an image sequence add #### or ### ")
    s['GenerateMask'].setTooltip("Generate Mask")
    