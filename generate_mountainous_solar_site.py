import blenderproc as bproc
"""
Mountainous Solar Construction Site Dataset Generator
基于《光伏板桩特征调研报告》的高保真数据集生成器

This script creates a photorealistic mountainous solar construction site with:
- High-fidelity pile assets (PHC, Spiral Steel, Cast-in-place)
- Constraint-based layout following GB 50797-2012
- Environmental storytelling (track marks, debris, geological presets)
- Terraced terrain with steps
- Mixed textures (red soil + dry grass)
- Bulldozed/scraped areas under pile rows
- Tire track normal maps
- Road gaps between rows
- Distractor objects (white material bags, yellow machinery blocks)
- Nadir camera at 100m altitude, 500+ piles visible
"""

import argparse
import numpy as np
import os
import cv2
import random
import glob
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Literal
import bpy
import mathutils
from blenderproc.python.utility.Utility import Utility

# Import new modules
try:
    from pile_factory import create_pile_variant
    from pile_layout_engine import layout_piles_with_constraints
    from environmental_storytelling import (
        create_track_marks,
        create_construction_debris,
        configure_geological_preset,
        add_vegetation_traces
    )
    ADVANCED_FEATURES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Advanced features not available: {e}")
    print("  Falling back to basic pile generation")
    ADVANCED_FEATURES_AVAILABLE = False


