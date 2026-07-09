import os
import arabic_reshaper
from bidi.algorithm import get_display

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QGridLayout, QGroupBox)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
import matplotlib.pyplot as plt
import matplotlib

# تنظیم فونت فارسی
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "Vazir.ttf")
if os.path.exists(FONT_PATH):
    matplotlib.font_manager.fontManager.addfont(FONT_PATH)
    prop = FontProperties(fname=FONT_PATH)
    font_name = prop.get_name()
    plt.rcParams['font.family'] = font_name
else:
    prop = FontProperties()

def fa(text: str) -> str:
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

class StatsWidget(QWidget):
    def __init__(self, logger, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.setMinimumWidth(400)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # کارت خلاصه
        summary_card = QGroupBox("خلاصه امروز")
        summary_card.setStyleSheet(
            "QGroupBox { color: #cccccc; font-weight: bold; border: 1px solid #444; "
            "border-radius: 8px; padding: 10px; }"
        )
        self.summary_layout = QGridLayout()
        self.summary_layout.setHorizontalSpacing(20)
        self.lbl_complete = QLabel()
        self.lbl_incomplete = QLabel()
        self.lbl_avg = QLabel()
        self.lbl_score = QLabel()
        for lbl in (self.lbl_complete, self.lbl_incomplete, self.lbl_avg, self.lbl_score):
            lbl.setStyleSheet("color: white; font-size: 14px;")
        self.summary_layout.addWidget(QLabel("✅ کامل:"), 0, 0)
        self.summary_layout.addWidget(self.lbl_complete, 0, 1)
        self.summary_layout.addWidget(QLabel("⚠️ ناقص:"), 0, 2)
        self.summary_layout.addWidget(self.lbl_incomplete, 0, 3)
        self.summary_layout.addWidget(QLabel("⏱️ میانگین:"), 1, 0)
        self.summary_layout.addWidget(self.lbl_avg, 1, 1)
        self.summary_layout.addWidget(QLabel("🎯 امتیاز:"), 1, 2)
        self.summary_layout.addWidget(self.lbl_score, 1, 3)
        summary_card.setLayout(self.summary_layout)
        main_layout.addWidget(summary_card)

        # نمودار میله‌ای
        self.bar_chart = FigureCanvas(Figure(figsize=(4, 2.5)))
        self.bar_ax = self.bar_chart.figure.add_subplot(111)
        main_layout.addWidget(self.bar_chart)

        # هیستوگرام
        self.hist_chart = FigureCanvas(Figure(figsize=(4, 2.5)))
        self.hist_ax = self.hist_chart.figure.add_subplot(111)
        main_layout.addWidget(self.hist_chart)

        # نقشه حرارتی
        self.heatmap_chart = FigureCanvas(Figure(figsize=(4, 2.5)))
        self.heatmap_ax = self.heatmap_chart.figure.add_subplot(111)
        main_layout.addWidget(self.heatmap_chart)

        # نمودار حواس‌پرتی (دایره‌ای ساده)
        self.pie_chart = FigureCanvas(Figure(figsize=(3, 2.5)))
        self.pie_ax = self.pie_chart.figure.add_subplot(111)
        main_layout.addWidget(self.pie_chart)

        main_layout.addStretch()
        self.refresh()

    def refresh(self):
        stats = self.logger.get_daily_stats()
        complete_sec = stats.get("complete", 0)
        incomplete_sec = stats.get("incomplete", 0)
        self.lbl_complete.setText(f"{complete_sec // 60} دقیقه")
        self.lbl_incomplete.setText(f"{incomplete_sec // 60} دقیقه")
        avg_len = self.logger.get_average_session_length()
        self.lbl_avg.setText(f"{avg_len:.0f} دقیقه")
        score = self.logger.get_focus_score_today()
        self.lbl_score.setText(f"{score}/100")

        # نمودار میله‌ای (روزهای هفته)
        daily = self.logger.get_weekly_daily_totals()
        labels = [d[5:] for d, _ in daily]
        values = [v for _, v in daily]
        self.bar_ax.clear()
        self.bar_ax.bar(labels, values, color='#6c5ce7')
        self.bar_ax.set_title(fa("دقایق تمرکز کامل (۷ روز)"), fontproperties=prop, color='#cccccc')
        self.bar_ax.set_ylabel(fa("دقیقه"), fontproperties=prop, color='#cccccc')
        self.bar_ax.tick_params(colors='#cccccc')
        self.bar_ax.set_facecolor('#1e1e1e')
        self.bar_chart.figure.set_facecolor('#1e1e1e')

        # هیستوگرام
        durations = self.logger.get_completed_durations()
        if durations:
            self.hist_ax.clear()
            self.hist_ax.hist(durations, bins=10, color='#a29bfe', edgecolor='white')
            self.hist_ax.set_title(fa("توزیع طول جلسات کامل"), fontproperties=prop, color='#cccccc')
            self.hist_ax.set_xlabel(fa("دقیقه"), fontproperties=prop, color='#cccccc')
            self.hist_ax.set_ylabel(fa("تعداد"), fontproperties=prop, color='#cccccc')
            self.hist_ax.tick_params(colors='#cccccc')
        else:
            self.hist_ax.clear()
            self.hist_ax.text(0.5, 0.5, fa("بدون داده"), ha='center', va='center', color='#888888')
            self.hist_ax.set_facecolor('#1e1e1e')
        self.hist_chart.figure.set_facecolor('#1e1e1e')

        # نقشه حرارتی
        hours_data = self.logger.get_hourly_heatmap_data()
        self.heatmap_ax.clear()
        self.heatmap_ax.bar(range(24), hours_data, color='#00cec9')
        self.heatmap_ax.set_title(fa("بازدهی ساعتی (۳۰ روز)"), fontproperties=prop, color='#cccccc')
        self.heatmap_ax.set_xlabel(fa("ساعت روز"), fontproperties=prop, color='#cccccc')
        self.heatmap_ax.set_ylabel(fa("دقیقه"), fontproperties=prop, color='#cccccc')
        self.heatmap_ax.tick_params(colors='#cccccc')
        self.heatmap_ax.set_facecolor('#1e1e1e')
        self.heatmap_chart.figure.set_facecolor('#1e1e1e')

        # نمودار حواس‌پرتی
        # مجموع تلاش‌های مسدودشده امروز
        self.pie_ax.clear()
        total_distractions = 0
        sessions = self.logger.get_today_sessions()
        for row in sessions:
            # row = (duration_seconds, target_duration, status, distraction_attempts)
            total_distractions += row[3]

        if total_distractions > 0:
            labels = [fa("تلاش‌های مسدود"), fa("بدون حواس‌پرتی")]
            sizes = [total_distractions, max(0, 10 - total_distractions)]  # نمایش نسبی
            self.pie_ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
                            colors=['#e74c3c', '#2ecc71'], textprops={'fontproperties': prop, 'color': 'white'})
            self.pie_ax.set_title(fa("امروز {} تلاش مسدودشده").format(total_distractions),
                                  fontproperties=prop, color='#cccccc')
        else:
            self.pie_ax.text(0.5, 0.5, fa("بدون حواس‌پرتی"), ha='center', va='center',
                             fontproperties=prop, color='#888888')
        self.pie_ax.set_facecolor('#1e1e1e')
        self.pie_chart.figure.set_facecolor('#1e1e1e')

        self.bar_chart.draw()
        self.hist_chart.draw()
        self.heatmap_chart.draw()
        self.pie_chart.draw()