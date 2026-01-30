from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import asyncio

from config import bot, ADMIN_ID, AdminState
from database import load_users, save_users, load_transactions, load_promocodes, save_promocodes, load_domains, save_domains
from services import get_sub_status, add_subscription
from keyboards import (
    get_start_text, get_start_kb, get_cancel_kb, 
    get_domains_menu_kb, get_domains_list_kb, get_domain_info_kb, get_confirm_kb
)

router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")

def get_stats_text(period="day"):
    users = load_users()
    txs = load_transactions()
    
    admin_uid = str(ADMIN_ID)
    if admin_uid in users:
        del users[admin_uid]
    
    total_users = len(users)
    
    now = datetime.now()
    if period == "day":
        cutoff = now - timedelta(days=1)
        period_name = "За сегодня"
    elif period == "week":
        cutoff = now - timedelta(weeks=1)
        period_name = "За неделю"
    elif period == "month":
        cutoff = now - timedelta(days=30)
        period_name = "За месяц"
    else: # all
        cutoff = datetime.min
        period_name = "За все время"
        
    new_users = 0
    revenue = 0.0
    
    for uid, data in users.items():
        joined_at_str = data.get("joined_at")
        if joined_at_str:
            joined_at = datetime.fromisoformat(joined_at_str)
            if joined_at > cutoff:
                new_users += 1
                
    for tx in txs:
        if str(tx["user_id"]) == admin_uid:
            continue
        tx_date = datetime.fromisoformat(tx["date"])
        if tx_date > cutoff:
            revenue += tx["amount"]
            
    return (
        f"📊 <b>Статистика ({period_name})</b>\n\n"
        f"👥 Всего пользователей: <b>{total_users}</b>\n"
        f"🆕 Новых пользователей: <b>{new_users}</b>\n"
        f"💰 Заработано: <b>{revenue:.2f} USDT</b>"
    )

