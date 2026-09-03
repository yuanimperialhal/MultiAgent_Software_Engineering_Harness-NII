from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QLabel, QWidget
from PySide6.QtGui import QFont


class PerformanceMainWindow(QMainWindow):
    """
    主性能监控窗口，显示 CPU、内存使用率及更新时间戳。
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("实时性能监控")
        self.setMinimumSize(400, 200)

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Labels
        self.cpu_label = QLabel("CPU: --%")
        self.mem_label = QLabel("Memory: --% (-- GB used)")
        self.timestamp_label = QLabel("Last updated: --")

        # Styling
        font = QFont("SF Pro Display", 12) if hasattr(QFont, "SF Pro Display") else QFont("Segoe UI", 12)
        font.setBold(True)
        for label in [self.cpu_label, self.mem_label, self.timestamp_label]:
            label.setFont(font)
            label.setStyleSheet("color: #333; margin: 4px 0;")

        layout.addWidget(self.cpu_label)
        layout.addWidget(self.mem_label)
        layout.addWidget(self.timestamp_label)

    def update_display(self, cpu_percent: float, mem_used_mb: int, timestamp: int):
        """
        槽函数：安全更新 UI 显示。

        Args:
            cpu_percent (float): CPU 使用率（0.0–100.0）
            mem_used_mb (int): 已用内存（MB）
            timestamp (int): Unix 时间戳（秒）
        """
        from datetime import datetime

        # Format memory: convert MB → GB with one decimal, avoid scientific notation
        mem_gb = mem_used_mb / 1024.0

        self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")
        self.mem_label.setText(f"Memory: {mem_gb:.1f} GB used")
        self.timestamp_label.setText(f"Last updated: {datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')}")