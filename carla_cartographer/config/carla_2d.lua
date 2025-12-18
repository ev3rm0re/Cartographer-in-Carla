include "map_builder.lua"
include "trajectory_builder.lua"

options = {
  map_builder = MAP_BUILDER,
  trajectory_builder = TRAJECTORY_BUILDER,
  
  -- 坐标系配置
  map_frame = "map",              -- 全局地图坐标系
  tracking_frame = "ego_vehicle", -- 机器人中心坐标系（需与 TF 树一致）
  published_frame = "odom",       -- Cartographer 发布的坐标系（通常为 odom 或 map）
  odom_frame = "odom",            -- 里程计坐标系
  
  -- 关键配置：里程计模式
  provide_odom_frame = true,
  
  publish_frame_projected_to_2d = false,
  use_pose_extrapolator = true,   -- 使用位姿外推器平滑输出
  use_odometry = true,            -- 订阅 /odom 话题
  use_nav_sat = false,            -- 不使用 GPS
  use_landmarks = false,          -- 不使用地标
  
  -- 传感器配置
  num_laser_scans = 0,
  num_multi_echo_laser_scans = 0,
  num_subdivisions_per_laser_scan = 1,
  num_point_clouds = 1,           -- 订阅 1 个点云话题 (/points2)
  
  -- 系统参数
  lookup_transform_timeout_sec = 0.5,
  submap_publish_period_sec = 0.1,
  pose_publish_period_sec = 5e-2,
  trajectory_publish_period_sec = 30e-2,
  
  -- 采样比率（1.0 表示使用所有数据）
  rangefinder_sampling_ratio = 1.,
  odometry_sampling_ratio = 1.,
  fixed_frame_pose_sampling_ratio = 1.,
  imu_sampling_ratio = 1.,
  landmarks_sampling_ratio = 1.,
}

-- 2D SLAM 配置
MAP_BUILDER.use_trajectory_builder_2d = true

-- 激光雷达配置
TRAJECTORY_BUILDER_2D.submaps.num_range_data = 35
TRAJECTORY_BUILDER_2D.min_range = 0.3
TRAJECTORY_BUILDER_2D.max_range = 50.
TRAJECTORY_BUILDER_2D.missing_data_ray_length = 1.
TRAJECTORY_BUILDER_2D.num_accumulated_range_data = 2
TRAJECTORY_BUILDER_2D.min_z = 0.5
TRAJECTORY_BUILDER_2D.max_z = 3.5

-- IMU 配置
-- 在仿真环境中，如果 IMU 噪声过大或未正确校准，建议禁用
TRAJECTORY_BUILDER_2D.use_imu_data = false

-- 扫描匹配配置
TRAJECTORY_BUILDER_2D.use_online_correlative_scan_matching = true
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.linear_search_window = 0.1
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.translation_delta_cost_weight = 10.
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.rotation_delta_cost_weight = 1e-1

-- 运动过滤
TRAJECTORY_BUILDER_2D.motion_filter.max_angle_radians = math.rad(0.2)

return options
