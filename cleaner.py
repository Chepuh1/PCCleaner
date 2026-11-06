"""
PCCleaner — приложение для очистки и обслуживания ПК на tkinter (Windows 10/11).
https://github.com/Chepuh1/PCCleaner  •  лицензия MIT

Запуск:   python cleaner.py
Для гладкой графики (рекомендуется):   pip install pillow
Сборка .exe:   build_exe_x64.bat

Возможности:
  • очистка временных файлов, кэша браузеров, корзины (быстрый параллельный обход);
  • белый список — файлы и папки, которые никогда не удаляются;
  • «Особые файлы» — ручной выбор скрытых, системных и защищённых файлов;
  • живые индикаторы нагрузки CPU, GPU и RAM;
  • очистка оперативной памяти (рабочие наборы процессов) с защитой системных процессов;
  • «Игровой режим» — максимальная производительность Windows (с откатом);
  • файловый менеджер: удаление программ, игр и приложений Microsoft Store,
    бэкап файлов и конфигов в .zip одной кнопкой;
  • 5 тем оформления и 2 языка (русский / English) — переключаются без перезапуска;
  • вход и выход из режима администратора.

Параметры запуска:
  --keep-ide   не отрываться от консоли и не закрывать PyCharm
"""

import concurrent.futures as cf
import ctypes
import json
import math
import ntpath as _np
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import xml.etree.ElementTree as ET
import zipfile
import webbrowser
import zlib
from ctypes import wintypes
from tkinter import filedialog, messagebox, ttk

try:
    import winreg
except ImportError:  # не Windows
    winreg = None

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk

    HAS_PIL = True
    RESAMPLE = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
except Exception:
    HAS_PIL = False

IS_WIN = sys.platform == "win32"
NO_WINDOW = 0x08000000 if IS_WIN else 0
FROZEN = bool(getattr(sys, "frozen", False))  # запущено как .exe

# Закрывать PyCharm после запуска (только если программу запустили из PyCharm).
# Окно закрывается «мягко», как крестиком. Поставьте True, чтобы включить.
AUTO_CLOSE_IDE = False

APP_NAME = "PCCleaner"  # название программы — одинаковое на всех языках
APP_VERSION = "0.11.0"
# Контакты для обратной связи (раздел «О приложении»): (подпись, ник/адрес, ссылка).
SOCIAL_LINKS = [
    ("✈  Telegram", "@vitaliydyadya", "https://t.me/vitaliydyadya"),
    ("📷  Instagram", "@cheeb15", "https://www.instagram.com/cheeb15/"),
    ("✉  E-mail", "dimaborovkov68@gmail.com", "mailto:dimaborovkov68@gmail.com"),
    ("</>  GitHub", "Chepuh1/PCCleaner", "https://github.com/Chepuh1/PCCleaner"),
]

# ───────────────────────── Темы оформления, цвета и шрифты ─────────────────────────
# Порядок цветов в палитре:
#   фон, карточка, наведение, наведение-2, текст, приглушённый текст,
#   акцент, акцент-наведение, зелёный, зелёный-наведение, жёлтый, красный, красный-наведение,
#   текст на акцентных кнопках, недоступный элемент, ползунок выкл., дорожка выкл.,
#   рамка флажка, выделение в таблице, отмеченная строка, пункт меню, разделитель строк,
#   и 4 доп. цвета диаграммы (розовый, бирюзовый, фиолетовый, оранжевый).
_PALETTE_KEYS = ("bg", "card", "card_hover", "card_hover2", "text", "muted",
                 "accent", "accent_hover", "green", "green_hover", "amber", "red", "red_hover",
                 "on_accent", "disabled", "knob_off", "track_off",
                 "check_outline", "selected", "row_checked", "menu_on", "separator",
                 "pink", "cyan", "violet", "orange")


def _palette(title, dark, *colors):
    assert len(colors) == len(_PALETTE_KEYS)
    return dict(zip(_PALETTE_KEYS, colors), title=title, dark=dark)


THEMES = {
    "classic": _palette(
        "Стандартная", True,
        "#12141c", "#1c1f2b", "#2a2f42", "#383e57", "#e8eaf2", "#8b90a5",
        "#6c8cff", "#8aa3ff", "#4ade80", "#6ee7a0", "#fbbf24", "#f87171", "#fca5a5",
        "#0b0d14", "#2a2e3f", "#555a70", "#3a3f55",
        "#4a5070", "#2f3650", "#26304f", "#232a44", "#232738",
        "#f472b6", "#22d3ee", "#a78bfa", "#fb923c"),
    "graphene": _palette(
        "В стиле GrapheneOS", True,
        "#171717", "#212121", "#2e2e2e", "#3c3c3c", "#ececec", "#a0a0a0",
        "#7cacf8", "#a3c4fa", "#81c995", "#a8dab5", "#fdd663", "#f28b82", "#f6aea9",
        "#0f0f0f", "#2b2b2b", "#6b6b6b", "#3d3d3d",
        "#5c5c5c", "#2c3a4f", "#243246", "#263345", "#2a2a2a",
        "#ff8bcb", "#78d9ec", "#c58af9", "#fcad70"),
    "nord": _palette(
        "Nord", True,
        "#242933", "#2e3440", "#3b4252", "#434c5e", "#eceff4", "#8f99ad",
        "#88c0d0", "#a3d3e0", "#a3be8c", "#b8d0a4", "#ebcb8b", "#bf616a", "#d08a91",
        "#1d222b", "#353b48", "#616e88", "#434c5e",
        "#4c566a", "#3b4a5c", "#334050", "#354152", "#363d4a",
        "#b48ead", "#8fbcbb", "#81a1c1", "#d08770"),
    "light": _palette(
        "Светлая", False,
        "#eef0f5", "#ffffff", "#e6e9f2", "#d7dbe8", "#1c2030", "#6a7086",
        "#4c6ef5", "#6b86f7", "#22a55a", "#3cbf73", "#d98a06", "#e5484d", "#f07a7e",
        "#ffffff", "#e3e6ee", "#ffffff", "#c9cfdd",
        "#aab1c4", "#dfe6ff", "#e4eaff", "#e8edff", "#eceef4",
        "#e2479b", "#0ea5c6", "#8b5cf6", "#f97316"),
    "amber": _palette(
        "Графит и янтарь", True,
        "#141312", "#1f1d1b", "#2c2926", "#3a3632", "#f2ede6", "#a39a8f",
        "#ff9f43", "#ffb76b", "#7bd88f", "#9be3a9", "#ffd166", "#ff6b6b", "#ff9b9b",
        "#1a1209", "#2a2724", "#6f675e", "#3f3a35",
        "#5a534b", "#3a2f22", "#33291d", "#352a1e", "#2a2724",
        "#ff7eb6", "#5ccfe6", "#c3a6ff", "#f4a261"),
}


def _saved_theme():
    """Тема из настроек. Читается до всего остального: цвета нужны уже при загрузке модуля."""
    try:
        path = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                            "PCCleaner", "state.json")
        with open(path, "r", encoding="utf-8") as f:
            name = json.load(f).get("theme")
        return name if name in THEMES else "classic"
    except Exception:
        return "classic"


def apply_theme(name):
    """Делает тему текущей: переписывает глобальные цвета. Уже созданные виджеты не
    меняются — после смены темы интерфейс перестраивается (CleanerApp.rebuild_ui)."""
    global THEME, THEME_DARK, BG, CARD, CARD_HOVER, CARD_HOVER2, TEXT, MUTED, ACCENT, \
        ACCENT_HOVER, GREEN, GREEN_HOVER, AMBER, RED, RED_HOVER, DARK, DISABLED, KNOB_OFF, \
        TRACK_OFF, CHECK_OUTLINE, SELECTED, ROW_CHECKED, MENU_ON, SEPARATOR, CHART_COLORS, \
        COLORS, BORDER_ACTIVE, BORDER_INACTIVE
    THEME = name if name in THEMES else "classic"
    p = THEMES[THEME]
    THEME_DARK = p["dark"]          # тёмный заголовок окна Windows
    BG, CARD, CARD_HOVER, CARD_HOVER2 = p["bg"], p["card"], p["card_hover"], p["card_hover2"]
    TEXT, MUTED, ACCENT, ACCENT_HOVER = p["text"], p["muted"], p["accent"], p["accent_hover"]
    GREEN, GREEN_HOVER, AMBER = p["green"], p["green_hover"], p["amber"]
    RED, RED_HOVER = p["red"], p["red_hover"]
    DARK = p["on_accent"]           # текст на акцентных (цветных) кнопках
    DISABLED, KNOB_OFF, TRACK_OFF = p["disabled"], p["knob_off"], p["track_off"]
    CHECK_OUTLINE, SELECTED, ROW_CHECKED = p["check_outline"], p["selected"], p["row_checked"]
    MENU_ON, SEPARATOR = p["menu_on"], p["separator"]
    CHART_COLORS = [ACCENT, GREEN, AMBER, p["pink"], p["cyan"], p["violet"], p["orange"], RED]
    BORDER_ACTIVE, BORDER_INACTIVE = ACCENT, CARD_HOVER  # рамка активного/неактивного окна
    if "CATEGORIES" in globals():
        COLORS = dict(zip(CATEGORIES, CHART_COLORS))


apply_theme(_saved_theme())
FONT = "Segoe UI"
FONT_SEMI = "Segoe UI Semibold"  # уточняется при запуске, если шрифта нет

UI_SCALE = 1.0


def S(n):
    """Масштабирование пикселей под DPI экрана (чёткость на 4K и ноутбуках)."""
    return int(round(n * UI_SCALE))


def enable_hidpi():
    """Включаем поддержку высокого DPI — текст перестаёт быть размытым."""
    if not IS_WIN:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# ───────────────────────── Вспомогательные функции ─────────────────────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def blend(c1, c2, t):
    """Смешивает два цвета (t от 0 до 1)."""
    t = max(0.0, min(1.0, t))
    a, b = hex_to_rgb(c1), hex_to_rgb(c2)
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def approach(cur, target, dt, rate=12.0, eps=0.5):
    """Плавное приближение значения к цели (не зависит от частоты кадров)."""
    if abs(target - cur) <= eps:
        return target
    return cur + (target - cur) * (1.0 - math.exp(-rate * max(dt, 0.001)))


def load_color(p):
    """Цвет индикатора: зелёный → жёлтый → красный."""
    if p < 60:
        return blend(GREEN, AMBER, p / 60)
    return blend(AMBER, RED, (p - 60) / 40)


def fmt_size(n: float) -> str:
    for unit in (T("Б"), T("КБ"), T("МБ"), T("ГБ"), T("ТБ")):
        if n < 1024 or unit == T("ТБ"):
            return f"{n:.0f} {unit}" if unit == T("Б") else f"{n:.1f} {unit}"
        n /= 1024


def fmt_gb(n):
    return T('{0:.1f} ГБ').format(n / 1024 ** 3)


_CTRL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]+")


def clean_text(s):
    """Приводит строку к безопасному для вывода виду: без управляющих символов,
    лишних пробелов и символов вне BMP (их Tk может не отобразить)."""
    s = _CTRL_CHARS.sub(" ", str(s))
    s = "".join(ch for ch in s if ord(ch) <= 0xFFFF)
    return re.sub(r"\s{2,}", " ", s).strip()


# ───────────────────────── Настройки и белый список ─────────────────────────
STATE_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "PCCleaner")
STATE_FILE = os.path.join(STATE_DIR, "state.json")


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    """Атомарная запись: сначала во временный файл, потом замена."""
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STATE_FILE)
    except OSError:
        pass


# ───────────────────────── Язык интерфейса (русский / English) ─────────────────────────
def detect_lang():
    """Язык из настроек; при первом запуске — по языку Windows (ru/uk/be → русский)."""
    lang = load_state().get("lang")
    if lang in ("ru", "en"):
        return lang
    try:
        lid = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
        return "ru" if lid in (0x19, 0x22, 0x23) else "en"
    except Exception:
        return "ru"


LANG = detect_lang()


def apply_language(lang):
    """Делает язык текущим. Тексты берутся через T() при создании виджетов, поэтому после
    смены языка интерфейс перестраивается (CleanerApp.rebuild_ui)."""
    global LANG
    LANG = lang if lang in ("ru", "en") else "ru"


LANGUAGES = (("ru", "Русский"), ("en", "English"))  # названия — на своём языке, не переводятся


def T(text):
    """Перевод строки интерфейса. Ключ — русский текст; нет перевода — русский как есть."""
    return EN.get(text, text) if LANG == "en" else text


EN = {
    '{0:.1f} ГБ':
        '{0:.1f} GB',
    'Б':
        'B',
    'КБ':
        'KB',
    'МБ':
        'MB',
    'ГБ':
        'GB',
    'ТБ':
        'TB',
    'Временные файлы пользователя':
        'User temporary files',
    'Папка %TEMP% — мусор от программ и установщиков':
        '%TEMP% folder — leftovers from programs and installers',
    'Временные файлы Windows':
        'Windows temporary files',
    'Кэш ускорения запуска программ (Windows пересоздаст его)':
        'Program launch acceleration cache (Windows will rebuild it)',
    'Кэш миниатюр и значков':
        'Thumbnail and icon cache',
    'thumbcache / iconcache проводника':
        'Explorer thumbcache / iconcache',
    'Дампы сбоев':
        'Crash dumps',
    'Файлы отчётов об ошибках приложений':
        'Application error report files',
    'Кэш Google Chrome':
        'Google Chrome cache',
    'Закройте браузер перед очисткой':
        'Close the browser before cleaning',
    'Кэш Microsoft Edge':
        'Microsoft Edge cache',
    'Корзина':
        'Recycle Bin',
    'Удалённые файлы будут стёрты безвозвратно':
        'Deleted files will be erased permanently',
    '✔ Анимации окон отключены':
        '✔ Window animations disabled',
    'Часть визуальных эффектов применится после перезахода в Windows.':
        'Some visual effects will apply after you sign in to Windows again.',
    'Приложение Microsoft Store':
        'Microsoft Store app',
    'Собираю список файлов…':
        'Collecting the file list…',
    'Найдено: {0}':
        'Found: {0}',
    '   •   Отмечено: {0} ({1})':
        '   •   Selected: {0} ({1})',
    'Удалить отмеченные файлы: {0} шт. (≈ {1})?\n\nЭто действие необратимо — файлы не попадут в корзину.':
        'Delete the selected files: {0} (≈ {1})?\n\nThis cannot be undone — the files will not go to the Recycle Bin.',
    'Удалить выбранные файлы (≈ {0})?\n\n':
        'Delete the selected files (≈ {0})?\n\n',
    'Файлы, которые сейчас используются, будут пропущены.':
        'Files that are currently in use will be skipped.',
    'Освободить память пользовательских программ?\n\nКритические процессы Windows, службы, антивирус и античиты затронуты не будут.':
        'Free up memory used by user programs?\n\nCritical Windows processes, services, antivirus and anti-cheat software will not be affected.',
    'Программ: {0}   •   Отмечено: {1}':
        'Programs: {0}   •   Selected: {1}',
    'Выбрано: {0} из {1}':
        'Selected: {0} of {1}',
    'Готово: {0}  •  файлов: {1}  •  {2} → {3}  •  {4:.1f} с':
        'Done: {0}  •  files: {1}  •  {2} → {3}  •  {4:.1f} s',
    'Нужно разрешение':
        'Permission required',
    'занят':
        'in use',
    '✖ Схема максимальной производительности недоступна на этом ПК':
        '✖ The Ultimate Performance power plan is not available on this PC',
    '✔ Игровой режим Windows включён, фоновая запись игр отключена, прозрачность и эффекты переведены в режим производительности':
        '✔ Windows Game Mode enabled, background game recording disabled, transparency and effects set for performance',
    '✔ Отключено энергосбережение процессов (Power Throttling)':
        '✔ Process power saving disabled (Power Throttling)',
    '✔ Схема питания, реестр и анимации возвращены как было.':
        '✔ Power plan, registry and animations restored.',
    'Настройки PCCleaner':
        'PCCleaner settings',
    'PowerShell: профиль':
        'PowerShell: profile',
    'PowerShell 7: профиль':
        'PowerShell 7: profile',
    'VS Code: настройки':
        'VS Code: settings',
    'Windows Terminal: настройки':
        'Windows Terminal: settings',
    'Файл hosts':
        'hosts file',
    'н/д':
        'n/a',
    'Белый список':
        'Whitelist',
    'Особые файлы — выбор для удаления':
        'Special files — choose what to delete',
    ' (показаны первые {0})':
        ' (showing the first {0})',
    '\n\nПри отказе в доступе для файла будет изменён владелец и выданы права администраторам.':
        '\n\nIf access is denied, the file owner will be changed and administrators will be granted access.',
    'Файлов к удалению':
        'Files to delete',
    'Выбрано категорий':
        'Categories selected',
    'Больше всего места занимает':
        'Takes up the most space',
    'Очистить':
        'Clean',
    'Сканировать':
        'Scan',
    '📂  Особые файлы':
        '📂  Special files',
    'Удалять скрытые и системные файлы':
        'Delete hidden and system files',
    'Файлы с атрибутами «скрытый» и «системный» внутри выбранных папок':
        'Files with the “hidden” and “system” attributes inside the selected folders',
    'Принудительное удаление защищённых файлов':
        'Force-delete protected files',
    '\n• Исключены белым списком: {0}.':
        '\n• Excluded by the whitelist: {0}.',
    '\n• Будут удалены скрытые и системные файлы в выбранных папках.':
        '\n• Hidden and system files in the selected folders will be deleted.',
    '\n• Для защищённых файлов будет изменён владелец и выданы права администраторам.':
        '\n• For protected files, the owner will be changed and administrators will be granted access.',
    'НАГРУЗКА НА СИСТЕМУ':
        'SYSTEM LOAD',
    'Процессор':
        'Processor',
    'Видеокарта':
        'Graphics card',
    'Память':
        'Memory',
    'ОЧИСТКА ОПЕРАТИВНОЙ ПАМЯТИ':
        'RAM CLEANUP',
    '🧠  Очистить память':
        '🧠  Free up memory',
    'ИГРОВОЙ РЕЖИМ':
        'GAME MODE',
    '\n\nДополнительно будет сброшен кэш памяти Windows.':
        '\n\nThe Windows memory cache will also be flushed.',
    'Удалить выбранные':
        'Uninstall selected',
    'Тихое удаление, если поддерживается':
        'Silent uninstall, if supported',
    'Без окон деинсталлятора. Строки с замком 🔒 — защищённые компоненты, их удалить нельзя':
        'No uninstaller windows. Rows with a lock 🔒 are protected components and cannot be removed',
    '\n… и ещё {0}':
        '\n… and {0} more',
    '💾  Создать бэкап':
        '💾  Create backup',
    '📂  Открыть папку':
        '📂  Open folder',
    'Папка бэкапов':
        'Backup folder',
    'Имя архива':
        'Archive name',
    'Пропускать кэш и служебные папки':
        'Skip cache and service folders',
    'Cache, node_modules, __pycache__, .venv, logs и т. п. — бэкап быстрее и меньше':
        'Cache, node_modules, __pycache__, .venv, logs, etc. — faster and smaller backup',
    'Сильное сжатие':
        'Strong compression',
    'Архив меньше, но создаётся в несколько раз дольше':
        'Smaller archive, but takes several times longer to create',
    '   •   {0}{1}, файлов: {2}':
        '   •   {0}{1}, files: {2}',
    '  •  пропущено: {0}':
        '  •  skipped: {0}',
    'PCCleaner — чёткая графика':
        'PCCleaner — crisp graphics',
    'Для ровной сглаженной графики нужен модуль Pillow, но он не установлен в этом окружении Python. Без него края диаграмм и кнопок получаются рваными.\n\nУстановить сейчас? (pip install pillow, нужен интернет, около 10–30 секунд)\n\nДа — установить и перезапустить\nНет — не предлагать больше\nОтмена — спросить в следующий раз':
        "Smooth, anti-aliased graphics require the Pillow module, but it is not installed in this Python environment. Without it, the edges of charts and buttons look jagged.\n\nInstall it now? (pip install pillow, requires internet, about 10–30 seconds)\n\nYes — install and restart\nNo — don't ask again\nCancel — ask next time",
    'Установка Pillow':
        'Installing Pillow',
    'Скрытый':
        'Hidden',
    'Системный':
        'System',
    'Только чтение':
        'Read-only',
    'Игровой режим доступен только в Windows.':
        'Game mode is available only on Windows.',
    'Игровой режим уже включён.':
        'Game mode is already on.',
    '✔ Схема питания: максимальная производительность':
        '✔ Power plan: Ultimate Performance',
    '✖ Не удалось переключить схему питания':
        '✖ Could not switch the power plan',
    '• Power Throttling не изменён — нужны права администратора':
        '• Power Throttling unchanged — administrator rights required',
    'Игровой режим не был включён.':
        'Game mode was not on.',
    '+ Файлы':
        '+ Files',
    '+ Папка':
        '+ Folder',
    'Файлы для белого списка':
        'Files for the whitelist',
    'Папка для белого списка':
        'Folder for the whitelist',
    'Такого пути не существует.':
        'This path does not exist.',
    'Отметьте строки в списке.':
        'Check rows in the list.',
    'Выбрать всё':
        'Select all',
    'Снять выбор':
        'Clear selection',
    '+ Добавить папку':
        '+ Add folder',
    'Обновить':
        'Refresh',
    'Поиск…   ':
        'Searching…   ',
    'Папка для поиска особых файлов':
        'Folder to search for special files',
    'Папка защищена':
        'Protected folder',
    'Эта папка относится к Windows, Program Files или загрузчику.\nУдаление файлов в ней может сломать систему, поэтому она недоступна.':
        'This folder belongs to Windows, Program Files or the boot loader.\nDeleting files in it can break the system, so it is not available.',
    'Особые файлы':
        'Special files',
    'Ничего не отмечено.':
        'Nothing is checked.',
    'Подтверждение':
        'Confirmation',
    'Удаление…':
        'Deleting…',
    'Готов к работе':
        'Ready',
    'Получение доступа через права администратора (takeown / icacls)':
        'Gaining access with administrator rights (takeown / icacls)',
    'Требуется запуск от администратора':
        'Requires running as administrator',
    '{0} из {1}':
        '{0} of {1}',
    'к очистке':
        'to clean',
    'Сканирование…':
        'Scanning…',
    'Ничего не выбрано.':
        'Nothing is selected.',
    'Очистка…':
        'Cleaning…',
    'нет данных':
        'no data',
    'Очистка памяти':
        'Memory cleanup',
    'Выполняю…':
        'Working…',
    'Игровой режим':
        'Game mode',
    'Доступно только в Windows.':
        'Available only on Windows.',
    'По имени':
        'By name',
    'По размеру':
        'By size',
    'Загрузка…   ':
        'Loading…   ',
    'Программы':
        'Programs',
    'Удаление программ':
        'Uninstall programs',
    'Будут запущены программы удаления ({0} шт.):\n\n{1}\n\nЭто необратимо. Продолжить?':
        'Uninstallers will be launched for {0} program(s):\n\n{1}\n\nThis cannot be undone. Continue?',
    '+ Типовые конфиги':
        '+ Standard configs',
    'Отметьте, что сохранить, и нажмите «Создать бэкап»':
        'Check what to save and click “Create backup”',
    'Бэкап':
        'Backup',
    'Все найденные типовые конфиги уже в списке.':
        'All standard configs found are already in the list.',
    'Отметьте строки, которые нужно убрать из списка.':
        'Check the rows you want to remove from the list.',
    'Убрать из списка отмеченные пункты ({0})?\n\nСами файлы на диске не удаляются.':
        'Remove the checked items from the list ({0})?\n\nThe files themselves are not deleted from disk.',
    'Куда сохранять бэкапы':
        'Where to save backups',
    'Отметьте в списке хотя бы один существующий файл или папку.':
        'Check at least one existing file or folder in the list.',
    'Укажите полный путь к папке для бэкапов, например D:\\Backups.':
        'Enter the full path to the backup folder, for example D:\\Backups.',
    'Введите имя архива.':
        'Enter an archive name.',
    'Файл «{0}» уже есть в этой папке.\n\nДа — заменить\nНет — сохранить под новым именем\nОтмена — ничего не делать':
        'The file “{0}” already exists in this folder.\n\nYes — replace it\nNo — save under a new name\nCancel — do nothing',
    '✖  Отменить':
        '✖  Cancel',
    'Подготовка…':
        'Preparing…',
    'Не удалось создать архив:\n\n{0}':
        'Could not create the archive:\n\n{0}',
    'Не удалось установить Pillow автоматически.\nУстановите вручную: откройте терминал PyCharm и выполните\n\n    pip install pillow\n\n':
        'Could not install Pillow automatically.\nInstall it manually: open the PyCharm terminal and run\n\n    pip install pillow\n\n',
    'Архивирую: {0}':
        'Archiving: {0}',
    'Убрать отмеченные':
        'Remove checked',
    'Добавить':
        'Add',
    '🛡 В белый список':
        '🛡 To whitelist',
    'Сейчас создаётся бэкап. Прервать его и выйти?\n\nНезаконченный архив будет удалён.':
        'A backup is being created. Stop it and exit?\n\nThe unfinished archive will be deleted.',
    '🧹  Очистка':
        '🧹  Cleanup',
    '⚡  Производительность':
        '⚡  Performance',
    '📦  Программы':
        '📦  Programs',
    '💾  Бэкап':
        '💾  Backup',
    '  •  нужны права администратора':
        '  •  administrator rights required',
    '🛡  Белый список':
        '🛡  Whitelist',
    'Очищаю: {0}…':
        'Cleaning: {0}…',
    'Не удалось запросить права:\n{0}':
        'Could not request rights:\n{0}',
    '🎮  Игровой режим: ВКЛ':
        '🎮  Game mode: ON',
    '🎮  Игровой режим: ВЫКЛ':
        '🎮  Game mode: OFF',
    'Будут применены настройки для максимальной производительности:\n\n• схема питания «Максимальная производительность»;\n• Игровой режим Windows включён, фоновая запись игр отключена;\n• прозрачность, анимации и визуальные эффекты отключены;\n• отключено энергосбережение процессов (нужны права администратора).\n\nПовторное нажатие кнопки вернёт все настройки как были. Включить?':
        'Maximum performance settings will be applied:\n\n• “Ultimate Performance” power plan;\n• Windows Game Mode on, background game recording off;\n• transparency, animations and visual effects off;\n• process power saving off (requires administrator rights).\n\nClicking the button again restores all settings. Turn on?',
    'Применяю настройки…':
        'Applying settings…',
    'Возвращаю прежние настройки…':
        'Restoring previous settings…',
    'Поиск программы…':
        'Search programs…',
    'Удаляю ({0}/{1}): {2}…':
        'Uninstalling ({0}/{1}): {2}…',
    'Обзор':
        'Browse',
    'По умолчанию':
        'Default',
    'Нельзя добавить папку с бэкапами саму в себя:\n':
        'You cannot add the backup folder to itself:\n',
    'Папка для бэкапа':
        'Folder to back up',
    'Будет создан: {0}    •    в имени можно использовать {{date}}, {{time}}, {{pc}}':
        'Will be created: {0}    •    you can use {{date}}, {{time}}, {{pc}} in the name',
    'Введите имя архива':
        'Enter an archive name',
    'Не удалось открыть папку:\n{0}':
        'Could not open the folder:\n{0}',
    'Отменяю…':
        'Cancelling…',
    'Не удалось создать папку:\n{0}\n\n{1}':
        'Could not create the folder:\n{0}\n\n{1}',
    'Папка бэкапов находится внутри временных файлов, которые удаляет вкладка «Очистка».\nБэкапы могут быть стёрты при очистке. Всё равно сохранить сюда?':
        'The backup folder is inside the temporary files that the “Cleanup” tab deletes.\nBackups may be erased during cleanup. Save here anyway?',
    'Бэкап отменён — незаконченный архив удалён':
        'Backup cancelled — the unfinished archive was deleted',
    'Ошибка: {0}':
        'Error: {0}',
    '… и ещё {0}':
        '… and {0} more',
    'Архив создан, но часть файлов и папок ({0}) прочитать не удалось — они заняты другой программой или нет доступа:\n\n':
        'The archive was created, but some files and folders ({0}) could not be read — they are in use by another program or access is denied:\n\n',
    'Pillow установлен. Запустите программу снова.':
        'Pillow is installed. Start the program again.',
    'Файлы и папки из этого списка исключаются из сканирования и очистки. Папка защищает всё содержимое. Скрытые файлы можно добавить, вставив путь в поле ниже или отметив их в окне «Особые файлы».':
        'Files and folders in this list are excluded from scanning and cleanup. A folder protects all of its contents. Hidden files can be added by pasting the path into the field below or by checking them in the “Special files” window.',
    'Путь:':
        'Path:',
    'Папка':
        'Folder',
    'Файл':
        'File',
    'Скрытые, системные, «только чтение» и защищённые файлы в папках очистки. Нажмите на строку, чтобы отметить файл; заголовок столбца сортирует список. Файлы Windows, Program Files и загрузчика сюда не попадают.':
        'Hidden, system, read-only and protected files in the cleanup folders. Click a row to check a file; a column header sorts the list. Files of Windows, Program Files and the boot loader are not listed.',
    'Получать разрешение системы при отказе в доступе':
        'Request system permission when access is denied',
    '🛡  Права администратора':
        '🛡  Administrator rights',
    'ОБЩАЯ СТАТИСТИКА':
        'OVERALL STATISTICS',
    'Освобождает неиспользуемую память пользовательских программ (рабочие наборы). Не затрагиваются: процессы и службы Windows, оболочка Explorer, антивирус, античиты, процессы других сессий и сама программа.':
        'Frees unused memory of user programs (working sets). Not affected: Windows processes and services, the Explorer shell, antivirus, anti-cheat, processes of other sessions and this program itself.',
    'Глубокая очистка: сбросить кэш памяти Windows':
        'Deep cleanup: flush the Windows memory cache',
    'Схема питания «Максимальная производительность», Game Mode Windows, отключение фоновой записи игр, прозрачности и анимаций. Повторное нажатие возвращает все настройки.':
        '“Ultimate Performance” power plan, Windows Game Mode, background game recording, transparency and animations turned off. Clicking again restores all settings.',
    'Установленные программы, игры и приложения':
        'Installed programs, games and apps',
    'Сортировка:':
        'Sort:',
    'Резервная копия файлов и настроек':
        'Backup of files and settings',
    'не найден':
        'not found',
    'На диске свободно {0}, а выбрано {1}.\nАрхив может не поместиться. Продолжить?':
        'Free disk space: {0}, selected: {1}.\nThe archive may not fit. Continue?',
    'Сканирование завершено':
        'Scan complete',
    'Устанавливаю Pillow…\nПодождите, окно закроется само.':
        'Installing Pillow…\nPlease wait, this window will close by itself.',
    'Изменяется владелец файла и выдаются права администраторам':
        'Changes the file owner and grants access to administrators',
    'Удалено файлов: {0}, освобождено {1}.':
        'Files deleted: {0}, freed {1}.',
    '✔ Запущено от администратора':
        '✔ Running as administrator',
    '📁  Файловый менеджер':
        '📁  File manager',
    'О приложении':
        'About',
    'Тема оформления':
        'Theme',
    'Стандартная':
        'Classic',
    'В стиле GrapheneOS':
        'GrapheneOS style',
    'Светлая':
        'Light',
    'Графит и янтарь':
        'Graphite & Amber',
    'Версия {0}':
        'Version {0}',
    'Бесплатная программа для Windows, которая помогает держать компьютер в порядке: освобождает место на диске, ускоряет систему, удаляет ненужные программы и сохраняет важные файлы и настройки в резервную копию.':
        'A free Windows app that helps keep your PC in order: frees up disk space, speeds up the system, removes unneeded programs and backs up important files and settings.',
    'ВОЗМОЖНОСТИ':
        'FEATURES',
    '🧹  Очистка — временные файлы, кэш браузеров, корзина, особые файлы и белый список':
        '🧹  Cleanup — temporary files, browser cache, Recycle Bin, special files and a whitelist',
    '⚡  Производительность — нагрузка CPU, GPU и RAM, очистка памяти и игровой режим':
        '⚡  Performance — CPU, GPU and RAM load, memory cleanup and game mode',
    '📦  Программы — удаление программ, игр и приложений Microsoft Store':
        '📦  Programs — uninstall programs, games and Microsoft Store apps',
    '💾  Бэкап — архив .zip с файлами и настройками в один клик':
        '💾  Backup — a .zip archive of files and settings in one click',
    'ОБРАТНАЯ СВЯЗЬ':
        'FEEDBACK',
    'Нашли ошибку или есть идея, как сделать программу лучше? Напишите мне — буду рад любому отзыву.':
        'Found a bug or have an idea how to make the app better? Write to me — any feedback is welcome.',
    '📋  Скопировать данные о системе':
        '📋  Copy system info',
    'Скопировано — вставьте в сообщение об ошибке':
        'Copied — paste it into your bug report',
    'Не удалось открыть ссылку:\n{0}':
        'Could not open the link:\n{0}',
    '🛡  Выйти из режима администратора':
        '🛡  Leave administrator mode',
    'Режим администратора':
        'Administrator mode',
    'Программа перезапустится с обычными правами (без администратора). Продолжить?':
        'The program will restart with standard rights (without administrator). Continue?',
    'Сейчас выполняется операция (сканирование, очистка, удаление программ или бэкап).\nДождитесь её окончания.':
        'An operation is in progress (scan, cleanup, uninstall or backup).\nWait for it to finish.',
    'Перезапускаю с обычными правами…':
        'Restarting with standard rights…',
    'Не удалось запустить программу с обычными правами:\n{0}':
        'Could not start the program with standard rights:\n{0}',
    'Новая копия программы не запустилась, поэтому это окно остаётся открытым.\n\nЗапустите программу заново обычным способом (без «Запуск от имени администратора»).':
        'The new copy of the program did not start, so this window stays open.\n\nStart the program again the usual way (without “Run as administrator”).',
    'Стандартные права — часть функций ограничена':
        'Standard rights — some features are limited',
    'Список ожидания; программы могут ненадолго открываться медленнее':
        'Standby list; programs may open a little slower for a short while',
    'Файлы для бэкапа':
        'Files to back up',
    'Готово! Освобождено {0}':
        'Done! Freed {0}',
    '\nНе удалось удалить: {0} (заняты или нет доступа).':
        '\nCould not delete: {0} (in use or access denied).',
    '  (пропущено файлов: {0} — заняты, защищены или в белом списке)':
        '  (files skipped: {0} — in use, protected or whitelisted)',
    'Освобождено ≈ {0}  •  обработано процессов: {1}  •  защищено: {2}':
        'Freed ≈ {0}  •  processes trimmed: {1}  •  protected: {2}',
    '  •  кэш Windows сброшен':
        '  •  Windows cache flushed',
    '  •  кэш Windows сбросить не удалось':
        '  •  could not flush the Windows cache',
    'Не удалось изменить игровой режим':
        'Could not change game mode',
    'Игровой режим включён':
        'Game mode is on',
    'Игровой режим выключен':
        'Game mode is off',
    'Программа':
        'Program',
    'Папка • {0}':
        'Folder • {0}',
    '\n\n✖ — программа не удалена: отмена, ошибка или нужно подтверждение в самой программе (например, в Steam).':
        '\n\n✖ — the program was not removed: cancelled, error, or confirmation is required in the program itself (for example, in Steam).',
    'Удалено: {0} из {1}\n\n':
        'Uninstalled: {0} of {1}\n\n',
    'Язык':
        'Language',
}


