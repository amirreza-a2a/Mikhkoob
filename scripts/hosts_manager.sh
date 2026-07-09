#!/bin/bash
# اسکریپت تغییر /etc/hosts با pkexec
# نحوه استفاده:
#   hosts_manager.sh enable domain1.com domain2.com ...
#   hosts_manager.sh disable domain1.com domain2.com ...

ACTION=$1
shift
DOMAINS=("$@")
HOSTS_FILE="/etc/hosts"
BACKUP="/etc/hosts.bak.focusguardian"
TEMP="/tmp/focusguardian_hosts.tmp"

if [ "$ACTION" = "enable" ]; then
    # پشتیبان‌گیری
    cp "$HOSTS_FILE" "$BACKUP"
    # اضافه کردن خطوط مسدودی
    for domain in "${DOMAINS[@]}"; do
        # اگر دامنه قبلاً اضافه نشده باشد
        if ! grep -q "0.0.0.0 $domain" "$HOSTS_FILE"; then
            echo "0.0.0.0 $domain" >> "$HOSTS_FILE"
        fi
    done
elif [ "$ACTION" = "disable" ]; then
    # حذف خطوط مربوطه
    cp "$HOSTS_FILE" "$TEMP"
    for domain in "${DOMAINS[@]}"; do
        sed -i "/0.0.0.0 $domain/d" "$TEMP"
    done
    mv "$TEMP" "$HOSTS_FILE"
else
    echo "عملیات نامعتبر"
    exit 1
fi