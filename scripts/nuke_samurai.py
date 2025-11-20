import nuke
import os
import threading
import gc
import subprocess
import json

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


    @classmethod
    def getBbox(cls):
        # Import cv2 locally (not available in Nuke Python by default)
        import cv2
        
        file_path = InputInfos.path
        
        # Check if file path is set
        if file_path is None or file_path == '':
            nuke.message("⚠️ Ошибка!\n\nСначала укажите путь к файлу:\n1. Нажмите 'Update Path'\n2. Затем нажмите 'Create Bounding Box'")
            return
        
        input_file_name = str(os.path.splitext(os.path.basename(file_path))[0])
        
        if "%04d" in input_file_name :
          file_path = file_path.replace('%04d', str(f"{int(nuke.thisNode().knob('FrameRangeMin').value()):04}")) 
        elif "%03d" in input_file_name :
          file_path =  file_path.replace('%03d', str(f"{int(nuke.thisNode().knob('FrameRangeMin').value()):03}"))    

        cls.input_path = file_path
        img_path = cls.input_path

        img = cv2.imread(img_path,  cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
        
        # Check if image loaded successfully
        if img is None:
            error_msg = f"⚠️ Ошибка загрузки изображения!\n\n"
            error_msg += f"Файл не найден или не может быть прочитан:\n{img_path}\n\n"
            error_msg += f"Проверьте:\n"
            error_msg += f"1. Путь указан правильно в 'File Path'\n"
            error_msg += f"2. Файл существует\n"
            error_msg += f"3. Формат файла поддерживается (jpg, png, exr, dpx и т.д.)\n"
            error_msg += f"4. У вас есть права на чтение файла"
            nuke.message(error_msg)
            return

        cv2.namedWindow("BBOX - Press Enter or Space to validate",0) 
        cv2.setWindowProperty("BBOX - Press Enter or Space to validate", cv2.WND_PROP_TOPMOST, 1)
        cv2.resizeWindow("BBOX - Press Enter or Space to validate", 1280, 720) 
        
        # Bounding Box window
        x,y,w,h = cv2.selectROI("BBOX - Press Enter or Space to validate",img, fromCenter=False, showCrosshair=False)

        cv2.waitKey(13)
        cv2.destroyWindow("BBOX - Press Enter or Space to validate") 

        cls.x = x
        cls.y = y
        cls.w = w
        cls.h = h
        cls.bounding_box_coord = x,y,w,h
        nuke.tprint(f"{x = } {y = }  {w = } {h = }")

        return x,y,w,h,cls.bounding_box_coord


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
    
    # Prepare parameters
    params = {
        "video_path": video_path,
        "output_path": video_output_path,
        "bbox_coord": list(bbox_coord),
        "frame_range": frame_range,
        "model_path": model_path,
        "fps_original": original_fps,
        "fps_target": target_fps,
        "bits": bits,
        "sam2_repo": sam2_repo,
    }
    
    params_json = json.dumps(params)
    
    # Start subprocess worker
    system_python = r"C:\Users\nfspr\AppData\Local\Programs\Python\Python310\python.exe"
    
    nuke.tprint("[SAMURAI] Starting SAM2 inference via system Python...")
    nuke.tprint(f"[SAMURAI] Using GPU: torch with CUDA in Python 3.10")
    
    # Save node position for Read node creation
    node_x = nuke.thisNode().xpos()
    node_y = nuke.thisNode().ypos()
    
    def run_worker():
        try:
            process = subprocess.Popen(
                [system_python, worker_script, params_json],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
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


    s['FPS'].setFlag(nuke.STARTLINE)
    s['FrameRangeMax'].clearFlag(nuke.STARTLINE)
    s['UpdatePath'].setFlag(nuke.STARTLINE)
    s['GenerateMask'].setFlag(nuke.STARTLINE)
    
    s['CreateBoundingBox'].setTooltip("Create a bounding box. Press Enter or space to validate. Press C to cancel.")
    s['FPS'].setTooltip("Target FPS for the output video")
    s['ModelType'].setTooltip("Choose your model type")
    s['OutputPath'].setTooltip("path/to/your/file_####.exr, to create an image sequence add #### or ### ")
    s['GenerateMask'].setTooltip("Generate Mask")
    