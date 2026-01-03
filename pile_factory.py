"""
High-Fidelity Pile Asset Factory
基于《光伏板桩特征调研报告》的桩基资产生成模块

参考标准：
- GB 50797-2012《光伏发电站设计规范》
- 表 5.1 和 表 3-1 中的物理参数
"""

import blenderproc as bproc
import numpy as np
import bpy
import mathutils
from typing import Optional, Tuple, Literal
from pathlib import Path
from blenderproc.python.utility.Utility import Utility


# 全局缓存：避免重复加载材质
_CONCRETE_TEXTURE_CACHE = None


def load_concrete_texture(asset_path: Optional[str], print_found: bool = True) -> Optional[dict]:
    """
    加载混凝土纹理（带缓存）。
    
    :param asset_path: 资产路径
    :param print_found: 是否打印找到信息
    :return: 纹理字典或None
    """
    global _CONCRETE_TEXTURE_CACHE
    
    if _CONCRETE_TEXTURE_CACHE is not None:
        return _CONCRETE_TEXTURE_CACHE
    
    if not asset_path:
        return None
    
    base_path = Path(asset_path)
    # 查找混凝土纹理（concrete047A 或其他）
    concrete_folders = list(base_path.glob("*concrete*_4K-JPG")) + \
                       list(base_path.glob("*Concrete*_4K-JPG"))
    
    if not concrete_folders:
        return None
    
    folder = concrete_folders[0]
    textures = {}
    
    folder_name = folder.name
    color_file = folder / f"{folder_name}_Color.jpg"
    normal_file = folder / f"{folder_name}_NormalGL.jpg"
    roughness_file = folder / f"{folder_name}_Roughness.jpg"
    
    if color_file.exists():
        textures['color'] = color_file
    if normal_file.exists():
        textures['normal'] = normal_file
    if roughness_file.exists():
        textures['roughness'] = roughness_file
    
    if textures:
        _CONCRETE_TEXTURE_CACHE = textures
        if print_found:
            print(f"  Loaded concrete texture: {folder_name}")
        return textures
    
    return None


