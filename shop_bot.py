# -*- coding: utf-8 -*-
import logging, requests, csv, io, json
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler, filters, ContextTypes

# --- SOZLAMALAR ---
BOT_TOKEN  = "8275086123:AAFM8iifVbe8cidhE07hoEbQ0svwqvRB8ac"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=AIzaSyDTnMjVzYH6utYWodJS2X06ifZTB72HH8o"

# Faqat yangi baza (Rasmda ko'rsatilgan struktura)
SHEET_URL  = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ5Y5lhFw0cKz8UuVb_fjbv1JKT0ncQYPxihlAycO9cGyZa2E92TKZB3fNx8er9N5EclXKNyzB63Fe7/pub?gid=1315694608&single=true&output=csv"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_products():
    try:
        r = requests.get(SHEET_URL, timeout=15)
        r.raise_for_status()
        rows = list(csv.reader(io.StringIO(r.content.decode("utf-8"))))
        
        products = []
        # Yangi jadval ustunlari: 0:Kod, 2:Nom, 3:Narx, 4:Ball
        i = 1 
        while i < len(rows):
            row = rows[i]
            if not row or len(row) < 5 or not row[0].strip():
                i += 1
                continue
            
            kod  = row[0].strip()
            # Nomdan "Manbada mavjud..." kabi pastki qatorlarni olib tashlash
            nom  = row[2].strip().split('\n')[0] 
            # Narxdan "uzs" va bo'shliqlarni olib tashlash
            narx = row[3].strip().lower().replace(" uzs","").replace(",","").replace(" ","").strip()
            ball = row[4].strip() if row[4].strip() else "0"
            
            if kod and nom:
                products.append({"kod": kod, "nom": nom, "narx": narx, "ball": ball})
            i += 1
        return products, None
    except Exception as e:
        logger.error(f"Baza yuklashda xato: {e}")
        return [], str(e)

def format_price(narx):
    try:
        num = "".join(filter(str.isdigit, str(narx)))
        return "{:,}".format(int(num)).replace(",", " ")
    except:
        return narx

def search_products(query, products):
    q = query.lower().strip()
    return [p for p in products if q in p["kod"].lower() or q in p["nom"].lower()]

async def gemini_call(prompt):
    try:
        resp = requests.post(GEMINI_URL, headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except:
        return ""

async def get_tavsiya(nom):
    result = await gemini_call("Mahsulot uchun Ozbek tilida 1 qisqa tavsiya yoz (max 15 soz). Faqat tavsiya: " + nom)
    return result or "Sog'ligingiz uchun foydali mahsulot!"

async def ai_search(query, products):
    plist = "\n".join([f"{i+1}. Kod:{p['kod']} Nom:{p['nom']}" for i,p in enumerate(products[:300])])
    prompt = f'Savol: "{query}"\nJavobni faqat JSON: {{"kodlar":["KOD1"],"tavsiya":"..."}}\nRo\'yxat:\n{plist}'
    raw = await gemini_call(prompt)
    try:
        clean = raw.replace("```json","").replace("```","").strip()
        return json.loads(clean)
    except:
        return {"kodlar": [], "tavsiya": ""}

def make_card(p, tavsiya=""):
    msg = "✨ *Greenleaf Sifati* ✨\n\n"
    msg += f"🧼 *Mahsulot:* {p['nom']}\n"
    msg += f"🆔 *Kod:* `{p['kod']}`\n"
    msg += f"💰 *Narx:* {format_price(p['narx'])} so'm\n"
    msg += f"💎 *Ball:* {p['ball']} PV"
    if tavsiya:
        msg += f"\n✅ _{tavsiya}_"
    return msg

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Assalomu alaykum!*\n\n🔍 Mahsulot kodi yoki nomini yozing.\n📋 /barchasi — hamma mahsulotlar\n🔄 /yangilash — bazani yangilash",
        parse_mode="Markdown"
    )

async def barchasi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products, error = fetch_products()
    if error:
        await update.message.reply_text(f"Xato: {error}")
        return
    context.user_data["all_products"] = products
    await send_page(update, context, products, 0)

async def send_page(update, context, products, page):
    PS = 10
    si, ei = page*PS, (page+1)*PS
    text = f"📋 *Barcha mahsulotlar* ({len(products)} ta)\n_{page+1}-sahifa_\n\n"
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

async def page_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    page = int(update.callback_query.data.split("_")[1])
    products = context.user_data.get("all_products") or fetch_products()[0]
    await send_page(update, context, products, page)

async def yangilash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔄 Yangilanmoqda...")
    products, error = fetch_products()
    if error:
        await msg.edit_text(f"❌ Xato: {error}")
    else:
        await msg.edit_text(f"✅ Yangilandi! Jami: *{len(products)}* ta mahsulot.", parse_mode="Markdown")

async def qidiruv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if len(query) < 2: return
    
    msg = await update.message.reply_text("🔍 Qidirilmoqda...")
    products, _ = fetch_products()
    results = search_products(query, products)
    
    if results:
        if len(results) == 1:
            tavsiya = await get_tavsiya(results[0]["nom"])
            await msg.edit_text(make_card(results[0], tavsiya), parse_mode="Markdown")
        else:
            text = f"✅ *{len(results)}* ta natija:\n\n"
            for p in results[:15]:
                text += f"• `{p['kod']}` — {p['nom']} | {format_price(p['narx'])} so'm\n"
            await msg.edit_text(text, parse_mode="Markdown")
        return

    await msg.edit_text("🤖 AI qidirmoqda...")
    ai = await ai_search(query, products)
    found = [p for p in products if p["kod"] in ai.get("kodlar", [])]
    
    if not found:
        await msg.edit_text(f"😔 *'{query}'* topilmadi.")
        return
        
    text = f"💡 *'{query}'* uchun tavsiyalar:\n\n"
    for p in found[:5]:
        text += f"📦 *{p['nom']}*\n`{p['kod']}` | {format_price(p['narx'])} so'm\n\n"
    await msg.edit_text(text, parse_mode="Markdown")

async def inline_qidiruv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if len(query) < 2: return
    products, _ = fetch_products()
    results = search_products(query, products)[:10]
    answers = [InlineQueryResultArticle(id=p["kod"], title=p["nom"], 
               description=f"{format_price(p['narx'])} so'm",
               input_message_content=InputTextMessageContent(make_card(p), parse_mode="Markdown")) for p in results]
    await update.inline_query.answer(answers, cache_time=30)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("barchasi", barchasi))
    app.add_handler(CommandHandler("yangilash", yangilash))
    app.add_handler(CallbackQueryHandler(page_cb, pattern=r"^page_\d+$"))
    app.add_handler(InlineQueryHandler(inline_qidiruv))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, qidiruv))
    print("Bot faqat yangi baza bilan ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()