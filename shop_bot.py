# -*- coding: utf-8 -*-
import logging, requests, csv, io, json, os
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- RENDER PORTNI USHLAB TURISH UCHUN KICHIK SERVER ---
app = Flask('')

@app.route('/')
def home(): return "Bot is alive!"

@app.route('/health')
def health(): return "OK", 200

def run_flask():
    # Render PORTni avtomatik beradi, agar topilmasa 8080 ishlatiladi
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- SOZLAMALAR ---
# Eng oxirgi tokenni kiritganingizga ishonch hosil qiling
BOT_TOKEN  = "8275086123:AAFa8sY3eUsNBRyKGLA-W47AY1UPyOyrF8U"
ALLOWED_GROUP_ID = -1002307445361
ALLOWED_THREAD_ID = 1570

# Yangi CSV baza havolasi
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
                "nom": row[2].strip().split('\n')[0], # Faqat birinchi qatordagi nom
                "narx": row[3].strip().lower().replace(" uzs","").replace(",","").replace(" ","").strip(),
                "ball": row[4].strip() if row[4].strip() else "0"
            })
        return products, None
    except Exception as e: return [], str(e)

def format_price(narx):
    try:
        num = "".join(filter(str.isdigit, str(narx)))
        return "{:,}".format(int(num)).replace(",", " ")
    except: return narx

# --- SIZ SO'RAGAN ANIQ SHABLON ---
def make_card(p):
    tavsiya = "Табиий ва юқори сифатли маҳсулот, сизга албатта ёқади!"
    
    card = (
        f"✨ Greenleaf Сифати — Сизнинг саломатлигингиз uchun! ✨\n"
        f"🧼 Маҳсулот: {p['nom']}\n"
        f"🆔 Код: {p['kod']}\n"
        f"💰 Хамкор нархи: {format_price(p['narx'])} сўm\n"
        f"💎 Балл: {p['ball']} PV\n"
        f"✅ {tavsiya}\n"
        f"🛒 Буюртма: https://t.me/ORIFFFFFFFFFF\n"
        f"📞 Тел: +998 33 993 4070"
    )
    return card

async def qidiruv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Faqat belgilangan guruh va mavzu (topic) uchun
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    
    thread_id = update.message.message_thread_id if update.message else None
    if thread_id != ALLOWED_THREAD_ID: return

    query = update.message.text.strip()
    if len(query) < 2: return
    
    products, _ = fetch_products()
    res = [p for p in products if query.lower() in p["kod"].lower() or query.lower() in p["nom"].lower()]
    
    if res:
        if len(res) == 1:
            await update.message.reply_text(make_card(res[0]))
        else:
            text = f"✅ Шу код бўйича {len(res)} та натижа:\n\n"
            for p in res[:10]:
                text += f"• {p['nom']} (Код: {p['kod']})\n"
            text += "\nБатафсил маълумот учун кодни тўлиқ ёзинг."
            await update.message.reply_text(text)

def main():
    # Render uchun Flaskni alohida oqimda ishga tushirish
    Thread(target=run_flask, daemon=True).start()
    
    app_tg = Application.builder().token(BOT_TOKEN).build()
    
    # Matnli xabarlar uchun qidiruv
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, qidiruv))
    
    # Buyruqlar (faqat guruhda)
    app_tg.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Salom! Mahsulot kodini yozing.") if u.effective_chat.id == ALLOWED_GROUP_ID else None))

    print("Bot Render-da ishga tushdi...")
    app_tg.run_polling()

if __name__ == "__main__":
    main()
