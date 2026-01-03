"""
Environmental Storytelling and Trace Generation
环境叙事与痕迹生成模块

为了消除"CG感"，增加真实的环境细节：
1. 机械车辙（Track Marks）
2. 施工废料（Construction Debris）
3. 地质特征匹配（Geological Features）
"""

import blenderproc as bproc
import numpy as np
import bpy
import mathutils
from typing import List, Tuple, Optional, Dict, Literal
from pathlib import Path
from blenderproc.python.utility.Utility import Utility


def create_track_marks(
    terrain: bproc.types.MeshObject,
    pile_positions: List[np.ndarray],
    track_width: float = 0.7,  # 700mm车辙宽度
    track_spacing: float = 1.8,  # 1.8m履带间距
    track_depth: float = 0.05  # 5cm下陷深度
) -> None:
    """
    在每一排桩的间隙（行进通道）生成平行的履带车辙印。
    
    使用Blender的几何节点或置换修改器，使车辙处的地面轻微下陷，
    并改变该处的粗糙度和颜色（变深，模拟翻出的湿土）。
    
    :param terrain: 地形对象
    :param pile_positions: 桩位置列表（用于确定通道位置）
    :param track_width: 车辙宽度（m）
    :param track_spacing: 履带间距（m）
    :param track_depth: 车辙深度（m）
    """
    print(f"Creating track marks (width={track_width}m, spacing={track_spacing}m)...")
    
    # 获取地形材质
    terrain_material = terrain.get_materials()[0] if terrain.get_materials() else None
    
    if not terrain_material:
        print("Warning: Terrain has no material, skipping track marks")
        return
    
    nodes = terrain_material.blender_obj.node_tree.nodes
    links = terrain_material.blender_obj.node_tree.links
    principled_bsdf = Utility.get_the_one_node_with_type(nodes, "BsdfPrincipled")
    
    # 创建车辙纹理（使用程序化纹理）
    # 方法：使用多个条纹纹理叠加，模拟履带印
    
    # 创建纹理坐标
    tex_coord = nodes.new(type='ShaderNodeTexCoord')
    mapping = nodes.new(type='ShaderNodeMapping')
    mapping.inputs['Scale'].default_value = (0.5, 0.5, 1.0)  # 缩放
    links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
    
    # 创建条纹纹理（模拟车辙）
    wave_tex = nodes.new(type='ShaderNodeTexWave')
    wave_tex.wave_type = 'BANDS'
    wave_tex.inputs['Scale'].default_value = 2.0
    wave_tex.inputs['Distortion'].default_value = 0.5
    wave_tex.inputs['Detail'].default_value = 2.0
    links.new(mapping.outputs['Vector'], wave_tex.inputs['Vector'])
    
    # 创建噪声纹理（增加随机性）
    noise_tex = nodes.new(type='ShaderNodeTexNoise')
    noise_tex.inputs['Scale'].default_value = 5.0
    noise_tex.inputs['Detail'].default_value = 5.0
    links.new(mapping.outputs['Vector'], noise_tex.inputs['Vector'])
    
    # 混合噪声和条纹
    mix_track = nodes.new(type='ShaderNodeMixRGB')
    mix_track.inputs['Fac'].default_value = 0.5
    links.new(wave_tex.outputs['Fac'], mix_track.inputs['Color1'])
    links.new(noise_tex.outputs['Fac'], mix_track.inputs['Color2'])
    
    # 车辙颜色（深色，模拟翻出的湿土）
    track_color = nodes.new(type='ShaderNodeRGB')
    track_color.outputs['Color'].default_value = (0.3, 0.25, 0.2, 1.0)  # 深棕色
    
    # 混合车辙颜色到基础颜色
    mix_color = nodes.new(type='ShaderNodeMixRGB')
    mix_color.inputs['Fac'].default_value = 0.3  # 30%车辙颜色
    links.new(mix_track.outputs['Color'], mix_color.inputs['Fac'])  # 使用混合结果作为因子
    links.new(track_color.outputs['Color'], mix_color.inputs['Color1'])
    
    # 获取原有的基础颜色输入
    base_color_input = principled_bsdf.inputs['Base Color']
    if len(base_color_input.links) > 0:
        # 如果有现有连接，混合
        existing_color = base_color_input.links[0].from_socket
        links.new(existing_color, mix_color.inputs['Color2'])
    else:
        # 如果没有，使用默认颜色
        mix_color.inputs['Color2'].default_value = (0.6, 0.5, 0.4, 1.0)
    
    links.new(mix_color.outputs['Color'], base_color_input)
    
    # 增加车辙处的粗糙度
    roughness_mix = nodes.new(type='ShaderNodeMixRGB')
    roughness_mix.blend_type = 'MIX'
    roughness_mix.inputs['Fac'].default_value = 0.4
    links.new(mix_track.outputs['Color'], roughness_mix.inputs['Fac'])
    roughness_mix.inputs['Color1'].default_value = (0.95, 0.95, 0.95, 1.0)  # 高粗糙度
    roughness_mix.inputs['Color2'].default_value = (0.7, 0.7, 0.7, 1.0)  # 基础粗糙度
    
    # 连接到粗糙度
    roughness_input = principled_bsdf.inputs['Roughness']
    if len(roughness_input.links) > 0:
        existing_rough = roughness_input.links[0].from_socket
        roughness_mix.inputs['Color2'] = existing_rough.default_value
        links.remove(roughness_input.links[0])
    
    links.new(roughness_mix.outputs['Color'], roughness_input)
    
    # 添加置换修改器模拟下陷（如果可能）
    try:
        # 创建置换纹理
        displace_tex = bpy.data.textures.new(name="TrackDisplace", type='CLOUDS')
        displace_tex.noise_scale = 1.0
        
        # 添加置换修改器
        bpy.context.view_layer.objects.active = terrain.blender_obj
        bpy.ops.object.modifier_add(type='DISPLACE')
        terrain.blender_obj.modifiers[-1].name = "TrackMarks"
        terrain.blender_obj.modifiers[-1].texture = displace_tex
        terrain.blender_obj.modifiers[-1].strength = -track_depth  # 负值表示下陷
        terrain.blender_obj.modifiers[-1].mid_level = 0.5
    except Exception as e:
        print(f"Warning: Could not add displacement for track marks: {e}")
    
    print(f"  Added track marks to terrain material")


