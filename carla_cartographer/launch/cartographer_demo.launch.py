import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node, SetRemap
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # ========================================================================
    # 1. 参数配置 (定义读取变量)
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
    
    # 准备两个 JSON 文件的路径
    objects_file_clean = os.path.join(carla_cartographer_dir, 'config', 'objects_run1_clean.json')
    objects_file_noisy = os.path.join(carla_cartographer_dir, 'config', 'objects_run3_noisy.json')
    
    cartographer_config_dir = os.path.join(carla_cartographer_dir, 'config')
    cartographer_config_basename = 'carla_2d.lua'
    rviz_config = os.path.join(carla_cartographer_dir, 'config', 'demo_2d.rviz')

    # ========================================================================
    # 3. CARLA 节点
    # ========================================================================
    carla_ros_bridge_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(carla_ros_bridge_dir, 'carla_ros_bridge.launch.py')
        ),
        launch_arguments={
            'town': town,
            'fixed_delta_seconds': '0.05',
            'ego_vehicle_role_name': 'ego_vehicle'
        }.items()
    )

    # 动态选择 JSON 文件
    chosen_objects_file = PythonExpression([
        "'", objects_file_clean, "' if '", LaunchConfiguration('enable_c2'), 
        "' == 'true' else '", objects_file_noisy, "'"
    ])

    carla_spawn_objects_node = Node(
        package='carla_spawn_objects',
        executable='carla_spawn_objects',
        name='carla_spawn_objects',
        output='screen',
        parameters=[
            {'objects_definition_file': chosen_objects_file},
            {'spawn_point_ego_vehicle': '-3.0, 14.3, 0.5, 0, 0, 0'},
            {'spawn_sensors_only': False}
        ]
    )

    carla_set_initial_pose_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(carla_spawn_objects_dir, 'set_initial_pose.launch.py')
        ),
        launch_arguments={'role_name': 'ego_vehicle'}.items()
    )

    carla_manual_control_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(carla_manual_control_dir, 'carla_manual_control.launch.py')
        ),
        launch_arguments={'role_name': 'ego_vehicle'}.items()
    )
    
    # OdomToTF: 负责发布 odom -> ego_vehicle 的 TF
    odom_to_tf_node = Node(
        package='carla_cartographer',
        executable='odom_to_tf.py',
        name='odom_to_tf',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # ========================================================================
    # 4. Cartographer & RViz
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

    delayed_cartographer_launch = TimerAction(
        period=10.0,
        actions=[
            cartographer_node,
            cartographer_occupancy_grid_node,
            rviz_node
        ]
    )
    
    # ========================================================================
    # 5. 返回 Launch 描述
    # ========================================================================
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('town', default_value='Town05'),
        DeclareLaunchArgument('map_resolution', default_value='0.05'),
        
        carla_ros_bridge_launch,
        carla_spawn_objects_node,
        carla_set_initial_pose_launch,
        carla_manual_control_launch,
        odom_to_tf_node,
        delayed_cartographer_launch,
    ])
