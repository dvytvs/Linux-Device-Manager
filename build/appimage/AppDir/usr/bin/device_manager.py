#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Linux Device Manager — GTK4 + libadwaita"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('Gio', '2.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gdk, Gio, GLib, GdkPixbuf, Adw, Pango
import subprocess, os, sys, json, re, threading, struct
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ============================================================================
# ДАННЫЕ
# ============================================================================

class Dev:
    def __init__(self, name, category, subsystem='', driver='', status='Работает нормально',
                 device_id='', location='', vendor='', details=None, resources=None,
                 enabled=True, icon_name='computer', sysfs_path='', serial=''):
        self.name=name; self.category=category; self.subsystem=subsystem
        self.driver=driver; self.status=status; self.device_id=device_id
        self.location=location; self.vendor=vendor; self.details=details or {}
        self.resources=resources or {}; self.enabled=enabled; self.icon_name=icon_name
        self.sysfs_path=sysfs_path; self.serial=serial
    def to_dict(self):
        return {k:getattr(self,k) for k in ['name','category','subsystem','driver','status',
            'device_id','location','vendor','details','resources','enabled','icon_name','serial']}

class Scanner:
    CM={
        'audio':'Звуковые, игровые и видеоустройства','sound':'Звуковые, игровые и видеоустройства',
        'drm':'Видеоадаптеры','display':'Видеоадаптеры','block':'Дисковые устройства',
        'disk':'Дисковые устройства','input':'Клавиатуры','usb':'Контроллеры USB',
        'pci':'Системные устройства','net':'Сетевые адаптеры','network':'Сетевые адаптеры',
        'hid':'Устройства HID','hidraw':'Устройства HID','mouse':'Мыши','mice':'Мыши',
        'tty':'Порты (COM и LPT)','lp':'Порты (COM и LPT)','graphics':'Мониторы',
        'fb':'Мониторы','backlight':'Мониторы','scsi':'Контроллеры запоминающих устройств',
        'nvme':'Дисковые устройства','mmc':'Дисковые устройства','i2c':'Системные устройства',
        'spi':'Системные устройства','platform':'Системные устройства','acpi':'Системные устройства',
        'battery':'Батареи','power':'Батареи','power_supply':'Батареи','thermal':'Системные устройства',
        'watchdog':'Системные устройства','misc':'Системные устройства','virtio':'Системные устройства',
        'leds':'Системные устройства','video4linux':'Веб-камеры','bluetooth':'Bluetooth',
        'ieee1394':'Контроллеры запоминающих устройств','pcmcia':'Контроллеры запоминающих устройств',
    }
    CI={
        'Звуковые, игровые и видеоустройства':'audio-card','Видеоадаптеры':'video-display',
        'Дисковые устройства':'drive-harddisk','Клавиатуры':'input-keyboard',
        'Компьютер':'computer','Контроллеры USB':'drive-removable-media-usb',
        'Контроллеры запоминающих устройств':'drive-multidisk','Мониторы':'display-projector',
        'Мыши':'input-mouse','Очереди печати':'printer','Порты (COM и LPT)':'serial-terminal',
        'Системные устройства':'system-run','Устройства HID':'input-gaming',
        'Батареи':'battery','Bluetooth':'bluetooth','Веб-камеры':'camera-web',
        'Сетевые адаптеры':'network-wired','Процессоры':'cpu',
    }
    def __init__(self):
        self.devices=[]; self.categories={}; self.sys_info={}

    def scan_all(self):
        self.devices=[]; self.categories={}
        for m in [self._lspci,self._lsusb,self._disks,self._net,self._input,self._sound,
                   self._cpu,self._monitors,self._battery,self._bt,self._webcam,self._prn]:
            try: m()
            except: pass
        self._cat()
        self.sys_info={
            'hostname':self._r('hostname'),'kernel':self._r('uname -r'),
            'os':self._r("grep PRETTY_NAME /etc/os-release|cut -d= -f2|tr -d '\"'"),
            'arch':self._r('uname -m'),'uptime':self._r('uptime -p'),
        }
        return self.categories

    def _r(self,c):
        try: return subprocess.run(c,shell=True,capture_output=True,text=True,timeout=10).stdout.strip()
        except: return ''
    def _rf(self,p):
        try:
            with open(p) as f: return f.read().strip()
        except: return ''

    def _lspci(self):
        raw=self._r('lspci -vmm')
        if not raw: return
        cur={}
        for l in raw.split('\n'):
            if l.startswith('Slot:'):
                if cur: self._add_pci(cur)
                cur={'Slot':l.split(':',1)[1].strip()}
            elif ':' in l:
                k,v=l.split(':',1); cur[k.strip()]=v.strip()
        if cur: self._add_pci(cur)

    def _add_pci(self,d):
        slot=d.get('Slot',''); vn=d.get('Vendor',''); dn=d.get('Device','')
        sv=d.get('SVendor',''); sd=d.get('SDevice',''); cl=d.get('Class','')
        dr=d.get('Driver',''); mod=d.get('Module',''); irq=d.get('IRQ','')
        mem=d.get('Memory',''); io=d.get('I/O',''); rev=d.get('Rev','')
        nm=f"{vn} {dn}".strip() or dn or vn or 'Unknown'
        if rev: nm=f"{nm} (rev {rev})"
        cat=self._pc(cl)
        dev=Dev(nm,cat,'pci',dr,'Работает нормально' if dr else 'Нет драйвера',
                f'PCI\\{slot}',f'Slot {slot}',sv or vn)
        det={}
        if sv: det['Производитель платы']=sv
        if sd: det['Модель платы']=sd
        if cl: det['Класс']=cl
        if dr: det['Драйвер ядра']=dr
        if mod: det['Модули ядра']=mod
        if irq: det['IRQ']=irq
        if mem: det['Память']=mem
        if io: det['Порт I/O']=io
        if rev: det['Ревизия']=rev
        if dr:
            mi=self._r(f'modinfo {dr} 2>/dev/null|grep -E "^version|^description|^filename|^author"')
            for ml in mi.split('\n'):
                if ':' in ml:
                    mk,mv=ml.split(':',1); det[f'modinfo:{mk.strip()}']=mv.strip()
        dev.details=det
        res={}
        if irq: res['Прерывание']=f'IRQ {irq}'
        if mem: res['Память']=mem
        if io: res['Порт I/O']=io
        dev.resources=res
        self.devices.append(dev)

    def _pc(self,cl):
        c=cl.lower()
        if 'vga' in c or 'display' in c or '3d' in c: return 'Видеоадаптеры'
        if 'ethernet' in c or 'network' in c: return 'Сетевые адаптеры'
        if 'audio' in c or 'multimedia' in c: return 'Звуковые, игровые и видеоустройства'
        if 'usb' in c or 'xhci' in c or 'ehci' in c or 'ohci' in c: return 'Контроллеры USB'
        if 'sata' in c or 'ata' in c or 'storage' in c or 'nvme' in c: return 'Контроллеры запоминающих устройств'
        if 'bridge' in c or 'isa' in c: return 'Системные устройства'
        if 'bluetooth' in c: return 'Bluetooth'
        return 'Системные устройства'

    def _lsusb(self):
        raw=self._r('lsusb')
        if not raw: return
        for l in raw.split('\n'):
            m=re.match(r'Bus\s+(\d+)\s+Device\s+(\d+):\s+ID\s+([0-9a-fA-F]+):([0-9a-fA-F]+)\s+(.*)',l)
            if not m: continue
            b,d,v,p,desc=m.groups()
            if 'root hub' in desc.lower() or 'linux foundation' in desc.lower(): continue
            cat=self._uc(desc)
            dev=Dev(desc,cat,'usb','', 'Работает нормально',
                    f'USB\\VID_{v.upper()}_PID_{p.upper()}',f'Bus {b}, Device {d}',
                    desc.split()[0] if desc else '')
            dev.details={'Bus':b,'Device':d,'VendorID':v.upper(),'ProductID':p.upper()}
            self.devices.append(dev)

    def _uc(self,d):
        dl=d.lower()
        if 'keyboard' in dl or 'kb' in dl: return 'Клавиатуры'
        if 'mouse' in dl: return 'Мыши'
        if 'webcam' in dl or 'camera' in dl or 'uvc' in dl: return 'Веб-камеры'
        if 'bluetooth' in dl: return 'Bluetooth'
        if 'printer' in dl: return 'Очереди печати'
        if 'storage' in dl or 'mass storage' in dl: return 'Контроллеры запоминающих устройств'
        if 'hub' in dl: return 'Контроллеры USB'
        return 'Устройства HID'

    def _disks(self):
        raw=self._r('lsblk -d -b -o NAME,SIZE,MODEL,VENDOR,TRAN,TYPE,REV,SERIAL')
        if not raw: return
        for l in raw.strip().split('\n')[1:]:
            p=l.split(None,7)
            if len(p)<3: continue
            nm,sz,mdl,vnd,trn,dt,rv,sn=p[0],p[1],p[2],p[3] if len(p)>3 else '',p[4] if len(p)>4 else '',p[5] if len(p)>5 else '',p[6] if len(p)>6 else '',p[7] if len(p)>7 else ''
            if trn in('rom','loop','') and dt=='loop': continue
            if nm=='zram0': continue
            sb=int(sz) if sz.isdigit() else 0
            szs=self._fmt(sb) if sb else ''
            dev=Dev(f"{vnd} {mdl}".strip() or mdl,'Дисковые устройства','block','','Работает нормально',
                    f'DISK\\{nm}',f'/dev/{nm}',vnd or '')
            dev.details={'Устройство':f'/dev/{nm}','Модель':mdl,'Производитель':vnd or 'N/A',
                         'Интерфейс':trn or 'N/A','Объём':szs}
            if rv: dev.details['Ревизия']=rv
            if sn: dev.details['Серийный номер']=sn; dev.serial=sn
            ss=self._rf(f'/sys/block/{nm}/queue/hw_sector_size')
            if ss: dev.details['Размер сектора']=f'{ss} байт'
            self.devices.append(dev)

    def _fmt(self,b):
        for u in ['Б','КБ','МБ','ГБ','ТБ']:
            if b<1024: return f'{b:.1f} {u}'
            b/=1024
        return f'{b:.1f} ПБ'

    def _net(self):
        raw=self._r('ip -o link show')
        if not raw: return
        for l in raw.split('\n'):
            p=l.split()
            if len(p)<2: continue
            ifc=p[1].rstrip(':')
            if ifc in('lo','docker0') or ifc.startswith(('br-','veth','docker','cni','flannel')): continue
            eth=self._r(f'ethtool -i {ifc}')
            dr=dv=fw=''
            if eth:
                for el in eth.split('\n'):
                    if el.startswith('driver:'): dr=el.split(':',1)[1].strip()
                    elif el.startswith('version:'): dv=el.split(':',1)[1].strip()
                    elif el.startswith('firmware-version:'): fw=el.split(':',1)[1].strip()
            mac=self._rf(f'/sys/class/net/{ifc}/address')
            spd=self._rf(f'/sys/class/net/{ifc}/speed')
            mtu=self._rf(f'/sys/class/net/{ifc}/mtu')
            st=self._rf(f'/sys/class/net/{ifc}/operstate')
            ip4=self._r(f"ip -4 addr show {ifc}|grep 'inet '|awk '{{print $2}}'")
            dev=Dev(ifc,'Сетевые адаптеры','net',dr,
                    'Подключено' if st=='up' else 'Отключено',f'NET\\{ifc}','',icon_name='network-wired')
            det={'Интерфейс':ifc,'MAC':mac or 'N/A','Состояние':st or 'N/A'}
            if ip4: det['IPv4']=ip4
            if spd and spd!='-1': det['Скорость']=f'{spd} Мбит/с'
            if mtu: det['MTU']=mtu
            if dr: det['Драйвер']=dr
            if dv: det['Версия драйвера']=dv
            if fw: det['Прошивка']=fw
            dev.details=det
            self.devices.append(dev)

    def _input(self):
        raw=self._r('cat /proc/bus/input/devices')
        if not raw: return
        cur={}
        for l in raw.split('\n'):
            l=l.strip()
            if l.startswith('I:'):
                if cur: self._ai(cur)
                cur={}
                for pt in l.split():
                    if '=' in pt: k,v=pt.split('=',1); cur[k]=v.strip('"')
            elif l.startswith('N:') and 'Name=' in l: cur['Name']=l.split('Name=',1)[1].strip('"')
            elif l.startswith('P:'): cur['Phys']=l.split('=',1)[1].strip('"') if '=' in l else ''
            elif l.startswith('H:'): cur['Handlers']=l.split(':',1)[1].strip() if ':' in l else ''
            elif l.startswith('U:'): cur['Uniq']=l.split('=',1)[1].strip('"') if '=' in l else ''
        if cur: self._ai(cur)

    def _ai(self,d):
        nm=d.get('Name','')
        if not nm or 'Power Button' in nm: return
        h=d.get('Handlers','')
        cat='Устройства HID'
        if any(x in h for x in['mouse','mice']): cat='Мыши'
        elif any(x in h for x in['kbd','keyboard']): cat='Клавиатуры'
        dev=Dev(nm,cat,'input','','Работает нормально',f'INPUT\\{nm[:50]}','',icon_name=self.CI.get(cat,'input-gaming'),location=d.get('Phys',''))
        dev.details={'Имя':nm,'Обработчики':h,'Физ.расположение':d.get('Phys','N/A')}
        if d.get('Uniq'): dev.details['Уникальный ID']=d['Uniq']
        self.devices.append(dev)

    def _sound(self):
        raw=self._r('cat /proc/asound/cards')
        if not raw: return
        for l in raw.split('\n'):
            m=re.search(r'\[(\d+)\]\s+([^\s]+)\s*:\s+(.*)',l)
            if not m: continue
            cn,sn,ds=m.groups()
            dev=Dev(ds.strip(),'Звуковые, игровые и видеоустройства','sound','','Работает нормально',
                    f'SOUND\\CARD{cn}',f'card {cn}: {sn}',icon_name='audio-card')
            det={'Карта':cn,'Краткое имя':sn,'Описание':ds}
            cd=self._rf(f'/proc/asound/card{cn}/codec#0')
            if cd: det['Кодек']='\n'.join(cd.split('\n')[:5])[:200]
            ci=self._rf(f'/sys/class/sound/card{cn}/id')
            if ci: det['ID карты']=ci
            dev.details=det
            self.devices.append(dev)

    def _cpu(self):
        raw=self._r('cat /proc/cpuinfo')
        if not raw: return
        th=[]; cur={}
        for l in raw.split('\n'):
            if l.startswith('processor'):
                if cur: th.append(cur)
                cur={'processor':l.split(':')[1].strip() if ':' in l else '0'}
            elif l.startswith('model name'): cur['mn']=l.split(':')[1].strip() if ':' in l else ''
            elif l.startswith('physical id'): cur['pid']=l.split(':')[1].strip() if ':' in l else '0'
            elif l.startswith('core id'): cur['cid']=l.split(':')[1].strip() if ':' in l else ''
            elif l.startswith('cpu MHz'): cur['mhz']=l.split(':')[1].strip() if ':' in l else ''
            elif l.startswith('cache size'): cur['cache']=l.split(':')[1].strip() if ':' in l else ''
            elif l.startswith('cpu cores'): cur['cores']=l.split(':')[1].strip() if ':' in l else ''
            elif l.startswith('siblings'): cur['sib']=l.split(':')[1].strip() if ':' in l else ''
            elif l.startswith('vendor_id'): cur['vid']=l.split(':')[1].strip() if ':' in l else ''
            elif l.startswith('stepping'): cur['step']=l.split(':')[1].strip() if ':' in l else ''
            elif l.startswith('microcode'): cur['ucode']=l.split(':')[1].strip() if ':' in l else ''
            elif l.startswith('bogomips'): cur['bogo']=l.split(':')[1].strip() if ':' in l else ''
        if cur: th.append(cur)
        if not th: return
        tt=len(th); mn=th[0].get('mn','Unknown'); vid=th[0].get('vid','')
        cc=int(th[0].get('cores','0')) if th[0].get('cores','0').isdigit() else 0
        sib=int(th[0].get('sib',str(tt))) if th[0].get('sib','').isdigit() else tt
        uc=th[0].get('ucode','')
        cm={}
        for t in th:
            pid=t.get('pid','0'); cid=t.get('cid','').strip()
            if cid:
                k=(pid,cid)
                if k not in cm: cm[k]=[]
                cm[k].append(t)
        if not cm:
            tpc=sib if sib>0 else (tt//cc if cc>0 else 1)
            for t in th:
                pr=int(t.get('processor','0')); ci=pr//tpc; pid=t.get('pid','0')
                k=(pid,str(ci))
                if k not in cm: cm[k]=[]
                cm[k].append(t)
        if cc>0 and len(cm)!=cc:
            tpc=tt//cc if cc>0 else 1; cm={}
            for t in th:
                pr=int(t.get('processor','0')); ci=pr//tpc; pid=t.get('pid','0')
                k=(pid,str(ci))
                if k not in cm: cm[k]=[]
                cm[k].append(t)
        pcc=len(cm); sk=set(t.get('pid','0') for t in th)
        for ci,((pid,cid),tl) in enumerate(sorted(cm.items())):
            mhz=tl[0].get('mhz',''); cache=tl[0].get('cache','')
            step=tl[0].get('step',''); bogo=tl[0].get('bogo','')
            dev=Dev(mn,'Процессоры','cpu','','Работает нормально',f'CPU\\CORE_{pid}_{cid}',vid,icon_name='cpu')
            dev.details={'Модель':mn,'Производитель':vid,
                'Физическое ядро':f'{ci} (physical_id={pid}, core_id={cid})',
                'Всего физических ядер':str(pcc),'Всего логических процессоров':str(tt),
                'Физических сокетов':str(len(sk)),'Частота':f'{mhz} МГц' if mhz else 'N/A',
                'Кэш L2':cache or 'N/A','Степпинг':step or 'N/A','BogoMIPS':bogo or 'N/A'}
            if uc: dev.details['Микрокод']=uc
            dev.resources={'Ядро':f'Physical {pid}, Core {cid}','Потоков на ядро':str(len(tl))}
            self.devices.append(dev)

    def _monitors(self):
        dd=Path('/sys/class/drm')
        if not dd.exists(): return
        for e in sorted(dd.iterdir()):
            if not e.is_dir(): continue
            nm=e.name
            if not re.match(r'card\d+-(DP|HDMI|DVI|VGA|eDP|LVDS|DSI)',nm): continue
            st=self._rf(e/'status')
            if st!='connected': continue
            ct=re.search(r'-(DP|HDMI|DVI|VGA|eDP|LVDS|DSI)',nm)
            ctype=ct.group(1) if ct else ''
            ep=e/'edid'; mn=''; sn=''; vn=''
            if ep.exists() and ep.stat().st_size>=128:
                es=self._r(f'strings {ep}')
                for s in es.split('\n'):
                    s=s.strip()
                    if 2<=len(s)<=40 and any(c.isalpha() for c in s) and not s.startswith('Linux') and 'Monitor' in s:
                        mn=s; break
                if not mn:
                    for s in es.split('\n'):
                        s=s.strip()
                        if 3<=len(s)<=40 and all(32<=ord(c)<=126 for c in s) and not s.startswith('Linux'):
                            mn=s; break
                if not mn:
                    try:
                        d=ep.read_bytes()
                        if len(d)>=128:
                            vid=(d[8]<<8)|d[9]
                            v1=chr(64+((vid>>10)&0x1F)); v2=chr(64+((vid>>5)&0x1F)); v3=chr(64+(vid&0x1F))
                            vn=v1+v2+v3
                            sno=struct.unpack('<I',d[12:16])[0]
                            if sno: sn=str(sno)
                            for off in range(54,127,18):
                                if off+18>len(d): break
                                bl=d[off:off+18]
                                if bl[0]==0 and bl[1]==0 and bl[3]==0xFC:
                                    nb=bl[5:18]; name=''
                                    for b in nb:
                                        if b==0x0A: break
                                        if 32<=b<=126: name+=chr(b)
                                    if name.strip(): mn=name.strip(); break
                    except: pass
            dn=mn or f'{ctype} Monitor'
            mr=self._rf(e/'modes'); modes=[]
            if mr:
                for m in mr.split('\n'):
                    m=m.strip()
                    if m and m not in modes: modes.append(m)
                modes=modes[:5]
            dev=Dev(dn,'Мониторы','drm','','Подключён',f'MONITOR\\{nm}',nm,vn,icon_name='display-projector',serial=sn)
            det={'Подключение':nm,'Тип порта':ctype,'Статус':'Подключён'}
            if vn: det['Производитель']=vn
            if mn: det['Модель']=mn
            if sn: det['Серийный номер']=sn
            if modes: det['Режимы']=', '.join(modes[:3]); det['Нативное разрешение']=modes[0]
            dev.details=det
            self.devices.append(dev)

    def _battery(self):
        ps=Path('/sys/class/power_supply')
        if not ps.exists(): return
        for e in ps.iterdir():
            if not e.is_dir() or not(e.name.startswith('BAT') or e.name.startswith('CMB')): continue
            nm=self._rf(e/'name') or e.name; st=self._rf(e/'status')
            cap=self._rf(e/'capacity'); tech=self._rf(e/'technology')
            volt=self._rf(e/'voltage_now')
            dev=Dev(nm,'Батареи','power_supply','','Работает нормально',f'BATTERY\\{nm}',icon_name='battery')
            dev.details={'Статус':st or 'N/A','Заряд':f'{cap}%' if cap else 'N/A','Технология':tech or 'N/A'}
            if volt and volt.isdigit(): dev.details['Напряжение']=f'{int(volt)/1000000:.2f} В'
            self.devices.append(dev)

    def _bt(self):
        raw=self._r('bluetoothctl list')
        if raw:
            for l in raw.split('\n'):
                if 'Controller' in l:
                    p=l.split()
                    if len(p)>=3:
                        mac=p[1]; nm=' '.join(p[2:])
                        dev=Dev(nm,'Bluetooth','bluetooth','','Работает нормально',f'BT\\{mac}',icon_name='bluetooth')
                        dev.details={'MAC':mac,'Имя':nm}
                        self.devices.append(dev)
            return
        ls=self._r('lsusb')
        if ls and 'bluetooth' in ls.lower():
            dev=Dev('Bluetooth Adapter','Bluetooth','bluetooth','','Работает нормально','BT\\ADAPTER',icon_name='bluetooth')
            self.devices.append(dev)

    def _webcam(self):
        raw=self._r('v4l2-ctl --list-devices')
        if raw:
            cn=''
            for l in raw.split('\n'):
                if not l.startswith('\t'): cn=l.strip()
                elif cn and '/dev/video' in l:
                    dp=l.strip()
                    dev=Dev(cn,'Веб-камеры','video4linux','','Работает нормально',f'V4L2\\{cn[:50]}',dp,icon_name='camera-web')
                    self.devices.append(dev)
            return
        for vp in sorted(Path('/dev').glob('video*')):
            dev=Dev(vp.name,'Веб-камеры','video4linux','','Работает нормально',f'V4L2\\{vp.name}',str(vp),icon_name='camera-web')
            self.devices.append(dev)

    def _prn(self):
        raw=self._r('lpstat -p')
        if raw:
            for l in raw.split('\n'):
                if ' is ' in l:
                    p=l.split(' is ',1); pn=p[0].replace('printer ','').strip(); ps=p[1].strip() if len(p)>1 else ''
                    dev=Dev(pn,'Очереди печати','printer','',ps,f'PRN\\{pn}',icon_name='printer')
                    dev.details={'Статус':ps}
                    self.devices.append(dev)

    def _cat(self):
        self.categories={}
        for d in self.devices: self.categories.setdefault(d.category,[]).append(d)

# ============================================================================
# GTK4 UI
# ============================================================================

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self,app):
        super().__init__(application=app,title='Диспетчер устройств',default_width=1100,default_height=750)
        self.set_opacity(1.0)
        self.add_css_class('solid-background')
        ip=os.path.join(os.path.dirname(os.path.abspath(__file__)),'build','icons','linux','icon.png')
        if os.path.exists(ip):
            try: self.set_icon_from_file(ip)
            except: pass
        self.sc=Scanner(); self.cats={}; self.icon_size=16
        self.is_light=self._detect_light()
        self._css()
        self._build()
        # Применяем непрозрачный фон после realise
        self.connect('realize', self._on_realize)
        self._scan()
        Gtk.Settings.get_default().connect('notify::gtk-application-prefer-dark-theme',self._theme_change)

    def _on_realize(self,w):
        pass

    def _detect_light(self):
        s=Gtk.Settings.get_default()
        return not s.get_property('gtk-application-prefer-dark-theme') if s else True

    def _css(self):
        bg = '#1c1c1e' if not self.is_light else '#f5f5f7'
        hdr = '#262628' if not self.is_light else '#eee'
        tv = '#141416' if not self.is_light else '#ffffff'
        bar = '#262628' if not self.is_light else '#eee'
        fg = '#ffffff' if not self.is_light else '#1a1a1a'
        sel = '#005a9e' if not self.is_light else '#cde4ff'
        pop = '#262628' if not self.is_light else '#ffffff'
        btn = '#323234' if not self.is_light else '#f0f0f0'
        entry = '#1e1e20' if not self.is_light else '#ffffff'
        sep = 'rgba(255,255,255,0.06)' if not self.is_light else 'rgba(0,0,0,0.08)'
        brd = 'rgba(255,255,255,0.06)' if not self.is_light else 'rgba(0,0,0,0.1)'
        hvr = 'rgba(255,255,255,0.06)' if not self.is_light else 'rgba(0,0,0,0.04)'

        css = f"""
        window {{ background-color: {bg}; color: {fg}; }}
        .solid-background {{ background-color: {bg}; color: {fg}; }}
        .opaque-bg {{ background-color: {bg}; color: {fg}; }}
        headerbar {{ background-color: {hdr}; border-bottom: 1px solid {brd}; }}
        treeview {{ background-color: {tv}; color: {fg}; }}
        treeview cell {{ color: {fg}; }}
        treeview:selected {{ background-color: {sel}; color: {fg}; }}
        treeview:hover {{ background-color: {hvr}; }}
        .statusbar {{ background-color: {bar}; color: {fg}; border-top: 1px solid {brd}; padding: 4px 8px; }}
        popover, menu {{ background-color: {pop}; color: {fg}; }}
        button {{ background-color: {btn}; color: {fg}; }}
        entry {{ background-color: {entry}; color: {fg}; }}
        label {{ color: {fg}; }}
        frame, notebook {{ background-color: {bg}; }}
        notebook > stack {{ background-color: {tv}; }}
        paned > separator {{ background-color: {sep}; min-width: 2px; }}
        scrolledwindow {{ background-color: {tv}; }}
        """
        p=Gtk.CssProvider(); p.load_from_string(css)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),p,800)

    def _theme_change(self,*a):
        self.is_light=self._detect_light(); self._build_tree()

    def _setup_actions(self):
        ag=Gio.SimpleActionGroup()
        def mk(cb):
            return lambda a,p: cb()
        for n,cb in [('refresh',self._scan),('export',self._export),('quit',lambda: self.close()),
                      ('enable',lambda: self._toggle(True)),('disable',lambda: self._toggle(False)),
                      ('large',lambda: self._set_sz(32)),('small',lambda: self._set_sz(16)),
                      ('about',self._about)]:
            a=Gio.SimpleAction(name=n)
            a.connect('activate',mk(cb))
            ag.add_action(a)
        self.insert_action_group('app',ag)

    def _build(self):
        self._setup_actions()

        # Header bar
        hb=Adw.HeaderBar(show_start_title_buttons=True,show_end_title_buttons=True)
        self.set_titlebar(hb)
        hb.set_title_widget(Gtk.Label(label='Диспетчер устройств',valign=Gtk.Align.CENTER))

        # Меню
        def mbtn(label,items):
            m=Gio.Menu()
            for lbl,act in items:
                m.append(lbl,f'app.{act}')
            p=Gtk.PopoverMenu(); p.set_menu_model(m)
            b=Gtk.MenuButton(label=label,popover=p)
            hb.pack_start(b)

        mbtn('Справка',[('О программе','about')])
        mbtn('Вид',[('Крупные значки','large'),('Мелкие значки','small')])
        mbtn('Действие',[('Обновить конфигурацию','refresh'),('Включить устройство','enable'),('Отключить устройство','disable')])
        mbtn('Файл',[('Обновить','refresh'),('Экспорт...','export'),('Выход','quit')])

        # Оборачиваем всё в opaque box
        opaque=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        opaque.add_css_class('solid-background')
        self.set_child(opaque)

        # Поиск
        sb=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=5)
        sb.set_margin_start(8); sb.set_margin_end(8); sb.set_margin_top(4); sb.set_margin_bottom(4)
        opaque.append(sb)
        sb.append(Gtk.Image.new_from_icon_name('edit-find'))
        self.se=Gtk.Entry(); self.se.set_placeholder_text('Поиск устройств...')
        self.se.connect('changed',self._search); sb.append(self.se)
        cb=Gtk.Button.new_from_icon_name('edit-clear')
        cb.connect('clicked',lambda w:self.se.set_text('')); sb.append(cb)

        # Дерево
        sw=Gtk.ScrolledWindow(); sw.set_hexpand(True); sw.set_vexpand(True); opaque.append(sw)
        self.tv=Gtk.TreeView(); self.tv.set_headers_visible(False)
        self.tv.connect('row-activated',self._dbl)
        gc=Gtk.GestureClick()
        gc.set_button(3); gc.connect('pressed',self._rclick); self.tv.add_controller(gc)
        # Стрелка (Pixbuf) + иконка + текст
        r_exp=Gtk.CellRendererPixbuf()
        r_exp.set_property('xpad',2); r_exp.set_property('ypad',2)
        r_icon=Gtk.CellRendererPixbuf()
        r_text=Gtk.CellRendererText()
        r_text.set_property('ellipsize',Pango.EllipsizeMode.END)
        r_text.set_property('xpad',6)
        col=Gtk.TreeViewColumn()
        col.pack_start(r_exp,False)
        col.pack_start(r_icon,False)
        col.add_attribute(r_icon,'icon-name',1)
        col.pack_start(r_text,True)
        col.add_attribute(r_text,'text',0)
        col.add_attribute(r_text,'weight',2)
        col.add_attribute(r_text,'weight-set',3)
        col.set_cell_data_func(r_exp,self._expander_draw)
        col.set_cell_data_func(r_icon,self._ricon)
        self.tv.append_column(col)
        self.st=Gtk.TreeStore(str,str,int,bool,bool,bool)
        self.tv.set_model(self.st)
        sw.set_child(self.tv)
        # Обработка клика по стрелке
        gc2=Gtk.GestureClick(); gc2.set_button(1)
        gc2.connect('pressed',self._on_tree_click)
        self.tv.add_controller(gc2)

        # Статусбар
        self.sb=Gtk.Label(css_classes=['statusbar']); opaque.append(self.sb)

    def _ricon(self,col,cell,model,it,data):
        nm=model[it][1]
        try:
            th=Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            info=th.lookup_icon(nm,[],self.icon_size,1,Gtk.TextDirection.NONE,Gtk.IconLookupFlags.FORCE_SYMBOLIC)
            cell.set_property('pixbuf',info.load_icon())
        except: cell.set_property('pixbuf',None)

    def _expander_draw(self,col,cell,model,it,data):
        has=model[it][4]; exp=model[it][5]
        if has:
            cell.set_property('icon-name','pan-down-symbolic' if exp else 'pan-end-symbolic')
            cell.set_property('visible',True)
        else:
            cell.set_property('visible',False)
            cell.set_property('icon-name',None)

    def _on_tree_click(self,gc,npress,x,y):
        """Обработка левого клика по дереву"""
        path_info=self.tv.get_path_at_pos(x,y)
        if not path_info: return False
        path,cols,cell_x,cell_y=path_info
        if cell_x < 24:
            it=self.st.get_iter(path)
            model=self.tv.get_model()
            if it and model and model[it][4]:
                if self.tv.row_expanded(path):
                    self.tv.collapse_row(path)
                    self.st.set_value(it,5,False)
                else:
                    self.tv.expand_row(path,False)
                    self.st.set_value(it,5,True)
                return True
        return False

    def _ricon(self,col,cell,model,it,data):
        nm=model[it][1]
        try:
            th=Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            info=th.lookup_icon(nm,[],self.icon_size,1,Gtk.TextDirection.NONE,Gtk.IconLookupFlags.FORCE_SYMBOLIC)
            cell.set_property('pixbuf',info.load_icon())
        except: cell.set_property('pixbuf',None)

    def _set_sz(self,sz):
        self.icon_size=sz; self._build_tree()

    def _scan(self):
        self.sb.set_text('Сканирование...')
        t=threading.Thread(target=self._do_scan); t.daemon=True; t.start()

    def _do_scan(self):
        self.cats=self.sc.scan_all()
        GLib.idle_add(self._build_tree)
        GLib.idle_add(self._done)

    def _toggle_expander(self, renderer, path_str):
        """Клик по стрелке — развернуть/свернуть"""
        path = Gtk.TreePath.new_from_string(path_str)
        it=self.st.get_iter(path)
        if self.tv.row_expanded(path):
            self.tv.collapse_row(path)
            if it: self.st.set_value(it,5,False)
        else:
            self.tv.expand_row(path, False)
            if it: self.st.set_value(it,5,True)

    def _build_tree(self):
        self.st.clear()
        for cat in sorted(self.cats):
            devs=self.cats[cat]
            if not devs: continue
            ic=self.sc.CI.get(cat,'computer')
            pi=self.st.append(None,[f'{cat} ({len(devs)})',ic,800,True,True,False])
            seen=set()
            for d in devs:
                if d.name in seen: continue
                seen.add(d.name)
                self.st.append(pi,[d.name,d.icon_name,400,True,False,False])

    def _done(self):
        t=sum(len(v) for v in self.cats.values())
        self.sb.set_text(f'Найдено {t} устройств в {len(self.cats)} категориях')

    def _dbl(self,tv,path,col):
        m=tv.get_model(); it=m.get_iter(path)
        if it and m.iter_parent(it):
            nm=m[it][0]; d=self._find(nm)
            if d: Props(self,d).present()

    def _rclick(self,gc,npress,x,y):
        tv=gc.get_widget()
        p=tv.get_path_at_pos(x,y)
        if p:
            tv.get_selection().select_path(p[0])
            pop=self._menu(p[0])
            pop.set_parent(tv)
            # Позиционируем ниже и правее клика, чтобы не перекрывать элемент
            rect = Gdk.Rectangle()
            rect.x = int(x) + 5
            rect.y = int(y) + 20
            rect.width = 1
            rect.height = 1
            pop.set_pointing_to(rect)
            pop.set_position(Gtk.PositionType.BOTTOM)
            pop.popup()
            return True
        return False

    def _menu(self,path):
        pop=Gtk.Popover()
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_margin_start(4); box.set_margin_end(4)
        box.set_margin_top(4); box.set_margin_bottom(4)
        pop.set_child(box)
        it=self.tv.get_model().get_iter(path)
        if not it: return pop
        nm=self.tv.get_model()[it][0]

        def add_btn(label,cb):
            b=Gtk.Button(label=label,halign=Gtk.Align.FILL)
            b.get_style_context().add_class('flat')
            b.connect('clicked',lambda w: (cb(), pop.popdown()))
            box.append(b)

        def add_sep():
            box.append(Gtk.Separator())

        if self.tv.get_model().iter_parent(it):
            # Устройство
            add_btn('Включить', lambda: self._toggle(True))
            add_btn('Отключить', lambda: self._toggle(False))
            add_sep()
            add_btn('Свойства', lambda: Props(self,self._find(nm)).present() if self._find(nm) else None)
        else:
            # Категория
            add_btn('Развернуть', lambda: self.tv.expand_row(path,False))
            add_btn('Свернуть', lambda: self.tv.collapse_row(path))
            add_sep()
            add_btn('Обновить', lambda: self._scan())

        return pop

    def _toggle(self,en):
        sel=self.tv.get_selection(); m,it=sel.get_selected()
        if not it or not m.iter_parent(it): return
        nm=m[it][0]; d=self._find(nm)
        if not d: return
        ok=False
        if d.subsystem=='usb' and d.location:
            bd=d.location.split(',')[0].replace('Bus ','') if ',' in d.location else ''
            if bd:
                ap=f'/sys/bus/usb/devices/{bd}/authorized'
                try:
                    with open(ap,'w') as f: f.write('1' if en else '0'); ok=True
                except PermissionError: self._err('Нужны права root'); return
                except: pass
        if not ok and d.sysfs_path:
            pw=os.path.join(d.sysfs_path,'power','control')
            if os.path.exists(pw):
                try:
                    with open(pw,'w') as f: f.write('on' if en else 'auto'); ok=True
                except PermissionError: self._err('Нужны права root'); return
                except: pass
        if not ok and d.subsystem=='pci' and d.driver:
            bp=f'/sys/bus/pci/drivers/{d.driver}/{"unbind" if not en else "bind"}'
            di=d.device_id.replace('PCI\\','') if d.device_id else ''
            if di and os.path.exists(bp):
                try:
                    with open(bp,'w') as f: f.write(di); ok=True
                except PermissionError: self._err('Нужны права root'); return
                except: pass
        d.enabled=en; d.status='Работает нормально' if en else 'Отключено'; self._build_tree()

    def _err(self,msg):
        d=Gtk.MessageDialog(self,Gtk.DialogFlags.MODAL,Gtk.MessageType.ERROR,Gtk.ButtonsType.OK,msg)
        d.run(); d.destroy()

    def _search(self,e):
        txt=e.get_text().strip()
        if not txt: self._build_tree(); return
        tl=txt.lower(); self.st.clear()
        for cat in sorted(self.cats):
            dv=[d for d in self.cats[cat] if tl in d.name.lower()]
            if not dv: continue
            ic=self.sc.CI.get(cat,'computer')
            pi=self.st.append(None,[f'{cat} ({len(dv)})',ic,800,True,True,False])
            self.tv.expand_row(self.st.get_path(pi),False)
            seen=set()
            for d in dv:
                if d.name in seen: continue
                seen.add(d.name); self.st.append(pi,[d.name,d.icon_name,400,True,False,False])

    def _export(self,w=None,p=None):
        d=Gtk.FileDialog()
        def cb(o,r):
            fn=r.get_path()
            if not fn: return
            ext=fn.rsplit('.',1)[-1].lower()
            if ext=='json': self._ej(fn)
            elif ext=='html': self._eh(fn)
            else: self._et(fn)
        d.save(self,None,cb)

    def _ej(self,fn):
        with open(fn,'w') as f: json.dump({'system':self.sc.sys_info,'devices':[d.to_dict() for d in self.sc.devices],'date':datetime.now().isoformat()},f,ensure_ascii=False,indent=2)
    def _et(self,fn):
        with open(fn,'w') as f:
            f.write(f'Дата: {datetime.now()}\n')
            for k,v in self.sc.sys_info.items(): f.write(f'{k}: {v}\n')
            f.write('\n')
            for cat,dv in sorted(self.cats.items()):
                f.write(f'\n{cat} ({len(dv)}):\n')
                for d in dv:
                    f.write(f'  {d.name}\n')
                    if d.driver: f.write(f'    Драйвер: {d.driver}\n')
                    for dk,dv2 in d.details.items(): f.write(f'    {dk}: {dv2}\n')
    def _eh(self,fn):
        h='<html><body>'
        for cat,dv in sorted(self.cats.items()):
            h+=f'<h2>{cat}</h2><table border=1><tr><th>Устройство</th><th>Драйвер</th><th>Статус</th></tr>'
            for d in dv: h+=f'<tr><td>{d.name}</td><td>{d.driver or "Встроен"}</td><td>{d.status}</td></tr>'
            h+='</table>'
        h+='</body></html>'
        with open(fn,'w') as f: f.write(h)

    def _about(self,w=None,p=None):
        d=Adw.AboutWindow(transient_for=self,modal=True,
            application_name='Диспетчер устройств Linux',application_icon='system-hardware',
            version='1.0.0',copyright='© 2026 dvytvs',
            license_type=Gtk.License.MIT_X11,
            website='https://github.com/dvytvs/Linux-Device-Manager.git',
            developers=['dvytvs'],
            comments='Диспетчер устройств для Linux\nРеальные данные из системы')
        ip=os.path.join(os.path.dirname(os.path.abspath(__file__)),'build','icons','linux','icon.png')
        if os.path.exists(ip):
            try: d.set_application_icon_from_file(ip)
            except: pass
        d.present()

    def _find(self,nm):
        for dv in self.cats.values():
            for d in dv:
                if d.name==nm: return d
        return None


