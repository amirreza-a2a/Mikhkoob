from PyQt6.QtCore import QObject, QTimer, pyqtSignal

class FocusTimer(QObject):
    tick = pyqtSignal(int)           # remaining seconds
    finished = pyqtSignal()          # focus finished normally
    abandoned = pyqtSignal(int)      # focus abandoned (completed_seconds)
    rest_tick = pyqtSignal(int)      # rest remaining seconds
    rest_finished = pyqtSignal()     # rest completed
    grace_tick = pyqtSignal(int)     # grace period remaining
    grace_expired = pyqtSignal()     # 2 minutes ended without return

    def __init__(self, duration_seconds=75*60):
        super().__init__()
        self.default_duration = duration_seconds
        self.duration = duration_seconds
        self.remaining = duration_seconds
        self.state = "IDLE"           # IDLE, FOCUS, REST, GRACE
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)
        self.elapsed = 0
        self.rest_remaining = 0
        self.grace_remaining = 0

    def start_focus(self, duration=None):
        if duration:
            self.duration = duration
        else:
            self.duration = self.default_duration
        self.remaining = self.duration
        self.elapsed = 0
        self.state = "FOCUS"
        self.timer.start(1000)

    def abandon_focus(self):
        if self.state == "FOCUS":
            self.timer.stop()
            completed = self.elapsed
            self.state = "IDLE"
            self.abandoned.emit(completed)

    def cancel_focus(self):
        """انصراف دستی (همان abandon)"""
        self.abandon_focus()

    def start_rest(self, rest_seconds):
        if self.state in ("FOCUS", "IDLE"):
            self.timer.stop()
            self.rest_remaining = rest_seconds
            self.state = "REST"
            self.timer.start(1000)

    def skip_rest(self):
        """کاربر استراحت را رد کند"""
        if self.state == "REST":
            self.timer.stop()
            self.state = "IDLE"
            self.rest_finished.emit()

    def start_grace(self):
        """۲ دقیقه فرصت برای برگشت"""
        self.grace_remaining = 120  # 2 minutes
        self.state = "GRACE"
        self.timer.start(1000)

    def reset(self):
        self.timer.stop()
        self.remaining = self.duration
        self.elapsed = 0
        self.state = "IDLE"

    def _update(self):
        if self.state == "FOCUS":
            self.remaining -= 1
            self.elapsed += 1
            self.tick.emit(self.remaining)
            if self.remaining <= 0:
                self.timer.stop()
                self.state = "IDLE"
                self.finished.emit()
        elif self.state == "REST":
            self.rest_remaining -= 1
            self.rest_tick.emit(self.rest_remaining)
            if self.rest_remaining <= 0:
                self.timer.stop()
                self.state = "IDLE"
                self.rest_finished.emit()
        elif self.state == "GRACE":
            self.grace_remaining -= 1
            self.grace_tick.emit(self.grace_remaining)
            if self.grace_remaining <= 0:
                self.timer.stop()
                self.state = "IDLE"
                self.grace_expired.emit()