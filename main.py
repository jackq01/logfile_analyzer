import sys
import os
import logging
import multiprocessing
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from app.main_window import LogAnalyzerApp
from app.style_manager import apply_global_styles


def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("log_analyzer_debug.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    icon_path = get_resource_path("icon.ico")
    if not os.path.exists(icon_path):
        icon_path = get_resource_path("icon.png")
    
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    apply_global_styles(app)
    window = LogAnalyzerApp()
    window.show()
    sys.exit(app.exec())
