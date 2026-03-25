# -*- coding: utf-8 -*-
import logging
import requests
import csv
import io
import os
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai  # <-- GEMINI QO'SHILDI

# --- RENDER PORT SOZLAMASI ---
app = Flask(__name__)

@app.route('/')
def home(): 
    return "Bot ishlamoqda!"

def run_flask():
    # Render avtomatik taqdim etadigan portni ishlatamiz
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- SOZLAMALAR ---
BOT_TOKEN = "8275086123:AAFa8sY3eUsNBRyKGLA-W47AY1UPyOyrF8U"

# API kalitni Render'ning Environment Variables bo'limidan oladi
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyBQjfFX4NqPBr8fpIEXC7w4eZxmu2vEudI") 

ALLOWED_GROUP_ID = -1002307445361
ALLOWED_THREAD_ID = 1570
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ5Y5lhFw0cKz8UuVb_fjbv1JKT0ncQYPxihlAycO9cGyZa2E92TKZB3fNx8er9N5EclXKNyzB63Fe7/pub?gid=1315694608&single=true&output=csv"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- GEMINI SOZLAMASI ---
genai.configure(api_key=GOOGLE_API_KEY)

def is_allowed(update: Update):
    if update.effective_chat.id == ALLOWED_GROUP_ID:
        thread_id = update.message.message_thread_id if update.message else None
        if thread_id == ALLOWED_THREAD_ID:
            return True
    return False

def fetch_products():
    try:
        r = requests.get(SHEET_URL, timeout=15)
        r.raise_for_status()
        rows = list(csv.reader(io.StringIO(r.content.decode("utf-8"))))
        products = []
        for i in range(1, len(rows)):
            row = rows[i]
            if not row or len(row) < 5 or not row[0].strip(): 
                continue
            products.append({
                "kod": row[0].strip(),
                "nom": row[2].strip().split('\n')[0],
                "narx": row[3].strip().lower().replace(" uzs", "").replace(",", "").replace(" ", "").strip(),
                "ball": row[4].strip() if row[4].strip() else "0"
            })
        return products, None
    except Exception as e: 
        return [], str(e)

def format_price(narx):
    try:
        num = "".join(filter(str.isdigit, str(narx)))
        return "{:,}".format(int(num)).replace(",", " ")
    except: 
        return narx

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): 
        return
    await update.message.reply_text("👋 *Greenleaf Botga xush kelibsiz!*", parse_mode="Markdown")

async def qidiruv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): 
        return
    
    query = update.message.text.strip()
    if len(query) < 2: 
        return
        
    # Foydalanuvchiga bot "yozmoqda..." degan statusni ko'rsatamiz
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    products, _ = fetch_products()
    
    # Gemini tushunishi uchun jadval ma'lumotlarini chiroyli matn holatiga keltiramiz
    catalog_text = ""
    for p in products:
        catalog_text += f"Kod: {p['kod']} | Nom: {p['nom']} | Narx: {format_price(p['narx'])} so'm | Ball: {p['ball']} PV\n"

    instruction = f"""
    Siz Greenleaf Rishton markazi mutaxassisiz. 
    Mijozlar bilan samimiy va xushmuomala gaplashing. 
    Faqat quyidagi katalog bo'yicha ma'lumot bering va narxlarni chiroyli qilib yozing:
    {catalog_text}
    """
    
    try:
        model = genai.GenerativeModel(
            model_name='models/gemini-2.5-flash',
            system_instruction=instruction
        )
        response = model.generate_content(query)
        await update.message.reply_text(response.text)
    except Exception as e:
        logger.error(f"Gemini xatosi: {e}")
        await update.message.reply_text("Kechirasiz, tizimda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.")

def main():
    # 1. Flask veb-serverini alohida oqimda ishga tushirish
    Thread(target=run_flask, daemon=True).start()
    
    # 2. Telegram botni sozlash
    app_tg = Application.builder().token(BOT_TOKEN).build()
    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, qidiruv))
    
    logger.info("Bot polling boshladi...")
    
    # drop_pending_updates=True
    app_tg.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
