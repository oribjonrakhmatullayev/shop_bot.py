# -*- coding: utf-8 -*-
import logging, requests, csv, io, os
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- RENDER/PYTHONANYWHERE UCHUN SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot ishlamoqda!"

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

def format_price(narx):
    try:
        # Narx ichidagi raqam bo'lmagan belgilarni olib tashlash
        num = "".join(filter(str.isdigit, str(narx)))
        # 50000 -> 50 000 ko'rinishiga keltirish
        return "{:,}".format(int(num)).replace(",", " ")
    except:
        return narx

def make_card(p):
    # Mahsulot haqida qisqa va samimiy tavsiya qismi
    # Agar jadvalda tavsiya ustuni bo'lmasa, umumiy sifatli gap qo'shiladi
    tavsiya = "Tabiiy va yuqori sifatli mahsulot, sizga albatta yoqadi!"
    
    # Siz so'ragan shablon:
    card = (
        f"✨ Greenleaf Сифати — Сизнинг саломатлигингиз учун! ✨\n"
        f"🧼 Маҳсулот: {p['nom']}\n"
        f"🆔 Код: {p['kod']}\n"
        f"💰 Хамкор нархи: {format_price(p['narx'])} сўм\n"
        f"💎 Балл: {p['ball']} PV\n"
        f"✅ {tavsiya}\n"
    )
    return card

async def qidiruv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Guruh va Mavzu filtri
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    if update.message.message_thread_id != ALLOWED_THREAD_ID: return

    query = update.message.text.strip()
    if len(query) < 2: return
    
    products, _ = fetch_products()
    res = [p for p in products if query.lower() in p["kod"].lower() or query.lower() in p["nom"].lower()]
    
    if res:
        # Agar bitta mahsulot topilsa, faqat shablonni chiqaradi
        if len(res) == 1:
            await update.message.reply_text(make_card(res[0]))
        else:
            # Agar bir nechta chiqsa, qisqa ro'yxat
            text = f"✅ Шу код бўйича {len(res)} та натижа:\n\n"
            for p in res[:10]:
                text += f"• {p['nom']} (Код: {p['kod']})\n"
            text += "\nAniqroq ma'lumot uchun kodni to'liq yozing."
            await update.message.reply_text(text)

def main():
    Thread(target=run_flask, daemon=True).start()
    app_tg = Application.builder().token(BOT_TOKEN).build()
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, qidiruv))
    app_tg.run_polling()

if __name__ == "__main__":
    main()
