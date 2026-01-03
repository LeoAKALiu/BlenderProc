import blenderproc as bproc
"""
Simple solar farm dataset generator - starting from scratch with minimal approach.

⚠️ TEST ONLY: This is a minimal test version for debugging and verification.
For production use, please use generate_mountainous_solar_site.py instead.

This script uses a simple, incremental approach:
1. Create minimal scene (ground + few piles)
2. Use proven working camera parameters
3. Verify each step before adding complexity
4. Generate YOLO format annotations
"""

import argparse
import numpy as np
import os
import cv2
import random
import glob
from pathlib import Path
from typing import List, Tuple, Optional
import bpy


def create_simple_pile(location: np.ndarray, radius: float = 0.4, height: float = 3.0) -> bproc.types.MeshObject:
    """
    Create a cylindrical pile with a concrete backfill base.
    
    :param location: 3D location [x, y, z] where z is the base height
    :param radius: Radius of the cylinder
    :param height: Height of the cylinder
    :return: Pile mesh object (the main cylinder)
    """
    # Create main cylinder
    pile = bproc.object.create_primitive("CYLINDER", radius=radius, depth=height)
    
    # Position Jitter: Add random x/y offset (+/- 0.2m)
    jitter_x = np.random.uniform(-0.2, 0.2)
    jitter_y = np.random.uniform(-0.2, 0.2)
    pile.set_location([
        location[0] + jitter_x,
        location[1] + jitter_y,
        location[2] + height/2
    ])
    
    # Rotation Jitter: Randomly tilt the piles slightly (0-5 degrees)
    tilt_x = np.random.uniform(0, np.radians(5))  # Tilt around X axis
    tilt_y = np.random.uniform(0, np.radians(5))  # Tilt around Y axis
    tilt_z = np.random.uniform(0, 2 * np.pi)  # Random rotation around Z axis
    pile.set_rotation_euler([tilt_x, tilt_y, tilt_z])
    
    # Ensure visible
    pile.blender_obj.hide_set(False)
    pile.blender_obj.hide_render = False
    
    # Pile material - Realistic metallic silver/gray
    pile_material = pile.new_material("pile_material")
    pile_material.set_principled_shader_value("Base Color", [0.5, 0.5, 0.55, 1.0])  # Metallic silver/gray
    pile_material.set_principled_shader_value("Metallic", 0.85)
    pile_material.set_principled_shader_value("Roughness", 0.25)  # Slightly shiny
    
    # Create concrete backfill base - wider, flat cylinder at the base
    base_radius = 0.8  # Wider than pile
    base_height = 0.05  # Very flat
    base = bproc.object.create_primitive("CYLINDER", radius=base_radius, depth=base_height)
    
    # Position base at the bottom of the pile (slightly above ground to avoid z-fighting)
    # Use the same jitter as the pile so they stay aligned
    base_z = location[2] + base_height / 2 + 0.01
    base.set_location([
        location[0] + jitter_x,
        location[1] + jitter_y,
        base_z
    ])
    
    # Base should follow pile's rotation (slight tilt)
    base.set_rotation_euler([tilt_x, tilt_y, tilt_z])
    
    # Random scale to make it not a perfect circle (slight variation)
    # Scale X and Y independently for an elliptical shape
    scale_x = np.random.uniform(0.85, 1.15)
    scale_y = np.random.uniform(0.85, 1.15)
    base.set_scale([scale_x, scale_y, 1.0])  # Keep Z scale at 1.0
    
    # Ensure visible
    base.blender_obj.hide_set(False)
    base.blender_obj.hide_render = False
    
    # Base material - Whitish/light-grey concrete with high roughness
    base_material = base.new_material("base_material")
    # Light grey/white color for concrete backfill
    base_color = np.random.uniform([0.75, 0.75, 0.78], [0.9, 0.9, 0.92])  # Slight variation in whiteness
    base_material.set_principled_shader_value("Base Color", list(base_color) + [1.0])
    base_material.set_principled_shader_value("Metallic", 0.0)  # Non-metallic
    base_material.set_principled_shader_value("Roughness", 0.95)  # Very rough, like concrete
    
    # Set category_id for base (same as pile, or could be different)
    # For now, we'll use the same category_id as pile so it's part of the same object
    base.set_cp("category_id", 0)  # Same as pile
    
    return pile


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
        
        # Create mapping from instance ID to attributes
        inst_id_to_attrs = {}
        if isinstance(attr_map, list):
            for attr_dict in attr_map:
                if isinstance(attr_dict, dict) and "idx" in attr_dict:
                    inst_id_to_attrs[attr_dict["idx"]] = attr_dict
        elif isinstance(attr_map, dict):
            inst_id_to_attrs = attr_map
        
        unique_ids = np.unique(segmap)
        
        for inst_id in unique_ids:
            if inst_id == 0:  # Skip background
                continue
            
            inst_info = inst_id_to_attrs.get(int(inst_id), {})
            category_id = inst_info.get("category_id", None)
            
            if category_id is None or category_id != class_id:
                continue
            
            # Calculate bounding box from segmentation mask
            binary_mask = (segmap == inst_id).astype(np.uint8)
            coords = np.column_stack(np.where(binary_mask > 0))
            if len(coords) == 0:
                continue
            
            y_min, x_min = coords.min(axis=0)
            y_max, x_max = coords.max(axis=0)
            
            # Convert to YOLO format (normalized center, width, height)
            center_x = (x_min + x_max) / 2.0 / width
            center_y = (y_min + y_max) / 2.0 / height
            bbox_width = (x_max - x_min) / width
            bbox_height = (y_max - y_min) / height
            
            # Skip if bbox is too small
            if bbox_width < 0.005 or bbox_height < 0.005:
                continue
            
            annotations.append(f"{class_id} {center_x:.6f} {center_y:.6f} {bbox_width:.6f} {bbox_height:.6f}")
        
        # Write annotation file
        annotation_file = os.path.join(labels_dir, f"{image_prefix}{frame_idx:06d}.txt")
        with open(annotation_file, 'w') as f:
            f.write('\n'.join(annotations))
        
        if frame_idx == 0:
            print(f"   Generated {len(annotations)} annotations for frame {frame_idx}")


