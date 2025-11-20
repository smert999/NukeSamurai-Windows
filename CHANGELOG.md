# Changelog

All notable changes to NukeSamurai Windows GPU Edition will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] - 2025-01-20

### 🎉 Initial Release - Windows GPU Ready!

After 10+ hours of development, the plugin is fully adapted for Windows with GPU acceleration!

### ✨ Added

- **GPU Acceleration via Subprocess Architecture**
  - Worker script runs in system Python 3.10
  - Nuke Python 3.11 only handles UI
  - Clean separation bypasses DLL/ABI conflicts
  - RTX 4090 support: 100x speedup over CPU

- **Automatic Read Node Creation**
  - Read node created automatically after mask generation
  - Positioned 200px to the right of SAMURAI node
  - Automatically configured with correct mask path

- **PNG Support (8-bit)**
  - Default output format changed to PNG
  - OpenCV compatible on Windows (no EXR support in wheels)
  - Sufficient quality for binary masks (0/255)
  - Smaller file size, faster save

- **Real-time Progress Bar**
  - Progress updates via STDOUT parsing
  - Nuke ProgressTask shows frame-by-frame progress
  - Cancellable via progress bar

- **Clean Startup Logs**
  - Minimal console output on Nuke startup
  - One line: `[NukeSamurai] Plugin loaded (GPU via subprocess)`
  - All diagnostic logs removed

- **Auto-detection**
  - CUDA version detection
  - Model path resolution
  - Frame range calculation
  - FPS detection from input

### 🐛 Fixed

#### 1. PyTorch DLL Compatibility
- **Problem**: Nuke Python 3.11 incompatible with PyTorch DLLs
- **Root Cause**: ABI/CRT mismatch between Foundry-compiled Python and PyTorch wheels
- **Solution**: Subprocess architecture using system Python 3.10
- **Result**: torch with CUDA works perfectly in worker process

#### 2. Config File Path
- **Problem**: `Cannot find primary config 'sam2_repo\configs\samurai\...'`
- **Root Cause**: Missing `sam2/` in path (configs inside sam2 subdirectory)
- **Solution**: Changed path from `sam2_repo/configs` to `sam2_repo/sam2/configs`
- **Result**: Config files loaded correctly

#### 3. Encoding Errors
- **Problem**: `UnicodeEncodeError: 'charmap' codec can't encode character '❌'`
- **Root Cause**: Windows console cp1251 doesn't support emoji
- **Solution**: Removed all emoji from worker output, use plain text
- **Result**: Clean logs without encoding errors

#### 4. SAM2 nuke Import
- **Problem**: `ModuleNotFoundError: No module named 'nuke'` in worker
- **Root Cause**: SAM2's `misc.py` imports nuke (not available in system Python)
- **Solution**: Conditional import with NukeFallback class
- **Result**: SAM2 works in both Nuke and system Python environments

#### 5. Model Path Resolution
- **Problem**: `FileNotFoundError: '.../sam2_repo/../checkpoints/...'`
- **Root Cause**: Extra `..` in path caused wrong directory
- **Solution**: Removed `..` from model path join
- **Result**: Models load correctly from sam2_repo/checkpoints/

#### 6. Frame Range Calculation
- **Problem**: `IndexError: list index out of range` (182 iterations for 181 frames)
- **Root Cause**: `frame_max + 1` in frame range calculation
- **Solution**: Removed `+1`, UI range is now inclusive
- **Result**: Correct frame count, no index errors

#### 7. OpenEXR Support
- **Problem**: `OpenCV(4.12.0) error: OpenEXR codec is disabled`
- **Root Cause**: OpenCV Python wheels don't include OpenEXR on Windows
- **Solution**: Changed output to PNG (8-bit, fully compatible)
- **Result**: Masks save successfully without compilation

#### 8. Overflow Error
- **Problem**: `OverflowError: Python integer 257 out of bounds for uint8`
- **Root Cause**: Attempted 16-bit conversion on 8-bit array
- **Solution**: Direct PNG save without bit depth conversion
- **Result**: Masks save correctly

#### 9. UI File Type Options
- **Problem**: Only EXR and MP4 options in dropdown
- **Solution**: Added PNG as first option (default)
- **Result**: User can select PNG, EXR, or MP4

### 🔄 Changed

- **Default Output Format**: EXR → **PNG** (recommended for Windows)
- **Architecture**: In-process → **Subprocess** (DLL isolation)
- **init.py**: 94 lines → **16 lines** (removed all DLL pre-loading)
- **File Type Order**: PNG, EXR, MP4 (PNG first)
- **Worker Logging**: Full console output → Parsed progress + key messages

### 🗑️ Removed

- DLL pre-loading via ctypes (no longer needed)
- sys.path manipulation (subprocess handles environment)
- Torch imports in Nuke Python (subprocess only)
- Diagnostic print statements
- Unnecessary PATH modifications

### 📊 Performance

**Test System**: RTX 4090, Nuke 16.0v4, Windows 11

| Task | CPU Time | GPU Time | Speedup |
|------|----------|----------|---------|
| 181 frames (Base+ model) | 15-20 min | 15-20 sec | **100x** |
| Reading frames | N/A | 4 sec @ 38 FPS | - |
| Propagation | N/A | 10-15 sec @ 15-30 FPS | - |

### 🏗️ Technical Details

**Subprocess Architecture**:
```python
# Nuke Python 3.11 (UI)
def GenerateMask():
    params = prepare_parameters()
    subprocess.Popen([system_python, worker_script, params_json])
    monitor_progress()
    create_read_node()

# System Python 3.10 (Worker)
def main():
    torch.cuda.set_device(0)
    predictor = build_sam2_video_predictor()
    propagate_masks()
    save_png()
```

**Key Files Modified**:
- `init.py`: Simplified to 16 lines
- `nuke_samurai.py`: Added subprocess logic, removed torch imports
- `sam2_worker.py`: New worker script for system Python
- `sam2/utils/misc.py`: Conditional nuke imports with fallback

### 📝 Known Issues

- MP4 output not fully tested (PNG recommended)
- Large models (Large) may need more VRAM than 24GB for long sequences
- Progress bar doesn't show during frame reading (only during propagation)

### 🔮 Future Plans

- Multi-object selection support
- Batch processing
- Custom model training integration
- Real-time preview
- Better progress indication during frame reading

---

## [0.9.0] - Development Phase

### Development Log (10+ hours)

**Hour 0-2**: Initial setup
- Cloned original NukeSamurai
- Attempted direct PyTorch installation
- Discovered DLL compatibility issues

**Hour 2-4**: DLL debugging
- Tested various PyTorch versions (cu118, cu121, CPU-only)
- Attempted DLL pre-loading strategies
- Discovered root cause: ABI incompatibility

**Hour 4-6**: Subprocess architecture
- Designed subprocess solution
- Created sam2_worker.py
- Implemented progress monitoring

**Hour 6-8**: Bug fixes
- Fixed config paths
- Fixed encoding errors
- Fixed SAM2 nuke imports
- Fixed model paths

**Hour 8-10**: Polish and testing
- Fixed frame range calculation
- Added PNG support
- Added automatic Read node creation
- Cleaned up logs

**Hour 10+**: Documentation
- Created README.md
- Created INSTALL.md
- Created CHANGELOG.md
- Prepared for GitHub release

---

## Credits

- **Original NukeSamurai**: Theo-SAMINADIN-td
- **SAM 2.1**: Meta AI Research
- **Windows GPU Adaptation**: Ostrix (nfsprostreet2007@mail.ru)

---

**Made with ❤️ and lots of ☕ for the Nuke community**