@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    text = get_stats_text("day")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 За неделю", callback_data="stats_week"),
            InlineKeyboardButton(text="📋 Список", callback_data="users_page_0")
        ],
        [
            InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin_promos_menu"),
            InlineKeyboardButton(text="🌐 Домены", callback_data="d_menu")
        ],
        [
            InlineKeyboardButton(text="📣 Написать всем", callback_data="broadcast_ask")
        ],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="cancel_build")]]
    )
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("stats_"))
async def cb_admin_stats(callback: CallbackQuery):
    period = callback.data.split("_")[1]
    text = get_stats_text(period)
    
    if period == "day":
        next_text, next_cb = "📊 За неделю", "stats_week"
    elif period == "week":
        next_text, next_cb = "📊 За месяц", "stats_month"
    elif period == "month":
        next_text, next_cb = "📊 За все время", "stats_all"
    else: # all
        next_text, next_cb = "📊 За сегодня", "stats_day"
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=next_text, callback_data=next_cb),
            InlineKeyboardButton(text="📋 Список", callback_data="users_page_0")
        ],
        [
            InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin_promos_menu"),
            InlineKeyboardButton(text="🌐 Домены", callback_data="d_menu")
        ],
        [
            InlineKeyboardButton(text="📣 Написать всем", callback_data="broadcast_ask")
        ],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="cancel_build")]]
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("users_page_"))
async def cb_users_list(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    users = load_users()
    
    if str(ADMIN_ID) in users:
        del users[str(ADMIN_ID)]
    
    active = []
    blocked = []
    for uid, data in users.items():
        if data.get("is_blocked"):
            blocked.append(uid)
        else:
            active.append(uid)
            
    active.sort(key=lambda x: users[x].get("joined_at", ""), reverse=True)
    blocked.sort(key=lambda x: users[x].get("joined_at", ""), reverse=True)
    
    user_ids = active + blocked
    items_per_page = 5
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_users = user_ids[start_idx:end_idx]
    
    buttons = []
    for uid in page_users:
        u_data = users[uid]
        name = u_data.get("username")
        if not name:
            name = u_data.get("first_name", uid)
        else:
            name = f"@{name}"
            
        if u_data.get("is_blocked"):
            name = f"❌ {name}"
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"user_detail_{uid}")])
        
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"users_page_{page-1}"))
    if end_idx < len(user_ids):
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"users_page_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
        
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(f"👥 <b>Список пользователей ({len(users)})</b>\nСтраница {page+1}", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("user_detail_"))
async def cb_user_detail(callback: CallbackQuery):
    target_id = callback.data.split("_")[2]
    users = load_users()
    
    if target_id not in users:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
        
    u_data = users[target_id]
    
    username = f"@{u_data.get('username')}" if u_data.get('username') else "Нет"
    full_name = f"{u_data.get('first_name', '')} {u_data.get('last_name', '')}".strip()
    if not full_name: full_name = "Неизвестно"
    
    days_with_us = 0
    joined_at_str = u_data.get("joined_at")
    if joined_at_str:
        joined_at = datetime.fromisoformat(joined_at_str)
        days_with_us = (datetime.now() - joined_at).days
        
    total_spent = 0.0
    txs = load_transactions()
    for tx in txs:
        if str(tx["user_id"]) == str(target_id):
            total_spent += tx["amount"]
            
    sub_status = get_sub_status(target_id)
    is_blocked = u_data.get("is_blocked", False)
    status_emoji = "🔴 Заблокирован" if is_blocked else "🟢 Активен"
    
    text = (
        f"👤 <b>Информация о пользователе</b>\n\n"
        f"🆔 ID: <code>{target_id}</code>\n"
        f"📛 Имя: <b>{full_name}</b>\n"
        f"🔗 Юзернейм: <b>{username}</b>\n"
        f"🚦 Статус: <b>{status_emoji}</b>\n\n"
        f"📅 С нами: <b>{days_with_us} дн.</b>\n"
        f"💰 Потрачено: <b>{total_spent} USDT</b>\n"
        f"⏳ Подписка: <b>{sub_status}</b>"
    )
    
    # Для самого себя (если админ открыл свой профиль) или для других
    buttons = []
    if str(callback.from_user.id) == str(ADMIN_ID) and str(target_id) != str(ADMIN_ID):
        if is_blocked:
            block_btn = InlineKeyboardButton(text="🔓 Разблокировать", callback_data=f"unblock_ask_{target_id}")
        else:
            block_btn = InlineKeyboardButton(text="⛔ Заблокировать", callback_data=f"block_ask_{target_id}")
            
        buttons.append([InlineKeyboardButton(text="⚙️ Управлять", callback_data=f"manage_sub_{target_id}"), block_btn])
        buttons.append([InlineKeyboardButton(text="✉️ Написать", callback_data=f"send_msg_ask_{target_id}")])
    
    # Если админ смотрит кого-то другого, кнопка "К списку". Если юзер себя - "В меню"
    if str(callback.from_user.id) == str(ADMIN_ID) and str(target_id) != str(ADMIN_ID):
        buttons.append([InlineKeyboardButton(text="🔙 К списку", callback_data="users_page_0")])
    else:
        buttons.append([InlineKeyboardButton(text="🔙 В меню", callback_data="cancel_build")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("manage_sub_"))
async def cb_manage_sub(callback: CallbackQuery):
    target_id = callback.data.split("_")[2]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Увеличить", callback_data=f"manage_act_add_{target_id}"),
            InlineKeyboardButton(text="➖ Сократить", callback_data=f"manage_act_remove_{target_id}")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"user_detail_{target_id}")]])
    await callback.message.edit_text(f"⚙️ <b>Управление подпиской пользователя {target_id}</b>\nВыберите действие:", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("manage_act_"))