def load_ground_texture_from_folder(asset_folder: str) -> Optional[dict]:
    """
    Load PBR textures from a local asset folder (CC0 format).
    
    Expected structure:
    - GroundXXX_4K-JPG/
      - GroundXXX_4K-JPG_Color.jpg
      - GroundXXX_4K-JPG_Displacement.jpg
      - GroundXXX_4K-JPG_NormalGL.jpg
      - GroundXXX_4K-JPG_Roughness.jpg
    
    :param asset_folder: Path to the asset folder
    :return: Dictionary with texture paths, or None if not found
    """
    asset_path = Path(asset_folder)
    if not asset_path.exists():
        return None
    
    # Find all Ground texture folders
    ground_folders = list(asset_path.glob("Ground*_4K-JPG"))
    if not ground_folders:
        return None
    
    # Randomly select one ground texture
    selected_folder = random.choice(ground_folders)
    folder_name = selected_folder.name
    
    # Build texture paths
    textures = {
        'base_color': selected_folder / f"{folder_name}_Color.jpg",
        'displacement': selected_folder / f"{folder_name}_Displacement.jpg",
        'normal': selected_folder / f"{folder_name}_NormalGL.jpg",
        'roughness': selected_folder / f"{folder_name}_Roughness.jpg",
    }
    
    # Check if base color exists (required)
    if not textures['base_color'].exists():
        return None
    
    return textures


