import blenderproc as bproc
"""
Generate synthetic dataset for solar farm construction site object detection.

This script creates a procedurally generated scene with:
- Solar piles (cylinders) arranged in a grid with variations
- Uneven ground with displacement and tire tracks
- Distractor objects (blue/yellow geometric primitives)
- YOLO format annotations for object detection

Author: Computer Vision Engineer
"""
import argparse
import numpy as np
import os
import cv2
from pathlib import Path
from typing import List, Tuple, Optional
import bpy


def write_yolo_annotations(
    output_dir: str,
    instance_segmaps: List[np.ndarray],
    instance_attribute_maps: List[dict],
    class_id: int = 0,
    image_prefix: str = "image_",
) -> None:
    """
    Write YOLO format annotations from segmentation maps.

    YOLO format: <class_id> <x_center> <y_center> <width> <height>
    All values are normalized (0-1).

    :param output_dir: Output directory for annotations
    :param instance_segmaps: List of instance segmentation maps
    :param instance_attribute_maps: List of attribute maps per frame
    :param class_id: Class ID for the target objects (default: 0 for "pile")
    :param image_prefix: Prefix for image filenames
    """
    os.makedirs(output_dir, exist_ok=True)
    labels_dir = os.path.join(output_dir, "labels")
    os.makedirs(labels_dir, exist_ok=True)

    for frame_idx, (segmap, attr_map) in enumerate(zip(instance_segmaps, instance_attribute_maps)):
        height, width = segmap.shape[:2]
        annotations = []

        # Create a mapping from instance ID to attributes
        # attr_map is a list of dicts: [{"idx": 0, "category_id": 0, ...}, ...]
        inst_id_to_attrs = {}
        if isinstance(attr_map, list):
            for attr_dict in attr_map:
                if isinstance(attr_dict, dict) and "idx" in attr_dict:
                    inst_id_to_attrs[attr_dict["idx"]] = attr_dict
        elif isinstance(attr_map, dict):
            inst_id_to_attrs = attr_map

        # Get unique instance IDs from segmentation map
        unique_ids = np.unique(segmap)
        
        # Debug: print first frame info
        if frame_idx == 0:
            print(f"Debug: Found {len(unique_ids)} unique IDs in segmap (excluding 0)")
            print(f"Debug: Attribute map has {len(inst_id_to_attrs)} entries")
            if len(inst_id_to_attrs) > 0:
                print(f"Debug: First few entries: {list(inst_id_to_attrs.items())[:3]}")
        
        for inst_id in unique_ids:
            if inst_id == 0:  # Skip background
                continue
            
            # Check if this instance belongs to our target class
            inst_info = inst_id_to_attrs.get(int(inst_id), {})
            category_id = inst_info.get("category_id", None)
            
            # Debug output for first frame
            if frame_idx == 0 and inst_id <= 5:
                print(f"Debug: inst_id={inst_id}, category_id={category_id}, inst_info={inst_info}")
            
            # If category_id is None, the instance might not be in the mapping
            # This can happen if the object is not visible or not properly registered
            if category_id is None:
                # If we have a mapping but this instance is not in it, skip it
                if len(inst_id_to_attrs) > 0:
                    continue
                # If no mapping at all, we can't determine the class - skip for safety
                continue
            elif category_id != class_id:
                continue
            
            # Create binary mask for this instance
            binary_mask = (segmap == inst_id).astype(np.uint8)
            
            # Find bounding box
            coords = np.column_stack(np.where(binary_mask > 0))
            if len(coords) == 0:
                continue
            
            y_min, x_min = coords.min(axis=0)
            y_max, x_max = coords.max(axis=0)
            
            # Calculate normalized YOLO format: center_x, center_y, width, height
            center_x = (x_min + x_max) / 2.0 / width
            center_y = (y_min + y_max) / 2.0 / height
            bbox_width = (x_max - x_min) / width
            bbox_height = (y_max - y_min) / height
            
            # Skip if bbox is too small
            if bbox_width < 0.01 or bbox_height < 0.01:
                continue
            
            annotations.append(f"{class_id} {center_x:.6f} {center_y:.6f} {bbox_width:.6f} {bbox_height:.6f}")
        
        # Write annotation file
        annotation_file = os.path.join(labels_dir, f"{image_prefix}{frame_idx:06d}.txt")
        with open(annotation_file, 'w') as f:
            f.write('\n'.join(annotations))


