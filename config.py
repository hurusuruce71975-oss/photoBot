import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.state import State, StatesGroup

# Загрузка переменных окружения из .env файла
load_dotenv()

# --- Конфигурация ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN")
# ADMIN_ID должен быть числом
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID"))
except (TypeError, ValueError):
    # Fallback или ошибка, если ID не задан корректно
    ADMIN_ID = 0 
    print("WARNING: ADMIN_ID not set or invalid in .env")

# Проверка наличия критических переменных
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Состояния (States) ---

# Состояния для создания ссылки
class LinkState(StatesGroup):
    waiting_for_target_url = State()
    waiting_for_domain_selection = State()

# Состояния админа
class AdminState(StatesGroup):
    waiting_for_hours = State()
    waiting_for_message = State()
    waiting_for_broadcast = State()
    # Promo creation
    waiting_for_promo_code = State()
    waiting_for_promo_type = State()
    waiting_for_promo_value = State()
    waiting_for_promo_limit = State()
    # Domains
    waiting_for_new_domain = State()

# Состояния ввода промокода юзером
class PromoState(StatesGroup):
    waiting_for_code = State()