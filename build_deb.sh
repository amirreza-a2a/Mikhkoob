#!/bin/bash
# build_deb.sh - ساخت بستهٔ .deb برای FocusGuardian
set -e

# ---------- تنظیمات ----------
APP_NAME="focusguardian"
VERSION="1.0.0"
ARCH="amd64"
MAINTAINER="شما <you@example.com>"
DESCRIPTION="دستیار تمرکز با تشخیص حضور و مسدودساز هوشمند"
DEPENDS="libc6, libstdc++6"

# ---------- نام پوشهٔ ساخت (با معماری) ----------
BUILD_DIR="deb_build"
DEB_FOLDER="${APP_NAME}_${VERSION}_${ARCH}"
DEB_PATH="${BUILD_DIR}/${DEB_FOLDER}"

# ---------- مرحله ۱: ساخت فایل اجرایی با PyInstaller ----------
echo "==> ساخت فایل اجرایی با PyInstaller..."
pip install pyinstaller --quiet 2>/dev/null || true
pyinstaller --onefile --windowed \
    --name="${APP_NAME}" \
    --add-data "data:data" \
    --add-data "assets:assets" \
    --add-data "models:models" \
    main.py

if [ ! -f "dist/${APP_NAME}" ]; then
    echo "خطا: فایل اجرایی ساخته نشد."
    exit 1
fi

# ---------- مرحله ۲: آماده‌سازی پوشه‌ها ----------
echo "==> آماده‌سازی ساختار بسته..."
rm -rf "${DEB_PATH}"
mkdir -p "${DEB_PATH}/opt/${APP_NAME}"
mkdir -p "${DEB_PATH}/usr/local/bin"
mkdir -p "${DEB_PATH}/usr/share/applications"
mkdir -p "${DEB_PATH}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${DEB_PATH}/DEBIAN"

# کپی فایل اجرایی اصلی
cp "dist/${APP_NAME}" "${DEB_PATH}/opt/${APP_NAME}/${APP_NAME}"
chmod 755 "${DEB_PATH}/opt/${APP_NAME}/${APP_NAME}"

# ایجاد اسکریپت راه‌انداز (wrapper) برای اجرای بهتر از محیط دسکتاپ
cat > "${DEB_PATH}/opt/${APP_NAME}/run_${APP_NAME}.sh" <<'EOF'
#!/bin/bash
exec /opt/focusguardian/focusguardian "$@"
EOF
chmod 755 "${DEB_PATH}/opt/${APP_NAME}/run_${APP_NAME}.sh"

# لینک سمبلیک در /usr/local/bin به اسکریپت راه‌انداز (توسط postinst هم اعمال می‌شود)
ln -sf /opt/${APP_NAME}/run_${APP_NAME}.sh "${DEB_PATH}/usr/local/bin/${APP_NAME}"

# کپی آیکون (در صورت وجود)
if [ -f "assets/icon.png" ]; then
    cp "assets/icon.png" "${DEB_PATH}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
else
    echo "هشدار: فایل assets/icon.png یافت نشد. آیکون اضافه نمی‌شود."
fi

# ---------- فایل‌های کنترلی ----------
echo "==> ایجاد فایل‌های کنترلی..."

cat > "${DEB_PATH}/DEBIAN/control" <<EOF
Package: ${APP_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: ${MAINTAINER}
Description: ${DESCRIPTION}
 این برنامه با تشخیص حضور از طریق وب‌کم و مسدودسازی سایت‌های مزاحم،
 به شما کمک می‌کند جلسات تمرکز عمیق داشته باشید.
Depends: ${DEPENDS}
EOF

cat > "${DEB_PATH}/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e
ln -sf /opt/focusguardian/run_focusguardian.sh /usr/local/bin/focusguardian
if [ -x /usr/bin/update-desktop-database ]; then
    /usr/bin/update-desktop-database || true
fi
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    /usr/bin/gtk-update-icon-cache /usr/share/icons/hicolor || true
fi
EOF
chmod 755 "${DEB_PATH}/DEBIAN/postinst"

# فایل desktop که از طریق اسکریپت راه‌انداز اجرا شود
cat > "${DEB_PATH}/usr/share/applications/${APP_NAME}.desktop" <<EOF
[Desktop Entry]
Name=Mikhkoob
Comment=${DESCRIPTION}
Exec=/opt/${APP_NAME}/run_${APP_NAME}.sh
Icon=${APP_NAME}
Terminal=false
Type=Application
Categories=Utility;Productivity;
EOF

# ---------- ساخت بسته ----------
echo "==> ساخت بستهٔ .deb..."
dpkg-deb --build "${DEB_PATH}" "${BUILD_DIR}/${DEB_FOLDER}.deb"

echo "✅ بسته با موفقیت ساخته شد: ${BUILD_DIR}/${DEB_FOLDER}.deb"
echo "برای نصب: sudo dpkg -i ${BUILD_DIR}/${DEB_FOLDER}.deb"