_WL_EXACT = frozenset()
_WL_PREFIX = ()


def _apply_whitelist(paths):
    global _WL_EXACT, _WL_PREFIX
    norm = [os.path.normcase(os.path.abspath(p)) for p in paths]
    _WL_EXACT = frozenset(norm)
    _WL_PREFIX = tuple(x.rstrip("\\/") + os.sep for x in norm)


def get_whitelist():
    return list(load_state().get("whitelist", []))


def set_whitelist(paths):
    paths = list(dict.fromkeys(os.path.normpath(p) for p in paths))
    st = load_state()
    st["whitelist"] = paths
    save_state(st)
    _apply_whitelist(paths)


def is_whitelisted(path):
    """True — файл или папка в белом списке (или лежит внутри папки из списка)."""
    if not _WL_EXACT:
        return False
    k = os.path.normcase(path)
    return k in _WL_EXACT or k.startswith(_WL_PREFIX)


_apply_whitelist(get_whitelist())


# ───────────────────────── Что чистим ─────────────────────────
LOCAL = os.environ.get("LOCALAPPDATA", "")
WIN = os.environ.get("SystemRoot", r"C:\Windows")


def _p(*parts):
    return os.path.join(*parts)


# Названия и описания — по-русски; перевод через T() при показе (язык меняется на лету).
CATEGORIES = {
    "user_temp": {
        "title": "Временные файлы пользователя",
        "desc": "Папка %TEMP% — мусор от программ и установщиков",
        "paths": [tempfile.gettempdir()],
    },
    "win_temp": {
        "title": "Временные файлы Windows",
        "desc": r"C:\Windows\Temp",
        "paths": [_p(WIN, "Temp")],
        "admin": True,
    },
    "prefetch": {
        "title": "Prefetch",
        "desc": "Кэш ускорения запуска программ (Windows пересоздаст его)",
        "paths": [_p(WIN, "Prefetch")],
        "admin": True,
    },
    "thumbs": {
        "title": "Кэш миниатюр и значков",
        "desc": "thumbcache / iconcache проводника",
        "paths": [_p(LOCAL, "Microsoft", "Windows", "Explorer")],
        "match": lambda n: n.lower().startswith(("thumbcache", "iconcache")),
        "hidden_ok": True,
    },
    "crash": {
        "title": "Дампы сбоев",
        "desc": "Файлы отчётов об ошибках приложений",
        "paths": [_p(LOCAL, "CrashDumps")],
    },
    "chrome": {
        "title": "Кэш Google Chrome",
        "desc": "Закройте браузер перед очисткой",
        "paths": [
            _p(LOCAL, "Google", "Chrome", "User Data", "Default", "Cache"),
            _p(LOCAL, "Google", "Chrome", "User Data", "Default", "Code Cache"),
        ],
    },
    "edge": {
        "title": "Кэш Microsoft Edge",
        "desc": "Закройте браузер перед очисткой",
        "paths": [
            _p(LOCAL, "Microsoft", "Edge", "User Data", "Default", "Cache"),
            _p(LOCAL, "Microsoft", "Edge", "User Data", "Default", "Code Cache"),
        ],
    },
    "recycle": {
        "title": "Корзина",
        "desc": "Удалённые файлы будут стёрты безвозвратно",
        "paths": [],
        "special": "recycle",
    },
}
COLORS = dict(zip(CATEGORIES, CHART_COLORS))


# ───────────────────────── Права и атрибуты файлов ─────────────────────────
ATTR_READONLY = 0x1
ATTR_HIDDEN = 0x2
ATTR_SYSTEM = 0x4
ATTR_NORMAL = 0x80
ATTR_REPARSE = 0x400  # ссылки и junction — внутрь не заходим
INVALID_HANDLE = ctypes.c_void_p(-1).value

if IS_WIN:
    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _H, _D, _B = wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL
    _k32.GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
    _k32.GetFileAttributesW.restype = _D
    _k32.SetFileAttributesW.argtypes = [wintypes.LPCWSTR, _D]
    _k32.SetFileAttributesW.restype = _B
    _k32.CreateFileW.argtypes = [wintypes.LPCWSTR, _D, _D, ctypes.c_void_p, _D, _D, _H]
    _k32.CreateFileW.restype = _H
    _k32.CloseHandle.argtypes = [_H]
    _k32.OpenProcess.argtypes = [_D, _B, _D]
    _k32.OpenProcess.restype = _H
    _k32.GetCurrentProcess.restype = _H
    _k32.QueryFullProcessImageNameW.argtypes = [_H, _D, wintypes.LPWSTR,
                                                ctypes.POINTER(_D)]
    _k32.ProcessIdToSessionId.argtypes = [_D, ctypes.POINTER(_D)]
    _k32.CreateToolhelp32Snapshot.argtypes = [_D, _D]
    _k32.CreateToolhelp32Snapshot.restype = _H
    _k32.Process32FirstW.argtypes = [_H, ctypes.c_void_p]
    _k32.Process32FirstW.restype = _B
    _k32.Process32NextW.argtypes = [_H, ctypes.c_void_p]
    _k32.Process32NextW.restype = _B
    _k32.GlobalMemoryStatusEx.argtypes = [ctypes.c_void_p]
    _k32.GlobalMemoryStatusEx.restype = _B
    _k32.GetSystemTimes.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    _k32.GetSystemTimes.restype = _B
    _k32.WaitForSingleObject.argtypes = [_H, _D]
    _k32.WaitForSingleObject.restype = _D
    _psapi = ctypes.WinDLL("psapi", use_last_error=True)
    _psapi.EmptyWorkingSet.argtypes = [_H]
    _psapi.EmptyWorkingSet.restype = _B


def get_attrs(path):
    if not IS_WIN:
        return None
    a = _k32.GetFileAttributesW(path)
    return None if a == 0xFFFFFFFF else a


def set_attrs_normal(path):
    if IS_WIN:
        try:
            _k32.SetFileAttributesW(path, ATTR_NORMAL)
        except Exception:
            pass


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def sys_dir():
    """Папка System32. 32-битный процесс на 64-битной Windows → Sysnative."""
    root = os.environ.get("SystemRoot", r"C:\Windows")
    if IS_WIN and ctypes.sizeof(ctypes.c_void_p) == 4:
        p = os.path.join(root, "Sysnative")
        if os.path.exists(p):
            return p
    return os.path.join(root, "System32")


def sys_tool(name):
    return os.path.join(sys_dir(), name + ".exe")


def run_hidden(cmd, timeout=25, encoding=None):
    try:
        kw = dict(capture_output=True, text=True, errors="ignore",
                  timeout=timeout, creationflags=NO_WINDOW)
        if encoding:
            kw["encoding"] = encoding
        return subprocess.run(cmd, **kw)
    except Exception:
        return None


def grant_access(path):
    """Берём файл во владение группы «Администраторы» и выдаём полный доступ."""
    run_hidden([sys_tool("takeown"), "/f", path, "/a"])
    run_hidden([sys_tool("icacls"), path, "/grant", "*S-1-5-32-544:F"])


# ───────────────────────── Защита системы ─────────────────────────
WIN = os.environ.get("SystemRoot", r"C:\Windows")


def _norm(p):
    return _np.normcase(_np.abspath(p))


def _under(p, root):
    return p == root or p.startswith(root.rstrip("\\") + "\\")


_PF = os.environ.get("ProgramFiles", r"C:\Program Files")
_PF86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
PROTECTED_ROOTS = [_norm(x) for x in dict.fromkeys([WIN, _PF, _PF86])]
SAFE_SYSTEM_SUBDIRS = [_norm(_np.join(WIN, "Temp")), _norm(_np.join(WIN, "Prefetch"))]
PROTECTED_TOP = {"boot", "efi", "recovery", "system volume information", "$recycle.bin"}
_MEI = getattr(sys, "_MEIPASS", None) if FROZEN else None
_SELF_DIR = _norm(_MEI) if _MEI else None


def is_protected_path(path, is_dir=False):
    """True — путь нельзя трогать: Windows, Program Files, загрузчик, корень диска."""
    p = _norm(path)
    if any(_under(p, ok) for ok in SAFE_SYSTEM_SUBDIRS):
        return False
    if any(_under(p, root) for root in PROTECTED_ROOTS):
        return True
    _drive, tail = _np.splitdrive(p)
    parts = [x for x in tail.split("\\") if x]
    if not parts:
        return True  # корень диска
    if parts[0] in PROTECTED_TOP:
        return True
    if not is_dir and len(parts) == 1:
        return True  # файл прямо в корне диска (pagefile.sys, hiberfil.sys…)
    return False


def is_self_path(path):
    """Распакованные файлы самого .exe (PyInstaller) удалять нельзя — программа сломается."""
    return bool(_SELF_DIR) and _under(_norm(path), _SELF_DIR)


# ───────────────────────── Быстрый обход, сканирование и удаление ─────────────────────────
WORKERS = max(2, min(8, os.cpu_count() or 4))
_BUDGET_LOCK = threading.Lock()


def walk_files(base, include_hidden=False, stop=None):
    """Быстрый обход папки: (путь, размер, атрибуты). Атрибуты берутся из scandir —
    без лишних обращений к диску. Ссылки, junction и белый список пропускаются."""
    if is_whitelisted(base):
        return
    stack = [base]
    while stack:
        if stop and stop():
            return
        cur = stack.pop()
        try:
            it = os.scandir(cur)
        except OSError:
            continue
        with it:
            for e in it:
                try:
                    st = e.stat(follow_symlinks=False)
                    attrs = getattr(st, "st_file_attributes", 0)
                    if attrs & ATTR_REPARSE:
                        continue
                    if not include_hidden and attrs & (ATTR_HIDDEN | ATTR_SYSTEM):
                        continue
                    path = e.path
                    if _WL_EXACT and is_whitelisted(path):
                        continue
                    if e.is_dir(follow_symlinks=False):
                        if _SELF_DIR and is_self_path(path):
                            continue
                        stack.append(path)
                    else:
                        yield path, st.st_size, attrs
                except OSError:
                    continue


def category_files(cat, include_hidden):
    """Файлы категории: (путь, размер)."""
    include = include_hidden or cat.get("hidden_ok", False)
    match = cat.get("match")
    for base in cat["paths"]:
        if not os.path.isdir(base):
            continue
        for path, size, _attrs in walk_files(os.path.abspath(base), include):
            if match and not match(os.path.basename(path)):
                continue
            yield path, size


def scan_category(cat, include_hidden=False):
    """Возвращает (размер, число файлов)."""
    if cat.get("special") == "recycle":
        return recycle_info()
    total = count = 0
    for _path, size in category_files(cat, include_hidden):
        total += size
        count += 1
    return total, count


def remove_file(path, force=False, budget=None):
    """Удаляет файл. Снимает атрибуты, при необходимости берёт доступ."""
    if _WL_EXACT and is_whitelisted(path):
        return False
    err = None
    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        return True
    except OSError as e:
        err = getattr(e, "winerror", None)
    if err in (32, 33):  # файл занят другой программой
        return False

    set_attrs_normal(path)  # снимаем «только чтение / скрытый / системный»
    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        return True
    except OSError as e:
        err = getattr(e, "winerror", None)

    if force and err == 5 and budget is not None:
        with _BUDGET_LOCK:
            allowed = budget["n"] > 0
            if allowed:
                budget["n"] -= 1
        if allowed:
            grant_access(path)  # «отказано в доступе» → нужны разрешения системы
            set_attrs_normal(path)
            try:
                os.remove(path)
                return True
            except OSError:
                pass
    return False


def prune_empty(path):
    """Удаляет пустые вложенные папки (ссылки, junction и белый список не трогаем)."""
    try:
        entries = list(os.scandir(path))
    except OSError:
        return
    for e in entries:
        try:
            if not e.is_dir(follow_symlinks=False):
                continue
            if getattr(e.stat(follow_symlinks=False), "st_file_attributes", 0) & ATTR_REPARSE:
                continue
        except OSError:
            continue
        if is_whitelisted(e.path):
            continue
        prune_empty(e.path)
        try:
            os.rmdir(e.path)
        except OSError:
            pass


def clean_category(cat, include_hidden=False, force=False, budget=None, progress=None):
    """Возвращает (освобождено байт, удалено, пропущено). Удаление идёт параллельно."""
    if cat.get("special") == "recycle":
        size, count = recycle_info()
        recycle_empty()
        return size, count, 0

    files = list(category_files(cat, include_hidden))
    total = len(files)
    freed = removed = skipped = 0

    def work(item):
        return item[1], remove_file(item[0], force, budget)

    if total:
        with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for start in range(0, total, 400):
                batch = files[start:start + 400]
                for size, ok in ex.map(work, batch):
                    if ok:
                        freed += size
                        removed += 1
                    else:
                        skipped += 1
                if progress:
                    progress(min(1.0, (start + len(batch)) / total))

    if not cat.get("match"):
        for base in cat["paths"]:
            if os.path.isdir(base) and not is_whitelisted(base):
                prune_empty(base)
    if progress:
        progress(1.0)
    return freed, removed, skipped


# ───────────────────────── Особые файлы (ручной выбор) ─────────────────────────
def can_delete_status(path):
    """None — файл можно удалить; иначе код ошибки Windows (5 — нет прав, 32 — занят)."""
    if not IS_WIN:
        return None if os.access(path, os.W_OK) else 5
    # открываем с правом DELETE и общим доступом: так проверяются и права, и блокировка
    h = _k32.CreateFileW(path, 0x00010000, 7, None, 3, 0x00200000, None)
    if h is None or h == INVALID_HANDLE:
        return ctypes.get_last_error()
    _k32.CloseHandle(h)
    return None


def special_kinds(path, attrs=None):
    """Список причин, почему файл «особый». Пустой список — обычный файл."""
    a = get_attrs(path) if attrs is None else attrs
    kinds = []
    if a:
        if a & ATTR_HIDDEN:
            kinds.append(T("Скрытый"))
        if a & ATTR_SYSTEM:
            kinds.append(T("Системный"))
        if a & ATTR_READONLY:
            kinds.append(T("Только чтение"))
    err = can_delete_status(path)
    if err == 5 and not (a and a & ATTR_READONLY):
        kinds.append(T("Нужно разрешение"))
    if err in (32, 33) and kinds:
        kinds.append(T("занят"))
    return kinds


def iter_special_files(folders, limit=5000, stop=None):
    """Находит скрытые, системные, read-only и защищённые файлы: (путь, размер, причины)."""
    found = 0
    for base in folders:
        if not os.path.isdir(base) or is_protected_path(base, is_dir=True):
            continue
        for path, size, attrs in walk_files(os.path.abspath(base), True, stop):
            kinds = special_kinds(path, attrs)
            if not kinds:
                continue
            yield path, size, kinds
            found += 1
            if found >= limit:
                return


# ───────────────────────── Корзина ─────────────────────────
class _RBInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("i64Size", ctypes.c_longlong),
        ("i64NumItems", ctypes.c_longlong),
    ]


def recycle_info():
    try:
        info = _RBInfo()
        info.cbSize = ctypes.sizeof(_RBInfo)
        ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
        return info.i64Size, info.i64NumItems
    except Exception:
        return 0, 0


def recycle_empty():
    try:
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x7)
    except Exception:
        pass



# ───────────────────────── Игровой режим ─────────────────────────

GUID_RE = re.compile(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}")
ULTIMATE_GUID = "e9a42b02-d5df-448d-aa00-03f14749eb61"  # Максимальная производительность
HIGH_GUID = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"      # Высокая производительность

# (раздел, ключ, параметр, значение)
REG_TWEAKS = [
    ("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled", 1),
    ("HKCU", r"Software\Microsoft\GameBar", "AllowAutoGameMode", 1),
    ("HKCU", r"System\GameConfigStore", "GameDVR_Enabled", 0),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", 0),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency", 0),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting", 2),
    ("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling", "PowerThrottlingOff", 1),
]


def get_active_scheme():
    r = run_hidden([sys_tool("powercfg"), "/getactivescheme"])
    m = GUID_RE.search(r.stdout) if r else None
    return m.group(0) if m else None


def ensure_perf_scheme(state):
    """Находит или создаёт схему питания «максимальная производительность»."""
    saved = state.get("perf_scheme")
    r = run_hidden([sys_tool("powercfg"), "/list"])
    listing = (r.stdout if r else "").lower()
    if saved and saved.lower() in listing:
        return saved
    for src in (ULTIMATE_GUID, HIGH_GUID):
        r = run_hidden([sys_tool("powercfg"), "-duplicatescheme", src])
        m = GUID_RE.search(r.stdout) if r and r.returncode == 0 else None
        if m:
            guid = m.group(0)
            run_hidden([sys_tool("powercfg"), "/changename", guid, "PCCleaner Max Performance"])
            return guid
    return None


def _spi():
    f = ctypes.windll.user32.SystemParametersInfoW
    f.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
    f.restype = wintypes.BOOL
    return f


def get_client_anim():
    try:
        v = wintypes.BOOL()
        ok = _spi()(0x1042, 0, ctypes.byref(v), 0)  # SPI_GETCLIENTAREAANIMATION
        return bool(v.value) if ok else None
    except Exception:
        return None


def set_client_anim(on):
    try:
        _spi()(0x1043, 0, ctypes.c_void_p(1 if on else 0), 3)  # SPI_SETCLIENTAREAANIMATION
    except Exception:
        pass


def reg_apply(admin):
    saved, skipped = [], 0
    hives = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}
    for hive, path, name, value in REG_TWEAKS:
        if hive == "HKLM" and not admin:
            skipped += 1
            continue
        try:
            with winreg.CreateKeyEx(hives[hive], path, 0,
                                    winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
                try:
                    old, typ = winreg.QueryValueEx(k, name)
                except FileNotFoundError:
                    old, typ = None, None
                winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, value)
            saved.append([hive, path, name, old, typ])
        except OSError:
            skipped += 1
    return saved, skipped


def reg_restore(saved):
    hives = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}
    for hive, path, name, old, typ in saved:
        try:
            with winreg.OpenKey(hives[hive], path, 0, winreg.KEY_SET_VALUE) as k:
                if old is None:
                    try:
                        winreg.DeleteValue(k, name)
                    except FileNotFoundError:
                        pass
                else:
                    winreg.SetValueEx(k, name, 0, typ, old)
        except OSError:
            pass


def game_mode_on(admin):
    if not IS_WIN or winreg is None:
        return False, [T("Игровой режим доступен только в Windows.")]
    state = load_state()
    if state.get("game"):
        return True, [T("Игровой режим уже включён.")]

    lines = []
    saved = {"scheme": get_active_scheme(), "anim": get_client_anim(), "reg": []}

    guid = ensure_perf_scheme(state)
    if guid:
        r = run_hidden([sys_tool("powercfg"), "/setactive", guid])
        if r and r.returncode == 0:
            lines.append(T("✔ Схема питания: максимальная производительность"))
        else:
            lines.append(T("✖ Не удалось переключить схему питания"))
    else:
        lines.append(T("✖ Схема максимальной производительности недоступна на этом ПК"))

    reg_saved, skipped = reg_apply(admin)
    saved["reg"] = reg_saved
    if reg_saved:
        lines.append(T("✔ Игровой режим Windows включён, фоновая запись игр отключена, "
                     "прозрачность и эффекты переведены в режим производительности"))
    if admin and any(x[0] == "HKLM" for x in reg_saved):
        lines.append(T("✔ Отключено энергосбережение процессов (Power Throttling)"))
    elif not admin:
        lines.append(T("• Power Throttling не изменён — нужны права администратора"))

    set_client_anim(False)
    lines.append(T("✔ Анимации окон отключены"))
    lines.append("")
    lines.append(T("Часть визуальных эффектов применится после перезахода в Windows."))

    state["perf_scheme"] = guid
    state["game"] = saved
    save_state(state)
    return True, lines


def game_mode_off():
    if not IS_WIN or winreg is None:
        return False, [T("Игровой режим доступен только в Windows.")]
    state = load_state()
    saved = state.get("game")
    if not saved:
        return True, [T("Игровой режим не был включён.")]

    prev = saved.get("scheme")
    ok = False
    if prev:
        r = run_hidden([sys_tool("powercfg"), "/setactive", prev])
        ok = bool(r and r.returncode == 0)
    if not ok:
        run_hidden([sys_tool("powercfg"), "/setactive", "SCHEME_BALANCED"])
    reg_restore(saved.get("reg", []))
    if saved.get("anim") is not None:
        set_client_anim(saved["anim"])

    state.pop("game", None)
    save_state(state)
    return True, [T("✔ Схема питания, реестр и анимации возвращены как было.")]




# ───────────────────────── Мониторинг CPU / GPU / RAM ─────────────────────────
class _MEMSTAT(ctypes.Structure):
    _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


class _FT(ctypes.Structure):
    _fields_ = [("lo", wintypes.DWORD), ("hi", wintypes.DWORD)]


class _PdhVal(ctypes.Structure):
    _fields_ = [("status", wintypes.DWORD), ("value", ctypes.c_double)]


class _PdhItem(ctypes.Structure):
    _fields_ = [("name", ctypes.c_wchar_p), ("fmt", _PdhVal)]


def memory_status():
    """(загрузка %, всего байт, свободно байт)."""
    if not IS_WIN:
        return 0, 0, 0
    m = _MEMSTAT()
    m.dwLength = ctypes.sizeof(m)
    _k32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.dwMemoryLoad, m.ullTotalPhys, m.ullAvailPhys


def cpu_times():
    """(время простоя, всё время) в тиках системы."""
    idle, kern, user = _FT(), _FT(), _FT()
    _k32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user))
    f = lambda x: (x.hi << 32) | x.lo
    return f(idle), f(kern) + f(user)  # kernel уже включает простой


