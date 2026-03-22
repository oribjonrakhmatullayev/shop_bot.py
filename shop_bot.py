# -*- coding: utf-8 -*-
import logging, requests, csv, io, os
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- RENDER UCHUN SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- SOZLAMALAR ---
BOT_TOKEN  = "8275086123:AAFa8sY3eUsNBRyKGLA-W47AY1UPyOyrF8U"
ALLOWED_GROUP_ID = -1002307445361
ALLOWED_THREAD_ID = 1570

SHEET_URL  = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ5Y5lhFw0cKz8UuVb_fjbv1JKT0ncQYPxihlAycO9cGyZa2E92TKZB3fNx8er9N5EclXKNyzB63Fe7/pub?gid=1315694608&single=true&output=csv"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- MAHSULOTLARNI YUKLASH ---
def fetch_products():
    try:
        r = requests.get(SHEET_URL, timeout=15)
        r.raise_for_status()
        rows = list(csv.reader(io.StringIO(r.content.decode("utf-8"))))
        products = []
        for i in range(1, len(rows)):
            row = rows[i]
            if not row or len(row) < 5 or not row[0].strip(): continue
            products.append({
                "kod": row[0].strip(),
                "nom": row[2].strip().split('\n')[0],
                "narx": row[3].strip().lower().replace(" uzs","").replace(",","").replace(" ","").strip(),
                "ball": row[4].strip() if row[4].strip() else "0"
            })
        return products, None
    except Exception as e: return [], str(e)

# --- ASOSIY FILTR VA DEBUG ---
async def debug_and_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id if update.message else None
    text = update.message.text.strip()
    
    # Logga chiqarish (Render loglarida ko'rasiz)
    logger.info(f"Yangi xabar! Chat: {chat_id}, Topic: {thread_id}, Text: {text}")

    # Filtr: Faqat belgilangan guruh va mavzuda javob berish
    if chat_id != ALLOWED_GROUP_ID or thread_id != ALLOWED_THREAD_ID:
        return

    # Qidiruv logikasi
    products, _ = fetch_products()
    res = [p for p in products if text.lower() in p["kod"].lower() or text.lower() in p["nom"].lower()]
    
    if res:
        if len(res) == 1:
            p = res[0]
            price = "{:,}".format(int("".join(filter(str.isdigit, p['narx'])))).replace(",", " ")
            msg = f"✨ *Mahsulot:* {p['nom']}\n🆔 *Kod:* `{p['kod']}`\n💰 *Narx:* {price} so'm\n💎 *Ball:* {p['ball']} PV"
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            resp = f"✅ *{len(res)}* ta natija:\n"
            for p in res[:10]: resp += f"• `{p['kod']}` — {p['nom']}\n"
            await update.message.reply_text(resp, parse_mode="Markdown")

def main():
    Thread(target=run_flask, daemon=True).start()
    
    app_tg = Application.builder().token(BOT_TOKEN).build()
    
    # Hamma xabarlarni tekshirish uchun handler
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, debug_and_search))
    
    # Buyruqlar
    app_tg.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Salom! Mahsulot kodini yozing.") if u.effective_chat.id == ALLOWED_GROUP_ID else None))

    print("Bot debug rejimida ishga tushdi...")
    app_tg.run_polling()

if __name__ == "__main__":
    main()
