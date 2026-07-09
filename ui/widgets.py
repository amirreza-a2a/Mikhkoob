import math
import os
import tempfile
import wave
import struct
import json
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt6.QtGui import QPainter, QImage, QColor, QPen, QFont, QBrush, QConicalGradient, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QTimer, pyqtSignal, QUrl
from PyQt6.QtMultimedia import QSoundEffect

# ----------  توابع کمکی صدا و پیام (بدون تغییر) ----------
def generate_tick_wav():
    sample_rate = 44100
    duration = 0.04
    freq = 1000
    num_samples = int(sample_rate * duration)
    buf = b''
    for i in range(num_samples):
        t = i / sample_rate
        val = int(32767 * 0.25 * math.sin(2 * math.pi * freq * t))
        buf += struct.pack('<h', val)
    tmp = os.path.join(tempfile.gettempdir(), "focusguard_tick.wav")
    with wave.open(tmp, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(buf)
    return tmp

def load_messages():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "messages.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def get_message_for_minutes(minutes):
    msgs = load_messages()
    for key, msg in msgs.items():
        low, high = map(int, key.split('-'))
        if low <= minutes <= high:
            return msg
    return ""


# ---------- ویجت دوربین (بدون تغییر) ----------
class CameraWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.status = "present"
        self.warning_text = ""
        self.show_warning = False
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self._toggle_blink)
        self.blink_visible = True
        self.setMinimumSize(320, 240)

    def set_frame(self, qimg):
        self.image = qimg
        self.update()

    def set_present(self):
        self.status = "present"
        self.show_warning = False
        self.blink_timer.stop()
        self.update()

    def set_warning(self, seconds_left):
        self.status = "absent"
        self.warning_text = f"بازگشت به صندلی: {seconds_left} ثانیه"
        self.show_warning = True
        if not self.blink_timer.isActive():
            self.blink_visible = True
            self.blink_timer.start(500)
        self.update()

    def set_abandoned(self):
        self.status = "abandoned"
        self.show_warning = False
        self.blink_timer.stop()
        self.update()

    def _toggle_blink(self):
        if self.show_warning:
            self.blink_visible = not self.blink_visible
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        area = self.rect()
        radius = 30
        path = QPainterPath()
        path.addRoundedRect(QRectF(area), radius, radius)
        painter.setClipPath(path)
        painter.fillRect(area, QColor(20, 20, 20))
        if self.image and not self.image.isNull():
            scaled = self.image.scaled(area.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x = (area.width() - scaled.width()) // 2
            y = (area.height() - scaled.height()) // 2
            painter.drawImage(x, y, scaled)
        painter.setClipping(False)
        pen = QPen()
        pen.setWidth(4)
        if self.status == "present":
            pen.setColor(QColor(0, 200, 100))
        elif self.status == "absent":
            pen.setColor(QColor(255, 80, 80))
        else:
            pen.setColor(QColor(150, 150, 150))
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(area).adjusted(2, 2, -2, -2), radius, radius)
        if self.show_warning and self.blink_visible:
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", 18, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(area, Qt.AlignmentFlag.AlignCenter, self.warning_text)


# ---------- ویجت نشانگر (بدون تغییر) ----------
class Badge(QWidget):
    def __init__(self, icon_text, label_text, active=True, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 2, 4, 2)
        self.dot = QLabel(icon_text)
        self.dot.setStyleSheet("font-size: 18px;")
        self.label = QLabel(label_text)
        self.label.setStyleSheet("color: #dddddd; font-size: 12px;")
        layout.addWidget(self.dot)
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.set_active(active)

    def set_active(self, state):
        if state:
            self.dot.setStyleSheet("font-size: 18px; color: #2ecc71;")
        else:
            self.dot.setStyleSheet("font-size: 18px; color: #e74c3c;")