def create_terraced_terrain(
    size: float = 200.0,
    num_terraces: int = 8,
    terrace_height: float = 2.0,
    asset_path: Optional[str] = None,
    texture_selection: Optional[Dict[str, Dict[str, Path]]] = None
) -> bproc.types.MeshObject:
    """
    Create a large terraced terrain mesh with step-like levels.
    
    :param size: Size of the terrain (square)
    :param num_terraces: Number of terrace levels
    :param terrace_height: Height difference between terraces
    :param asset_path: Path to texture assets
    :return: Ground mesh object
    """
    print(f"Creating terraced terrain: {size}m x {size}m, {num_terraces} terraces")
    
    # Create large subdivided plane for smooth displacement
    ground = bproc.object.create_primitive("PLANE", scale=[size/2, size/2, 1])
    ground.set_location([0, 0, 0])
    
    # Add UV mapping
    ground.add_uv_mapping("smart")
    
    # Subdivide for smooth displacement
    try:
        bpy.context.view_layer.objects.active = ground.blender_obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.subdivide(number_cuts=20)  # High subdivision for smooth terraces
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception as e:
        print(f"Warning: Could not subdivide mesh: {e}")
    
    # Create displacement texture for terraces
    displacement_texture = bproc.material.create_procedural_texture('CLOUDS')
    
    # Apply mixed textures
    ground_material = ground.new_material("terrain_material")
    
    # Load textures if available (use provided selection or load all)
    if texture_selection is not None:
        textures = texture_selection
    else:
        textures = load_terrain_textures(asset_path) if asset_path else None
    
    # Get material nodes for texture mixing
    nodes = ground_material.blender_obj.node_tree.nodes
    links = ground_material.blender_obj.node_tree.links
    principled_bsdf = Utility.get_the_one_node_with_type(nodes, "BsdfPrincipled")
    
    if textures and (textures.get('grass') or textures.get('ground')):
        # Create texture coordinate and mapping nodes
        tex_coord = nodes.new(type='ShaderNodeTexCoord')
        mapping = nodes.new(type='ShaderNodeMapping')
        mapping.inputs['Scale'].default_value = (5.0, 5.0, 1.0)  # Scale textures
        links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
        
        # Create noise texture for mixing
        noise_tex = nodes.new(type='ShaderNodeTexNoise')
        noise_tex.inputs['Scale'].default_value = 2.0
        noise_tex.inputs['Detail'].default_value = 5.0
        noise_tex.location = (-600, 0)
        noise_coord = nodes.new(type='ShaderNodeTexCoord')
        links.new(noise_coord.outputs['Generated'], noise_tex.inputs['Vector'])
        
        texture_nodes = []
        
        # Load ground texture(s)
        if textures.get('ground'):
            ground_set = textures['ground']
            if ground_set.get('color'):
                ground_img = bpy.data.images.load(str(ground_set['color']), check_existing=True)
                ground_tex = nodes.new(type='ShaderNodeTexImage')
                ground_tex.image = ground_img
                ground_tex.location = (-400, 100)
                links.new(mapping.outputs['Vector'], ground_tex.inputs['Vector'])
                texture_nodes.append(('ground', ground_tex))
                
                # Add roughness if available
                if ground_set.get('roughness'):
                    roughness_img = bpy.data.images.load(str(ground_set['roughness']), check_existing=True)
                    roughness_tex = nodes.new(type='ShaderNodeTexImage')
                    roughness_tex.image = roughness_img
                    roughness_tex.location = (-400, -100)
                    links.new(mapping.outputs['Vector'], roughness_tex.inputs['Vector'])
                    links.new(roughness_tex.outputs['Color'], principled_bsdf.inputs['Roughness'])
        
        # Load additional ground textures for variety
        if textures.get('ground_1'):
            ground_set = textures['ground_1']
            if ground_set.get('color'):
                ground_img = bpy.data.images.load(str(ground_set['color']), check_existing=True)
                ground_tex = nodes.new(type='ShaderNodeTexImage')
                ground_tex.image = ground_img
                ground_tex.location = (-400, -300)
                links.new(mapping.outputs['Vector'], ground_tex.inputs['Vector'])
                texture_nodes.append(('ground_1', ground_tex))
        
        # Load grass texture
        if textures.get('grass'):
            grass_set = textures['grass']
            if grass_set.get('color'):
                grass_img = bpy.data.images.load(str(grass_set['color']), check_existing=True)
                grass_tex = nodes.new(type='ShaderNodeTexImage')
                grass_tex.image = grass_img
                grass_tex.location = (-400, -500)
                links.new(mapping.outputs['Vector'], grass_tex.inputs['Vector'])
                texture_nodes.append(('grass', grass_tex))
        
        # Mix textures using noise
        if len(texture_nodes) >= 2:
            # Mix ground and grass
            mix_node = nodes.new(type='ShaderNodeMixRGB')
            mix_node.blend_type = 'MIX'
            mix_node.inputs['Fac'].default_value = 0.4  # 40% grass, 60% ground
            mix_node.location = (-200, -400)
            links.new(texture_nodes[0][1].outputs['Color'], mix_node.inputs['Color1'])
            links.new(texture_nodes[1][1].outputs['Color'], mix_node.inputs['Color2'])
            links.new(noise_tex.outputs['Fac'], mix_node.inputs['Fac'])
            
            # If we have multiple ground textures, mix them too
            if len(texture_nodes) >= 3:
                mix_ground = nodes.new(type='ShaderNodeMixRGB')
                mix_ground.blend_type = 'MIX'
                mix_ground.inputs['Fac'].default_value = 0.5
                mix_ground.location = (-200, -200)
                links.new(texture_nodes[0][1].outputs['Color'], mix_ground.inputs['Color1'])
                links.new(texture_nodes[2][1].outputs['Color'], mix_ground.inputs['Color2'])
                
                # Final mix
                final_mix = nodes.new(type='ShaderNodeMixRGB')
                final_mix.blend_type = 'OVERLAY'
                final_mix.inputs['Fac'].default_value = 0.3
                final_mix.location = (0, -300)
                links.new(mix_node.outputs['Color'], final_mix.inputs['Color1'])
                links.new(mix_ground.outputs['Color'], final_mix.inputs['Color2'])
                links.new(final_mix.outputs['Color'], principled_bsdf.inputs['Base Color'])
            else:
                links.new(mix_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
        elif len(texture_nodes) == 1:
            # Only one texture, use it directly
            links.new(texture_nodes[0][1].outputs['Color'], principled_bsdf.inputs['Base Color'])
        
        # Add normal map for tire tracks if available
        if textures.get('tire_tracks') and textures['tire_tracks'].get('normal'):
            tire_normal_path = str(textures['tire_tracks']['normal'])
            bproc.material.add_normal(
                nodes, links, tire_normal_path, principled_bsdf, invert_y_channel=True
            )
        
        # Add normal map from ground texture if available
        if textures.get('ground') and textures['ground'].get('normal'):
            ground_normal_path = str(textures['ground']['normal'])
            bproc.material.add_normal(
                nodes, links, ground_normal_path, principled_bsdf, invert_y_channel=True
            )
        
        # Set roughness if not set by texture
        if not (textures.get('ground') and textures['ground'].get('roughness')):
            ground_material.set_principled_shader_value("Roughness", 0.9)
    else:
        # Fallback: Procedural mixed colors (grass + multiple soil colors)
        # Create noise-based mixing for procedural textures
        noise_tex = nodes.new(type='ShaderNodeTexNoise')
        noise_tex.inputs['Scale'].default_value = 3.0
        noise_tex.inputs['Detail'].default_value = 5.0
        noise_tex.location = (-400, 0)
        noise_coord = nodes.new(type='ShaderNodeTexCoord')
        links.new(noise_coord.outputs['Generated'], noise_tex.inputs['Vector'])
        
        # Multiple soil colors
        red_soil_color = nodes.new(type='ShaderNodeRGB')
        red_soil_color.outputs['Color'].default_value = (0.6, 0.35, 0.25, 1.0)
        red_soil_color.location = (-200, 200)
        
        dark_soil_color = nodes.new(type='ShaderNodeRGB')
        dark_soil_color.outputs['Color'].default_value = (0.4, 0.25, 0.15, 1.0)
        dark_soil_color.location = (-200, 0)
        
        light_soil_color = nodes.new(type='ShaderNodeRGB')
        light_soil_color.outputs['Color'].default_value = (0.7, 0.5, 0.4, 1.0)
        light_soil_color.location = (-200, -200)
        
        grass_color = nodes.new(type='ShaderNodeRGB')
        grass_color.outputs['Color'].default_value = (0.5, 0.45, 0.3, 1.0)
        grass_color.location = (-200, -400)
        
        # Mix soil colors first
        mix_soil = nodes.new(type='ShaderNodeMixRGB')
        mix_soil.blend_type = 'MIX'
        mix_soil.inputs['Fac'].default_value = 0.5
        mix_soil.location = (0, 0)
        links.new(red_soil_color.outputs['Color'], mix_soil.inputs['Color1'])
        links.new(dark_soil_color.outputs['Color'], mix_soil.inputs['Color2'])
        links.new(noise_tex.outputs['Fac'], mix_soil.inputs['Fac'])
        
        # Mix with light soil
        mix_soil2 = nodes.new(type='ShaderNodeMixRGB')
        mix_soil2.blend_type = 'MIX'
        mix_soil2.inputs['Fac'].default_value = 0.3
        mix_soil2.location = (200, -100)
        links.new(mix_soil.outputs['Color'], mix_soil2.inputs['Color1'])
        links.new(light_soil_color.outputs['Color'], mix_soil2.inputs['Color2'])
        
        # Final mix with grass
        final_mix = nodes.new(type='ShaderNodeMixRGB')
        final_mix.blend_type = 'MIX'
        final_mix.inputs['Fac'].default_value = 0.4  # 40% grass
        final_mix.location = (400, -200)
        links.new(mix_soil2.outputs['Color'], final_mix.inputs['Color1'])
        links.new(grass_color.outputs['Color'], final_mix.inputs['Color2'])
        links.new(noise_tex.outputs['Fac'], final_mix.inputs['Fac'])
        
        links.new(final_mix.outputs['Color'], principled_bsdf.inputs['Base Color'])
        ground_material.set_principled_shader_value("Roughness", 0.9)
    
    # Add displacement modifier for terraces
    try:
        ground.add_displace_modifier(
            texture=displacement_texture,
            strength=terrace_height * 0.8,  # Strong displacement for visible steps
            subdiv_level=3,  # High subdivision for smooth steps
        )
        print(f"Added displacement modifier: {terrace_height * 0.8} strength")
    except Exception as e:
        print(f"Warning: Could not add displacement modifier: {e}")
    
    ground.set_cp("category_id", -1)
    return ground


def load_texture_set(folder_path: Path) -> Optional[Dict[str, Path]]:
    """
    Load a complete PBR texture set from a folder.
    
    :param folder_path: Path to texture folder
    :return: Dictionary with texture paths (color, normal, roughness, displacement, ao) or None
    """
    folder_name = folder_path.name
    textures = {}
    
    # Base color
    color_file = folder_path / f"{folder_name}_Color.jpg"
    if color_file.exists():
        textures['color'] = color_file
    
    # Normal map (OpenGL format)
    normal_file = folder_path / f"{folder_name}_NormalGL.jpg"
    if normal_file.exists():
        textures['normal'] = normal_file
    
    # Roughness
    roughness_file = folder_path / f"{folder_name}_Roughness.jpg"
    if roughness_file.exists():
        textures['roughness'] = roughness_file
    
    # Displacement
    displacement_file = folder_path / f"{folder_name}_Displacement.jpg"
    if displacement_file.exists():
        textures['displacement'] = displacement_file
    
    # Ambient Occlusion
    ao_file = folder_path / f"{folder_name}_AmbientOcclusion.jpg"
    if ao_file.exists():
        textures['ao'] = ao_file
    
    return textures if textures else None


def load_all_terrain_textures(asset_path: str) -> Optional[Dict[str, List[Dict[str, Path]]]]:
    """
    Load ALL available terrain textures for randomization.
    
    :param asset_path: Base path to asset folder
    :return: Dictionary with lists of texture sets for each type
    """
    base_path = Path(asset_path)
    if not base_path.exists():
        return None
    
    all_textures = {
        'grass': [],
        'ground': [],
        'tire_tracks': [],
        'pathway': []
    }
    
    # Load all grass textures
    grass_folders = sorted(base_path.glob("*Grass*_4K-JPG"))
    for folder in grass_folders:
        grass_set = load_texture_set(folder)
        if grass_set:
            all_textures['grass'].append(grass_set)
    
    # Load all ground textures
    ground_folders = sorted(base_path.glob("*Ground*_4K-JPG"))
    for folder in ground_folders:
        ground_set = load_texture_set(folder)
        if ground_set:
            all_textures['ground'].append(ground_set)
    
    # Load all tire track textures
    tire_folders = sorted(base_path.glob("*Tire*_4K-JPG"))
    for folder in tire_folders:
        tire_set = load_texture_set(folder)
        if tire_set:
            all_textures['tire_tracks'].append(tire_set)
    
    # Load all pathway textures
    pathway_folders = sorted(base_path.glob("*Pathway*_4K-JPG"))
    for folder in pathway_folders:
        pathway_set = load_texture_set(folder)
        if pathway_set:
            all_textures['pathway'].append(pathway_set)
    
    return all_textures


def load_terrain_textures(asset_path: str) -> Optional[Dict[str, Dict[str, Path]]]:
    """
    Load terrain textures from asset folder.
    Automatically detects available textures by name patterns.
    
    :param asset_path: Base path to asset folder
    :return: Dictionary of texture sets or None
    """
    base_path = Path(asset_path)
    if not base_path.exists():
        return None
    
    textures = {}
    
    # Search for grass textures (Grass037, etc.)
    grass_folders = sorted(base_path.glob("*Grass*_4K-JPG"))
    if grass_folders:
        grass_set = load_texture_set(grass_folders[0])
        if grass_set:
            textures['grass'] = grass_set
            print(f"  Found grass texture: {grass_folders[0].name}")
    
    # Search for ground textures (Ground017, Ground029, etc.)
    ground_folders = sorted(base_path.glob("*Ground*_4K-JPG"))
    if ground_folders:
        # Use multiple ground textures for variety
        for i, folder in enumerate(ground_folders[:3]):  # Use first 3 ground textures
            ground_set = load_texture_set(folder)
            if ground_set:
                key = f'ground_{i+1}' if i > 0 else 'ground'
                textures[key] = ground_set
                print(f"  Found ground texture {i+1}: {folder.name}")
    
    # Search for tire tracks (TireTracks001)
    tire_folders = sorted(base_path.glob("*Tire*_4K-JPG"))
    if tire_folders:
        tire_set = load_texture_set(tire_folders[0])
        if tire_set:
            textures['tire_tracks'] = tire_set
            print(f"  Found tire tracks texture: {tire_folders[0].name}")
    
    # Search for pathway/road textures (Pathway002)
    pathway_folders = sorted(base_path.glob("*Pathway*_4K-JPG"))
    if pathway_folders:
        pathway_set = load_texture_set(pathway_folders[0])
        if pathway_set:
            textures['pathway'] = pathway_set
            print(f"  Found pathway texture: {pathway_folders[0].name}")
    
    return textures if textures else None


def select_random_textures(all_textures: Dict[str, List[Dict[str, Path]]]) -> Dict[str, Dict[str, Path]]:
    """
    Randomly select textures from available options for diversity.
    
    :param all_textures: Dictionary with lists of texture sets
    :return: Dictionary with selected texture sets
    """
    selected = {}
    
    # Randomly select grass texture
    if all_textures.get('grass') and len(all_textures['grass']) > 0:
        selected['grass'] = np.random.choice(all_textures['grass'])
    
    # Randomly select 1-3 ground textures
    if all_textures.get('ground') and len(all_textures['ground']) > 0:
        num_ground = np.random.randint(1, min(4, len(all_textures['ground']) + 1))
        selected_ground = np.random.choice(all_textures['ground'], size=num_ground, replace=False)
        for i, ground_set in enumerate(selected_ground):
            key = 'ground' if i == 0 else f'ground_{i+1}'
            selected[key] = ground_set
    
    # Randomly select tire tracks (optional)
    if all_textures.get('tire_tracks') and len(all_textures['tire_tracks']) > 0:
        if np.random.random() > 0.3:  # 70% chance to include tire tracks
            selected['tire_tracks'] = np.random.choice(all_textures['tire_tracks'])
    
    # Randomly select pathway (optional)
    if all_textures.get('pathway') and len(all_textures['pathway']) > 0:
        if np.random.random() > 0.5:  # 50% chance to include pathway
            selected['pathway'] = np.random.choice(all_textures['pathway'])
    
    return selected


# Cache for concrete texture to avoid reloading
_concrete_texture_cache = None

def load_concrete_texture(asset_path: str, print_found: bool = False) -> Optional[Dict[str, Path]]:
    """
    Load concrete texture for piles. Uses caching to avoid reloading.
    
    :param asset_path: Base path to asset folder
    :param print_found: Whether to print when texture is found (only first time)
    :return: Dictionary with concrete texture paths or None
    """
    global _concrete_texture_cache
    
    # Return cached texture if available
    if _concrete_texture_cache is not None:
        return _concrete_texture_cache
    
    base_path = Path(asset_path)
    if not base_path.exists():
        return None
    
    # Search for concrete textures (Concrete047A, etc.)
    concrete_folders = sorted(base_path.glob("*Concrete*_4K-JPG"))
    if concrete_folders:
        concrete_set = load_texture_set(concrete_folders[0])
        if concrete_set:
            if print_found:
                print(f"  Found concrete texture: {concrete_folders[0].name}")
            _concrete_texture_cache = concrete_set
            return concrete_set
    
    return None


def get_terrain_height(x: float, y: float, terrain: bproc.types.MeshObject) -> float:
    """
    Get terrain height at given x, y coordinates using ray casting.
    This accounts for displacement modifiers and actual mesh geometry.
    
    :param x: X coordinate
    :param y: Y coordinate
    :param terrain: Terrain mesh object
    :return: Z height at (x, y)
    """
    # Use ray casting from above to get actual terrain height
    # Cast ray from high above (z=100) straight down (direction = [0, 0, -1])
    ray_origin = np.array([x, y, 100.0])
    ray_direction = np.array([0.0, 0.0, -1.0])
    
    # Cast ray to find terrain intersection
    hit, location, normal, index, hit_object, matrix = bproc.object.scene_ray_cast(
        origin=ray_origin,
        direction=ray_direction,
        max_distance=200.0
    )
    
    if hit and hit_object is not None:
        # Check if we hit the terrain object
        if hit_object.get_name() == terrain.get_name():
            return location[2]
    
    # Fallback: Simple terrace model if ray casting fails
    distance = np.sqrt(x**2 + y**2)
    terrace_level = int(distance / 25.0)
    variation = 0.3 * np.sin(distance * 0.1) * np.cos(x * 0.05) * np.sin(y * 0.05)
    base_height = terrace_level * 2.0
    return base_height + variation


def create_pile_on_terrain(
    location: np.ndarray,
    terrain: bproc.types.MeshObject,
    radius: float = 0.4,
    height: float = 3.0,
    asset_path: Optional[str] = None
) -> bproc.types.MeshObject:
    """
    Create a pile positioned on terrain, adjusting Z-height to match ground.
    
    :param location: 2D location [x, y] (Z will be calculated from terrain)
    :param terrain: Terrain mesh object
    :param radius: Pile radius
    :param height: Pile height
    :return: Pile mesh object
    """
    # Position jitter
    jitter_x = np.random.uniform(-0.2, 0.2)
    jitter_y = np.random.uniform(-0.2, 0.2)
    
    # Calculate final position after jitter
    final_x = location[0] + jitter_x
    final_y = location[1] + jitter_y
    
    # Get terrain height at jittered location (after jitter for accurate placement)
    terrain_z = get_terrain_height(final_x, final_y, terrain)
    
    # Create pile
    # CYLINDER with depth=height: the cylinder extends from -height/2 to +height/2 relative to its center
    # So to place bottom at terrain_z, center should be at terrain_z + height/2
    pile = bproc.object.create_primitive("CYLINDER", radius=radius, depth=height)
    pile.set_location([
        final_x,
        final_y,
        terrain_z + height/2  # Center at terrain_z + height/2 so bottom is at terrain_z
    ])
    
    # Rotation jitter
    tilt_x = np.random.uniform(0, np.radians(5))
    tilt_y = np.random.uniform(0, np.radians(5))
    tilt_z = np.random.uniform(0, 2 * np.pi)
    pile.set_rotation_euler([tilt_x, tilt_y, tilt_z])
    
    pile.blender_obj.hide_set(False)
    pile.blender_obj.hide_render = False
    
    # Add UV mapping for texture
    pile.add_uv_mapping("smart")
    
    # Pile material with concrete texture
    pile_material = pile.new_material("pile_material")
    
    # Try to load concrete texture (only print on first load)
    concrete_texture = load_concrete_texture(asset_path, print_found=False) if asset_path else None
    
    if concrete_texture and concrete_texture.get('color'):
        # Use concrete texture
        nodes = pile_material.blender_obj.node_tree.nodes
        links = pile_material.blender_obj.node_tree.links
        principled_bsdf = Utility.get_the_one_node_with_type(nodes, "BsdfPrincipled")
        
        # Create texture coordinate and mapping
        tex_coord = nodes.new(type='ShaderNodeTexCoord')
        mapping = nodes.new(type='ShaderNodeMapping')
        mapping.inputs['Scale'].default_value = (2.0, 2.0, 2.0)  # Scale for cylinder
        links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
        
        # Base color
        concrete_color = bpy.data.images.load(str(concrete_texture['color']), check_existing=True)
        color_tex = nodes.new(type='ShaderNodeTexImage')
        color_tex.image = concrete_color
        color_tex.location = (-400, 0)
        links.new(mapping.outputs['Vector'], color_tex.inputs['Vector'])
        links.new(color_tex.outputs['Color'], principled_bsdf.inputs['Base Color'])
        
        # Normal map
        if concrete_texture.get('normal'):
            concrete_normal_path = str(concrete_texture['normal'])
            bproc.material.add_normal(
                nodes, links, concrete_normal_path, principled_bsdf, invert_y_channel=True
            )
        
        # Roughness
        if concrete_texture.get('roughness'):
            concrete_roughness = bpy.data.images.load(str(concrete_texture['roughness']), check_existing=True)
            roughness_tex = nodes.new(type='ShaderNodeTexImage')
            roughness_tex.image = concrete_roughness
            roughness_tex.location = (-400, -200)
            links.new(mapping.outputs['Vector'], roughness_tex.inputs['Vector'])
            links.new(roughness_tex.outputs['Color'], principled_bsdf.inputs['Roughness'])
        else:
            pile_material.set_principled_shader_value("Roughness", 0.7)  # Concrete is rough
        
        pile_material.set_principled_shader_value("Metallic", 0.0)  # Concrete is not metallic
    else:
        # Fallback: Simple gray material
        pile_material.set_principled_shader_value("Base Color", [0.5, 0.5, 0.55, 1.0])
        pile_material.set_principled_shader_value("Metallic", 0.0)
        pile_material.set_principled_shader_value("Roughness", 0.7)
    
    # Create base
    base_radius = 0.8
    base_height = 0.05
    base = bproc.object.create_primitive("CYLINDER", radius=base_radius, depth=base_height)
    # Base should sit directly on terrain surface
    # CYLINDER center is at base_height/2 from bottom, so to place bottom at terrain_z:
    base.set_location([
        final_x,
        final_y,
        terrain_z + base_height / 2  # Bottom at terrain_z, no offset needed
    ])
    base.set_rotation_euler([tilt_x, tilt_y, tilt_z])
    
    scale_x = np.random.uniform(0.85, 1.15)
    scale_y = np.random.uniform(0.85, 1.15)
    base.set_scale([scale_x, scale_y, 1.0])
    
    base.blender_obj.hide_set(False)
    base.blender_obj.hide_render = False
    
    base_material = base.new_material("base_material")
    base_color = np.random.uniform([0.75, 0.75, 0.78], [0.9, 0.9, 0.92])
    base_material.set_principled_shader_value("Base Color", list(base_color) + [1.0])
    base_material.set_principled_shader_value("Metallic", 0.0)
    base_material.set_principled_shader_value("Roughness", 0.95)
    
    base.set_cp("category_id", 0)
    pile.set_cp("category_id", 0)
    
    return pile


def create_curved_pile_rows(
    terrain: bproc.types.MeshObject,
    num_rows: int = 15,
    piles_per_row: int = 35,
    row_spacing: float = 3.5,
    area_size: float = 200.0,
    road_width: float = 8.0,
    asset_path: Optional[str] = None
) -> List[bproc.types.MeshObject]:
    """
    Create curved pile rows following terrain contours, with gaps for roads.
    
    :param terrain: Terrain mesh object
    :param num_rows: Number of pile rows
    :param piles_per_row: Number of piles per row
    :param row_spacing: Spacing between rows
    :param area_size: Size of the area
    :param road_width: Width of road gaps
    :return: List of pile objects
    """
    print(f"Creating {num_rows} curved rows with {piles_per_row} piles each...")
    
    piles = []
    total_piles = 0
    
    for row_idx in range(num_rows):
        # Create curved path for this row
        # Use sine wave or bezier curve for natural terrain following
        row_y = (row_idx - num_rows/2) * row_spacing
        
        # Check if this row should be a road gap
        road_gap_interval = 5  # Every 5 rows is a road
        if row_idx % road_gap_interval == road_gap_interval - 1:
            print(f"  Row {row_idx}: Road gap (skipping)")
            continue
        
        # Create curved path (sine wave for natural look)
        amplitude = area_size * 0.1 * np.sin(row_idx * 0.3)  # Varying amplitude
        frequency = 0.02
        
        for pile_idx in range(piles_per_row):
            # X position along row
            x_base = (pile_idx - piles_per_row/2) * 3.0  # 3m spacing along row
            
            # Add curve to X position
            x_offset = amplitude * np.sin(frequency * x_base)
            x = x_base + x_offset
            
            # Y position with slight curve
            y_curve = 0.5 * np.sin(frequency * x_base)
            y = row_y + y_curve
            
            # Skip if outside area
            if abs(x) > area_size/2 or abs(y) > area_size/2:
                continue
            
            # Create pile on terrain
            location = np.array([x, y])
            pile = create_pile_on_terrain(location, terrain, radius=0.4, height=3.0, asset_path=asset_path)
            pile.set_name(f"pile_row_{row_idx}_col_{pile_idx}")
            piles.append(pile)
            total_piles += 1
    
    print(f"Created {total_piles} piles in curved rows")
    return piles


def create_pile_cluster(
    terrain: bproc.types.MeshObject,
    center_x: float,
    center_y: float,
    row_angle: float,
    min_piles: int = 50,
    max_piles: int = 100,
    cluster_size: float = 30.0,
    pile_spacing: float = 3.0,
    asset_path: Optional[str] = None
) -> List[bproc.types.MeshObject]:
    """
    Create a cluster of piles with a specific row direction.
    
    :param terrain: Terrain mesh object
    :param center_x: X coordinate of cluster center
    :param center_y: Y coordinate of cluster center
    :param row_angle: Angle of row direction in radians (0 = along X axis)
    :param min_piles: Minimum number of piles in cluster (default: 50)
    :param max_piles: Maximum number of piles in cluster (default: 100)
    :param cluster_size: Size of cluster area in meters
    :param pile_spacing: Spacing between piles
    :param asset_path: Path to asset folder for textures
    :return: List of pile objects
    """
    num_piles = np.random.randint(min_piles, max_piles + 1)
    
    # Calculate rows and columns based on cluster size
    # Approximate: sqrt(num_piles) rows and columns
    approx_rows = int(np.sqrt(num_piles)) + 1
    approx_cols = int(np.sqrt(num_piles)) + 1
    
    piles = []
    
    # Rotation matrix for row direction
    cos_a = np.cos(row_angle)
    sin_a = np.sin(row_angle)
    rotation_matrix = np.array([
        [cos_a, -sin_a],
        [sin_a, cos_a]
    ])
    
    for row_idx in range(approx_rows):
        for col_idx in range(approx_cols):
            if len(piles) >= num_piles:
                break
            
            # Position in local coordinate system (along row direction)
            local_x = (col_idx - approx_cols/2) * pile_spacing
            local_y = (row_idx - approx_rows/2) * pile_spacing
            
            # Rotate to row direction
            rotated = rotation_matrix @ np.array([local_x, local_y])
            
            # World position
            world_x = center_x + rotated[0]
            world_y = center_y + rotated[1]
            
            # Check if within cluster bounds (circular or rectangular)
            distance_from_center = np.sqrt(rotated[0]**2 + rotated[1]**2)
            if distance_from_center > cluster_size / 2:
                continue
            
            # Create pile on terrain
            location = np.array([world_x, world_y])
            pile = create_pile_on_terrain(location, terrain, radius=0.4, height=3.0, asset_path=asset_path)
            pile.set_name(f"pile_cluster_row{row_idx}_col{col_idx}")
            piles.append(pile)
    
    return piles


def create_pile_clusters(
    terrain: bproc.types.MeshObject,
    num_clusters: int = 3,
    min_piles_per_cluster: int = 50,
    max_piles_per_cluster: int = 100,
    terrain_size: float = 200.0,
    cluster_size: float = 30.0,
    asset_path: Optional[str] = None
) -> List[bproc.types.MeshObject]:
    """
    Create multiple pile clusters with random positions and row directions.
    
    :param terrain: Terrain mesh object
    :param num_clusters: Number of clusters to create (1-5)
    :param min_piles_per_cluster: Minimum piles per cluster
    :param max_piles_per_cluster: Maximum piles per cluster
    :param terrain_size: Size of terrain area
    :param cluster_size: Size of each cluster
    :param asset_path: Path to asset folder for textures
    :return: List of all pile objects from all clusters
    """
    print(f"Creating {num_clusters} pile clusters...")
    
    all_piles = []
    min_distance = cluster_size * 1.5  # Minimum distance between cluster centers
    
    cluster_centers = []
    
    for cluster_idx in range(num_clusters):
        # Find a valid position for this cluster (avoid overlap)
        max_attempts = 50
        for attempt in range(max_attempts):
            center_x = np.random.uniform(-terrain_size/2 + cluster_size, terrain_size/2 - cluster_size)
            center_y = np.random.uniform(-terrain_size/2 + cluster_size, terrain_size/2 - cluster_size)
            
            # Check distance from existing clusters
            too_close = False
            for existing_center in cluster_centers:
                distance = np.sqrt((center_x - existing_center[0])**2 + (center_y - existing_center[1])**2)
                if distance < min_distance:
                    too_close = True
                    break
            
            if not too_close:
                break
        
        if too_close:
            print(f"  Warning: Could not find valid position for cluster {cluster_idx+1}, skipping")
            continue
        
        cluster_centers.append((center_x, center_y))
        
        # Random row direction (0 to 2*pi)
        row_angle = np.random.uniform(0, 2 * np.pi)
        row_angle_deg = np.degrees(row_angle)
        
        # Create cluster
        cluster_piles = create_pile_cluster(
            terrain=terrain,
            center_x=center_x,
            center_y=center_y,
            row_angle=row_angle,
            min_piles=min_piles_per_cluster,
            max_piles=max_piles_per_cluster,
            cluster_size=cluster_size,
            pile_spacing=3.0,
            asset_path=asset_path
        )
        
        all_piles.extend(cluster_piles)
        print(f"  Cluster {cluster_idx+1}: {len(cluster_piles)} piles at ({center_x:.1f}, {center_y:.1f}), row angle: {row_angle_deg:.1f}°")
    
    print(f"Created {len(all_piles)} total piles in {len(cluster_centers)} clusters")
    return all_piles


def create_material_bags(
    num_bags: int = 30,
    area_size: float = 200.0,
    terrain: Optional[bproc.types.MeshObject] = None
) -> List[bproc.types.MeshObject]:
    """
    Create white rectangular packages (material bags) as negative samples.
    
    :param num_bags: Number of material bags
    :param area_size: Size of the area
    :param terrain: Optional terrain for height matching
    :return: List of bag objects
    """
    print(f"Creating {num_bags} white material bags...")
    bags = []
    
    for i in range(num_bags):
        # Random position
        x = np.random.uniform(-area_size/2, area_size/2)
        y = np.random.uniform(-area_size/2, area_size/2)
        
        # Get terrain height if available
        if terrain:
            z = get_terrain_height(x, y, terrain)
        else:
            z = 0.0
        
        # Create rectangular bag (flattened box)
        length = np.random.uniform(0.8, 1.5)
        width = np.random.uniform(0.6, 1.2)
        height = np.random.uniform(0.3, 0.6)
        
        bag = bproc.object.create_primitive("CUBE", size=1.0)
        bag.set_scale([length/2, width/2, height/2])
        # Place bag ON the terrain surface (not floating)
        bag.set_location([x, y, z + height/2])
        
        # Random rotation
        bag.set_rotation_euler([
            np.random.uniform(0, 2 * np.pi),
            np.random.uniform(0, 2 * np.pi),
            np.random.uniform(0, 2 * np.pi)
        ])
        
        bag.blender_obj.hide_set(False)
        bag.blender_obj.hide_render = False
        
        # White material
        bag_material = bag.new_material(f"bag_material_{i}")
        white_color = np.random.uniform([0.9, 0.9, 0.9], [1.0, 1.0, 1.0])
        bag_material.set_principled_shader_value("Base Color", list(white_color) + [1.0])
        bag_material.set_principled_shader_value("Metallic", 0.0)
        bag_material.set_principled_shader_value("Roughness", 0.7)
        
        # Negative sample - NOT a pile
        bag.set_cp("category_id", -1)
        bags.append(bag)
    
    print(f"Created {len(bags)} material bags")
    return bags


def create_machinery_blocks(
    num_blocks: int = 15,
    area_size: float = 200.0,
    terrain: Optional[bproc.types.MeshObject] = None
) -> List[bproc.types.MeshObject]:
    """
    Create yellow blocks (machinery) as negative samples.
    
    :param num_blocks: Number of machinery blocks
    :param area_size: Size of the area
    :param terrain: Optional terrain for height matching
    :return: List of machinery objects
    """
    print(f"Creating {num_blocks} yellow machinery blocks...")
    blocks = []
    
    for i in range(num_blocks):
        # Random position
        x = np.random.uniform(-area_size/2, area_size/2)
        y = np.random.uniform(-area_size/2, area_size/2)
        
        # Get terrain height if available
        if terrain:
            z = get_terrain_height(x, y, terrain)
        else:
            z = 0.0
        
        # Create machinery block (larger than bags)
        size = np.random.uniform(1.5, 3.0)
        height = np.random.uniform(0.8, 1.5)
        
        block = bproc.object.create_primitive("CUBE", size=1.0)
        block.set_scale([size/2, size/2, height/2])
        # Place block ON the terrain surface (not floating)
        block.set_location([x, y, z + height/2])
        
        # Random rotation
        block.set_rotation_euler([
            np.random.uniform(0, 2 * np.pi),
            np.random.uniform(0, 2 * np.pi),
            np.random.uniform(0, 2 * np.pi)
        ])
        
        block.blender_obj.hide_set(False)
        block.blender_obj.hide_render = False
        
        # Yellow material (construction machinery color)
        block_material = block.new_material(f"machinery_material_{i}")
        yellow_color = np.random.uniform([0.8, 0.7, 0.1], [0.95, 0.85, 0.2])
        block_material.set_principled_shader_value("Base Color", list(yellow_color) + [1.0])
        block_material.set_principled_shader_value("Metallic", 0.3)
        block_material.set_principled_shader_value("Roughness", 0.5)
        
        # Negative sample - NOT a pile
        block.set_cp("category_id", -1)
        blocks.append(block)
    
    print(f"Created {len(blocks)} machinery blocks")
    return blocks


def write_yolo_annotations(
    labels_dir: str,
    instance_segmaps,
    instance_attribute_maps: List[Dict],
    image_width: int,
    image_height: int,
    image_index: int = 0
) -> None:
    """
    Write YOLO format annotations from segmentation maps.
    
    :param labels_dir: Labels directory (e.g., "output/labels")
    :param instance_segmaps: Instance segmentation maps (can be list or numpy array)
    :param instance_attribute_maps: Attribute maps for each instance
    :param image_width: Image width
    :param image_height: Image height
    :param image_index: Global image index for filename (e.g., 0, 1, 2, ...)
    """
    os.makedirs(labels_dir, exist_ok=True)
    
    # Handle both list and numpy array formats
    if isinstance(instance_segmaps, list):
        segmaps_list = instance_segmaps
    else:
        # Convert numpy array to list if needed
        if len(instance_segmaps.shape) > 2:
            segmaps_list = [instance_segmaps[i] for i in range(instance_segmaps.shape[0])]
        else:
            segmaps_list = [instance_segmaps]
    
    # Defensive check: ensure segmaps_list is not empty
    if not segmaps_list or len(segmaps_list) == 0:
        print(f"Warning: Empty segmentation maps list, skipping annotation generation for image {image_index:06d}")
        # Create empty annotation file
        label_file = os.path.join(labels_dir, f"{image_index:06d}.txt")
        with open(label_file, 'w') as f:
            pass  # Empty file
        return
    
    # Process first frame (assuming one image per render call)
    segmap = segmaps_list[0]
    
    # Additional defensive check: ensure segmap is valid
    # Check if segmap is None or not a valid array-like object
    if segmap is None:
        print(f"Warning: Segmentation map is None, skipping annotation generation for image {image_index:06d}")
        label_file = os.path.join(labels_dir, f"{image_index:06d}.txt")
        with open(label_file, 'w') as f:
            pass  # Empty file
        return
    
    # Convert to numpy array if needed (handles both numpy arrays and lists)
    try:
        segmap = np.asarray(segmap)
    except Exception as e:
        print(f"Warning: Cannot convert segmentation map to numpy array: {e}, skipping annotation generation for image {image_index:06d}")
        label_file = os.path.join(labels_dir, f"{image_index:06d}.txt")
        with open(label_file, 'w') as f:
            pass  # Empty file
        return
    
    # Check if segmap is empty (now safe to access .size)
    if segmap.size == 0:
        print(f"Warning: Empty segmentation map, skipping annotation generation for image {image_index:06d}")
        label_file = os.path.join(labels_dir, f"{image_index:06d}.txt")
        with open(label_file, 'w') as f:
            pass  # Empty file
        return
    
    # Find unique instance IDs (excluding background 0)
    unique_ids = np.unique(segmap)
    unique_ids = unique_ids[unique_ids > 0]
    
    annotations = []
    
    for instance_id in unique_ids:
        # Get mask for this instance
        mask = (segmap == instance_id).astype(np.uint8)
        
        # Find bounding box
        coords = np.column_stack(np.where(mask > 0))
        if len(coords) == 0:
            continue
        
        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)
        
        # Convert to YOLO format (normalized center x, center y, width, height)
        center_x = (x_min + x_max) / 2.0 / image_width
        center_y = (y_min + y_max) / 2.0 / image_height
        width = (x_max - x_min) / image_width
        height = (y_max - y_min) / image_height
        
        # Get category_id from attribute map
        category_id = 0  # Default to pile
        if len(instance_attribute_maps) > 0:
            frame_attrs = instance_attribute_maps[0]
            if isinstance(frame_attrs, list):
                for attr in frame_attrs:
                    # Check both 'segmap_id' and 'idx' (BlenderProc uses different keys)
                    segmap_id = attr.get('segmap_id') or attr.get('idx')
                    if segmap_id == instance_id:
                        category_id = attr.get('category_id', 0)
                        break
        
        # Only write annotations for piles (category_id == 0)
        if category_id == 0:
            annotations.append(f"{category_id} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f}\n")
    
    # Write annotation file with global image index
    label_file = os.path.join(labels_dir, f"{image_index:06d}.txt")
    with open(label_file, 'w') as f:
        f.writelines(annotations)
    
    print(f"  Generated {len(annotations)} annotations -> {label_file}")


