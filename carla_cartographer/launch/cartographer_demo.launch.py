import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetRemap
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    """
    启动 CARLA ROS Bridge 和 Cartographer 进行 2D 建图。
    
    主要功能：
    1. 启动 CARLA ROS Bridge，并重映射其 TF 发布，避免与 Cartographer 冲突。
    2. 发布必要的静态 TF 变换 (Lidar, IMU, Map->Odom)。
    3. 生成并生成 ego_vehicle。
    4. 启动手动控制节点。
    5. 启动 odom_to_tf 节点，转换里程计数据。
    6. 启动 Cartographer 和 RViz。
    """

    # ========================================================================
    # 1. 参数配置
    # ========================================================================
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    town = LaunchConfiguration('town', default='Town05')
    map_resolution = LaunchConfiguration('map_resolution', default='0.05')
    
    # ========================================================================
    # 2. 路径获取
    # ========================================================================
    carla_cartographer_dir = get_package_share_directory('carla_cartographer')
    carla_ros_bridge_dir = get_package_share_directory('carla_ros_bridge')
    carla_spawn_objects_dir = get_package_share_directory('carla_spawn_objects')
    carla_manual_control_dir = get_package_share_directory('carla_manual_control')
    
    objects_definition_file = os.path.join(carla_cartographer_dir, 'config', 'objects_cartographer.json')
    cartographer_config_dir = os.path.join(carla_cartographer_dir, 'config')
    cartographer_config_basename = 'carla_2d.lua'
    rviz_config = os.path.join(carla_cartographer_dir, 'config', 'demo_2d.rviz')

    # ========================================================================
    # 3. 静态 TF 发布
    # ========================================================================
    
    # Lidar -> ego_vehicle (z=2.4m)
    lidar_tf_publisher = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='lidar_tf_publisher',
        arguments=['0', '0', '2.4', '0', '0', '0', 'ego_vehicle', 'ego_vehicle/lidar'],
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # IMU -> ego_vehicle (z=0m)
    imu_tf_publisher = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='imu_tf_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'ego_vehicle', 'ego_vehicle/imu'],
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # Map -> Odom (Identity)
    # 关键：由于我们在 carla_2d.lua 中禁用了 provide_odom_frame，
    # 我们需要手动连接 map 和 odom，使它们重合。
    # 这样小车就会显示在 CARLA 的绝对坐标位置上。
    map_to_odom_publisher = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='map_to_odom_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom'],
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # ========================================================================
    # 4. CARLA 节点 (Bridge, Spawn, Control)
    # ========================================================================

    # CARLA ROS Bridge
    # 使用 GroupAction 屏蔽 Bridge 发布的 TF，避免与 Cartographer 冲突
    carla_ros_bridge_launch_desc = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(carla_ros_bridge_dir, 'carla_ros_bridge.launch.py')
        ),
        launch_arguments={
            'town': town,
            'fixed_delta_seconds': '0.05',
            'ego_vehicle_role_name': 'ego_vehicle'
        }.items()
    )
    
    carla_ros_bridge_launch = GroupAction(
        actions=[
            SetRemap(src='/tf', dst='/tf_ignored'),
            SetRemap(src='/tf_static', dst='/tf_static_ignored'),
            carla_ros_bridge_launch_desc
        ]
    )

    # Spawn Objects (生成车辆)
    carla_spawn_objects_node = Node(
        package='carla_spawn_objects',
        executable='carla_spawn_objects',
        name='carla_spawn_objects',
        output='screen',
        parameters=[
            {'objects_definition_file': objects_definition_file},
            {'spawn_point_ego_vehicle': '-3.0, 14.3, 0.5, 0, 0, 0'},
            {'spawn_sensors_only': False}
        ]
    )

    carla_set_initial_pose_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(carla_spawn_objects_dir, 'set_initial_pose.launch.py')
        ),
        launch_arguments={
            'role_name': 'ego_vehicle'
        }.items()
    )

    # Manual Control (手动控制)
    carla_manual_control_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(carla_manual_control_dir, 'carla_manual_control.launch.py')
        ),
        launch_arguments={
            'role_name': 'ego_vehicle'
        }.items()
    )
    
    # Odom to TF (里程计转换)
    # 将 CARLA 的 /carla/ego_vehicle/odometry 转换为标准的 /odom 并发布 TF
    odom_to_tf_node = Node(
        package='carla_cartographer',
        executable='odom_to_tf.py',
        name='odom_to_tf',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )
    
    # ========================================================================
    # 5. Cartographer & RViz
    # ========================================================================
    
    cartographer_node = Node(
        package='cartographer_ros',
        executable='cartographer_node',
        name='cartographer_node',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            '-configuration_directory', cartographer_config_dir,
            '-configuration_basename', cartographer_config_basename
        ],
        remappings=[
            ('points2', '/carla/ego_vehicle/lidar'),
            ('imu', '/carla/ego_vehicle/imu'),
            ('odom', '/odom')
        ]
    )
    
    cartographer_occupancy_grid_node = Node(
        package='cartographer_ros',
        executable='cartographer_occupancy_grid_node',
        name='cartographer_occupancy_grid_node',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'resolution': map_resolution},
            {'publish_period_sec': 0.1}
        ]
    )
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen'
    )

    # 延迟启动 Cartographer，确保 TF 树已准备好
    delayed_cartographer_launch = TimerAction(
        period=10.0,
        actions=[
            cartographer_node,
            cartographer_occupancy_grid_node,
            rviz_node
        ]
    )
    
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('town', default_value='Town05'),
        DeclareLaunchArgument('map_resolution', default_value='0.05'),
        
        carla_ros_bridge_launch,
        lidar_tf_publisher,
        imu_tf_publisher,
        map_to_odom_publisher,
        carla_spawn_objects_node,
        carla_set_initial_pose_launch,
        carla_manual_control_launch,
        odom_to_tf_node,
        delayed_cartographer_launch,
    ])