class GpuSampler:
    """Загрузка GPU через счётчики производительности Windows (PDH, «GPU Engine»)."""

    MORE_DATA = 0x800007D2
    NAME_RE = re.compile(r"luid_(0x[0-9a-fA-F]+_0x[0-9a-fA-F]+)_phys_\d+_eng_\d+_engtype_(.+)$")

    def __init__(self):
        self.ok = False
        if not IS_WIN:
            return
        try:
            p = ctypes.WinDLL("pdh")
            H, D = wintypes.HANDLE, wintypes.DWORD
            p.PdhOpenQueryW.argtypes = [wintypes.LPCWSTR, ctypes.c_size_t, ctypes.POINTER(H)]
            p.PdhAddEnglishCounterW.argtypes = [H, wintypes.LPCWSTR, ctypes.c_size_t,
                                                ctypes.POINTER(H)]
            p.PdhCollectQueryData.argtypes = [H]
            p.PdhGetFormattedCounterArrayW.argtypes = [H, D, ctypes.POINTER(D),
                                                       ctypes.POINTER(D), ctypes.c_void_p]
            p.PdhCloseQuery.argtypes = [H]
            for fn in (p.PdhOpenQueryW, p.PdhAddEnglishCounterW, p.PdhCollectQueryData,
                       p.PdhGetFormattedCounterArrayW, p.PdhCloseQuery):
                fn.restype = D
            self.pdh = p
            self.ok = True
        except Exception:
            self.ok = False

    def sample(self, wait):
        """wait() — пауза между двумя замерами. Возвращает % загрузки или None."""
        if not self.ok:
            wait()
            return None
        p = self.pdh
        q, c = wintypes.HANDLE(), wintypes.HANDLE()
        if p.PdhOpenQueryW(None, 0, ctypes.byref(q)) != 0:
            wait()
            return None
        try:
            if p.PdhAddEnglishCounterW(q, r"\GPU Engine(*)\Utilization Percentage", 0,
                                       ctypes.byref(c)) != 0:
                self.ok = False  # счётчиков нет (старая Windows или драйвер)
                wait()
                return None
            p.PdhCollectQueryData(q)
            wait()
            p.PdhCollectQueryData(q)
            size, count = wintypes.DWORD(0), wintypes.DWORD(0)
            fmt = 0x200 | 0x8000  # PDH_FMT_DOUBLE | PDH_FMT_NOCAP100
            st = p.PdhGetFormattedCounterArrayW(c, fmt, ctypes.byref(size),
                                                ctypes.byref(count), None)
            if st != self.MORE_DATA or size.value == 0:
                return 0.0
            buf = ctypes.create_string_buffer(size.value)
            st = p.PdhGetFormattedCounterArrayW(c, fmt, ctypes.byref(size),
                                                ctypes.byref(count), buf)
            if st != 0:
                return None
            items = ctypes.cast(buf, ctypes.POINTER(_PdhItem))
            groups = {}
            for i in range(count.value):
                it = items[i]
                if it.fmt.status not in (0, 1):
                    continue
                m = self.NAME_RE.search(it.name or "")
                key = (m.group(1), m.group(2)) if m else ("?", "?")
                groups[key] = groups.get(key, 0.0) + it.fmt.value
            return min(100.0, max(groups.values())) if groups else 0.0
        except Exception:
            return None
        finally:
            p.PdhCloseQuery(q)


class ResourceMonitor(threading.Thread):
    """Раз в секунду измеряет CPU, GPU и RAM и кладёт результат в очередь."""

    def __init__(self, out):
        super().__init__(daemon=True)
        self.out = out
        self.active = threading.Event()  # снимается, когда окно свёрнуто — экономим ресурсы
        self.active.set()
        self.stop_flag = False

    def run(self):
        gpu = GpuSampler()
        while not self.stop_flag:
            if not self.active.wait(0.5):
                continue
            idle1, tot1 = cpu_times()
            gpu_val = gpu.sample(lambda: time.sleep(1.0))
            idle2, tot2 = cpu_times()
            d_tot = tot2 - tot1
            cpu = 100.0 * (1.0 - (idle2 - idle1) / d_tot) if d_tot > 0 else 0.0
            load, total, avail = memory_status()
            self.out.put(("sys", max(0.0, min(100.0, cpu)), gpu_val, load, total, avail))


# ───────────────────────── Очистка оперативной памяти ─────────────────────────
class _PE32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]


# Критические процессы: их рабочий набор не трогаем никогда.
CRITICAL_PROCESSES = {
    "system", "system idle process", "registry", "memory compression", "secure system",
    "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe",
    "lsaiso.exe", "svchost.exe", "fontdrvhost.exe", "dwm.exe", "explorer.exe", "sihost.exe",
    "ctfmon.exe", "taskhostw.exe", "runtimebroker.exe", "shellexperiencehost.exe",
    "startmenuexperiencehost.exe", "searchhost.exe", "searchapp.exe", "searchindexer.exe",
    "textinputhost.exe", "audiodg.exe", "spoolsv.exe", "wudfhost.exe", "conhost.exe",
    "dllhost.exe", "taskmgr.exe", "msmpeng.exe", "nissrv.exe", "securityhealthservice.exe",
    "securityhealthsystray.exe", "mpdefendercoreservice.exe", "vmmem", "vmmemwsl",
    "easyanticheat.exe", "easyanticheat_eos.exe", "beservice.exe", "battleye.exe",
    "vgc.exe", "vgtray.exe", "faceitclient.exe", "ricochet.exe",
}


def list_processes():
    """[(pid, имя)] всех процессов."""
    if not IS_WIN:
        return []
    snap = _k32.CreateToolhelp32Snapshot(0x2, 0)
    if snap is None or snap == INVALID_HANDLE:
        return []
    out = []
    try:
        pe = _PE32()
        pe.dwSize = ctypes.sizeof(pe)
        ok = _k32.Process32FirstW(snap, ctypes.byref(pe))
        while ok:
            out.append((pe.th32ProcessID, pe.szExeFile))
            ok = _k32.Process32NextW(snap, ctypes.byref(pe))
    finally:
        _k32.CloseHandle(snap)
    return out


def process_image_path(h):
    buf = ctypes.create_unicode_buffer(1024)
    size = wintypes.DWORD(1024)
    if _k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
        return buf.value
    return ""


def enable_privilege(name):
    """Включает привилегию в токене процесса (нужны права администратора)."""
    try:
        adv = ctypes.WinDLL("advapi32", use_last_error=True)

        class LUID(ctypes.Structure):
            _fields_ = [("lo", wintypes.DWORD), ("hi", wintypes.LONG)]

        class LUID_ATTR(ctypes.Structure):
            _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]

        class TOKEN_PRIV(ctypes.Structure):
            _fields_ = [("Count", wintypes.DWORD), ("Privileges", LUID_ATTR * 1)]

        adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                         ctypes.POINTER(wintypes.HANDLE)]
        adv.LookupPrivilegeValueW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR,
                                              ctypes.POINTER(LUID)]
        adv.AdjustTokenPrivileges.argtypes = [wintypes.HANDLE, wintypes.BOOL,
                                              ctypes.POINTER(TOKEN_PRIV), wintypes.DWORD,
                                              ctypes.c_void_p, ctypes.c_void_p]
        token = wintypes.HANDLE()
        if not adv.OpenProcessToken(_k32.GetCurrentProcess(), 0x28, ctypes.byref(token)):
            return False
        try:
            luid = LUID()
            if not adv.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
                return False
            tp = TOKEN_PRIV()
            tp.Count = 1
            tp.Privileges[0].Luid = luid
            tp.Privileges[0].Attributes = 2  # SE_PRIVILEGE_ENABLED
            ctypes.set_last_error(0)
            ok = adv.AdjustTokenPrivileges(token, False, ctypes.byref(tp), 0, None, None)
            return bool(ok) and ctypes.get_last_error() != 1300  # ERROR_NOT_ALL_ASSIGNED
        finally:
            _k32.CloseHandle(token)
    except Exception:
        return False


def purge_standby_list():
    """Сброс списка ожидания (кэш памяти Windows). Только администратор."""
    try:
        if not enable_privilege("SeProfileSingleProcessPrivilege"):
            return False
        cmd = ctypes.c_int(4)  # MemoryPurgeStandbyList
        status = ctypes.WinDLL("ntdll").NtSetSystemInformation(
            80, ctypes.byref(cmd), ctypes.sizeof(cmd))  # SystemMemoryListInformation
        return status == 0
    except Exception:
        return False


def clean_working_set(deep=False):
    """Освобождает рабочие наборы пользовательских процессов (память уходит в кэш Windows).
    Не затрагиваются: критические процессы, службы (сессия 0), чужие сессии, компоненты Windows,
    антивирус, античиты и сама программа."""
    res = {"trimmed": 0, "protected": 0, "denied": 0, "freed": 0, "deep": None}
    if not IS_WIN:
        return res
    before = memory_status()[2]
    me = os.getpid()
    my_sess = wintypes.DWORD(0)
    _k32.ProcessIdToSessionId(me, ctypes.byref(my_sess))
    win_dir = _norm(WIN)

    for pid, name in list_processes():
        if pid <= 4 or pid == me or name.lower() in CRITICAL_PROCESSES:
            res["protected"] += 1
            continue
        sess = wintypes.DWORD(0)
        if not _k32.ProcessIdToSessionId(pid, ctypes.byref(sess)) or sess.value != my_sess.value:
            res["protected"] += 1  # службы и процессы других сессий
            continue
        h = _k32.OpenProcess(0x0100 | 0x0400, False, pid)  # SET_QUOTA | QUERY_INFORMATION
        if not h:
            res["denied"] += 1
            continue
        try:
            path = process_image_path(h)
            if path and _under(_norm(path), win_dir):
                res["protected"] += 1  # компонент Windows
                continue
            if _psapi.EmptyWorkingSet(h):
                res["trimmed"] += 1
            else:
                res["denied"] += 1
        finally:
            _k32.CloseHandle(h)

    if deep:
        res["deep"] = purge_standby_list()
    time.sleep(0.5)
    res["freed"] = max(0, memory_status()[2] - before)
    return res


# ───────────────────────── Установленные программы ─────────────────────────
UNINSTALL_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"

# Компоненты, без которых ломаются программы и Windows: удаление заблокировано.
PROTECTED_PROGRAMS = re.compile(
    r"Microsoft Visual C\+\+|Microsoft \.NET|\.NET (Core|Runtime|Desktop|SDK|Host)|"
    r"Windows (Driver|SDK|Software Development Kit)|WebView2|Microsoft Edge|"
    r"NVIDIA (Graphics|HD Audio|PhysX|Driver)|AMD (Software|Chipset|Radeon)|"
    r"Intel\(R\) (Chipset|Management|Graphics|Serial)|Realtek|DirectX|Visual Studio Installer",
    re.I)
UPDATE_NAMES = re.compile(r"^(Update for|Security Update|Hotfix)\b|\bKB\d{6,}\b", re.I)
PROTECTED_STORE_PREFIXES = (
    "microsoft.windows", "windows.", "microsoftwindows.", "microsoft.net", "microsoft.vclibs",
    "microsoft.ui.", "microsoft.desktopappinstaller", "microsoft.sechealthui",
    "microsoft.store", "microsoft.aad", "microsoft.accountscontrol", "microsoft.lockapp",
    "microsoft.win32webviewhost", "microsoft.directx", "ncsiuwpapp", "microsoft.microsoftedge",
)
_REG_VALUES = ("DisplayName", "DisplayVersion", "Publisher", "UninstallString",
               "QuietUninstallString", "EstimatedSize", "SystemComponent", "ParentKeyName",
               "ReleaseType", "NoRemove", "DisplayIcon", "InstallLocation")


def _read_reg_values(hive, path, view):
    out = {}
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_READ | view) as k:
            for name in _REG_VALUES:
                try:
                    out[name] = winreg.QueryValueEx(k, name)[0]
                except OSError:
                    pass
    except OSError:
        pass
    return out


def iter_installed_programs():
    """Программы и игры из реестра (как в «Установке и удалении программ»)."""
    if winreg is None:
        return
    sources = [("HKLM", winreg.HKEY_LOCAL_MACHINE, 0x100),   # 64-битный раздел
               ("HKLM", winreg.HKEY_LOCAL_MACHINE, 0x200),   # 32-битный раздел
               ("HKCU", winreg.HKEY_CURRENT_USER, 0x100)]
    seen = set()
    for hname, hive, view in sources:
        try:
            root = winreg.OpenKey(hive, UNINSTALL_PATH, 0, winreg.KEY_READ | view)
        except OSError:
            continue
        with root:
            for i in range(winreg.QueryInfoKey(root)[0]):
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    continue
                v = _read_reg_values(hive, UNINSTALL_PATH + "\\" + sub, view)
                name = clean_text(v.get("DisplayName", ""))
                cmd = str(v.get("UninstallString", "")).strip()
                if not name or not cmd:
                    continue
                if v.get("SystemComponent") == 1 or v.get("ParentKeyName"):
                    continue
                if UPDATE_NAMES.search(name) or v.get("ReleaseType") in (
                        "Update", "Hotfix", "Security Update", "ServicePack"):
                    continue
                version = clean_text(v.get("DisplayVersion", ""))
                key = (name.lower(), version)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    size = int(v.get("EstimatedSize", 0)) * 1024
                except (TypeError, ValueError):
                    size = 0
                yield {
                    "kind": "reg", "name": name, "version": version,
                    "publisher": clean_text(v.get("Publisher", "")), "size": size,
                    "icon": str(v.get("DisplayIcon", "")).strip(),
                    "location": str(v.get("InstallLocation", "")).strip(),
                    "cmd": cmd, "quiet_cmd": str(v.get("QuietUninstallString", "")).strip(),
                    "protected": bool(v.get("NoRemove") == 1 or PROTECTED_PROGRAMS.search(name)),
                    "hive": hname, "hive_const": hive, "view": view, "sub": sub,
                }


def reg_entry_exists(item):
    try:
        winreg.CloseKey(winreg.OpenKey(item["hive_const"], UNINSTALL_PATH + "\\" + item["sub"],
                                       0, winreg.KEY_READ | item["view"]))
        return True
    except OSError:
        return False


def pretty_package_name(name):
    """'AdvancedMicroDevicesInc-2.AMDRadeonSoftware' → 'AMD Radeon Software'."""
    if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-", name, re.I):
        return T("Приложение Microsoft Store")  # у пакета нет читаемого имени
    tail = name.split(".", 1)[1] if "." in name else name
    tail = re.sub(r"[-_]+", " ", tail)
    tail = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", tail)
    return clean_text(tail) or name


def store_publisher(raw):
    """'CN="Anthropic, PBC", O=...' → 'Anthropic, PBC'. Хэш-подобные значения отбрасываются."""
    raw = str(raw or "")
    for field in ("CN", "O"):
        m = re.search(field + r'=(?:"([^"]+)"|([^,]+))', raw)
        if m:
            val = clean_text(m.group(1) or m.group(2)).strip('"')
            if val and not re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-", val, re.I):
                return val
    return ""


def list_store_apps():
    """Приложения Microsoft Store, которые можно удалить (через PowerShell)."""
    if not IS_WIN:
        return []
    ps = ("$apps = @(Get-StartApps | Select-Object Name,AppID); "
          "$pk = @(Get-AppxPackage | Where-Object { -not $_.NonRemovable -and -not $_.IsFramework "
          "-and $_.SignatureKind -ne 'System' } | "
          "Select-Object Name,PackageFullName,PackageFamilyName,Version,Publisher,InstallLocation); "
          "ConvertTo-Json -Compress -Depth 4 -InputObject @{apps=$apps; pk=$pk}")
    exe = os.path.join(sys_dir(), "WindowsPowerShell", "v1.0", "powershell.exe")
    r = run_hidden([exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                    "-Command", "[Console]::OutputEncoding=[Text.Encoding]::UTF8; " + ps],
                   timeout=120, encoding="utf-8")
    if not r or not r.stdout.strip():
        return []
    try:
        data = json.loads(r.stdout)
    except ValueError:
        return []
    start_names = {}  # семейство пакета → название из меню «Пуск»
    for a in data.get("apps") or []:
        appid = str(a.get("AppID", ""))
        if "!" in appid:
            start_names.setdefault(appid.split("!")[0].lower(), clean_text(a.get("Name", "")))
    pk = data.get("pk") or []
    if isinstance(pk, dict):
        pk = [pk]
    apps = []
    for d in pk:
        raw_name = str(d.get("Name", ""))
        full = str(d.get("PackageFullName", ""))
        if not raw_name or not full:
            continue
        family = str(d.get("PackageFamilyName", "")).lower()
        apps.append({
            "kind": "store",
            "name": start_names.get(family) or pretty_package_name(raw_name),
            "version": clean_text(d.get("Version", "")),
            "publisher": store_publisher(d.get("Publisher", "")), "size": 0, "full": full,
            "location": str(d.get("InstallLocation") or ""),
            "protected": raw_name.lower().startswith(PROTECTED_STORE_PREFIXES),
        })
    return apps


def remove_store_app(full_name):
    exe = os.path.join(sys_dir(), "WindowsPowerShell", "v1.0", "powershell.exe")
    r = run_hidden([exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                    "-Command", f"Remove-AppxPackage -Package '{full_name}'"], timeout=600)
    return bool(r and r.returncode == 0)


def split_command(cmd):
    """Делит командную строку на (программа, параметры)."""
    cmd = cmd.strip()
    if cmd.startswith('"'):
        end = cmd.find('"', 1)
        if end > 0:
            return cmd[1:end], cmd[end + 1:].strip()
    m = re.search(r"\.(exe|bat|cmd|msi)\b", cmd, re.I)
    if m:
        return cmd[:m.end()].strip(), cmd[m.end():].strip()
    return cmd, ""


class _SEI(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("fMask", ctypes.c_ulong), ("hwnd", wintypes.HWND),
                ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR),
                ("lpParameters", wintypes.LPCWSTR), ("lpDirectory", wintypes.LPCWSTR),
                ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE),
                ("lpIDList", ctypes.c_void_p), ("lpClass", wintypes.LPCWSTR),
                ("hkeyClass", wintypes.HKEY), ("dwHotKey", wintypes.DWORD),
                ("hIconOrMonitor", wintypes.HANDLE), ("hProcess", wintypes.HANDLE)]


def shell_run_wait(file, params, elevate=False, timeout_ms=1800000):
    """Запускает программу (при необходимости с запросом UAC) и ждёт завершения."""
    shell = ctypes.WinDLL("shell32", use_last_error=True)
    shell.ShellExecuteExW.argtypes = [ctypes.POINTER(_SEI)]
    shell.ShellExecuteExW.restype = wintypes.BOOL
    sei = _SEI()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = 0x40  # SEE_MASK_NOCLOSEPROCESS
    sei.lpVerb = "runas" if elevate else None
    sei.lpFile = file
    sei.lpParameters = params or None
    sei.nShow = 1
    if not shell.ShellExecuteExW(ctypes.byref(sei)):
        return False
    if sei.hProcess:
        _k32.WaitForSingleObject(sei.hProcess, timeout_ms)
        _k32.CloseHandle(sei.hProcess)
    return True


def uninstall_program(item, quiet, admin):
    """Запускает штатный деинсталлятор программы. True — запущен."""
    cmd = item["cmd"]
    if quiet and item.get("quiet_cmd"):
        cmd = item["quiet_cmd"]
    if "msiexec" in cmd.lower():
        cmd = re.sub(r"(?i)/i(?=\s*\{)", "/X", cmd)  # «установить» → «удалить»
        if quiet and "/q" not in cmd.lower():
            cmd += " /qn /norestart"
    file, params = split_command(cmd)
    return shell_run_wait(file, params, elevate=(item["hive"] == "HKLM" and not admin))



# ───────────────────────── Значки программ ─────────────────────────
class _BIH(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


_GDI_API = None


def _gdi_api():
    """Настраивает функции GDI один раз (потокобезопасно для наших нужд)."""
    global _GDI_API
    if _GDI_API is None:
        g = ctypes.WinDLL("gdi32", use_last_error=True)
        u = ctypes.WinDLL("user32", use_last_error=True)
        sh = ctypes.WinDLL("shell32", use_last_error=True)
        g.CreateCompatibleDC.argtypes = [wintypes.HDC]
        g.CreateCompatibleDC.restype = wintypes.HDC
        g.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.c_void_p, wintypes.UINT,
                                       ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE,
                                       wintypes.DWORD]
        g.CreateDIBSection.restype = wintypes.HBITMAP
        g.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
        g.SelectObject.restype = wintypes.HGDIOBJ
        g.DeleteObject.argtypes = [wintypes.HGDIOBJ]
        g.DeleteDC.argtypes = [wintypes.HDC]
        u.DrawIconEx.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.HICON,
                                 ctypes.c_int, ctypes.c_int, wintypes.UINT, wintypes.HBRUSH,
                                 wintypes.UINT]
        u.DrawIconEx.restype = wintypes.BOOL
        u.DestroyIcon.argtypes = [wintypes.HICON]
        u.GetSystemMetrics.argtypes = [ctypes.c_int]
        sh.ExtractIconExW.argtypes = [wintypes.LPCWSTR, ctypes.c_int,
                                      ctypes.POINTER(wintypes.HICON),
                                      ctypes.POINTER(wintypes.HICON), wintypes.UINT]
        sh.ExtractIconExW.restype = wintypes.UINT
        _GDI_API = (g, u, sh)
    return _GDI_API


def _hicon_to_image(hicon, size):
    """Значок Windows → картинка RGBA с честной прозрачностью.
    Значок рисуется на чёрном и на белом фоне; по разнице вычисляется альфа-канал."""
    g, u, _sh = _gdi_api()
    hdc = g.CreateCompatibleDC(None)
    if not hdc:
        return None
    bmi = _BIH()
    bmi.biSize = ctypes.sizeof(_BIH)
    bmi.biWidth, bmi.biHeight = size, -size  # отрицательная высота — строки сверху вниз
    bmi.biPlanes, bmi.biBitCount, bmi.biCompression = 1, 32, 0
    bits = ctypes.c_void_p()
    hbmp = g.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    if not hbmp or not bits.value:
        g.DeleteDC(hdc)
        return None
    old = g.SelectObject(hdc, hbmp)
    n = size * size * 4
    try:
        ctypes.memset(bits.value, 0x00, n)
        u.DrawIconEx(hdc, 0, 0, hicon, size, size, 0, None, 3)  # DI_NORMAL
        black = ctypes.string_at(bits.value, n)
        ctypes.memset(bits.value, 0xFF, n)
        u.DrawIconEx(hdc, 0, 0, hicon, size, size, 0, None, 3)
        white = ctypes.string_at(bits.value, n)
    finally:
        g.SelectObject(hdc, old)
        g.DeleteObject(hbmp)
        g.DeleteDC(hdc)
    out = bytearray(n)
    for i in range(0, n, 4):
        diff = ((white[i] - black[i]) + (white[i + 1] - black[i + 1])
                + (white[i + 2] - black[i + 2])) / 3.0
        a = 255.0 - diff
        if a < 1.0:
            continue  # полностью прозрачный пиксель
        k = 255.0 / a
        out[i] = min(255, int(black[i + 2] * k))      # R
        out[i + 1] = min(255, int(black[i + 1] * k))  # G
        out[i + 2] = min(255, int(black[i] * k))      # B
        out[i + 3] = min(255, int(round(a)))
    return Image.frombytes("RGBA", (size, size), bytes(out))


def parse_icon_ref(ref):
    """'"C:\\a\\b.exe",2' → ('C:\\a\\b.exe', 2)."""
    ref = os.path.expandvars(str(ref).strip())
    m = re.match(r'^\s*"([^"]+)"\s*(?:,\s*(-?\d+))?\s*$', ref)
    if not m:
        m = re.match(r'^(.*?)(?:,\s*(-?\d+))?\s*$', ref)
    path = m.group(1).strip().strip('"')
    return path, int(m.group(2)) if m.group(2) else 0


def extract_icon_image(path, index, size):
    """Значок из exe/dll/ico нужного размера или None."""
    if not HAS_PIL or not path or not os.path.isfile(path):
        return None
    try:
        if path.lower().endswith(".ico"):
            return Image.open(path).convert("RGBA").resize((size, size), RESAMPLE)
        if not IS_WIN:
            return None
        _g, u, sh = _gdi_api()
        large, small = wintypes.HICON(), wintypes.HICON()
        n = sh.ExtractIconExW(path, index, ctypes.byref(large), ctypes.byref(small), 1)
        try:
            if n in (0, 0xFFFFFFFF) or not large:
                return None
            big = max(size, u.GetSystemMetrics(11) or 32)  # SM_CXICON
            img = _hicon_to_image(large, big)
            return img.resize((size, size), RESAMPLE) if img else None
        finally:
            for h in (large, small):
                if h:
                    u.DestroyIcon(h)
    except Exception:
        return None


def store_icon_image(location, size):
    """Логотип приложения Microsoft Store из его манифеста или None."""
    if not HAS_PIL or not location or not os.path.isdir(location):
        return None
    try:
        root = ET.parse(os.path.join(location, "AppxManifest.xml")).getroot()
        logo = None
        for el in root.iter():
            if el.tag.endswith("VisualElements"):
                logo = el.get("Square44x44Logo") or el.get("Square150x150Logo")
                break
        if not logo:
            return None
        parts = logo.replace("\\", "/").split("/")  # в манифесте бывают оба разделителя
        folder = os.path.join(location, *parts[:-1])
        base, ext = os.path.splitext(parts[-1])
        names = [f for f in os.listdir(folder)
                 if f.lower().startswith(base.lower()) and f.lower().endswith(ext.lower())
                 and "contrast" not in f.lower()]
        if not names:
            return None
        for hint in ("targetsize-48", "targetsize-32", "targetsize-64", "scale-200",
                     "scale-100", "targetsize-24"):
            found = [f for f in names if hint in f.lower()]
            if found:
                names = found
                break
        names.sort(key=lambda f: "altform" in f.lower())  # обычный вариант — раньше
        img = Image.open(os.path.join(folder, names[0])).convert("RGBA")
        return img.resize((size, size), RESAMPLE)
    except Exception:
        return None


AVATAR_COLORS = ["#6c8cff", "#4ade80", "#fbbf24", "#f472b6", "#22d3ee", "#a78bfa",
                 "#fb923c", "#f87171"]


def avatar_image(name, size):
    """Запасной значок: первая буква названия на цветной плашке (цвет зависит от названия)."""
    ss = 4
    s = size * ss
    col = AVATAR_COLORS[zlib.crc32(name.encode("utf-8", "ignore")) % len(AVATAR_COLORS)]
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=s * 0.28, fill=col)
    letter = next((ch for ch in name if ch.isalnum()), "?").upper()
    font = None
    for fname in ("segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(os.path.join(WIN, "Fonts", fname) if IS_WIN else fname,
                                      int(s * 0.58))
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    box = d.textbbox((0, 0), letter, font=font)
    d.text(((s - (box[2] - box[0])) / 2 - box[0], (s - (box[3] - box[1])) / 2 - box[1]),
           letter, font=font, fill=DARK)
    return img.resize((size, size), RESAMPLE)


def make_app_icon(item, size, cache):
    """Значок программы: из файла, из манифеста Store или буква на плашке."""
    img = None
    if item["kind"] == "store":
        img = store_icon_image(item.get("location"), size)
    else:
        refs = []
        if item.get("icon"):
            refs.append(parse_icon_ref(item["icon"]))
        exe = split_command(item["cmd"])[0]
        if exe and "msiexec" not in exe.lower():
            refs.append((os.path.expandvars(exe), 0))
        for path, idx in refs:
            key = (path.lower(), idx)
            if key not in cache:
                cache[key] = extract_icon_image(path, idx, size)
            img = cache[key]
            if img is not None:
                break
    return img if img is not None else avatar_image(item["name"], size)

# ───────────────────────── Резервное копирование (бэкап в .zip) ─────────────────────────
BACKUP_DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "PCCleaner Backups")
BACKUP_DEFAULT_NAME = "backup_{date}_{time}"
BACKUP_MANIFEST = "_backup_info.json"
BACKUP_CHUNK = 1024 * 1024

# Папки с кэшем и «пересобираемым» содержимым — по умолчанию в архив не попадают.
BACKUP_SKIP_DIRS = frozenset(x.lower() for x in (
    "Cache", "Cache_Data", "Code Cache", "GPUCache", "CachedData", "CachedExtensionVSIXs",
    "ShaderCache", "DawnCache", "GrShaderCache", "Service Worker", "Crashpad", "logs",
    "workspaceStorage", "node_modules", "__pycache__", ".venv", "venv", ".venv64",
    ".gradle", ".mypy_cache", ".pytest_cache", ".tox", "$RECYCLE.BIN",
    "System Volume Information",
))
# Уже сжатые форматы: повторное сжатие почти ничего не даёт, только тратит время.
BACKUP_STORED_EXT = frozenset((
    ".zip", ".7z", ".rar", ".gz", ".bz2", ".xz", ".zst", ".cab", ".jar", ".apk", ".whl",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".avif",
    ".mp3", ".aac", ".ogg", ".opus", ".flac", ".m4a",
    ".mp4", ".mkv", ".avi", ".mov", ".webm",
    ".docx", ".xlsx", ".pptx", ".odt", ".ods", ".pdf", ".epub",
))
_BAD_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
                   *(f"lpt{i}" for i in range(1, 10))}


