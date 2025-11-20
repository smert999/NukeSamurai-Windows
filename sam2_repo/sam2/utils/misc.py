# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"
import gc
import warnings
from threading import Thread
from tqdm import tqdm
import numpy as np
import torch
from PIL import Image
from tqdm import tqdm

# Conditional nuke import - only available in Nuke environment
try:
    import nuke
except ImportError:
    # Fallback when not in Nuke (e.g., subprocess worker)
    class NukeFallback:
        @staticmethod
        def tprint(msg):
            print(msg)
        
        @staticmethod
        def message(msg):
            print(msg)
        
        @staticmethod
        def createNode(node_type):
            pass
        
        @staticmethod
        def selectedNode():
            return None
        
        @staticmethod
        def root():
            class Root:
                @staticmethod
                def knob(name):
                    class Knob:
                        @staticmethod
                        def getValue():
                            return 1000
                    return Knob()
            return Root()
        
        class ProgressTask:
            def __init__(self, name):
                self.name = name
                print(f"[Progress] {name}")
            
            def setProgress(self, progress):
                pass
            
            def setMessage(self, msg):
                pass
            
            def isCancelled(self):
                return False
    
    nuke = NukeFallback()

import cv2
import re

def get_sdpa_settings():
    if torch.cuda.is_available():
        old_gpu = torch.cuda.get_device_properties(0).major < 7
        # only use Flash Attention on Ampere (8.0) or newer GPUs
        use_flash_attn = torch.cuda.get_device_properties(0).major >= 8
        if not use_flash_attn:
            warnings.warn(
                "Flash Attention is disabled as it requires a GPU with Ampere (8.0) CUDA capability.",
                category=UserWarning,
                stacklevel=2,
            )
        # keep math kernel for PyTorch versions before 2.2 (Flash Attention v2 is only
        # available on PyTorch 2.2+, while Flash Attention v1 cannot handle all cases)
        pytorch_version = tuple(int(v) for v in torch.__version__.split(".")[:2])
        if pytorch_version < (2, 2):
            warnings.warn(
                f"You are using PyTorch {torch.__version__} without Flash Attention v2 support. "
                "Consider upgrading to PyTorch 2.2+ for Flash Attention v2 (which could be faster).",
                category=UserWarning,
                stacklevel=2,
            )
        math_kernel_on = pytorch_version < (2, 2) or not use_flash_attn
    else:
        old_gpu = True
        use_flash_attn = False
        math_kernel_on = True

    return old_gpu, use_flash_attn, math_kernel_on


def get_connected_components(mask):
    """
    Get the connected components (8-connectivity) of binary masks of shape (N, 1, H, W).

    Inputs:
    - mask: A binary mask tensor of shape (N, 1, H, W), where 1 is foreground and 0 is
            background.

    Outputs:
    - labels: A tensor of shape (N, 1, H, W) containing the connected component labels
              for foreground pixels and 0 for background pixels.
    - counts: A tensor of shape (N, 1, H, W) containing the area of the connected
              components for foreground pixels and 0 for background pixels.
    """
    from sam2 import _C

    return _C.get_connected_componnets(mask.to(torch.uint8).contiguous())


def mask_to_box(masks: torch.Tensor):
    """
    compute bounding box given an input mask

    Inputs:
    - masks: [B, 1, H, W] masks, dtype=torch.Tensor

    Returns:
    - box_coords: [B, 1, 4], contains (x, y) coordinates of top left and bottom right box corners, dtype=torch.Tensor
    """
    B, _, h, w = masks.shape
    device = masks.device
    xs = torch.arange(w, device=device, dtype=torch.int32)
    ys = torch.arange(h, device=device, dtype=torch.int32)
    grid_xs, grid_ys = torch.meshgrid(xs, ys, indexing="xy")
    grid_xs = grid_xs[None, None, ...].expand(B, 1, h, w)
    grid_ys = grid_ys[None, None, ...].expand(B, 1, h, w)
    min_xs, _ = torch.min(torch.where(masks, grid_xs, w).flatten(-2), dim=-1)
    max_xs, _ = torch.max(torch.where(masks, grid_xs, -1).flatten(-2), dim=-1)
    min_ys, _ = torch.min(torch.where(masks, grid_ys, h).flatten(-2), dim=-1)
    max_ys, _ = torch.max(torch.where(masks, grid_ys, -1).flatten(-2), dim=-1)
    bbox_coords = torch.stack((min_xs, min_ys, max_xs, max_ys), dim=-1)

    return bbox_coords


