Name:           linux-device-manager
Version:        1.0.0
Release:        1%{?dist}
Summary:        Device Manager for Linux
License:        MIT
URL:            https://github.com/dvytvs/Linux-Device-Manager
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  desktop-file-utils
Requires:       python3, python3-gobject, gtk3, libadwaita

%description
A full-featured device manager for Linux inspired by Windows 11 Device Manager.
Scans and displays PCI, USB, network, disk, audio, and other devices.

%prep
%setup -q

%build
# No build step needed for Python script

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/%{name}
mkdir -p %{buildroot}%{_datadir}/applications
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/512x512/apps

cp device_manager.py %{buildroot}%{_datadir}/%{name}/

cat > %{buildroot}%{_bindir}/%{name} << 'EOFSCRIPT'
#!/usr/bin/env bash
exec python3 %{_datadir}/%{name}/device_manager.py "$@"
EOFSCRIPT
chmod +x %{buildroot}%{_bindir}/%{name}

cp linux-device-manager.desktop %{buildroot}%{_datadir}/applications/
cp build/icons/linux/icon.png %{buildroot}%{_datadir}/icons/hicolor/512x512/apps/%{name}.png

%files
%{_bindir}/%{name}
%{_datadir}/%{name}/
%{_datadir}/applications/%{name}.desktop
%{_datadir}/icons/hicolor/512x512/apps/%{name}.png

%changelog
* Сб апр 04 2026 dvytvs <dvytvs@github.com> - 1.0.0-1
- Initial package
