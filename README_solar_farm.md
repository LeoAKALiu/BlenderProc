# Solar Farm Construction Site Dataset Generator

This script generates a synthetic dataset for object detection (YOLO format) of a solar farm construction site, specifically targeting "pile" detection.

## Features

- **Solar Piles**: Grid of metallic cylinders with:
  - Random height variations
  - Slight tilt/rotation jitter (30% of piles)
  - 50% have white patches at base (concrete backfill simulation)
  
- **Realistic Ground**:
  - Uneven terrain using displacement modifier with subdivision
  - Procedural muddy texture (can be replaced with PBR textures)
  - Placeholder for tire tracks and noise patches

- **Distractor Objects**:
  - Blue PVC pipes (cylinders)
  - Yellow machinery parts (cubes)
  - Not labeled as "pile" (category_id = -1)

- **Lighting & Camera**:
  - SunLight with low angle for long shadows
  - Oblique aerial view (30-60m height, -60° to -85° pitch)
  - Multiple camera poses for dataset diversity

- **Output**:
  - RGB images (JPG format)
  - YOLO format annotations (`<class_id> <x_center> <y_center> <width> <height>`)
  - HDF5 files for visualization

## Usage

### Basic Usage

```bash
blenderproc run generate_solar_farm_dataset.py output/solar_farm
```

### Advanced Usage

```bash
blenderproc run generate_solar_farm_dataset.py output/solar_farm \
    --num_piles_x 10 \
    --num_piles_y 8 \
    --pile_spacing 5.0 \
    --num_cameras 20 \
    --texture_path /path/to/muddy_ground_texture.jpg
```

### Parameters

- `output_dir`: Output directory (default: `output/solar_farm`)
- `--num_piles_x`: Number of piles in X direction (default: 8)
- `--num_piles_y`: Number of piles in Y direction (default: 6)
- `--pile_spacing`: Base spacing between piles in meters (default: 4.0)
- `--num_cameras`: Number of camera poses to render (default: 10)
- `--texture_path`: Path to muddy ground texture image (optional)

## Output Structure

```
output/solar_farm/
├── images/
│   ├── image_000000.jpg
│   ├── image_000001.jpg
│   └── ...
├── labels/
│   ├── image_000000.txt
│   ├── image_000001.txt
│   └── ...
└── 0.hdf5  (for visualization)
```

### YOLO Format

Each `.txt` file contains one line per detected pile:
```
0 0.523456 0.678901 0.123456 0.234567
```

Format: `<class_id> <x_center> <y_center> <width> <height>`
- All values are normalized (0-1)
- `class_id = 0` for "pile"
- Coordinates are relative to image dimensions

## Adding High-Quality Textures

### Ground Texture

To use a real muddy ground texture:

1. Download a PBR texture set (e.g., from [texturehaven.com](https://texturehaven.com))
2. Use the `--texture_path` parameter:
   ```bash
   blenderproc run generate_solar_farm_dataset.py output/solar_farm \
       --texture_path /path/to/muddy_ground_diffuse.jpg
   ```

3. For full PBR support, modify the `create_ground()` function to load:
   - Base color texture
   - Normal map
   - Roughness map
   - Displacement map

### Tire Tracks

To add tire tracks simulation:

1. Create a darker texture pattern for compressed mud
2. Use `ground_material.infuse_texture()` to blend it:
   ```python
   tire_track_texture = bproc.material.create_material_from_texture(
       "/path/to/tire_track_texture.jpg", "tire_track"
   )
   ground_material.infuse_texture(
       tire_track_texture,
       mode="overlay",
       strength=0.3
   )
   ```

## Visualization

View the generated dataset:

```bash
blenderproc vis hdf5 output/solar_farm/0.hdf5
```

## Customization

### Adjusting Pile Properties

Edit the `create_pile_with_patch()` function:
- `height`: Pile height range
- `radius`: Pile radius
- Material properties (metallic, roughness)

### Adjusting Lighting

Modify the sun light setup in `main()`:
- `set_rotation_euler()`: Sun angle (lower = longer shadows)
- `set_energy()`: Light intensity
- `set_color()`: Light color temperature

### Adjusting Camera

Modify camera sampling in `main()`:
- Height range: `np.random.uniform(30, 60)`
- Pitch range: `np.random.uniform(-85, -60)`
- Resolution: `bproc.camera.set_resolution(width, height)`

## Notes

- The script uses procedural textures by default for ground
- White patches are created as separate plane objects
- Distractor objects are automatically excluded from annotations
- All randomization uses `bproc.sampler` utilities for reproducibility

## Requirements

- BlenderProc installed
- Python 3.7+
- NumPy
- OpenCV (for image writing)

## Citation

If you use this dataset generator, please cite:
- BlenderProc: [paper](https://github.com/DLR-RM/BlenderProc)






