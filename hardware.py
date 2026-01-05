import subprocess
import os
import re

def run_command(command):
    """Безопасное выполнение команд"""
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return ""

def get_hardware_info():
    """
    Собирает полную информацию об оборудовании, имитируя структуру Windows.
    """
    devices = {
        'Processors': [],
        'Display adapters': [],
        'Disk drives': [],
        'Network adapters': [],
        'Sound, video and game controllers': [],
        'Universal Serial Bus controllers': [],
        'Memory technology devices': [],
        'System devices': []
    }

    # --- 1. Процессоры ---
    try:
        cpu_info = run_command(['lscpu'])
        model_name = "Unknown Processor"
        for line in cpu_info.split('\n'):
            if "Model name:" in line:
                model_name = line.split(":")[1].strip()
                break
        
        # Получаем количество ядер, чтобы создать запись для каждого (как в Windows)
        cores = os.cpu_count() or 1
        for _ in range(cores):
            devices['Processors'].append({
                'name': model_name,
                'status': 'Working properly',
                'driver': 'intel_pstate' if 'Intel' in model_name else 'acpi_cpufreq',
                'id': 'CPU',
                'type': 'CPU'
            })
    except Exception:
        pass

    # --- 2. PCI Устройства (Видео, Звук, Сеть) ---
    # lspci -k показывает драйверы ядра
    pci_output = run_command(['lspci', '-vmm', '-k'])
    current_device = {}
    
    for line in pci_output.split('\n'):
        if not line:
            if current_device:
                _process_pci_device(current_device, devices)
                current_device = {}
            continue
            
        if ':' in line:
            key, val = line.split(':', 1)
            current_device[key.strip()] = val.strip()
    
    # Обработка последнего устройства
    if current_device:
        _process_pci_device(current_device, devices)

    # --- 3. USB Контроллеры и устройства ---
    usb_output = run_command(['lsusb'])
    for line in usb_output.split('\n'):
        if not line: continue
        # Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
        parts = line.split()
        if len(parts) >= 6:
            name = ' '.join(parts[6:])
            dev_id = f"{parts[5]}"
            devices['Universal Serial Bus controllers'].append({
                'name': name,
                'status': 'Working properly',
                'driver': 'usb-storage' if 'Storage' in name else 'usbhid',
                'id': f"USB\\VID_{parts[5].replace(':', '&PID_')}",
                'type': 'USB'
            })

    # --- 4. Диски (Disk Drives) ---
    blk_output = run_command(['lsblk', '-d', '-o', 'NAME,MODEL,TYPE,TRAN', '-n'])
    for line in blk_output.split('\n'):
        if not line: continue
        parts = line.split()
        if len(parts) >= 2:
            if 'disk' in line:
                # Пытаемся красиво склеить имя
                model = ' '.join([p for p in parts if p not in ['disk', 'sata', 'nvme', 'usb']])
                devices['Disk drives'].append({
                    'name': model or "Generic Disk Drive",
                    'status': 'Working properly',
                    'driver': 'sd_mod',
                    'id': f"SCSI\\Disk{model.replace(' ', '')}",
                    'type': 'Disk'
                })

    return devices

def _process_pci_device(pci_dev, devices_dict):
    """Распределяет PCI устройства по категориям Windows"""
    cls = pci_dev.get('Class', '').lower()
    vendor = pci_dev.get('Vendor', 'Unknown')
    device = pci_dev.get('Device', 'Unknown')
    driver = pci_dev.get('Driver', 'Unknown')
    full_name = f"{vendor} {device}"
    
    dev_obj = {
        'name': full_name,
        'status': 'Working properly',
        'driver': driver,
        'id': f"PCI\\VEN_XXXX&DEV_XXXX", # Имитация ID
        'provider': vendor
    }

    if 'vga' in cls or '3d' in cls or 'display' in cls:
        devices_dict['Display adapters'].append(dev_obj)
    elif 'ethernet' in cls or 'network' in cls or 'wireless' in cls:
        devices_dict['Network adapters'].append(dev_obj)
    elif 'audio' in cls or 'multimedia' in cls:
        devices_dict['Sound, video and game controllers'].append(dev_obj)
    else:
        # Все остальное кидаем в системные, как Windows
        devices_dict['System devices'].append(dev_obj)