def create_phc_pile(
    location: np.ndarray,
    diameter: Literal[300, 400, 500] = 400,
    exposed_height: float = 0.4,
    age_state: Literal["new", "aged"] = "new",
    has_hoop_clamp: bool = True,
    has_cracked_top: bool = False,
    asset_path: Optional[str] = None
) -> Tuple[bproc.types.MeshObject, Optional[bproc.types.MeshObject]]:
    """
    创建PHC管桩（预应力高强混凝土管桩）。
    
    参考报告：直径300mm/400mm/500mm，壁厚70mm，露出地面300-500mm
    
    :param location: 位置 [x, y, z_base]（z_base是桩底位置）
    :param diameter: 外径（mm，转换为米）
    :param exposed_height: 露出地面高度（m）
    :param age_state: 老化状态："new"（新桩，灰白）或"aged"（陈旧，深灰有裂纹）
    :param has_hoop_clamp: 是否包含抱箍结构（金属材质环绕）
    :param has_cracked_top: 是否包含破碎切口（不规则的粗糙顶面）
    :param asset_path: 资产路径（用于加载混凝土纹理）
    :return: (主桩对象, 抱箍对象或None)
    """
    # 转换为米
    outer_radius = (diameter / 1000.0) / 2.0
    wall_thickness = 0.07  # 70mm壁厚
    inner_radius = outer_radius - wall_thickness
    
    # 总高度：入土深度 + 露出高度（假设入土1.5m，可根据需要调整）
    total_height = 1.5 + exposed_height
    
    # 创建空心圆柱（外圆柱减去内圆柱）
    # 方法：创建外圆柱，然后使用布尔修改器减去内圆柱
    outer_cylinder = bproc.object.create_primitive(
        "CYLINDER",
        radius=outer_radius,
        depth=total_height
    )
    
    # 创建内圆柱（用于布尔运算）
    inner_cylinder = bproc.object.create_primitive(
        "CYLINDER",
        radius=inner_radius,
        depth=total_height * 1.1  # 稍长以确保完全切除
    )
    inner_cylinder.set_location(location)
    inner_cylinder.blender_obj.hide_render = True
    inner_cylinder.blender_obj.hide_set(True)
    
    # 设置外圆柱位置（底部在location的z）
    outer_cylinder.set_location([
        location[0],
        location[1],
        location[2] + total_height / 2.0
    ])
    
    # 使用布尔修改器创建空心
    try:
        bpy.context.view_layer.objects.active = outer_cylinder.blender_obj
        bpy.ops.object.modifier_add(type='BOOLEAN')
        outer_cylinder.blender_obj.modifiers[-1].name = "Hollow"
        outer_cylinder.blender_obj.modifiers[-1].operation = 'DIFFERENCE'
        outer_cylinder.blender_obj.modifiers[-1].object = inner_cylinder.blender_obj
        bpy.ops.object.modifier_apply(modifier="Hollow")
    except Exception as e:
        print(f"Warning: Could not create hollow cylinder for PHC pile: {e}")
        # 如果布尔失败，使用实心圆柱作为后备
        pass
    
    # 删除内圆柱（不再需要）
    bpy.data.objects.remove(inner_cylinder.blender_obj, do_unlink=True)
    
    outer_cylinder.blender_obj.hide_set(False)
    outer_cylinder.blender_obj.hide_render = False
    outer_cylinder.add_uv_mapping("smart")
    
    # 创建混凝土材质
    pile_material = outer_cylinder.new_material("phc_pile_material")
    nodes = pile_material.blender_obj.node_tree.nodes
    links = pile_material.blender_obj.node_tree.links
    principled_bsdf = Utility.get_the_one_node_with_type(nodes, "BsdfPrincipled")
    
    # 根据老化状态设置颜色（参考报告表）
    if age_state == "new":
        # 新桩：灰白色(200, 200, 200)
        base_color = (0.78, 0.78, 0.78, 1.0)  # RGB 200/255
        roughness = 0.3  # 光滑，模板印痕
    else:
        # 陈旧桩：深灰(120, 120, 120)，有裂纹
        base_color = (0.47, 0.47, 0.47, 1.0)  # RGB 120/255
        roughness = 0.7  # 粗糙，风化
    
    # 尝试加载混凝土纹理
    concrete_texture = load_concrete_texture(asset_path, print_found=False)
    
    if concrete_texture and concrete_texture.get('color'):
        # 使用纹理
        tex_coord = nodes.new(type='ShaderNodeTexCoord')
        mapping = nodes.new(type='ShaderNodeMapping')
        mapping.inputs['Scale'].default_value = (2.0, 2.0, 2.0)
        links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
        
        color_tex = nodes.new(type='ShaderNodeTexImage')
        color_tex.image = bpy.data.images.load(str(concrete_texture['color']))
        links.new(mapping.outputs['Vector'], color_tex.inputs['Vector'])
        
        # 混合纹理和基础颜色
        mix = nodes.new(type='ShaderNodeMixRGB')
        mix.inputs['Fac'].default_value = 0.7  # 70%纹理，30%基础色
        links.new(color_tex.outputs['Color'], mix.inputs['Color1'])
        mix.inputs['Color2'].default_value = base_color
        links.new(mix.outputs['Color'], principled_bsdf.inputs['Base Color'])
        
        # 添加法线贴图
        if concrete_texture.get('normal'):
            normal_tex = nodes.new(type='ShaderNodeTexImage')
            normal_tex.image = bpy.data.images.load(str(concrete_texture['normal']))
            normal_tex.image.colorspace_settings.name = 'Non-Color'
            links.new(mapping.outputs['Vector'], normal_tex.inputs['Vector'])
            
            normal_map = nodes.new(type='ShaderNodeNormalMap')
            links.new(normal_tex.outputs['Color'], normal_map.inputs['Color'])
            links.new(normal_map.outputs['Normal'], principled_bsdf.inputs['Normal'])
        
        # 粗糙度
        if concrete_texture.get('roughness'):
            rough_tex = nodes.new(type='ShaderNodeTexImage')
            rough_tex.image = bpy.data.images.load(str(concrete_texture['roughness']))
            rough_tex.image.colorspace_settings.name = 'Non-Color'
            links.new(mapping.outputs['Vector'], rough_tex.inputs['Vector'])
            links.new(rough_tex.outputs['Color'], principled_bsdf.inputs['Roughness'])
        else:
            pile_material.set_principled_shader_value("Roughness", roughness)
    else:
        # 无纹理，使用纯色
        pile_material.set_principled_shader_value("Base Color", base_color)
        pile_material.set_principled_shader_value("Roughness", roughness)
    
    pile_material.set_principled_shader_value("Metallic", 0.0)
    
    # 添加破碎顶面（如果启用）
    if has_cracked_top:
        # 在顶部添加不规则的粗糙面
        # 使用细分和随机顶点位移模拟
        try:
            bpy.context.view_layer.objects.active = outer_cylinder.blender_obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            
            # 选择顶部面
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            
            # 使用修改器添加噪声
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.modifier_add(type='DISPLACE')
            noise_tex = bpy.data.textures.new(name="CrackNoise", type='CLOUDS')
            noise_tex.noise_scale = 0.1
            outer_cylinder.blender_obj.modifiers[-1].texture = noise_tex
            outer_cylinder.blender_obj.modifiers[-1].strength = 0.02  # 轻微位移
            outer_cylinder.blender_obj.modifiers[-1].mid_level = 0.5
        except Exception as e:
            print(f"Warning: Could not add cracked top: {e}")
    
    # 创建抱箍（如果启用）
    hoop_obj = None
    if has_hoop_clamp:
        # 抱箍：金属材质，环绕桩顶
        hoop_height = 0.05  # 5cm高
        hoop_radius = outer_radius + 0.01  # 略大于桩半径
        
        hoop = bproc.object.create_primitive(
            "CYLINDER",
            radius=hoop_radius,
            depth=hoop_height
        )
        hoop.set_location([
            location[0],
            location[1],
            location[2] + total_height - hoop_height / 2.0  # 在顶部
        ])
        
        # 金属材质（镀锌钢）
        hoop_material = hoop.new_material("hoop_clamp_material")
        hoop_material.set_principled_shader_value("Base Color", (0.7, 0.7, 0.75, 1.0))  # 银灰色
        hoop_material.set_principled_shader_value("Metallic", 0.9)
        hoop_material.set_principled_shader_value("Roughness", 0.2)
        
        hoop.blender_obj.hide_set(False)
        hoop.blender_obj.hide_render = False
        hoop.set_cp("category_id", 0)  # 与桩相同类别
        hoop_obj = hoop
    
    outer_cylinder.set_cp("category_id", 0)
    outer_cylinder.set_name(f"PHC_Pile_{diameter}mm")
    
    return outer_cylinder, hoop_obj


