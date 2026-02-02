import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# --- Конфигурация Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Если переменные не заданы, будем использовать локальные файлы (fallback)
# Это полезно для локальной разработки, если нет ключей
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

supabase: Client = None
if USE_SUPABASE:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error initializing Supabase: {e}")
        USE_SUPABASE = False

# Имена ключей в БД (соответствуют старым именам файлов без расширения)
KEY_USERS = "users"
KEY_TRANSACTIONS = "transactions"
KEY_PROMOCODES = "promocodes"
KEY_LINKS = "links"
KEY_DOMAINS = "domains"

# --- Внутренние функции ---

def _load_data(key, default=None):
    if default is None: default = {}
    
    if USE_SUPABASE:
        try:
            response = supabase.table("json_storage").select("data").eq("key", key).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]["data"]
            return default
        except Exception as e:
            print(f"Supabase load error ({key}): {e}")
            # Fallback to local file if fetch fails? Better return default or handle error.
            return default
    else:
        # Локальный режим (совместимость)
        filename = f"{key}.json"
        if not os.path.exists(filename): return default
        with open(filename, "r") as f: return json.load(f)

def _save_data(key, data):
    if USE_SUPABASE:
        try:
            # Upsert данных
            supabase.table("json_storage").upsert({
                "key": key, 
                "data": data
            }).execute()
        except Exception as e:
            print(f"Supabase save error ({key}): {e}")
    else:
        # Локальный режим
        filename = f"{key}.json"
        with open(filename, "w") as f: json.dump(data, f, indent=4)

# --- Экспорт ---

def load_db():
    # Legacy unused
    return {}

def save_db(data):
    pass

def load_domains():
    return _load_data(KEY_DOMAINS)

def save_domains(data):
    _save_data(KEY_DOMAINS, data)

def load_users():
    return _load_data(KEY_USERS)

def save_users(data):
    _save_data(KEY_USERS, data)

def load_transactions():
    return _load_data(KEY_TRANSACTIONS, default=[])

def save_transactions(data):
    _save_data(KEY_TRANSACTIONS, data)

def load_promocodes():
    return _load_data(KEY_PROMOCODES)

def save_promocodes(data):
    _save_data(KEY_PROMOCODES, data)

def load_links():
    return _load_data(KEY_LINKS)

def save_links(data):
    _save_data(KEY_LINKS, data)