# AGENTS.md

This file provides context and instructions for AI coding agents working on the Solar Farm Synthetic Dataset Generation project.

## Project Overview

This project uses BlenderProc to generate synthetic datasets for solar farm construction site object detection. The goal is to create realistic aerial/nadir view images of solar piles (桩基) with YOLO-format annotations.

### Key Requirements
- Generate synthetic images matching real drone orthographic images (5280x3956 resolution)
- Create solar pile objects (cylindrical, metallic, 2-3m tall) in a grid layout
- Generate YOLO-format bounding box annotations
- Match real data characteristics: 30-40 pixel objects, dense grid layout (300+ piles per image)

## Current Status

### Working Components ✅
- ✅ BlenderProc installation and setup
- ✅ Basic scene creation (ground, objects)
- ✅ Object creation with category_id for segmentation
- ✅ Segmentation rendering setup (verified correct)
- ✅ **NEW**: `generate_solar_farm_simple.py` - Simple working version
  - Creates visible scenes (152+ unique pixel values)
  - Detects objects in segmentation maps
  - Uses proven working camera parameters (oblique view, -45°)

### Known Issues
- ❌ Pure color images in nadir view (camera not seeing scene)
- ❌ Objects not visible in segmentation maps for nadir view
- ⚠️  Works with oblique view (-50° to -45°) but not nadir view (-88° to -90°)
- ⚠️  **Current issue**: Only 1 pile visible (out of 48 created), positioned at image edge (center_x=0.992)
- ⚠️  Camera position needs optimization to center piles in image
- ✅ YOLO annotation generation working (added to simple version)

## Development Environment

### Setup
```bash
# Install BlenderProc in development mode
pip install -e .

# Install Blender dependencies
./install_blender_dependencies.sh

# Use custom Blender path on macOS
export PATH="/Users/leo/Library/Python/3.12/bin:$PATH"
blenderproc run <script.py> <output_dir> --custom-blender-path "/Applications/Blender.app"
```

### Key Dependencies
- BlenderProc 2.8.0
- Blender 4.2.0 (custom path: `/Applications/Blender.app`)
- Python packages: numpy, opencv-python, h5py, trimesh, imageio, scikit-learn

## File Structure

### Main Scripts
- `generate_solar_farm_dataset.py` - Main dataset generation script
- `download_blender.sh` - Blender download script for macOS
- `install_blender_dependencies.sh` - Install Python packages into Blender

### Documentation
- `FIX_SSL_AND_BLENDER.md` - Installation troubleshooting
- `REAL_DATA_ANALYSIS.md` - Analysis of real drone image data
- `SEGMENTATION_VERIFICATION.md` - Segmentation rendering verification
- `PURE_COLOR_IMAGE_FIX.md` - Pure color image issue diagnosis
- `FIXES_APPLIED.md` - Summary of fixes applied
- `SCENE_IMPROVEMENT_GUIDE.md` - Scene improvement suggestions
- **`DEBUG_SESSION_SUMMARY.md`** - Complete summary of current debugging session ⭐
- **`CAMERA_POSITION_DEBUG.md`** - Detailed camera position debugging record
- **`CODE_CHANGES_SUMMARY.md`** - Summary of all code changes

## Development Guidelines

### Code Style
- Follow PEP 257 docstring conventions
- Add type annotations to all functions
- Use descriptive variable names
- Add comments explaining BlenderProc-specific operations

### Testing
- Test with small scenes first (5x4 grid)
- Verify images are not pure color
- Check segmentation maps contain objects
- Validate YOLO annotations are generated

### Debugging Tips
- Always check image statistics (unique values, range, std dev)
- Verify objects are in scene: `len(bpy.context.scene.objects)`
- Check camera position relative to scene center
- Use oblique view (-50° to -45°) first to ensure scene is visible
- Print object locations and camera parameters for debugging

## Common Issues & Solutions

### Pure Color Images
**Symptom**: Generated images are uniform color (10-20 unique values)

**Possible Causes**:
1. Camera not seeing scene (wrong position/angle)
2. Scene objects not created or hidden
3. Camera FOV/height mismatch with scene size

**Solutions**:
- Use oblique view first to verify scene visibility
- Check camera position is relative to scene center
- Verify ground plane covers scene extent
- Calculate camera height based on scene size and FOV

### Objects Not in Segmentation
**Symptom**: Segmentation map only contains background (ID=0)

**Possible Causes**:
1. Objects too small in image (< 1 pixel)
2. Objects outside camera view
3. category_id not set correctly
4. Objects hidden or not rendered

**Solutions**:
- Verify `set_cp("category_id", 0)` is called
- Check `hide_render = False`
- Ensure objects are above ground (z > 0)
- Use lower camera height for better visibility

### BlenderProc Import Error
**Symptom**: `RuntimeError: The given script does not have a blenderproc import at the top!`

**Solution**: `import blenderproc as bproc` must be the FIRST line (before docstring)

## Real Data Characteristics

Based on analysis of real drone orthographic images:
- **Resolution**: 5280x3956 pixels
- **Object size**: 30-40 pixels (width: 34.6px avg, height: 37.6px avg)
- **Objects per image**: 323 average, up to 768
- **View angle**: Almost vertical (nadir/orthographic, ~-90°)
- **Camera height**: Estimated 30-60m for real drones

## New Development Approach

### Strategy: Start Simple, Build Up

1. **Phase 1: Minimal Working Example**
   - Use BlenderProc basic example as template
   - Create single pile object
   - Render from known working camera angle
   - Verify object appears in segmentation

2. **Phase 2: Grid Layout**
   - Add multiple piles in simple grid
   - Ensure all visible in single frame
   - Verify segmentation works for all

3. **Phase 3: Nadir View**
   - Gradually adjust camera angle from oblique to nadir
   - Adjust camera height to maintain object visibility
   - Calculate proper height based on scene size

4. **Phase 4: Scale Up**
   - Increase pile count to match real data (300+)
   - Add realistic materials and textures
   - Optimize for production use

### Key Principles
- **Test incrementally**: Each change should be verified
- **Use working examples**: Start from BlenderProc basic examples
- **Verify visibility first**: Ensure objects are visible before optimizing
- **Match real data gradually**: Don't try to match all characteristics at once

## Command Examples

### Basic Test
```bash
blenderproc run generate_solar_farm_dataset.py output/test \
  --num_cameras 1 \
  --num_piles_x 5 \
  --num_piles_y 4 \
  --pile_spacing 4.0 \
  --render_width 1920 \
  --render_height 1080
```

### Production (when working)
```bash
blenderproc run generate_solar_farm_dataset.py output/dataset \
  --num_cameras 50 \
  --num_piles_x 20 \
  --num_piles_y 15 \
  --pile_spacing 2.8 \
  --render_width 5280 \
  --render_height 3956
```

## References

- [BlenderProc Documentation](https://github.com/DLR-RM/BlenderProc)
- [AGENTS.md Format](https://github.com/agentsmd/agents.md)
- Real data: `/Users/leo/Library/CloudStorage/OneDrive-个人/创业/2025/1203-光伏板桩识别/DatasetId_853_1766643148/`

## Notes

- Current BlenderProc version: 2.8.0 (may have compatibility issues with Blender 4.2.0)
- Some fixes were applied to `blenderproc/python/renderer/RendererUtility.py` for Blender 4.2.0 compatibility
- SSL certificate issues during installation were resolved using `--trusted-host` flag