def backup_presets():
    """Типовые конфиги, которые есть на этом ПК: (название, путь)."""
    home = os.path.expanduser("~")
    appdata = os.environ.get("APPDATA", "")
    docs = os.path.join(home, "Documents")
    cand = [
        (T("Настройки PCCleaner"), STATE_DIR),
        ("Git: .gitconfig", os.path.join(home, ".gitconfig")),
        (T("PowerShell: профиль"), os.path.join(docs, "WindowsPowerShell")),
        (T("PowerShell 7: профиль"), os.path.join(docs, "PowerShell")),
        (T("VS Code: настройки"), os.path.join(appdata, "Code", "User")),
        (T("Windows Terminal: настройки"),
         os.path.join(LOCAL, "Packages", "Microsoft.WindowsTerminal_8wekyb3d8bbwe", "LocalState")),
        (T("Файл hosts"), os.path.join(WIN, "System32", "drivers", "etc", "hosts")),
    ]
    return [(t, os.path.normpath(p)) for t, p in cand if p and os.path.exists(p)]


def backup_settings():
    st = load_state().get("backup") or {}
    if "sources" not in st:  # первый запуск — предлагаем типовые конфиги
        st["sources"] = [{"path": p, "on": True} for _t, p in backup_presets()]
    st.setdefault("dest", BACKUP_DEFAULT_DIR)
    st.setdefault("name", BACKUP_DEFAULT_NAME)
    st.setdefault("skip_cache", True)
    st.setdefault("strong", False)
    return st


def save_backup_settings(bk):
    st = load_state()
    st["backup"] = bk
    save_state(st)


def backup_name(template, when=None):
    """Имя архива из шаблона: {date}, {time}, {pc} подставляются, запрещённые символы
    Windows убираются, «.zip» добавляется. Пустая строка — имя некорректно."""
    when = time.localtime(when)
    pc = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "PC"
    name = (template or "").strip()
    for key, val in (("{date}", time.strftime("%Y-%m-%d", when)),
                     ("{time}", time.strftime("%H-%M-%S", when)),
                     ("{pc}", pc)):
        name = name.replace(key, val)
    if name.lower().endswith(".zip"):
        name = name[:-4]
    name = _BAD_NAME_CHARS.sub("_", name).strip(" .")
    if not name:
        return ""
    if name.split(".")[0].lower() in _RESERVED_NAMES:
        name = "_" + name
    return name[:150] + ".zip"