def create_pile_with_patch(
    location: np.ndarray,
    height: float = 2.0,
    radius: float = 0.15,
    has_patch: bool = False,
) -> Tuple[bproc.types.MeshObject, Optional[bproc.types.MeshObject]]:
    """
    Create a solar pile (cylinder) with optional white patch at base.

    :param location: 3D location [x, y, z]
    :param height: Height of the cylinder
    :param radius: Radius of the cylinder
    :param has_patch: Whether to add a white patch at the base
    :return: Tuple of (pile object, patch object or None)
    """
    # Create the main cylinder (pile)
    # Note: Blender's cylinder is created with center at origin
    # Increase radius slightly for better visibility
    pile = bproc.object.create_primitive("CYLINDER", radius=radius, depth=height)
    # Set location - the z coordinate positions the cylinder center
    # Since cylinder center is at origin, we move it up by height/2 to place base at z=0
    pile.set_location([location[0], location[1], location[2]])
    
    # Ensure object is visible (not hidden)
    pile.blender_obj.hide_set(False)
    pile.blender_obj.hide_render = False
    
    # Add slight random rotation jitter for some piles
    if np.random.random() < 0.3:  # 30% chance of tilt
        tilt_angle = np.random.uniform(-0.1, 0.1)  # Small tilt in radians
        pile.set_rotation_euler([tilt_angle, 0, np.random.uniform(0, 2 * np.pi)])
    else:
        pile.set_rotation_euler([0, 0, np.random.uniform(0, 2 * np.pi)])
    
    # Create metallic material for pile
    pile_material = pile.new_material("pile_material")
    # Metallic, semi-matte silver/grey - darker for better contrast against ground
    pile_material.set_principled_shader_value("Base Color", [0.6, 0.6, 0.65, 1.0])  # Darker silver-grey
    pile_material.set_principled_shader_value("Metallic", 0.85)  # High metallic
    pile_material.set_principled_shader_value("Roughness", 0.25)  # Semi-matte (slightly shinier)
    
    patch = None
    if has_patch:
        # Create irregular white patch at base (flat plane on ground)
        # The patch should be at ground level (z=0) or slightly above
        patch_size = np.random.uniform(0.3, 0.6)
        patch = bproc.object.create_primitive("PLANE", scale=[patch_size, patch_size, 1])
        # Place patch at ground level, slightly offset to avoid z-fighting
        patch.set_location([location[0], location[1], 0.01])
        patch.set_rotation_euler([np.pi/2, 0, np.random.uniform(0, 2 * np.pi)])
        
        # Create white material for patch (concrete backfill / disturbed earth)
        patch_material = patch.new_material("patch_material")
        patch_material.set_principled_shader_value("Base Color", [0.95, 0.95, 0.9, 1.0])
        patch_material.set_principled_shader_value("Roughness", 0.7)
    
    return pile, patch


