import psutil
import time


class SystemSensor:
    """
    跨平台系统性能传感器，封装 CPU 和内存监控逻辑。
    """

    def __init__(self):
        # 首次调用 cpu_percent 需预热；此处仅初始化，不触发采集
        self._cpu_preheated = False

    def get_cpu_percent(self, percpu=False) -> float | list[float]:
        """
        获取当前 CPU 使用率（%）。

        Args:
            percpu (bool): 若为 True，返回每个逻辑 CPU 的使用率列表；
                           否则返回整体平均值（float）。
        Returns:
            float or list[float]: CPU 使用率（0.0–100.0 范围）。
        """
        if not self._cpu_preheated:
            # 预热：首次调用需间隔 >0 才能返回有效值
            psutil.cpu_percent(interval=None)
            self._cpu_preheated = True
        return psutil.cpu_percent(interval=None, percpu=percpu)

    def get_memory_info(self) -> dict:
        """
        获取当前内存使用信息。

        Returns:
            dict: 包含 'total' (bytes), 'available' (bytes), 'used' (bytes),
                  'percent' (float, 0.0–100.0) 的字典。
        """
        mem = psutil.virtual_memory()
        return {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent,
        }


if __name__ == "__main__":
    # 单元验证：直接运行此文件，确认基础采集功能可用
    sensor = SystemSensor()

    print("[CPU]")
    cpu_avg = sensor.get_cpu_percent(percpu=False)
    print(f"  Overall: {cpu_avg:.1f}%")

    print("[Memory]")
    mem = sensor.get_memory_info()
    print(f"  Total: {mem['total'] / (1024**3):.1f} GB")
    print(f"  Used:  {mem['used'] / (1024**3):.1f} GB ({mem['percent']:.1f}%)")

    # 短暂等待后再次采样，验证变化性
    time.sleep(1.0)
    cpu_avg2 = sensor.get_cpu_percent(percpu=False)
    print(f"  After 1s: {cpu_avg2:.1f}% (delta: {abs(cpu_avg2 - cpu_avg):.1f}%)")