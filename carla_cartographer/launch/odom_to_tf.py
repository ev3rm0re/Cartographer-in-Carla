#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OdomToTF Node
-------------
功能：
1. 订阅 CARLA 发布的原始里程计数据 (/carla/ego_vehicle/odometry)。
2. 广播 odom -> ego_vehicle 的 TF 变换。
3. 将里程计消息的 frame_id 修正为 'odom' 并重新发布到 /odom。

原因：
CARLA 发布的里程计数据 frame_id 可能不符合 ROS 标准（或 Cartographer 期望），
且我们需要一个专门的节点来维护 TF 树的完整性。
"""

import copy
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster

class OdomToTF(Node):
    def __init__(self):
        super().__init__('odom_to_tf')
        
        # 订阅 CARLA 原始里程计
        self.subscription = self.create_subscription(
            Odometry,
            '/carla/ego_vehicle/odometry', 
            self.listener_callback,
            10
        )
            
        # 发布修正后的里程计 (供 Cartographer 使用)
        self.publisher = self.create_publisher(Odometry, '/odom', 10)
        
        # TF 广播器
        self.tf_broadcaster = TransformBroadcaster(self)
        
        self.get_logger().info('OdomToTF node started.')
        self.get_logger().info('  Subscribing: /carla/ego_vehicle/odometry')
        self.get_logger().info('  Publishing:  /odom')
        self.get_logger().info('  Broadcasting TF: odom -> ego_vehicle')

    def listener_callback(self, msg):
        """
        回调函数：处理接收到的里程计消息
        """
        # 1. 广播 TF: odom -> ego_vehicle
        t = TransformStamped()
        t.header.stamp = msg.header.stamp
        t.header.frame_id = 'odom'
        t.child_frame_id = 'ego_vehicle' # 对应 carla_2d.lua 中的 tracking_frame

        # 直接使用里程计中的位姿数据
        t.transform.translation.x = msg.pose.pose.position.x
        t.transform.translation.y = msg.pose.pose.position.y
        t.transform.translation.z = msg.pose.pose.position.z
        t.transform.rotation = msg.pose.pose.orientation

        self.tf_broadcaster.sendTransform(t)

        # 2. 发布修正后的里程计消息
        # 深拷贝以避免修改原始消息（虽然这里原始消息不再使用，但为了安全）
        new_msg = copy.deepcopy(msg)
        
        # 修改坐标系 ID 以匹配 TF 树
        new_msg.header.frame_id = 'odom'
        new_msg.child_frame_id = 'ego_vehicle'
        
        self.publisher.publish(new_msg)

def main(args=None):
    rclpy.init(args=args)
    node = OdomToTF()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()