# Changelog

All notable changes to NukeSamurai Windows GPU Edition will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] - 2025-01-22

### 🎉 Major UX Improvements

This release focuses on dramatically improving the user experience with a brand new Timeline UI and detailed progress tracking!

### Added

#### 🎯 Timeline UI for Bounding Box Selection
The biggest feature of this release! Now you can **select ANY frame** to draw your bounding box, not just the first frame!

**Features:**
- **Visual Frame Browser** - See each frame before selecting
- **Interactive Trackbar** - Scrub through frames with a slider
- **Keyboard Navigation**:
  - `A` - Previous frame
  - `D` - Next frame
  - `Space/Enter` - Select current frame for bbox
  - `ESC` - Cancel
- **Frame Counter** - Always shows current frame number
- **On-screen Instructions** - No need to remember controls
- **Reference Frame Knob** - Shows which frame was used for bbox (read-only info field)

**Why it matters:**
- Objects might not be visible in the first frame
- You can choose the clearest frame for bbox
- Better initial detection = better propagation quality

**Technical Details:**
- Refactored `BoundingBox.getBbox()` method
- Added frame caching and loading system
- New `selected_frame` class variable
- New `ReferenceFrame` knob in SAMURAI node

---

#### 📊 Detailed Progress Bar
The progress bar now shows **exactly** what's happening at each stage!

**Before:**
```
Propagating Masks... 65%
```

**After:**
```
🎬 Processing Frame 45/181 (65%)
```

**Progress Stages:**
1. **⏳ Loading Model... (0-15%)** - Loading SAM2 checkpoint
2. **⚙️ Initializing Video... (15-20%)** - Setting up inference state
3. **📁 Reading Frames (0/181)... (20-35%)** - Loading image sequence
4. **🎯 Detecting Object (Frame 1001)... (35-40%)** - Initial bbox detection
5. **🚀 Propagating Masks (0/181)... (40-95%)** - Main processing loop
   - Shows: `🎬 Processing Frame 45/181 (65%)`
   - Updates in real-time
6. **💾 Finalizing (181/181 frames saved)... (95%)** - Cleanup
7. **✅ Complete! (100%)** - Done!

**Why it matters:**
- You know exactly how many frames are left
- Can estimate remaining time
- Better understanding of where time is spent
- Looks more professional 😎

**Technical Details:**
- Updated `sam2_worker.py` progress reporting
- Better progress calculation (40-95% for propagation, scaled by frames)
- Added emojis for visual clarity

---

#### 📖 Complete Documentation Overhaul

**Installation Guide:**
- ✅ **Step 0** added - "Where to download and place plugin"
- ✅ Explained `%USERPROFILE%` environment variable
- ✅ Showed expected folder structure
- ✅ Two methods: Release download OR git clone
- ✅ Verification steps

**Usage Guide (Completely Rewritten):**
- ✅ Step-by-step workflow (8 detailed steps)
- ✅ Screenshots-level descriptions
- ✅ What each button does
- ✅ Common mistakes to avoid
- ✅ Tips and best practices
- ✅ Typical workflow diagram
- ✅ Performance expectations

**Why it matters:**
- New users can get started without asking questions
- Reduces support burden
- Professional-looking documentation

---

### Changed

- **BoundingBox UI flow** - Now two-step: (1) Select frame → (2) Draw bbox
- **Progress bar granularity** - From 6 stages to 7 stages with frame counts
- **README structure** - More beginner-friendly, step-by-step approach

---

### Technical Details

#### Files Modified:
- `scripts/nuke_samurai.py`:
  - Refactored `BoundingBox.getBbox()` (~150 lines → ~250 lines)
  - Added `selected_frame` class variable
  - Added `ReferenceFrame` knob to `CreateSamuraiNode()`
  - Timeline UI with cv2 trackbar and keyboard controls
  
- `scripts/sam2_worker.py`:
  - Updated progress reporting (7 detailed stages)
  - Added frame count to progress messages
  - Better PROGRESS percentage scaling