def _load_img_as_tensor(img_path, image_size):
    img_pil = Image.open(img_path)
    img_np = np.array(img_pil.convert("RGB").resize((image_size, image_size)))
    if img_np.dtype == np.uint8:  # np.uint8 is expected for JPEG images
        img_np = img_np / 255.0
    else:
        raise RuntimeError(f"Unknown image dtype: {img_np.dtype} on {img_path}")
    img = torch.from_numpy(img_np).permute(2, 0, 1)
    video_width, video_height = img_pil.size  # the original video size
    
    return img, video_height, video_width


class AsyncVideoFrameLoader:
    """
    A list of video frames to be load asynchronously without blocking session start.
    """

    def __init__(
        self,
        img_paths,
        image_size,
        offload_video_to_cpu,
        img_mean,
        img_std,
        compute_device,
    ):
        self.img_paths = img_paths
        self.image_size = image_size
        self.offload_video_to_cpu = offload_video_to_cpu
        self.img_mean = img_mean
        self.img_std = img_std
        # items in `self.images` will be loaded asynchronously
        self.images = [None] * len(img_paths)
        # catch and raise any exceptions in the async loading thread
        self.exception = None
        # video_height and video_width be filled when loading the first image
        self.video_height = None
        self.video_width = None
        self.compute_device = compute_device

        # load the first frame to fill video_height and video_width and also
        # to cache it (since it's most likely where the user will click)
        self.__getitem__(0)

        # load the rest of frames asynchronously without blocking the session start
        def _load_frames():
            try:
                for n in tqdm(range(len(self.images)), desc="frame loading (JPEG)"):
                    self.__getitem__(n)
            except Exception as e:
                self.exception = e

        self.thread = Thread(target=_load_frames, daemon=True)
        self.thread.start()

    def __getitem__(self, index):
        if self.exception is not None:
            raise RuntimeError("Failure in frame loading thread") from self.exception

        img = self.images[index]
        if img is not None:
            return img

        img, video_height, video_width = _load_img_as_tensor(
            self.img_paths[index], self.image_size
        )
        self.video_height = video_height
        self.video_width = video_width
        # normalize by mean and std
        img -= self.img_mean
        img /= self.img_std
        if not self.offload_video_to_cpu:
            img = img.to(self.compute_device, non_blocking=True)
        # self.images[index] = img
        return img

    def __len__(self):
        return len(self.images)


# def load_video_frames(
#     video_path,
#     image_size,
#     offload_video_to_cpu,
#     frame_range_min,
#     frame_range_max,
#     original_fps,
#     target_fps,
#     bits,
#     img_mean=(0.485, 0.456, 0.406),
#     img_std=(0.229, 0.224, 0.225),
#     async_loading_frames=False,
#     compute_device=torch.device("cuda"),
    
# ):
#     """
#     Load the video frames from video_path. The frames are resized to image_size as in
#     the model and are loaded to GPU if offload_video_to_cpu=False. This is used by the demo.
#     """
#     return ImgSequences(video_path, frame_range_min, frame_range_max, original_fps, target_fps, bits, image_size).ReadSequence()
    
#     # is_bytes = isinstance(video_path, bytes)
#     # is_str = isinstance(video_path, str)
#     # is_mp4_path = is_str and os.path.splitext(video_path)[-1] in [".mp4", ".MP4"]
#     # if is_bytes or is_mp4_path:
#     #     return load_video_frames_from_video_file(
#     #         video_path=video_path,
#     #         image_size=image_size,
#     #         offload_video_to_cpu=offload_video_to_cpu,
#     #         img_mean=img_mean,
#     #         img_std=img_std,
#     #         compute_device=compute_device,
#     #     )
#     # elif is_str and os.path.isdir(video_path):
#     #     return load_video_frames_from_jpg_images(
#     #         video_path=video_path,
#     #         image_size=image_size,
#     #         offload_video_to_cpu=offload_video_to_cpu,
#     #         img_mean=img_mean,
#     #         img_std=img_std,
#     #         async_loading_frames=async_loading_frames,
#     #         compute_device=compute_device,
#     #     )
#     # else:
#     #     raise NotImplementedError(
#     #         "Only MP4 video and JPEG folder are supported at this moment"
#     #     )