def generate_single_image(
    images_dir: str,
    labels_dir: str,
    render_width: int,
    render_height: int,
    asset_path: Optional[str],
    use_clusters: bool,
    all_textures: Optional[Dict[str, List[Dict[str, Path]]]] = None,
    image_index: int = 0,
    save_hdf5: bool = False,
    save_coco: bool = False,
    hdf5_dir: Optional[str] = None,
    coco_dir: Optional[str] = None,
    **kwargs
) -> None:
    """
    Generate a single image with randomized parameters for diversity.
    
    :param images_dir: Directory to save images (e.g., "output/images")
    :param labels_dir: Directory to save labels (e.g., "output/labels")
    :param render_width: Image width
    :param render_height: Image height
    :param asset_path: Path to asset folder
    :param use_clusters: Whether to use cluster mode
    :param all_textures: All available textures for randomization
    :param image_index: Global image index for filename
    :param save_hdf5: Whether to save HDF5 files
    :param save_coco: Whether to save COCO annotations
    :param hdf5_dir: Directory for HDF5 files (if save_hdf5=True)
    :param coco_dir: Directory for COCO files (if save_coco=True)
    :param kwargs: Additional parameters (with defaults or ranges)
    """
    # Randomize terrain parameters
    terrain_size = kwargs.get('terrain_size', np.random.uniform(180.0, 220.0))
    num_terraces = kwargs.get('num_terraces', np.random.randint(6, 12))
    terrace_height = kwargs.get('terrace_height', np.random.uniform(1.5, 3.0))
    
    # Randomize pile parameters
    if use_clusters:
        num_clusters = kwargs.get('num_clusters', np.random.randint(1, 6))
        min_piles_per_cluster = kwargs.get('min_piles_per_cluster', np.random.randint(50, 70))
        max_piles_per_cluster = kwargs.get('max_piles_per_cluster', np.random.randint(80, 120))
        cluster_size = kwargs.get('cluster_size', np.random.uniform(25.0, 35.0))
    else:
        num_rows = kwargs.get('num_rows', np.random.randint(12, 18))
        piles_per_row = kwargs.get('piles_per_row', np.random.randint(30, 40))
        row_spacing = kwargs.get('row_spacing', np.random.uniform(3.0, 4.0))
    
    # Randomize distractor counts
    num_bags = kwargs.get('num_bags', np.random.randint(20, 40))
    num_machinery = kwargs.get('num_machinery', np.random.randint(10, 20))
    
    # Randomize lighting
    sun_elevation = kwargs.get('sun_elevation', np.random.uniform(30, 60))
    sun_azimuth = kwargs.get('sun_azimuth', np.random.uniform(0, 360))
    sun_energy = kwargs.get('sun_energy', np.random.uniform(1.0, 2.0))  # Further reduced based on working versions
    sun_radius = kwargs.get('sun_radius', np.random.uniform(1.5, 2.5))
    
    # Random seed is set in main() based on --seed and --image_index
    # Each process is independent, so seed is already set correctly
    
    # Select random textures
    selected_textures = None
    if all_textures:
        selected_textures = select_random_textures(all_textures)
    
    # Note: No scene cleanup needed - each process is fresh, bproc.init() already cleaned the scene
    
    # Set resolution
    bproc.camera.set_resolution(render_width, render_height)
    
    # Create terraced terrain with random textures
    print(f"Creating terraced terrain (size={terrain_size:.1f}m, terraces={num_terraces}, height={terrace_height:.1f}m)...")
    terrain = create_terraced_terrain(
        size=terrain_size,
        num_terraces=num_terraces,
        terrace_height=terrace_height,
        asset_path=asset_path,
        texture_selection=selected_textures
    )
    
    # Pre-load concrete texture once (will be cached for all piles)
    if asset_path:
        load_concrete_texture(asset_path, print_found=False)
    
    # Choose geological preset (for advanced features)
    geological_preset = kwargs.get('geological_preset', np.random.choice(["loess", "hills"]))
    use_advanced_features = kwargs.get('use_advanced_features', ADVANCED_FEATURES_AVAILABLE)
    
    # Configure geological preset (if using advanced features)
    preset_config = None
    if use_advanced_features:
        preset_config = configure_geological_preset(terrain, geological_preset, asset_path)
        add_vegetation_traces(terrain, preset_config, asset_path)
    
    # Create piles: use advanced layout engine or legacy methods
    piles = []
    pile_positions = []  # For track marks and debris
    
    if use_advanced_features and ADVANCED_FEATURES_AVAILABLE:
        # Use constraint-based layout engine
        print("Using advanced constraint-based layout engine (GB 50797-2012)...")
        
        # Calculate number of groups based on desired pile count
        if use_clusters:
            num_groups = num_clusters
            piles_per_group = (min_piles_per_cluster + max_piles_per_cluster) // 2
        else:
            num_groups = num_rows
            piles_per_group = piles_per_row
        
        # Get pile layout from engine
        pile_info_list = layout_piles_with_constraints(
            terrain=terrain,
            area_size=terrain_size,
            num_groups=num_groups,
            piles_per_group=piles_per_group,
            road_width=8.0,
            asset_path=asset_path
        )
        
        # Create piles using factory
        for pile_info in pile_info_list:
            pos = pile_info['position']
            terrain_z = pile_info['terrain_z']
            tilt = pile_info['tilt']
            pile_type = pile_info['pile_type']
            pile_params = pile_info['pile_params']
            
            # Override pile type based on preset (if specified)
            if preset_config:
                pile_type_rand = np.random.random()
                pile_type_probs = preset_config.get('pile_type_probability', {})
                if pile_type_probs:
                    pile_type = np.random.choice(
                        list(pile_type_probs.keys()),
                        p=list(pile_type_probs.values())
                    )
            
            # Create pile using factory
            pile_obj, attachment = create_pile_variant(
                pile_type=pile_type,
                location=pos,
                terrain_z=terrain_z,
                **pile_params
            )
            
            # Apply tilt (engineering tolerance)
            pile_obj.set_rotation_euler(tilt)
            
            piles.append(pile_obj)
            if attachment:
                piles.append(attachment)
            
            pile_positions.append(pos)
        
        print(f"Total piles created: {len(piles)} (using advanced factory)")
    else:
        # Use legacy methods
        if use_clusters:
            print(f"Creating {num_clusters} pile clusters ({min_piles_per_cluster}-{max_piles_per_cluster} piles each)...")
            piles = create_pile_clusters(
                terrain=terrain,
                num_clusters=num_clusters,
                min_piles_per_cluster=min_piles_per_cluster,
                max_piles_per_cluster=max_piles_per_cluster,
                terrain_size=terrain_size,
                cluster_size=cluster_size,
                asset_path=asset_path
            )
            # Extract positions for legacy clusters (approximate)
            for pile in piles:
                loc = pile.get_location()
                pile_positions.append(np.array([loc[0], loc[1]]))
        else:
            print(f"Creating {num_rows} curved rows ({piles_per_row} piles per row)...")
            piles = create_curved_pile_rows(
                terrain=terrain,
                num_rows=num_rows,
                piles_per_row=piles_per_row,
                row_spacing=row_spacing,
                area_size=terrain_size,
                road_width=8.0,
                asset_path=asset_path
            )
            # Extract positions for legacy rows
            for pile in piles:
                loc = pile.get_location()
                pile_positions.append(np.array([loc[0], loc[1]]))
        
        print(f"Total piles created: {len(piles)}")
    
    # Add environmental storytelling (if using advanced features)
    if use_advanced_features and ADVANCED_FEATURES_AVAILABLE and pile_positions:
        print("Adding environmental storytelling...")
        
        # Create track marks
        create_track_marks(terrain, pile_positions)
        
        # Create construction debris
        debris_objects = create_construction_debris(
            terrain,
            pile_positions,
            debris_probability=0.3
        )
        # Note: debris_objects are already created and added to scene
    
    # Create distractor objects
    print(f"Creating {num_bags} material bags and {num_machinery} machinery blocks...")
    material_bags = create_material_bags(
        num_bags=num_bags,
        area_size=terrain_size,
        terrain=terrain
    )
    
    machinery_blocks = create_machinery_blocks(
        num_blocks=num_machinery,
        area_size=terrain_size,
        terrain=terrain
    )
    
    # Setup camera - Nadir view at 100m altitude
    camera_height = 100.0
    camera_location = np.array([0.0, 0.0, camera_height])
    target_point = np.array([0.0, 0.0, 0.0])
    
    # Look straight down
    forward = target_point - camera_location
    forward = forward / np.linalg.norm(forward)
    
    rotation_matrix = bproc.camera.rotation_from_forward_vec(forward, up_axis='Y')
    cam2world = bproc.math.build_transformation_mat(camera_location, rotation_matrix)
    bproc.camera.add_camera_pose(cam2world)
    
    # Wide FOV to cover large area
    fov_radians = np.radians(90.0)
    bproc.camera.set_intrinsics_from_blender_params(
        lens_unit='FOV',
        lens=fov_radians,
        image_width=render_width,
        image_height=render_height,
        clip_start=0.1,
        clip_end=500.0
    )
    
    # Lighting - Randomized sun
    light = bproc.types.Light()
    light.set_type("SUN")
    light.set_location([0, 0, 0])
    
    light.set_rotation_euler([
        np.radians(-sun_elevation),
        np.radians(sun_azimuth),
        0
    ])
    light.set_energy(sun_energy)
    light.set_radius(sun_radius)
    light.set_color([1.0, 0.98, 0.95])
    
    print(f"Sun: {sun_elevation:.1f}° elevation, {sun_azimuth:.1f}° azimuth, energy={sun_energy:.1f}, radius={sun_radius:.1f}")
    
    # No need to clear outputs - each process starts fresh with bproc.init()
    
    # Enable segmentation BEFORE rendering
    # This must be called fresh for each image to avoid duplicate registration
    bproc.renderer.enable_segmentation_output(
        map_by=["category_id", "instance", "name"],
        default_values={"category_id": -1}
    )
    
    # Render
    print("Rendering...")
    data = bproc.renderer.render()
    
    # Save image to images directory (using same method as working versions)
    os.makedirs(images_dir, exist_ok=True)
    if 'colors' in data and len(data['colors']) > 0:
        # Get first frame (assuming one image per render)
        color_image = data['colors'][0]
        
        # Debug: Check value range
        img_min, img_max, img_mean = color_image.min(), color_image.max(), color_image.mean()
        print(f"  Color image stats: min={img_min:.3f}, max={img_max:.3f}, mean={img_mean:.3f}, dtype={color_image.dtype}")
        
        # BlenderProc returns images - check if already in [0,255] or [0,1] range
        # Based on working code: generate_solar_farm_dataset.py uses (color_bgr * 255)
        # So values are in [0,1] range and need to be multiplied by 255
        # But if max > 1, they're already in [0,255] range
        
        if img_max > 1.0:
            # Already in [0,255] range (like generate_solar_farm_simple.py)
            color_uint8 = np.clip(color_image, 0, 255).astype(np.uint8)
            # Convert RGB to BGR
            if color_uint8.shape[2] >= 3:
                color_uint8[..., :3] = color_uint8[..., :3][..., ::-1]
        else:
            # In [0,1] range (like generate_solar_farm_dataset.py)
            # Convert from RGB to BGR for OpenCV
            color_bgr = color_image.copy()
            if color_bgr.shape[2] >= 3:
                color_bgr[..., :3] = color_bgr[..., :3][..., ::-1]
            # Convert from float [0,1] to uint8 [0,255]
            color_uint8 = (color_bgr * 255).astype(np.uint8)
        
        # Save as PNG
        image_path = os.path.join(images_dir, f"{image_index:06d}.png")
        cv2.imwrite(image_path, color_uint8)
        print(f"  Image saved: {image_path}")
    else:
        print("Warning: No color image found in render data")
    
    # Generate YOLO annotations
    if 'instance_segmaps' in data and 'instance_attribute_maps' in data:
        write_yolo_annotations(
            labels_dir,
            data['instance_segmaps'],
            data['instance_attribute_maps'],
            render_width,
            render_height,
            image_index
        )
    else:
        print("Warning: instance_segmaps or instance_attribute_maps not found in render data")
    
    # Optionally save HDF5
    if save_hdf5 and hdf5_dir:
        os.makedirs(hdf5_dir, exist_ok=True)
        # Create a temporary subdirectory for this image to avoid filename conflicts
        temp_hdf5_dir = os.path.join(hdf5_dir, f"temp_{image_index:06d}")
        os.makedirs(temp_hdf5_dir, exist_ok=True)
        bproc.writer.write_hdf5(temp_hdf5_dir, data)
        # Move the generated file to the correct location
        generated_hdf5 = os.path.join(temp_hdf5_dir, "0.hdf5")
        final_hdf5 = os.path.join(hdf5_dir, f"{image_index:06d}.hdf5")
        if os.path.exists(generated_hdf5):
            import shutil
            shutil.move(generated_hdf5, final_hdf5)
            os.rmdir(temp_hdf5_dir)
        print(f"  HDF5 saved: {final_hdf5}")
    
    # Optionally save COCO annotations
    if save_coco and coco_dir and 'instance_segmaps' in data and 'instance_attribute_maps' in data and 'colors' in data:
        os.makedirs(coco_dir, exist_ok=True)
        bproc.writer.write_coco_annotations(
            coco_dir,
            instance_segmaps=data['instance_segmaps'],
            instance_attribute_maps=data['instance_attribute_maps'],
            colors=data['colors']
        )
        print(f"  COCO annotations saved: {coco_dir}")
    
    print(f"✅ Image {image_index:06d} saved")


