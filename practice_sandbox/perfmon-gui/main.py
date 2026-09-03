import sys
from PySide6.QtWidgets import QApplication

from main_window import PerformanceMainWindow
from data_poller import DataPoller


def main():
    app = QApplication(sys.argv)

    # Create main window
    window = PerformanceMainWindow()

    # Create and start data poller
    poller = DataPoller()
    poller.start()

    # Connect signal to slot
    poller.data_updated.connect(window.update_display)

    # Show window and run app
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()