def create_reads(
    save_path,
    output_video_path_folder,
    output_file_name,
    save_to_file
):
    # Now uses NukeFallback if not in real Nuke environment
    if save_to_file == "exr" :
        nuke.createNode('Read')
        if "%04d" in save_path :
            nuke.selectedNode().knob('file').setValue(r"%s" % str(os.path.dirname(save_path)) +"/"+
                                                                    str(os.path.splitext(os.path.basename(save_path.replace('%04d', '####')))[0]) +".exr")
        elif "%03d" in save_path :
            nuke.selectedNode().knob('file').setValue(r"%s" % str(os.path.dirname(save_path))+"/"+
                                                                    str(os.path.splitext(os.path.basename(save_path.replace('%03d', '###')))[0]) +".exr")
        nuke.selectedNode().knob('first').setValue(1)
        nuke.selectedNode().knob('last').setValue(int(nuke.root().knob('last_frame').getValue())) 
        nuke.tprint("Generating mask done")
        nuke.message("Generating mask done") 

    if save_to_file == "mp4" :
        nuke.createNode('Read')  
        nuke.selectedNode().knob('file').setValue(r"%s" % (os.path.join(output_video_path_folder,output_file_name + ".mp4")))
        nuke.selectedNode().knob('first').setValue(1)
        nuke.selectedNode().knob('last').setValue(int(nuke.root().knob('last_frame').getValue())) 
        nuke.tprint("Generating mask done")
        nuke.message("Generating mask done") 
    



