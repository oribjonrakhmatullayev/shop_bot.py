# -*- coding: utf-8 -*-
import logging, requests, csv, io, os, re
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- RENDER UCHUN SERVER (Bot uxlab qolmasligi uchun) ---
app = Flask('')
@app.route('/')
def home(): return "Bot ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- SOZLAMALAR ---
BOT_TOKEN  = "8275086123:AAFa8sY3eUsNBRyKGLA-W47AY1UPyOyrF8U"
SHEET_URL  = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ5Y5lhFw0cKz8UuVb_fjbv1JKT0ncQYPxihlAycO9cGyZa2E92TKZB3fNx8er9N5EclXKNyzB63Fe7/pub?gid=1315694608&single=true&output=csv"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- MA'LUMOTLARNI YUKLASH ---
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
                "kod": row[0].strip().upper(),
                "nom": row[2].strip().split('\n')[0],
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
    return (
        f"✨ Greenleaf Сифати — Сизнинг саломатлигингиз учун! ✨\n\n"
        f"🧼 Маҳсулот: {p['nom']}\n"
        f"🆔 Код: {p['kod']}\n"
        f"💰 Хамкор нархи: {format_price(p['narx'])} сўм\n"
        f"💎 Балл: {p['ball']} PV\n\n"
        f"✅ {tavsiya}\n\n"
        f"🛒 Буюртма: https://t.me/ORIFFFFFFFFFF\n"
        f"📞 Тел: +998 33 993 4070"
    )

async def qidiruv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Hech qanday guruh yoki mavzu filtri yo'q - hamma joyda ishlaydi
    text = update.message.text.strip().upper()
    if len(text) < 2: return
    
    # ASF063ASF063 kabi xatolarni tozalash (faqat birinchi kodni oladi)
    match = re.search(r'[A-Z]{2,3}\d{2,4}', text)
    query = match.group(0) if match else text[:10]

    products, _ = fetch_products()
    # Kod bo'yicha aniq qidirish
    res = [p for p in products if query == p["kod"]]
    
    # Agar aniq kod topilmasa, nomi bo'yicha qisman qidirish
    if not res:
        res = [p for p in products if query in p["kod"] or query.lower() in p["nom"].lower()]

    if res:
        if len(res) == 1:
            await update.message.reply_text(make_card(res[0]))
        else:
            resp_text = f"✅ Шу сўров бўйича {len(res)} та натижа:\n\n"
            for p in res[:10]:
                resp_text += f"• {p['nom']} (Код: {p['kod']})\n"
            resp_text += "\nБатафсил маълумот учун kodni тўлиқ ёзинг."
            await update.message.reply_text(resp_text)

def main():
    # Render'da bot o'chib qolmasligi uchun serverni boshlash
    Thread(target=run_flask, daemon=True).start()
    
    app_tg = Application.builder().token(BOT_TOKEN).build()
    
    # Barcha matnli xabarlarni qabul qilish
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, qidiruv))
    
    app_tg.run_polling()

if __name__ == "__main__":
    main()
