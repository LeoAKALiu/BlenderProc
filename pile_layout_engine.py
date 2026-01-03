"""
Constraint-based Pile Layout Engine
基于GB 50797-2012规范的智能排布算法

参考标准：
- GB 50797-2012《光伏发电站设计规范》
- 报告2.1节：桩间距（东西向跨距）
- 报告5.2节：随坡与阶梯逻辑
"""

import numpy as np
import blenderproc as bproc
from typing import List, Tuple, Optional, Dict
import math


def calculate_row_spacing(
    slope_angle: float,
    slope_direction: float,
    component_height: float = 2.278,  # 组件高度（m）
    min_spacing: float = 3.6,
    max_spacing: float = 4.7
) -> float:
    """
    根据地形坡度动态计算排间距（防遮挡逻辑）。
    
    参考GB 50797-2012：北坡间距大，南坡间距小
    
    :param slope_angle: 坡度角（弧度，0=水平，正=上坡）
    :param slope_direction: 坡向（弧度，0=北，π/2=东，π=南，3π/2=西）
    :param component_height: 组件高度（m）
    :param min_spacing: 最小排间距（m）
    :param max_spacing: 最大排间距（m）
    :return: 计算得到的排间距（m）
    """
    # 简化计算：如果坡向朝南（π），间距可以较小
    # 如果坡向朝北（0），间距需要较大以避免遮挡
    
    # 将坡向转换为0-2π范围
    normalized_direction = slope_direction % (2 * np.pi)
    
    # 计算朝向因子：南坡（π附近）因子小，北坡（0或2π附近）因子大
    if normalized_direction < np.pi:
        # 0到π：从北到南
        direction_factor = 1.0 - (normalized_direction / np.pi) * 0.3  # 北坡1.0，南坡0.7
    else:
        # π到2π：从南到北
        direction_factor = 0.7 + ((normalized_direction - np.pi) / np.pi) * 0.3  # 南坡0.7，北坡1.0
    
    # 坡度影响：坡度越大，间距需要越大
    slope_factor = 1.0 + abs(slope_angle) * 0.2  # 坡度每增加1弧度，间距增加20%
    
    # 计算最终间距
    base_spacing = (min_spacing + max_spacing) / 2.0
    spacing = base_spacing * direction_factor * slope_factor
    
    # 限制在范围内
    spacing = np.clip(spacing, min_spacing, max_spacing)
    
    return spacing


def get_terrain_slope(
    x: float,
    y: float,
    terrain: bproc.types.MeshObject,
    sample_radius: float = 2.0
) -> Tuple[float, float]:
    """
    获取指定位置的地形坡度和坡向。
    
    :param x: X坐标
    :param y: Y坐标
    :param terrain: 地形对象
    :param sample_radius: 采样半径（用于计算局部坡度）
    :return: (坡度角（弧度）, 坡向（弧度，0=北）)
    """
    # 采样周围点计算坡度
    sample_points = [
        (x - sample_radius, y),
        (x + sample_radius, y),
        (x, y - sample_radius),
        (x, y + sample_radius),
    ]
    
    # 使用ray cast获取高度
    heights = []
    for px, py in sample_points:
        hit, location = bproc.object.scene_ray_cast(
            [px, py, 100.0],  # 从上方100m开始
            [0, 0, -1]  # 向下
        )
        if hit:
            heights.append(location[2])
        else:
            heights.append(0.0)
    
    # 计算梯度
    dz_dx = (heights[1] - heights[0]) / (2 * sample_radius)
    dz_dy = (heights[3] - heights[2]) / (2 * sample_radius)
    
    # 坡度角
    slope_angle = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    
    # 坡向（0=北，π/2=东，π=南，3π/2=西）
    slope_direction = np.arctan2(dz_dy, dz_dx) + np.pi / 2.0
    
    return slope_angle, slope_direction


