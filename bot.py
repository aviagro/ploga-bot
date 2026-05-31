import os, re, json, logging, requests, pandas as pd
from io import StringIO
from dotenv import load_dotenv
load_dotenv()
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
URL1 = os.getenv("SHEET_CSV_URL", "")
SHEET_ERROR = (
    "לא הצלחתי לטעון את הגיליון.\n"
    "בדוק ש-SHEET_CSV_URL מסתיים ב-/export?format=csv "
    "ושהגיליון משותף לצפייה (Anyone with the link → Viewer)."
)
HELP_TEXT = (
    "📋 פקודות:\n"
    "/search שם — חיפוש\n"
    "שלח שם חייל — חיפוש ישיר\n"
    "/setweapon — עדכון סוג נשק ומספר נשק\n"
    "  או: /setweapon שם|סוג נשק|מספר\n"
    "/list — עד 20 שמות\n"
    "/columns — עמודות בגיליון\n"
    "/cancel — ביטול עדכון נשק\n"
    "/help — עזרה"
)
SHEETS_WRITE_HELP = (
    "עדכון הגיליון דורש חשבון שירות Google.\n"
    "הוסף ב-.env / Render:\n"
    "GOOGLE_SERVICE_ACCOUNT_JSON — תוכן קובץ ה-JSON\n"
    "ושתף את הגיליון עם אימייל השירות (עורך)."
)
SW_NAME, SW_WEAPON, SW_NUMBER, SW_CONFIRM = range(4)
logging.basicConfig(level=logging.INFO)

def _editor_ids():
    raw = os.getenv("ALLOWED_EDITOR_IDS", "").strip()
    if not raw:
        return None
    return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}

def can_edit(user_id):
    allowed = _editor_ids()
    return allowed is None or user_id in allowed

def sheet_id():
    sid = os.getenv("GOOGLE_SHEET_ID", "").strip()
    if sid:
        return sid
    m = re.search(r"/d/([a-zA-Z0-9-_]+)", URL1 or "")
    return m.group(1) if m else ""

def get_worksheet():
    import gspread
    from google.oauth2.service_account import Credentials

    cred_raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if cred_raw.startswith("{"):
        info = json.loads(cred_raw)
    elif cred_path and os.path.isfile(cred_path):
        with open(cred_path, encoding="utf-8") as f:
            info = json.load(f)
    else:
        return None, SHEETS_WRITE_HELP

    sid = sheet_id()
    if not sid:
        return None, "חסר מזהה גיליון (GOOGLE_SHEET_ID או SHEET_CSV_URL תקין)."

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    ws = gspread.authorize(creds).open_by_key(sid).sheet1
    return ws, None

def find_soldier_rows(ws, name):
    headers = [str(h).strip() for h in ws.row_values(1)]
    if "שם החייל" not in headers:
        return None, "חסרה עמודה 'שם החייל' בגיליון."
    col_name = headers.index("שם החייל") + 1
    name_norm = name.strip().lower()
    rows = []
    for row_idx, row in enumerate(ws.get_all_values()[1:], start=2):
        if len(row) < col_name:
            continue
        if str(row[col_name - 1]).strip().lower() == name_norm:
            rows.append(row_idx)
    if not rows:
        return None, f"לא נמצא חייל: {name}"
    return rows, None

def update_weapon_in_sheet(name, weapon_type, weapon_number):
    ws, err = get_worksheet()
    if err:
        return False, err

    headers = [str(h).strip() for h in ws.row_values(1)]
    for col in ("נשק", "מספר נשק"):
        if col not in headers:
            return False, f"חסרה עמודה '{col}' בגיליון."

    rows, err = find_soldier_rows(ws, name)
    if err:
        return False, err

    col_weapon = headers.index("נשק") + 1
    col_num = headers.index("מספר נשק") + 1
    for row_idx in rows:
        ws.update_cell(row_idx, col_weapon, weapon_type)
        ws.update_cell(row_idx, col_num, str(weapon_number))
    return True, (
        f"✅ עודכן עבור {name} ({len(rows)} שורות):\n"
        f"🔫 נשק: {weapon_type}\n"
        f"📌 מספר נשק: {weapon_number}"
    )

def parse_setweapon_args(text):
    if "|" not in text:
        return None
    parts = [p.strip() for p in text.split("|")]
    if len(parts) != 3 or not all(parts):
        return None
    return {"name": parts[0], "weapon": parts[1], "number": parts[2]}

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

def search(q, df=None):
    if df is None:
        df = fetch()
    if df is None:
        return None
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
    await u.message.reply_text(
        "שלום! שלח שם חייל לחיפוש, או /help לעזרה.\n"
        "/list — רשימה | /columns — עמודות"
    )