def create_construction_debris(
    terrain: bproc.types.MeshObject,
    pile_positions: List[np.ndarray],
    debris_probability: float = 0.3,
    debris_radius: float = 1.0
) -> List[bproc.types.MeshObject]:
    """
    在桩基周围1米范围内，按概率生成施工废料。
    
    废料类型：
    - 截断的混凝土饼（Concrete chunks）
    - 锈蚀的短钢筋头（Rusty rebar pieces）
    - 白色石灰粉线（Lime powder lines）
    
    :param terrain: 地形对象
    :param pile_positions: 桩位置列表
    :param debris_probability: 生成废料的概率（30%）
    :param debris_radius: 废料生成半径（m，桩周围1米）
    :return: 废料对象列表
    """
    print(f"Creating construction debris (probability={debris_probability*100}%)...")
    
    debris_objects = []
    
    for pile_pos in pile_positions:
        if np.random.random() > debris_probability:
            continue
        
        # 在桩周围随机位置生成废料
        angle = np.random.uniform(0, 2 * np.pi)
        distance = np.random.uniform(0.3, debris_radius)
        debris_x = pile_pos[0] + distance * np.cos(angle)
        debris_y = pile_pos[1] + distance * np.sin(angle)
        
        # 获取地形高度
        hit, location = bproc.object.scene_ray_cast(
            [debris_x, debris_y, 100.0],
            [0, 0, -1]
        )
        if hit:
            debris_z = location[2]
        else:
            debris_z = 0.0
        
        # 随机选择废料类型
        debris_type = np.random.choice(["concrete", "rebar", "lime"], p=[0.5, 0.3, 0.2])
        
        if debris_type == "concrete":
            # 截断的混凝土饼
            chunk = bproc.object.create_primitive(
                "ICOSPHERE",
                subdivisions=1,
                radius=np.random.uniform(0.1, 0.3)
            )
            chunk.set_location([debris_x, debris_y, debris_z + 0.05])
            chunk.set_scale([
                np.random.uniform(0.8, 1.2),
                np.random.uniform(0.8, 1.2),
                np.random.uniform(0.3, 0.6)  # 扁平
            ])
            chunk.set_rotation_euler([
                np.random.uniform(0, np.pi),
                np.random.uniform(0, np.pi),
                np.random.uniform(0, 2 * np.pi)
            ])
            
            # 混凝土材质（深灰色，粗糙）
            chunk_material = chunk.new_material("concrete_chunk_material")
            chunk_material.set_principled_shader_value("Base Color", (0.4, 0.4, 0.4, 1.0))
            chunk_material.set_principled_shader_value("Roughness", 0.9)
            chunk_material.set_principled_shader_value("Metallic", 0.0)
            
            chunk.set_cp("category_id", -1)  # 背景，不标注
            debris_objects.append(chunk)
        
        elif debris_type == "rebar":
            # 锈蚀的短钢筋头
            rebar = bproc.object.create_primitive(
                "CYLINDER",
                radius=0.01,  # 1cm半径
                depth=np.random.uniform(0.2, 0.5)
            )
            rebar.set_location([debris_x, debris_y, debris_z + 0.1])
            rebar.set_rotation_euler([
                np.random.uniform(0, np.pi / 4),
                np.random.uniform(0, np.pi / 4),
                np.random.uniform(0, 2 * np.pi)
            ])
            
            # 锈蚀金属材质
            rebar_material = rebar.new_material("rusty_rebar_material")
            rebar_material.set_principled_shader_value("Base Color", (0.5, 0.3, 0.2, 1.0))  # 锈色
            rebar_material.set_principled_shader_value("Metallic", 0.7)
            rebar_material.set_principled_shader_value("Roughness", 0.8)
            
            rebar.set_cp("category_id", -1)
            debris_objects.append(rebar)
        
        else:  # lime
            # 白色石灰粉线（使用平面）
            lime = bproc.object.create_primitive(
                "PLANE",
                scale=[np.random.uniform(0.3, 0.8), np.random.uniform(0.1, 0.3), 1.0]
            )
            lime.set_location([debris_x, debris_y, debris_z + 0.001])  # 紧贴地面
            lime.set_rotation_euler([np.pi / 2, 0, np.random.uniform(0, 2 * np.pi)])
            
            # 白色材质（高亮度，低粗糙度）
            lime_material = lime.new_material("lime_powder_material")
            lime_material.set_principled_shader_value("Base Color", (0.95, 0.95, 0.9, 1.0))  # 白色
            lime_material.set_principled_shader_value("Roughness", 0.3)
            lime_material.set_principled_shader_value("Metallic", 0.0)
            lime_material.set_principled_shader_value("Emission", (0.1, 0.1, 0.1, 1.0))  # 轻微发光
            
            lime.set_cp("category_id", -1)
            debris_objects.append(lime)
    
    print(f"  Created {len(debris_objects)} debris objects")
    return debris_objects