class ImgSequences :
    
    def __init__(self, path, frame_range_min, frame_range_max, original_fps, target_fps, bits, image_size):
        self.path = path
        self.frame_range_min = frame_range_min
        self.frame_range_max = frame_range_max
        self.target_fps = target_fps
        self.original_fps = original_fps
        self.bits = bits 
        self.image_size = image_size
        self.input_path_folder = os.path.dirname(path) + "/"
        self.input_file_name = str(os.path.splitext(os.path.basename(path))[0])
        self.file_extension = str(os.path.splitext(os.path.basename(path))[1])
        
        
        if "%04d" in self.input_file_name :
            self.input_file_name_split = re.split("%04d", self.input_file_name)[0]
        elif "%03d" in self.input_file_name :
            self.input_file_name_split = re.split("%03d", self.input_file_name)[0]  
        else :
            raise TypeError("Input is not a sequence")
        

        cut_fn = re.split(r"[{}]".format(self.input_file_name_split[-1]), self.input_file_name)
        try : 
            self.index = cut_fn.index("%04d")
        except : 
             self.index = cut_fn.index("%03d")
       
        
    def ReadSequence(self):  
        original_fps = self.original_fps
        img_mean=(0.485, 0.456, 0.406)
        img_std=(0.229, 0.224, 0.225)
        img_mean = torch.tensor(img_mean, dtype=torch.float32)[:, None, None]
        img_std = torch.tensor(img_std, dtype=torch.float32)[:, None, None]

        # CPU Offload option is coming soon
        compute_device=torch.device("cuda")

        nuke.tprint('Reading image sequence : ' +str(self.path) )
        
        if self.target_fps < 0:
            self.target_fps = 24
        
        target_fps = self.target_fps
        stride = max(round(original_fps / target_fps), 1)
        # Get all frames in folder
        frame_paths = []  
        for filename in os.listdir(self.input_path_folder):
            
            if self.file_extension in os.path.basename(filename):
                
                if self.input_file_name_split in filename:
                    seq = os.path.join(self.input_path_folder, filename)
                    frame_paths.append(seq)   
        frame_paths = sorted(frame_paths)
            
        nuke.tprint(str(len(frame_paths)) + ' frames from sequence detected')    
        
        # Get all index
        convert_num = []
        for num in frame_paths:
            
            num = os.path.splitext(os.path.basename(num))[0]
            num = re.split(r"[{}]".format(self.input_file_name_split[-1]), num)
            num = num[self.index]
            
            convert_num.append(int(num))
        convert_num = np.array(convert_num)


        process_len = self.frame_range_max - self.frame_range_min
        frame_start = self.frame_range_min - np.min(convert_num)

        nuke.tprint('Process length : ' +str(process_len) )   
        nuke.tprint('Frame range : ' + str(self.frame_range_min) + " - " + str( self.frame_range_max-1)) 
        
        images = torch.zeros(process_len, 3, self.image_size, self.image_size, dtype=torch.float32)
        
        # Reading only necessary frames
        frame_count = 0   
        renderProgress = nuke.ProgressTask('Reading frames..')
        for fpath in tqdm(range(0,process_len), desc="Reading frames") :
            
            
            Step = 100 / process_len    
            renderProgress.setProgress(int(frame_count * Step))
            renderProgress.setMessage("Reading frames: (" + str(frame_count+1) + " of " + str(process_len) +")")
            if renderProgress.isCancelled():
                
                gc.collect()
                torch.cuda.empty_cache()
                del renderProgress
                raise Exception("Generation aborted")  
            
            if frame_count % stride == 0:
                
                fpath = frame_paths[frame_start]
                frame = cv2.imread(fpath, cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH ) 
                original_height,original_width = frame.shape[:2]
                frame = cv2.resize(frame, (self.image_size, self.image_size))
                frame = np.array(frame)
                frame = torch.from_numpy(frame).permute(2,0,1)

                if "float" not in self.bits :
                    
                    if "8" in self.bits:
                        #Normalizing 8 bit values to fit in a 0-1 range
                        frame = frame/255
                        
                    if "10" in self.bits:
                        #Normalizing 10 bit values to fit in a 0-1 range
                        frame = frame/1023
                        
                    if "12" in self.bits:
                        #Normalizing 12 bit values to fit in a 0-1 range
                        frame = frame/4095

                    if "14" in self.bits:
                        #Normalizing 12 bit values to fit in a 0-1 range
                        frame = frame/16383

                    if "16" in self.bits:
                        # Normalizing 16 bit values to fit in a 0-1 range
                        frame = frame/65535

                images[frame_count] = frame 
            frame_count += 1  
            frame_start += 1

       
        images = images.to(compute_device)
        img_mean = img_mean.to(compute_device)
        img_std = img_std.to(compute_device)
     
        # Normalizing by mean & std
        images -= img_mean
        images /= img_std
       
        
        frame_start = self.frame_range_min - np.min(convert_num)
        del renderProgress
        return images, original_height, original_width, frame_start



