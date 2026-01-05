from PyQt6.QtWidgets import (
    QMainWindow, QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout, 
    QToolBar, QStatusBar, QMessageBox, QMenu, QDialog, QTabWidget,
    QLabel, QPushButton, QHBoxLayout, QFrame, QStyle, QApplication
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QAction, QIcon, QPalette, QColor
import hardware

class DevicePropertiesDialog(QDialog):
    """Диалоговое окно свойств, как в Windows (General, Driver, Details)"""
    def __init__(self, device_info, parent=None):
        super().__init__(parent)
        self.device = device_info
        self.setWindowTitle(f"{device_info['name']} Properties")
        self.setFixedSize(450, 550)
        # Убираем кнопку контекстной помощи в заголовке
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        
        # --- Заголовок с иконкой ---
        header_layout = QHBoxLayout()
        icon_label = QLabel()
        # Используем стандартную иконку компьютера как заглушку
        icon_label.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon).pixmap(32, 32))
        title_label = QLabel(device_info['name'])
        # Важно: задаем жирный шрифт и черный цвет явно
        title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #000000;") 
        title_label.setWordWrap(True)
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # --- Вкладки ---
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_driver_tab(), "Driver")
        tabs.addTab(self._create_details_tab(), "Details")
        # Вкладку Events пока уберем для простоты, она все равно пустая была
        # tabs.addTab(self._create_events_tab(), "Events") 
        layout.addWidget(tabs)
        
        # --- Кнопки OK/Cancel ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        # Стилизация кнопок под Windows 10 (плоские, с рамкой)
        btn_style = """
            QPushButton {
                background-color: #e1e1e1;
                border: 1px solid #adadad;
                color: black;
                min-width: 75px;
                height: 23px;
            }
            QPushButton:hover {
                background-color: #e5f1fb;
                border: 1px solid #0078d7;
            }
            QPushButton:pressed {
                background-color: #cce4f7;
            }
        """
        for btn in [ok_btn, cancel_btn]:
            btn.setStyleSheet(btn_style)
            
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _create_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Группа информации
        form_box = QFrame()
        form_layout = QVBoxLayout(form_box)
        form_layout.setSpacing(10)
        
        # Используем HTML для форматирования жирным, гарантируем черный цвет
        lbl_style = "QLabel { color: black; }"
        
        type_lbl = QLabel(f"<b>Device type:</b> {self.device.get('type', 'Unknown')}")
        type_lbl.setStyleSheet(lbl_style)
        
        manufacturer_lbl = QLabel(f"<b>Manufacturer:</b> {self.device.get('provider', 'Standard system devices')}")
        manufacturer_lbl.setStyleSheet(lbl_style)
        
        location_lbl = QLabel(f"<b>Location:</b> PCI Slot / Internal Bus")
        location_lbl.setStyleSheet(lbl_style)
        
        form_layout.addWidget(type_lbl)
        form_layout.addWidget(manufacturer_lbl)
        form_layout.addWidget(location_lbl)
        
        layout.addWidget(form_box)
        
        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Статус
        status_group_lbl = QLabel("Device status:")
        status_group_lbl.setStyleSheet(lbl_style)
        
        status_box = QFrame()
        status_box.setStyleSheet("background-color: white; border: 1px solid #ccc; padding: 10px;")
        status_text = QLabel(self.device['status'])
        status_text.setStyleSheet("color: black;")
        status_text.setWordWrap(True)
        status_text.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        s_layout = QVBoxLayout(status_box)
        s_layout.addWidget(status_text)
        
        layout.addWidget(status_group_lbl)
        layout.addWidget(status_box)
        return tab

    def _create_driver_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        info = [
            ("Driver Provider:", self.device.get('provider', 'Linux Kernel')),
            ("Driver Date:", "21.06.2024"), 
            ("Driver Version:", self.device.get('driver', 'Unknown')),
            ("Digital Signer:", "Microsoft Windows Hardware Compatibility (Fake)")
        ]
        
        info_box = QFrame()
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(15)
        
        for title, value in info:
            h = QHBoxLayout()
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: black; font-weight: bold;")
            h.addWidget(t_lbl)
            
            v_lbl = QLabel(value)
            v_lbl.setStyleSheet("color: black;")
            h.addWidget(v_lbl)
            h.addStretch()
            info_layout.addLayout(h)
            
        layout.addWidget(info_box)
        layout.addStretch()
        
        # Кнопки управления драйвером (заглушки)
        buttons = ["Driver Details", "Update Driver", "Roll Back Driver", "Disable Device", "Uninstall Device"]
        btn_style = """
             QPushButton { min-width: 130px; color: black; }
             QPushButton:disabled { color: gray; }
        """
        for btn_text in buttons:
            h_btn = QHBoxLayout()
            h_btn.addStretch()
            btn = QPushButton(btn_text)
            btn.setStyleSheet(btn_style)
            if btn_text in ["Roll Back Driver"]:
                btn.setEnabled(False)
            h_btn.addWidget(btn)
            h_btn.addStretch()
            layout.addLayout(h_btn)
            
        return tab
        
    def _create_details_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        combo_lbl = QLabel("Property")
        combo_lbl.setStyleSheet("color: black;")
        layout.addWidget(combo_lbl)
        
        # Эмуляция комбобокса (пока просто лейбл)
        fake_combo = QLabel("Hardware Ids")
        fake_combo.setStyleSheet("border: 1px solid #ccc; padding: 2px; background: white; color: black;")
        layout.addWidget(fake_combo)

        val_lbl = QLabel("Value:")
        val_lbl.setStyleSheet("color: black; margin-top: 10px;")
        layout.addWidget(val_lbl)
        
        prop_box = QFrame()
        prop_box.setStyleSheet("background-color: white; border: 1px solid #ccc;")
        p_layout = QVBoxLayout(prop_box)
        
        # Показываем ID устройства
        val_text = QLabel(self.device.get('id', 'Unknown ID'))
        val_text.setStyleSheet("color: black;")
        val_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        p_layout.addWidget(val_text)
        p_layout.addStretch()
        
        layout.addWidget(prop_box)
        return tab


class WindowsStyleDeviceManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Device Manager")
        self.resize(800, 600)
        
        # =================================================================
        # ГЛАВНОЕ ИСПРАВЛЕНИЕ ЗДЕСЬ
        # =================================================================
        # Мы принудительно задаем черный цвет текста (color: #000000) 
        # для всех виджетов, чтобы перебить темную тему Linux.
        self.setStyleSheet("""
            /* Глобальный сброс цвета текста на черный */
            QWidget {
                color: #000000;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 9pt;
            }
            
            /* Фон главного окна и диалогов - светло-серый */
            QMainWindow, QDialog, QTabWidget::pane {
                background-color: #f0f0f0;
            }

            /* --- Стилизация дерева устройств --- */
            QTreeWidget {
                background-color: #ffffff; /* Белый фон */
                border: 1px solid #828790; /* Рамка как в Windows */
                outline: none; /* Убираем пунктирную обводку фокуса */
            }
            /* Элемент дерева */
            QTreeWidget::item {
                height: 22px;
                color: #000000; /* Текст ОБЯЗАТЕЛЬНО черный */
                border: 1px solid transparent; /* Резервируем место под рамку */
            }
            /* При наведении мыши (как в Windows 10/11) */
            QTreeWidget::item:hover {
                background-color: #e5f3ff;
                color: #000000;
            }
            /* Выделенный активный элемент */
            QTreeWidget::item:selected:active {
                background-color: #cce8ff;
                color: #000000;
                border: 1px solid #99d1ff;
            }
            /* Выделенный НЕактивный элемент (когда окно не в фокусе) */
            QTreeWidget::item:selected:!active {
                background-color: #f0f0f0;
                color: #000000;
                border: 1px solid transparent;
            }
            
            /* --- Стилизация Тулбара --- */
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fbfbfb, stop:1 #e0e0e0);
                border-bottom: 1px solid #a0a0a0;
                spacing: 5px;
                padding: 3px;
            }
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                padding: 2px;
            }
            QToolButton:hover {
                background-color: #e5f3ff;
                border: 1px solid #a0a0a0;
            }
            
            /* --- Стилизация Меню --- */
            QMenuBar {
                background-color: #f0f0f0;
                color: #000000;
            }
            QMenuBar::item:selected {
                background-color: #cce8ff;
            }
            QMenu {
                background-color: #f0f0f0;
                border: 1px solid #a0a0a0;
                color: #000000;
            }
            QMenu::item:selected {
                background-color: #99d1ff;
                color: #000000;
            }

            /* --- Статус бар --- */
            QStatusBar {
                background-color: #f0f0f0;
                color: #000000;
                border-top: 1px solid #a0a0a0;
            }
            QStatusBar::item {
                border: none;
            }
        """)
        # =================================================================
        
        self._create_menubar()
        self._create_toolbar()
        
        # Главный виджет - дерево
        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderHidden(True)
        self.device_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.device_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.device_tree.itemDoubleClicked.connect(self.on_item_double_click)
        self.device_tree.setIndentation(20) # Отступ ветвей как в Windows
        
        self.setCentralWidget(self.device_tree)
        
        self.statusBar().showMessage("Ready")
        
        # Загружаем устройства с небольшой задержкой, чтобы интерфейс прорисовался
        QApplication.processEvents()
        self.load_devices()
        
    def _create_menubar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        file_menu.addAction("Exit", self.close)
        
        action_menu = menubar.addMenu("Action")
        scan_act = action_menu.addAction("Scan for hardware changes", self.scan_hardware)
        # Иконка для меню
        scan_act.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        action_menu.addSeparator()
        action_menu.addAction("Properties")
        
        view_menu = menubar.addMenu("View")
        view_menu.addAction("Devices by type").setChecked(True)
        view_menu.addAction("Devices by connection")
        view_menu.addSeparator()
        view_menu.addAction("Show hidden devices")
        
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About Device Manager")

    def _create_toolbar(self):
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16)) # Стандартный размер иконок в Win
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        style = self.style()
        
        # Кнопки Back/Forward (для визуала)
        toolbar.addAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowLeft), "")
        toolbar.addAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowRight), "")
        toolbar.addSeparator()
        
        scan_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "Scan for hardware changes", self)
        scan_action.triggered.connect(self.scan_hardware)
        toolbar.addAction(scan_action)

    def load_devices(self):
        self.device_tree.clear()
        
        # Корень - имя ПК
        root_node = QTreeWidgetItem(self.device_tree)
        root_node.setText(0, "LINUX-DESKTOP")
        root_node.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        root_node.setExpanded(True)
        
        # Получаем данные из hardware.py
        devices = hardware.get_hardware_info()
        
        # Сортируем категории
        for category in sorted(devices.keys()):
            if not devices[category]:
                continue
                
            cat_item = QTreeWidgetItem(root_node)
            cat_item.setText(0, category)
            
            # Подбираем стандартные иконки Qt, похожие на Windows
            icon_map = {
                'Processors': QStyle.StandardPixmap.SP_TitleBarMenuButton, # Похоже на чип
                'Display adapters': QStyle.StandardPixmap.SP_DesktopIcon,
                'Disk drives': QStyle.StandardPixmap.SP_DriveHDIcon,
                'Network adapters': QStyle.StandardPixmap.SP_DriveNetIcon,
                'Sound, video and game controllers': QStyle.StandardPixmap.SP_MediaVolume,
                'Universal Serial Bus controllers': QStyle.StandardPixmap.SP_DriveFDIcon, # Отдаленно похоже на порт
            }
            
            icon_code = icon_map.get(category, QStyle.StandardPixmap.SP_DirIcon)
            cat_item.setIcon(0, self.style().standardIcon(icon_code))
            
            for dev in devices[category]:
                dev_item = QTreeWidgetItem(cat_item)
                dev_item.setText(0, dev['name'])
                # Сохраняем словарь с данными устройства в скрытых данных элемента
                dev_item.setData(0, Qt.ItemDataRole.UserRole, dev)
                
                # Иконка для конечного устройства (маленькая шестеренка/файл)
                dev_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
    
    def scan_hardware(self):
        # Эмуляция процесса сканирования
        self.statusBar().showMessage("Scanning plug and play compliant hardware...")
        self.device_tree.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents() # Даем GUI обновиться
        
        # Типа задержка сканирования
        import time
        time.sleep(0.5)
        
        self.load_devices()
        
        QApplication.restoreOverrideCursor()
        self.device_tree.setEnabled(True)
        self.statusBar().showMessage("Ready")

    def show_context_menu(self, position):
        item = self.device_tree.itemAt(position)
        if not item: return
        
        menu = QMenu()
        dev_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if dev_data: # Это устройство
            menu.addAction("Update driver...")
            menu.addAction("Disable device")
            menu.addAction("Uninstall device")
            menu.addSeparator()
            menu.addAction("Scan for hardware changes", self.scan_hardware)
            menu.addSeparator()
            prop_act = menu.addAction("Properties")
            prop_act.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold)) # Жирным, как в Win
            prop_act.triggered.connect(lambda: self.show_properties_dialog(dev_data))
        elif item.parent(): # Это категория
            menu.addAction("Scan for hardware changes", self.scan_hardware)
            menu.addSeparator()
            menu.addAction("Properties")
        else: # Это корень (Имя ПК)
             menu.addAction("Scan for hardware changes", self.scan_hardware)
            
        menu.exec(self.device_tree.mapToGlobal(position))

    def on_item_double_click(self, item, column):
        dev_data = item.data(0, Qt.ItemDataRole.UserRole)
        if dev_data:
            self.show_properties_dialog(dev_data)
        # Если двойной клик по категории - она сама раскроется/скроется, 
        # дополнительно ничего делать не надо.

    def show_properties_dialog(self, dev_data):
        dialog = DevicePropertiesDialog(dev_data, self)
        dialog.exec()
