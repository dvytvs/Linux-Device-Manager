#!/bin/bash
# Скрипт запуска Диспетчера устройств Linux

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Проверяем Python
PYTHON=${PYTHON:-python3}

# Проверяем наличие python3
if ! command -v $PYTHON &> /dev/null; then
    echo "Ошибка: python3 не найден"
    echo "Установите: sudo apt install python3"
    exit 1
fi

# Проверяем PyGObject
if ! $PYTHON -c "import gi; gi.require_version('Gtk', '3.0')" 2>/dev/null; then
    echo "Установка зависимостей..."
    if command -v apt &> /dev/null; then
        sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3-gobject gtk3
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm python-gobject gtk3
    else
        echo "Не удалось определить пакетный менеджер"
        echo "Установите PyGObject вручную:"
        echo "  sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0"
        exit 1
    fi
fi

# Проверяем дополнительные утилиты
for cmd in lspci lsusb ip ethtool; do
    if ! command -v $cmd &> /dev/null; then
        echo "Предупреждение: $cmd не найден (некоторые функции могут быть недоступны)"
    fi
done

# Запускаем приложение
echo "Запуск Диспетчера устройств Linux..."
cd "$SCRIPT_DIR"
exec $PYTHON "$SCRIPT_DIR/device_manager.py" "$@"