def load_video_frames_from_jpg_images(
    video_path,
    image_size,
    offload_video_to_cpu,
    img_mean=(0.485, 0.456, 0.406),
    img_std=(0.229, 0.224, 0.225),
    async_loading_frames=False,
    compute_device=torch.device("cuda"),
):
    """
    Load the video frames from a directory of JPEG files ("<frame_index>.jpg" format).

    The frames are resized to image_size x image_size and are loaded to GPU if
    `offload_video_to_cpu` is `False` and to CPU if `offload_video_to_cpu` is `True`.

    You can load a frame asynchronously by setting `async_loading_frames` to `True`.
    """
    if isinstance(video_path, str) and os.path.isdir(video_path):
        jpg_folder = video_path
    else:
        raise NotImplementedError(
            "Only JPEG frames are supported at this moment. For video files, you may use "
            "ffmpeg (https://ffmpeg.org/) to extract frames into a folder of JPEG files, such as \n"
            "```\n"
            "ffmpeg -i <your_video>.mp4 -q:v 2 -start_number 0 <output_dir>/'%05d.jpg'\n"
            "```\n"
            "where `-q:v` generates high-quality JPEG frames and `-start_number 0` asks "
            "ffmpeg to start the JPEG file from 00000.jpg."
        )

    frame_names = [
        p
        for p in os.listdir(jpg_folder)
        if os.path.splitext(p)[-1] in [".jpg", ".jpeg", ".JPG", ".JPEG"]
    ]
    frame_names.sort(key=lambda p: int(os.path.splitext(p)[0]))
    num_frames = len(frame_names)
    if num_frames == 0:
        raise RuntimeError(f"no images found in {jpg_folder}")
    img_paths = [os.path.join(jpg_folder, frame_name) for frame_name in frame_names]
    img_mean = torch.tensor(img_mean, dtype=torch.float32)[:, None, None]
    img_std = torch.tensor(img_std, dtype=torch.float32)[:, None, None]

    if async_loading_frames:
        lazy_images = AsyncVideoFrameLoader(
            img_paths,
            image_size,
            offload_video_to_cpu,
            img_mean,
            img_std,
            compute_device,
        )
        return lazy_images, lazy_images.video_height, lazy_images.video_width

    images = torch.zeros(num_frames, 3, image_size, image_size, dtype=torch.float32)

    
    for n, img_path in enumerate(tqdm(img_paths, desc="frame loading (JPEG)")):
        images[n], video_height, video_width = _load_img_as_tensor(img_path, image_size)
    if not offload_video_to_cpu:
        images = images.to(compute_device)
        img_mean = img_mean.to(compute_device)
        img_std = img_std.to(compute_device)


   

    # normalize by mean and std
    images -= img_mean
    images /= img_std
    
  
    return images, video_height, video_width


def load_video_frames_from_video_file(
    video_path,
    image_size,
    offload_video_to_cpu,
    img_mean=(0.485, 0.456, 0.406),
    img_std=(0.229, 0.224, 0.225),
    compute_device=torch.device("cuda"),
):
    """Load the video frames from a video file."""
    import decord

    img_mean = torch.tensor(img_mean, dtype=torch.float32)[:, None, None]
    img_std = torch.tensor(img_std, dtype=torch.float32)[:, None, None]
    # Get the original video height and width
    decord.bridge.set_bridge("torch")
    video_height, video_width, _ = decord.VideoReader(video_path).next().shape
    # Iterate over all frames in the video
    images = []
    for frame in decord.VideoReader(video_path, width=image_size, height=image_size):
        images.append(frame.permute(2, 0, 1))

    images = torch.stack(images, dim=0).float() / 255.0
    if not offload_video_to_cpu:
        images = images.to(compute_device)
        img_mean = img_mean.to(compute_device)
        img_std = img_std.to(compute_device)
    # normalize by mean and std
    images -= img_mean
    images /= img_std
    return images, video_height, video_width


def fill_holes_in_mask_scores(mask, max_area):
    """
    A post processor to fill small holes in mask scores with area under `max_area`.
    """
    # Holes are those connected components in background with area <= self.max_area
    # (background regions are those with mask scores <= 0)
    assert max_area > 0, "max_area must be positive"

    input_mask = mask
    try:
        labels, areas = get_connected_components(mask <= 0)
        is_hole = (labels > 0) & (areas <= max_area)
        # We fill holes with a small positive mask score (0.1) to change them to foreground.
        mask = torch.where(is_hole, 0.1, mask)
    except Exception as e:
        # Skip the post-processing step on removing small holes if the CUDA kernel fails
        warnings.warn(
            f"{e}\n\nSkipping the post-processing step due to the error above. You can "
            "still use SAM 2 and it's OK to ignore the error above, although some post-processing "
            "functionality may be limited (which doesn't affect the results in most cases; see "
            "https://github.com/facebookresearch/sam2/blob/main/INSTALL.md).",
            category=UserWarning,
            stacklevel=2,
        )
        mask = input_mask

    return mask


def concat_points(old_point_inputs, new_points, new_labels):
    """Add new points and labels to previous point inputs (add at the end)."""
    if old_point_inputs is None:
        points, labels = new_points, new_labels
    else:
        points = torch.cat([old_point_inputs["point_coords"], new_points], dim=1)
        labels = torch.cat([old_point_inputs["point_labels"], new_labels], dim=1)

    return {"point_coords": points, "point_labels": labels}
