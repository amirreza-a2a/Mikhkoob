#!/usr/bin/env python3
import sys
import json
import struct
import socket
import traceback

PORT = 9876
APP_HOST = '127.0.0.1'

def log_error(msg):
    """نوشتن خطاها در stderr تا در لاگ کروم قابل مشاهده باشد."""
    sys.stderr.write(f"[Mikhkoob Native Host] {msg}\n")
    sys.stderr.flush()

def read_message():
    """خواندن یک پیام از پروتکل Native Messaging (۴ بایت طول + JSON)."""
    try:
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length or len(raw_length) < 4:
            return None
        message_length = struct.unpack('=I', raw_length)[0]
        if message_length == 0:
            return None
        message = sys.stdin.buffer.read(message_length).decode('utf-8')
        return json.loads(message)
    except json.JSONDecodeError as e:
        log_error(f"JSON decode error: {e}")
        return None
    except Exception as e:
        log_error(f"Unexpected read error: {e}")
        return None

def send_message(message):
    """ارسال یک پیام JSON به استاندارد خروجی مطابق پروتکل."""
    try:
        encoded = json.dumps(message).encode('utf-8')
        sys.stdout.buffer.write(struct.pack('=I', len(encoded)))
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()
    except Exception as e:
        log_error(f"Send error: {e}")

def forward_to_app(msg):
    """ارسال پیام به برنامه اصلی از طریق TCP و پاسخ به افزونه در صورت نیاز."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)  # از هنگ کردن جلوگیری کند
        sock.connect((APP_HOST, PORT))
        sock.sendall(json.dumps(msg).encode('utf-8'))
        response = sock.recv(4096)
        if response:
            reply = json.loads(response.decode('utf-8'))
            if reply.get('action') in ('update_blocklist', 'clear_blocklist'):
                send_message(reply)
        sock.close()
    except socket.timeout:
        log_error("Timeout connecting to app.")
    except Exception as e:
        log_error(f"Forward error: {traceback.format_exc()}")

def main():
    log_error("Native host started.")
    while True:
        msg = read_message()
        if msg is None:
            # اگر ارتباط قطع شد، حلقه را تمام کن (کروم دوباره تلاش می‌کند)
            break
        forward_to_app(msg)
    log_error("Native host exiting.")

if __name__ == '__main__':
    main()