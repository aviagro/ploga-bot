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

def cell_val(row, key):
    v = row.get(key, "")
    return str(v).strip() if pd.notna(v) and str(v).strip() not in ["nan", ""] else ""

def first_val(rows, key):
    for row in rows:
        v = cell_val(row, key)
        if v:
            return v
    return ""

def ameral_entries(rows):
    entries = []
    for row in rows:
        entry = {
            "סוג": cell_val(row, "סוג אמרל"),
            "מספר": cell_val(row, "מספר אמרל"),
            "נוסף": cell_val(row, "אמרל נוסף"),
        }
        if any(entry.values()):
            entries.append(entry)
    return entries

def fmt_ameral_lines(entries):
    lines = []
    multi = len(entries) > 1
    for i, e in enumerate(entries, 1):
        if multi:
            lines.append(f"\n📦 אמרל {i}:")
        elif not lines:
            lines.append("\n📦 אמרל:")
        if e["סוג"]:
            lines.append(f"סוג אמרל: {e['סוג']}")
        if e["מספר"]:
            lines.append(f"מספר אמרל: {e['מספר']}")
        if e["נוסף"]:
            lines.append(f"אמרל נוסף: {e['נוסף']}")
    return lines

def fmt(rows):
    r = rows[0]
    lines = ["─" * 22]
    val = lambda k: cell_val(r, k)

    if val("שם החייל"): lines.append(f"👤 שם: {val('שם החייל')}")
    if val("מספר אישי"): lines.append(f"🪪 מספר אישי: {val('מספר אישי')}")
    if val("צוות"): lines.append(f"🏷 צוות: {val('צוות')}")
    if val("נשק"): lines.append(f"🔫 נשק: {val('נשק')}")
    if val("מספר נשק"): lines.append(f"📌 מספר נשק: {val('מספר נשק')}")
    if val("כוונת"): lines.append(f"🎯 כוונת: {val('כוונת')}")
    if val("מספר"): lines.append(f"📌 מספר כוונת: {val('מספר')}")

    entries = ameral_entries(rows)
    if entries:
        lines.extend(fmt_ameral_lines(entries))

    when_signed = first_val(rows, "מתי חתם")
    if when_signed:
        lines.append(f"מתי חתם: {when_signed}")

    zoche = first_val(rows, "זוכה")
    if zoche:
        lines.append(f"זוכה: {zoche}")

    chatam = first_val(rows, "חתם 30/4") or first_val(rows, "חתם 30\\4") or first_val(rows, "30/4")
    if chatam:
        lines.append(f"✅ חתם 30/4: {'כן' if chatam == '1' else chatam}")

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
    if not TOKEN:
        print("שגיאה: חסר TELEGRAM_TOKEN")
        raise SystemExit(1)
    if not URL1:
        print("שגיאה: חסר SHEET_CSV_URL")
        raise SystemExit(1)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", srch))
    app.add_handler(CommandHandler("list", lst))
    app.add_handler(CommandHandler("columns", cols))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, txt))

    on_render = os.getenv("RENDER") == "true"
    webhook_base = (os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL", "")).rstrip("/")

    if on_render and webhook_base:
        port = int(os.getenv("PORT", "10000"))
        path = os.getenv("WEBHOOK_PATH", "webhook")
        url = f"{webhook_base}/{path}"
        print(f"הבוט פועל בענן (webhook): {url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=path,
            webhook_url=url,
            allowed_updates=Update.ALL_TYPES,
        )
    else:
        print("הבוט פועל!")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()