def create_spiral_steel_pile(
    location: np.ndarray,
    pipe_diameter: Literal[76, 89, 114, 159] = 89,
    total_length: float = 2.0,
    exposed_height: float = 0.3,
    rust_level: Literal["new", "light", "medium", "heavy"] = "new",
    asset_path: Optional[str] = None
) -> Tuple[bproc.types.MeshObject, bproc.types.MeshObject]:
    """
    创建螺旋钢桩。
    
    参考报告：钢管直径76/89/114/159mm，壁厚3-5mm，顶部焊接圆形法兰盘（直径220mm，厚10mm）
    热镀锌钢，支持锈蚀程度调节
    
    :param location: 位置 [x, y, z_base]
    :param pipe_diameter: 钢管直径（mm）
    :param total_length: 总长度（m）
    :param exposed_height: 露出地面高度（m）
    :param rust_level: 锈蚀程度："new"（新桩，银灰光泽）、"light"（3-6月，浅灰）、"medium"（1-2年，锈斑）、"heavy"（2年+，深锈）
    :param asset_path: 资产路径
    :return: (钢管对象, 法兰盘对象)
    """
    # 转换为米
    pipe_radius = (pipe_diameter / 1000.0) / 2.0
    wall_thickness = 0.004  # 4mm壁厚
    
    # 创建钢管（实心圆柱，后续可改为空心）
    pipe = bproc.object.create_primitive(
        "CYLINDER",
        radius=pipe_radius,
        depth=total_length
    )
    pipe.set_location([
        location[0],
        location[1],
        location[2] + total_length / 2.0
    ])
    pipe.blender_obj.hide_set(False)
    pipe.blender_obj.hide_render = False
    pipe.add_uv_mapping("smart")
    
    # 创建螺旋叶片（简化：使用环形几何体）
    # 实际螺旋叶片需要更复杂的建模，这里用环形代替
    spiral_outer_radius = pipe_radius * 4.0  # 叶片外径约为管径的4倍
    spiral_thickness = 0.005  # 5mm厚
    
    # 创建多个螺旋环（1.5-3圈）
    num_rings = 2
    spiral_rings = []
    for i in range(num_rings):
        ring = bproc.object.create_primitive(
            "TORUS",
            major_radius=spiral_outer_radius,
            minor_radius=spiral_thickness / 2.0
        )
        ring_height = (i + 0.5) * (total_length / num_rings)
        ring.set_location([
            location[0],
            location[1],
            location[2] + ring_height
        ])
        ring.set_rotation_euler([np.pi / 2, 0, 0])  # 旋转为水平
        ring.blender_obj.hide_set(False)
        ring.blender_obj.hide_render = False
        spiral_rings.append(ring)
    
    # 创建法兰盘（顶部）
    flange_diameter = 0.22  # 220mm
    flange_thickness = 0.01  # 10mm
    flange = bproc.object.create_primitive(
        "CYLINDER",
        radius=flange_diameter / 2.0,
        depth=flange_thickness
    )
    flange.set_location([
        location[0],
        location[1],
        location[2] + total_length - flange_thickness / 2.0
    ])
    flange.blender_obj.hide_set(False)
    flange.blender_obj.hide_render = False
    
    # 热镀锌钢材质（根据锈蚀程度）
    if rust_level == "new":
        # 新桩：银灰金属光泽(180, 180, 180)
        base_color = (0.71, 0.71, 0.71, 1.0)
        metallic = 0.95
        roughness = 0.1  # 高光泽
    elif rust_level == "light":
        # 3-6月：浅灰(160, 160, 160)，镀锌层轻微氧化
        base_color = (0.63, 0.63, 0.63, 1.0)
        metallic = 0.85
        roughness = 0.2
    elif rust_level == "medium":
        # 1-2年：锈蚀初期(139, 90, 43)，局部红褐色锈斑
        base_color = (0.55, 0.35, 0.17, 1.0)
        metallic = 0.6
        roughness = 0.5
    else:  # heavy
        # 2年+：深锈色(100, 60, 30)，镀锌层大面积失效
        base_color = (0.39, 0.24, 0.12, 1.0)
        metallic = 0.3
        roughness = 0.8
    
    # 钢管材质
    pipe_material = pipe.new_material("spiral_steel_pipe_material")
    pipe_material.set_principled_shader_value("Base Color", base_color)
    pipe_material.set_principled_shader_value("Metallic", metallic)
    pipe_material.set_principled_shader_value("Roughness", roughness)
    
    # 螺旋环和法兰盘使用相同材质
    for ring in spiral_rings:
        ring_material = ring.new_material("spiral_ring_material")
        ring_material.set_principled_shader_value("Base Color", base_color)
        ring_material.set_principled_shader_value("Metallic", metallic)
        ring_material.set_principled_shader_value("Roughness", roughness)
        ring.set_cp("category_id", 0)
    
    flange_material = flange.new_material("flange_material")
    flange_material.set_principled_shader_value("Base Color", base_color)
    flange_material.set_principled_shader_value("Metallic", metallic)
    flange_material.set_principled_shader_value("Roughness", roughness)
    
    pipe.set_cp("category_id", 0)
    flange.set_cp("category_id", 0)
    pipe.set_name(f"SpiralSteelPile_{pipe_diameter}mm")
    
    return pipe, flange


