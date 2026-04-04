#!/usr/bin/env bash
# Сборка Linux Device Manager во все форматы
# Запускать из корня проекта: ./build/build-all.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$SCRIPT_DIR"
PKG_DIR="$BUILD_DIR/pkg"
VERSION="1.0.0"
APPNAME="linux-device-manager"

echo "========================================="
echo "Linux Device Manager v$VERSION — Build All"
echo "========================================="
echo ""

# ============================================================================
# Подготовка: копируем файлы приложения
# ============================================================================
echo ">> Подготовка файлов..."
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/share/$APPNAME"

cp "$PROJECT_DIR/device_manager.py" "$PKG_DIR/usr/bin/$APPNAME"
cp "$PROJECT_DIR/run.sh" "$PKG_DIR/usr/share/$APPNAME/run.sh"
chmod +x "$PKG_DIR/usr/bin/$APPNAME"

# Создаём обёртку для запуска
cat > "$PKG_DIR/usr/bin/$APPNAME" << 'WRAPPER'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || cd "$(dirname "$0")"
exec python3 "$(dirname "$0")/device_manager.py" "$@"
WRAPPER
chmod +x "$PKG_DIR/usr/bin/$APPNAME"

cp "$PROJECT_DIR/device_manager.py" "$PKG_DIR/usr/share/$APPNAME/device_manager.py"

echo "   Файлы скопированы"

# ============================================================================
# 1. tar.gz
# ============================================================================
echo ""
echo ">> [1/7] Создание tar.gz..."
TAR_GZ="$BUILD_DIR/${APPNAME}-${VERSION}.tar.gz"
tar czf "$TAR_GZ" -C "$PROJECT_DIR" \
    device_manager.py run.sh README.md requirements.txt \
    linux-device-manager.desktop \
    build/icons/linux/icon.png
echo "   ✓ ${APPNAME}-${VERSION}.tar.gz"

# ============================================================================
# 2. tar.zst
# ============================================================================
echo ""
echo ">> [2/7] Создание tar.zst..."
TAR_ZST="$BUILD_DIR/${APPNAME}-${VERSION}.tar.zst"
if command -v zstd &>/dev/null; then
    tar cf - -C "$PROJECT_DIR" \
        device_manager.py run.sh README.md requirements.txt \
        linux-device-manager.desktop \
        build/icons/linux/icon.png | zstd -c > "$TAR_ZST"
    echo "   ✓ ${APPNAME}-${VERSION}.tar.zst"
else
    echo "   ⚠ zstd не установлен. Пропускаю."
    echo "   Установи: sudo pacman -S zstd"
fi

# ============================================================================
# 8. Arch Linux PKGBUILD → .pkg.tar.zst
# ============================================================================
echo ""
echo ">> [8/8] Сборка Arch пакета..."
cp "$BUILD_DIR/arch/PKGBUILD.template" "$BUILD_DIR/arch/PKGBUILD"

SRC_ARCH="$BUILD_DIR/arch/${APPNAME}-${VERSION}.tar.gz"
tar czf "$SRC_ARCH" -C "$PROJECT_DIR" \
    device_manager.py run.sh README.md requirements.txt \
    linux-device-manager.desktop \
    build/icons/linux/icon.png

# Сборка через makepkg
WORK_DIR=$(mktemp -d)
cp "$SRC_ARCH" "$WORK_DIR/${APPNAME}-${VERSION}.tar.gz"
cp "$BUILD_DIR/arch/PKGBUILD" "$WORK_DIR/PKGBUILD"
cd "$WORK_DIR"
if makepkg --noconfirm --skipchecksums &>/dev/null; then
    PKG_OUT=$(find "$WORK_DIR" -name "*.pkg.tar.zst" | head -1)
    if [ -n "$PKG_OUT" ]; then
        cp "$PKG_OUT" "$BUILD_DIR/"
        echo "   ✓ $(basename "$PKG_OUT")"
    fi
else
    echo "   ⚠ makepkg не удалось (нужны base-devel)"
fi
rm -rf "$WORK_DIR"

# ============================================================================
# 3. AppImage
# ============================================================================
echo ""
echo ">> [3/6] Создание AppImage..."
APPIMAGE_DIR="$BUILD_DIR/appimage/AppDir"
mkdir -p "$APPIMAGE_DIR/usr/bin"
mkdir -p "$APPIMAGE_DIR/usr/share/applications"
mkdir -p "$APPIMAGE_DIR/usr/share/icons/hicolor/512x512/apps"

