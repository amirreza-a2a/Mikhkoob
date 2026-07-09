import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QCheckBox, QListWidget,
    QPushButton, QHBoxLayout, QLabel, QInputDialog, QMessageBox,
    QListWidgetItem, QLineEdit, QSpinBox, QGroupBox, QFormLayout,
    QDialog, QDialogButtonBox, QComboBox
)
from PyQt6.QtCore import Qt


class SettingsWidget(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setMinimumWidth(400)

        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # ---------- تب ۱: دوربین ----------
        camera_tab = QWidget()
        camera_layout = QVBoxLayout(camera_tab)
        self.camera_check = QCheckBox("فعال‌سازی تشخیص حضور با دوربین")
        self.camera_check.setChecked(self.config.camera_enabled)
        self.camera_check.stateChanged.connect(self._on_camera_changed)
        camera_layout.addWidget(self.camera_check)
        camera_layout.addStretch()
        self.tabs.addTab(camera_tab, "دوربین")

        # ---------- تب ۲: پروفایل‌های زمانی ----------
        presets_tab = QWidget()
        presets_layout = QVBoxLayout(presets_tab)
        self.presets_list = QListWidget()
        self._refresh_presets_list()
        presets_layout.addWidget(QLabel("پروفایل‌های زمانی (ستاره = پیش‌فرض):"))
        presets_layout.addWidget(self.presets_list)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ افزودن")
        edit_btn = QPushButton("✏️ ویرایش")
        del_btn = QPushButton("🗑️ حذف")
        default_btn = QPushButton("⭐ پیش‌فرض")
        add_btn.clicked.connect(self._add_preset)
        edit_btn.clicked.connect(self._edit_preset)
        del_btn.clicked.connect(self._delete_preset)
        default_btn.clicked.connect(self._set_default_preset)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(default_btn)
        presets_layout.addLayout(btn_layout)
        self.tabs.addTab(presets_tab, "پروفایل‌ها")

        # ---------- تب ۳: دسته‌های مسدودی ----------
        block_tab = QWidget()
        block_layout = QVBoxLayout(block_tab)

        self.block_list = QListWidget()
        self._refresh_block_list()
        block_layout.addWidget(QLabel("دسته‌های مسدودی (✅ = فعال، ❌ = غیرفعال، برچسب scope)"))
        block_layout.addWidget(self.block_list)

        block_btn_layout = QHBoxLayout()
        add_full_btn = QPushButton("➕ افزودن دسته (کل دامنه)")
        add_path_btn = QPushButton("➕ افزودن دسته (مسیر خاص)")
        edit_btn = QPushButton("✏️ ویرایش")
        delete_btn = QPushButton("🗑️ حذف")
        add_full_btn.clicked.connect(self._add_full_domain_category)
        add_path_btn.clicked.connect(self._add_path_category)
        edit_btn.clicked.connect(self._edit_category)
        delete_btn.clicked.connect(self._delete_category)
        block_btn_layout.addWidget(add_full_btn)
        block_btn_layout.addWidget(add_path_btn)
        block_btn_layout.addWidget(edit_btn)
        block_btn_layout.addWidget(delete_btn)
        block_layout.addLayout(block_btn_layout)

        self.tabs.addTab(block_tab, "مسدودی‌ها")

        main_layout.addWidget(self.tabs)

        # اتصال سیگنال تغییر چک‌باکس (فقط یک بار)
        self.block_list.itemChanged.connect(self._on_category_check_changed)

    # ------------------------ دوربین ------------------------
    def _on_camera_changed(self, state):
        self.config.data["camera_enabled"] = (state == 2)
        self.config.save_settings()

    # ------------------------ پروفایل‌ها ------------------------
    def _refresh_presets_list(self):
        self.presets_list.clear()
        for p in self.config.presets:
            star = "⭐ " if p.get("default") else ""
            item = QListWidgetItem(f"{star}{p['name']}  ({p['minutes']} دقیقه)")
            item.setData(Qt.ItemDataRole.UserRole, p)
            self.presets_list.addItem(item)

    def _add_preset(self):
        dlg = PresetDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, mins = dlg.get_data()
            self.config.presets.append({"name": name, "minutes": mins, "default": False})
            self.config.save_presets()
            self._refresh_presets_list()

    def _edit_preset(self):
        item = self.presets_list.currentItem()
        if not item:
            return
        p = item.data(Qt.ItemDataRole.UserRole)
        dlg = PresetDialog(self, p["name"], p["minutes"])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, mins = dlg.get_data()
            p["name"] = name
            p["minutes"] = mins
            self.config.save_presets()
            self._refresh_presets_list()

    def _delete_preset(self):
        item = self.presets_list.currentItem()
        if not item:
            return
        p = item.data(Qt.ItemDataRole.UserRole)
        self.config.presets.remove(p)
        self.config.save_presets()
        self._refresh_presets_list()

    def _set_default_preset(self):
        item = self.presets_list.currentItem()
        if not item:
            return
        p = item.data(Qt.ItemDataRole.UserRole)
        for preset in self.config.presets:
            preset["default"] = False
        p["default"] = True
        self.config.save_presets()
        self._refresh_presets_list()

    # ------------------------ دسته‌های مسدودی ------------------------
    def _refresh_block_list(self):
        try:
            self.block_list.itemChanged.disconnect(self._on_category_check_changed)
        except:
            pass

        self.block_list.clear()
        enabled_ids = self.config.get_enabled_categories()
        for cat in self.config.blocklists["categories"]:
            check = "✅" if cat["id"] in enabled_ids else "❌"
            dom_count = len(cat.get("domains", []))
            path_rules = cat.get("path_rules", {})
            path_count = sum(len(v) for v in path_rules.values())
            scope = cat.get("scope", "focus")
            desc = f"{check} [{scope}] {cat['name']} | {dom_count} دامنه"
            if path_count > 0:
                desc += f" + {path_count} مسیر خاص"
            item = QListWidgetItem(desc)
            item.setData(Qt.ItemDataRole.UserRole, cat)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if cat["id"] in enabled_ids else Qt.CheckState.Unchecked)
            self.block_list.addItem(item)

        self.block_list.itemChanged.connect(self._on_category_check_changed)

    def _on_category_check_changed(self, item):
        cat = item.data(Qt.ItemDataRole.UserRole)
        enabled = self.config.get_enabled_categories()
        if item.checkState() == Qt.CheckState.Checked:
            if cat["id"] not in enabled:
                enabled.append(cat["id"])
        else:
            if cat["id"] in enabled:
                enabled.remove(cat["id"])
        self.config.set_enabled_categories(enabled)

        # به‌روزرسانی ظاهر همان آیتم
        check = "✅" if cat["id"] in enabled else "❌"
        dom_count = len(cat.get("domains", []))
        path_count = sum(len(v) for v in cat.get("path_rules", {}).values())
        scope = cat.get("scope", "focus")
        desc = f"{check} [{scope}] {cat['name']} | {dom_count} دامنه"
        if path_count > 0:
            desc += f" + {path_count} مسیر خاص"
        item.setText(desc)

    def _add_full_domain_category(self):
        name, ok = QInputDialog.getText(self, "دسته جدید", "نام دسته:")
        if ok and name:
            cat_id = name.lower().replace(" ", "_")
            if self._cat_id_exists(cat_id):
                QMessageBox.warning(self, "خطا", "این شناسه تکراری است.")
                return
            new_cat = {
                "id": cat_id,
                "name": name,
                "default": False,
                "dominans": [],
                "path_rules": {},
                "scope": "focus"   # پیش‌فرض
            }
            self.config.blocklists["categories"].append(new_cat)
            self.config.save_blocklists()
            self._refresh_block_list()
            self._edit_domains(new_cat, focus_on_paths=False)

    def _add_path_category(self):
        name, ok = QInputDialog.getText(self, "دسته جدید", "نام دسته:")
        if ok and name:
            cat_id = name.lower().replace(" ", "_")
            if self._cat_id_exists(cat_id):
                QMessageBox.warning(self, "خطا", "این شناسه تکراری است.")
                return
            new_cat = {
                "id": cat_id,
                "name": name,
                "default": False,
                "domains": [],
                "path_rules": {},
                "scope": "focus"
            }
            self.config.blocklists["categories"].append(new_cat)
            self.config.save_blocklists()
            self._refresh_block_list()
            self._edit_domains(new_cat, focus_on_paths=True)

    def _edit_category(self):
        item = self.block_list.currentItem()
        if not item:
            return
        cat = item.data(Qt.ItemDataRole.UserRole)
        self._edit_domains(cat, focus_on_paths=False)

    def _delete_category(self):
        item = self.block_list.currentItem()
        if not item:
            return
        cat = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "تأیید حذف",
                                     f"آیا از حذف دسته «{cat['name']}» اطمینان دارید؟",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.config.blocklists["categories"].remove(cat)
            self.config.save_blocklists()
            self._refresh_block_list()

    def _cat_id_exists(self, cat_id):
        for cat in self.config.blocklists["categories"]:
            if cat["id"] == cat_id:
                return True
        return False

    def _edit_domains(self, cat, focus_on_paths=False):
        dlg = DomainEditorDialog(self, cat, focus_on_paths)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_domains, new_path_rules, new_scope = dlg.get_data()
            cat["domains"] = new_domains
            cat["path_rules"] = new_path_rules
            cat["scope"] = new_scope
            self.config.save_blocklists()
            self._refresh_block_list()


