def rest_minutes(focus_minutes):
    """
    محاسبه زمان استراحت بهینه (دقیقه) با استفاده از مدل خستگی عصبی.
    همیشه حداقل ۳ و حداکثر ۳۰ دقیقه.
    """
    if focus_minutes <= 0:
        return 3
    raw = 0.08 * focus_minutes + 0.0022 * (focus_minutes ** 2) - 2
    return min(30, max(3, round(raw)))