def unique_path(path):
    """file.zip → «file (2).zip», если такой файл уже есть."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{base} ({n}){ext}"):
        n += 1
    return f"{base} ({n}){ext}"


def _arc_roots(sources):
    """Имя верхней папки в архиве для каждого источника (без повторов)."""
    used, out = set(), []
    for src in sources:
        base = os.path.basename(src.rstrip("\\/")) or src[:1] or "disk"
        base = _BAD_NAME_CHARS.sub("_", base)
        name, n = base, 2
        while name.lower() in used:
            name = f"{base} ({n})"
            n += 1
        used.add(name.lower())
        out.append(name)
    return out


def iter_backup_files(src, skip_cache=True, exclude=(), stop=None, errors=None):
    """Файлы источника: (путь, путь_внутри_источника, размер). Скрытые файлы входят
    (конфиги часто скрыты), ссылки/junction и папка с самими бэкапами — нет."""
    if os.path.isfile(src):
        try:
            yield src, "", os.path.getsize(src)  # одиночный файл лежит в корне архива
        except OSError:
            pass
        return
    stack = [src]
    while stack:
        if stop and stop():
            return
        cur = stack.pop()
        try:
            it = os.scandir(cur)
        except OSError as e:
            if errors is not None:  # нет доступа к папке — сообщим пользователю
                errors.append((cur, e.strerror or str(e)))
            continue
        with it:
            for e in it:
                try:
                    st = e.stat(follow_symlinks=False)
                    if getattr(st, "st_file_attributes", 0) & ATTR_REPARSE or e.is_symlink():
                        continue
                    if e.is_dir(follow_symlinks=False):
                        if skip_cache and e.name.lower() in BACKUP_SKIP_DIRS:
                            continue
                        if exclude and _norm(e.path) in exclude:
                            continue
                        stack.append(e.path)
                    elif e.is_file(follow_symlinks=False):
                        yield e.path, os.path.relpath(e.path, src), st.st_size
                except (OSError, ValueError):
                    continue


def source_size(src, skip_cache=True, exclude=(), stop=None):
    total = count = 0
    for _p, _r, size in iter_backup_files(src, skip_cache, exclude, stop):
        total += size
        count += 1
    return total, count


def create_backup(sources, dest_dir, name, skip_cache=True, strong=False,
                  stop=None, progress=None):
    """Архивирует файлы и папки в dest_dir/name. Пишет во временный «.part» и
    переименовывает в конце — оборванный бэкап не выглядит готовым.
    progress(pct, text) вызывается не чаще ~10 раз в секунду."""
    t0 = time.time()
    os.makedirs(dest_dir, exist_ok=True)
    final = os.path.join(dest_dir, name)
    part = final + ".part"
    dest_n = _norm(dest_dir)
    exclude = {dest_n}
    stop = stop or (lambda: False)
    report = progress or (lambda _p, _t: None)

    # 1) список файлов — нужен для честного прогресса
    report(0.0, T("Собираю список файлов…"))
    files, roots, skipped = [], _arc_roots(sources), []
    for src, root in zip(sources, roots):
        for path, rel, size in iter_backup_files(src, skip_cache, exclude, stop, skipped):
            if _under(_norm(path), dest_n):  # сами бэкапы (и .part) в архив не берём
                continue
            arc = root + "/" + rel.replace("\\", "/") if rel else root
            files.append((path, arc, size))
    if stop():
        return {"cancelled": True}
    total = sum(f[2] for f in files) or 1

    # 2) архивация
    level = 9 if strong else 1  # 1 — быстро, 9 — компактнее, но в разы медленнее
    done = 0
    written = 0
    last = 0.0
    zf = None
    try:
        zf = zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED, allowZip64=True)
        for path, arc, size in files:
            if stop():
                break
            now = time.time()
            if now - last > 0.1:
                last = now
                report(done / total * 100, T('Архивирую: {0}').format(arc))
            try:
                src_f = open(path, "rb")
            except OSError as e:
                skipped.append((path, e.strerror or str(e)))
                done += size
                continue
            with src_f:
                zi = zipfile.ZipInfo.from_file(path, arc, strict_timestamps=False)
                stored = os.path.splitext(path)[1].lower() in BACKUP_STORED_EXT
                zi.compress_type = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
                for attr in ("compress_level", "_compresslevel"):  # Python 3.13+ / до 3.13
                    try:
                        setattr(zi, attr, None if stored else level)
                    except AttributeError:
                        pass
                try:
                    with zf.open(zi, "w", force_zip64=size > 0x7FFFFFFF) as dst:
                        while True:
                            chunk = src_f.read(BACKUP_CHUNK)
                            if not chunk:
                                break
                            dst.write(chunk)
                            done += len(chunk)
                            if stop():
                                break
                            now = time.time()
                            if now - last > 0.1:
                                last = now
                                report(min(done / total * 100, 99.9), T('Архивирую: {0}').format(arc))
                except OSError as e:  # файл заблокирован на чтение посреди копирования
                    skipped.append((path, e.strerror or str(e)))
                    continue
            written += 1
        if not stop():
            info = {
                "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "computer": os.environ.get("COMPUTERNAME", ""),
                "files": written,
                "sources": {r: s for r, s in zip(roots, sources)},
                "skipped": [p for p, _e in skipped],
            }
            zf.writestr(BACKUP_MANIFEST, json.dumps(info, ensure_ascii=False, indent=2))
        zf.close()
        zf = None
        if stop():
            os.remove(part)
            return {"cancelled": True}
        os.replace(part, final)
    except BaseException:
        if zf is not None:
            try:
                zf.close()
            except Exception:
                pass
        try:
            os.remove(part)
        except OSError:
            pass
        raise
    return {"path": final, "files": written, "size": sum(f[2] for f in files),
            "zip_size": os.path.getsize(final), "skipped": skipped,
            "elapsed": time.time() - t0}


# ───────────────────────── Запуск: отрываемся от консоли и IDE ─────────────────────────
def launched_from_pycharm():
    return bool(os.environ.get("PYCHARM_HOSTED"))


def pythonw_exe():
    exe = sys.executable
    if os.path.basename(exe).lower() == "python.exe":
        w = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.exists(w):
            return w
    return exe


def self_command():
    """(программа, параметры) для повторного запуска самого себя."""
    if FROZEN:
        # Без этого новая копия .exe (PyInstaller --onefile) наследует временную папку
        # _MEI… текущей копии, а та удаляет её при выходе — новая падает с ошибкой
        # «cannot import name '_imagingtk'». Переменная велит распаковаться заново.
        os.environ["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        return sys.executable, "--detached"
    return pythonw_exe(), f'"{os.path.abspath(sys.argv[0])}" --detached'


def struct_bits():
    return ctypes.sizeof(ctypes.c_void_p) * 8


def launch_unelevated():
    """Запускает копию программы БЕЗ прав администратора. Просим Проводник открыть
    программу: он работает с обычными правами, и новая копия получает его права
    (и его переменные окружения — папка _MEI… у неё будет своя)."""
    explorer = os.path.join(WIN, "explorer.exe")
    if FROZEN:
        target = sys.executable
    else:  # запуск из исходников: Проводник не умеет передавать параметры — через .cmd
        target = os.path.join(tempfile.gettempdir(), "pccleaner_relaunch.cmd")
        with open(target, "w", encoding="utf-8") as f:
            f.write("@echo off\r\nchcp 65001 >nul\r\n"
                    f'start "" "{pythonw_exe()}" "{os.path.abspath(sys.argv[0])}" --detached\r\n')
    subprocess.Popen([explorer, target], creationflags=NO_WINDOW, close_fds=True)


def relaunch_detached():
    """Запускает копию без консоли и отдельно от PyCharm. True — если получилось."""
    exe, _ = self_command()
    script = os.path.abspath(sys.argv[0])
    args = [a for a in sys.argv[1:] if a != "--detached"] + ["--detached"]
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    for extra in (0x01000000, 0):    # сначала с отрывом от job-объекта PyCharm, потом без
        try:
            subprocess.Popen([exe, script] + args, creationflags=flags | extra,
                             close_fds=True, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             cwd=os.path.dirname(script) or None)
            return True
        except OSError:
            continue
    return False


def close_ide_windows():
    """Мягко закрывает окна PyCharm (сообщение WM_CLOSE — как крестик в углу окна)."""
    if not IS_WIN:
        return 0
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    H = wintypes.HWND
    user32.IsWindowVisible.argtypes = [H]
    user32.GetWindowThreadProcessId.argtypes = [H, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindow.argtypes = [H, wintypes.UINT]
    user32.GetWindow.restype = H
    user32.PostMessageW.argtypes = [H, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                               wintypes.LPWSTR,
                                               ctypes.POINTER(wintypes.DWORD)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, H, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [enum_proc, wintypes.LPARAM]

    def process_name(pid):
        h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                return os.path.basename(buf.value).lower()
        finally:
            k32.CloseHandle(h)
        return ""

    closed = []

    def callback(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd) and not user32.GetWindow(hwnd, 4):  # GW_OWNER
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if process_name(pid.value).startswith("pycharm"):
                user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
                closed.append(hwnd)
        return True

    cb = enum_proc(callback)
    user32.EnumWindows(cb, 0)
    return len(closed)




# ───────────────────────── Оформление окон Windows (рамка, заголовок, углы) ─────────────────────────
DWMWA_DARK = 20            # тёмный заголовок (Windows 10 2004+ / 11)
DWMWA_DARK_OLD = 19        # то же на ранних сборках Windows 10
DWMWA_CORNERS = 33         # скругление углов (Windows 11)
DWMWA_BORDER_COLOR = 34    # цвет рамки окна (Windows 11)
DWMWA_CAPTION_COLOR = 35   # цвет полосы заголовка (Windows 11)
DWMWA_TEXT_COLOR = 36      # цвет текста заголовка (Windows 11)
CORNER_ROUND, CORNER_SMALL = 2, 3


def _colorref(hex_color):
    r, g, b = hex_to_rgb(hex_color)
    return r | (g << 8) | (b << 16)


def window_handle(win):
    """HWND настоящего окна верхнего уровня (у Tk winfo_id — внутреннее окно)."""
    win.update_idletasks()
    return ctypes.windll.user32.GetAncestor(win.winfo_id(), 2) or win.winfo_id()  # GA_ROOT


def _dwm_set(hwnd, attr, value):
    v = ctypes.c_int(value)
    try:
        return ctypes.windll.dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd), attr, ctypes.byref(v), ctypes.sizeof(v)) == 0
    except Exception:
        return False


_THEME_DEFAULT = object()  # «взять цвет текущей темы»


def style_window(win, caption=_THEME_DEFAULT, border=_THEME_DEFAULT, text=_THEME_DEFAULT,
                 corners=CORNER_ROUND, dark=None):
    """Стиль окна в тон программе: тёмный заголовок цвета фона, цветная рамка, скруглённые
    углы. Работает в Windows 11; в Windows 10 — только тёмный заголовок. True — если
    Windows 11 приняла настройки (углы и рамка будут нарисованы системой)."""
    if not IS_WIN:
        return False
    try:
        hwnd = window_handle(win)
    except Exception:
        return False
    if dark is None:
        dark = THEME_DARK  # у светлой темы — светлый заголовок с тёмными кнопками окна
    caption = BG if caption is _THEME_DEFAULT else caption
    border = BORDER_ACTIVE if border is _THEME_DEFAULT else border
    text = TEXT if text is _THEME_DEFAULT else text
    if not _dwm_set(hwnd, DWMWA_DARK, 1 if dark else 0):
        _dwm_set(hwnd, DWMWA_DARK_OLD, 1 if dark else 0)
    ok = _dwm_set(hwnd, DWMWA_CORNERS, corners)
    if caption:
        _dwm_set(hwnd, DWMWA_CAPTION_COLOR, _colorref(caption))
        _dwm_set(hwnd, DWMWA_TEXT_COLOR, _colorref(text))
    if border:
        _dwm_set(hwnd, DWMWA_BORDER_COLOR, _colorref(border))
    return ok


def set_window_border(win, color):
    if IS_WIN:
        try:
            _dwm_set(window_handle(win), DWMWA_BORDER_COLOR, _colorref(color))
        except Exception:
            pass


def decorate_window(win):
    """Стиль окна + рамка, которая подсвечивается акцентом, когда окно активно."""
    style_window(win)
    win.bind("<Activate>", lambda e: e.widget is win and set_window_border(win, BORDER_ACTIVE),
             add="+")
    win.bind("<Deactivate>",
             lambda e: e.widget is win and set_window_border(win, BORDER_INACTIVE), add="+")


def app_icon_image(size):
    """Значок программы: скруглённый квадрат с градиентом и белой «искрой» чистоты."""
    ss = 4
    n = size * ss
    grad = Image.new("RGB", (n, n))
    top, bottom = hex_to_rgb("#7c9bff"), hex_to_rgb("#a35cff")
    px = grad.load()
    for yy in range(n):
        for xx in range(n):
            t = (xx + yy) / (2 * n)
            px[xx, yy] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, n - 1, n - 1], radius=n * 0.24, fill=255)
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)

    def star(cx, cy, r, k=0.22):
        pts = []
        for i in range(8):
            ang = math.pi / 4 * i - math.pi / 2
            rr = r if i % 2 == 0 else r * k
            pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
        d.polygon(pts, fill=(255, 255, 255, 255))

    star(n * 0.46, n * 0.52, n * 0.30)
    star(n * 0.74, n * 0.27, n * 0.12)
    return img.resize((size, size), RESAMPLE)


def set_app_icon(root):
    """Свой значок вместо пёрышка Tk — в заголовке, на панели задач и в Alt+Tab."""
    if IS_WIN:
        try:  # чтобы на панели задач был наш значок, а не значок python.exe
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PCCleaner.App")
        except Exception:
            pass
    if not HAS_PIL:
        return
    try:
        root._icons = [ImageTk.PhotoImage(app_icon_image(sz)) for sz in (16, 32, 48, 256)]
        root.iconphoto(True, *root._icons)
    except Exception:
        pass


# ───────────────────────── Анимации и графика ─────────────────────────
ANIM = None  # единый аниматор: один таймер на все анимации (экономит процессор)


class Animator:
    def __init__(self, root):
        self.root = root
        self.jobs = {}
        self.running = False
        self.last = 0.0

    def run(self, key, fn):
        """fn(now, dt) → True, пока анимация не закончена."""
        self.jobs[key] = fn
        if not self.running:
            self.running = True
            self.last = time.perf_counter()
            self.root.after(16, self._tick)

    def _tick(self):
        now = time.perf_counter()
        dt = min(now - self.last, 0.05)
        self.last = now
        for key, fn in list(self.jobs.items()):
            try:
                alive = fn(now, dt)
            except Exception:  # виджет уничтожен или ошибка — задачу снимаем
                alive = False
            if not alive and self.jobs.get(key) is fn:
                self.jobs.pop(key, None)
        if self.jobs:
            self.root.after(16, self._tick)
        else:
            self.running = False


def ring_photo(size, ring, margin, segs, bg, track, gap=0.0):
    """Сглаженное кольцо (Pillow). Рисуется в 4× размере секторами и «дыркой» в центре,
    затем усредняется 4×4 пикселя — края ровные, без ореолов и размытия."""
    if not HAS_PIL:
        return None
    ss = 4
    size = int(size)
    big = size * ss
    m = margin * ss
    outer = [m, m, big - m - 1, big - m - 1]
    im = m + ring * ss
    inner = [im, im, big - im - 1, big - im - 1]
    img = Image.new("RGB", (big, big), bg)
    d = ImageDraw.Draw(img)
    d.ellipse(outer, fill=track)
    ang = 0.0
    for color, sweep in segs:
        draw = sweep - gap
        if sweep >= 359.5:
            d.ellipse(outer, fill=color)
        elif draw > 0.3:
            d.pieslice(outer, ang, ang + draw, fill=color)
        ang += sweep
    d.ellipse(inner, fill=bg)
    img = img.rotate(90).reduce(ss)  # старт сверху; усреднение блоков 4×4
    return ImageTk.PhotoImage(img)


def draw_ring(canvas, size, ring, margin, segs, bg, track, gap=0.0):
    photo = ring_photo(size, ring, margin, segs, bg, track, gap)
    if photo is not None:
        canvas.create_image(0, 0, anchor="nw", image=photo)
        canvas._ring_img = photo  # держим ссылку, иначе картинка исчезнет
        return
    c = size / 2
    r_mid = c - margin - ring / 2
    box = (c - r_mid, c - r_mid, c + r_mid, c + r_mid)
    canvas.create_oval(*box, outline=track, width=ring)
    start = 90.0
    for color, sweep in segs:
        draw = 359.9 if sweep >= 359.5 else max(sweep - gap, 0.5)
        canvas.create_arc(*box, start=start, extent=-draw, style="arc",
                          outline=color, width=ring)
        start -= sweep


# ───────────────────────── Сглаженная графика (Pillow, суперсэмплинг) ─────────────────────────
_PHOTOS = {}


def get_photo(key, make):
    """Кэш готовых картинок. Виджеты хранят и свою ссылку, поэтому очистка кэша безопасна."""
    ph = _PHOTOS.get(key)
    if ph is None:
        if len(_PHOTOS) > 500:
            _PHOTOS.clear()
        ph = _PHOTOS[key] = ImageTk.PhotoImage(make())
    return ph


def swatch_image(d, ring, fill, bg, ss=4):
    """Кружок-образец темы: цвет акцента в кольце цвета фона темы."""
    img = Image.new("RGB", (d * ss, d * ss), bg)
    dr = ImageDraw.Draw(img)
    dr.ellipse([0, 0, d * ss - 1, d * ss - 1], fill=ring)
    k = int(d * ss * 0.22)
    dr.ellipse([k, k, d * ss - 1 - k, d * ss - 1 - k], fill=fill)
    return img.reduce(ss)


def pill_image(w, h, fill, bg, ss=4):
    """Скруглённая «таблетка» со сглаженными краями."""
    img = Image.new("RGB", (w * ss, h * ss), bg)
    ImageDraw.Draw(img).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1],
                                          radius=h * ss / 2, fill=fill)
    return img.reduce(ss)


def bar_image(w, h, fill_w, fill, track, bg, ss=4):
    """Полоса прогресса: дорожка и заполненная часть со скруглёнными концами."""
    img = Image.new("RGB", (w * ss, h * ss), bg)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], radius=h * ss / 2, fill=track)
    if fill_w > 0:
        fw = max(fill_w, h) * ss
        d.rounded_rectangle([0, 0, min(fw, w * ss) - 1, h * ss - 1], radius=h * ss / 2,
                            fill=fill)
    return img.reduce(ss)


def toggle_image(w, h, t, enabled, bg, ss=4):
    img = Image.new("RGB", (w * ss, h * ss), bg)
    d = ImageDraw.Draw(img)
    if enabled:
        track, knob = blend(TRACK_OFF, ACCENT, t), "#ffffff"
    else:
        track, knob = DISABLED, KNOB_OFF
    d.rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], radius=h * ss / 2, fill=track)
    pad = S(3) * ss
    dd = h * ss - 2 * pad
    x = pad + (w * ss - 2 * pad - dd) * t
    d.ellipse([x, pad, x + dd, pad + dd], fill=knob)
    return img.reduce(ss)


def pill_canvas(canvas, x0, y0, x1, y1, fill):
    """Запасной вариант без Pillow: «таблетка» из двух кругов и прямоугольника."""
    h = y1 - y0
    r = h / 2
    canvas.create_oval(x0, y0, x0 + h, y1, fill=fill, outline=fill)
    canvas.create_oval(x1 - h, y0, x1, y1, fill=fill, outline=fill)
    canvas.create_rectangle(x0 + r, y0, x1 - r, y1, fill=fill, outline=fill)


def checkbox_image(size, on, bg, ss=4):
    """Сглаженный флажок: пустой с рамкой или закрашенный с галочкой."""
    s_ = size * ss
    img = Image.new("RGB", (s_, s_), bg)
    d = ImageDraw.Draw(img)
    r = s_ * 0.26
    if on:
        d.rounded_rectangle([0, 0, s_ - 1, s_ - 1], radius=r, fill=ACCENT)
        d.line([(s_ * 0.25, s_ * 0.52), (s_ * 0.43, s_ * 0.70), (s_ * 0.76, s_ * 0.32)],
               fill="#ffffff", width=max(2, int(s_ * 0.13)), joint="curve")
    else:
        t = ss * 2
        d.rounded_rectangle([0, 0, s_ - 1, s_ - 1], radius=r, fill=CHECK_OUTLINE)
        d.rounded_rectangle([t, t, s_ - 1 - t, s_ - 1 - t], radius=max(r - t, 1), fill=bg)
    return img.reduce(ss)


def ellipsize(text, font, maxw, mid=False, cache=None):
    """Обрезает строку по ширине в пикселях: «длинное назв…» или «начало…конец» для путей (mid=True)."""
    if maxw <= 4:
        return ""
    key = (id(font), text, maxw, mid)
    if cache is not None and key in cache:
        return cache[key]
    if font.measure(text) <= maxw:
        res = text
    elif not mid:
        lo, hi = 0, len(text)
        while lo < hi:
            m = (lo + hi + 1) // 2
            if font.measure(text[:m].rstrip() + "…") <= maxw:
                lo = m
            else:
                hi = m - 1
        res = text[:lo].rstrip() + "…"
    else:
        n = len(text)
        lo, hi = 0, n
        while lo < hi:  # lo — сколько символов оставить всего (поровну с начала и конца)
            k = (lo + hi + 1) // 2
            if font.measure(text[:(k + 1) // 2] + "…" + text[n - k // 2:]) <= maxw:
                lo = k
            else:
                hi = k - 1
        res = text[:(lo + 1) // 2] + "…" + text[n - lo // 2:]
    if cache is not None:
        if len(cache) > 4000:
            cache.clear()
        cache[key] = res
    return res


# ───────────────────────── Текст: подсказки, обрезка, перенос ─────────────────────────
class Tooltip:
    """Всплывающая подсказка с полным текстом."""

    def __init__(self, widget):
        self.widget, self.text, self.tip, self.job = widget, "", None, None
        widget.bind("<Enter>", self._enter, add="+")
        widget.bind("<Leave>", self._leave, add="+")
        widget.bind("<ButtonPress>", self._leave, add="+")

    def _enter(self, _e=None):
        self._leave()
        if self.text:
            self.job = self.widget.after(450, self._show)

    def _show(self):
        self.job = None
        if not self.text or self.tip is not None:
            return
        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        try:
            tip.wm_attributes("-topmost", True)
        except tk.TclError:
            pass
        tk.Label(tip, text=self.text, bg=CARD_HOVER2, fg=TEXT, font=(FONT, 9),
                 padx=S(8), pady=S(4), justify="left", wraplength=S(520)).pack()
        x = self.widget.winfo_rootx() + S(8)
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + S(4)
        tip.wm_geometry(f"+{x}+{y}")
        self.tip = tip

    def _leave(self, _e=None):
        if self.job:
            self.widget.after_cancel(self.job)
            self.job = None
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class EllipsisLabel(tk.Label):
    """Однострочная подпись: длинный текст аккуратно обрезается «…», полный виден в подсказке.
    Размещать с fill="x" — тогда ширина берётся из окружения, а не из длины текста."""

    def __init__(self, master, text="", font=None, **kw):
        kw.setdefault("anchor", "w")
        kw.setdefault("justify", "left")
        super().__init__(master, text="", font=font, width=1, **kw)
        self._full = " ".join(str(text).split())
        self._font = tkfont.Font(font=font) if font else tkfont.nametofont("TkDefaultFont")
        self._tip = Tooltip(self)
        self._last_w = -1
        self.bind("<Configure>", self._on_conf)
        self._apply()

    def configure(self, cnf=None, **kw):
        if "text" in kw:
            self._full = " ".join(str(kw.pop("text")).split())
            if kw or cnf:
                tk.Label.configure(self, cnf, **kw)
            self._apply()
            return None
        return tk.Label.configure(self, cnf, **kw)

    config = configure

    def _on_conf(self, e):
        if e.width != self._last_w:
            self._last_w = e.width
            self._apply()

    def _apply(self):
        w = self.winfo_width() - S(2)
        txt = self._full
        if w > S(12) and self._font.measure(txt) > w:
            lo, hi = 0, len(txt)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if self._font.measure(txt[:mid].rstrip() + "…") <= w:
                    lo = mid
                else:
                    hi = mid - 1
            shown = txt[:lo].rstrip() + "…"
            self._tip.text = self._full
        else:
            shown = txt
            self._tip.text = ""
        if shown != tk.Label.cget(self, "text"):
            tk.Label.configure(self, text=shown)


class WrapLabel(tk.Label):
    """Абзац текста: переносится по словам под текущую ширину окна.
    Размещать с fill="x"."""

    def __init__(self, master, text="", font=None, **kw):
        kw.setdefault("anchor", "w")
        kw.setdefault("justify", "left")
        super().__init__(master, text=text, font=font, wraplength=S(300), **kw)
        self.bind("<Configure>", self._on_conf)

    def _on_conf(self, e):
        wl = max(S(60), e.width - S(2))
        if abs(wl - int(float(self.cget("wraplength")))) > 1:
            tk.Label.configure(self, wraplength=wl)


# ───────────────────────── Виджеты ─────────────────────────
class FlatButton(tk.Canvas):
    """Скруглённая кнопка со сглаженными краями и плавной подсветкой при наведении."""

    def __init__(self, master, text, command, bg=None, hover=None,
                 fg=None, size=11, padx=22, pady=10):
        # цвета по умолчанию берутся в момент создания — чтобы работала смена темы на лету
        bg, hover, fg = bg or ACCENT, hover or ACCENT_HOVER, fg or DARK
        self._font = tkfont.Font(family=FONT, size=size, weight="bold")
        self._padx, self._pady = S(padx), S(pady)
        self._text = text
        try:
            self._outer = master.cget("bg")
        except tk.TclError:
            self._outer = BG
        self._bw, self._hpx = self._measure()
        super().__init__(master, width=self._bw, height=self._hpx, bg=self._outer,
                         highlightthickness=0, cursor="hand2")
        self._bg, self._hover, self._fg, self._cmd = bg, hover, fg, command
        self._enabled = True
        self._hv = self._ht = 0.0
        self._img = None
        self.bind("<Enter>", lambda e: self._hover_to(1.0))
        self.bind("<Leave>", lambda e: self._hover_to(0.0))
        self.bind("<Button-1>", lambda e: self._enabled and self._cmd())
        self._draw()

    def _measure(self):
        h = self._font.metrics("linespace") + 2 * self._pady
        return max(self._font.measure(self._text) + 2 * self._padx, h), h

    def configure(self, cnf=None, **kw):
        if "text" in kw:
            self._text = str(kw.pop("text"))
            self._bw, self._hpx = self._measure()
            kw["width"], kw["height"] = self._bw, self._hpx
            tk.Canvas.configure(self, cnf, **kw)
            self._draw()
            return None
        return tk.Canvas.configure(self, cnf, **kw)

    config = configure

    def _draw(self):
        self.delete("all")
        w, h = self._bw, self._hpx
        if self._enabled:
            color = blend(self._bg, self._hover, round(self._hv * 8) / 8)
            fg = self._fg
        else:
            color, fg = DISABLED, MUTED
        if HAS_PIL:
            self._img = get_photo(("pill", w, h, color, self._outer),
                                  lambda: pill_image(w, h, color, self._outer))
            self.create_image(0, 0, anchor="nw", image=self._img)
        else:
            pill_canvas(self, 1, 1, w - 1, h - 1, color)
        self.create_text(w / 2, h / 2, text=self._text, fill=fg, font=self._font)

    def _hover_to(self, v):
        if not self._enabled:
            return
        self._ht = v
        if ANIM:
            ANIM.run(("btn", id(self)), self._step)
        else:
            self._hv = v
            self._draw()

    def _step(self, now, dt):
        self._hv = approach(self._hv, self._ht, dt, 18.0, 0.02)
        self._draw()
        return self._hv != self._ht

    def set_style(self, bg, hover, fg):
        self._bg, self._hover, self._fg = bg, hover, fg
        self._draw()

    def set_enabled(self, value: bool):
        self._enabled = value
        tk.Canvas.configure(self, cursor="hand2" if value else "arrow")
        self._draw()


class Toggle(tk.Canvas):
    """Переключатель в стиле iOS: сглаженный, с плавным движением ползунка."""

    def __init__(self, master, variable, command=None, bg=None, enabled=True):
        bg = bg or CARD
        self.w, self.h = S(40), S(22)
        super().__init__(master, width=self.w, height=self.h, bg=bg,
                         highlightthickness=0, cursor="hand2" if enabled else "arrow")
        self._outer = bg
        self.var, self.command, self.enabled = variable, command, enabled
        self._t = self._target = 1.0 if variable.get() else 0.0
        self._from, self._t0 = self._t, 0.0
        self._img = None
        self.bind("<Button-1>", self._click)
        variable.trace_add("write", self._on_var)
        self.redraw()

    def _click(self, _e):
        if not self.enabled:
            return
        self.var.set(not self.var.get())
        if self.command:
            self.command()

    def _on_var(self, *_):
        if not self.winfo_exists():
            return
        self._target = 1.0 if self.var.get() else 0.0
        self._from, self._t0 = self._t, time.perf_counter()
        if ANIM:
            ANIM.run(("toggle", id(self)), self._step)
        else:
            self._t = self._target
            self.redraw()

    def _step(self, now, dt):
        p = min(1.0, (now - self._t0) / 0.2)
        self._t = self._from + (self._target - self._from) * ease_out(p)
        self.redraw()
        return p < 1.0

    def redraw(self):
        self.delete("all")
        t = round(self._t * 24) / 24
        w, h = self.w, self.h
        if HAS_PIL:
            en, bg = self.enabled, self._outer
            self._img = get_photo(("toggle", w, h, t, en, bg),
                                  lambda: toggle_image(w, h, t, en, bg))
            self.create_image(0, 0, anchor="nw", image=self._img)
            return
        track = blend(TRACK_OFF, ACCENT, t) if self.enabled else DISABLED
        knob = "#ffffff" if self.enabled else KNOB_OFF
        pad = S(3)
        r = h / 2
        self.create_oval(0, 0, h, h, fill=track, outline=track)
        self.create_oval(w - h, 0, w, h, fill=track, outline=track)
        self.create_rectangle(r, 0, w - r, h, fill=track, outline=track)
        d = h - 2 * pad
        x = pad + (w - 2 * pad - d) * t
        self.create_oval(x, pad, x + d, pad + d, fill=knob, outline=knob)


class RingGauge(tk.Canvas):
    """Круговой индикатор нагрузки с плавным изменением значения."""

    def __init__(self, master, title, size=112):
        self.size = S(size)
        super().__init__(master, width=self.size, height=self.size + S(30), bg=CARD,
                         highlightthickness=0)
        self.title = title
        self.value = self.target = 0.0
        self.sub = ""
        self.available = True
        self.redraw()

    def set(self, value, sub=""):
        self.sub = sub
        self.available = value is not None
        self.target = 0.0 if value is None else max(0.0, min(100.0, value))
        if ANIM:
            ANIM.run(("gauge", id(self)), self._step)

    def _step(self, now, dt):
        self.value = approach(self.value, self.target, dt, 7.0, 0.05)
        self.redraw()
        return self.value != self.target

    def redraw(self):
        c = self
        c.delete("all")
        sweep = self.value / 100 * 360
        segs = [(load_color(self.value), sweep)] if sweep > 0.5 else []
        draw_ring(c, self.size, S(11), S(4), segs, CARD, CARD_HOVER)
        cx = self.size / 2
        txt = f"{self.value:.0f}%" if self.available else T("н/д")
        c.create_text(cx, cx - S(6), text=txt, fill=TEXT, font=(FONT, 17, "bold"))
        if self.sub:
            c.create_text(cx, cx + S(16), text=self.sub, fill=MUTED, font=(FONT, 8))
        c.create_text(cx, self.size + S(14), text=self.title, fill=TEXT, font=(FONT, 10, "bold"))


class MiniMeter(tk.Canvas):
    """Компактный индикатор для верхней панели (сглаженная полоса)."""

    def __init__(self, master, title):
        self.w, self.h = S(112), S(36)
        super().__init__(master, width=self.w, height=self.h, bg=BG, highlightthickness=0)
        self.title = title
        self.value = self.target = 0.0
        self.available = True
        self._img = None
        self.redraw()

    def set(self, value):
        self.available = value is not None
        self.target = 0.0 if value is None else max(0.0, min(100.0, value))
        if ANIM:
            ANIM.run(("mini", id(self)), self._step)

    def _step(self, now, dt):
        self.value = approach(self.value, self.target, dt, 8.0, 0.05)
        self.redraw()
        return self.value != self.target

    def redraw(self):
        self.delete("all")
        self.create_text(0, S(8), anchor="w", text=self.title, fill=MUTED, font=(FONT, 8, "bold"))
        txt = f"{self.value:.0f}%" if self.available else "—"
        self.create_text(self.w, S(8), anchor="e", text=txt, fill=TEXT, font=(FONT, 9, "bold"))
        y0, hb = S(21), S(8)
        fill_w = int(round(self.w * self.value / 100))
        color = load_color(self.value)
        if HAS_PIL:
            self._img = ImageTk.PhotoImage(
                bar_image(self.w, hb, fill_w, color, CARD_HOVER, BG))
            self.create_image(0, y0, anchor="nw", image=self._img)
        else:
            pill_canvas(self, 0, y0, self.w, y0 + hb, CARD_HOVER)
            if fill_w > 0:
                pill_canvas(self, 0, y0, max(fill_w, hb), y0 + hb, color)


class SmoothProgress(tk.Canvas):
    """Полоса прогресса со скруглёнными краями. Интерфейс как у ttk.Progressbar: config(value=…)."""

    def __init__(self, master, height=10):
        self.hpx = S(height)
        try:
            self._outer = master.cget("bg")
        except tk.TclError:
            self._outer = BG
        super().__init__(master, height=self.hpx, bg=self._outer, highlightthickness=0)
        self.value = 0.0
        self._img = None
        self._last = None
        self.bind("<Configure>", lambda e: self.redraw())

    def configure(self, cnf=None, **kw):
        if "value" in kw:
            self.value = max(0.0, min(100.0, float(kw.pop("value"))))
            if kw or cnf:
                tk.Canvas.configure(self, cnf, **kw)
            self.redraw()
            return None
        return tk.Canvas.configure(self, cnf, **kw)

    config = configure

    def redraw(self):
        w = self.winfo_width()
        if w <= 4:
            return
        h = self.hpx
        fill_w = int(round(w * self.value / 100))
        state = (w, fill_w)
        if state == self._last:
            return
        self._last = state
        self.delete("all")
        if HAS_PIL:
            self._img = ImageTk.PhotoImage(
                bar_image(w, h, fill_w, ACCENT, CARD, self._outer))
            self.create_image(0, 0, anchor="nw", image=self._img)
        else:
            pill_canvas(self, 0, 0, w, h, CARD)
            if fill_w > 0:
                pill_canvas(self, 0, 0, max(fill_w, h), h, ACCENT)


class _MenuRow(tk.Canvas):
    """Строка выпадающего списка: при наведении подсвечивается скруглённой «таблеткой»."""

    def __init__(self, master, text, on, width, command, swatch=None):
        self.swatch = swatch  # (цвет фона темы, акцент темы) — кружок-образец слева от текста
        self.f = tkfont.Font(family=FONT, size=10, weight="bold" if on else "normal")
        self.h = self.f.metrics("linespace") + S(14)
        super().__init__(master, width=width, height=self.h, bg=CARD, highlightthickness=0,
                         cursor="hand2")
        self.text, self.on, self.w = text, on, width
        self.hover = False
        self._img = None
        self.bind("<Enter>", lambda e: self._set(True))
        self.bind("<Leave>", lambda e: self._set(False))
        self.bind("<ButtonRelease-1>", lambda e: command())
        self.draw()

    def _set(self, v):
        self.hover = v
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = self.w, self.h
        row_bg = CARD
        if self.hover or self.on:
            fill = row_bg = CARD_HOVER if self.hover else MENU_ON
            if HAS_PIL:
                self._img = get_photo(("pill_r", w, h, fill), lambda: pill_image(w, h, fill, CARD))
                self.create_image(0, 0, anchor="nw", image=self._img)
            else:
                pill_canvas(self, 0, 0, w, h, fill)
        x = S(14)
        if self.on:
            self.create_text(x, h / 2, text="✔", anchor="w", fill=ACCENT, font=self.f)
        x += S(24)
        if self.swatch:
            d = S(16)
            if HAS_PIL:
                ph = get_photo(("swatch", d) + tuple(self.swatch) + (row_bg,),
                               lambda: swatch_image(d, *self.swatch, row_bg))
                self._sw = ph
                self.create_image(x, h / 2, anchor="w", image=ph)
            else:
                self.create_oval(x, h / 2 - d / 2, x + d, h / 2 + d / 2, fill=self.swatch[1],
                                 outline=self.swatch[0], width=3)
            x += d + S(10)
        self.create_text(x, h / 2, text=self.text, anchor="w",
                         fill=ACCENT if self.on else TEXT, font=self.f)


class Dropdown(tk.Toplevel):
    """Выпадающий список под кнопкой: скруглённые углы (Windows 11), плавное появление
    со сдвигом вниз. Закрывается кликом мимо списка, клавишей Esc или при переключении
    на другое окно."""

    OPEN_TIME = 0.16
    CLOSE_TIME = 0.10
    SLIDE = 8

    def __init__(self, anchor, items, current, command, on_close=None):
        super().__init__(anchor)
        self.withdraw()  # прячем до расчёта позиции: иначе Windows рисует окно в углу экрана
        self.command, self.on_close = command, on_close
        self.closing = False
        self.overrideredirect(True)
        self.configure(bg=CARD)
        self.box = tk.Frame(self, bg=CARD)
        self.box.pack(fill="both", expand=True)
        f = tkfont.Font(family=FONT, size=10, weight="bold")
        items = [tuple(it) + (None,) * (3 - len(it)) for it in items]  # (ключ, текст, образец)
        extra = S(26) if any(sw for _k, _t, sw in items) else 0
        width = max(anchor.winfo_width() - S(12),
                    max(f.measure(t) for _k, t, _s in items) + S(58) + extra)
        for key, text, sw in items:
            _MenuRow(self.box, text, key == current, width,
                     lambda k=key: self._pick(k), swatch=sw).pack(padx=S(6), pady=(S(2), 0))
        tk.Frame(self.box, bg=CARD, height=S(6)).pack()
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = anchor.winfo_rootx() + anchor.winfo_width() - w  # правый край — под кнопкой
        self.y0 = anchor.winfo_rooty() + anchor.winfo_height() + S(6)
        self.x0, self.w, self.h = max(0, x), w, h
        self._place(0.0)
        try:
            self.attributes("-topmost", True)
            self.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        self.deiconify()
        self._place(0.0)  # повторно: Windows может сбросить позицию при показе окна
        if not style_window(self, caption=None, border=CARD_HOVER2, corners=CORNER_ROUND,
                            dark=False):
            self.configure(bg=CARD_HOVER2)  # нет скругления (Windows 10) — тонкая рамка
            self.box.pack_configure(padx=1, pady=1)
        self.bind("<Escape>", lambda e: self.close())
        self.bind("<Button-1>", self._click_outside)
        self.bind("<FocusOut>", lambda e: self.close())
        self.focus_force()
        try:
            self.grab_set()  # клик в любом месте окна программы попадает сюда
        except tk.TclError:
            pass
        self.t0 = time.perf_counter()
        self._animate(self._open_step)

    # ---------- анимация ----------
    def _animate(self, fn):
        if ANIM:
            ANIM.run(("dropdown", id(self)), fn)
        else:
            fn(time.perf_counter() + 10, 0)

    def _place(self, t):
        dy = int(round((1 - t) * -S(self.SLIDE)))
        self.geometry(f"{self.w}x{self.h}+{self.x0}+{self.y0 + dy}")

    def _alpha(self, a):
        try:
            self.attributes("-alpha", max(0.0, min(1.0, a)))
        except tk.TclError:
            pass

    def _open_step(self, now, _dt):
        if self.closing or not self.winfo_exists():
            return False
        t = ease_out((now - self.t0) / self.OPEN_TIME)
        self._place(t)
        self._alpha(t)
        return t < 1.0

    def _close_step(self, now, _dt):
        if not self.winfo_exists():
            return False
        t = min(1.0, (now - self.t0) / self.CLOSE_TIME)
        self._alpha(1.0 - t)
        if t >= 1.0:
            self.destroy()
            return False
        return True

    # ---------- события ----------
    def _click_outside(self, e):
        x, y = e.x_root - self.winfo_rootx(), e.y_root - self.winfo_rooty()
        if not (0 <= x < self.winfo_width() and 0 <= y < self.winfo_height()):
            self.close()

    def _pick(self, key):
        self.close()
        self.command(key)

    def close(self):
        if self.closing or not self.winfo_exists():
            return
        self.closing = True
        try:
            self.grab_release()
        except tk.TclError:
            pass
        if self.on_close:
            self.on_close()
        self.t0 = time.perf_counter()
        self._animate(self._close_step)


class Tabs(tk.Frame):
    def __init__(self, master, names, command, size=10, padx=16, pady=8,
                 active=None, active_hover=None, active_fg=None):
        super().__init__(master, bg=BG)
        self.command = command
        self.active = (active or ACCENT, active_hover or ACCENT_HOVER, active_fg or DARK)
        self.buttons = {}
        for key, text in names:
            b = FlatButton(self, text, lambda k=key: self.select(k), bg=CARD, hover=CARD_HOVER,
                           fg=MUTED, size=size, padx=padx, pady=pady)
            b.pack(side="left", padx=(0, S(6)))
            self.buttons[key] = b

    def select(self, key, call=True):
        for k, b in self.buttons.items():
            if k == key:
                b.set_style(*self.active)
            else:
                b.set_style(CARD, CARD_HOVER, MUTED)
        if call:
            self.command(key)


class CheckList(tk.Frame):
    """Прокручиваемый список с отметками. На Canvas рисуются только видимые строки,
    поэтому он быстр и при тысячах записей. В строке: флажок, значок, название и
    пояснение (слева), значение и метка (справа). Длинный текст обрезается «…»,
    полный показывается во всплывающей подсказке."""

    def __init__(self, master, on_change=None, row_h=54, icon_px=0, right_w=120):
        super().__init__(master, bg=CARD)
        self.on_change = on_change
        self.rh = S(row_h)
        self.icon_px = icon_px
        self.right_w = S(right_w)
        self.items = {}      # iid -> словарь строки
        self.order = []      # все строки в порядке сортировки
        self.view = []       # строки после фильтра
        self.checked = set()
        self.offset = self._target = 0.0
        self.hover = -1
        self._seq = 0
        self._job = None
        self._pred = None
        self._ell = {}
        self._used = []
        self._tip = self._tip_job = None
        self._tip_row = -1
        self.f_name = tkfont.Font(family=FONT_SEMI, size=10)
        self.f_sub = tkfont.Font(family=FONT, size=9)
        self.f_right = tkfont.Font(family=FONT_SEMI, size=10)
        self.f_tag = tkfont.Font(family=FONT, size=8)

        self.canvas = tk.Canvas(self, bg=CARD, highlightthickness=0)
        self.sb = ttk.Scrollbar(self, orient="vertical", command=self._on_sb)
        self.sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._schedule())
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<Button-1>", self._on_click)

    # ---------- данные ----------
    def add(self, name, sub="", right="", tag="", payload=None, locked=False, keys=None,
            image=None, mid=False):
        self._seq += 1
        iid = str(self._seq)
        name = clean_text(name) or "—"
        it = {"name": name, "sub": clean_text(sub), "right": clean_text(right),
              "tag": clean_text(tag), "payload": payload, "locked": locked,
              "keys": dict(keys or {}), "image": image, "mid": mid, "trunc": False}
        it["keys"].setdefault("name", name.lower())
        self.items[iid] = it
        self.order.append(iid)
        self._schedule()
        return iid

    def set_image(self, iid, photo):
        if iid in self.items:
            self.items[iid]["image"] = photo
            self._schedule()

    def checked_items(self):
        return [self.items[i] for i in self.checked if i in self.items]

    def set_checked(self, iid, on):
        it = self.items.get(iid)
        if it and not it["locked"]:
            (self.checked.add if on else self.checked.discard)(iid)

    def select_all(self):
        self._flush()
        for iid in self.view:
            self.set_checked(iid, True)
        self._redraw()
        if self.on_change:
            self.on_change()

    def select_none(self):
        self.checked.clear()
        self._redraw()
        if self.on_change:
            self.on_change()

    def apply_filter(self, pred=None):
        self._pred = pred
        self.offset = self._target = 0.0
        self._schedule()

    def sort_by(self, key, reverse=False):
        self.order.sort(key=lambda i: self.items[i]["keys"].get(key, ""), reverse=reverse)
        self._schedule()

    def remove(self, iids):
        for iid in iids:
            self.checked.discard(iid)
            self.items.pop(iid, None)
        self.order = [i for i in self.order if i in self.items]
        self._schedule()

    def clear(self):
        self.items.clear()
        self.order.clear()
        self.view.clear()
        self.checked.clear()
        self.offset = self._target = 0.0
        self._schedule()

    # ---------- перерисовка ----------
    def _schedule(self):
        if self._job is None:
            self._job = self.after(25, self._flush)

    def _flush(self):
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        if not self.winfo_exists():
            return
        pred = self._pred
        self.view = [i for i in self.order if pred is None or pred(self.items[i])]
        self._clamp()
        self._redraw()

    def _max_off(self):
        return max(0.0, len(self.view) * self.rh - self.canvas.winfo_height())

    def _clamp(self):
        m = self._max_off()
        self.offset = max(0.0, min(self.offset, m))
        self._target = max(0.0, min(self._target, m))

    def _update_sb(self):
        total = len(self.view) * self.rh
        h = self.canvas.winfo_height()
        if total <= h or total <= 0:
            self.sb.set(0.0, 1.0)
        else:
            self.sb.set(self.offset / total, (self.offset + h) / total)

    def _draw_check(self, x, y, size, on, bg):
        c = self.canvas
        if HAS_PIL:
            ph = get_photo(("cb", size, on, bg), lambda: checkbox_image(size, on, bg))
            self._used.append(ph)
            c.create_image(x, y, anchor="nw", image=ph)
        else:
            c.create_rectangle(x, y, x + size, y + size, outline=ACCENT if on else CHECK_OUTLINE,
                               fill=ACCENT if on else bg, width=2)
            if on:
                c.create_line(x + size * .25, y + size * .52, x + size * .43, y + size * .70,
                              x + size * .76, y + size * .32, fill="#ffffff", width=2)

    def _redraw(self):
        c = self.canvas
        c.delete("all")
        self._used = []
        W, H = c.winfo_width(), c.winfo_height()
        if W <= 2 or H <= 2:
            return
        rh, n = self.rh, len(self.view)
        off = int(round(self.offset))
        first = max(0, off // rh)
        last = min(n, (off + H) // rh + 1)
        pad, cb, gap = S(14), S(20), S(12)
        rw = self.right_w
        for idx in range(first, last):
            iid = self.view[idx]
            it = self.items[iid]
            on = iid in self.checked
            bg = ROW_CHECKED if on else (CARD_HOVER if idx == self.hover else CARD)
            y = idx * rh - off
            cy = y + rh / 2 - 0.5
            c.create_rectangle(0, y, W, y + rh - 1, fill=bg, outline=bg)
            c.create_line(0, y + rh - 1, W, y + rh - 1, fill=SEPARATOR)
            x = pad
            if it["locked"]:
                c.create_text(x + cb / 2, cy, text="🔒", fill=MUTED, font=(FONT, 10))
            else:
                self._draw_check(x, cy - cb / 2, cb, on, bg)
            x += cb + gap
            if self.icon_px:
                if it["image"] is not None:
                    c.create_image(x, cy - self.icon_px / 2, anchor="nw", image=it["image"])
                x += self.icon_px + gap
            dim = MUTED if it["locked"] else TEXT
            c.create_text(W - pad, cy - S(9), anchor="e", fill=dim, font=self.f_right,
                          text=ellipsize(it["right"], self.f_right, rw, cache=self._ell))
            c.create_text(W - pad, cy + S(10), anchor="e", fill=MUTED, font=self.f_tag,
                          text=ellipsize(it["tag"], self.f_tag, rw, cache=self._ell))
            avail = W - pad - rw - gap - x
            name_s = ellipsize(it["name"], self.f_name, avail, cache=self._ell)
            sub_s = ellipsize(it["sub"], self.f_sub, avail, it["mid"], self._ell)
            c.create_text(x, cy - S(9), anchor="w", text=name_s, fill=dim, font=self.f_name)
            c.create_text(x, cy + S(10), anchor="w", text=sub_s, fill=MUTED, font=self.f_sub)
            it["trunc"] = name_s != it["name"] or sub_s != it["sub"]
        self._update_sb()

    # ---------- прокрутка ----------
    def _on_wheel(self, e):
        self._scroll_to(self._target + (-1 if e.delta > 0 else 1) * self.rh * 1.6)

    def _on_sb(self, *args):
        h = self.canvas.winfo_height()
        if args[0] == "moveto":
            total = len(self.view) * self.rh
            self.offset = self._target = max(0.0, min(float(args[1]) * total, self._max_off()))
            self._redraw()
        elif args[0] == "scroll":
            step = self.rh if args[2] == "units" else h * 0.9
            self._scroll_to(self._target + int(args[1]) * step)

    def _scroll_to(self, target):
        self._target = max(0.0, min(target, self._max_off()))
        if ANIM:
            ANIM.run(("scroll", id(self)), self._scroll_step)
        else:
            self.offset = self._target
            self._redraw()

    def _scroll_step(self, now, dt):
        self.offset = approach(self.offset, self._target, dt, 16.0, 0.5)
        self._redraw()
        return self.offset != self._target

    # ---------- мышь ----------
    def _row_at(self, y):
        idx = int((y + round(self.offset)) // self.rh)
        return idx if 0 <= idx < len(self.view) else -1

    def _on_click(self, e):
        self._hide_tip()
        idx = self._row_at(e.y)
        if idx < 0:
            return
        iid = self.view[idx]
        if self.items[iid]["locked"]:
            return
        self.set_checked(iid, iid not in self.checked)
        self._redraw()
        if self.on_change:
            self.on_change()

    def _on_motion(self, e):
        idx = self._row_at(e.y)
        if idx != self.hover:
            self.hover = idx
            self._redraw()
        if idx != self._tip_row:
            self._hide_tip()
            self._tip_row = idx
            if idx >= 0 and self.items[self.view[idx]]["trunc"]:
                self._tip_job = self.after(500, self._show_tip, idx, e.x_root, e.y_root)

    def _on_leave(self, _e=None):
        self.hover = -1
        self._tip_row = -1
        self._hide_tip()
        self._redraw()

    def _show_tip(self, idx, x, y):
        self._tip_job = None
        if idx != self.hover or idx >= len(self.view):
            return
        it = self.items[self.view[idx]]
        text = "\n".join(t for t in (it["name"], it["sub"], it["tag"]) if t)
        tip = tk.Toplevel(self)
        tip.wm_overrideredirect(True)
        try:
            tip.wm_attributes("-topmost", True)
        except tk.TclError:
            pass
        tk.Label(tip, text=text, bg=CARD_HOVER2, fg=TEXT, font=(FONT, 9), padx=S(10),
                 pady=S(6), justify="left", wraplength=S(560)).pack()
        tip.wm_geometry(f"+{x + S(14)}+{y + S(18)}")
        self._tip = tip

    def _hide_tip(self):
        if self._tip_job:
            self.after_cancel(self._tip_job)
            self._tip_job = None
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None


# ───────────────────────── Окно белого списка ─────────────────────────
class WhitelistWindow(tk.Toplevel):
    """Файлы и папки, которые программа никогда не удаляет."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title(T("Белый список"))
        self.configure(bg=BG)
        w = min(S(820), self.winfo_screenwidth() - 60)
        h = min(S(560), self.winfo_screenheight() - 100)
        self.geometry(f"{w}x{h}")
        self.minsize(S(640), S(420))
        self.transient(app)
        self.var_path = tk.StringVar()
        self._build()
        decorate_window(self)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._reload()

    def _build(self):
        pad = S(22)
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=pad, pady=(S(18), S(6)))
        tk.Label(head, text=T("🛡  Белый список"), bg=BG, fg=TEXT,
                 font=(FONT, 18, "bold")).pack(anchor="w")
        WrapLabel(head, bg=BG, fg=MUTED, font=(FONT, 10),
                 text=T("Файлы и папки из этого списка исключаются из сканирования и очистки. "
                      "Папка защищает всё содержимое. Скрытые файлы можно добавить, вставив "
                      "путь в поле ниже или отметив их в окне «Особые файлы».")
                 ).pack(fill="x", pady=(S(2), 0))

        bottom = tk.Frame(self, bg=BG)
        bottom.pack(side="bottom", fill="x", padx=pad, pady=(S(8), S(18)))
        btns = tk.Frame(bottom, bg=BG)
        btns.pack(fill="x", pady=(S(10), 0))
        FlatButton(btns, T("Убрать отмеченные"), self.remove_selected, bg=RED, hover=RED_HOVER,
                   size=10, padx=16, pady=9).pack(side="right")
        for text, cmd in ((T("+ Файлы"), self.add_files), (T("+ Папка"), self.add_folder)):
            FlatButton(btns, text, cmd, bg=CARD_HOVER, hover=CARD_HOVER2, fg=TEXT,
                       size=10, padx=14, pady=9).pack(side="left", padx=(0, S(8)))

        row = tk.Frame(bottom, bg=CARD)
        row.pack(fill="x")
        tk.Label(row, text=T("Путь:"), bg=CARD, fg=MUTED, font=(FONT, 10)).pack(
            side="left", padx=(S(14), S(8)), pady=S(8))
        entry = tk.Entry(row, textvariable=self.var_path, bg=CARD_HOVER, fg=TEXT,
                         insertbackground=TEXT, relief="flat", font=(FONT, 10))
        entry.pack(side="left", fill="x", expand=True, ipady=S(5), pady=S(8))
        entry.bind("<Return>", lambda e: self.add_typed())
        FlatButton(row, T("Добавить"), self.add_typed, size=10, padx=14, pady=6).pack(
            side="left", padx=S(10))

        self.ct = CheckList(self, row_h=50, right_w=80)
        self.ct.pack(fill="both", expand=True, padx=pad)

    def _reload(self):
        self.ct.clear()
        for p in get_whitelist():
            self.ct.add(os.path.basename(p.rstrip("\\/")) or p, sub=p,
                        right=T("Папка") if os.path.isdir(p) else T("Файл"), payload=p, mid=True)

    def _add(self, paths):
        paths = [os.path.normpath(p) for p in paths if p]
        if not paths:
            return
        set_whitelist(get_whitelist() + paths)
        self._reload()
        self.app.on_whitelist_changed()

    def add_files(self):
        files = filedialog.askopenfilenames(parent=self, title=T("Файлы для белого списка"))
        self._add(list(files))

    def add_folder(self):
        d = filedialog.askdirectory(parent=self, title=T("Папка для белого списка"))
        self._add([d] if d else [])

    def add_typed(self):
        p = self.var_path.get().strip().strip('"')
        if not p:
            return
        if not os.path.exists(p):
            messagebox.showwarning(T("Белый список"), T("Такого пути не существует."), parent=self)
            return
        self.var_path.set("")
        self._add([p])

    def remove_selected(self):
        sel = [it["payload"] for it in self.ct.checked_items()]
        if not sel:
            messagebox.showinfo(T("Белый список"), T("Отметьте строки в списке."), parent=self)
            return
        keep = [p for p in get_whitelist() if p not in sel]
        set_whitelist(keep)
        self._reload()
        self.app.on_whitelist_changed()

    def _close(self):
        self.app.wl_window = None
        self.destroy()