async def cb_manage_action(callback: CallbackQuery):
    parts = callback.data.split("_")
    action = parts[2]
    target_id = parts[3]
    action_text = "увеличить" if action == "add" else "сократить"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 час", callback_data=f"manage_apply_{action}_1_{target_id}"),
            InlineKeyboardButton(text="6 часов", callback_data=f"manage_apply_{action}_6_{target_id}"),
            InlineKeyboardButton(text="12 часов", callback_data=f"manage_apply_{action}_12_{target_id}")
        ],
        [
            InlineKeyboardButton(text="1 день", callback_data=f"manage_apply_{action}_24_{target_id}"),
            InlineKeyboardButton(text="7 дней", callback_data=f"manage_apply_{action}_168_{target_id}"),
            InlineKeyboardButton(text="1 месяц", callback_data=f"manage_apply_{action}_720_{target_id}")
        ],
        [InlineKeyboardButton(text="✍️ Указать своё", callback_data=f"manage_manual_{action}_{target_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"manage_sub_{target_id}")]])
    await callback.message.edit_text(f"Укажите время, на которое нужно <b>{action_text}</b> подписку:", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("manage_apply_"))
async def cb_manage_apply(callback: CallbackQuery):
    parts = callback.data.split("_")
    action = parts[2]
    hours = int(parts[3])
    target_id = parts[4]
    
    final_hours = hours if action == "add" else -hours
    add_subscription(target_id, hours=final_hours)
    
    await callback.answer("Подписка изменена", show_alert=True)
    new_callback = callback.model_copy(update={"data": f"user_detail_{target_id}"})
    await cb_user_detail(new_callback)

@router.callback_query(F.data.startswith("manage_manual_"))
async def cb_manage_manual(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    action = parts[2]
    target_id = parts[3]
    
    await state.update_data(manage_action=action, manage_target=target_id)
    await state.set_state(AdminState.waiting_for_hours)
    
    action_text = "добавить" if action == "add" else "убрать"
    await callback.message.answer(f"Введите количество часов (целое число), которое нужно <b>{action_text}</b>:", reply_markup=get_cancel_kb(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminState.waiting_for_hours)
async def process_manual_hours(message: Message, state: FSMContext):
    try:
        hours = int(message.text)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите целое число.", reply_markup=get_cancel_kb())
        return
        
    data = await state.get_data()
    action = data['manage_action']
    target_id = data['manage_target']
    
    final_hours = hours if action == "add" else -hours
    add_subscription(target_id, hours=final_hours)
    
    await message.answer(f"✅ Успешно! Подписка пользователя {target_id} обновлена.")
    
    msg = await message.answer("🔄 Обновление данных...")
    fake_cb = CallbackQuery(id="0", from_user=message.from_user, chat_instance="0", message=msg, data=f"user_detail_{target_id}")
    await state.clear()
    await cb_user_detail(fake_cb)

@router.callback_query(F.data.startswith("send_msg_ask_"))
async def cb_send_msg_ask(callback: CallbackQuery, state: FSMContext):
    target_id = callback.data.split("_")[3]
    await state.update_data(msg_target=target_id)
    await state.set_state(AdminState.waiting_for_message)
    await callback.message.edit_text(f"✍️ <b>Напишите сообщение для пользователя {target_id}:</b>", reply_markup=get_cancel_kb(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminState.waiting_for_message)
async def process_admin_message(message: Message, state: FSMContext):
    data = await state.get_data()
    target_id = data['msg_target']
    try:
        await bot.copy_message(chat_id=target_id, from_chat_id=message.chat.id, message_id=message.message_id)
        await message.answer("✅ Сообщение успешно отправлено.")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить сообщение.\nОшибка: {e}")
    
    msg = await message.answer("🔄 Возврат...")
    fake_cb = CallbackQuery(id="0", from_user=message.from_user, chat_instance="0", message=msg, data=f"user_detail_{target_id}")
    await state.clear()
    await cb_user_detail(fake_cb)

@router.callback_query(F.data == "broadcast_ask")
async def cb_broadcast_ask(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_for_broadcast)
    await callback.message.edit_text("📣 <b>Рассылка по всем пользователям</b>\n\nПришлите сообщение (текст, фото, видео), которое нужно отправить всем.", reply_markup=get_cancel_kb(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminState.waiting_for_broadcast)
async def process_broadcast_message(message: Message, state: FSMContext):
    users = load_users()
    total = 0; success = 0; blocked = 0; errors = 0
    status_msg = await message.answer("⏳ Рассылка началась...")
    
    for uid in users:
        if users[uid].get("is_blocked"):
            blocked += 1
            continue
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
            success += 1
        except Exception:
            errors += 1
        total += 1
        
    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n📬 Всего попыток: {total}\n✅ Успешно: {success}\n⛔ Пропущено (бан): {blocked}\n❌ Ошибки: {errors}",
        parse_mode="HTML"
    )
    admin_data = users.get(str(message.from_user.id))
    await message.answer(get_start_text(message.from_user, admin_data), reply_markup=get_start_kb(message.from_user.id), parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data.startswith("block_ask_"))
async def cb_block_ask(callback: CallbackQuery):
    target_id = callback.data.split("_")[2]
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Да, заблокировать", callback_data=f"block_confirm_{target_id}"), InlineKeyboardButton(text="Нет", callback_data=f"user_detail_{target_id}")]])
    await callback.message.edit_text(f"⚠️ <b>Вы уверены, что хотите заблокировать пользователя {target_id}?</b>", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("block_confirm_"))
async def cb_block_confirm(callback: CallbackQuery):
    target_id = callback.data.split("_")[2]
    users = load_users()
    if target_id in users:
        users[target_id]["is_blocked"] = True
        save_users(users)
    await callback.answer("Пользователь заблокирован", show_alert=True)
    new_callback = callback.model_copy(update={"data": f"user_detail_{target_id}"})
    await cb_user_detail(new_callback)

@router.callback_query(F.data.startswith("unblock_ask_"))
async def cb_unblock_ask(callback: CallbackQuery):
    target_id = callback.data.split("_")[2]
    users = load_users()
    if target_id in users:
        users[target_id]["is_blocked"] = False
        save_users(users)
    await callback.answer("Пользователь разблокирован", show_alert=True)
    new_callback = callback.model_copy(update={"data": f"user_detail_{target_id}"})
    await cb_user_detail(new_callback)

# --- Промокоды ---
@router.callback_query(F.data == "admin_promos_menu")
async def cb_admin_promos_menu(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Создать промокод", callback_data="create_promo_start"),
            InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin_promos_list_0")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])
    await callback.message.edit_text("🎟 <b>Управление промокодами</b>", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("admin_promos_list_"))
async def cb_admin_promos_list(callback: CallbackQuery):
    page = int(callback.data.split("_")[3])
    promocodes = load_promocodes()
    
    # Сортируем по дате создания (новые выше)
    sorted_codes = sorted(promocodes.keys(), key=lambda x: promocodes[x].get("created_at", ""), reverse=True)
    
    items_per_page = 5
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_codes = sorted_codes[start_idx:end_idx]
    
    buttons = []
    for code in page_codes:
        p_data = promocodes[code]
        # Отображаем код и остаток активаций
        btn_text = f"{code} ({p_data.get('activations_left', 0)})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"promo_detail_{code}")])
        
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_promos_list_{page-1}"))
    if end_idx < len(sorted_codes):
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_promos_list_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
        
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_promos_menu")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(f"📋 <b>Список промокодов ({len(promocodes)})</b>\nСтраница {page+1}", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("promo_detail_"))
async def cb_promo_detail(callback: CallbackQuery):
    code = callback.data.split("_")[2]
    promocodes = load_promocodes()
    
    if code not in promocodes:
        await callback.answer("Промокод не найден", show_alert=True)
        # Возвращаемся к списку
        await cb_admin_promos_list(callback.model_copy(update={"data": "admin_promos_list_0"}))
        return
        
    p = promocodes[code]
    
    p_type = "⏳ Часы" if p.get("type") == "hours" else "🏗 Билды (ссылки)"
    created_at = "Неизвестно"
    if p.get("created_at"):
        try:
            dt = datetime.fromisoformat(p.get("created_at"))
            created_at = dt.strftime("%Y-%m-%d %H:%M")
        except:
            pass

    text = (
        f"🎟 <b>Промокод:</b> <code>{code}</code>\n\n"
        f"Тип: <b>{p_type}</b>\n"
        f"Значение: <b>{p.get('value')}</b>\n"
        f"Осталось активаций: <b>{p.get('activations_left')}</b>\n"
        f"Создан: {created_at}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"promo_delete_ask_{code}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_promos_list_0")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("promo_delete_ask_"))
async def cb_promo_delete_ask(callback: CallbackQuery):
    code = callback.data.split("_")[3]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, удалить", callback_data=f"promo_delete_confirm_{code}"),
            InlineKeyboardButton(text="Нет", callback_data=f"promo_detail_{code}")
        ]
    ])
    await callback.message.edit_text(f"⚠️ Удалить промокод <code>{code}</code>?", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("promo_delete_confirm_"))
async def cb_promo_delete_confirm(callback: CallbackQuery):
    code = callback.data.split("_")[3]
    promocodes = load_promocodes()
    
    if code in promocodes:
        del promocodes[code]
        save_promocodes(promocodes)
        await callback.answer("✅ Промокод удален", show_alert=True)
    else:
        await callback.answer("❌ Промокод уже не существует", show_alert=True)
        
    # Возвращаемся к списку
    await cb_admin_promos_list(callback.model_copy(update={"data": "admin_promos_list_0"}))

@router.callback_query(F.data == "create_promo_start")
async def cb_create_promo_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✍️ <b>Запишите промокод</b> (текст):", reply_markup=get_cancel_kb(), parse_mode="HTML")
    await state.set_state(AdminState.waiting_for_promo_code)
    await callback.answer()

@router.message(AdminState.waiting_for_promo_code)
async def process_admin_promo_code(message: Message, state: FSMContext):
    code = message.text.strip()
    if not code:
        await message.answer("❌ Пустой код.", reply_markup=get_cancel_kb())
        return
    await state.update_data(promo_code=code)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ Часы", callback_data="promo_type_hours"), InlineKeyboardButton(text="🏗 Билды (ссылки)", callback_data="promo_type_builds")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_build")]])
    await message.answer("<b>Выбери тип промокода:</b>", reply_markup=kb, parse_mode="HTML")
    await state.set_state(AdminState.waiting_for_promo_type)