def create_cast_in_place_pile(
    location: np.ndarray,
    diameter: float = 0.3,  # 300mm
    total_length: float = 2.0,
    exposed_height: float = 0.3,
    has_spiral_marks: bool = True,
    has_leakage: bool = False,
    asset_path: Optional[str] = None
) -> bproc.types.MeshObject:
    """
    创建灌注桩。
    
    参考报告：直径300mm，表面需生成螺旋状的模具痕迹（纸筒模具特征）
    底部与地面接触处可能有"漏浆结块"或不规则扩径
    
    :param location: 位置 [x, y, z_base]
    :param diameter: 直径（m）
    :param total_length: 总长度（m）
    :param exposed_height: 露出地面高度（m）
    :param has_spiral_marks: 是否包含螺旋模具痕迹
    :param has_leakage: 是否在底部有漏浆结块
    :param asset_path: 资产路径
    :return: 桩对象
    """
    radius = diameter / 2.0
    
    # 创建主桩体
    pile = bproc.object.create_primitive(
        "CYLINDER",
        radius=radius,
        depth=total_length
    )
    pile.set_location([
        location[0],
        location[1],
        location[2] + total_length / 2.0
    ])
    pile.blender_obj.hide_set(False)
    pile.blender_obj.hide_render = False
    pile.add_uv_mapping("smart")
    
    # 添加螺旋模具痕迹（使用修改器）
    if has_spiral_marks:
        try:
            bpy.context.view_layer.objects.active = pile.blender_obj
            # 使用数组修改器创建螺旋效果
            bpy.ops.object.modifier_add(type='ARRAY')
            # 或者使用纹理坐标创建螺旋纹理
            # 这里简化：使用法线贴图模拟螺旋痕迹
        except Exception as e:
            print(f"Warning: Could not add spiral marks: {e}")
    
    # 添加漏浆结块（底部不规则扩径）
    if has_leakage:
        try:
            # 在底部创建不规则的结块
            leakage = bproc.object.create_primitive(
                "ICOSPHERE",
                subdivisions=2,
                radius=radius * 1.3  # 略大于桩径
            )
            # 随机缩放和变形
            leakage.set_location([
                location[0] + np.random.uniform(-0.05, 0.05),
                location[1] + np.random.uniform(-0.05, 0.05),
                location[2] + 0.1  # 在底部
            ])
            leakage.set_scale([
                np.random.uniform(0.8, 1.2),
                np.random.uniform(0.8, 1.2),
                np.random.uniform(0.5, 0.8)
            ])
            leakage.blender_obj.hide_set(False)
            leakage.blender_obj.hide_render = False
            
            # 漏浆材质（深色混凝土）
            leakage_material = leakage.new_material("leakage_material")
            leakage_material.set_principled_shader_value("Base Color", (0.3, 0.3, 0.3, 1.0))
            leakage_material.set_principled_shader_value("Roughness", 0.9)
            leakage_material.set_principled_shader_value("Metallic", 0.0)
            leakage.set_cp("category_id", 0)  # 与桩相同
        except Exception as e:
            print(f"Warning: Could not add leakage: {e}")
    
    # 混凝土材质（C30，新浇筑灰白色）
    pile_material = pile.new_material("cast_in_place_pile_material")
    nodes = pile_material.blender_obj.node_tree.nodes
    links = pile_material.blender_obj.node_tree.links
    principled_bsdf = Utility.get_the_one_node_with_type(nodes, "BsdfPrincipled")
    
    # 新浇筑：灰白色(210, 210, 210)
    base_color = (0.82, 0.82, 0.82, 1.0)
    
    # 尝试加载混凝土纹理
    concrete_texture = load_concrete_texture(asset_path, print_found=False)
    
    if concrete_texture and concrete_texture.get('color'):
        tex_coord = nodes.new(type='ShaderNodeTexCoord')
        mapping = nodes.new(type='ShaderNodeMapping')
        mapping.inputs['Scale'].default_value = (3.0, 3.0, 3.0)  # 螺旋纹理需要更细的缩放
        links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
        
        color_tex = nodes.new(type='ShaderNodeTexImage')
        color_tex.image = bpy.data.images.load(str(concrete_texture['color']))
        links.new(mapping.outputs['Vector'], color_tex.inputs['Vector'])
        
        # 混合
        mix = nodes.new(type='ShaderNodeMixRGB')
        mix.inputs['Fac'].default_value = 0.6
        links.new(color_tex.outputs['Color'], mix.inputs['Color1'])
        mix.inputs['Color2'].default_value = base_color
        links.new(mix.outputs['Color'], principled_bsdf.inputs['Base Color'])
        
        # 法线贴图（模拟螺旋痕迹）
        if concrete_texture.get('normal'):
            normal_tex = nodes.new(type='ShaderNodeTexImage')
            normal_tex.image = bpy.data.images.load(str(concrete_texture['normal']))
            normal_tex.image.colorspace_settings.name = 'Non-Color'
            links.new(mapping.outputs['Vector'], normal_tex.inputs['Vector'])
            
            normal_map = nodes.new(type='ShaderNodeNormalMap')
            links.new(normal_tex.outputs['Color'], normal_map.inputs['Color'])
            links.new(normal_map.outputs['Normal'], principled_bsdf.inputs['Normal'])
    else:
        pile_material.set_principled_shader_value("Base Color", base_color)
    
    pile_material.set_principled_shader_value("Roughness", 0.6)
    pile_material.set_principled_shader_value("Metallic", 0.0)
    
    pile.set_cp("category_id", 0)
    pile.set_name("CastInPlacePile_300mm")
    
    return pile