# ---------- حلقه زمان‌سنج (نسخه نهایی با set_mode) ----------
class DialTimer(QWidget):
    duration_changed = pyqtSignal(int)  # دقیقه

    def __init__(self, min_minutes=5, max_minutes=120, parent=None):
        super().__init__(parent)
        self.min = min_minutes
        self.max = max_minutes
        self.value = 45  # مقدار پیش‌فرض
        self.mouse_pressed = False
        self.running_mode = False
        self.mode = 'idle'          # 'idle', 'focus', 'rest', 'grace'
        self.remaining_seconds = 0

        self.tick_sound = QSoundEffect()
        tick_file = generate_tick_wav()
        self.tick_sound.setSource(QUrl.fromLocalFile(tick_file))
        self.tick_sound.setVolume(0.3)

        self.setMinimumSize(260, 260)

    def set_minutes(self, minutes):
        if not self.running_mode:
            minutes = max(self.min, min(self.max, minutes))
            if minutes != self.value:
                self.value = minutes
                self.duration_changed.emit(minutes)
                self.tick_sound.play()
                self.update()

    def set_mode(self, mode, value=None):
        """تنظیم حالت نمایش: idle, focus, rest, grace. value ثانیه باقی‌مانده."""
        self.running_mode = (mode != 'idle')
        self.mode = mode
        self.remaining_seconds = value if value else 0
        self.update()

    def _value_to_angles(self):
        ratio = (self.value - self.min) / (self.max - self.min)
        start_angle = 135
        span = int(ratio * 270)
        return start_angle * 16, span * 16

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height())
        rect = QRectF((self.width()-side)/2, (self.height()-side)/2, side, side)
        rect.adjust(20, 20, -20, -20)

        if not self.running_mode:
            # حالت idle (تنظیم زمان)
            pen_track = QPen(QColor(50, 50, 50), 12)
            painter.setPen(pen_track)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(rect, 135 * 16, 270 * 16)

            start_16, span_16 = self._value_to_angles()
            gradient = QConicalGradient(rect.center(), 135 + span_16/16.0)
            gradient.setColorAt(0.0, QColor(0, 210, 210))
            gradient.setColorAt(1.0, QColor(140, 0, 210))
            pen_active = QPen()
            pen_active.setWidth(12)
            pen_active.setBrush(QBrush(gradient))
            painter.setPen(pen_active)
            painter.drawArc(rect, start_16, span_16)

            # متن‌ها
            painter.setPen(QColor(255, 255, 255))
            font_time = QFont("Arial", 38, QFont.Weight.Bold)
            painter.setFont(font_time)
            text_rect = QRectF(rect.left(), rect.top() + 15, rect.width(), rect.height()/2 - 10)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, f"{self.value:02d}:00")

            font_sub = QFont("Arial", 12)
            painter.setFont(font_sub)
            painter.setPen(QColor(200, 200, 200))
            sub_rect = QRectF(rect.left(), rect.top() + rect.height()/2 - 5, rect.width(), 25)
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, "دقیقه کار عمیق")

            msg = get_message_for_minutes(self.value)
            if msg:
                font_msg = QFont("Arial", 10)
                painter.setFont(font_msg)
                painter.setPen(QColor(160, 160, 160))
                msg_rect = QRectF(rect.left(), rect.top() + rect.height()/2 + 30, rect.width(), 30)
                painter.drawText(msg_rect, Qt.AlignmentFlag.AlignCenter, msg)
        else:
            # حالت‌های running: focus, rest, grace
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(30, 30, 30, 200))
            painter.drawEllipse(rect)

            mins, secs = divmod(self.remaining_seconds, 60)
            time_str = f"{int(mins):02d}:{int(secs):02d}"
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", 42, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, time_str)

            # زیرنویس برای حالت rest یا grace
            if self.mode == 'rest':
                painter.setFont(QFont("Arial", 12))
                painter.setPen(QColor(200, 200, 200))
                painter.drawText(rect.adjusted(0, 30, 0, 0), Qt.AlignmentFlag.AlignCenter, "استراحت")
            elif self.mode == 'grace':
                painter.setFont(QFont("Arial", 12))
                painter.setPen(QColor(200, 200, 200))
                painter.drawText(rect.adjusted(0, 30, 0, 0), Qt.AlignmentFlag.AlignCenter, "فرصت بازگشت")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.running_mode:
            self.mouse_pressed = True
            self._update_from_pos(event.pos())

    def mouseMoveEvent(self, event):
        if self.mouse_pressed and not self.running_mode:
            self._update_from_pos(event.pos())

    def mouseReleaseEvent(self, event):
        self.mouse_pressed = False

    def wheelEvent(self, event):
        if not self.running_mode:
            delta = event.angleDelta().y()
            step = 1 if delta > 0 else -1
            new_minutes = self.value + step
            new_minutes = max(self.min, min(self.max, new_minutes))
            self.set_minutes(new_minutes)
            event.accept()

    def _update_from_pos(self, pos):
        center = self.rect().center()
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()
        angle_deg = math.degrees(math.atan2(-dy, dx)) % 360
        if angle_deg < 135:
            mapped = angle_deg + 360
        else:
            mapped = angle_deg
        mapped = max(135, min(mapped, 405))
        ratio = (mapped - 135) / 270.0
        minutes = int(self.min + ratio * (self.max - self.min) + 0.5)
        minutes = max(self.min, min(self.max, minutes))
        self.set_minutes(minutes)