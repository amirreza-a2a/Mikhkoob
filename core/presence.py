import cv2
import os
import sys
import time
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# مسیرهای مدل DNN (اختیاری)
MODEL_DIR = resource_path("models")
PROTOTXT_PATH = os.path.join(MODEL_DIR, "deploy.prototxt")
CAFFEMODEL_PATH = os.path.join(MODEL_DIR, "res10_300x300_ssd_iter_140000_fp16.caffemodel")


class PresenceDetector(QThread):
    absent_warning = pyqtSignal()
    presence_restored = pyqtSignal()
    abandoned = pyqtSignal()
    warning_beep = pyqtSignal()
    frame_ready = pyqtSignal(QImage)

    def __init__(self, camera_index=0, warning_delay=5, abandon_delay=20):
        super().__init__()
        self.camera_index = camera_index
        self.warning_delay = warning_delay
        self.abandon_delay = abandon_delay
        self.running = False

        # انتخاب روش تشخیص چهره
        self.use_dnn = os.path.isfile(PROTOTXT_PATH) and os.path.isfile(CAFFEMODEL_PATH)
        if self.use_dnn:
            print("[Presence] استفاده از مدل DNN (دقت بالا)")
            self.net = cv2.dnn.readNetFromCaffe(PROTOTXT_PATH, CAFFEMODEL_PATH)
        else:
            print("[Presence] فایل‌های DNN یافت نشد. استفاده از Haar Cascade (دقت کمتر).")
            cascade_path = resource_path(os.path.join("assets", "haarcascade_frontalface_alt2.xml"))
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                raise RuntimeError("خطا: مدل تشخیص چهره در دسترس نیست.")

    def run(self):
        self.running = True
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print("خطا: دوربین در دسترس نیست.")
            return

        last_face_time = time.time()
        beep_emitted_this_cycle = False
        abandoned_emitted = False
        last_beep_time = 0

        while self.running:
            ret, frame = cap.read()
            if not ret:
                break

            h, w = frame.shape[:2]
            faces = []

            if self.use_dnn:
                blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), [104, 117, 123], False, False)
                self.net.setInput(blob)
                detections = self.net.forward()
                for i in range(detections.shape[2]):
                    confidence = detections[0, 0, i, 2]
                    if confidence > 0.5:
                        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                        (x1, y1, x2, y2) = box.astype("int")
                        faces.append((x1, y1, x2 - x1, y2 - y1))
            else:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.2, minNeighbors=6, minSize=(30, 30)
                )

            face_found = len(faces) > 0

            # رسم کادر
            for (x, y, fw, fh) in faces:
                cv2.rectangle(frame, (x, y), (x + fw, y + fh), (0, 255, 0), 2)

            # منطق حضور
            now = time.time()
            if face_found:
                if not abandoned_emitted:
                    if now - last_face_time > self.warning_delay:
                        self.presence_restored.emit()
                    last_face_time = now
                    beep_emitted_this_cycle = False
            else:
                absent_duration = now - last_face_time
                if self.warning_delay <= absent_duration < self.abandon_delay:
                    if not beep_emitted_this_cycle:
                        self.absent_warning.emit()
                        beep_emitted_this_cycle = True
                    if now - last_beep_time >= 1.0:
                        self.warning_beep.emit()
                        last_beep_time = now
                elif absent_duration >= self.abandon_delay and not abandoned_emitted:
                    self.abandoned.emit()
                    abandoned_emitted = True
                    self.running = False

            # ارسال فریم رنگی
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
            self.frame_ready.emit(qimg.copy())

            self.msleep(50)

        cap.release()

    def stop(self):
        self.running = False
        self.wait()