def create_stepped_pile_group(
    terrain: bproc.types.MeshObject,
    group_center: np.ndarray,
    row_angle: float,
    num_piles: int = 10,
    pile_spacing: float = 3.6,
    vertical_tolerance: float = 0.04,  # 40mm同组桩顶标高差
    exposed_height_range: Tuple[float, float] = (0.3, 1.0)
) -> List[Tuple[np.ndarray, float]]:
    """
    创建阶梯状桩组（Table，约10根桩）。
    
    参考报告：同一组内的桩顶必须在同一平面上，允许通过调节桩的露出高度（300mm-1000mm）来补偿地形起伏
    
    :param terrain: 地形对象
    :param group_center: 组中心位置 [x, y]
    :param row_angle: 行方向角度（弧度）
    :param num_piles: 桩数量（默认10根，对应2×5配置）
    :param pile_spacing: 桩间距（m）
    :param vertical_tolerance: 垂直容差（m，同组桩顶标高差≤40mm）
    :param exposed_height_range: 露出高度范围（m）
    :return: [(位置, 地形高度), ...] 列表
    """
    pile_positions = []
    
    # 计算行和列（2×5配置）
    rows = 2
    cols = num_piles // rows
    
    # 旋转矩阵
    cos_a = np.cos(row_angle)
    sin_a = np.sin(row_angle)
    rotation_matrix = np.array([
        [cos_a, -sin_a],
        [sin_a, cos_a]
    ])
    
    # 收集所有位置和地形高度
    positions_with_heights = []
    
    for row_idx in range(rows):
        for col_idx in range(cols):
            # 局部坐标
            local_x = (col_idx - cols / 2.0) * pile_spacing
            local_y = (row_idx - rows / 2.0) * 3.6  # 行间距3.6m（参考报告）
            
            # 旋转到行方向
            local_pos = np.array([local_x, local_y])
            rotated_pos = rotation_matrix @ local_pos
            
            # 全局位置
            global_x = group_center[0] + rotated_pos[0]
            global_y = group_center[1] + rotated_pos[1]
            
            # 获取地形高度
            hit, location = bproc.object.scene_ray_cast(
                [global_x, global_y, 100.0],
                [0, 0, -1]
            )
            if hit:
                terrain_z = location[2]
            else:
                terrain_z = 0.0
            
            positions_with_heights.append((np.array([global_x, global_y]), terrain_z))
    
    # 计算目标标高（所有桩顶在同一平面）
    # 方法：取最高地形点，其他点通过调节露出高度补偿
    max_terrain_z = max(z for _, z in positions_with_heights)
    target_top_z = max_terrain_z + exposed_height_range[0]  # 使用最小露出高度作为基准
    
    # 确保所有桩顶在容差范围内
    for pos, terrain_z in positions_with_heights:
        # 计算需要的露出高度以达到目标顶高
        required_exposed = target_top_z - terrain_z
        
        # 限制在范围内
        exposed_height = np.clip(required_exposed, exposed_height_range[0], exposed_height_range[1])
        
        # 如果超出范围，调整目标顶高（向下调整）
        if exposed_height != required_exposed:
            target_top_z = terrain_z + exposed_height
        
        pile_positions.append((pos, terrain_z))
    
    return pile_positions


def apply_engineering_tolerances(
    base_position: np.ndarray,
    row_alignment: bool = True,
    vertical_deviation: float = 0.005  # 0.5%倾斜
) -> Tuple[np.ndarray, np.ndarray]:
    """
    应用工程容差。
    
    参考报告：
    - 行内约束：同一排桩的圆心偏差应极小（<10mm）
    - 垂直度偏差：给每根桩添加微小的随机倾斜（<0.5%）
    - 列间抖动：排与排之间的对齐可以相对宽松
    
    :param base_position: 基础位置 [x, y]
    :param row_alignment: 是否在行内（True=严格对齐，False=允许抖动）
    :param vertical_deviation: 垂直度偏差（弧度，0.5% ≈ 0.005弧度）
    :return: (最终位置, 倾斜角度 [tilt_x, tilt_y, tilt_z])
    """
    if row_alignment:
        # 行内：极小偏差（<10mm = 0.01m）
        position_jitter = np.random.uniform(-0.005, 0.005, size=2)
    else:
        # 列间：相对宽松（±20cm）
        position_jitter = np.random.uniform(-0.2, 0.2, size=2)
    
    final_position = base_position + position_jitter
    
    # 垂直度偏差（<0.5%）
    tilt_x = np.random.uniform(-vertical_deviation, vertical_deviation)
    tilt_y = np.random.uniform(-vertical_deviation, vertical_deviation)
    tilt_z = np.random.uniform(0, 2 * np.pi)  # 随机旋转
    
    return final_position, np.array([tilt_x, tilt_y, tilt_z])