def configure_geological_preset(
    terrain: bproc.types.MeshObject,
    preset: Literal["loess", "hills"],
    asset_path: Optional[str] = None
) -> Dict:
    """
    配置地质特征预设。
    
    预设：
    - Config_Loess（黄土高原）：螺旋桩 + 干燥黄土 + 风积沙
    - Config_Hills（南方丘陵）：PHC桩 + 红粘土 + 植被痕迹
    
    :param terrain: 地形对象
    :param preset: 预设类型
    :param asset_path: 资产路径
    :return: 配置字典（包含推荐的桩类型、纹理等）
    """
    print(f"Configuring geological preset: {preset}")
    
    if preset == "loess":
        # 黄土高原配置
        config = {
            'pile_type_preference': "spiral_steel",  # 螺旋桩
            'pile_type_probability': {"spiral_steel": 0.7, "PHC": 0.2, "cast_in_place": 0.1},
            'terrain_color': (0.7, 0.6, 0.5, 1.0),  # 干燥黄土色
            'terrain_roughness': 0.8,
            'has_sand_deposits': True,
            'vegetation_density': 0.1,  # 低植被
            'texture_keywords': ["loess", "dry", "sand", "yellow"]
        }
        
        # 应用黄土材质
        terrain_material = terrain.get_materials()[0] if terrain.get_materials() else None
        if terrain_material:
            terrain_material.set_principled_shader_value("Base Color", config['terrain_color'])
            terrain_material.set_principled_shader_value("Roughness", config['terrain_roughness'])
    
    elif preset == "hills":
        # 南方丘陵配置
        config = {
            'pile_type_preference': "PHC",  # PHC桩
            'pile_type_probability': {"PHC": 0.6, "cast_in_place": 0.3, "spiral_steel": 0.1},
            'terrain_color': (0.6, 0.4, 0.3, 1.0),  # 红粘土色
            'terrain_roughness': 0.7,
            'has_sand_deposits': False,
            'vegetation_density': 0.5,  # 中等植被
            'texture_keywords': ["red", "clay", "grass", "vegetation"]
        }
        
        # 应用红粘土材质
        terrain_material = terrain.get_materials()[0] if terrain.get_materials() else None
        if terrain_material:
            terrain_material.set_principled_shader_value("Base Color", config['terrain_color'])
            terrain_material.set_principled_shader_value("Roughness", config['terrain_roughness'])
    
    else:
        raise ValueError(f"Unknown preset: {preset}")
    
    print(f"  Applied {preset} preset configuration")
    return config


