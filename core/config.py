import json
import os

class Config:
    def __init__(self, settings_path=None, presets_path=None, blocklists_path=None):
        # دایرکتوری داده کاربر
        data_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "focusguardian")
        os.makedirs(data_dir, exist_ok=True)
        
        self.settings_path = settings_path or os.path.join(data_dir, "settings.json")
        self.presets_path = presets_path or os.path.join(data_dir, "presets.json")
        self.blocklists_path = blocklists_path or os.path.join(data_dir, "blocklists.json")
        # بقیه کد ...

        # تنظیمات عمومی
        self.data = {
            "camera_enabled": True,
            "enabled_categories": ["news_sites", "short_videos"]
        }
        self.load(self.settings_path, self.data)

        # پروفایل‌های زمانی
        self.presets = [
            {"name": "دروس عمومی", "minutes": 45, "default": True},
            {"name": "دروس تخصصی", "minutes": 75, "default": False}
        ]
        self.load(self.presets_path, self.presets)

        # لیست‌های مسدودی (همراه با scope)
        self.blocklists = {
            "categories": [
                {
                    "id": "news_sites",
                    "name": "سایت‌های خبری",
                    "scope": "always",
                    "default": True,
                    "domains": ["bbc.com", "cnn.com", "irna.ir", "aparat.com"]
                },
                {
                    "id": "short_videos",
                    "name": "ویدیوهای کوتاه",
                    "scope": "focus",
                    "default": True,
                    "domains": ["youtube.com", "tiktok.com"],
                    "path_rules": {"youtube.com": ["/shorts"]}
                }
            ]
        }
        self.load(self.blocklists_path, self.blocklists)

    def load(self, path, default_data):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(default_data, list):
                        default_data.clear()
                        default_data.extend(loaded)
                    elif isinstance(default_data, dict):
                        default_data.clear()
                        default_data.update(loaded)
            except:
                pass

    def save_settings(self):
        self._save(self.settings_path, self.data)

    def save_presets(self):
        self._save(self.presets_path, self.presets)

    def save_blocklists(self):
        self._save(self.blocklists_path, self.blocklists)

    def _save(self, path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @property
    def session_duration_minutes(self):
        """
        اولویت اول: مقدار ذخیره‌شده توسط کاربر از طریق دیال (در settings.json)
        اولویت دوم: پروفایل پیش‌فرض
        اولویت سوم: اولین پروفایل موجود
        اولویت آخر: ۴۵ دقیقه
        """
        # اگر کاربر قبلاً دیال را چرخانده باشد، مقدار در self.data ذخیره شده است
        if "session_duration_minutes" in self.data:
            return self.data["session_duration_minutes"]

        # در غیر این صورت، از پروفایل‌ها بخوان
        for p in self.presets:
            if p.get("default"):
                return p["minutes"]
        if self.presets:
            return self.presets[0]["minutes"]
        return 45

    @property
    def camera_enabled(self):
        return self.data.get("camera_enabled", True)

    def get_enabled_categories(self):
        return self.data.get("enabled_categories", [])

    def set_enabled_categories(self, ids):
        self.data["enabled_categories"] = ids
        self.save_settings()

    def get_categories_by_scope(self, scope):
        """بازگرداندن دسته‌های فعال با scope مشخص"""
        enabled_ids = self.get_enabled_categories()
        result = []
        for cat in self.blocklists["categories"]:
            if cat["id"] in enabled_ids and cat.get("scope", "focus") == scope:
                result.append(cat)
        return result

    def get_all_domains_for_scope(self, scope):
        """مجموعه دامنه‌ها و path_rules برای یک scope خاص"""
        cats = self.get_categories_by_scope(scope)
        domains = []
        path_rules = {}
        for cat in cats:
            domains.extend(cat.get("domains", []))
            if "path_rules" in cat:
                for d, paths in cat["path_rules"].items():
                    if d not in path_rules:
                        path_rules[d] = []
                    path_rules[d].extend(paths)
        # اضافه کردن کلیدهای path_rules به لیست دامنه‌ها (اگر وجود ندارند)
        for d in path_rules:
            if d not in domains:
                domains.append(d)
        unique_domains = list(set(domains))
        return unique_domains, path_rules