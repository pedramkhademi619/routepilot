"""Application translation and internationalization manager for RoutePilot."""

import json
import logging
import os
from typing import Any

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class TranslationManager(QObject):
    """Manages application localization, translations, and dynamic language switching."""

    language_changed = pyqtSignal(str)

    _instance: "TranslationManager | None" = None

    CONFIG_PATH = os.path.expanduser("~/.config/routepilot/settings.json")

    TRANSLATIONS: dict[str, dict[str, str]] = {
        "en": {
            # Navigation
            "app.title": "RoutePilot — Traffic Policy Routing",
            "nav.overview": "Overview",
            "nav.rules": "Traffic Rules",
            "nav.connections": "Connections",
            "nav.diagnostics": "Diagnostics",
            "nav.settings": "Settings",
            # Common
            "common.active": "Active",
            "common.disabled": "Disabled",
            "common.enable": "Enable",
            "common.disable": "Disable",
            "common.edit": "Edit",
            "common.delete": "Delete",
            "common.cancel": "Cancel",
            "common.save": "Save",
            "common.refresh": "Refresh",
            "common.apply": "⚡ Apply to Kernel",
            "common.create_rule": "+ Create Rule",
            "common.filter_placeholder": "Filter rules by name, domain, or IP...",
            # Overview
            "overview.title": "Overview",
            "overview.subtitle": "Live Linux connection discovery, active VPN egress, and routing policy status.",
            "overview.card_egress": "Network & VPN Egress",
            "overview.scanning": "Scanning network...",
            "overview.card_rules": "Traffic Rules",
            "overview.manage_rules": "Manage Rules",
            "overview.reality_title": "Observed Network Reality vs Intended Policy",
            "overview.reality_desc": (
                "• Direct internet bypass routes traffic out physical non-VPN interfaces via Linux kernel policy routing (RPDB).\n"
                "• Sockets established before a rule was applied remain bound to their original interface until reopened.\n"
                "• Domain routing uses resolved IP sets: shared CDN/Anycast edge IPs (e.g. Cloudflare) affect other domains on that edge.\n"
                "• Applications with internal DNS-over-HTTPS (DoH) may bypass local resolver configuration."
            ),
            # Rules
            "rules.title": "Traffic Rules",
            "rules.subtitle": "Define which domains, IP ranges, or applications bypass VPN or use specific connections.",
            "rules.col_state": "State",
            "rules.col_prio": "Prio",
            "rules.col_name": "Rule Name",
            "rules.col_target": "Target Selector",
            "rules.col_action": "Action",
            "rules.col_condition": "Condition",
            "rules.col_controls": "Controls",
            # Connections
            "connections.title": "Network & VPN Connections",
            "connections.subtitle": "Discovered Linux interfaces, NetworkManager active connections, and routing metrics.",
            "connections.empty": "No active network connections detected.",
            # Diagnostics
            "diagnostics.title": "Diagnostics & Route Evaluation",
            "diagnostics.subtitle": "Verify how traffic to any destination IP or domain is evaluated against your active policies.",
            "diagnostics.sim_title": "Simulate Policy Evaluation",
            "diagnostics.input_placeholder": "Enter destination IP or domain (e.g. 198.51.100.1 or example.com)...",
            "diagnostics.eval_btn": "Evaluate Path",
            "diagnostics.awaiting": "Awaiting evaluation...",
            "diagnostics.awaiting_desc": "Enter a destination above to trace its effective kernel route and winning rule.",
            "diagnostics.bundle_title": "Sanitized Support Bundle",
            "diagnostics.bundle_desc": (
                "Export an anonymized JSON report containing active interface types, metrics, and rule "
                "definitions. All passwords, authentication tokens, and user credentials are automatically stripped."
            ),
            "diagnostics.export_btn": "Export Sanitized Bundle (.json)",
            # Settings
            "settings.title": "Settings & Maintenance",
            "settings.subtitle": "Appearance preferences, emergency recovery, and system maintenance.",
            "settings.lang_card": "Interface Language",
            "settings.lang_label": "Language:",
            "settings.lang_en": "English",
            "settings.lang_fa": "فارسی (Persian)",
            "settings.theme_card": "Appearance Theme",
            "settings.theme_label": "Color Scheme:",
            "settings.theme_dark": "Dark Theme",
            "settings.theme_light": "Light Theme",
            "settings.purge_card": "Emergency State Purge",
            "settings.purge_desc": (
                "Purges all RoutePilot nftables tables, policy routing rules, and custom tables.\n"
                "Use this if network connectivity feels stalled or after an unexpected service crash."
            ),
            "settings.reset_btn": "Emergency Reset Kernel State",
            "settings.clear_btn": "Clear All Rules",
            "settings.about_title": "About RoutePilot",
            "settings.about_desc": (
                "RoutePilot v0.1.0\n"
                "Open-source Linux Desktop Utility for Selective VPN Bypass and Traffic Routing.\n"
                "Licensed under GNU General Public License v3.0 or later (GPL-3.0-or-later).\n"
                "https://github.com/routepilot/routepilot"
            ),
            # Editor
            "editor.title_new": "Configure Traffic Rule",
            "editor.title_edit": "Edit Traffic Rule",
            "editor.name": "Rule Name:",
            "editor.target_type": "Target Type:",
            "editor.target_value": "Target Value:",
            "editor.action": "Action:",
            "editor.priority": "Priority (lower = higher prio):",
            "editor.condition": "Activation Condition:",
            "editor.failure": "Failure Behavior:",
            "editor.explanation": "Plain-Language Rule Explanation:",
            "editor.cancel": "Cancel",
            "editor.save": "Save Rule",
        },
        "fa": {
            # Navigation
            "app.title": "RoutePilot — مسیریابی هوشمند ترافیک و بای‌پس VPN",
            "nav.overview": "نمای کلی",
            "nav.rules": "قوانین ترافیک",
            "nav.connections": "اتصالات شبکه",
            "nav.diagnostics": "عیب‌یابی مسیر",
            "nav.settings": "تنظیمات",
            # Common
            "common.active": "فعال",
            "common.disabled": "غیرفعال",
            "common.enable": "فعال‌سازی",
            "common.disable": "غیرفعال‌سازی",
            "common.edit": "ویرایش",
            "common.delete": "حذف",
            "common.cancel": "انصراف",
            "common.save": "ذخیره",
            "common.refresh": "به‌روزرسانی",
            "common.apply": "⚡ اعمال به هسته لینوکس",
            "common.create_rule": "+ ایجاد قانون جدید",
            "common.filter_placeholder": "فیلتر قوانین بر اساس نام، دامنه، یا آی‌پی...",
            # Overview
            "overview.title": "نمای کلی",
            "overview.subtitle": "وضعیت زنده اتصالات لینوکس، خروجی فعال VPN و سیاست‌های مسیریابی.",
            "overview.card_egress": "خروجی شبکه و VPN",
            "overview.scanning": "در حال اسکن اتصالات شبکه...",
            "overview.card_rules": "قوانین ترافیک",
            "overview.manage_rules": "مدیریت قوانین",
            "overview.reality_title": "واقعیت فنی مشاهده‌شده شبکه در برابر سیاست تعیین‌شده",
            "overview.reality_desc": (
                "• بای‌پس اینترنت مستقیم، ترافیک را از رابط‌های فیزیکی غیر VPN از طریق جدول‌های مسیریابی هسته لینوکس (RPDB) هدایت می‌کند.\n"
                "• سوکت‌های بازشده قبل از اعمال قانون تا زمان بازگشایی مجدد به رابط اولیه متصل می‌مانند.\n"
                "• مسیریابی بر اساس دامنه از آی‌پی‌های رزولوشده استفاده می‌کند: آی‌پی‌های اشتراکی CDN بر دامنه‌های دیگر روی همان لبه اثر می‌گذارند.\n"
                "• برنامه‌های دارای DNS داخلی رمزگذاری‌شده (DoH) ممکن است تنظیمات DNS محلی را نادیده بگیرند."
            ),
            # Rules
            "rules.title": "قوانین هدایت ترافیک",
            "rules.subtitle": "مشخص کنید کدام دامنه‌ها، رنج‌های آی‌پی یا برنامه‌ها VPN را دور بزنند یا از اتصال خاصی عبور کنند.",
            "rules.col_state": "وضعیت",
            "rules.col_prio": "اولویت",
            "rules.col_name": "نام قانون",
            "rules.col_target": "مقصد / دامنه",
            "rules.col_action": "عملیات",
            "rules.col_condition": "شرط فعال‌سازی",
            "rules.col_controls": "عملیات",
            # Connections
            "connections.title": "اتصالات شبکه و VPN",
            "connections.subtitle": "رابط‌های شناسایی‌شده لینوکس، اتصالات فعال NetworkManager و متریک‌های مسیریابی.",
            "connections.empty": "هیچ اتصال فعالی شناسایی نشد.",
            # Diagnostics
            "diagnostics.title": "عیب‌یابی و ارزیابی مسیر",
            "diagnostics.subtitle": "بررسی نحوه ارزیابی و مسیریابی ترافیک به مقصد هر دامنه یا آدرس آی‌پی.",
            "diagnostics.sim_title": "شبیه‌سازی ارزیابی مسیر ترافیک",
            "diagnostics.input_placeholder": "دامنه یا آی‌پی مقصد را وارد کنید (مثلاً soft98.ir یا examplebank.ir)...",
            "diagnostics.eval_btn": "ارزیابی مسیر",
            "diagnostics.awaiting": "در انتظار ارزیابی...",
            "diagnostics.awaiting_desc": "یک مقصد در بالا وارد کنید تا مسیر موثر هسته لینوکس و قانون برنده ردیابی شود.",
            "diagnostics.bundle_title": "بسته پشتیبانی و عیب‌یابی امن",
            "diagnostics.bundle_desc": (
                "خروجی گزارش JSON ناشناس شامل انواع رابط‌های فعال، متریک‌ها و تعاریف قوانین. "
                "تمام رمزهای عبور، توکن‌های احراز هویت و اطلاعات کاربری به طور خودکار حذف می‌شوند."
            ),
            "diagnostics.export_btn": "ذخیره بسته تشخیصی (.json)",
            # Settings
            "settings.title": "تنظیمات و نگهداری",
            "settings.subtitle": "تنظیمات ظاهری، زبان رابط کاربری، بازیابی اضطراری و نگهداری سیستم.",
            "settings.lang_card": "زبان رابط کاربری (Language)",
            "settings.lang_label": "انتخاب زبان:",
            "settings.lang_en": "English (انگلیسی)",
            "settings.lang_fa": "فارسی (Persian)",
            "settings.theme_card": "پوسته ظاهری",
            "settings.theme_label": "تم رنگی:",
            "settings.theme_dark": "تم تیره (Dark)",
            "settings.theme_light": "تم روشن (Light)",
            "settings.purge_card": "پاکسازی اضطراری وضعیت هسته",
            "settings.purge_desc": (
                "تمام جداول nftables، قوانین مسیریابی policy routing و تنظیمات موقت RoutePilot را به طور کامل پاک می‌کند.\n"
                "در صورت اختلال در اینترنت یا پس از بسته شدن غیرمنتظره برنامه از این گزینه استفاده کنید."
            ),
            "settings.reset_btn": "بازنشانی اضطراری تنظیمات هسته",
            "settings.clear_btn": "پاک کردن تمام قوانین",
            "settings.about_title": "درباره RoutePilot",
            "settings.about_desc": (
                "RoutePilot نسخه ۰.۱.۰\n"
                "ابزار متن‌باز دسکتاپ لینوکس برای بای‌پس انتخابی VPN و هدایت هوشمند ترافیک.\n"
                "تحت مجوز عمومی گنو نسخه ۳ یا بالاتر (GPL-3.0-or-later).\n"
                "https://github.com/routepilot/routepilot"
            ),
            # Editor
            "editor.title_new": "پیکربندی قانون ترافیک",
            "editor.title_edit": "ویرایش قانون ترافیک",
            "editor.name": "نام قانون:",
            "editor.target_type": "نوع هدف:",
            "editor.target_value": "مقدار هدف:",
            "editor.action": "عملیات:",
            "editor.priority": "اولویت (عدد کمتر = اولویت بالاتر):",
            "editor.condition": "شرط فعال‌سازی:",
            "editor.failure": "رفتار در صورت قطعی اتصال:",
            "editor.explanation": "توضیح روان عملکرد قانون:",
            "editor.cancel": "انصراف",
            "editor.save": "ذخیره قانون",
        },
    }

    def __init__(self) -> None:
        super().__init__()
        self._current_language = self._load_persisted_language()

    @classmethod
    def instance(cls) -> "TranslationManager":
        """Singleton accessor for TranslationManager."""
        if cls._instance is None:
            cls._instance = TranslationManager()
        return cls._instance

    @property
    def current_language(self) -> str:
        return self._current_language

    def translate(self, key: str, **kwargs: Any) -> str:
        """Translates a key into current language with optional format interpolations."""
        lang_dict = self.TRANSLATIONS.get(self._current_language, self.TRANSLATIONS["en"])
        val = lang_dict.get(key)
        if val is None:
            # Fallback to English
            val = self.TRANSLATIONS["en"].get(key, key)
        if kwargs:
            try:
                return val.format(**kwargs)
            except Exception:
                return val
        return val

    def t(self, key: str, **kwargs: Any) -> str:
        """Short alias for translate."""
        return self.translate(key, **kwargs)

    def set_language(self, lang: str) -> None:
        """Switches active language, sets Qt layout direction, and notifies observers."""
        if lang not in self.TRANSLATIONS:
            lang = "en"
        if self._current_language == lang:
            return

        self._current_language = lang
        self._persist_language(lang)

        # Update Qt layout direction for RTL support in Persian
        app = QApplication.instance()
        if app is not None:
            if lang == "fa":
                app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            else:
                app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self.language_changed.emit(lang)

    def _load_persisted_language(self) -> str:
        if os.path.exists(self.CONFIG_PATH):
            try:
                with open(self.CONFIG_PATH, encoding="utf-8") as f:
                    data = json.load(f)
                    return str(data.get("language", "en"))
            except Exception as e:
                logger.warning("Could not read language from %s: %s", self.CONFIG_PATH, e)
        return "en"

    def _persist_language(self, lang: str) -> None:
        try:
            os.makedirs(os.path.dirname(self.CONFIG_PATH), exist_ok=True)
            data: dict[str, Any] = {}
            if os.path.exists(self.CONFIG_PATH):
                with open(self.CONFIG_PATH, encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = {}
            data["language"] = lang
            with open(self.CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning("Could not persist language to %s: %s", self.CONFIG_PATH, e)
