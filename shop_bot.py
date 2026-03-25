# -*- coding: utf-8 -*-
import logging, requests, csv, io, json, os
from flask import Flask
from threading import Thread
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler, filters, ContextTypes

# --- RENDER PORT SOZLAMASI (MUHIM) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    # Render avtomatik beradigan PORTni olish
    port = int(os.environ.get("PORT", 8080))
    # 0.0.0.0 Render uchun shart
    app.run(host='0.0.0.0', port=port)

# --- BOT SOZLAMALARI ---
# Yangi tokenni kiritganingizga ishonch hosil qiling
BOT_TOKEN  = "8275086123:AAFa8sY3eUsNBRyKGLA-W47AY1UPyOyrF8U"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=AIzaSyDTnMjVzYH6utYWodJS2X06ifZTB72HH8o"
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
    except Exception as e:
        return [], str(e)

def format_price(narx):
    try:
        num = "".join(filter(str.isdigit, str(narx)))
        return "{:,}".format(int(num)).replace(",", " ")
    except: return narx

async def start(update, context):
    await update.message.reply_text("👋 *Greenleaf Botga xush kelibsiz!*\n\nKodi yoki nomini yozing.\n/barchasi — Hamma mahsulotlar", parse_mode="Markdown")

async def barchasi(update, context):
    products, error = fetch_products()
    if error:
        await update.message.reply_text(f"Xato: {error}")
        return
    context.user_data["all_products"] = products
    await send_page(update, context, products, 0)

async def send_page(update, context, products, page):
    PS = 10
    si, ei = page*PS, (page+1)*PS
    text = f"📋 *Mahsulotlar* ({len(products)} ta)\n_{page+1}-sahifa_\n\n"
    for p in products[si:ei]:
        text += f"• `{p['kod']}` — {p['nom']} | {format_price(p['narx'])} so'm\n"
    
    btns = []
    if page > 0: btns.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"page_{page-1}"))
    if ei < len(products): btns.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"page_{page+1}"))
    
    kb = InlineKeyboardMarkup([btns]) if btns else None
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def page_cb(update, context):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("_")[1])
    products = context.user_data.get("all_products")
    if not products:
        products, _ = fetch_products()
        context.user_data["all_products"] = products
    await send_page(update, context, products, page)

async def qidiruv(update, context):
    query = update.message.text.strip()
    if len(query) < 2: return
    products, _ = fetch_products()
    res = [p for p in products if query.lower() in p["kod"].lower() or query.lower() in p["nom"].lower()]
    if res:
        if len(res) == 1:
            p = res[0]
            msg = f"✨ *Mahsulot:* {p['nom']}\n🆔 *Kod:* `{p['kod']}`\n💰 *Narx:* {format_price(p['narx'])} so'm\n💎 *Ball:* {p['ball']} PV"
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            text = f"✅ *{len(res)}* natija:\n"
            for p in res[:15]: text += f"• `{p['kod']}` — {p['nom']}\n"
            await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text("😔 Topilmadi.")

def main():
    # Flaskni alohida thread'da ishga tushirish
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    # Telegram Botni ishga tushirish
    app_tg = Application.builder().token(BOT_TOKEN).build()
    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(CommandHandler("barchasi", barchasi))
    app_tg.add_handler(CallbackQueryHandler(page_cb, pattern=r"^page_\d+$"))
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, qidiruv))
    
    app_tg.run_polling()

if __name__ == "__main__":
    main()