@router.callback_query(F.data.startswith("promo_type_"))
async def cb_promo_type(callback: CallbackQuery, state: FSMContext):
    p_type = callback.data.split("_")[2]
    await state.update_data(promo_type=p_type)
    msg_text = "Укажите количество часов:" if p_type == "hours" else "Укажите количество ссылок:"
    await callback.message.edit_text(msg_text, reply_markup=get_cancel_kb())
    await state.set_state(AdminState.waiting_for_promo_value)
    await callback.answer()

@router.message(AdminState.waiting_for_promo_value)
async def process_promo_value(message: Message, state: FSMContext):
    try:
        val = int(message.text)
        if val <= 0: raise ValueError
    except:
        await message.answer("❌ Введите положительное целое число.", reply_markup=get_cancel_kb())
        return
    await state.update_data(promo_value=val)
    await message.answer("Укажите число выпуска промокодов (лимит активаций):", reply_markup=get_cancel_kb())
    await state.set_state(AdminState.waiting_for_promo_limit)

@router.message(AdminState.waiting_for_promo_limit)
async def process_promo_limit(message: Message, state: FSMContext):
    try:
        limit = int(message.text)
        if limit <= 0: raise ValueError
    except:
        await message.answer("❌ Введите положительное целое число.", reply_markup=get_cancel_kb())
        return
    
    data = await state.get_data()
    code = data['promo_code']
    p_type = data['promo_type']
    val = data['promo_value']
    
    promocodes = load_promocodes()
    if code in promocodes:
        await message.answer("⚠️ Такой промокод уже существует и будет перезаписан.")
        
    promocodes[code] = {
        "type": p_type,
        "value": val,
        "activations_left": limit,
        "created_at": datetime.now().isoformat()
    }
    save_promocodes(promocodes)
    
    await state.clear()
    await message.answer(f"✅ <b>Промокод создан!</b>\n\nКод: <code>{code}</code>\nТип: {p_type}\nЗначение: {val}\nЛимит: {limit}", parse_mode="HTML")
    
    users = load_users()
    admin_data = users.get(str(message.from_user.id))
    await message.answer(get_start_text(message.from_user, admin_data), reply_markup=get_start_kb(message.from_user.id), parse_mode="HTML")