async def help_cmd(u, c):
    await u.message.reply_text(HELP_TEXT)

async def cols(u, c):
    df = fetch()
    if df is None:
        await u.message.reply_text(SHEET_ERROR)
        return
    cs = [x for x in df.columns if "Unnamed" not in x]
    await u.message.reply_text(" | ".join(cs))

async def lst(u, c):
    df = fetch()
    if df is None:
        await u.message.reply_text(SHEET_ERROR)
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

async def setweapon_entry(u, c):
    if not can_edit(u.effective_user.id):
        await u.message.reply_text("אין לך הרשאה לעדכן נשק.")
        return ConversationHandler.END

    rest = (u.message.text or "").split(maxsplit=1)
    rest = rest[1].strip() if len(rest) > 1 else ""
    one = parse_setweapon_args(rest) if rest else None
    if one:
        ok, msg = update_weapon_in_sheet(one["name"], one["weapon"], one["number"])
        await u.message.reply_text(msg if ok else f"❌ {msg}")
        return ConversationHandler.END

    c.user_data["sw"] = {}
    await u.message.reply_text(
        "עדכון נשק — שלח את שם החייל:\n"
        "(או ביטול: /cancel)\n\n"
        "טיפ: /setweapon שם|סוג נשק|מספר"
    )
    return SW_NAME

async def sw_name(u, c):
    name = u.message.text.strip()
    if not name:
        await u.message.reply_text("נא לשלוח שם חייל.")
        return SW_NAME
    c.user_data["sw"]["name"] = name
    df = fetch()
    if df is not None:
        hits = df[df["שם החייל"].astype(str).str.strip().str.lower() == name.lower()]
        if hits.empty:
            await u.message.reply_text(f"⚠️ לא נמצא '{name}' בגיליון — אפשר להמשיך בכל זאת.")
        else:
            w = str(hits.iloc[0].get("נשק", "")).strip()
            n = str(hits.iloc[0].get("מספר נשק", "")).strip()
            cur = f"\nנוכחי: {w or '—'} | {n or '—'}" if w or n else ""
            await u.message.reply_text(f"נמצא: {name}{cur}")
    await u.message.reply_text("שלח סוג נשק (למשל: מיקרו תבור):")
    return SW_WEAPON

async def sw_weapon(u, c):
    weapon = u.message.text.strip()
    if not weapon:
        await u.message.reply_text("נא לשלוח סוג נשק.")
        return SW_WEAPON
    c.user_data["sw"]["weapon"] = weapon
    await u.message.reply_text("שלח מספר נשק:")
    return SW_NUMBER

async def sw_number(u, c):
    number = u.message.text.strip()
    if not number:
        await u.message.reply_text("נא לשלוח מספר נשק.")
        return SW_NUMBER
    c.user_data["sw"]["number"] = number
    d = c.user_data["sw"]
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ אישור", callback_data="sw_ok"),
            InlineKeyboardButton("❌ ביטול", callback_data="sw_no"),
        ]
    ])
    await u.message.reply_text(
        f"לאשר עדכון?\n\n"
        f"👤 {d['name']}\n"
        f"🔫 נשק: {d['weapon']}\n"
        f"📌 מספר: {d['number']}",
        reply_markup=kb,
    )
    return SW_CONFIRM

async def sw_confirm(u, c):
    q = u.callback_query
    await q.answer()
    if q.data == "sw_no":
        await q.edit_message_text("בוטל.")
        return ConversationHandler.END
    d = c.user_data.get("sw", {})
    if not d.get("name"):
        await q.edit_message_text("שגיאה — התחל מחדש עם /setweapon")
        return ConversationHandler.END
    ok, msg = update_weapon_in_sheet(d["name"], d["weapon"], d["number"])
    await q.edit_message_text(msg if ok else f"❌ {msg}")
    return ConversationHandler.END

async def cancel_cmd(u, c):
    await u.message.reply_text("בוטל.")
    return ConversationHandler.END

async def go(u, q):
    await u.message.reply_text(f"מחפש {q}...")
    res = search(q)
    if res is None:
        await u.message.reply_text(SHEET_ERROR)
        return
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
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("search", srch))
    app.add_handler(CommandHandler("list", lst))
    app.add_handler(CommandHandler("columns", cols))
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("setweapon", setweapon_entry)],
            states={
                SW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, sw_name)],
                SW_WEAPON: [MessageHandler(filters.TEXT & ~filters.COMMAND, sw_weapon)],
                SW_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, sw_number)],
                SW_CONFIRM: [CallbackQueryHandler(sw_confirm, pattern="^sw_")],
            },
            fallbacks=[CommandHandler("cancel", cancel_cmd)],
            allow_reentry=True,
        )
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, txt))
    print("הבוט פועל!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()