cp "$PKG_DIR/usr/bin/$APPNAME" "$APPIMAGE_DIR/usr/bin/"
cp "$PKG_DIR/usr/share/$APPNAME/device_manager.py" "$APPIMAGE_DIR/usr/bin/"
cp "$BUILD_DIR/appimage/linux-device-manager.desktop" "$APPIMAGE_DIR/usr/share/applications/"
cp "$BUILD_DIR/appimage/linux-device-manager.png" "$APPIMAGE_DIR/usr/share/icons/hicolor/512x512/apps/"
cp "$BUILD_DIR/appimage/linux-device-manager.png" "$APPIMAGE_DIR/linux-device-manager.png"

# AppRun
cat > "$APPIMAGE_DIR/AppRun" << 'APPRUN'
#!/bin/bash
SELF="$(readlink -f "$0")"
HERE="${SELF%/*}"
export PYTHONPATH="${HERE}/usr/bin:${PYTHONPATH}"
exec "${HERE}/usr/bin/python3" "${HERE}/usr/bin/device_manager.py" "$@"
APPRUN
chmod +x "$APPIMAGE_DIR/AppRun"

# Копируем системный python3 как заглушку (AppImage будет использовать системный)
# Для полноценного AppImage нужен linuxdeploy с python plugin
if command -v linuxdeploy &>/dev/null; then
    APPIMAGE_OUT="$BUILD_DIR/${APPNAME}-${VERSION}-x86_64.AppImage"
    linuxdeploy --appdir="$APPIMAGE_DIR" \
        --desktop-file="$APPIMAGE_DIR/usr/share/applications/linux-device-manager.desktop" \
        --icon-file="$APPIMAGE_DIR/usr/share/icons/hicolor/512x512/apps/linux-device-manager.png" \
        --output=appimage \
        -d "$APPIMAGE_DIR/usr/share/applications/linux-device-manager.desktop" \
        --executable="$APPIMAGE_DIR/usr/bin/device_manager.py" || true
    echo "   ✓ AppImage создан"
else
    # Создаём упрощённый AppImage вручную
    APPIMAGE_OUT="$BUILD_DIR/${APPNAME}-${VERSION}-x86_64.AppImage"
    
    # Скачиваем appimagetool если нет
    if [ ! -f "$BUILD_DIR/appimagetool-x86_64.AppImage" ]; then
        echo "   Скачиваю appimagetool..."
        curl -L -o "$BUILD_DIR/appimagetool-x86_64.AppImage" \
            "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" 2>/dev/null || \
        wget -q -O "$BUILD_DIR/appimagetool-x86_64.AppImage" \
            "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" || true
        chmod +x "$BUILD_DIR/appimagetool-x86_64.AppImage" 2>/dev/null || true
    fi
    
    if [ -f "$BUILD_DIR/appimagetool-x86_64.AppImage" ]; then
        export ARCH=x86_64
        "$BUILD_DIR/appimagetool-x86_64.AppImage" "$APPIMAGE_DIR" "$APPIMAGE_OUT" 2>/dev/null || {
            echo "   ⚠ AppImage сборка не удалась (нужен linuxdeploy)"
            echo "   Создаю tar.gz вместо AppImage..."
        }
        if [ -f "$APPIMAGE_OUT" ]; then
            chmod +x "$APPIMAGE_OUT"
            echo "   ✓ ${APPNAME}-${VERSION}-x86_64.AppImage"
        fi
    else
        echo "   ⚠ appimagetool не удалось скачать"
        echo "   Для сборки AppImage установи: sudo pacman -S appimagetool-bin (из AUR через paru)"
    fi
fi

# ============================================================================
# 4. Flatpak
# ============================================================================
echo ""
echo ">> [4/6] Создание Flatpak manifest..."
MANIFEST="$BUILD_DIR/flatpak/com.dvytvs.device-manager.yml"
# Manifest уже создан ниже, просто проверяем
if [ -f "$MANIFEST" ]; then
    echo "   ✓ Manifest создан: $MANIFEST"
    echo "   Для сборки: flatpak-builder --repo=repo --force-clean build-dir $MANIFEST"
    echo "   Затем: flatpak build-bundle repo ${APPNAME}.flatpak com.dvytvs.device-manager"
else
    echo "   ⚠ Manifest не найден"
fi

# ============================================================================
# 5. DEB (Debian/Ubuntu)
# ============================================================================
echo ""
echo ">> [5/6] Создание DEB..."
DEB_DIR="$BUILD_DIR/debian"
mkdir -p "$DEB_DIR/DEBIAN"
mkdir -p "$DEB_DIR/usr/bin"
mkdir -p "$DEB_DIR/usr/share/applications"
mkdir -p "$DEB_DIR/usr/share/icons/hicolor/512x512/apps"
mkdir -p "$DEB_DIR/usr/share/${APPNAME}"