def add_vegetation_traces(
    terrain: bproc.types.MeshObject,
    preset_config: Dict,
    asset_path: Optional[str] = None
) -> None:
    """
    根据预设配置添加植被痕迹。
    
    :param terrain: 地形对象
    :param preset_config: 地质预设配置
    :param asset_path: 资产路径
    """
    vegetation_density = preset_config.get('vegetation_density', 0.3)
    
    if vegetation_density < 0.2:
        # 低密度，跳过
        return
    
    print(f"Adding vegetation traces (density={vegetation_density})...")
    
    # 这里可以添加简单的植被几何体或纹理
    # 简化实现：调整地形材质的颜色混合，增加绿色成分
    
    terrain_material = terrain.get_materials()[0] if terrain.get_materials() else None
    if not terrain_material:
        return
    
    nodes = terrain_material.blender_obj.node_tree.nodes
    links = terrain_material.blender_obj.node_tree.links
    principled_bsdf = Utility.get_the_one_node_with_type(nodes, "BsdfPrincipled")
    
    # 添加绿色植被颜色混合
    grass_color = nodes.new(type='ShaderNodeRGB')
    grass_color.outputs['Color'].default_value = (0.4, 0.5, 0.3, 1.0)  # 绿色
    
    # 噪声纹理控制植被分布
    veg_noise = nodes.new(type='ShaderNodeTexNoise')
    veg_noise.inputs['Scale'].default_value = 2.0
    veg_noise.inputs['Detail'].default_value = 3.0
    
    tex_coord = nodes.new(type='ShaderNodeTexCoord')
    links.new(tex_coord.outputs['Generated'], veg_noise.inputs['Vector'])
    
    # 混合植被颜色
    veg_mix = nodes.new(type='ShaderNodeMixRGB')
    veg_mix.inputs['Fac'].default_value = vegetation_density * 0.3  # 30%最大混合
    links.new(veg_noise.outputs['Fac'], veg_mix.inputs['Fac'])
    links.new(grass_color.outputs['Color'], veg_mix.inputs['Color1'])
    
    # 连接到基础颜色
    base_color_input = principled_bsdf.inputs['Base Color']
    if len(base_color_input.links) > 0:
        existing_color = base_color_input.links[0].from_socket
        links.new(existing_color, veg_mix.inputs['Color2'])
        links.remove(base_color_input.links[0])
    else:
        veg_mix.inputs['Color2'].default_value = preset_config.get('terrain_color', (0.6, 0.5, 0.4, 1.0))
    
    links.new(veg_mix.outputs['Color'], base_color_input)
    
    print(f"  Added vegetation traces to terrain")