def create_ground(
    size: float = 100.0,
    texture_path: Optional[str] = None,
) -> bproc.types.MeshObject:
    """
    Create uneven ground with displacement modifier and textures.

    :param size: Size of the ground plane
    :param texture_path: Optional path to muddy ground texture (placeholder if None)
    :return: Ground mesh object
    """
    # Create large ground plane
    ground = bproc.object.create_primitive("PLANE", scale=[size/2, size/2, 1])
    ground.set_location([0, 0, 0])
    
    # Add UV mapping for textures
    ground.add_uv_mapping("smart")
    
    # Create ground material - make it look like construction site / muddy ground
    ground_material = ground.new_material("ground_material")
    
    # Load texture if provided, otherwise use procedural
    if texture_path and os.path.exists(texture_path):
        # Load actual muddy ground texture
        # NOTE: For full PBR support, load multiple textures:
        # - Base color: texture_path
        # - Normal map: texture_path.replace('diffuse', 'normal')
        # - Roughness: texture_path.replace('diffuse', 'roughness')
        # - Displacement: texture_path.replace('diffuse', 'displacement')
        try:
            texture_image = bpy.data.images.load(texture_path, check_existing=True)
            ground_material.set_principled_shader_value("Base Color", texture_image)
            # Use the texture for displacement as well
            texture = bproc.material.create_procedural_texture('CLOUDS')
        except Exception as e:
            print(f"Warning: Could not load texture {texture_path}: {e}")
            print("Falling back to procedural texture")
            texture = bproc.material.create_procedural_texture('CLOUDS')
            # Use earthy brown color for construction site
            ground_material.set_principled_shader_value("Base Color", [0.35, 0.28, 0.22, 1.0])
    else:
        # Create procedural muddy texture for construction site
        texture = bproc.material.create_procedural_texture('CLOUDS')
        # Set base color to earthy brown/beige for construction site
        # More realistic color: brownish-gray like disturbed earth
        ground_material.set_principled_shader_value("Base Color", [0.35, 0.28, 0.22, 1.0])
    
    ground_material.set_principled_shader_value("Roughness", 0.95)  # Very rough, like dirt
    
    # Add displacement modifier with subdivision for uneven terrain
    # Re-enable displacement for realistic construction site appearance
    # Use moderate displacement to add terrain variation without hiding objects
    try:
        ground.add_displace_modifier(
            texture=texture,
            strength=0.3,  # Moderate displacement for subtle uneven terrain
            subdiv_level=2,  # Medium subdivision for smooth displacement
        )
    except Exception as e:
        print(f"Warning: Could not add displacement modifier: {e}")
        print("Using flat ground instead")
    
    # TODO: Add tire tracks simulation
    # To add tire tracks, create a darker texture pattern and blend it:
    # tire_track_texture = bproc.material.create_material_from_texture(
    #     "/path/to/tire_track_texture.jpg", "tire_track"
    # )
    # ground_material.infuse_texture(
    #     tire_track_texture,
    #     mode="overlay",
    #     strength=0.3,
    #     texture_scale=0.1  # Scale for linear patterns
    # )
    
    # TODO: Add random noise patches (lighter color for dry earth)
    # Similar approach as tire tracks but with lighter color and random placement
    
    return ground


def create_distractor_objects(
    num_objects: int = 10,
    area_size: float = 80.0,
) -> List[bproc.types.MeshObject]:
    """
    Create distractor objects (blue PVC pipes, yellow machinery parts).

    :param num_objects: Number of distractor objects to create
    :param area_size: Size of the area to scatter objects
    :return: List of distractor mesh objects
    """
    distractors = []
    
    for _ in range(num_objects):
        # Randomly choose between cube (machinery) and cylinder (PVC pipe)
        obj_type = np.random.choice(["CUBE", "CYLINDER"])
        
        if obj_type == "CUBE":
            obj = bproc.object.create_primitive("CUBE", scale=[np.random.uniform(0.5, 1.5), 
                                                               np.random.uniform(0.5, 1.5),
                                                               np.random.uniform(0.2, 0.5)])
            color = [1.0, 0.8, 0.0, 1.0]  # Yellow for machinery
        else:
            obj = bproc.object.create_primitive("CYLINDER", 
                                                radius=np.random.uniform(0.1, 0.2),
                                                depth=np.random.uniform(1.0, 3.0))
            color = [0.0, 0.3, 1.0, 1.0]  # Blue for PVC pipes
        
        # Random location
        obj.set_location([
            np.random.uniform(-area_size/2, area_size/2),
            np.random.uniform(-area_size/2, area_size/2),
            np.random.uniform(0.5, 2.0)
        ])
        obj.set_rotation_euler(np.random.uniform([0, 0, 0], [2*np.pi, 2*np.pi, 2*np.pi]))
        
        # Create material
        mat = obj.new_material(f"distractor_{obj_type.lower()}")
        mat.set_principled_shader_value("Base Color", color)
        mat.set_principled_shader_value("Roughness", 0.5)
        
        # Set category_id to -1 so they're not labeled as "pile"
        obj.set_cp("category_id", -1)
        
        distractors.append(obj)
    
    return distractors