# ================== دیالوگ ویرایش پروفایل ==================
class PresetDialog(QDialog):
    def __init__(self, parent=None, name="", minutes=45):
        super().__init__(parent)
        self.setWindowTitle("پروفایل زمانی")
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(name)
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(5, 180)
        self.minutes_spin.setValue(minutes)
        layout.addRow("نام:", self.name_edit)
        layout.addRow("دقیقه:", self.minutes_spin)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return self.name_edit.text(), self.minutes_spin.value()


# ================== دیالوگ ویرایش دامنه‌ها و مسیرهای خاص ==================
class DomainEditorDialog(QDialog):
    def __init__(self, parent, category, focus_on_paths=False):
        super().__init__(parent)
        self.category = category
        self.setWindowTitle(f"ویرایش دسته: {category['name']}")
        layout = QVBoxLayout(self)

        # بخش دامنه‌های کامل
        layout.addWidget(QLabel("<b>دامنه‌های مسدود کامل (با کاما جدا کنید):</b>"))
        self.domains_edit = QLineEdit()
        self.domains_edit.setText(", ".join(category.get("domains", [])))
        layout.addWidget(self.domains_edit)

        # بخش مسیرهای خاص
        layout.addWidget(QLabel("<b>مسدودسازی مسیر خاص (domain/path):</b>"))
        self.path_list = QListWidget()
        self._populate_path_list()
        layout.addWidget(self.path_list)

        # افزودن مسیر جدید
        add_path_layout = QHBoxLayout()
        self.path_domain = QLineEdit()
        self.path_domain.setPlaceholderText("youtube.com")
        self.path_path = QLineEdit()
        self.path_path.setPlaceholderText("/shorts")
        add_path_btn = QPushButton("➕ افزودن مسیر")
        add_path_btn.clicked.connect(self._add_path_rule)
        add_path_layout.addWidget(QLabel("دامنه:"))
        add_path_layout.addWidget(self.path_domain)
        add_path_layout.addWidget(QLabel("مسیر:"))
        add_path_layout.addWidget(self.path_path)
        add_path_layout.addWidget(add_path_btn)
        layout.addLayout(add_path_layout)

        remove_path_btn = QPushButton("🗑️ حذف مسیر انتخاب‌شده")
        remove_path_btn.clicked.connect(self._remove_path_rule)
        layout.addWidget(remove_path_btn)

        # انتخاب scope
        layout.addWidget(QLabel("<b>Scope (زمان فعال بودن):</b>"))
        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["always", "focus", "rest"])
        current_scope = category.get("scope", "focus")
        self.scope_combo.setCurrentText(current_scope)
        layout.addWidget(self.scope_combo)

        if focus_on_paths:
            self.path_domain.setFocus()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_path_list(self):
        self.path_list.clear()
        for domain, paths in self.category.get("path_rules", {}).items():
            for path in paths:
                self.path_list.addItem(f"{domain}  →  {path}")

    def _add_path_rule(self):
        domain = self.path_domain.text().strip()
        path = self.path_path.text().strip()
        if not domain or not path:
            QMessageBox.warning(self, "ورودی ناقص", "هر دو فیلد دامنه و مسیر باید پر شوند.")
            return
        for i in range(self.path_list.count()):
            if self.path_list.item(i).text() == f"{domain}  →  {path}":
                QMessageBox.information(self, "تکراری", "این مسیر قبلاً اضافه شده است.")
                return
        self.path_list.addItem(f"{domain}  →  {path}")
        self.path_domain.clear()
        self.path_path.clear()

    def _remove_path_rule(self):
        current = self.path_list.currentRow()
        if current >= 0:
            self.path_list.takeItem(current)

    def get_data(self):
        domains = [d.strip() for d in self.domains_edit.text().split(",") if d.strip()]
        path_rules = {}
        for i in range(self.path_list.count()):
            text = self.path_list.item(i).text()
            parts = text.split("  →  ")
            if len(parts) == 2:
                d, p = parts[0].strip(), parts[1].strip()
                if d not in path_rules:
                    path_rules[d] = []
                if p not in path_rules[d]:
                    path_rules[d].append(p)
        scope = self.scope_combo.currentText()
        return domains, path_rules, scope