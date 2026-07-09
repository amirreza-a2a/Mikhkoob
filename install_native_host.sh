#!/bin/bash
# install_native_host.sh
PROJECT_DIR="$HOME/Mikhkoob"
NATIVE_SCRIPT="$PROJECT_DIR/native_host/mikhkoob_native_host.py"

# ساختن فایل مانیفست
MANIFEST=$(cat <<EOF
{
  "name": "com.mikhkoob.focusblocker",
  "description": "Mikhkoob Native Host",
  "path": "$NATIVE_SCRIPT",
  "type": "stdio",
  "allowed_extensions": ["mikhkoob@example.com"]
}
EOF
)

# نصب برای گوگل کروم
CHROME_DIR="$HOME/.config/google-chrome/NativeMessagingHosts"
mkdir -p "$CHROME_DIR"
echo "$MANIFEST" > "$CHROME_DIR/com.mikhkoob.focusblocker.json"
echo "Native host installed for Google Chrome."

# نصب برای فایرفاکس
FIREFOX_DIR="$HOME/.mozilla/native-messaging-hosts"
mkdir -p "$FIREFOX_DIR"
echo "$MANIFEST" > "$FIREFOX_DIR/com.mikhkoob.focusblocker.json"
echo "Native host installed for Firefox."

# اطمینان از اجرایی بودن اسکریپت
chmod +x "$NATIVE_SCRIPT"
echo "Native host script is now executable."