def scatter_debris(
    num_debris: int = 75,
    area_size: float = 100.0,
    ground_z: float = 0.0
) -> List[bproc.types.MeshObject]:
    """
    Scatter random debris objects on the ground as negative samples.
    
    These objects will NOT be labeled as piles (category_id != 0).
    They serve as negative samples for the YOLO model.
    
    :param num_debris: Number of debris objects to create (50-100)
    :param area_size: Size of the area to scatter debris
    :param ground_z: Z coordinate of the ground
    :return: List of debris mesh objects
    """
    debris_objects = []
    
    # Random number of debris between 50-100
    if num_debris < 50:
        num_debris = np.random.randint(50, 101)
    
    print(f"Scattering {num_debris} debris objects...")
    
    for i in range(num_debris):
        # Random position within area
        x = np.random.uniform(-area_size/2, area_size/2)
        y = np.random.uniform(-area_size/2, area_size/2)
        
        # Random object type: cube or flattened box
        obj_type = np.random.choice(["CUBE", "BOX"])
        
        if obj_type == "CUBE":
            # Regular cube
            size = np.random.uniform(0.3, 0.8)
            debris = bproc.object.create_primitive("CUBE", size=size)
        else:
            # Flattened box (like a flat panel or sheet)
            # Create cube first, then scale it to desired dimensions
            length = np.random.uniform(0.5, 1.5)
            width = np.random.uniform(0.5, 1.5)
            height = np.random.uniform(0.05, 0.15)  # Very flat
            debris = bproc.object.create_primitive("CUBE", size=1.0)  # Create unit cube
            # Scale to desired dimensions (cube is 2x2x2 by default, so divide by 2)
            debris.set_scale([length/2, width/2, height/2])
        
        # Position on ground (slightly above to avoid z-fighting)
        debris.set_location([x, y, ground_z + debris.get_scale()[2] / 2 + 0.01])
        
        # Random rotation for more natural look
        debris.set_rotation_euler([
            np.random.uniform(0, 2 * np.pi),
            np.random.uniform(0, 2 * np.pi),
            np.random.uniform(0, 2 * np.pi)
        ])
        
        # Ensure visible
        debris.blender_obj.hide_set(False)
        debris.blender_obj.hide_render = False
        
        # Random color assignment
        color_type = np.random.choice(["blue", "yellow", "dark_grey"], p=[0.33, 0.33, 0.34])
        
        debris_material = debris.new_material(f"debris_material_{i}")
        
        if color_type == "blue":
            # Blue (like PVC pipes or plastic)
            blue_color = np.random.uniform([0.1, 0.3, 0.7], [0.2, 0.5, 0.9])
            debris_material.set_principled_shader_value("Base Color", list(blue_color) + [1.0])
            debris_material.set_principled_shader_value("Metallic", 0.0)
            debris_material.set_principled_shader_value("Roughness", 0.6)
        elif color_type == "yellow":
            # Yellow (like machinery parts or construction equipment)
            yellow_color = np.random.uniform([0.7, 0.6, 0.1], [0.9, 0.8, 0.3])
            debris_material.set_principled_shader_value("Base Color", list(yellow_color) + [1.0])
            debris_material.set_principled_shader_value("Metallic", 0.3)
            debris_material.set_principled_shader_value("Roughness", 0.5)
        else:  # dark_grey
            # Dark grey (like rocks or metal debris)
            grey_color = np.random.uniform([0.15, 0.15, 0.15], [0.3, 0.3, 0.3])
            debris_material.set_principled_shader_value("Base Color", list(grey_color) + [1.0])
            debris_material.set_principled_shader_value("Metallic", 0.2)
            debris_material.set_principled_shader_value("Roughness", 0.8)
        
        # IMPORTANT: Set category_id to -1 (background) so they are NOT labeled as piles
        # Piles have category_id = 0, so these will be filtered out in YOLO annotation generation
        # Note: User requested category_id=0, but in our code 0=pile, -1=background
        # Setting to -1 ensures debris are NOT labeled (which is the intent)
        debris.set_cp("category_id", -1)
        
        debris.set_name(f"debris_{i}")
        debris_objects.append(debris)
    
    print(f"Created {len(debris_objects)} debris objects (negative samples)")
    return debris_objects