def main() -> None:
    """Main function - Mountainous Solar Construction Site with batch generation support."""
    parser = argparse.ArgumentParser(description="Generate mountainous solar construction site dataset")
    parser.add_argument('output_dir', type=str, help="Output directory")
    parser.add_argument('--image_index', type=int, default=0, help="Image index for filename (e.g., 0 -> 000000.png)")
    parser.add_argument('--num_rows', type=int, default=15, help="Number of pile rows (or range: min,max)")
    parser.add_argument('--piles_per_row', type=int, default=35, help="Piles per row (or range: min,max)")
    parser.add_argument('--row_spacing', type=float, default=3.5, help="Spacing between rows (or range: min,max)")
    parser.add_argument('--terrain_size', type=float, default=200.0, help="Terrain size in meters (or range: min,max)")
    parser.add_argument('--num_terraces', type=int, default=8, help="Number of terrace levels (or range: min,max)")
    parser.add_argument('--terrace_height', type=float, default=2.0, help="Height difference between terraces (or range: min,max)")
    parser.add_argument('--render_width', type=int, default=5280, help="Render width")
    parser.add_argument('--render_height', type=int, default=3956, help="Render height")
    parser.add_argument('--num_cameras', type=int, default=1, help="Number of camera poses (deprecated, always 1 per image)")
    # Default asset path: try relative path first, then absolute path
    default_asset_path = None
    relative_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "asset")
    absolute_path = "/Volumes/leo_disk/asset"
    
    if os.path.exists(relative_path):
        default_asset_path = os.path.abspath(relative_path)
    elif os.path.exists(absolute_path):
        default_asset_path = absolute_path
    
    parser.add_argument(
        '--asset_path', 
        type=str, 
        default=default_asset_path,
        help=f"Path to asset folder (default: {default_asset_path or 'None - must be specified'})"
    )
    parser.add_argument('--num_bags', type=int, default=30, help="Number of material bags (or range: min,max)")
    parser.add_argument('--num_machinery', type=int, default=15, help="Number of machinery blocks (or range: min,max)")
    parser.add_argument('--use_clusters', action='store_true', help="Use cluster mode: 1-5 clusters with 50+ piles each, random row directions")
    parser.add_argument('--num_clusters', type=int, default=None, help="Number of clusters (1-5, random if not specified)")
    parser.add_argument('--min_piles_per_cluster', type=int, default=50, help="Minimum piles per cluster (or range: min,max)")
    parser.add_argument('--max_piles_per_cluster', type=int, default=100, help="Maximum piles per cluster (or range: min,max)")
    parser.add_argument('--cluster_size', type=float, default=30.0, help="Size of each cluster in meters (or range: min,max)")
    parser.add_argument('--seed', type=int, default=None, help="Random seed for reproducibility (if not set, uses random seed)")
    parser.add_argument('--use_gpu', action='store_true', default=True, help="Use GPU for rendering (Metal on Apple Silicon)")
    parser.add_argument('--max_samples', type=int, default=50, help="Maximum number of samples per pixel (default: 50, use 100 for higher quality)")
    parser.add_argument('--noise_threshold', type=float, default=0.01, help="Noise threshold for adaptive sampling (default: 0.01)")
    parser.add_argument('--save_hdf5', action='store_true', help="Save HDF5 files (optional, for visualization)")
    parser.add_argument('--save_coco', action='store_true', help="Save COCO annotations (optional)")
    parser.add_argument('--use_advanced_features', action='store_true', default=True, help="Use advanced features (high-fidelity piles, constraint-based layout, environmental storytelling)")
    parser.add_argument('--geological_preset', type=str, choices=["loess", "hills"], default=None, help="Geological preset: 'loess' (黄土高原) or 'hills' (南方丘陵). If not set, randomly chosen.")
    args = parser.parse_args()
    
    # Set random seed if provided (for reproducibility and parallel execution)
    if args.seed is not None:
        os.environ['BLENDER_PROC_RANDOM_SEED'] = str(args.seed)
        np.random.seed(args.seed)
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")
    
    # Initialize BlenderProc once (before the loop)
    bproc.init()
    
    # Configure GPU rendering for Apple Silicon (Metal)
    if args.use_gpu:
        print("Configuring GPU rendering (Metal for Apple Silicon)...")
        bproc.renderer.set_render_devices(
            use_only_cpu=False,
            desired_gpu_device_type="METAL"
        )
        
        # Note: On Apple Silicon, it's often better to use BOTH GPU and CPU
        # Disabling CPU can actually slow things down. Let both work together.
        # Note: Tile size settings removed in Blender 4.2+ (handled automatically)
        print("  Using GPU + CPU for optimal performance on Apple Silicon")
    else:
        print("Using CPU rendering (slower)")
        bproc.renderer.set_render_devices(use_only_cpu=True)
    
    # Set exposure to prevent overexposure (negative exposure = darker)
    import bpy
    bpy.context.scene.view_settings.exposure = -0.5  # Reduce exposure by 0.5 stops
    print("  Set exposure to -0.5 to prevent overexposure")
    
    # Optimize render settings for faster training data generation
    # Note: Keep default Filmic view transform (as in working versions)
    print(f"Optimizing render settings: max_samples={args.max_samples}, noise_threshold={args.noise_threshold}")
    bproc.renderer.set_max_amount_of_samples(args.max_samples)
    bproc.renderer.set_noise_threshold(args.noise_threshold)
    
    # For training data, we can use higher noise threshold to speed up rendering
    # The denoiser will clean up the noise anyway
    if args.max_samples <= 50:
        # With fewer samples, use slightly higher threshold for faster rendering
        actual_threshold = max(args.noise_threshold, 0.02)
        if actual_threshold > args.noise_threshold:
            bproc.renderer.set_noise_threshold(actual_threshold)
            print(f"  Adjusted noise threshold to {actual_threshold} for faster rendering with {args.max_samples} samples")
    
    # Additional Cycles optimizations for speed
    import bpy
    # Disable light tree (increases render time per sample, not needed for simple scenes)
    bpy.context.scene.cycles.use_light_tree = False
    
    # Reduce light bounces for faster rendering (training data doesn't need perfect GI)
    bproc.renderer.set_light_bounces(
        diffuse_bounces=2,
        glossy_bounces=2,
        transmission_bounces=2,
        max_bounces=4
    )
    
    # Disable caustics (not needed for training data, speeds up rendering)
    bpy.context.scene.cycles.caustics_reflective = False
    bpy.context.scene.cycles.caustics_refractive = False
    
    print("  Optimized Cycles settings: light_tree=off, reduced bounces, caustics=off")
    
    # Disable denoiser for faster rendering (denoiser can add 20-50% render time)
    # For training data, we can accept some noise to speed up generation significantly
    try:
        # Use the correct API path
        from blenderproc.python.renderer.RendererUtility import disable_all_denoiser
        disable_all_denoiser()
        print("  Denoiser disabled for faster rendering")
    except Exception as e:
        # Fallback: manually disable denoiser
        try:
            import bpy
            bpy.context.view_layer.cycles.use_denoising = False
            bpy.context.scene.cycles.use_denoising = False
            print("  Denoiser disabled manually")
        except Exception as e2:
            print(f"  Note: Could not disable denoiser: {e}, {e2}")
            print("  Continuing...")
    
    # Load all available textures once for randomization
    all_textures = None
    if args.asset_path:
        print("Loading all available textures for randomization...")
        all_textures = load_all_terrain_textures(args.asset_path)
        if all_textures:
            total = sum(len(v) for v in all_textures.values())
            print(f"  Loaded {total} texture sets for randomization")
        else:
            print("  No textures found, will use procedural fallback")
    
    # Parse range parameters (format: "min,max" or single value)
    def parse_range(value, default_min, default_max):
        if isinstance(value, str) and ',' in value:
            parts = value.split(',')
            return (float(parts[0]), float(parts[1]))
        return value
    
    # Create unified output directories for YOLO training format
    images_dir = os.path.join(args.output_dir, "images")
    labels_dir = os.path.join(args.output_dir, "labels")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(labels_dir, exist_ok=True)
    
    # Optional directories for HDF5 and COCO (if needed)
    hdf5_dir = os.path.join(args.output_dir, "hdf5") if args.save_hdf5 else None
    coco_dir = os.path.join(args.output_dir, "coco_annotations") if args.save_coco else None
    if hdf5_dir:
        os.makedirs(hdf5_dir, exist_ok=True)
    if coco_dir:
        os.makedirs(coco_dir, exist_ok=True)
    
    print(f"Output structure:")
    print(f"  Images: {images_dir}")
    print(f"  Labels: {labels_dir}")
    if hdf5_dir:
        print(f"  HDF5: {hdf5_dir}")
    if coco_dir:
        print(f"  COCO: {coco_dir}")
    
    # Generate images
    # Set random seed based on image_index and seed
    # This ensures each process gets a unique seed for diversity
    if args.seed is not None:
        # Use seed + image_index for unique randomization per image
        effective_seed = args.seed + args.image_index
    else:
        # Use image_index as seed if no base seed provided
        effective_seed = args.image_index
    
    os.environ['BLENDER_PROC_RANDOM_SEED'] = str(effective_seed)
    np.random.seed(effective_seed)
    random.seed(effective_seed)
    print(f"Using random seed: {effective_seed} (base={args.seed}, index={args.image_index})")
    
    print(f"\n{'='*60}")
    print(f"Generating image (Index: {args.image_index:06d})")
    print(f"{'='*60}\n")
    
    # Randomize all parameters for diversity
    kwargs = {}
    
    # Terrain randomization
    if isinstance(args.terrain_size, str) and ',' in args.terrain_size:
        min_size, max_size = map(float, args.terrain_size.split(','))
        kwargs['terrain_size'] = np.random.uniform(min_size, max_size)
    else:
        kwargs['terrain_size'] = args.terrain_size if args.terrain_size != 200.0 else np.random.uniform(180.0, 220.0)
    
    if isinstance(args.num_terraces, str) and ',' in args.num_terraces:
        min_t, max_t = map(int, args.num_terraces.split(','))
        kwargs['num_terraces'] = np.random.randint(min_t, max_t + 1)
    else:
        kwargs['num_terraces'] = args.num_terraces if args.num_terraces != 8 else np.random.randint(6, 12)
    
    if isinstance(args.terrace_height, str) and ',' in args.terrace_height:
        min_h, max_h = map(float, args.terrace_height.split(','))
        kwargs['terrace_height'] = np.random.uniform(min_h, max_h)
    else:
        kwargs['terrace_height'] = args.terrace_height if args.terrace_height != 2.0 else np.random.uniform(1.5, 3.0)
    
    # Pile randomization
    if args.use_clusters:
        kwargs['num_clusters'] = args.num_clusters if args.num_clusters is not None else np.random.randint(1, 6)
        
        if isinstance(args.min_piles_per_cluster, str) and ',' in args.min_piles_per_cluster:
            min_p, max_p = map(int, args.min_piles_per_cluster.split(','))
            kwargs['min_piles_per_cluster'] = np.random.randint(min_p, max_p + 1)
        else:
            kwargs['min_piles_per_cluster'] = args.min_piles_per_cluster if args.min_piles_per_cluster != 50 else np.random.randint(50, 70)
        
        if isinstance(args.max_piles_per_cluster, str) and ',' in args.max_piles_per_cluster:
            min_p, max_p = map(int, args.max_piles_per_cluster.split(','))
            kwargs['max_piles_per_cluster'] = np.random.randint(min_p, max_p + 1)
        else:
            kwargs['max_piles_per_cluster'] = args.max_piles_per_cluster if args.max_piles_per_cluster != 100 else np.random.randint(80, 120)
        
        if isinstance(args.cluster_size, str) and ',' in args.cluster_size:
            min_s, max_s = map(float, args.cluster_size.split(','))
            kwargs['cluster_size'] = np.random.uniform(min_s, max_s)
        else:
            kwargs['cluster_size'] = args.cluster_size if args.cluster_size != 30.0 else np.random.uniform(25.0, 35.0)
    else:
        if isinstance(args.num_rows, str) and ',' in args.num_rows:
            min_r, max_r = map(int, args.num_rows.split(','))
            kwargs['num_rows'] = np.random.randint(min_r, max_r + 1)
        else:
            kwargs['num_rows'] = args.num_rows if args.num_rows != 15 else np.random.randint(12, 18)
        
        if isinstance(args.piles_per_row, str) and ',' in args.piles_per_row:
            min_p, max_p = map(int, args.piles_per_row.split(','))
            kwargs['piles_per_row'] = np.random.randint(min_p, max_p + 1)
        else:
            kwargs['piles_per_row'] = args.piles_per_row if args.piles_per_row != 35 else np.random.randint(30, 40)
        
        if isinstance(args.row_spacing, str) and ',' in args.row_spacing:
            min_s, max_s = map(float, args.row_spacing.split(','))
            kwargs['row_spacing'] = np.random.uniform(min_s, max_s)
        else:
            kwargs['row_spacing'] = args.row_spacing if args.row_spacing != 3.5 else np.random.uniform(3.0, 4.0)
    
    # Distractor randomization
    if isinstance(args.num_bags, str) and ',' in args.num_bags:
        min_b, max_b = map(int, args.num_bags.split(','))
        kwargs['num_bags'] = np.random.randint(min_b, max_b + 1)
    else:
        kwargs['num_bags'] = args.num_bags if args.num_bags != 30 else np.random.randint(20, 40)
    
    if isinstance(args.num_machinery, str) and ',' in args.num_machinery:
        min_m, max_m = map(int, args.num_machinery.split(','))
        kwargs['num_machinery'] = np.random.randint(min_m, max_m + 1)
    else:
        kwargs['num_machinery'] = args.num_machinery if args.num_machinery != 15 else np.random.randint(10, 20)
    
    # Lighting randomization (always randomized)
    kwargs['sun_elevation'] = np.random.uniform(30, 60)
    kwargs['sun_azimuth'] = np.random.uniform(0, 360)
    kwargs['sun_energy'] = np.random.uniform(1.0, 2.0)
    kwargs['sun_radius'] = np.random.uniform(1.5, 2.5)
    
    # Generate single image (no cleanup needed - fresh process)
    # Add advanced features parameters
    kwargs['use_advanced_features'] = args.use_advanced_features
    if args.geological_preset:
        kwargs['geological_preset'] = args.geological_preset
    
    generate_single_image(
        images_dir=images_dir,
        labels_dir=labels_dir,
        render_width=args.render_width,
        render_height=args.render_height,
        asset_path=args.asset_path,
        use_clusters=args.use_clusters,
        all_textures=all_textures,
        image_index=args.image_index,
        save_hdf5=args.save_hdf5,
        save_coco=args.save_coco,
        hdf5_dir=hdf5_dir,
        coco_dir=coco_dir,
        **kwargs
    )
    
    print(f"\n{'='*60}")
    print(f"✅ Image {args.image_index:06d} saved to {args.output_dir}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