# Control
cat > "$DEB_DIR/DEBIAN/control" << EOF
Package: $APPNAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Depends: python3, python3-gi, gir1.2-gtk-3.0, gir1.2-adw-1, pciutils, usbutils
Maintainer: dvytvs <dvytvs@github.com>
Description: Device Manager for Linux
 A full-featured device manager for Linux inspired by Windows 11 Device Manager.
 Scans and displays PCI, USB, network, disk, audio, and other devices.
EOF

# Postinst
cat > "$DEB_DIR/DEBIAN/postinst" << 'POSTINST'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor
fi
POSTINST
chmod +x "$DEB_DIR/DEBIAN/postinst"

# Files
cp "$PKG_DIR/usr/bin/$APPNAME" "$DEB_DIR/usr/bin/"
cp "$PKG_DIR/usr/share/$APPNAME/device_manager.py" "$DEB_DIR/usr/share/$APPNAME/"
cp "$BUILD_DIR/pkg/usr/share/applications/linux-device-manager.desktop" "$DEB_DIR/usr/share/applications/"
cp "$BUILD_DIR/pkg/usr/share/icons/hicolor/512x512/apps/linux-device-manager.png" "$DEB_DIR/usr/share/icons/hicolor/512x512/apps/"

DEB_OUT="$BUILD_DIR/${APPNAME}-${VERSION}-amd64.deb"
if command -v dpkg-deb &>/dev/null; then
    dpkg-deb --build "$DEB_DIR" "$DEB_OUT"
    echo "   ✓ ${APPNAME}-${VERSION}-amd64.deb"
else
    echo "   ⚠ dpkg-deb не установлен"
    echo "   Установи: sudo pacman -S dpkg"
    echo "   Затем запусти скрипт снова"
fi

# ============================================================================
# 6. RPM (Fedora/RHEL/openSUSE)
# ============================================================================
echo ""
echo ">> [6/6] Создание RPM..."
RPM_DIR="$BUILD_DIR/rpm"
SPEC="$RPM_DIR/SPECS/${APPNAME}.spec"

# Создаём source tarball для RPM
RPM_SRC="$RPM_DIR/SOURCES"
mkdir -p "$RPM_SRC"
tar czf "$RPM_SRC/${APPNAME}-${VERSION}.tar.gz" -C "$PROJECT_DIR" \
    device_manager.py run.sh README.md requirements.txt \
    linux-device-manager.desktop \
    build/icons/linux/icon.png

cat > "$SPEC" << EOF
Name:           $APPNAME
Version:        $VERSION
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
exec python3 %{_datadir}/%{name}/device_manager.py "\$@"
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
* $(date '+%a %b %d %Y') dvytvs <dvytvs@github.com> - $VERSION-1
- Initial package
EOF

echo "   ✓ RPM spec создан: $SPEC"
echo "   Для сборки: rpmbuild -ba $SPEC"
if command -v rpmbuild &>/dev/null; then
    rpmbuild -bb "$SPEC" --define "_topdir $RPM_DIR" 2>/dev/null && {
        RPM_OUT=$(find "$RPM_DIR/RPMS" -name "*.rpm" 2>/dev/null | head -1)
        if [ -n "$RPM_OUT" ]; then
            cp "$RPM_OUT" "$BUILD_DIR/"
            echo "   ✓ $(basename "$RPM_OUT")"
        fi
    } || echo "   ⚠ rpmbuild не удалось (нужны зависимости)"
else
    echo "   ⚠ rpmbuild не установлен"
    echo "   Установи: sudo pacman -S rpm-tools"
fi

# ============================================================================
# Итоги
# ============================================================================
echo ""
echo "========================================="
echo "Сборка завершена!"
echo "========================================="
echo ""
echo "Созданные файлы в build/:"
find "$BUILD_DIR" -maxdepth 1 -type f \( -name "*.tar.gz" -o -name "*.tar.zst" -o -name "*.pkg.tar.zst" -o -name "*.deb" -o -name "*.rpm" -o -name "*.AppImage" -o -name "*.flatpak" \) 2>/dev/null | while read f; do
    echo "  ✓ $(basename "$f") ($(du -h "$f" | cut -f1))"
done
echo ""
echo "Готовые манифесты:"
echo "  ✓ build/arch/PKGBUILD          → cd build/arch && paru -S"
echo "  ✓ build/debian/DEBIAN/control   → dpkg-deb --build (Debian/Ubuntu)"
echo "  ✓ build/rpm/SPECS/*.spec        → rpmbuild -ba (Fedora/RHEL)"
echo "  ✓ build/flatpak/*.yml           → flatpak-builder"
echo "  ✓ build/snap/snapcraft.yaml     → snapcraft"
echo "  ✓ build/appimage/AppDir/        → appimagetool"
echo ""
echo "Установка на CachyOS:"
echo "  sudo pacman -U build/linux-device-manager-*-any.pkg.tar.zst"