- `README.md`:
  - Added "Step 0: Download and Place Plugin"
  - Complete rewrite of "Usage" section (8 steps)
  - Updated Changelog with v1.2.0
  - Updated feature list in header

- `CHANGELOG.md`:
  - Created this file! 🎉

#### API Changes:
- `BoundingBox.selected_frame` - NEW: stores frame number used for bbox
- `SAMURAI node.ReferenceFrame` - NEW: read-only knob showing selected frame

#### Backwards Compatibility:
- ✅ **Fully backwards compatible** with v1.1.0
- Old projects will continue to work
- `ReferenceFrame` defaults to `FrameRangeMin` if not set

---

### Performance

No performance changes - this release is purely UX improvements!

- Timeline UI adds ~1-2 seconds to bbox selection (worth it!)
- Progress bar adds negligible overhead (~0.01%)

---

### Known Issues

None reported yet!

---

### Migration from v1.1.0

**No migration needed!** Just replace files:

```bash
cd %USERPROFILE%\.nuke\NukeSamurai
# Backup old version (optional)
copy scripts\nuke_samurai.py scripts\nuke_samurai.py.v1.1.0.bak

# Download new version
# Extract to same location
```

Restart Nuke and you're good to go! ✅

---

## [1.1.0] - 2025-01-21

### Added

- **EXR automatic fallback** to PNG when OpenCV doesn't support EXR
- **Tooltip in UI** explaining file format support
- **Detailed progress stages** (Loading Model, Reading Frames, Detecting Object, Propagating)
- **OCIO colorspace support** for Read node (Linear/Utility - Linear - sRGB)
- **OpenEXR environment variable** support (OPENCV_IO_ENABLE_OPENEXR=1)

### Fixed

- **Read node creation context issue** (nuke.thisNode() in executeInMainThread)
- **EXR fallback path reporting** (worker now sends correct PNG path to Nuke)
- **Read node frame range** auto-configuration (first/last/origfirst/origlast)
- **Read node file existence check** before creation
- **Progress bar accuracy** (correct total_frames calculation)
- **cv2 import error** on Nuke startup (moved to local import in getBbox)

---

## [1.0.0] - 2025-01-20

### Added

- **GPU acceleration** через subprocess architecture
- **Automatic Read node creation** with proper settings
- **PNG support** (8-bit, OpenCV compatible)
- **Real-time progress bar** with stage names
- **Clean startup** (minimal logs, no spam)
- **Auto-detection** of CUDA version and Python path

### Fixed

- **PyTorch DLL compatibility** with Nuke Python 3.11 (subprocess isolation)
- **OpenEXR → PNG conversion** (OpenCV limitation on Windows)
- **Frame range calculation** (inclusive range)
- **Encoding errors** (emoji in Windows console)
- **Config path resolution** for SAM2 configs
- **Model path resolution** for checkpoints
- **SAM2 conditional nuke imports** (removed nuke dependency from SAM2 code)

### Changed

- **Default file type**: EXR → PNG
- **Architecture**: In-process → Subprocess
- **init.py**: 94 lines → 16 lines (cleaner!)

---

## [0.9.0] - 2025-01-15 (Beta)

### Initial Windows GPU Adaptation

- Forked from [Theo-SAMINADIN-td/NukeSamurai](https://github.com/Theo-SAMINADIN-td/NukeSamurai)
- Added Windows GPU support
- Fixed DLL conflicts
- Basic functionality working

---

## Links

- **Repository**: https://github.com/YOUR_USERNAME/NukeSamurai-Windows
- **Issues**: https://github.com/YOUR_USERNAME/NukeSamurai-Windows/issues
- **Original Plugin**: https://github.com/Theo-SAMINADIN-td/NukeSamurai
- **SAM 2**: https://github.com/facebookresearch/sam2

---

**Made with ❤️ for the Nuke community**