def create_simple_ground(size: float = 50.0, asset_path: Optional[str] = None) -> bproc.types.MeshObject:
    """
    Create a ground plane with PBR textures and displacement modifier.
    
    :param size: Size of the ground plane
    :param asset_path: Path to the asset folder containing textures (e.g., /Volumes/leo_disk/asset)
    :return: Ground mesh object
    """
    ground = bproc.object.create_primitive("PLANE", scale=[size/2, size/2, 1])
    ground.set_location([0, 0, 0])
    
    # Add UV mapping for textures
    ground.add_uv_mapping("smart")
    
    # Try to load PBR textures from asset folder
    textures = None
    if asset_path:
        textures = load_ground_texture_from_folder(asset_path)
    
    # Create ground material
    ground_material = ground.new_material("ground_material")
    
    if textures and textures['base_color'].exists():
        # Load PBR textures
        print(f"Loading ground texture from: {textures['base_color'].parent.name}")
        
        # Load base color
        base_color_image = bpy.data.images.load(str(textures['base_color']), check_existing=True)
        ground_material.set_principled_shader_value("Base Color", base_color_image)
        
        # Load normal map if available
        if textures['normal'].exists():
            normal_image = bpy.data.images.load(str(textures['normal']), check_existing=True)
            normal_image.colorspace_settings.name = 'Non-Color'
            # Add normal map to material
            nodes = ground_material.blender_obj.node_tree.nodes
            links = ground_material.blender_obj.node_tree.links
            principled_bsdf = nodes.get("Principled BSDF")
            
            if principled_bsdf:
                normal_map_node = nodes.new('ShaderNodeNormalMap')
                normal_map_node.location.x = -300
                normal_map_node.location.y = -200
                
                normal_tex_node = nodes.new('ShaderNodeTexImage')
                normal_tex_node.image = normal_image
                normal_tex_node.location.x = -500
                normal_tex_node.location.y = -200
                
                links.new(normal_tex_node.outputs["Color"], normal_map_node.inputs["Color"])
                links.new(normal_map_node.outputs["Normal"], principled_bsdf.inputs["Normal"])
        
        # Load roughness if available
        if textures['roughness'].exists():
            roughness_image = bpy.data.images.load(str(textures['roughness']), check_existing=True)
            roughness_image.colorspace_settings.name = 'Non-Color'
            # Connect roughness to material
            nodes = ground_material.blender_obj.node_tree.nodes
            links = ground_material.blender_obj.node_tree.links
            principled_bsdf = nodes.get("Principled BSDF")
            
            if principled_bsdf:
                roughness_tex_node = nodes.new('ShaderNodeTexImage')
                roughness_tex_node.image = roughness_image
                roughness_tex_node.location.x = -300
                roughness_tex_node.location.y = -400
                
                links.new(roughness_tex_node.outputs["Color"], principled_bsdf.inputs["Roughness"])
        else:
            ground_material.set_principled_shader_value("Roughness", 0.9)
        
        # Create displacement texture for modifier
        displacement_texture = None
        if textures['displacement'].exists():
            # Load displacement image and create texture
            displacement_image = bpy.data.images.load(str(textures['displacement']), check_existing=True)
            displacement_image.colorspace_settings.name = 'Non-Color'
            
            # Create texture from image
            displacement_texture = bpy.data.textures.new(name="ground_displacement", type="IMAGE")
            displacement_texture.image = displacement_image
            displacement_texture.use_nodes = True
        else:
            # Fallback to procedural texture
            displacement_texture = bproc.material.create_procedural_texture('CLOUDS')
        
        # Add displacement modifier for uneven terrain
        # This makes shadows look realistic and distorted, not perfectly straight
        try:
            ground.add_displace_modifier(
                texture=displacement_texture,
                strength=0.3,  # Moderate displacement for subtle unevenness
                subdiv_level=2,  # Medium subdivision for smooth displacement
            )
            print("Added displacement modifier to ground")
        except Exception as e:
            print(f"Warning: Could not add displacement modifier: {e}")
    else:
        # Fallback to simple material if textures not found
        print("Warning: Ground textures not found, using simple material")
        ground_material.set_principled_shader_value("Base Color", [0.4, 0.3, 0.2, 1.0])
        ground_material.set_principled_shader_value("Roughness", 0.9)
        
        # Add procedural displacement
        displacement_texture = bproc.material.create_procedural_texture('CLOUDS')
        try:
            ground.add_displace_modifier(
                texture=displacement_texture,
                strength=0.3,
                subdiv_level=2,
            )
        except Exception as e:
            print(f"Warning: Could not add displacement modifier: {e}")
    
    return ground


