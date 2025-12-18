import rclpy
from rclpy.node import Node
from tf2_ros import Buffer, TransformListener
import time
import sys

class TfRecorder(Node):
    def __init__(self, target_frame, source_frame, output_file):
        super().__init__('tf_recorder')
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.target_frame = target_frame
        self.source_frame = source_frame
        self.file = open(output_file, 'w')
        self.start_time = time.time()
        # 这里的频率决定了提取轨迹的密度，10Hz通常足够
        self.timer = self.create_timer(0.1, self.save_transform)
        print(f"开始监听: {target_frame} -> {source_frame}")
        print("请在一个新的终端播放你的 bag 包: ros2 bag play ...")

    def save_transform(self):
        try:
            # 查找最近的变换
            t = self.buffer.lookup_transform(
                self.target_frame,
                self.source_frame,
                rclpy.time.Time())

            # 提取数据
            timestamp = t.header.stamp.sec + t.header.stamp.nanosec * 1e-9
            tx = t.transform.translation.x
            ty = t.transform.translation.y
            tz = t.transform.translation.z
            qx = t.transform.rotation.x
            qy = t.transform.rotation.y
            qz = t.transform.rotation.z
            qw = t.transform.rotation.w

            # 写入 TUM 格式: time x y z qx qy qz qw
            line = f"{timestamp:.6f} {tx:.6f} {ty:.6f} {tz:.6f} {qx:.6f} {qy:.6f} {qz:.6f} {qw:.6f}\n"
            self.file.write(line)
            self.file.flush()
            print(".", end="", flush=True) # 打印进度点

        except Exception as e:
            # 刚开始播放时可能查不到变换，忽略
            pass

def main():
    rclpy.init()
    # 配置你的坐标系名称
    # 参数: python3 export_tf.py <父坐标系> <子坐标系> <文件名>
    # 默认: map -> ego_vehicle -> est.tum
    node = TfRecorder('map', 'ego_vehicle', 'est.tum')
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.file.close()
        node.destroy_node()
        rclpy.shutdown()
        print("\n提取完成，文件已保存为 est.tum")

if __name__ == '__main__':
    main()