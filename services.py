import os
import aiohttp
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from config import CRYPTO_BOT_TOKEN, ADMIN_ID
from database import load_users, save_users, load_transactions, save_transactions

# --- Парсинг метаданных ---
async def fetch_url_metadata(url):
    """
    Скачивает страницу и извлекает OG-теги (title, description, image).
    Имитирует бота соцсетей (Facebook/Telegram), чтобы получить чистые метаданные.
    """
    headers = {
        # Притворяемся краулером Facebook, так как ему сайты охотнее отдают статику с OG-тегами
        "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    meta = {}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10, ssl=False) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # Title
                    og_title = soup.find("meta", property="og:title")
                    if og_title and og_title.get("content"):
                        meta["title"] = og_title["content"]
                    else:
                        title_tag = soup.find("title")
                        if title_tag:
                            meta["title"] = title_tag.string
                            
                    # Description
                    og_desc = soup.find("meta", property="og:description")
                    if og_desc and og_desc.get("content"):
                        meta["description"] = og_desc["content"]
                    else:
                        desc_tag = soup.find("meta", attrs={"name": "description"})
                        if desc_tag and desc_tag.get("content"):
                            meta["description"] = desc_tag["content"]

                    # Image
                    og_image = soup.find("meta", property="og:image")
                    if og_image and og_image.get("content"):
                        meta["image"] = og_image["content"]
                        
    except Exception as e:
        print(f"Error fetching metadata for {url}: {e}")
        
    return meta

# --- Подписки ---
def get_sub_status(user_id):
    if user_id == ADMIN_ID:
        return "∞"
    
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        return "Не активна"
    
    status_parts = []
    
    # 1. Проверка времени
    exp_str = users[uid].get("expiry")
    is_expired = False
    
    if exp_str:
        expiry = datetime.fromisoformat(exp_str)
        now = datetime.now()
        
        if expiry > now:
            diff = expiry - now
            if diff.days > 0:
                time_str = f"{diff.days} дн. {diff.seconds // 3600} ч."
            else:
                time_str = f"{diff.seconds // 3600} ч. {diff.seconds % 3600 // 60} мин."
            status_parts.append(time_str)
        else:
            is_expired = True
    
    # 2. Проверка баланса ссылок (вместо билдов)
    try:
        links_balance = int(users[uid].get("builds_balance", 0)) # Используем то же поле builds_balance для простоты
    except:
        links_balance = 0
        
    if links_balance > 0:
        status_parts.append(f"Ссылок: {links_balance}")
        
    if not status_parts:
        if is_expired:
            return "Истекла"
        return "Не активна"
        
    return " | ".join(status_parts)

def add_subscription(user_id, hours=0, amount=0, builds=0):
    users = load_users()
    uid = str(user_id)
    now = datetime.now()
    
    if uid not in users:
        users[uid] = {"joined_at": now.isoformat(), "is_blocked": False}
    
    # Добавление времени
    if hours != 0:
        current_exp_str = users[uid].get("expiry")
        if current_exp_str:
            try:
                current_exp = datetime.fromisoformat(current_exp_str)
            except ValueError:
                current_exp = now
                
            if current_exp > now:
                start_time = current_exp
            else:
                start_time = now
        else:
            start_time = now
            
        try:
            new_exp = start_time + timedelta(hours=hours)
            # Дополнительная защита, если год становится слишком большим
            if new_exp.year >= 9999:
                 new_exp = datetime.max
        except OverflowError:
            new_exp = datetime.max
            
        users[uid]["expiry"] = new_exp.isoformat()

    # Добавление "билдов" (ссылок)
    if builds != 0:
        current_builds = users[uid].get("builds_balance", 0)
        users[uid]["builds_balance"] = max(0, current_builds + builds)
    
    save_users(users)
    
    # Запись транзакции
    if amount > 0:
        txs = load_transactions()
        txs.append({
            "user_id": user_id,
            "amount": float(amount),
            "date": now.isoformat()
        })
        save_transactions(txs)

# --- CryptoBot API ---
async def create_invoice(amount_usdt):
    if not CRYPTO_BOT_TOKEN or "YOUR_" in CRYPTO_BOT_TOKEN:
        return None, None
        
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    data = {
        "asset": "USDT",
        "amount": str(amount_usdt),
        "description": "Premium Subscription",
        "allow_comments": False,
        "allow_anonymous": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as resp:
            result = await resp.json()
            if result.get("ok"):
                return result["result"]["pay_url"], result["result"]["invoice_id"]
    return None, None

async def check_invoice(invoice_id):
    if not CRYPTO_BOT_TOKEN or "YOUR_" in CRYPTO_BOT_TOKEN:
        return False
        
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    params = {"invoice_ids": str(invoice_id)}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            result = await resp.json()
            if result.get("ok") and result["result"]["items"]:
                status = result["result"]["items"][0]["status"]
                return status == "paid"
    return False

def is_user_blocked(user_id):
    users = load_users()
    return users.get(str(user_id), {}).get("is_blocked", False)
