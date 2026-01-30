import json
import os

# Имена файлов
DB_FILE = "database.json" # Legacy from BuilderBot, might not be needed but keeping for compatibility if used
USERS_FILE = "users.json"
TRANSACTIONS_FILE = "transactions.json"
PROMOCODES_FILE = "promocodes.json"
LINKS_FILE = "links.json"
DOMAINS_FILE = "domains.json"

def _load_json(filename, default=None):
    if default is None: default = {}
    if not os.path.exists(filename): return default
    with open(filename, "r") as f: return json.load(f)

def _save_json(filename, data):
    with open(filename, "w") as f: json.dump(data, f, indent=4)

# --- Экспорт ---

def load_db():
    return _load_json(DB_FILE)

def save_db(data):
    _save_json(DB_FILE, data)

def load_domains():
    return _load_json(DOMAINS_FILE)

def save_domains(data):
    _save_json(DOMAINS_FILE, data)

def load_users():
    return _load_json(USERS_FILE)

def save_users(data):
    _save_json(USERS_FILE, data)

def load_transactions():
    return _load_json(TRANSACTIONS_FILE, default=[])

def save_transactions(data):
    _save_json(TRANSACTIONS_FILE, data)

def load_promocodes():
    return _load_json(PROMOCODES_FILE)

def save_promocodes(data):
    _save_json(PROMOCODES_FILE, data)

def load_links():
    return _load_json(LINKS_FILE)

def save_links(data):
    _save_json(LINKS_FILE, data)
