from PyQt6.QtCore import QProcess
import json

class HostsBlocker:
    def __init__(self, config):
        self.config = config
        self.process = None

    def get_domains_to_block(self):
        """بر اساس دسته‌های فعال، دامنه‌ها و path_rules را برمی‌گرداند"""
        enabled_ids = self.config.get_enabled_categories()
        domains = []
        path_rules = {}
        for cat in self.config.blocklists["categories"]:
            if cat["id"] in enabled_ids:
                domains.extend(cat.get("domains", []))
                if "path_rules" in cat:
                    for d, paths in cat["path_rules"].items():
                        if d not in path_rules:
                            path_rules[d] = []
                        path_rules[d].extend(paths)
        # حذف تکراری‌ها
        unique_domains = list(set(domains))
        return unique_domains, path_rules

    def enable(self, domains):
        """مسدود کردن دامنه‌ها از طریق hosts (دیگر استفاده نمی‌شود ولی نگه می‌داریم)"""
        self._run_script("enable", domains)

    def disable(self, domains):
        self._run_script("disable", domains)

    def _run_script(self, action, domains):
        # این متد را برای سازگاری نگه می‌داریم ولی دیگر فراخوانی نمی‌شود چون از افزونه استفاده می‌کنیم
        pass