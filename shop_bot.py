# -*- coding: utf-8 -*-
import logging, requests, csv, io, json, os
from flask import Flask
from threading import Thread
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler, filters, ContextTypes

# --- RENDER PORT SOZLAMASI ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    # Render PORTni avtomatik beradi, agar bermasa 8080 ishlatiladi
    port = int(os.environ.get("PORT", 8080))
    # '0.0.0.0' orqali Render tashqaridan ulanishi mumkin bo'ladi
    app.run(host='0.0.0.0', port=port)

# --- BOT SOZLAMALARI ---
BOT_TOKEN  = "8275086123:AAFM8iifVbe8cidhE07hoEbQ0svwqvRB8ac"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=AIzaSyDTnMjVzYH6utYWodJS2X06ifZTB72HH8o"
# Yangi jadval: A:Kod, C:Nomi, D:Narxi, E:PV
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
            kod = row[0].strip()
            nom = row[2].strip().split('\n')[0] 
            narx = row[3].strip().lower().replace(" uzs","").replace(",","").replace(" ","").strip()
            ball = row[4].strip() if row[4].strip() else "0"
            if kod and nom:
                products.append({"kod": kod, "nom": nom, "narx": narx, "ball": ball})
        return products, None
    except Exception as e:
        return [], str(e)

def format_price(narx):
    try:
        num = "".join(filter(str.isdigit, str(narx)))
        return "{:,}".format(int(num)).replace(",", " ")
    except: return narx

def search_products(query, products):
    q = query.lower().strip()
    return [p for p in products if q in p["kod"].lower() or q in p["nom"].lower()]

async def gemini_call(prompt):
    try:
        resp = requests.post(GEMINI_URL, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except: return ""

async def get_tavsiya(nom):
    res = await gemini_call(f"Mahsulot uchun Ozbekcha qisqa tavsiya (max 10 soz): {nom}")
    return res or "Sog'liq uchun foydali!"

def make_card(p, tavsiya=""):
    msg = f"✨ *Greenleaf Sifati*\n\n🧼 *Nom:* {p['nom']}\n🆔 *Kod:* `{p['kod']}`\n💰 *Narx:* {format_price(p['narx'])} so'm\n💎 *Ball:* {p['ball']} PV"
    if tavsiya: msg += f"\n✅ _{tavsiya}_"
    return msg

async def start(update, context):
    await update.message.reply_text("👋 *Assalomu alaykum!*\nKodi yoki nomini yozing.\n/barchasi | /yangilash", parse_mode="Markdown")

async def barchasi(update, context):
    products, error = fetch_products()
    if error: await update.message.reply_text(f"Xato: {error}"); return
    context.user_data["all_products"] = products
    await send_page(update, context, products, 0)

async def send_page(update, context, products, page):
    PS = 10
    si, ei = page*PS, (page+1)*PS
    text = f"📋 *Mahsulotlar* ({len(products)} ta)\n\n"
    for p in products[si:ei]:
        text += f"• `{p['kod']}` — {p['nom']} | {format_price(p['narx'])}\n"
    btns = []
    if page > 0: btns.append(InlineKeyboardButton("⬅️", callback_data=f"page_{page-1}"))
    if ei < len(products): btns.append(InlineKeyboardButton("➡️", callback_data=f"page_{page+1}"))
    kb = InlineKeyboardMarkup([btns]) if btns else None
    if update.callback_query: await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else: await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def page_cb(update, context):
    await update.callback_query.answer()
    page = int(update.callback_query.data.split("_")[1])
    products = context.user_data.get("all_products") or fetch_products()[0]
    await send_page(update, context, products, page)

async def yangilash(update, context):
    msg = await update.message.reply_text("🔄 Yangilanmoqda...")
    products, error = fetch_products()
    if error: await msg.edit_text(f"❌ Xato: {error}")
    else: await msg.edit_text(f"✅ Jami: *{len(products)}* ta.", parse_mode="Markdown")

async def qidiruv(update, context):
    query = update.message.text.strip()
    if len(query) < 2: return
    msg = await update.message.reply_text("🔍...")
    products, _ = fetch_products()
    res = search_products(query, products)
    if res:
        if len(res) == 1:
            t = await get_tavsiya(res[0]["nom"])
            await msg.edit_text(make_card(res[0], t), parse_mode="Markdown")
        else:
            text = f"✅ *{len(res)}* natija:\n"
            for p in res[:15]: text += f"• `{p['kod']}` — {p['nom']}\n"
            await msg.edit_text(text, parse_mode="Markdown")
    else: await msg.edit_text("😔 Topilmadi.")

def main():
    # Render Port binding uchun Flaskni alohida thread'da boshlash (SHART!)
    Thread(target=run_flask).start()
    
    app_tg = Application.builder().token(BOT_TOKEN).build()
    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(CommandHandler("barchasi", barchasi))
    app_tg.add_handler(CommandHandler("yangilash", yangilash))
    app_tg.add_handler(CallbackQueryHandler(page_cb, pattern=r"^page_\d+$"))
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, qidiruv))
    
    # Botni ishga tushirish
    app_tg.run_polling()

if __name__ == "__main__":
    main()