# ───────────────────────── Окно выбора особых файлов ─────────────────────────
class FilePicker(tk.Toplevel):
    """Список скрытых, системных, read-only и защищённых файлов с ручным выбором."""

    MAX_ITEMS = 5000

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title(T("Особые файлы — выбор для удаления"))
        self.configure(bg=BG)
        w = min(S(1000), self.winfo_screenwidth() - 60)
        h = min(S(660), self.winfo_screenheight() - 100)
        self.geometry(f"{w}x{h}")
        self.minsize(S(780), S(500))
        self.transient(app)

        self.q = queue.Queue()
        self.extra_dirs = []
        self.stop = False
        self.scanning = False
        self.deleting = False
        self.var_force = tk.BooleanVar(value=app.admin)

        self._build()
        decorate_window(self)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(60, self._poll)
        self.rescan()

    def _build(self):
        pad = S(22)
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=pad, pady=(S(18), S(6)))
        tk.Label(head, text=T("📂  Особые файлы"), bg=BG, fg=TEXT,
                 font=(FONT, 18, "bold")).pack(anchor="w")
        WrapLabel(head, bg=BG, fg=MUTED, font=(FONT, 10),
                 text=T("Скрытые, системные, «только чтение» и защищённые файлы в папках очистки. "
                      "Нажмите на строку, чтобы отметить файл; заголовок столбца сортирует список. "
                      "Файлы Windows, Program Files и загрузчика сюда не попадают.")
                 ).pack(fill="x", pady=(S(2), 0))
        self.info = EllipsisLabel(head, text="", bg=BG, fg=ACCENT, font=(FONT, 10, "bold"))
        self.info.pack(fill="x", pady=(S(6), 0))

        bottom = tk.Frame(self, bg=BG)
        bottom.pack(side="bottom", fill="x", padx=pad, pady=(S(8), S(18)))
        btns = tk.Frame(bottom, bg=BG)
        btns.pack(fill="x", pady=(S(10), 0))
        FlatButton(btns, T("Удалить выбранные"), self.delete_selected, bg=RED, hover=RED_HOVER,
                   size=10, padx=16, pady=9).pack(side="right")
        FlatButton(btns, T("🛡 В белый список"), self.to_whitelist, bg=CARD_HOVER,
                   hover=CARD_HOVER2, fg=TEXT, size=10, padx=14, pady=9).pack(
            side="right", padx=(0, S(8)))
        for text, cmd in ((T("Выбрать всё"), lambda: self.ct.select_all()),
                          (T("Снять выбор"), lambda: self.ct.select_none()),
                          (T("+ Добавить папку"), self.add_dir), (T("Обновить"), self.rescan)):
            FlatButton(btns, text, cmd, bg=CARD_HOVER, hover=CARD_HOVER2, fg=TEXT,
                       size=10, padx=14, pady=9).pack(side="left", padx=(0, S(8)))

        opt = tk.Frame(bottom, bg=CARD)
        opt.pack(fill="x")
        Toggle(opt, self.var_force, bg=CARD, enabled=self.app.admin).pack(
            side="left", padx=(S(14), S(10)), pady=S(8))
        box = tk.Frame(opt, bg=CARD)
        box.pack(side="left", fill="x", expand=True)
        EllipsisLabel(box, text=T("Получать разрешение системы при отказе в доступе"), bg=CARD,
                      fg=TEXT if self.app.admin else MUTED,
                      font=(FONT, 10, "bold")).pack(fill="x")
        EllipsisLabel(box, bg=CARD, fg=MUTED, font=(FONT, 9),
                      text=T("Изменяется владелец файла и выдаются права администраторам")
                      if self.app.admin else T("Требуется запуск от администратора")).pack(fill="x")

        self.ct = CheckList(self, on_change=self._update_info, row_h=54, right_w=190)
        self.ct.pack(fill="both", expand=True, padx=pad)

    def _update_info(self):
        items = self.ct.items
        size = sum(items[i]["payload"][1] for i in self.ct.checked if i in items)
        text = T('Найдено: {0}').format(len(items))
        if len(items) >= self.MAX_ITEMS:
            text += T(' (показаны первые {0})').format(self.MAX_ITEMS)
        text += T('   •   Отмечено: {0} ({1})').format(len(self.ct.checked), fmt_size(size))
        if self.scanning:
            text = T("Поиск…   ") + text
        self.info.config(text=text)

    # ---------- поиск ----------
    def _folders(self):
        folders = []
        for cat in CATEGORIES.values():
            if cat.get("special") or cat.get("match"):
                continue
            if cat.get("admin") and not self.app.admin:
                continue
            folders.extend(cat["paths"])
        folders.extend(self.extra_dirs)
        return list(dict.fromkeys(folders))

    def add_dir(self):
        d = filedialog.askdirectory(parent=self, title=T("Папка для поиска особых файлов"))
        if not d:
            return
        d = os.path.normpath(d)
        if is_protected_path(d, is_dir=True):
            messagebox.showwarning(
                T("Папка защищена"),
                T("Эта папка относится к Windows, Program Files или загрузчику.\n"
                "Удаление файлов в ней может сломать систему, поэтому она недоступна."),
                parent=self)
            return
        if d not in self.extra_dirs:
            self.extra_dirs.append(d)
        self.rescan()

    def rescan(self):
        if self.scanning or self.deleting:
            return
        self.scanning = True
        self.ct.clear()
        self._update_info()
        threading.Thread(target=self._scan_worker, args=(self._folders(),),
                         daemon=True).start()

    def _scan_worker(self, folders):
        for path, size, kinds in iter_special_files(folders, self.MAX_ITEMS, lambda: self.stop):
            self.q.put(("item", path, size, kinds))
        self.q.put(("done",))

    # ---------- действия ----------
    def _chosen(self):
        items = self.ct.items
        return [(i, items[i]["payload"][0], items[i]["payload"][1])
                for i in self.ct.checked if i in items]

    def to_whitelist(self):
        chosen = self._chosen()
        if not chosen:
            messagebox.showinfo(T("Особые файлы"), T("Ничего не отмечено."), parent=self)
            return
        set_whitelist(get_whitelist() + [p for _i, p, _s in chosen])
        self.ct.remove([i for i, _p, _s in chosen])
        self._update_info()
        self.app.on_whitelist_changed()

    def delete_selected(self):
        if self.scanning or self.deleting:
            return
        chosen = self._chosen()
        if not chosen:
            messagebox.showinfo(T("Особые файлы"), T("Ничего не отмечено."), parent=self)
            return
        total = sum(c[2] for c in chosen)
        force = self.var_force.get() and self.app.admin
        text = (T('Удалить отмеченные файлы: {0} шт. (≈ {1})?\n\nЭто действие необратимо — файлы не попадут в корзину.').format(len(chosen), fmt_size(total)))
        if force:
            text += (T("\n\nПри отказе в доступе для файла будет изменён владелец "
                     "и выданы права администраторам."))
        if not messagebox.askyesno(T("Подтверждение"), text, parent=self, icon="warning"):
            return
        self.deleting = True
        self.info.config(text=T("Удаление…"))
        threading.Thread(target=self._delete_worker, args=(chosen, force), daemon=True).start()

    def _delete_worker(self, chosen, force):
        budget = {"n": 300}
        done, freed, skipped = [], 0, 0
        for iid, path, size in chosen:
            if is_protected_path(path) or is_self_path(path) or is_whitelisted(path):
                skipped += 1
                continue
            if remove_file(path, force, budget):
                done.append(iid)
                freed += size
            else:
                skipped += 1
        self.q.put(("deleted", done, freed, skipped))

    # ---------- сообщения из потоков ----------
    def _poll(self):
        if self.stop:
            return
        try:
            for _ in range(300):
                msg = self.q.get_nowait()
                if msg[0] == "item":
                    _, path, size, kinds = msg
                    self.ct.add(os.path.basename(path), sub=os.path.dirname(path),
                                right=fmt_size(size), tag=", ".join(kinds),
                                payload=(path, size), keys={"size": size}, mid=True)
                elif msg[0] == "done":
                    self.scanning = False
                    self.ct.sort_by("size", True)  # самые крупные — сверху
                    self._update_info()
                elif msg[0] == "deleted":
                    _, done, freed, skipped = msg
                    self.ct.remove(done)
                    self.deleting = False
                    self._update_info()
                    text = T('Удалено файлов: {0}, освобождено {1}.').format(len(done), fmt_size(freed))
                    if skipped:
                        text += T('\nНе удалось удалить: {0} (заняты или нет доступа).').format(skipped)
                    messagebox.showinfo(T("Особые файлы"), text, parent=self)
                    if not self.app.busy:
                        self.app.start_scan()
        except queue.Empty:
            pass
        if self.scanning:
            self._update_info()
        self.after(60, self._poll)

    def _close(self):
        self.stop = True
        self.app.picker = None
        self.destroy()