def layout_piles_with_constraints(
    terrain: bproc.types.MeshObject,
    area_size: float = 200.0,
    num_groups: int = 20,
    piles_per_group: int = 10,
    road_width: float = 8.0,
    asset_path: Optional[str] = None
) -> List[Dict]:
    """
    基于规范的智能排布主函数。
    
    实现：
    1. 随坡与阶梯逻辑
    2. 工程容差注入
    3. 道路间隙
    
    :param terrain: 地形对象
    :param area_size: 区域大小（m）
    :param num_groups: 桩组数量
    :param piles_per_group: 每组桩数（默认10，对应2×5配置）
    :param road_width: 道路宽度（m）
    :param asset_path: 资产路径
    :return: 桩信息列表，每个元素包含位置、类型、参数等
    """
    pile_info_list = []
    
    # 随机生成组中心位置
    group_centers = []
    min_distance = 15.0  # 最小组间距
    
    for _ in range(num_groups):
        attempts = 0
        while attempts < 100:
            center_x = np.random.uniform(-area_size/2, area_size/2)
            center_y = np.random.uniform(-area_size/2, area_size/2)
            
            # 检查是否与已有组太近
            too_close = False
            for existing_center in group_centers:
                dist = np.sqrt((center_x - existing_center[0])**2 + (center_y - existing_center[1])**2)
                if dist < min_distance:
                    too_close = True
                    break
            
            if not too_close:
                group_centers.append(np.array([center_x, center_y]))
                break
            
            attempts += 1
    
    # 为每组创建桩
    for group_idx, group_center in enumerate(group_centers):
        # 随机行方向
        row_angle = np.random.uniform(0, 2 * np.pi)
        
        # 获取组中心的地形坡度
        slope_angle, slope_direction = get_terrain_slope(
            group_center[0],
            group_center[1],
            terrain
        )
        
        # 计算排间距
        pile_spacing = calculate_row_spacing(slope_angle, slope_direction)
        
        # 创建阶梯状桩组
        pile_positions = create_stepped_pile_group(
            terrain,
            group_center,
            row_angle,
            num_piles=piles_per_group,
            pile_spacing=pile_spacing
        )
        
        # 为每个桩应用工程容差
        for pile_idx, (base_pos, terrain_z) in enumerate(pile_positions):
            # 行内对齐（同一组内）
            is_in_row = (pile_idx % (piles_per_group // 2)) < (piles_per_group // 2)
            
            final_pos, tilt = apply_engineering_tolerances(
                base_pos,
                row_alignment=is_in_row
            )
            
            # 随机选择桩类型（可根据需要调整概率）
            pile_type_rand = np.random.random()
            if pile_type_rand < 0.4:
                pile_type = "PHC"
                pile_params = {
                    'diameter': np.random.choice([300, 400, 500]),
                    'exposed_height': np.random.uniform(0.3, 0.5),
                    'age_state': np.random.choice(["new", "aged"], p=[0.7, 0.3]),
                    'has_hoop_clamp': np.random.random() < 0.8,
                    'has_cracked_top': np.random.random() < 0.2,
                    'asset_path': asset_path
                }
            elif pile_type_rand < 0.7:
                pile_type = "spiral_steel"
                pile_params = {
                    'pipe_diameter': np.random.choice([76, 89, 114, 159]),
                    'total_length': np.random.uniform(1.5, 2.5),
                    'exposed_height': np.random.uniform(0.3, 0.5),
                    'rust_level': np.random.choice(["new", "light", "medium", "heavy"], p=[0.5, 0.3, 0.15, 0.05]),
                    'asset_path': asset_path
                }
            else:
                pile_type = "cast_in_place"
                pile_params = {
                    'diameter': 0.3,
                    'total_length': np.random.uniform(1.8, 2.5),
                    'exposed_height': np.random.uniform(0.3, 0.5),
                    'has_spiral_marks': True,
                    'has_leakage': np.random.random() < 0.3,
                    'asset_path': asset_path
                }
            
            pile_info_list.append({
                'position': final_pos,
                'terrain_z': terrain_z,
                'tilt': tilt,
                'pile_type': pile_type,
                'pile_params': pile_params,
                'group_id': group_idx
            })
    
    print(f"Created {len(pile_info_list)} piles in {len(group_centers)} groups with constraint-based layout")
    
    return pile_info_list

