import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
import gui

def main():
    app = QApplication(sys.argv)
    
    # Пытаемся установить стиль Windows, если доступен (через qt5ct/qt6ct)
    # Если нет, ставим Fusion как наиболее нейтральный
    if "Windows" in app.style().objectName():
        pass
    else:
        app.setStyle("Fusion")
    
    # Шрифт Segoe UI - стандарт для Windows
    font = QFont("Segoe UI", 9)
    # Fallback на системный sans-serif, если Segoe UI нет в Linux
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    
    window = gui.WindowsStyleDeviceManager()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
