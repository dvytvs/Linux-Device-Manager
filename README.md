<div align="center">

# 🔴 ПРОЕКТ ОФИЦИАЛЬНО ЗАКРЫТ 🔴

**Внимание! Разработка и поддержка этого проекта прекращены.** <br>
Рекомендуется использовать **[Hardinfo2](https://github.com/hardinfo2/hardinfo2.git)**.

</div>

---


# Linux Device Manager

Полнофункциональный диспетчер устройств для Linux, стилизованный под Диспетчер устройств Windows 11.

## Возможности

- **Полное сканирование устройств**: PCI, USB, сетевые, дисковые, звуковые, видео и другие устройства
- **Древовидная структура**: Категории устройств как в Windows Device Manager
- **Контекстное меню**: ПКМ для включения/отключения/удаления устройств
- **Окно свойств**: Вкладки "Общие", "Драйвер", "Ресурсы", "Сведения"
- **Меню и тулбар**: Файл, Действие, Вид, Справка
- **Поиск**: Фильтрация устройств по имени
- **Экспорт**: В TXT, JSON, HTML форматы
- **Иконки**: Для всех категорий устройств

## Источники данных

- `/sys/class/*` - sysfs информация
- `lspci` - PCI устройства
- `lsusb` - USB устройства
- `ip link` - сетевые интерфейсы
- `/proc/bus/input/devices` - устройства ввода
- `/proc/asound/cards` - звуковые устройства
- `/proc/cpuinfo` - процессоры
- `/sys/class/power_supply` - батареи
- `v4l2-ctl` - веб-камеры
- `lpstat` - принтеры
- `bluetoothctl` - Bluetooth

## Установка

### Ubuntu/Debian

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
sudo apt install pciutils usbutils net-tools ethtool
```

### Fedora

```bash
sudo dnf install python3-gobject gtk3
sudo dnf install pciutils usbutils ethtool
```

### Arch Linux

```bash
sudo pacman -S python-gobject gtk3
sudo pacman -S pciutils usbutils ethtool
```

## Запуск

```bash
./run.sh
```

Или напрямую:

```bash
python3 device_manager.py
```

## Установка .desktop файла

```bash
cp linux-device-manager.desktop ~/.local/share/applications/
chmod +x run.sh
```

## Структура проекта

```
linux-device-manager/
├── device_manager.py      # Основной код приложения
├── run.sh                 # Скрипт запуска
├── requirements.txt       # Python зависимости
├── linux-device-manager.desktop  # Desktop файл
└── README.md             # Документация
```

## Лицензия

MIT