def create_pile_variant(
    pile_type: Literal["PHC", "spiral_steel", "cast_in_place"],
    location: np.ndarray,
    terrain_z: float,
    **kwargs
) -> Tuple[bproc.types.MeshObject, Optional[bproc.types.MeshObject]]:
    """
    统一的桩基创建接口，根据类型调用相应的创建函数。
    
    :param pile_type: 桩基类型
    :param location: 2D位置 [x, y]（Z由terrain_z提供）
    :param terrain_z: 地形高度
    :param kwargs: 其他参数（传递给具体创建函数）
    :return: (主桩对象, 附件对象或None)
    """
    final_location = np.array([location[0], location[1], terrain_z])
    
    if pile_type == "PHC":
        diameter = kwargs.get('diameter', 400)
        exposed_height = kwargs.get('exposed_height', 0.4)
        age_state = kwargs.get('age_state', "new")
        has_hoop = kwargs.get('has_hoop_clamp', True)
        has_cracked = kwargs.get('has_cracked_top', False)
        asset_path = kwargs.get('asset_path')
        
        return create_phc_pile(
            final_location,
            diameter=diameter,
            exposed_height=exposed_height,
            age_state=age_state,
            has_hoop_clamp=has_hoop,
            has_cracked_top=has_cracked,
            asset_path=asset_path
        )
    
    elif pile_type == "spiral_steel":
        pipe_diameter = kwargs.get('pipe_diameter', 89)
        total_length = kwargs.get('total_length', 2.0)
        exposed_height = kwargs.get('exposed_height', 0.3)
        rust_level = kwargs.get('rust_level', "new")
        asset_path = kwargs.get('asset_path')
        
        return create_spiral_steel_pile(
            final_location,
            pipe_diameter=pipe_diameter,
            total_length=total_length,
            exposed_height=exposed_height,
            rust_level=rust_level,
            asset_path=asset_path
        )
    
    elif pile_type == "cast_in_place":
        diameter = kwargs.get('diameter', 0.3)
        total_length = kwargs.get('total_length', 2.0)
        exposed_height = kwargs.get('exposed_height', 0.3)
        has_spiral = kwargs.get('has_spiral_marks', True)
        has_leakage = kwargs.get('has_leakage', False)
        asset_path = kwargs.get('asset_path')
        
        pile = create_cast_in_place_pile(
            final_location,
            diameter=diameter,
            total_length=total_length,
            exposed_height=exposed_height,
            has_spiral_marks=has_spiral,
            has_leakage=has_leakage,
            asset_path=asset_path
        )
        return pile, None
    
    else:
        raise ValueError(f"Unknown pile type: {pile_type}")