def main() -> None:
    """Main function to generate the synthetic solar farm dataset."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic solar farm construction site dataset"
    )
    parser.add_argument(
        'output_dir',
        nargs='?',
        default="output/solar_farm",
        help="Path to where the final files will be saved"
    )
    parser.add_argument(
        '--num_piles_x',
        type=int,
        default=20,
        help="Number of piles in X direction (default: 20 to match real data density)"
    )
    parser.add_argument(
        '--num_piles_y',
        type=int,
        default=15,
        help="Number of piles in Y direction (default: 15 to match real data density)"
    )
    parser.add_argument(
        '--pile_spacing',
        type=float,
        default=2.8,
        help="Base spacing between piles in meters (with random jitter, default: 2.8m for dense grid)"
    )
    parser.add_argument(
        '--num_cameras',
        type=int,
        default=10,
        help="Number of camera poses to render"
    )
    parser.add_argument(
        '--texture_path',
        type=str,
        default=None,
        help="Path to muddy ground texture (optional)"
    )
    parser.add_argument(
        '--render_width',
        type=int,
        default=2640,
        help="Render width in pixels (default: 2640, use 5280 to match real data)"
    )
    parser.add_argument(
        '--render_height',
        type=int,
        default=1978,
        help="Render height in pixels (default: 1978, use 3956 to match real data)"
    )
    args = parser.parse_args()
    
    # Initialize BlenderProc
    bproc.init()
    
    # Set high resolution to match real drone images (5280x3956)
    # Real drone orthographic images are very high resolution
    # Use 5280x3956 to match the real dataset, or scale down for faster rendering
    # For testing, use 2640x1978 (half resolution) for faster rendering
    # For production, use 5280x3956 to match real data
    bproc.camera.set_resolution(args.render_width, args.render_height)
    
    # ========== CREATE GROUND ==========
    print("Creating ground...")
    ground = create_ground(size=100.0, texture_path=args.texture_path)
    ground.set_cp("category_id", -1)  # Not a target object
    
    # ========== CREATE PILES ==========
    print("Creating solar piles...")
    piles = []
    patches = []
    
    # Create a proper grid layout for solar farm
    # Solar farms typically have piles in regular rows and columns
    print(f"Creating {args.num_piles_x}x{args.num_piles_y} grid of solar piles...")
    
    # Create grid of piles with random jitter
    for i in range(args.num_piles_x):
        for j in range(args.num_piles_y):
            # Base position with jitter
            x = (i - args.num_piles_x/2) * args.pile_spacing + np.random.uniform(-0.5, 0.5)
            y = (j - args.num_piles_y/2) * args.pile_spacing + np.random.uniform(-0.5, 0.5)
            
            # Random height variation - increased for better visibility
            height = np.random.uniform(3.0, 4.0)  # Further increased: 3.0-4.0m
            # Location: z should be height/2 to place cylinder base at z=0
            # CRITICAL: Cylinder center must be at height/2, so base is at z=0
            # But we need to ensure the entire cylinder is well above ground
            # Since cylinder depth=height, center at z=height/2 means:
            #   - Top at z=height
            #   - Base at z=0
            # Add offset to ensure base is clearly above ground
            location = np.array([x, y, height/2 + 0.2])  # 0.2m offset: base at z=0.2m
            
            # 50% chance of having a white patch
            has_patch = np.random.random() < 0.5
            
            # Adjust radius for nadir view visibility
            # In real data, objects are 30-40 pixels in 5280x3956 images
            # For nadir view, need appropriate size to be visible
            # Increase radius slightly for better visibility in top-down view
            pile, patch = create_pile_with_patch(
                location=location,
                height=height,
                radius=0.4,  # 0.4m radius for better visibility in nadir view
                has_patch=has_patch,
            )
            
            # Set category_id for segmentation - MUST be set before rendering
            # Use a unique name to help with debugging
            pile.set_name(f"pile_{i}_{j}")
            pile.set_cp("category_id", 0)  # Class 0 = "pile"
            
            # Ensure object is visible and selectable
            pile.blender_obj.hide_set(False)
            pile.blender_obj.hide_render = False
            pile.blender_obj.select_set(True)
            
            # Verify it was set
            actual_cat_id = pile.get_cp("category_id")
            if actual_cat_id != 0:
                print(f"Warning: Failed to set category_id for pile at {location}, got {actual_cat_id}")
            else:
                # Debug: print first few pile locations
                if len(piles) < 3:
                    pile_loc = pile.get_location()
                    print(f"Debug: Pile {len(piles)} at {pile_loc}, category_id={actual_cat_id}, visible={not pile.blender_obj.hide_render}")
            
            piles.append(pile)
            
            if patch is not None:
                patch.set_name(f"patch_{i}_{j}")
                patch.set_cp("category_id", -1)  # Patches are not labeled
                patches.append(patch)
    
    # ========== CREATE DISTRACTORS ==========
    print("Creating distractor objects...")
    distractors = create_distractor_objects(num_objects=15, area_size=80.0)
    
    # ========== SETUP LIGHTING ==========
    print("Setting up lighting...")
    # Create SUN light with low angle for long shadows
    sun_light = bproc.types.Light()
    sun_light.set_type("SUN")
    sun_light.set_location([0, 0, 0])
    # Low sun angle: rotation around X and Y axes
    # This creates long shadows
    sun_light.set_rotation_euler([
        np.radians(-15),  # Low elevation (negative = low in sky)
        np.radians(45),   # Azimuth angle
        0
    ])
    sun_light.set_energy(5.0)  # High intensity
    sun_light.set_color([1.0, 0.95, 0.9])  # Slightly warm sunlight
    
    # ========== SETUP CAMERA ==========
    print("Setting up cameras...")
    # Resolution already set at initialization, don't override it here
    
    # Sample multiple camera poses
    # First, compute the center and bounds of all piles to ensure camera looks at them
    if len(piles) > 0:
        pile_locations = np.array([pile.get_location() for pile in piles])
        scene_center = pile_locations.mean(axis=0)
        scene_min = pile_locations.min(axis=0)
        scene_max = pile_locations.max(axis=0)
        scene_size = scene_max - scene_min
        max_extent = max(scene_size[0], scene_size[1])
        print(f"Debug: Scene center: {scene_center}, size: {scene_size}, max_extent: {max_extent}")
    else:
        scene_center = np.array([0, 0, 1])
        max_extent = 20
        print("Warning: No piles created!")
    
    # Set camera resolution BEFORE adding camera poses
    # This must be done after bproc.init() but before adding poses
    bproc.camera.set_resolution(args.render_width, args.render_height)
    print(f"Debug: Camera resolution set to {args.render_width}x{args.render_height}")
    
    for _ in range(args.num_cameras):
        # TEMPORARY: Use oblique view first to ensure we can see the scene
        # Once confirmed working, we can adjust to nadir view
        # Use proven working parameters from earlier tests
        height = np.random.uniform(8, 12)  # Lower height for visibility
        
        # Position camera around scene center with some distance
        distance = max(max_extent * 0.6, 8.0)
        distance = np.random.uniform(distance, distance * 1.2)
        angle = np.random.uniform(0, 2 * np.pi)
        x = scene_center[0] + distance * np.cos(angle)
        y = scene_center[1] + distance * np.sin(angle)
        
        # Pitch: -50 to -45 degrees (oblique view, proven to work)
        # This angle allows seeing both the grid layout and individual objects
        pitch = np.random.uniform(-50, -45)
        # Yaw: point towards scene center
        yaw = np.arctan2(scene_center[1] - y, scene_center[0] - x) + np.random.uniform(-0.1, 0.1)
        
        print(f"Debug: Using oblique view - height={height:.1f}m, distance={distance:.1f}m, pitch={pitch:.1f}°")
        
        # Convert to euler angles (Blender convention)
        euler_rotation = [np.radians(pitch), 0, yaw]
        
        cam2world = bproc.math.build_transformation_mat(
            [x, y, height],
            euler_rotation
        )
        bproc.camera.add_camera_pose(cam2world)
        
        # Debug: print camera position for first camera
        if _ == 0:
            offset_dist = np.sqrt(offset_x**2 + offset_y**2) if 'offset_x' in locals() else 0.0
            print(f"Debug: Camera position: ({x:.2f}, {y:.2f}, {height:.2f}), pitch: {pitch:.1f}° (nadir view)")
    
    print(f"Debug: Created {args.num_cameras} camera poses")
    print(f"Debug: Total objects in scene: {len(piles)} piles, {len(distractors)} distractors, {len(patches)} patches")
    if len(piles) > 0:
        first_pile_loc = piles[0].get_location()
        print(f"Debug: First pile location: {first_pile_loc}")
        print(f"Debug: First pile category_id: {piles[0].get_cp('category_id')}")
    
    # Debug: Print camera pose info
    if args.num_cameras > 0:
        # Get the last added camera pose (we can't easily get all, but this helps)
        print("Debug: Camera setup complete")
    
    # ========== RENDER ==========
    print("Rendering...")
    
    # Debug: Check all objects before rendering
    import bpy
    all_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    print(f"Debug: Total mesh objects in scene: {len(all_objects)}")
    pile_objects = [obj for obj in all_objects if 'pile' in obj.name.lower()]
    print(f"Debug: Pile objects found: {len(pile_objects)}")
    for i, obj in enumerate(pile_objects[:3]):
        cat_id = obj.get('category_id', 'N/A')
        # Check if object is above ground
        above_ground = obj.location.z > 0.5  # Should be at least 0.5m above ground
        print(f"  Pile {i}: {obj.name}, loc: ({obj.location.x:.2f}, {obj.location.y:.2f}, {obj.location.z:.2f}), cat_id: {cat_id}, above_ground: {above_ground}, visible: {not obj.hide_render}")
    
    # Enable segmentation output for bounding box generation
    # Use "category_id" and "instance" to get both class and instance segmentation
    # IMPORTANT: Set default_values to ensure objects without category_id get a default
    bproc.renderer.enable_segmentation_output(
        map_by=["category_id", "instance", "name"],
        default_values={"category_id": -1}  # Default for objects without category_id
    )
    
    # Debug: Check pass_index and category_id after enabling segmentation
    print(f"Debug: After enabling segmentation:")
    for i, obj in enumerate(pile_objects[:3]):
        cat_id_cp = obj.get('category_id', None)
        cat_id_blender = obj.get('category_id', None) if hasattr(obj, 'get') else None
        print(f"  Pile {i}: {obj.name}, pass_index: {obj.pass_index}, category_id: {cat_id_cp}")
    
    # Render
    data = bproc.renderer.render()
    
    # Debug: Check what we got
    print(f"Debug: Rendered {len(data.get('colors', []))} frames")
    print(f"Debug: Instance segmaps: {len(data.get('instance_segmaps', []))} frames")
    print(f"Debug: Attribute maps: {len(data.get('instance_attribute_maps', []))} frames")
    if len(data.get('instance_segmaps', [])) > 0:
        segmap = data['instance_segmaps'][0]
        unique_ids = np.unique(segmap)
        print(f"Debug: Unique IDs in first segmap: {unique_ids}")
        print(f"Debug: Segmap shape: {segmap.shape}, min={segmap.min()}, max={segmap.max()}")
    if len(data.get('instance_attribute_maps', [])) > 0:
        print(f"Debug: First frame attribute map type: {type(data['instance_attribute_maps'][0])}")
        print(f"Debug: First frame attribute map length: {len(data['instance_attribute_maps'][0]) if isinstance(data['instance_attribute_maps'][0], list) else 'N/A'}")
        if isinstance(data['instance_attribute_maps'][0], list):
            print(f"Debug: All entries: {data['instance_attribute_maps'][0]}")
    
    # ========== SAVE OUTPUTS ==========
    print("Saving outputs...")
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Save RGB images
    images_dir = os.path.join(args.output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    for frame_idx, color_image in enumerate(data["colors"]):
        # Convert to BGR for OpenCV
        color_bgr = color_image.copy()
        color_bgr[..., :3] = color_bgr[..., :3][..., ::-1]
        
        image_path = os.path.join(images_dir, f"image_{frame_idx:06d}.jpg")
        cv2.imwrite(image_path, (color_bgr * 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 95])
    
    # Write YOLO format annotations
    write_yolo_annotations(
        output_dir=args.output_dir,
        instance_segmaps=data["instance_segmaps"],
        instance_attribute_maps=data["instance_attribute_maps"],
        class_id=0,  # Class 0 = "pile"
        image_prefix="image_",
    )
    
    # Also save HDF5 for visualization
    bproc.writer.write_hdf5(args.output_dir, data)
    
    print(f"Dataset generated successfully in: {args.output_dir}")
    print(f"  - Images: {images_dir}")
    print(f"  - Labels: {os.path.join(args.output_dir, 'labels')}")
    print(f"  - Total frames: {len(data['colors'])}")


if __name__ == "__main__":
    main()