# ───────────────────────── Главное окно ─────────────────────────
class CleanerApp(tk.Tk):
    def __init__(self):
        global UI_SCALE, ANIM, FONT_SEMI
        super().__init__()
        UI_SCALE = max(1.0, self.winfo_fpixels("1i") / 96.0)
        ANIM = Animator(self)
        if FONT_SEMI not in tkfont.families(self):
            FONT_SEMI = FONT  # нет Segoe UI Semibold — используем обычный Segoe UI

        self.title(APP_NAME)
        self.configure(bg=BG)
        w = min(S(1000), self.winfo_screenwidth() - 40)
        h = min(S(900), self.winfo_screenheight() - 90)
        self.geometry(f"{w}x{h}")
        self.minsize(min(S(960), self.winfo_screenwidth() - 40), S(640))

        self.q = queue.Queue()
        self.busy = False
        self.game_busy = False
        self.mem_busy = False
        self.apps_loading = False
        self.apps_loaded = False
        self.uninstalling = False
        self.game_on = bool(load_state().get("game"))
        self._rescan = False
        self.picker = None
        self.wl_window = None
        self.admin = is_admin()
        self.chart_size = S(190)
        self.page = None
        self.pages = {}
        self.last_sys = None

        # данные для плавного отображения: цель (t_*) и текущее значение (v_*)
        self.sizes = {}
        self.vars = {}
        self.size_labels = {}
        self.pct_labels = {}
        self.v_size = {k: 0.0 for k in CATEGORIES}
        self.v_seg = {k: 0.0 for k in CATEGORIES}
        self.t_lbl = {k: 0.0 for k in CATEGORIES}
        self.t_seg = {k: 0.0 for k in CATEGORIES}
        self.v_files = self.t_files = 0.0
        self.v_prog = self.t_prog = 0.0
        self._lbl_txt = {}
        self._files_txt = None

        self._style()
        self._build()
        set_app_icon(self)
        decorate_window(self)

        self.monitor = None
        if IS_WIN:
            self.monitor = ResourceMonitor(self.q)
            self.monitor.start()
        self.bind("<Unmap>", lambda e: self._set_active(False) if e.widget is self else None)
        self.bind("<Map>", lambda e: self._set_active(True) if e.widget is self else None)
        self.bind_all("<MouseWheel>", self._on_wheel)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.after(60, self._poll)
        self.after(300, self.start_scan)

    def _set_active(self, value):
        if self.monitor:
            (self.monitor.active.set if value else self.monitor.active.clear)()

    def _on_close(self):
        if getattr(self, "bk_busy", False):
            if not messagebox.askyesno(T("Бэкап"), T("Сейчас создаётся бэкап. Прервать его и выйти?\n\n"
                                                "Незаконченный архив будет удалён.")):
                return
            self.bk_stop.set()
            if self.bk_thread:
                self.bk_thread.join(timeout=5)  # даём потоку удалить «.part»
        if self.monitor:
            self.monitor.stop_flag = True
        self.destroy()

    # ---------- оформление ----------
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Modern.Horizontal.TProgressbar",
                    troughcolor=CARD, background=ACCENT, bordercolor=CARD,
                    lightcolor=ACCENT, darkcolor=ACCENT, thickness=S(10))
        s.configure("Vertical.TScrollbar", background=CARD_HOVER, troughcolor=BG,
                    bordercolor=BG, arrowcolor=MUTED, lightcolor=CARD_HOVER,
                    darkcolor=CARD_HOVER, gripcount=0)
        s.configure("Dark.Treeview", background=CARD, fieldbackground=CARD,
                    foreground=TEXT, bordercolor=CARD, borderwidth=0,
                    rowheight=S(28), font=(FONT, 10))
        s.layout("Dark.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        s.configure("Dark.Treeview.Heading", background=CARD_HOVER, foreground=TEXT,
                    relief="flat", font=(FONT, 10, "bold"), padding=S(6))
        s.map("Dark.Treeview.Heading", background=[("active", CARD_HOVER2)])
        s.map("Dark.Treeview", background=[("selected", SELECTED)],
              foreground=[("selected", TEXT)])

    def _build(self):
        pad = S(28)

        # Шапка
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=pad, pady=(S(18), S(2)))
        self.btn_lang = FlatButton(header, f"🌐  {dict(LANGUAGES)[LANG]}  ▾", self.open_lang_menu,
                                   bg=CARD_HOVER, hover=CARD_HOVER2, fg=TEXT, size=10,
                                   padx=16, pady=8)
        self.btn_lang.pack(side="right")
        self.lang_menu = None
        left = tk.Frame(header, bg=BG)
        left.pack(side="left")
        tk.Label(left, text="🧹  " + APP_NAME, bg=BG, fg=TEXT,
                 font=(FONT, 22, "bold")).pack(anchor="w")
        if self.admin:
            tk.Label(left, text=T("✔ Запущено от администратора"), bg=BG, fg=GREEN,
                     font=(FONT, 10)).pack(anchor="w", pady=(S(2), 0))
            self.btn_unadmin = FlatButton(header, T("🛡  Выйти из режима администратора"),
                                          self.leave_admin, bg=CARD_HOVER, hover=CARD_HOVER2,
                                          fg=TEXT, size=10, padx=16, pady=8)
            self.btn_unadmin.pack(side="right", padx=(0, S(8)))
        else:
            tk.Label(left, text=T("Стандартные права — часть функций ограничена"), bg=BG,
                     fg=MUTED, font=(FONT, 10)).pack(anchor="w", pady=(S(2), 0))
            FlatButton(header, T("🛡  Права администратора"), self.relaunch_admin,
                       bg=CARD_HOVER, hover=CARD_HOVER2, fg=TEXT, size=10,
                       padx=16, pady=8).pack(side="right", padx=(0, S(8)))
        # Порядок справа налево: язык, права администратора, тема 🎨, «О приложении» ℹ
        self.btn_theme = FlatButton(header, "🎨", self.open_theme_menu, bg=CARD_HOVER,
                                    hover=CARD_HOVER2, fg=TEXT, size=10, padx=8, pady=8)
        self.btn_theme.pack(side="right", padx=(0, S(8)))
        Tooltip(self.btn_theme).text = T("Тема оформления")
        self.theme_menu = None
        self.btn_about = FlatButton(header, "ℹ", lambda: self.show_page("about"),
                                    bg=CARD_HOVER, hover=CARD_HOVER2, fg=TEXT, size=10,
                                    padx=8, pady=8)  # высота как у соседних кнопок
        self.btn_about.pack(side="right", padx=(0, S(8)))
        Tooltip(self.btn_about).text = T("О приложении")

        # Вкладки и мини-индикаторы нагрузки
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=pad, pady=(S(10), S(6)))
        self.tabs = Tabs(bar, [("clean", T("🧹  Очистка")), ("perf", T("⚡  Производительность")),
                               ("files", T("📁  Файловый менеджер"))],
                         self.show_page)
        self.tabs.pack(side="left")
        meters = tk.Frame(bar, bg=BG)
        meters.pack(side="right")
        self.mini = {}
        for key in ("CPU", "GPU", "RAM"):
            m = MiniMeter(meters, key)
            m.pack(side="left", padx=(S(12), 0))
            self.mini[key] = m

        self.host = tk.Frame(self, bg=BG)
        self.host.pack(fill="both", expand=True)
        self.pages["clean"] = self._build_clean(self.host)
        self.pages["perf"] = self._build_perf(self.host)
        self.pages["files"] = self._build_files(self.host)
        self.pages["about"] = self._build_about(self.host)
        self.tabs.select("clean")

    def show_page(self, key):
        for p in self.pages.values():
            p.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        self.page = key
        self.top_page = key
        if key == "about":  # раздел открыт кнопкой в шапке: вкладки снизу не подсвечиваем
            self.tabs.select(None, call=False)
            self.btn_about.set_style(ACCENT, ACCENT_HOVER, DARK)
        else:
            self.btn_about.set_style(CARD_HOVER, CARD_HOVER2, TEXT)
        if key == "files":  # self.page = видимый раздел: "apps" или "backup"
            self.show_sub(self.files_sub)
        if key == "perf" and self.last_sys:
            self._apply_gauges(*self.last_sys)

    # ======================= Раздел «О приложении» =======================
    def _build_about(self, parent):
        page = tk.Frame(parent, bg=BG)

        top = tk.Frame(page, bg=CARD)
        top.pack(fill="x", padx=S(28), pady=S(8))
        if HAS_PIL:
            self._about_icon = ImageTk.PhotoImage(app_icon_image(S(72)))
            tk.Label(top, image=self._about_icon, bg=CARD).pack(
                side="left", anchor="n", padx=(S(20), S(16)), pady=S(18))
        info = tk.Frame(top, bg=CARD)
        info.pack(side="left", fill="both", expand=True, padx=(0 if HAS_PIL else S(20), S(20)),
                  pady=S(16))
        head = tk.Frame(info, bg=CARD)
        head.pack(fill="x")
        tk.Label(head, text=APP_NAME, bg=CARD, fg=TEXT, font=(FONT, 18, "bold")).pack(side="left")
        tk.Label(head, text=T("Версия {0}").format(APP_VERSION), bg=CARD, fg=MUTED,
                 font=(FONT, 10)).pack(side="left", padx=S(12), pady=(S(8), 0))
        WrapLabel(info, bg=CARD, fg=TEXT, font=(FONT, 10),
                  text=T("Бесплатная программа для Windows, которая помогает держать компьютер "
                         "в порядке: освобождает место на диске, ускоряет систему, удаляет "
                         "ненужные программы и сохраняет важные файлы и настройки в резервную "
                         "копию.")).pack(fill="x", pady=(S(6), 0))

        feat = self._card(page, T("ВОЗМОЖНОСТИ"))
        for line in (T("🧹  Очистка — временные файлы, кэш браузеров, корзина, особые файлы и "
                       "белый список"),
                     T("⚡  Производительность — нагрузка CPU, GPU и RAM, очистка памяти и "
                       "игровой режим"),
                     T("📦  Программы — удаление программ, игр и приложений Microsoft Store"),
                     T("💾  Бэкап — архив .zip с файлами и настройками в один клик")):
            WrapLabel(feat, text=line, bg=CARD, fg=TEXT, font=(FONT, 10)).pack(
                fill="x", padx=S(20), pady=(S(6), 0))
        tk.Frame(feat, bg=CARD, height=S(12)).pack()

        fb = self._card(page, T("ОБРАТНАЯ СВЯЗЬ"))
        WrapLabel(fb, bg=CARD, fg=TEXT, font=(FONT, 10),
                  text=T("Нашли ошибку или есть идея, как сделать программу лучше? Напишите "
                         "мне — буду рад любому отзыву.")).pack(fill="x", padx=S(20), pady=(S(6), 0))
        links = tk.Frame(fb, bg=CARD)
        links.pack(fill="x", padx=S(20), pady=(S(10), S(4)))
        row = None
        for i, (title, handle, url) in enumerate(SOCIAL_LINKS):
            if i % 3 == 0:  # не больше трёх кнопок в строке — длинные адреса не обрезаются
                row = tk.Frame(links, bg=CARD)
                row.pack(fill="x")
            b = FlatButton(row, f"{title}   {handle}", lambda u=url: self.open_link(u),
                           bg=CARD_HOVER, hover=CARD_HOVER2, fg=TEXT, size=10, padx=16, pady=8)
            b.pack(side="left", padx=(0, S(8)), pady=(0, S(6)))
        sysrow = tk.Frame(fb, bg=CARD)
        sysrow.pack(fill="x", padx=S(20), pady=(S(4), S(16)))
        FlatButton(sysrow, T("📋  Скопировать данные о системе"), self.copy_system_info,
                   bg=CARD, hover=CARD_HOVER, fg=MUTED, size=9, padx=12, pady=6).pack(side="left")
        self.about_status = tk.Label(sysrow, text="", bg=CARD, fg=GREEN, font=(FONT, 9))
        self.about_status.pack(side="left", padx=S(10))

        tk.Label(page, text=f"© {time.strftime('%Y')} {APP_NAME}  •  {self.system_info()}",
                 bg=BG, fg=MUTED, font=(FONT, 9)).pack(side="bottom", pady=S(12))
        return page

    def system_info(self):
        """Строка для сообщений об ошибках: версия программы, Windows, Python."""
        build = "exe" if FROZEN else "py"
        return (f"{APP_NAME} {APP_VERSION} ({build}, {LANG})  •  Windows {platform.version()}  •  "
                f"Python {platform.python_version()} {struct_bits()}-bit")

    def copy_system_info(self):
        self.clipboard_clear()
        self.clipboard_append(self.system_info())
        self.about_status.config(text=T("Скопировано — вставьте в сообщение об ошибке"))
        self.after(4000, lambda: self.about_status.config(text=""))

    def open_link(self, url):
        try:
            if IS_WIN:
                os.startfile(url)
            else:
                webbrowser.open(url)
        except OSError as e:
            messagebox.showerror(APP_NAME, T("Не удалось открыть ссылку:\n{0}").format(e))

    # ======================= Раздел «Файловый менеджер» =======================
    def _build_files(self, parent):
        """Раздел с подвкладками «Программы» и «Бэкап»."""
        page = tk.Frame(parent, bg=BG)
        bar = tk.Frame(page, bg=BG)
        bar.pack(fill="x", padx=S(28), pady=(S(2), S(4)))
        self.sub_tabs = Tabs(bar, [("apps", T("📦  Программы")), ("backup", T("💾  Бэкап"))],
                             self.show_sub, size=9, padx=14, pady=6, active=CARD_HOVER2,
                             active_hover=CARD_HOVER2, active_fg=TEXT)
        self.sub_tabs.pack(side="left")
        self.files_host = tk.Frame(page, bg=BG)
        self.files_host.pack(fill="both", expand=True)
        self.sub_pages = {"apps": self._build_apps(self.files_host),
                          "backup": self._build_backup(self.files_host)}
        self.files_sub = "apps"
        self.sub_tabs.select("apps", call=False)
        return page

    def show_sub(self, key):
        self.files_sub = key
        self.sub_tabs.select(key, call=False)
        for p in self.sub_pages.values():
            p.pack_forget()
        self.sub_pages[key].pack(fill="both", expand=True)
        self.page = key
        if key == "apps" and not self.apps_loaded:
            self.load_apps()

    def _on_wheel(self, e):
        """Прокрутка списка категорий — только когда курсор над ним."""
        if self.page != "clean":
            return
        w = self.winfo_containing(e.x_root, e.y_root)
        while w is not None:
            if w is self.list_holder:
                self.list_canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")
                return
            w = getattr(w, "master", None)

    # ======================= Страница «Очистка» =======================
    def _build_clean(self, parent):
        page = tk.Frame(parent, bg=BG)
        pad = S(28)

        summary = tk.Frame(page, bg=CARD)
        summary.pack(fill="x", padx=pad, pady=S(8))
        self.chart = tk.Canvas(summary, width=self.chart_size, height=self.chart_size,
                               bg=CARD, highlightthickness=0)
        self.chart.pack(side="left", padx=(S(20), S(10)), pady=S(14))
        stats = tk.Frame(summary, bg=CARD)
        stats.pack(side="left", fill="both", expand=True, padx=(S(10), S(20)), pady=S(14))
        tk.Label(stats, text=T("ОБЩАЯ СТАТИСТИКА"), bg=CARD, fg=MUTED,
                 font=(FONT, 9, "bold")).pack(anchor="w")

        def stat(caption, color, size=16, ellipsis=False):
            tk.Label(stats, text=caption, bg=CARD, fg=MUTED,
                     font=(FONT, 9)).pack(anchor="w", pady=(S(10), 0))
            if ellipsis:  # длинный текст обрезается «…», полный — в подсказке
                lbl = EllipsisLabel(stats, text="—", bg=CARD, fg=color,
                                    font=(FONT, size, "bold"))
                lbl.pack(fill="x")
            else:
                lbl = tk.Label(stats, text="—", bg=CARD, fg=color, justify="left",
                               font=(FONT, size, "bold"))
                lbl.pack(anchor="w")
            return lbl

        self.stat_files = stat(T("Файлов к удалению"), ACCENT)
        self.stat_cats = stat(T("Выбрано категорий"), GREEN)
        self.stat_top = stat(T("Больше всего места занимает"), AMBER, 12, True)

        # нижняя панель пакуется раньше списка — всегда видна
        bottom = tk.Frame(page, bg=BG)
        bottom.pack(side="bottom", fill="x", padx=pad, pady=(0, S(14)))

        buttons = tk.Frame(bottom, bg=BG)
        buttons.pack(side="bottom", fill="x", pady=(S(10), 0))
        self.btn_clean = FlatButton(buttons, T("Очистить"), self.confirm_clean, padx=20)
        self.btn_clean.pack(side="right")
        self.btn_scan = FlatButton(buttons, T("Сканировать"), self.start_scan,
                                   bg=CARD_HOVER, hover=CARD_HOVER2, fg=TEXT, padx=16)
        self.btn_scan.pack(side="left")
        self.btn_pick = FlatButton(buttons, T("📂  Особые файлы"), self.open_picker,
                                   bg=CARD_HOVER, hover=CARD_HOVER2, fg=TEXT, padx=16)
        self.btn_pick.pack(side="left", padx=(S(8), 0))
        self.btn_wl = FlatButton(buttons, "", self.open_whitelist,
                                 bg=CARD_HOVER, hover=CARD_HOVER2, fg=TEXT, padx=16)
        self.btn_wl.pack(side="left", padx=(S(8), 0))
        self._refresh_wl_button()

        prog = tk.Frame(bottom, bg=BG)
        prog.pack(side="bottom", fill="x", pady=(S(10), 0))
        self.progress = SmoothProgress(prog)
        self.progress.pack(fill="x")
        self.status = EllipsisLabel(prog, text=T("Готов к работе"), bg=BG, fg=MUTED,
                                    font=(FONT, 10))
        self.status.pack(fill="x", pady=(S(6), 0))

        opts = tk.Frame(bottom, bg=CARD)
        opts.pack(side="bottom", fill="x", pady=(S(8), 0))
        self.var_hidden = tk.BooleanVar(value=False)
        self.var_force = tk.BooleanVar(value=False)
        self._option(opts, T("Удалять скрытые и системные файлы"),
                     T("Файлы с атрибутами «скрытый» и «системный» внутри выбранных папок"),
                     self.var_hidden, True, self.on_hidden_toggle)
        self._option(opts, T("Принудительное удаление защищённых файлов"),
                     T("Получение доступа через права администратора (takeown / icacls)")
                     if self.admin else T("Требуется запуск от администратора"),
                     self.var_force, self.admin, None)

        # список категорий с прокруткой
        self.list_holder = tk.Frame(page, bg=BG)
        self.list_holder.pack(fill="both", expand=True, padx=pad)
        self.list_canvas = tk.Canvas(self.list_holder, bg=BG, highlightthickness=0,
                                     height=S(160))
        sb = ttk.Scrollbar(self.list_holder, orient="vertical", command=self.list_canvas.yview)
        self.list_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.list_canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(self.list_canvas, bg=BG)
        win = self.list_canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: self.list_canvas.configure(
            scrollregion=self.list_canvas.bbox("all")))
        self.list_canvas.bind("<Configure>",
                              lambda e: self.list_canvas.itemconfigure(win, width=e.width))

        for key, cat in CATEGORIES.items():
            locked = bool(cat.get("admin")) and not self.admin
            row = tk.Frame(inner, bg=CARD)
            row.pack(fill="x", pady=S(2), padx=(0, S(6)))
            tk.Frame(row, bg=COLORS[key], width=S(5)).pack(side="left", fill="y")
            var = tk.BooleanVar(value=not locked)
            self.vars[key] = var
            Toggle(row, var, command=self.refresh_view, bg=CARD,
                   enabled=not locked).pack(side="left", padx=(S(12), S(10)), pady=S(9))
            pct = tk.Label(row, text="", bg=CARD, fg=COLORS[key], width=5, anchor="e",
                           font=(FONT, 10, "bold"))
            pct.pack(side="right", padx=(0, S(14)))
            self.pct_labels[key] = pct
            lbl = tk.Label(row, text="…", bg=CARD, fg=TEXT, width=9, anchor="e",
                           font=(FONT, 11, "bold"))
            lbl.pack(side="right", padx=S(6))  # фиксированная ширина: числа не «прыгают»
            self.size_labels[key] = lbl
            info = tk.Frame(row, bg=CARD)
            info.pack(side="left", fill="x", expand=True)
            EllipsisLabel(info, text=T(cat["title"]), bg=CARD, fg=MUTED if locked else TEXT,
                          font=(FONT, 11, "bold")).pack(fill="x")
            desc = T(cat["desc"]) + (T("  •  нужны права администратора") if locked else "")
            EllipsisLabel(info, text=desc, bg=CARD, fg=MUTED, font=(FONT, 9)).pack(fill="x")
        return page

    def _option(self, parent, title, desc, var, enabled, command):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x")
        Toggle(row, var, command=command, bg=CARD, enabled=enabled).pack(
            side="left", padx=(S(14), S(10)), pady=S(8))
        info = tk.Frame(row, bg=CARD)
        info.pack(side="left", fill="x", expand=True)
        EllipsisLabel(info, text=title, bg=CARD, fg=TEXT if enabled else MUTED,
                      font=(FONT, 10, "bold")).pack(fill="x")
        EllipsisLabel(info, text=desc, bg=CARD, fg=MUTED, font=(FONT, 9)).pack(fill="x")

    # ---------- плавное отображение данных ----------
    def refresh_view(self):
        """Пересчитывает цели для анимации: диаграмма, числа и проценты меняются плавно."""
        selected = [k for k, v in self.vars.items() if v.get()]
        get = lambda k: self.sizes.get(k, (0, 0))
        total = sum(get(k)[0] for k in selected)
        self.t_files = float(sum(get(k)[1] for k in selected)) if self.sizes else 0.0
        self.t_lbl = {k: float(get(k)[0]) for k in CATEGORIES}
        self.t_seg = {k: float(get(k)[0]) if k in selected else 0.0 for k in CATEGORIES}

        self.stat_cats.config(text=T('{0} из {1}').format(len(selected), len(CATEGORIES)))
        top = max(selected, key=lambda k: get(k)[0], default=None)
        has_top = top is not None and get(top)[0] > 0
        self.stat_top.config(
            text=f"{T(CATEGORIES[top]['title'])} — {fmt_size(get(top)[0])}" if has_top else "—")
        for key, lbl in self.pct_labels.items():
            size = get(key)[0]
            if key in selected and total > 0 and size > 0:
                p = size / total * 100
                lbl.config(text="<1%" if p < 1 else f"{p:.0f}%")
            else:
                lbl.config(text="")
        ANIM.run("view", self._view_step)

    def _view_step(self, now, dt):
        moving = False
        for k in CATEGORIES:
            a = approach(self.v_size[k], self.t_lbl[k], dt, 10.0, 0.5)
            b = approach(self.v_seg[k], self.t_seg[k], dt, 10.0, 0.5)
            if a != self.t_lbl[k] or b != self.t_seg[k]:
                moving = True
            self.v_size[k], self.v_seg[k] = a, b
            txt = fmt_size(a) if k in self.sizes else "…"
            if self._lbl_txt.get(k) != txt:
                self.size_labels[k].config(text=txt)
                self._lbl_txt[k] = txt
        f = approach(self.v_files, self.t_files, dt, 10.0, 0.5)
        if f != self.t_files:
            moving = True
        self.v_files = f
        ftxt = f"{int(round(f)):,}".replace(",", " ") if self.sizes else "—"
        if ftxt != self._files_txt:
            self.stat_files.config(text=ftxt)
            self._files_txt = ftxt
        p = approach(self.v_prog, self.t_prog, dt, 9.0, 0.05)
        if p != self.t_prog:
            moving = True
        if abs(p - self.v_prog) > 1e-6:
            self.progress.config(value=p)
        self.v_prog = p
        self.draw_chart()
        return moving

    def draw_chart(self):
        c = self.chart
        c.delete("all")
        size = self.chart_size
        cx = cy = size / 2
        vals = [(COLORS[k], self.v_seg[k]) for k in CATEGORIES if self.v_seg[k] > 0.5]
        total = sum(v for _, v in vals)
        segs = [(color, v / total * 360) for color, v in vals] if total > 0 else []
        draw_ring(c, size, S(24), S(6), segs, CARD, CARD_HOVER,
                  gap=2.0 if len(segs) > 1 else 0.0)
        center = fmt_size(total) if self.sizes else "…"
        c.create_text(cx, cy - S(8), text=center, fill=TEXT, font=(FONT, 17, "bold"))
        c.create_text(cx, cy + S(16), text=T("к очистке"), fill=MUTED, font=(FONT, 9))

    # ---------- сканирование ----------
    def _set_busy(self, value):
        self.busy = value
        self.btn_scan.set_enabled(not value)
        self.btn_clean.set_enabled(not value)

    def on_hidden_toggle(self):
        if self.busy:
            self._rescan = True
        else:
            self.start_scan()

    def on_whitelist_changed(self):
        self._refresh_wl_button()
        if self.busy:
            self._rescan = True
        else:
            self.start_scan()

    def _refresh_wl_button(self):
        n = len(get_whitelist())
        self.btn_wl.config(text=T("🛡  Белый список") + (f" ({n})" if n else ""))

    def start_scan(self):
        if self.busy:
            return
        self._set_busy(True)
        self.sizes.clear()
        self.v_prog = self.t_prog = 0.0
        self.progress.config(value=0)
        self.status.config(text=T("Сканирование…"), fg=MUTED)
        self.refresh_view()
        threading.Thread(target=self._scan_worker, args=(self.var_hidden.get(),),
                         daemon=True).start()

    def _scan_worker(self, include_hidden):
        keys = list(CATEGORIES)
        done = 0
        with cf.ThreadPoolExecutor(max_workers=4) as ex:  # папки сканируются параллельно
            futs = {ex.submit(scan_category, CATEGORIES[k], include_hidden): k for k in keys}
            for f in cf.as_completed(futs):
                try:
                    size, count = f.result()
                except Exception:
                    size = count = 0
                done += 1
                self.q.put(("scan", futs[f], size, count, done / len(keys) * 100))
        self.q.put(("scan_done",))

    # ---------- очистка ----------
    def confirm_clean(self):
        if self.busy:
            return
        selected = [k for k, v in self.vars.items() if v.get()]
        if not selected:
            messagebox.showinfo(APP_NAME, T("Ничего не выбрано."))
            return
        total = sum(self.sizes.get(k, (0, 0))[0] for k in selected)
        hidden, force = self.var_hidden.get(), self.var_force.get()
        text = T('Удалить выбранные файлы (≈ {0})?\n\n').format(fmt_size(total))
        text += T("Файлы, которые сейчас используются, будут пропущены.")
        wl = len(get_whitelist())
        if wl:
            text += T('\n• Исключены белым списком: {0}.').format(wl)
        if hidden:
            text += T("\n• Будут удалены скрытые и системные файлы в выбранных папках.")
        if force:
            text += (T("\n• Для защищённых файлов будет изменён владелец и выданы права "
                     "администраторам."))
        if not messagebox.askyesno(T("Подтверждение"), text):
            return
        self._set_busy(True)
        self.v_prog = self.t_prog = 0.0
        self.progress.config(value=0)
        self.status.config(text=T("Очистка…"), fg=MUTED)
        threading.Thread(target=self._clean_worker, args=(selected, hidden, force),
                         daemon=True).start()

    def _clean_worker(self, keys, hidden, force):
        freed_total = skipped_total = 0
        budget = {"n": 300}  # ограничение числа «принудительных» попыток за запуск
        n = len(keys)
        for i, key in enumerate(keys):
            self.q.put(("status", T('Очищаю: {0}…').format(T(CATEGORIES[key]['title']))))

            def prog(frac, i=i):
                self.q.put(("progress", (i + frac) / n * 100))

            freed, _removed, skipped = clean_category(
                CATEGORIES[key], hidden, force and self.admin, budget, prog)
            freed_total += freed
            skipped_total += skipped
        self.q.put(("clean_done", freed_total, skipped_total))

    # ---------- окна ----------
    def open_picker(self):
        if self.picker is not None and self.picker.winfo_exists():
            self.picker.lift()
            self.picker.focus_force()
            return
        self.picker = FilePicker(self)

    def open_whitelist(self):
        if self.wl_window is not None and self.wl_window.winfo_exists():
            self.wl_window.lift()
            self.wl_window.focus_force()
            return
        self.wl_window = WhitelistWindow(self)

    def relaunch_admin(self):
        try:
            exe, params = self_command()
            shell = ctypes.windll.shell32.ShellExecuteW
            shell.restype = ctypes.c_void_p
            rc = shell(None, "runas", exe, params, None, 1) or 0
            if rc > 32:
                self._on_close()
        except Exception as e:
            messagebox.showerror(APP_NAME, T('Не удалось запросить права:\n{0}').format(e))

    def _busy_any(self):
        return bool(self.busy or self.uninstalling or self.game_busy or self.mem_busy
                    or getattr(self, "bk_busy", False))

    def leave_admin(self):
        """Перезапуск с обычными правами пользователя (выход из режима администратора)."""
        if self._busy_any():
            messagebox.showinfo(T("Режим администратора"),
                                T("Сейчас выполняется операция (сканирование, очистка, удаление "
                                  "программ или бэкап).\nДождитесь её окончания."))
            return
        if not messagebox.askyesno(T("Режим администратора"),
                                   T("Программа перезапустится с обычными правами (без "
                                     "администратора). Продолжить?")):
            return
        name = os.path.basename(sys.executable).lower()
        before = {pid for pid, n in list_processes() if n.lower() == name}
        try:
            launch_unelevated()
        except Exception as e:
            messagebox.showerror(T("Режим администратора"),
                                 T("Не удалось запустить программу с обычными правами:\n{0}")
                                 .format(e))
            return
        self.btn_unadmin.set_enabled(False)
        self.btn_unadmin.config(text=T("Перезапускаю с обычными правами…"))
        deadline = time.time() + 10

        def wait_new_copy():
            """Закрываемся, только когда новая копия появилась — иначе остаёмся открытыми."""
            started = not FROZEN or any(n.lower() == name and pid not in before
                                        for pid, n in list_processes())
            if started:
                self.after(800, self._on_close)  # даём новой копии показать окно
            elif time.time() < deadline:
                self.after(300, wait_new_copy)
            else:
                self.btn_unadmin.set_enabled(True)
                self.btn_unadmin.config(text=T("🛡  Выйти из режима администратора"))
                messagebox.showwarning(
                    T("Режим администратора"),
                    T("Новая копия программы не запустилась, поэтому это окно остаётся "
                      "открытым.\n\nЗапустите программу заново обычным способом (без «Запуск "
                      "от имени администратора»)."))

        self.after(300, wait_new_copy)

    def open_lang_menu(self):
        """Выпадающий список языков под кнопкой 🌐."""
        if self.lang_menu is not None:
            self.lang_menu.close()
            return
        self.lang_menu = Dropdown(self.btn_lang, LANGUAGES, LANG, self.switch_language,
                                  on_close=lambda: setattr(self, "lang_menu", None))

    def open_theme_menu(self):
        """Выпадающий список тем под кнопкой 🎨 — с кружками-образцами цветов."""
        if self.theme_menu is not None:
            self.theme_menu.close()
            return
        items = [(k, T(t["title"]), (t["bg"], t["accent"])) for k, t in THEMES.items()]
        self.theme_menu = Dropdown(self.btn_theme, items, THEME, self.switch_theme,
                                   on_close=lambda: setattr(self, "theme_menu", None))

    def _switch_blocked(self, title):
        """Во время долгих операций интерфейс не перестраиваем — они пишут в его виджеты."""
        picker_busy = self.picker is not None and (self.picker.deleting or self.picker.scanning)
        if self._busy_any() or self.apps_loading or picker_busy:
            messagebox.showinfo(title, T("Сейчас выполняется операция (сканирование, очистка, "
                                         "удаление программ или бэкап).\nДождитесь её окончания."))
            return True
        return False

    def switch_theme(self, theme):
        """Смена темы без перезапуска: новые цвета + перестройка интерфейса."""
        if theme == THEME or self._switch_blocked(T("Тема оформления")):
            return
        st = load_state()
        st["theme"] = theme
        save_state(st)
        self._smooth_rebuild(lambda: apply_theme(theme))

    def switch_language(self, lang):
        """Смена языка без перезапуска: новые тексты + перестройка интерфейса."""
        if lang == LANG or self._switch_blocked(T("Язык")):
            return
        st = load_state()
        st["lang"] = lang
        save_state(st)
        self._smooth_rebuild(lambda: apply_language(lang))

    # ---------- перестройка интерфейса на лету ----------
    def _set_alpha(self, a):
        try:
            self.attributes("-alpha", max(0.0, min(1.0, a)))
        except tk.TclError:
            pass

    def _smooth_rebuild(self, apply):
        """Окно чуть «приглушается», интерфейс перестраивается и плавно проявляется снова."""
        dim, t_out, t_in = 0.25, 0.09, 0.16
        t0 = time.perf_counter()

        def fade_out(now, _dt):
            t = min(1.0, (now - t0) / t_out)
            self._set_alpha(1.0 - (1.0 - dim) * t)
            if t < 1.0:
                return True
            self.after(1, swap)
            return False

        def swap():
            apply()
            self.rebuild_ui()
            self.update_idletasks()
            t1 = time.perf_counter()

            def fade_in(now, _dt):
                t = ease_out((now - t1) / t_in)
                self._set_alpha(dim + (1.0 - dim) * t)
                return t < 1.0

            ANIM.run("ui_fade", fade_in)

        ANIM.run("ui_fade", fade_out)

    def rebuild_ui(self):
        """Пересоздаёт все виджеты в текущей теме и на текущем языке, сохраняя состояние:
        открытый раздел, результаты сканирования, переключатели, список программ и бэкап."""
        for w in (self.picker, self.wl_window):  # дочерние окна просто закрываем
            if w is not None:
                try:
                    w._close()
                except tk.TclError:
                    pass
        if getattr(self, "_bk_save_job", None):  # несохранённые поля бэкапа — сохраняем сейчас
            self.after_cancel(self._bk_save_job)
            self._bk_fields_commit()
        keep = {
            "page": getattr(self, "top_page", "clean"),
            "sub": getattr(self, "files_sub", "apps"),
            "cats": {k: v.get() for k, v in self.vars.items()},
            "hidden": self.var_hidden.get(), "force": self.var_force.get(),
            "deep": self.var_deep.get(), "quiet": self.var_quiet.get(),
            "apps": [it for _iid, it in self.apps_iids] if self.apps_loaded else None,
            "apps_sort": self.apps_sort, "apps_gen": self.apps_gen,
            "bk_last": getattr(self, "bk_last", None),
            "status_done": bool(self.sizes),
        }
        for child in self.winfo_children():
            child.destroy()
        self.pages = {}
        self._lbl_txt = {}
        self._files_txt = None
        self.configure(bg=BG)
        self._style()
        self._build()
        style_window(self)  # заголовок и рамка окна Windows — в цвет новой темы

        for k, v in keep["cats"].items():
            if k in self.vars and self.vars[k].get() != v:
                self.vars[k].set(v)
        self.var_hidden.set(keep["hidden"])
        self.var_force.set(keep["force"])
        self.var_deep.set(keep["deep"])
        self.var_quiet.set(keep["quiet"])
        self.bk_last = keep["bk_last"]
        self.apps_gen = keep["apps_gen"] + 1  # старые потоки значков сами остановятся
        self.apps_sort = keep["apps_sort"]
        self._style_sort_buttons()
        if keep["apps"] is not None:
            for item in keep["apps"]:
                self._handle(("app", item))
            self._handle(("apps_done",))
        self.v_size = {k: 0.0 for k in CATEGORIES}  # диаграмма и числа «доедут» анимацией
        self.v_seg = {k: 0.0 for k in CATEGORIES}
        self.v_files = 0.0
        self.refresh_view()
        if keep["status_done"]:
            self.status.config(text=T("Сканирование завершено"), fg=GREEN)
        self.files_sub = keep["sub"]
        self.tabs.select(keep["page"]) if keep["page"] in self.tabs.buttons \
            else self.show_page(keep["page"])
        if self.last_sys:
            self._handle(("sys",) + tuple(self.last_sys))

    # ======================= Страница «Производительность» =======================
    def _card(self, parent, title):
        card = tk.Frame(parent, bg=CARD)
        card.pack(fill="x", padx=S(28), pady=S(8))
        tk.Label(card, text=title, bg=CARD, fg=MUTED, font=(FONT, 9, "bold")).pack(
            anchor="w", padx=S(20), pady=(S(14), 0))
        return card

    def _build_perf(self, parent):
        page = tk.Frame(parent, bg=BG)

        card = self._card(page, T("НАГРУЗКА НА СИСТЕМУ"))
        row = tk.Frame(card, bg=CARD)
        row.pack(pady=(S(6), S(12)))
        self.g_cpu = RingGauge(row, T("Процессор"))
        self.g_gpu = RingGauge(row, T("Видеокарта"))
        self.g_ram = RingGauge(row, T("Память"))
        for g in (self.g_cpu, self.g_gpu, self.g_ram):
            g.pack(side="left", padx=S(34))

        mem = self._card(page, T("ОЧИСТКА ОПЕРАТИВНОЙ ПАМЯТИ"))
        WrapLabel(mem, bg=CARD, fg=TEXT, font=(FONT, 10),
                  text=T("Освобождает неиспользуемую память пользовательских программ (рабочие наборы). "
                       "Не затрагиваются: процессы и службы Windows, оболочка Explorer, антивирус, "
                       "античиты, процессы других сессий и сама программа.")
                  ).pack(fill="x", padx=S(20), pady=(S(6), S(2)))
        self.var_deep = tk.BooleanVar(value=False)
        deep_row = tk.Frame(mem, bg=CARD)
        deep_row.pack(fill="x", padx=S(6))
        Toggle(deep_row, self.var_deep, bg=CARD, enabled=self.admin).pack(
            side="left", padx=(S(14), S(10)), pady=S(8))
        dbox = tk.Frame(deep_row, bg=CARD)
        dbox.pack(side="left", fill="x", expand=True)
        EllipsisLabel(dbox, text=T("Глубокая очистка: сбросить кэш памяти Windows"), bg=CARD,
                      fg=TEXT if self.admin else MUTED,
                      font=(FONT, 10, "bold")).pack(fill="x")
        EllipsisLabel(dbox, bg=CARD, fg=MUTED, font=(FONT, 9),
                      text=T("Список ожидания; программы могут ненадолго открываться медленнее")
                      if self.admin else T("Требуется запуск от администратора")).pack(fill="x")
        act = tk.Frame(mem, bg=CARD)
        act.pack(fill="x", padx=S(20), pady=(S(4), S(14)))
        self.btn_mem = FlatButton(act, T("🧠  Очистить память"), self.clean_memory, size=10,
                                  padx=18, pady=9)
        self.btn_mem.pack(side="left")
        self.mem_result = WrapLabel(act, text="", bg=CARD, fg=MUTED, font=(FONT, 10))
        self.mem_result.pack(side="left", fill="x", expand=True, padx=S(14))

        gm = self._card(page, T("ИГРОВОЙ РЕЖИМ"))
        WrapLabel(gm, bg=CARD, fg=TEXT, font=(FONT, 10),
                  text=T("Схема питания «Максимальная производительность», Game Mode Windows, "
                       "отключение фоновой записи игр, прозрачности и анимаций. "
                       "Повторное нажатие возвращает все настройки.")
                  ).pack(fill="x", padx=S(20), pady=(S(6), S(8)))
        grow = tk.Frame(gm, bg=CARD)
        grow.pack(fill="x", padx=S(20), pady=(0, S(14)))
        self.btn_game = FlatButton(grow, "", self.toggle_game_mode, size=10, padx=18, pady=9)
        self.btn_game.pack(side="left")
        self._refresh_game_button()
        return page

    def _apply_gauges(self, cpu, gpu, load, total, avail):
        self.g_cpu.set(cpu, "")
        self.g_gpu.set(gpu, "" if gpu is not None else T("нет данных"))
        self.g_ram.set(load, f"{fmt_gb(total - avail)} / {fmt_gb(total)}" if total else "")

    # ---------- память ----------
    def clean_memory(self):
        if self.mem_busy or not IS_WIN:
            return
        deep = self.var_deep.get() and self.admin
        text = (T("Освободить память пользовательских программ?\n\n"
                "Критические процессы Windows, службы, антивирус и античиты затронуты не будут."))
        if deep:
            text += T("\n\nДополнительно будет сброшен кэш памяти Windows.")
        if not messagebox.askyesno(T("Очистка памяти"), text):
            return
        self.mem_busy = True
        self.btn_mem.set_enabled(False)
        self.mem_result.config(text=T("Выполняю…"), fg=MUTED)
        threading.Thread(target=self._mem_worker, args=(deep,), daemon=True).start()

    def _mem_worker(self, deep):
        try:
            res = clean_working_set(deep)
        except Exception as e:
            res = {"error": str(e)}
        self.q.put(("mem_done", res))

    # ---------- игровой режим ----------
    def _refresh_game_button(self):
        if self.game_on:
            self.btn_game.config(text=T("🎮  Игровой режим: ВКЛ"))
            self.btn_game.set_style(GREEN, GREEN_HOVER, DARK)
        else:
            self.btn_game.config(text=T("🎮  Игровой режим: ВЫКЛ"))
            self.btn_game.set_style(CARD_HOVER, CARD_HOVER2, TEXT)

    def toggle_game_mode(self):
        if self.game_busy:
            return
        if not IS_WIN:
            messagebox.showinfo(T("Игровой режим"), T("Доступно только в Windows."))
            return
        turn_on = not self.game_on
        if turn_on and not messagebox.askyesno(
                T("Игровой режим"),
                T("Будут применены настройки для максимальной производительности:\n\n"
                "• схема питания «Максимальная производительность»;\n"
                "• Игровой режим Windows включён, фоновая запись игр отключена;\n"
                "• прозрачность, анимации и визуальные эффекты отключены;\n"
                "• отключено энергосбережение процессов (нужны права администратора).\n\n"
                "Повторное нажатие кнопки вернёт все настройки как были. Включить?")):
            return
        self.game_busy = True
        self.btn_game.set_enabled(False)
        self.mem_result.config(
            text=T("Применяю настройки…") if turn_on else T("Возвращаю прежние настройки…"), fg=MUTED)
        threading.Thread(target=self._game_worker, args=(turn_on, self.admin),
                         daemon=True).start()

    def _game_worker(self, turn_on, admin):
        try:
            ok, lines = game_mode_on(admin) if turn_on else game_mode_off()
        except Exception as e:
            ok, lines = False, [T('Ошибка: {0}').format(e)]
        self.q.put(("game_done", turn_on, ok, lines))

    # ======================= Страница «Программы» =======================
    def _make_search(self, parent, placeholder):
        """Поле поиска с подсказкой внутри. Значение попадает в self.var_search."""
        box = tk.Frame(parent, bg=CARD)
        ent = tk.Entry(box, width=26, bg=CARD, fg=MUTED, insertbackground=TEXT,
                       relief="flat", font=(FONT, 10), highlightthickness=0)
        ent.pack(side="left", ipady=S(6), padx=S(12))
        state = {"ph": True}
        ent.insert(0, placeholder)

        def focus_in(_e):
            if state["ph"]:
                ent.delete(0, "end")
                ent.config(fg=TEXT)
                state["ph"] = False

        def focus_out(_e):
            if not ent.get():
                ent.insert(0, placeholder)
                ent.config(fg=MUTED)
                state["ph"] = True
                self.var_search.set("")

        def key(_e):
            if not state["ph"]:
                self.var_search.set(ent.get())

        ent.bind("<FocusIn>", focus_in)
        ent.bind("<FocusOut>", focus_out)
        ent.bind("<KeyRelease>", key)
        return box

    def _build_apps(self, parent):
        page = tk.Frame(parent, bg=BG)
        pad = S(28)
        self.icon_px = S(26)
        self.apps_gen = 0      # номер загрузки списка: старые потоки значков сами останавливаются
        self.apps_iids = []
        self.apps_sort = "name"
        self.var_search = tk.StringVar()
        self.var_search.trace_add("write", lambda *a: self._apps_filter())

        top = tk.Frame(page, bg=BG)
        top.pack(fill="x", padx=pad, pady=(S(6), S(8)))
        tk.Label(top, text=T("Установленные программы, игры и приложения"), bg=BG, fg=TEXT,
                 font=(FONT, 13, "bold")).pack(side="left")
        FlatButton(top, T("Обновить"), self.load_apps, bg=CARD_HOVER, hover=CARD_HOVER2,
                   fg=TEXT, size=10, padx=14, pady=7).pack(side="right")
        self._make_search(top, T("Поиск программы…")).pack(side="right", padx=S(10))

        bar = tk.Frame(page, bg=BG)
        bar.pack(fill="x", padx=pad, pady=(0, S(8)))
        tk.Label(bar, text=T("Сортировка:"), bg=BG, fg=MUTED, font=(FONT, 9)).pack(side="left")
        self.sort_btns = {}
        for key, text in (("name", T("По имени")), ("size", T("По размеру"))):
            b = FlatButton(bar, text, lambda k=key: self._apps_sort(k), size=9, padx=12, pady=5)
            b.pack(side="left", padx=(S(8), 0))
            self.sort_btns[key] = b
        self._style_sort_buttons()
        FlatButton(bar, T("Снять выбор"), lambda: self.apps_list.select_none(), bg=CARD,
                   hover=CARD_HOVER, fg=MUTED, size=9, padx=12, pady=5).pack(side="right")

        bottom = tk.Frame(page, bg=BG)
        bottom.pack(side="bottom", fill="x", padx=pad, pady=(0, S(14)))
        brow = tk.Frame(bottom, bg=BG)
        brow.pack(fill="x", pady=S(12))  # одинаковый отступ до списка и до карточки ниже
        self.btn_uninstall = FlatButton(brow, T("Удалить выбранные"), self.uninstall_selected,
                                        bg=RED, hover=RED_HOVER, size=10, padx=18, pady=9)
        self.btn_uninstall.pack(side="right")
        self.apps_info = EllipsisLabel(brow, text="", bg=BG, fg=ACCENT, font=(FONT, 10, "bold"))
        self.apps_info.pack(side="left", fill="x", expand=True, padx=(0, S(12)))
        qrow = tk.Frame(bottom, bg=CARD)
        qrow.pack(fill="x")
        self.var_quiet = tk.BooleanVar(value=False)
        self._option(qrow, T("Тихое удаление, если поддерживается"),
                     T("Без окон деинсталлятора. Строки с замком 🔒 — защищённые компоненты, "
                     "их удалить нельзя"), self.var_quiet, True, None)

        self.apps_list = CheckList(page, on_change=self._apps_changed, row_h=58,
                                   icon_px=self.icon_px, right_w=130)
        self.apps_list.pack(fill="both", expand=True, padx=pad)
        return page

    def _style_sort_buttons(self):
        for key, b in self.sort_btns.items():
            if key == self.apps_sort:
                b.set_style(ACCENT, ACCENT_HOVER, DARK)
            else:
                b.set_style(CARD, CARD_HOVER, MUTED)

    def _apps_sort(self, key):
        self.apps_sort = key
        self._style_sort_buttons()
        self.apps_list.sort_by(key, reverse=(key == "size"))

    def _apps_filter(self):
        q = self.var_search.get().strip().lower()
        pred = (lambda it: q in it["keys"]["name"] or q in it["keys"].get("pub", "")) if q else None
        self.apps_list.apply_filter(pred)

    def _apps_changed(self):
        items = self.apps_list.checked_items()
        size = sum(it["payload"].get("size", 0) for it in items)
        text = T('Программ: {0}   •   Отмечено: {1}').format(len(self.apps_list.items), len(items))
        if size:
            text += f" ({fmt_size(size)})"
        if self.apps_loading:
            text = T("Загрузка…   ") + text
        self.apps_info.config(text=text)

    def load_apps(self):
        if self.apps_loading or self.uninstalling:
            return
        self.apps_loading = True
        self.apps_gen += 1
        self.apps_iids = []
        self.apps_list.clear()
        self._apps_changed()
        threading.Thread(target=self._apps_worker, daemon=True).start()

    def _apps_worker(self):
        try:
            for item in iter_installed_programs():
                self.q.put(("app", item))
            for item in list_store_apps():  # медленнее — идёт после реестра
                self.q.put(("app", item))
        except Exception:
            pass
        self.q.put(("apps_done",))

    def _icons_worker(self, jobs, gen, size):
        """Фоновая загрузка значков: сначала из файлов программ, иначе буква на плашке."""
        cache = {}
        for iid, item in jobs:
            if gen != self.apps_gen:
                return
            try:
                img = make_app_icon(item, size, cache)
            except Exception:
                img = None
            if img is not None:
                self.q.put(("icon", iid, img, gen))

    def uninstall_selected(self):
        if self.uninstalling or self.apps_loading:
            return
        chosen = [it["payload"] for it in self.apps_list.checked_items()
                  if not it["payload"]["protected"]]
        if not chosen:
            messagebox.showinfo(T("Программы"), T("Ничего не отмечено."))
            return
        names = "\n".join("• " + c["name"] for c in chosen[:10])
        if len(chosen) > 10:
            names += T('\n… и ещё {0}').format(len(chosen) - 10)
        if not messagebox.askyesno(
                T("Удаление программ"),
                T('Будут запущены программы удаления ({0} шт.):\n\n{1}\n\nЭто необратимо. Продолжить?').format(len(chosen), names), icon="warning"):
            return
        self.uninstalling = True
        self.btn_uninstall.set_enabled(False)
        threading.Thread(target=self._uninstall_worker,
                         args=(chosen, self.var_quiet.get(), self.admin), daemon=True).start()

    def _uninstall_worker(self, items, quiet, admin):
        results = []
        for i, item in enumerate(items, 1):
            self.q.put(("apps_status", T('Удаляю ({0}/{1}): {2}…').format(i, len(items), item['name'])))
            try:
                if item["kind"] == "store":
                    ok = remove_store_app(item["full"])
                else:
                    uninstall_program(item, quiet, admin)
                    ok = not reg_entry_exists(item)
            except Exception:
                ok = False
            results.append((item["name"], ok))
        self.q.put(("uninstall_done", results))

    # ======================= Страница «Бэкап» =======================
    def _labeled_entry(self, parent, caption, var, buttons=()):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=S(14), pady=(S(8), 0))
        tk.Label(row, text=caption, bg=CARD, fg=MUTED, width=14, anchor="w",
                 font=(FONT, 10)).pack(side="left")
        for text, cmd in reversed(buttons):
            FlatButton(row, text, cmd, bg=CARD_HOVER, hover=CARD_HOVER2, fg=TEXT,
                       size=9, padx=12, pady=6).pack(side="right", padx=(S(6), 0))
        ent = tk.Entry(row, textvariable=var, bg=CARD_HOVER, fg=TEXT, insertbackground=TEXT,
                       relief="flat", font=(FONT, 10), highlightthickness=0)
        ent.pack(side="left", fill="x", expand=True, ipady=S(5))
        return ent

    def _build_backup(self, parent):
        page = tk.Frame(parent, bg=BG)
        pad = S(28)
        self.bk = backup_settings()
        self.bk_busy = False
        self.bk_stop = threading.Event()
        self.bk_thread = None
        self.bk_gen = 0          # номер пересчёта размеров: старые потоки игнорируются
        self.bk_sizes = {}       # путь -> (размер, файлов)
        self.bk_last = None      # путь последнего созданного архива

        top = tk.Frame(page, bg=BG)
        top.pack(fill="x", padx=pad, pady=(S(6), S(8)))
        tk.Label(top, text=T("Резервная копия файлов и настроек"), bg=BG, fg=TEXT,
                 font=(FONT, 13, "bold")).pack(side="left")

        bar = tk.Frame(page, bg=BG)
        bar.pack(fill="x", padx=pad, pady=(0, S(8)))
        for text, cmd in ((T("+ Файлы"), self.bk_add_files), (T("+ Папка"), self.bk_add_folder),
                          (T("+ Типовые конфиги"), self.bk_add_presets)):
            FlatButton(bar, text, cmd, bg=CARD_HOVER, hover=CARD_HOVER2, fg=TEXT,
                       size=9, padx=12, pady=6).pack(side="left", padx=(0, S(8)))
        FlatButton(bar, T("Убрать отмеченные"), self.bk_remove_checked, bg=CARD, hover=CARD_HOVER,
                   fg=MUTED, size=9, padx=12, pady=6).pack(side="right")

        # нижняя часть пакуется раньше списка — всегда видна
        bottom = tk.Frame(page, bg=BG)
        bottom.pack(side="bottom", fill="x", padx=pad, pady=(S(8), S(14)))

        brow = tk.Frame(bottom, bg=BG)
        brow.pack(side="bottom", fill="x", pady=(S(10), 0))
        self.btn_backup = FlatButton(brow, T("💾  Создать бэкап"), self.bk_button, bg=GREEN,
                                     hover=GREEN_HOVER, size=10, padx=18, pady=9)
        self.btn_backup.pack(side="right")
        self.btn_bk_open = FlatButton(brow, T("📂  Открыть папку"), self.bk_open_dest,
                                      bg=CARD_HOVER, hover=CARD_HOVER2, fg=TEXT, size=10,
                                      padx=16, pady=9)
        self.btn_bk_open.pack(side="right", padx=(0, S(8)))
        self.bk_info = EllipsisLabel(brow, text="", bg=BG, fg=ACCENT, font=(FONT, 10, "bold"))
        self.bk_info.pack(side="left", fill="x", expand=True, padx=(0, S(12)))

        prog = tk.Frame(bottom, bg=BG)
        prog.pack(side="bottom", fill="x", pady=(S(10), 0))
        self.bk_progress = SmoothProgress(prog)
        self.bk_progress.pack(fill="x")
        self.bk_status = EllipsisLabel(prog, text=T("Отметьте, что сохранить, и нажмите "
                                                  "«Создать бэкап»"), bg=BG, fg=MUTED,
                                       font=(FONT, 10))
        self.bk_status.pack(fill="x", pady=(S(6), 0))

        card = tk.Frame(bottom, bg=CARD)
        card.pack(side="bottom", fill="x")
        self.var_bk_dest = tk.StringVar(value=self.bk["dest"])
        self.var_bk_name = tk.StringVar(value=self.bk["name"])
        self._labeled_entry(card, T("Папка бэкапов"), self.var_bk_dest,
                            ((T("Обзор"), self.bk_browse),))
        self._labeled_entry(card, T("Имя архива"), self.var_bk_name,
                            ((T("По умолчанию"), self.bk_default_name),))
        self.bk_preview = EllipsisLabel(card, text="", bg=CARD, fg=MUTED, font=(FONT, 9))
        self.bk_preview.pack(fill="x", padx=S(14), pady=(S(4), S(4)))
        self.var_bk_skip = tk.BooleanVar(value=bool(self.bk["skip_cache"]))
        self.var_bk_strong = tk.BooleanVar(value=bool(self.bk["strong"]))
        self._option(card, T("Пропускать кэш и служебные папки"),
                     T("Cache, node_modules, __pycache__, .venv, logs и т. п. — бэкап быстрее "
                     "и меньше"), self.var_bk_skip, True, self.bk_options_changed)
        self._option(card, T("Сильное сжатие"),
                     T("Архив меньше, но создаётся в несколько раз дольше"),
                     self.var_bk_strong, True, self.bk_options_changed)
        tk.Frame(card, bg=CARD, height=S(6)).pack(fill="x")

        self.bk_list = CheckList(page, on_change=self.bk_checked_changed, row_h=50, right_w=110)
        self.bk_list.pack(fill="both", expand=True, padx=pad)

        self.var_bk_name.trace_add("write", lambda *a: self.bk_fields_changed())
        self.var_bk_dest.trace_add("write", lambda *a: self.bk_fields_changed())
        self._bk_save_job = None
        self.bk_reload()
        self._bk_tick()
        return page

    # ---------- список источников ----------
    def bk_reload(self):
        self.bk_list.clear()
        titles = {os.path.normcase(p): t for t, p in backup_presets()}
        for src in self.bk["sources"]:
            p = src["path"]
            exists = os.path.exists(p)
            name = titles.get(os.path.normcase(p)) or os.path.basename(p.rstrip("\\/")) or p
            iid = self.bk_list.add(name, sub=p, right=self._bk_size_text(p),
                                   tag=(T("Папка") if os.path.isdir(p) else T("Файл"))
                                   if exists else T("не найден"),
                                   payload=src, mid=True)
            if src.get("on", True) and exists:
                self.bk_list.set_checked(iid, True)
        self.bk_list._schedule()
        self.bk_recount()

    def _bk_size_text(self, path):
        if not os.path.exists(path):
            return "—"
        val = self.bk_sizes.get(path)
        return fmt_size(val[0]) if val else "…"

    def bk_recount(self):
        """Пересчитать размеры источников в фоне."""
        self.bk_gen += 1
        self.bk_sizes.clear()
        for it in self.bk_list.items.values():
            it["right"] = self._bk_size_text(it["payload"]["path"])
        self.bk_list._schedule()
        self._bk_update_info()
        paths = [s["path"] for s in self.bk["sources"] if os.path.exists(s["path"])]
        dest = self._bk_dest()
        exclude = {_norm(dest)} if dest else set()
        threading.Thread(target=self._bk_size_worker,
                         args=(paths, self.var_bk_skip.get(), exclude, self.bk_gen),
                         daemon=True).start()

    def _bk_size_worker(self, paths, skip, exclude, gen):
        for p in paths:
            if gen != self.bk_gen:
                return
            size, count = source_size(p, skip, exclude, stop=lambda: gen != self.bk_gen)
            self.q.put(("bk_size", gen, p, size, count))

    def _bk_set_sources(self, sources):
        self.bk["sources"] = sources
        self._bk_save()
        self.bk_reload()

    def _bk_dest(self):
        """Папка бэкапов из поля ввода: без кавычек, %ПЕРЕМЕННЫЕ% раскрыты. "" — не задана."""
        d = self.var_bk_dest.get().strip().strip('"').strip()
        return os.path.normpath(os.path.expandvars(d)) if d else ""

    def _bk_add(self, paths):
        known = {os.path.normcase(s["path"]) for s in self.bk["sources"]}
        dest = _norm(self._bk_dest() or BACKUP_DEFAULT_DIR)
        new, inside = [], []
        for p in paths:
            if not p:
                continue
            p = os.path.normpath(p)
            if os.path.normcase(p) in known:
                continue
            if _under(_norm(p), dest):
                inside.append(p)
                continue
            known.add(os.path.normcase(p))
            new.append({"path": p, "on": True})
        if inside:
            messagebox.showwarning(T("Бэкап"), T("Нельзя добавить папку с бэкапами саму в себя:\n")
                                   + "\n".join(inside[:5]))
        if new:
            self._bk_set_sources(self.bk["sources"] + new)

    def bk_add_files(self):
        if not self.bk_busy:
            self._bk_add(list(filedialog.askopenfilenames(title=T("Файлы для бэкапа"))))

    def bk_add_folder(self):
        if not self.bk_busy:
            d = filedialog.askdirectory(title=T("Папка для бэкапа"), mustexist=True)
            self._bk_add([d] if d else [])

    def bk_add_presets(self):
        if self.bk_busy:
            return
        before = len(self.bk["sources"])
        self._bk_add([p for _t, p in backup_presets()])
        if len(self.bk["sources"]) == before:
            messagebox.showinfo(T("Бэкап"), T("Все найденные типовые конфиги уже в списке."))

    def bk_remove_checked(self):
        if self.bk_busy:
            return
        sel = {id(it["payload"]) for it in self.bk_list.checked_items()}
        if not sel:
            messagebox.showinfo(T("Бэкап"), T("Отметьте строки, которые нужно убрать из списка."))
            return
        if not messagebox.askyesno(T("Бэкап"), T('Убрать из списка отмеченные пункты ({0})?\n\nСами файлы на диске не удаляются.').format(len(sel))):
            return
        self._bk_set_sources([s for s in self.bk["sources"] if id(s) not in sel])

    def bk_checked_changed(self):
        checked = {id(it["payload"]) for it in self.bk_list.checked_items()}
        for s in self.bk["sources"]:
            s["on"] = id(s) in checked
        self._bk_save()
        self._bk_update_info()

    def _bk_update_info(self):
        items = self.bk_list.checked_items()
        size = count = 0
        pending = False
        for it in items:
            val = self.bk_sizes.get(it["payload"]["path"])
            if val:
                size += val[0]
                count += val[1]
            else:
                pending = True
        text = T('Выбрано: {0} из {1}').format(len(items), len(self.bk_list.items))
        if items:
            text += T('   •   {0}{1}, файлов: {2}').format('≥ ' if pending else '', fmt_size(size), count)
        self.bk_info.config(text=text)

    # ---------- папка, имя, параметры ----------
    def bk_browse(self):
        if self.bk_busy:
            return
        cur = self._bk_dest()
        d = filedialog.askdirectory(title=T("Куда сохранять бэкапы"),
                                    initialdir=cur if os.path.isdir(cur) else None)
        if d:
            self.var_bk_dest.set(os.path.normpath(d))

    def bk_default_name(self):
        self.var_bk_name.set(BACKUP_DEFAULT_NAME)

    def bk_fields_changed(self):
        self._bk_preview()
        if self._bk_save_job:
            self.after_cancel(self._bk_save_job)
        self._bk_save_job = self.after(600, self._bk_fields_commit)

    def _bk_fields_commit(self):
        self._bk_save_job = None
        dest = self.var_bk_dest.get().strip()
        changed = dest != self.bk.get("dest")
        self.bk["dest"] = dest
        self.bk["name"] = self.var_bk_name.get()
        self._bk_save()
        if changed:
            self.bk_recount()

    def bk_options_changed(self):
        self.bk["skip_cache"] = self.var_bk_skip.get()
        self.bk["strong"] = self.var_bk_strong.get()
        self._bk_save()
        self.bk_recount()

    def _bk_save(self):
        save_backup_settings(self.bk)

    def _bk_preview(self):
        name = backup_name(self.var_bk_name.get())
        if name:
            self.bk_preview.config(text=T('Будет создан: {0}    •    в имени можно использовать {{date}}, {{time}}, {{pc}}').format(name), fg=MUTED)
        else:
            self.bk_preview.config(text=T("Введите имя архива"), fg=RED)

    def _bk_tick(self):
        """Раз в секунду обновляем предпросмотр имени — в нём может быть {time}."""
        if not self.winfo_exists():
            return
        if self.page == "backup" and not self.bk_busy:
            self._bk_preview()
        self.after(1000, self._bk_tick)

    def bk_open_dest(self):
        target = self.bk_last if self.bk_last and os.path.exists(self.bk_last) else None
        dest = self._bk_dest() or BACKUP_DEFAULT_DIR
        try:
            if target and IS_WIN:
                subprocess.Popen(["explorer", "/select,", target], creationflags=NO_WINDOW)
                return
            os.makedirs(dest, exist_ok=True)
            if IS_WIN:
                os.startfile(dest)
            else:
                subprocess.Popen(["xdg-open", dest])
        except OSError as e:
            messagebox.showerror(T("Бэкап"), T('Не удалось открыть папку:\n{0}').format(e))

    # ---------- создание архива ----------
    def bk_button(self):
        if self.bk_busy:
            self.bk_stop.set()
            self.btn_backup.set_enabled(False)
            self.bk_status.config(text=T("Отменяю…"), fg=AMBER)
            return
        self.start_backup()

    def start_backup(self):
        checked = {id(it["payload"]) for it in self.bk_list.checked_items()}
        sources = [s["path"] for s in self.bk["sources"]
                   if id(s) in checked and os.path.exists(s["path"])]
        if not sources:
            messagebox.showinfo(T("Бэкап"), T("Отметьте в списке хотя бы один существующий "
                                         "файл или папку."))
            return
        dest = self._bk_dest()
        if not dest or not os.path.isabs(dest):
            messagebox.showwarning(T("Бэкап"), T("Укажите полный путь к папке для бэкапов, "
                                            "например D:\\Backups."))
            return
        name = backup_name(self.var_bk_name.get())
        if not name:
            messagebox.showwarning(T("Бэкап"), T("Введите имя архива."))
            return
        try:
            os.makedirs(dest, exist_ok=True)
        except OSError as e:
            messagebox.showerror(T("Бэкап"), T('Не удалось создать папку:\n{0}\n\n{1}').format(dest, e))
            return
        dn = _norm(dest)
        clean_roots = [_norm(p) for c in CATEGORIES.values() for p in c["paths"]]
        if any(_under(dn, r) for r in clean_roots) and not is_whitelisted(dest):
            if not messagebox.askyesno(
                    T("Бэкап"), T("Папка бэкапов находится внутри временных файлов, которые "
                             "удаляет вкладка «Очистка».\nБэкапы могут быть стёрты при "
                             "очистке. Всё равно сохранить сюда?")):
                return
        path = os.path.join(dest, name)
        if os.path.exists(path):
            ans = messagebox.askyesnocancel(
                T("Бэкап"), T('Файл «{0}» уже есть в этой папке.\n\nДа — заменить\nНет — сохранить под новым именем\nОтмена — ничего не делать').format(name))
            if ans is None:
                return
            if ans is False:
                name = os.path.basename(unique_path(path))
        try:
            known = sum(self.bk_sizes.get(p, (0, 0))[0] for p in sources)
            free = shutil.disk_usage(dest).free
            if known > free and not messagebox.askyesno(
                    T("Бэкап"), T('На диске свободно {0}, а выбрано {1}.\nАрхив может не поместиться. Продолжить?').format(fmt_size(free), fmt_size(known))):
                return
        except OSError:
            pass

        self.bk_busy = True
        self.bk_stop.clear()
        self.btn_backup.config(text=T("✖  Отменить"))
        self.btn_backup.set_style(RED, RED_HOVER, DARK)
        self.bk_progress.config(value=0)
        self.bk_status.config(text=T("Подготовка…"), fg=MUTED)
        self.bk_thread = threading.Thread(
            target=self._bk_worker,
            args=(sources, dest, name, self.var_bk_skip.get(), self.var_bk_strong.get()),
            daemon=True)
        self.bk_thread.start()

    def _bk_worker(self, sources, dest, name, skip, strong):
        def progress(pct, text):
            self.q.put(("bk_progress", pct, text))
        try:
            res = create_backup(sources, dest, name, skip, strong,
                                stop=self.bk_stop.is_set, progress=progress)
        except Exception as e:
            res = {"error": str(e)}
        self.q.put(("bk_done", res))

    def _bk_finish(self, res):
        self.bk_busy = False
        self.btn_backup.set_enabled(True)
        self.btn_backup.config(text=T("💾  Создать бэкап"))
        self.btn_backup.set_style(GREEN, GREEN_HOVER, DARK)
        if res.get("cancelled"):
            self.bk_progress.config(value=0)
            self.bk_status.config(text=T("Бэкап отменён — незаконченный архив удалён"), fg=AMBER)
            return
        if "error" in res:
            self.bk_progress.config(value=0)
            self.bk_status.config(text=T('Ошибка: {0}').format(res['error']), fg=RED)
            messagebox.showerror(T("Бэкап"), T('Не удалось создать архив:\n\n{0}').format(res['error']))
            return
        self.bk_last = res["path"]
        self.bk_progress.config(value=100)
        text = (T('Готово: {0}  •  файлов: {1}  •  {2} → {3}  •  {4:.1f} с').format(os.path.basename(res['path']), res['files'], fmt_size(res['size']), fmt_size(res['zip_size']), res['elapsed']))
        skipped = res["skipped"]
        if skipped:
            text += T('  •  пропущено: {0}').format(len(skipped))
        self.bk_status.config(text=text, fg=GREEN if not skipped else AMBER)
        if skipped:
            lines = [f"• {p}  ({err})" for p, err in skipped[:12]]
            if len(skipped) > 12:
                lines.append(T('… и ещё {0}').format(len(skipped) - 12))
            messagebox.showwarning(
                T("Бэкап"), T('Архив создан, но часть файлов и папок ({0}) прочитать не удалось — они заняты другой программой или нет доступа:\n\n').format(len(skipped)) + "\n".join(lines))

    # ======================= Сообщения из потоков =======================
    def _poll(self):
        try:
            for _ in range(300):
                msg = self.q.get_nowait()
                self._handle(msg)
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _handle(self, msg):
        kind = msg[0]
        if kind == "scan":
            _, key, size, count, pct = msg
            self.sizes[key] = (size, count)
            self.t_prog = pct
            self.refresh_view()
        elif kind == "scan_done":
            self._set_busy(False)
            self.status.config(text=T("Сканирование завершено"), fg=GREEN)
            self.refresh_view()
            if self._rescan:
                self._rescan = False
                self.start_scan()
        elif kind == "status":
            self.status.config(text=msg[1], fg=MUTED)
        elif kind == "progress":
            self.t_prog = msg[1]
            ANIM.run("view", self._view_step)
        elif kind == "clean_done":
            _, freed, skipped = msg
            text = T('Готово! Освобождено {0}').format(fmt_size(freed))
            if skipped:
                text += T('  (пропущено файлов: {0} — заняты, защищены или в белом списке)').format(skipped)
            self._set_busy(False)
            self.start_scan()
            self.status.config(text=text, fg=GREEN)
        elif kind == "sys":
            _, cpu, gpu, load, total, avail = msg
            self.last_sys = (cpu, gpu, load, total, avail)
            self.mini["CPU"].set(cpu)
            self.mini["GPU"].set(gpu)
            self.mini["RAM"].set(load)
            if self.page == "perf":
                self._apply_gauges(*self.last_sys)
        elif kind == "mem_done":
            self.mem_busy = False
            self.btn_mem.set_enabled(True)
            res = msg[1]
            if "error" in res:
                self.mem_result.config(text=T('Ошибка: {0}').format(res['error']), fg=RED)
            else:
                text = (T('Освобождено ≈ {0}  •  обработано процессов: {1}  •  защищено: {2}').format(fmt_size(res['freed']), res['trimmed'], res['protected']))
                if res["deep"] is True:
                    text += T("  •  кэш Windows сброшен")
                elif res["deep"] is False:
                    text += T("  •  кэш Windows сбросить не удалось")
                self.mem_result.config(text=text, fg=GREEN)
        elif kind == "game_done":
            _, turn_on, ok, lines = msg
            self.game_busy = False
            self.btn_game.set_enabled(True)
            if ok:
                self.game_on = turn_on
            self._refresh_game_button()
            self.mem_result.config(
                text=(T("Игровой режим включён") if turn_on else T("Игровой режим выключен"))
                if ok else T("Не удалось изменить игровой режим"), fg=GREEN if ok else RED)
            messagebox.showinfo(T("Игровой режим"), "\n".join(lines))
        elif kind == "app":
            item = msg[1]
            sub = " • ".join(x for x in (item["publisher"], item["version"]) if x)
            iid = self.apps_list.add(
                item["name"], sub=sub,
                right=fmt_size(item["size"]) if item["size"] else "",
                tag="Microsoft Store" if item["kind"] == "store" else T("Программа"),
                payload=item, locked=item["protected"],
                keys={"size": item["size"], "pub": item["publisher"].lower()})
            self.apps_iids.append((iid, item))
            if item.get("_icon") is not None:  # значок уже был загружен (перестройка интерфейса)
                self.apps_list.set_image(iid, ImageTk.PhotoImage(item["_icon"]))
        elif kind == "apps_done":
            self.apps_loading = False
            self.apps_loaded = True
            self.apps_list.sort_by(self.apps_sort, reverse=(self.apps_sort == "size"))
            self._apps_filter()
            self._apps_changed()
            jobs = [(iid, it) for iid, it in self.apps_iids if it.get("_icon") is None]
            if HAS_PIL and jobs:
                threading.Thread(target=self._icons_worker,
                                 args=(jobs, self.apps_gen, self.icon_px),
                                 daemon=True).start()
        elif kind == "icon":
            _, iid, img, gen = msg
            if gen == self.apps_gen:
                it = self.apps_list.items.get(iid)
                if it:
                    it["payload"]["_icon"] = img  # пригодится при смене темы/языка
                self.apps_list.set_image(iid, ImageTk.PhotoImage(img))
        elif kind == "apps_status":
            self.apps_info.config(text=msg[1])
        elif kind == "bk_size":
            _, gen, path, size, count = msg
            if gen == self.bk_gen:
                self.bk_sizes[path] = (size, count)
                for it in self.bk_list.items.values():
                    if it["payload"]["path"] == path:
                        it["right"] = fmt_size(size)
                        it["tag"] = T('Папка • {0}').format(count) if os.path.isdir(path) else T("Файл")
                self.bk_list._schedule()
                self._bk_update_info()
        elif kind == "bk_progress":
            if self.bk_busy and not self.bk_stop.is_set():
                self.bk_progress.config(value=msg[1])
                self.bk_status.config(text=msg[2], fg=MUTED)
        elif kind == "bk_done":
            self._bk_finish(msg[1])
        elif kind == "uninstall_done":
            results = msg[1]
            self.uninstalling = False
            self.btn_uninstall.set_enabled(True)
            okc = sum(1 for _n, ok in results if ok)
            lines = [f"{'✔' if ok else '✖'} {n}" for n, ok in results[:15]]
            if len(results) > 15:
                lines.append(T('… и ещё {0}').format(len(results) - 15))
            tail = (T("\n\n✖ — программа не удалена: отмена, ошибка или нужно подтверждение "
                    "в самой программе (например, в Steam).")) if okc < len(results) else ""
            messagebox.showinfo(T("Удаление программ"),
                                T('Удалено: {0} из {1}\n\n').format(okc, len(results)) + "\n".join(lines) + tail)
            self.load_apps()