def main() -> None:
    """Main function - simple approach."""
    parser = argparse.ArgumentParser(description="Simple solar farm dataset generator")
    parser.add_argument('output_dir', nargs='?', default="output/solar_farm_nadir", help="Output directory")
    parser.add_argument('--num_piles_x', type=int, default=20, help="Number of piles in X direction (default: 20 for realistic scale)")
    parser.add_argument('--num_piles_y', type=int, default=15, help="Number of piles in Y direction (default: 15 for realistic scale)")
    parser.add_argument('--pile_spacing', type=float, default=3.0, help="Spacing between piles in meters (default: 3.0)")
    parser.add_argument('--render_width', type=int, default=1920, help="Render width (use 1920x1440 for 4:3 aspect ratio)")
    parser.add_argument('--render_height', type=int, default=1440, help="Render height (4:3 aspect ratio, closer to drone sensors)")
    parser.add_argument('--num_cameras', type=int, default=1, help="Number of camera poses")
    parser.add_argument('--asset_path', type=str, default="/Volumes/leo_disk/asset", help="Path to asset folder containing PBR textures")
    args = parser.parse_args()
    
    # Initialize
    bproc.init()
    
    # Set resolution
    bproc.camera.set_resolution(args.render_width, args.render_height)
    print(f"Resolution: {args.render_width}x{args.render_height}")
    
    # Create ground - LARGE ENOUGH and CENTERED AT (0, 0, 0)
    print("Creating ground with PBR textures...")
    # Ground should be large enough to cover entire pile grid
    # For 20x15 grid with 3m spacing: ~60m x 45m, use 200m x 200m for safety
    ground_size = max(args.num_piles_x, args.num_piles_y) * args.pile_spacing * 2 + 50.0
    ground = create_simple_ground(size=ground_size, asset_path=args.asset_path)
    ground.set_location([0, 0, 0])  # Explicitly center at origin
    ground.set_cp("category_id", -1)
    print(f"Ground size: {ground_size}m x {ground_size}m, centered at (0, 0, 0)")
    
    # Create piles in simple grid - CENTERED AT (0, 0, 0)
    print(f"Creating {args.num_piles_x}x{args.num_piles_y} grid of piles...")
    piles = []
    for i in range(args.num_piles_x):
        for j in range(args.num_piles_y):
            # Base position: center grid at (0, 0, 0)
            # Note: Additional position jitter (+/- 0.2m) is applied in create_simple_pile()
            x = (i - (args.num_piles_x - 1) / 2) * args.pile_spacing
            y = (j - (args.num_piles_y - 1) / 2) * args.pile_spacing
            location = np.array([x, y, 0])
            
            # Random height variation for realism
            height = np.random.uniform(2.5, 3.5)
            pile = create_simple_pile(location, radius=0.4, height=height)
            pile.set_name(f"pile_{i}_{j}")
            pile.set_cp("category_id", 0)
            piles.append(pile)
    
    print(f"Created {len(piles)} piles")
    
    # Calculate actual scene bounds for verification
    if len(piles) > 0:
        pile_locations = np.array([pile.get_location() for pile in piles])
        scene_min = pile_locations.min(axis=0)
        scene_max = pile_locations.max(axis=0)
        scene_center = pile_locations.mean(axis=0)
        scene_size = scene_max - scene_min
        max_extent = max(scene_size[0], scene_size[1])
        print(f"Scene bounds: min={scene_min}, max={scene_max}")
        print(f"Scene center: {scene_center}")
    else:
        max_extent = 20.0
    
    # Scatter debris objects as negative samples
    debris = scatter_debris(
        num_debris=np.random.randint(50, 101),  # Random 50-100
        area_size=max_extent * 1.2,  # Slightly larger than pile area
        ground_z=0.0
    )
    
    # Lighting - CRITICAL for top-down view: shadows are the main visual feature
    # Randomize Sun elevation (30-60 degrees) and azimuth (0-360 degrees)
    print("Setting up lighting...")
    light = bproc.types.Light()
    light.set_type("SUN")
    light.set_location([0, 0, 0])
    
    # Randomize Sun elevation: 30-60 degrees (not vertical!)
    sun_elevation = np.random.uniform(30, 60)
    # Randomize Sun azimuth: 0-360 degrees (full rotation)
    sun_azimuth = np.random.uniform(0, 360)
    
    # Set rotation: elevation (pitch), azimuth (yaw), roll=0
    # Negative elevation because Blender's rotation convention
    light.set_rotation_euler([
        np.radians(-sun_elevation),
        np.radians(sun_azimuth),
        0
    ])
    light.set_energy(10.0)  # Higher intensity for better visibility
    light.set_color([1.0, 0.98, 0.95])  # Slightly warm sunlight
    print(f"Sun angle: {sun_elevation:.1f}° elevation, {sun_azimuth:.1f}° azimuth (randomized)")
    
    # Setup cameras - FIXED POSITION STRATEGY for nadir view
    print("Setting up cameras...")
    
    # Calculate scene center (should be near 0, 0, 0)
    if len(piles) > 0:
        pile_locations = np.array([pile.get_location() for pile in piles])
        scene_center = pile_locations.mean(axis=0)
        scene_size = pile_locations.max(axis=0) - pile_locations.min(axis=0)
        max_extent = max(scene_size[0], scene_size[1])
        max_pile_height = max([pile.get_location()[2] + 3.5 for pile in piles])  # Max pile top
        print(f"Scene center: {scene_center}")
        print(f"Scene extent: {max_extent:.1f}m")
        print(f"Max pile height: {max_pile_height:.1f}m")
    else:
        scene_center = np.array([0, 0, 1.5])
        max_extent = 20.0
        max_pile_height = 3.5
    
    # Add multiple camera poses - USE LOOK-AT STRATEGY (not Euler angles)
    for cam_idx in range(args.num_cameras):
        # FIXED POSITION: Camera directly above scene center
        # Height: 50 meters (matching real drone 30-60m range)
        camera_height = 50.0
        
        # Position: directly above (0, 0, height)
        camera_location = np.array([0.0, 0.0, camera_height])
        
        # Target: scene center (0, 0, 0) - ground level
        target_point = np.array([0.0, 0.0, 0.0])
        
        # CRITICAL: Use rotation_from_forward_vec instead of Euler angles
        # Forward vector: from camera to target (pointing downward)
        forward_vec = target_point - camera_location  # [0, 0, -50]
        forward_vec = forward_vec / np.linalg.norm(forward_vec)  # Normalize to [0, 0, -1]
        
        # Compute rotation matrix using look-at logic
        # Up axis: Y (for nadir view, Y is the "up" direction in world space)
        rotation_matrix = bproc.camera.rotation_from_forward_vec(
            forward_vec,
            up_axis='Y'  # Y-axis is up in world space
        )
        
        # Build transformation matrix
        cam2world = bproc.math.build_transformation_mat(
            camera_location,
            rotation_matrix
        )
        bproc.camera.add_camera_pose(cam2world)
        
        # Set FOV and Clipping - CRITICAL for high altitude nadir view
        # FOV: 80° (wide angle like drones) = 80 * π/180 ≈ 1.396 radians
        # Clipping: 0.1-500m (must be large enough to see ground from 50m height)
        fov_radians = np.radians(80.0)  # 80 degrees in radians
        bproc.camera.set_intrinsics_from_blender_params(
            lens_unit='FOV',
            lens=fov_radians,  # 80° FOV (wide angle like drones)
            image_width=args.render_width,
            image_height=args.render_height,
            clip_start=0.1,
            clip_end=500.0
        )
        
        if cam_idx == 0:
            print(f"Camera {cam_idx}:")
            print(f"  Location: {camera_location}")
            print(f"  Target: {target_point}")
            print(f"  Forward vector: {forward_vec}")
            print(f"  Height: {camera_height}m (above ground)")
            print(f"  Rotation: Look-at (not Euler angles)")
            print(f"  FOV: ~80° (wide angle)")
            print(f"  Clipping: 0.1m - 500m")
            # Assert camera is above piles
            assert camera_height > max_pile_height, f"Camera height {camera_height}m must be > max pile height {max_pile_height}m"
    
    # Enable segmentation
    bproc.renderer.enable_segmentation_output(
        map_by=["category_id", "instance", "name"],
        default_values={"category_id": -1}
    )
    
    # Render
    print("Rendering...")
    data = bproc.renderer.render()
    
    # Debug output
    print(f"Rendered {len(data.get('colors', []))} frames")
    if 'instance_segmaps' in data and len(data['instance_segmaps']) > 0:
        segmap = data['instance_segmaps'][0]
        unique_ids = np.unique(segmap)
        print(f"Segmentation IDs: {unique_ids}")
    
    # Save
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    bproc.writer.write_hdf5(str(output_dir), data)
    
    # Save images
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    for i, color in enumerate(data.get('colors', [])):
        img_path = images_dir / f"image_{i:06d}.jpg"
        # Convert to uint8 and BGR
        img_uint8 = np.clip(color, 0, 255).astype(np.uint8)
        img_bgr = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(img_path), img_bgr)
    
    # Generate YOLO annotations
    print("Generating YOLO annotations...")
    if 'instance_segmaps' in data and 'instance_attribute_maps' in data:
        write_yolo_annotations(
            str(output_dir),
            data['instance_segmaps'],
            data['instance_attribute_maps'],
            class_id=0,
            image_prefix="image_"
        )
    
    print(f"✅ Dataset saved to: {output_dir}")
    print(f"   Images: {images_dir}")
    print(f"   Labels: {output_dir}/labels")
    print(f"   HDF5: {output_dir}/0.hdf5")


if __name__ == "__main__":
    main()

