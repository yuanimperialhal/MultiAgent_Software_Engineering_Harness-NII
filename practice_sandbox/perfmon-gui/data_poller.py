from PySide6.QtCore import QObject, QTimer, Signal
from sensor import SystemSensor
import time


class DataPoller(QObject):
    """
    数据轮询器：定期采集系统性能数据并发射信号。

    使用 QTimer 每 1000ms 触发一次采集，通过 data_updated 信号将
    CPU 百分比（float）、已用内存（MB，int）、时间戳（秒级 int）
    发送给 UI 层。
    """
    data_updated = Signal(float, int, int)  # cpu_percent: float, mem_used_mb: int, timestamp: int

    def __init__(self):
        super().__init__()
        self._sensor = SystemSensor()
        self._timer = QTimer()
        self._timer.timeout.connect(self._poll)
        # Ensure first cpu_percent call is preheated before any poll
        self._sensor.get_cpu_percent(percpu=False)

    def start(self):
        """启动轮询（1Hz）"""
        self._timer.start(1000)

    def _poll(self):
        """执行单次采集并发射信号"""
        try:
            cpu_percent = self._sensor.get_cpu_percent(percpu=False)
            mem_info = self._sensor.get_memory_info()
            # Convert bytes → MB (floor division for integer MB, avoids float precision noise in UI)
            mem_used_mb = mem_info['used'] // 1024 // 1024
            timestamp = int(time.time())

            # Emit with guaranteed units: cpu_percent in [0.0, 100.0], mem_used_mb in MB, timestamp in seconds
            self.data_updated.emit(cpu_percent, mem_used_mb, timestamp)
        except Exception as e:
            # Silently ignore sensor errors (e.g., psutil.AccessDenied) to avoid crashing UI
            # Real app may log or emit error signal; here we skip update only.
            pass