def pip_python():
    """python.exe рядом с текущим интерпретатором (у pythonw нет вывода для pip)."""
    exe = sys.executable
    if os.path.basename(exe).lower() == "pythonw.exe":
        cand = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.exists(cand):
            return cand
    return exe


def ensure_pillow():
    """Без Pillow графика рисуется грубо (рваные края). Предлагаем установить модуль
    и перезапускаем программу. True — текущий процесс нужно завершить."""
    if HAS_PIL or FROZEN or not IS_WIN or "--no-pillow" in sys.argv:
        return False
    if load_state().get("skip_pillow"):
        return False
    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    try:
        ans = messagebox.askyesnocancel(
            T("PCCleaner — чёткая графика"),
            T("Для ровной сглаженной графики нужен модуль Pillow, но он не установлен "
            "в этом окружении Python. Без него края диаграмм и кнопок получаются рваными.\n\n"
            "Установить сейчас? (pip install pillow, нужен интернет, около 10–30 секунд)\n\n"
            "Да — установить и перезапустить\nНет — не предлагать больше\nОтмена — спросить в следующий раз"),
            parent=root)
        if ans is None:
            return False
        if ans is False:
            st = load_state()
            st["skip_pillow"] = True
            save_state(st)
            return False

        win = tk.Toplevel(root)
        win.title(T("Установка Pillow"))
        win.configure(bg=BG)
        tk.Label(win, text=T("Устанавливаю Pillow…\nПодождите, окно закроется само."), bg=BG,
                 fg=TEXT, font=(FONT, 11), padx=36, pady=28).pack()
        win.update()
        with tempfile.TemporaryFile("w+", encoding="utf-8", errors="ignore") as log:
            proc = subprocess.Popen(
                [pip_python(), "-m", "pip", "install", "--disable-pip-version-check", "pillow"],
                stdout=log, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
            while proc.poll() is None:
                win.update()
                time.sleep(0.05)
            log.seek(0)
            tail = log.read()[-700:]
        win.destroy()
        if proc.returncode == 0:
            if not relaunch_detached():
                messagebox.showinfo(APP_NAME, T("Pillow установлен. Запустите программу снова."),
                                    parent=root)
            return True
        messagebox.showerror(
            APP_NAME,
            T("Не удалось установить Pillow автоматически.\nУстановите вручную: откройте "
            "терминал PyCharm и выполните\n\n    pip install pillow\n\n") + tail, parent=root)
        return False
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def main():
    enable_hidpi()
    argv = sys.argv[1:]
    keep = "--keep-ide" in argv
    from_ide = launched_from_pycharm()

    # Запуск из PyCharm: отрываемся от окна Run / консоли Python и выходим из него.
    if (IS_WIN and not FROZEN and not keep and "--detached" not in argv
            and from_ide and relaunch_detached()):
        return

    if ensure_pillow():
        return

    app = CleanerApp()
    if AUTO_CLOSE_IDE and IS_WIN and not FROZEN and not keep and from_ide:
        app.after(2000, lambda: threading.Thread(
            target=close_ide_windows, daemon=True).start())
    app.mainloop()


if __name__ == "__main__":
    main()
