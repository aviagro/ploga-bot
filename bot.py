import os, logging, requests, pandas as pd
from io import StringIO
from dotenv import load_dotenv
load_dotenv()
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
URL1 = os.getenv("SHEET_CSV_URL", "")
URL2 = "https://docs.google.com/spreadsheets/d/1FfsoH6nBfOIns0KhCFnNOC3E8OLibo-eA1JyTC3ubn8/export?format=csv&gid=1619129940"
logging.basicConfig(level=logging.INFO)

def fetch(url):
    try:
        r = requests.get(url, timeout=10)
        c = r.content.decode("utf-8-sig")
        df = pd.read_csv(StringIO(c))
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        logging.error(e)
        return None

def search_weapons(q):
    df = fetch(URL1)
    if df is None:
        return []
    m = df.apply(lambda row: row.astype(str).str.lower().str.contains(q.lower(), na=False).any(), axis=1)
    return df[m].to_dict(orient="records")

def search_amral(name):
    df = fetch(URL2)
    if df is None:
        return []
    name_col = df.columns[0]
    for col in df.columns:
        if "שם" in str(col):
            name_col = col
            break
    m = df[name_col].astype(str).str.lower().str.contains(name.lower(), na=False)
    return df[m].to_dict(orient="records")

def fmt_weapon(rec):
    fields = {
        "שם החייל": "👤 שם",
        "מספר אישי": "🪪 מספר אישי",
        "צוות": "🏷 צוות",
        "נשק": "🔫 נשק",
        "מספר נשק": "📌 מספר נשק",
        "כוונת": "🎯 כוונת",
        "מספר": "📌 מספר כוונת",
    }
    lines = ["─" * 22]
    for col, label in fields.items():
        if col in rec and pd.notna(rec[col]) and str(rec[col]).strip() and str(rec[col]) != "nan":
            lines.append(f"{label}: {rec[col]}")
    return "\n".join(lines)

async def start(u, c):
    await u.message.reply_text("שלום! שלח שם חייל לחיפוש\n/list - רשימה\n/columns - עמודות")

async def cols(u, c):
    df = fetch(URL1)
    if df is None:
        await u.message.reply_text("שגיאה")
        return
    cs = [x for x in df.columns if "Unnamed" not in x]
    await u.message.reply_text(" | ".join(cs))

async def lst(u, c):
    df = fetch(URL1)
    if df is None:
        await u.message.reply_text("שגיאה")
        return
    recs = df.head(20).to_dict(orient="records")
    msg = ""
    for i, r in enumerate(recs, 1):
        name = r.get("שם החייל", "")
        team = r.get("צוות", "")
        weapon = r.get("נשק", "")
        msg += f"{i}. {name} | {team} | {weapon}\n"
    await u.message.reply_text(msg)

async def srch(u, c):
    if not c.args:
        await u.message.reply_text("נא לציין מה לחפש")
        return
    await go(u, " ".join(c.args))

async def txt(u, c):
    await go(u, u.message.text)

async def go(u, q):
    await u.message.reply_text(f"מחפש {q}...")
    res = search_weapons(q)
    if not res:
        await u.message.reply_text(f"לא נמצא: {q}")
        return
    chunk = 5
    for start_i in range(0, len(res), chunk):
        batch = res[start_i:start_i+chunk]
        parts = []
        for r in batch:
            weapon_txt = fmt_weapon(r)
            name = str(r.get("שם החייל", "")).strip()
            amrals = search_amral(name) if name else []
            amral_lines = []
            for a in amrals:
                keys = list(a.keys())
                t = str(a.get(keys[2], "")).strip() if len(keys) > 2 else ""
                n = str(a.get(keys[3], "")).strip() if len(keys) > 3 else ""
                if t and t != "nan":
                    amral_lines.append(f"🔧 {t}: {n}" if n and n != "nan" else f"🔧 {t}")
            full = weapon_txt
            if amral_lines:
                full += "\n\n📦 אמרלים:\n" + "\n".join(amral_lines)
            parts.append(full)
        header = f"✅ נמצאו {len(res)} תוצאות:\n\n" if start_i == 0 else ""
        await u.message.reply_text(header + "\n\n".join(parts))

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", srch))
    app.add_handler(CommandHandler("list", lst))
    app.add_handler(CommandHandler("columns", cols))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, txt))
    print("הבוט פועל!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()