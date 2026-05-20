import os, logging, requests, pandas as pd
from io import StringIO
from dotenv import load_dotenv
load_dotenv()
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
URL1 = os.getenv("SHEET_CSV_URL", "")
logging.basicConfig(level=logging.INFO)

def fetch():
    try:
        r = requests.get(URL1, timeout=10)
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
    results = df[m]
    # קבץ לפי שם חייל
    grouped = {}
    for _, row in results.iterrows():
        name = str(row.get("שם החייל", "")).strip()
        if name not in grouped:
            grouped[name] = []
        grouped[name].append(row.to_dict())
    return list(grouped.values())

def fmt(rows):
    r = rows[0]
    lines = ["─" * 22]
    def val(k):
        v = r.get(k, "")
        return str(v).strip() if pd.notna(v) and str(v).strip() not in ["nan", ""] else ""

    if val("שם החייל"): lines.append(f"👤 שם: {val('שם החייל')}")
    if val("מספר אישי"): lines.append(f"🪪 מספר אישי: {val('מספר אישי')}")
    if val("צוות"): lines.append(f"🏷 צוות: {val('צוות')}")
    if val("נשק"): lines.append(f"🔫 נשק: {val('נשק')}")
    if val("מספר נשק"): lines.append(f"📌 מספר נשק: {val('מספר נשק')}")
    if val("כוונת"): lines.append(f"🎯 כוונת: {val('כוונת')}")
    if val("מספר"): lines.append(f"📌 מספר כוונת: {val('מספר')}")

    # אמרלים מכל השורות
    amrals = []
    for row in rows:
        sug = str(row.get("סוג אמרל", "")).strip()
        num = str(row.get("מספר אמרל", "")).strip()
        extra = str(row.get("אמרל נוסף", "")).strip()
        if sug and sug != "nan":
            amrals.append(f"🔧 {sug}: {num}" if num and num != "nan" else f"🔧 {sug}")
        if extra and extra != "nan":
            amrals.append(f"🔧 {extra}")

    if amrals:
        lines.append("\n📦 אמרלים:")
        lines.extend(amrals)

    # חתם 30/4
    chatam = str(r.get("חתם 30/4", r.get("חתם 30\\4", r.get("30/4", "")))).strip()
    if chatam and chatam not in ["nan", ""]:
        lines.append(f"\n✅ חתם 30/4: {'כן' if chatam == '1' else chatam}")

    return "\n".join(lines)

async def start(u, c):
    await u.message.reply_text("שלום! שלח שם חייל לחיפוש\n/list - רשימה\n/columns - עמודות")

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
    seen = set()
    for r in recs:
        name = r.get("שם החייל", "")
        if name in seen:
            continue
        seen.add(name)
        team = r.get("צוות", "")
        weapon = r.get("נשק", "")
        msg += f"{name} | {team} | {weapon}\n"
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
    chunk = 5
    for start_i in range(0, len(res), chunk):
        batch = res[start_i:start_i+chunk]
        parts = [fmt(r) for r in batch]
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