class Props(Gtk.Window):
    def __init__(self,parent,dev):
        super().__init__(title=f'Свойства: {dev.name}',transient_for=parent,modal=True,default_width=900,default_height=600)
        self.dev=dev
        self.add_css_class('solid-background')
        # Главный box с отступами
        outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,margin_start=16,margin_end=16,margin_top=16,margin_bottom=16)
        self.set_child(outer)
        nb=Gtk.Notebook(); outer.append(nb)
        nb.append_page(self._tab_gen(),Gtk.Label(label='Общие'))
        nb.append_page(self._tab_drv(),Gtk.Label(label='Драйвер'))
        nb.append_page(self._tab_res(),Gtk.Label(label='Ресурсы'))
        nb.append_page(self._tab_det(),Gtk.Label(label='Сведения'))
        btn=Gtk.Button(label='OK',halign=Gtk.Align.END,margin_top=12)
        btn.set_size_request(100,-1)
        btn.connect('clicked',lambda w:self.destroy()); outer.append(btn)

    def _row(self,key,val):
        r=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=16)
        k=Gtk.Label(label=f'<b>{key}:</b>',use_markup=True,xalign=0,halign=Gtk.Align.START,valign=Gtk.Align.START)
        k.set_size_request(200,-1)
        r.append(k)
        vl=Gtk.Label(label=str(val),xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD,halign=Gtk.Align.START,valign=Gtk.Align.START)
        vl.set_hexpand(True)
        r.append(vl)
        r.set_margin_bottom(6)
        return r

    def _tab_gen(self):
        sw=Gtk.ScrolledWindow(); sw.set_hexpand(True); sw.set_vexpand(True)
        b=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16,margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
        sw.set_child(b)
        # Заголовок
        h=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=20)
        img=Gtk.Image.new_from_icon_name(self.dev.icon_name); img.set_pixel_size(64)
        h.append(img)
        v=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        v.append(Gtk.Label(label=f'<big><b>{self.dev.name}</b></big>',use_markup=True,xalign=0))
        v.append(Gtk.Label(label=f'Состояние: {self.dev.status}',xalign=0))
        v.append(Gtk.Label(label=f'Тип: {self.dev.category}',xalign=0))
        v.append(Gtk.Label(label=f'Расположение: {self.dev.location or "N/A"}',xalign=0))
        h.append(v); b.append(h)
        # Сведения
        if self.dev.details:
            f=Gtk.Frame(label='Сведения'); fb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0,margin_start=12,margin_end=12,margin_top=8,margin_bottom=8)
            for k,v in self.dev.details.items():
                if v and len(str(v))<300: fb.append(self._row(k,v))
            f.set_child(fb); b.append(f)
        return sw

    def _tab_drv(self):
        sw=Gtk.ScrolledWindow(); sw.set_hexpand(True); sw.set_vexpand(True)
        b=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
        sw.set_child(b)
        f=Gtk.Frame(label='Драйвер'); fb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0,margin_start=12,margin_end=12,margin_top=8,margin_bottom=8)
        dr=self.dev.driver or 'Встроен в ядро Linux'
        items=[('Драйвер',dr)]
        for k in['modinfo:version','modinfo:description','modinfo:author','modinfo:filename','Модули ядра','Драйвер ядра','Драйвер','Версия драйвера','Прошивка']:
            if self.dev.details.get(k): items.append((k.replace('modinfo:',''),self.dev.details[k]))
        for l,v in items: fb.append(self._row(l,v))
        f.set_child(fb); b.append(f)
        return sw

    def _tab_res(self):
        sw=Gtk.ScrolledWindow(); sw.set_hexpand(True); sw.set_vexpand(True)
        b=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
        sw.set_child(b)
        if self.dev.resources:
            for k,v in self.dev.resources.items(): b.append(self._row(k,v))
        else: b.append(Gtk.Label(label='Ресурсы не указаны',margin_top=20))
        return sw

    def _tab_det(self):
        sw=Gtk.ScrolledWindow(); sw.set_hexpand(True); sw.set_vexpand(True)
        b=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0,margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
        sw.set_child(b)
        if self.dev.details:
            for k,v in self.dev.details.items():
                if v and len(str(v))<300: b.append(self._row(k,v))
        else: b.append(Gtk.Label(label='Нет сведений',margin_top=20))
        return sw


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='com.dvytvs.device-manager',flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        w=MainWindow(self); w.present()


if __name__=='__main__':
    app=App(); app.run(sys.argv)
