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
def main() -> None:
    """
    Botni ishga tushirish uchun asosiy funksiya.
    1. Web-serverni (Flask) alohida oqimda boshlaydi.
    2. Telegram handlerlarni ro'yxatdan o'tkazadi.
    3. Xatoliklarni nazorat qiladi.
    """
    # --- 1. Web-serverni (Render/PythonAnywhere uxlab qolmasligi uchun) boshlash ---
    try:
        server_thread = Thread(target=run_flask, daemon=True)
        server_thread.start()
        logger.info("✅ Flask web-serveri (Port: 8080) muvaffaqiyatli ishga tushdi.")
    except Exception as e:
        logger.error(f"❌ Web-serverni ishga tushirishda xatolik: {e}")
        return

    # --- 2. Telegram Application obyektini qurish ---
    try:
        # ApplicationBuilder orqali botni sozlash
        builder = Application.builder().token(BOT_TOKEN)
        
        # Ulanish vaqtini (timeouts) biroz uzaytirish (Render uchun foydali)
        builder.connect_timeout(30).read_timeout(30)
        
        app_tg = builder.build()
        logger.info("✅ Telegram Application obyekti yaratildi.")
    except Exception as e:
        logger.error(f"❌ Telegram bot tokeni bilan bog'liq xatolik: {e}")
        return

    # --- 3. Handlerlarni (Xabar boshqaruvchilarini) qo'shish ---
    # Buyruqlar bo'lmagan barcha matnlarni 'qidiruv' funksiyasiga yo'naltirish
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, qidiruv))
    
    # /start buyrug'i uchun handler
    async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Assalomu alaykum! Mahsulot kodini yozing.")
    
    app_tg.add_handler(CommandHandler("start", start_handler))

    # --- 4. Botni ishga tushirish (Polling) ---
    logger.info("🚀 Bot xabarlarni qabul qilish rejimiga o'tdi...")
    
    try:
        # 'drop_pending_updates' — bot o'chiq vaqtida kelgan eski xabarlarni e'tiborsiz qoldiradi
        app_tg.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"💥 Polling jarayonida kutilmagan xato: {e}")

# --- DASTURGA KIRISH NUQTASI ---
if __name__ == "__main__":
    # Logging darajasini sozlash (faqat INFO va undan yuqori)
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
        level=logging.INFO
    )
    
    try:
        main()
    except KeyboardInterrupt:
        # Ctrl+C bosilganda xavfsiz to'xtash
        print("\n🛑 Bot foydalanuvchi tomonidan to'xtatildi.")
    except SystemExit:
        print("🛑 Tizim botni to'xtatdi.")
