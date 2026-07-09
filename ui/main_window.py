import os
import tempfile
import wave
import struct
import math
import uuid
import time

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox, QScrollArea, QStackedWidget
)
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtMultimedia import QSoundEffect

from core.timer import FocusTimer
from core.presence import PresenceDetector
from core.blocker import HostsBlocker
from core.logger import SessionLogger
from core.config import Config
from core.blocker_extension import BlockerExtensionServer
from core.rest_calculator import rest_minutes
from ui.widgets import CameraWidget, DialTimer, Badge
from ui.stats_widget import StatsWidget
from ui.settings_widget import SettingsWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.logger = SessionLogger()
        self.blocker = HostsBlocker(self.config)
        self.timer = FocusTimer(self.config.session_duration_minutes * 60)
        self.presence = None

        self.ext_server = BlockerExtensionServer()
        self.ext_server.on_block_attempt = self._on_ext_block_attempt
        self.distraction_attempts = 0
        
        self.ext_server.start()
        self._update_server_state('idle')   # فقط always فعال شود

        self.warning_timer = QTimer(self)
        self.warning_timer.timeout.connect(self._update_warning_countdown)
        self.seconds_left = 0

        self.beep_sound = QSoundEffect()
        beep_file = self._generate_beep()
        self.beep_sound.setSource(QUrl.fromLocalFile(beep_file))
        self.beep_sound.setVolume(0.7)

        # متغیرهای استریک
        self.streak_id = None
        self.streak_position = 0
        self.overtime_seconds = 0
        self.focus_start_time = None
        self.pending_rest_minutes = 0
        self.auto_continue = False

        self.setWindowTitle("Mikhkoob")
        self.setStyleSheet("background-color: #1e1e1e;")
        self.setMinimumSize(900, 700)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ========== پنل چپ (ثابت) ==========
        left_panel = QWidget()
        left_panel.setFixedWidth(380)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0)

        # دوربین با stretch=0
        self.camera = CameraWidget()
        left_layout.addWidget(self.camera, 0)

        # دیال تایمر (همیشه نمایش داده می‌شود)
        self.dial = DialTimer()
        self.dial.setMinimumHeight(260)          # اطمینان از ارتفاع کافی
        self.dial.duration_changed.connect(self._on_dial_changed)
        left_layout.addWidget(self.dial, 2)      # stretch factor افزایش یافته

        # دکمه‌های پروفایل
        self.preset_buttons_layout = QHBoxLayout()
        self._refresh_preset_buttons()
        left_layout.addLayout(self.preset_buttons_layout)

        # برچسب وضعیت (برای استراحت/گریس)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        self.status_label.hide()
        left_layout.addWidget(self.status_label)

        # برچسب تایمر بزرگ (استفاده نمی‌شود، مخفی می‌ماند)
        self.running_label = QLabel("00:00")
        self.running_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.running_label.setStyleSheet("color: white; font-size: 56px; font-weight: bold;")
        self.running_label.hide()
        left_layout.addWidget(self.running_label)

        # دکمه‌های کنترل
        self.action_btn = QPushButton("شروع فوکوس")
        self.action_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6c5ce7, stop:1 #a29bfe);
                border-radius: 25px; padding: 15px 40px; color: white;
                font-size: 18px; font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7d6ff0, stop:1 #b4acff);
            }
            QPushButton:disabled { background: #555; }
        """)
        self.action_btn.clicked.connect(self.start_session)
        left_layout.addWidget(self.action_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # دکمه‌های استراحت
        self.skip_rest_btn = QPushButton("پایان استراحت (ادامه فوکوس)")
        self.skip_rest_btn.setStyleSheet(self.action_btn.styleSheet())
        self.skip_rest_btn.clicked.connect(self._on_skip_rest)
        self.skip_rest_btn.hide()
        left_layout.addWidget(self.skip_rest_btn)

        self.end_streak_btn = QPushButton("پایان استراحت و پایان استریک")
        self.end_streak_btn.setStyleSheet(self.action_btn.styleSheet())
        self.end_streak_btn.clicked.connect(self._on_end_streak)
        self.end_streak_btn.hide()
        left_layout.addWidget(self.end_streak_btn)

        main_layout.addWidget(left_panel)

        # ========== پنل راست (top bar + stack) ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        top_bar = QHBoxLayout()
        self.btn_report = QPushButton("📊 گزارش")
        self.btn_settings = QPushButton("⚙️ تنظیمات")
        self.btn_report.setCheckable(True)
        self.btn_settings.setCheckable(True)
        self.btn_report.setChecked(True)
        self.btn_report.setStyleSheet("QPushButton { padding: 10px; font-weight: bold; color: white; background: transparent; border-bottom: 2px solid transparent; } QPushButton:checked { border-bottom: 2px solid #a29bfe; }")
        self.btn_settings.setStyleSheet("QPushButton { padding: 10px; font-weight: bold; color: white; background: transparent; border-bottom: 2px solid transparent; } QPushButton:checked { border-bottom: 2px solid #a29bfe; }")
        top_bar.addWidget(self.btn_report)
        top_bar.addWidget(self.btn_settings)
        top_bar.addStretch()
        right_layout.addLayout(top_bar)

        self.stack = QStackedWidget()
        self.stats_widget = StatsWidget(self.logger)
        self.settings_widget = SettingsWidget(self.config)
        self.stack.addWidget(self.stats_widget)
        self.stack.addWidget(self.settings_widget)
        right_layout.addWidget(self.stack)

        self.btn_report.clicked.connect(lambda: self._switch_right_panel(0))
        self.btn_settings.clicked.connect(lambda: self._switch_right_panel(1))

        main_layout.addWidget(right_panel, 1)

        # اتصالات تایمر
        self.timer.tick.connect(self._on_focus_tick)
        self.timer.finished.connect(self._on_focus_finished)
        self.timer.abandoned.connect(self._on_focus_abandoned)
        self.timer.rest_tick.connect(self._on_rest_tick)
        self.timer.rest_finished.connect(self._on_rest_finished)
        self.timer.grace_tick.connect(self._on_grace_tick)
        self.timer.grace_expired.connect(self._on_grace_expired)

        self._apply_preset_to_dial()
        self._update_stats_title()

    # ---------- UI Helpers ----------
    def _refresh_preset_buttons(self):
        for i in reversed(range(self.preset_buttons_layout.count())):
            widget = self.preset_buttons_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        for preset in self.config.presets:
            btn = QPushButton(f"{preset['name']}\n{preset['minutes']}m")
            btn.setStyleSheet("QPushButton { background: #333; color: white; border-radius: 8px; padding: 5px; font-size: 10px; } QPushButton:hover { background: #555; }")
            btn.clicked.connect(lambda checked, p=preset: self._on_preset_clicked(p))
            self.preset_buttons_layout.addWidget(btn)

    def _switch_right_panel(self, index):
        self.stack.setCurrentIndex(index)
        self.btn_report.setChecked(index == 0)
        self.btn_settings.setChecked(index == 1)
        if index == 0:
            self.stats_widget.refresh()

    def _apply_preset_to_dial(self):
        minutes = self.config.session_duration_minutes
        self.dial.set_minutes(minutes)
        self.timer.duration = minutes * 60
        self.timer.remaining = minutes * 60

    # ---------- Sound ----------
    def _generate_beep(self):
        sample_rate = 44100; duration = 0.2; freq = 1500
        n = int(sample_rate * duration)
        buf = b''.join(struct.pack('<h', int(32767 * 0.4 * math.sin(2 * math.pi * freq * (i / sample_rate)))) for i in range(n))
        tmp = os.path.join(tempfile.gettempdir(), "focusguard_beep.wav")
        with wave.open(tmp, 'w') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(sample_rate); f.writeframes(buf)
        return tmp

    # ---------- Dial & Preset Events ----------
    def _on_dial_changed(self, minutes):
        self.config.data["session_duration_minutes"] = minutes
        self.config.save_settings()
        if self.timer.state == "IDLE":
            self.timer.duration = minutes * 60
            self.timer.remaining = self.timer.duration

    def _on_preset_clicked(self, preset):
        self.dial.set_minutes(preset["minutes"])

    # ---------- State Machine ----------
    def start_session(self):
        """Start a new focus session (from IDLE)."""
        if self.streak_id is None:
            self.streak_id = str(uuid.uuid4())
            self.streak_position = 1
        else:
            self.streak_position += 1

        # دیال همیشه نمایش داده شود
        self.dial.setVisible(True)
        # برچسب بزرگ مخفی بماند (دیگر استفاده نمی‌شود)
        self.running_label.hide()
        self.status_label.hide()
        self.skip_rest_btn.hide()
        self.end_streak_btn.hide()

        # تغییر دکمه شروع به دکمه لغو
        self.action_btn.setText("لغو فوکوس")
        self.action_btn.clicked.disconnect()
        self.action_btn.clicked.connect(self.cancel_session)
        self.action_btn.show()

        self.distraction_attempts = 0
        self.overtime_seconds = 0
        self.focus_start_time = None

        self._start_focus_internal()

    def _start_focus_internal(self):
        """Technical start of focus timer."""
        self._update_server_state('focus')

        self.timer.start_focus(self.config.session_duration_minutes * 60)
        self.focus_start_time = None

        if self.config.camera_enabled:
            self.presence = PresenceDetector()
            self.presence.frame_ready.connect(self.camera.set_frame)
            self.presence.absent_warning.connect(self._on_absent_warning)
            self.presence.presence_restored.connect(self._on_presence_restored)
            self.presence.abandoned.connect(self._on_focus_abandoned_camera)
            self.presence.warning_beep.connect(self.beep_sound.play)
            self.presence.start()

    def _on_focus_tick(self, remaining):
        if self.focus_start_time is None:
            self.focus_start_time = time.time()
        # به‌روزرسانی تایمر حلقوی (Dial) به جای برچسب بزرگ
        self.dial.set_mode('focus', remaining)

    def _on_focus_finished(self):
        """Focus completed normally."""
        self.overtime_seconds = 0
        comp_seconds = self.timer.elapsed
        self._log_focus_session(comp_seconds, "complete", rest_completed=False)

        self.pending_rest_minutes = rest_minutes(self.config.session_duration_minutes)
        self._enter_rest_mode()

    def _on_focus_abandoned(self, completed_seconds):
        """Focus cancelled or abandoned."""
        self.overtime_seconds = 0
        self._log_focus_session(completed_seconds, "incomplete", rest_completed=False)
        self._end_streak_and_reset()

    def _on_focus_abandoned_camera(self):
        """Camera detected prolonged absence."""
        self.warning_timer.stop()
        self.camera.set_abandoned()
        self.timer.abandon_focus()

    def _log_focus_session(self, duration, status, rest_completed=False):
        target = self.timer.duration
        self.logger.log_session(
            duration_seconds=duration,
            status=status,
            target_duration=target,
            distraction_attempts=self.distraction_attempts,
            streak_id=self.streak_id,
            streak_position=self.streak_position,
            overtime_seconds=self.overtime_seconds,
            break_after_seconds=0
        )

    def _enter_rest_mode(self):
        """Enter rest period."""
        self._update_server_state('rest')

        self.timer.start_rest(self.pending_rest_minutes * 60)
        self.dial.set_mode('rest', self.pending_rest_minutes * 60)
        self.running_label.hide()
        self.status_label.setText(f"استراحت ({self.pending_rest_minutes} دقیقه)")
        self.status_label.show()
        self.skip_rest_btn.show()
        self.end_streak_btn.show()

        if self.presence and self.presence.isRunning():
            self.presence.stop()

    def _on_rest_tick(self, remaining):
        mins, secs = divmod(remaining, 60)
        self.status_label.setText(f"استراحت ({mins:02d}:{secs:02d})")
        self.dial.set_mode('rest', remaining)

    def _on_rest_finished(self):
        """Rest finished, enter grace period."""
        self._enter_grace_mode()

    def _on_skip_rest(self):
        """User skipped rest to continue streak."""
        self.timer.skip_rest()
        self._continue_streak()

    def _on_end_streak(self):
        """User chose to end the streak."""
        self.timer.skip_rest()
        self._end_streak_and_reset()

    def _enter_grace_mode(self):
        """2-minute grace to return."""
        self._update_server_state('idle')
        self.timer.start_grace()
        self.status_label.setText("فرصت داری برگردی! (02:00)")
        self.dial.set_mode('grace', 120)
        self.skip_rest_btn.hide()
        self.end_streak_btn.hide()

        if self.config.camera_enabled:
            if self.presence and self.presence.isRunning():
                self.presence.stop()
            self.presence = PresenceDetector()
            self.presence.frame_ready.connect(self.camera.set_frame)
            self.presence.absent_warning.connect(self._on_absent_warning)
            self.presence.presence_restored.connect(self._on_presence_restored)
            self.presence.abandoned.connect(self._on_grace_abandoned)
            self.presence.warning_beep.connect(self.beep_sound.play)
            self.presence.start()

    def _on_grace_tick(self, remaining):
        mins, secs = divmod(remaining, 60)
        self.status_label.setText(f"فرصت داری برگردی! ({mins:02d}:{secs:02d})")
        self.dial.set_mode('grace', remaining)

    def _on_grace_expired(self):
        """Grace ended without return."""
        if self.presence and self.presence.isRunning():
            self.presence.stop()
        self._end_streak_and_reset()

    def _on_grace_abandoned(self):
        """Camera abandoned during grace."""
        if self.presence and self.presence.isRunning():
            self.presence.stop()
        self._end_streak_and_reset()

    def _continue_streak(self):
        """Continue streak (next focus without returning to IDLE)."""
        self.streak_position += 1
        self._start_focus_internal()

    def _end_streak_and_reset(self):
        """End the streak and go back to IDLE."""
        self._update_server_state('idle')
        if self.presence and self.presence.isRunning():
            self.presence.stop()
        self.streak_id = None
        self.streak_position = 0
        self._reset_ui_to_idle()

    def _reset_ui_to_idle(self):
        """Reset UI to initial idle state."""
        self.timer.reset()
        self.warning_timer.stop()
        self.camera.set_present()
        self.dial.set_mode('idle')
        self.dial.setVisible(True)
        self.running_label.hide()
        self.status_label.hide()
        self.skip_rest_btn.hide()
        self.end_streak_btn.hide()
        self.action_btn.setText("شروع فوکوس")
        self.action_btn.clicked.disconnect()
        self.action_btn.clicked.connect(self.start_session)
        self.action_btn.show()
        self._refresh_preset_buttons()
        self._apply_preset_to_dial()
        self._update_stats_title()
        self.stats_widget.refresh()
        
    def _update_server_state(self, current_state):
        """
        current_state: 'focus', 'rest', 'idle' (که در زمان idle فقط always فعال است)
        """
        # ساختار جدید: یک دیکشنری با سه scope
        rules = {
            "always": {"domains": [], "paths": {}},
            "focus":  {"domains": [], "paths": {}},
            "rest":   {"domains": [], "paths": {}}
        }

        # همیشه scope 'always' را پر کن
        always_domains, always_path_rules = self.config.get_all_domains_for_scope('always')
        rules["always"] = {"domains": always_domains, "paths": always_path_rules}

        # بسته به current_state، scope مربوطه را هم پر کن
        if current_state == 'focus':
            domains, path_rules = self.config.get_all_domains_for_scope('focus')
            rules["focus"] = {"domains": domains, "paths": path_rules}
        elif current_state == 'rest':
            domains, path_rules = self.config.get_all_domains_for_scope('rest')
            rules["rest"] = {"domains": domains, "paths": path_rules}
        # در حالت idle فقط always فعال است (که بالا پر شد)، بقیه خالی می‌مانند

        self.ext_server.update_block_rules(rules)

    # ---------- Distraction callback ----------
    def _on_ext_block_attempt(self, url):
        self.distraction_attempts += 1
        print(f"Blocked attempt: {url}")

    # ---------- Presence warnings (focus/grace) ----------
    def _on_absent_warning(self):
        self.seconds_left = 15
        self.camera.set_warning(self.seconds_left)
        self.warning_timer.start(1000)

    def _update_warning_countdown(self):
        self.seconds_left -= 1
        if self.seconds_left >= 0:
            self.camera.set_warning(self.seconds_left)
        else:
            self.warning_timer.stop()

    def _on_presence_restored(self):
        self.warning_timer.stop()
        self.camera.set_present()
        # اگر در حالت گریس بودیم و برگشتیم، ادامه استریک
        if self.timer.state == "GRACE":
            self.timer.timer.stop()
            if self.presence and self.presence.isRunning():
                self.presence.stop()
            self._continue_streak()

    def _update_stats_title(self):
        stats = self.logger.get_daily_stats()
        comp = stats.get("complete", 0) // 60
        inc = stats.get("incomplete", 0) // 60
        self.setWindowTitle(f"Mikhkoob | کامل: {comp}min / ناقص: {inc}min")

    # ---------- Cancel during focus ----------
    def cancel_session(self):
        if self.presence and self.presence.isRunning():
            self.presence.stop()
        self.timer.cancel_focus()

    def closeEvent(self, event):
        if self.presence and self.presence.isRunning():
            self.presence.stop()
        self.ext_server.stop()
        event.accept()