# --- Домены ---

@router.callback_query(F.data == "d_menu")
async def cb_domains_menu(callback: CallbackQuery):
    await callback.message.edit_text("🌐 <b>Управление доменами</b>", reply_markup=get_domains_menu_kb(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "d_add")
async def cb_domain_add(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✍️ <b>Укажите домен для добавления в список:</b>", reply_markup=get_cancel_kb(), parse_mode="HTML")
    await state.set_state(AdminState.waiting_for_new_domain)
    await callback.answer()

@router.message(AdminState.waiting_for_new_domain)
async def process_new_domain(message: Message, state: FSMContext):
    domain = message.text.strip()
    if not domain:
        await message.answer("❌ Пустое сообщение. Введите домен.", reply_markup=get_cancel_kb())
        return
        
    await state.update_data(new_domain=domain)
    await message.answer(
        f"Добавить домен <code>{domain}</code> в список?", 
        reply_markup=get_confirm_kb("d_save"), 
        parse_mode="HTML"
    )

@router.callback_query(F.data == "d_save_yes")
async def cb_domain_save_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    domain = data.get("new_domain")
    
    if domain:
        domains = load_domains()
        # Если формат доменов в БД - это словарь или список, нужно обработать
        # Используем словарь {domain_name: {created_at: ...}} для расширяемости
        if domain not in domains:
            domains[domain] = {
                "created_at": datetime.now().isoformat()
            }
            save_domains(domains)
            await callback.message.edit_text(f"✅ Домен <code>{domain}</code> успешно добавлен!", parse_mode="HTML")
        else:
            await callback.message.edit_text(f"⚠️ Домен <code>{domain}</code> уже есть в списке.", parse_mode="HTML")
    
    await state.clear()
    # Возвращаемся в меню доменов через небольшую паузу или сразу предлагаем меню
    await callback.message.answer("🌐 <b>Управление доменами</b>", reply_markup=get_domains_menu_kb(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "d_save_no")
async def cb_domain_save_no(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Добавление отменено.")
    await callback.message.answer("🌐 <b>Управление доменами</b>", reply_markup=get_domains_menu_kb(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("d_list_"))
async def cb_domains_list(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    domains = load_domains()
    
    domain_list = sorted(list(domains.keys()))
    
    kb = get_domains_list_kb(domain_list, page)
    await callback.message.edit_text(f"📋 <b>Список доменов ({len(domain_list)})</b>\nСтраница {page+1}", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("d_inf_"))
async def cb_domain_info(callback: CallbackQuery):
    domain = callback.data.split("_", 2)[2] # d_inf_google.com -> google.com
    domains = load_domains()
    
    if domain not in domains:
        await callback.answer("Домен не найден", show_alert=True)
        await cb_domains_list(callback.model_copy(update={"data": "d_list_0"}))
        return

    info = domains[domain]
    created_at = info.get("created_at", "Неизвестно")
    try:
        dt = datetime.fromisoformat(created_at)
        created_at_str = dt.strftime("%Y-%m-%d %H:%M")
    except:
        created_at_str = created_at
        
    text = (
        f"🌐 <b>Информация о домене</b>\n\n"
        f"🔗 Домен: <code>{domain}</code>\n"
        f"📅 Добавлен: {created_at_str}"
    )
    
    await callback.message.edit_text(text, reply_markup=get_domain_info_kb(domain), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("d_del_ask_"))
async def cb_domain_delete_ask(callback: CallbackQuery):
    domain = callback.data.split("_", 3)[3]
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data=f"d_del_y_{domain}"),
            InlineKeyboardButton(text="Нет", callback_data=f"d_del_n_{domain}")
        ]
    ])
    await callback.message.edit_text(f"⚠️ Вы уверены, что хотите удалить домен <code>{domain}</code>?", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("d_del_y_"))
async def cb_domain_delete_yes(callback: CallbackQuery):
    domain = callback.data.split("_", 3)[3]
    domains = load_domains()
    
    if domain in domains:
        del domains[domain]
        save_domains(domains)
        await callback.answer("✅ Домен удален", show_alert=True)
    else:
        await callback.answer("❌ Домен уже не существует", show_alert=True)
        
    await cb_domains_list(callback.model_copy(update={"data": "d_list_0"}))

@router.callback_query(F.data.startswith("d_del_n_"))
async def cb_domain_delete_no(callback: CallbackQuery):
    domain = callback.data.split("_", 3)[3]
    # Возврат к информации
    callback.data = f"d_inf_{domain}"
    await cb_domain_info(callback)
