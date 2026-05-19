import os, logging, requests, pandas as pd
from io import StringIO
from dotenv import load_dotenv
load_dotenv()
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
URL = os.getenv("SHEET_CSV_URL", "")
logging.basicConfig(level=logging.INFO)

def fetch():
    try:
        r = requests.get(URL, timeout=10)
        c = r.content.decode("utf-8-sig")
        df = pd.read_csv(StringIO(c))
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        logging.error(e)
        return None

def search(q):
    df = fetch()
    if df is None:
        return []
    m = df.apply(lambda row: row.astype(str).str.lower().str.contains(q.lower(), na=False).any(), axis=1)
    return df[m].to_dict(orient="records")

def fmt(rec, i=None):
    # שדות לתצוגה בלבד
    fields = {
        "שם החייל": "שם",
        "מספר אישי": "מספר אישי",
        "מספר נשק": "מספר נשק",
        "מספר": "מספר אמרל",
        "כוונת": "סוג אמרל",
    }
    lines = []
    if i:
        lines.append(f"תוצאה {i}")
    lines.append("-" * 20)
    for col, label in fields.items():
        if col in rec and pd.notna(rec[col]) and str(rec[col]).strip() and str(rec[col]) != "nan":
            lines.append(f"{label}: {rec[col]}")
    return "\n".join(lines)

async def start(u, c):
    await u.message.reply_text("שלום! שלח שם חייל או שם צוות לחיפוש\n/list - רשימה\n/columns - עמודות")

async def cols(u, c):
    df = fetch()
    if df is None:
        await u.message.reply_text("שגיאה")
        return
    cs = [x for x in df.columns if "Unnamed" not in x]
    await u.message.reply_text(" | ".join(cs))

async def lst(u, c):
    df = fetch()
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
    res = search(q)
    if not res:
        await u.message.reply_text(f"לא נמצא: {q}")
        return
    # חלק לפי הודעות של 10 תוצאות כל אחת (מגבלת טלגרם)
    chunk = 10
    for start_i in range(0, len(res), chunk):
        batch = res[start_i:start_i+chunk]
        parts = [fmt(r, start_i+i+1) for i, r in enumerate(batch)]
        header = f"נמצאו {len(res)} תוצאות:\n\n" if start_i == 0 else ""
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
