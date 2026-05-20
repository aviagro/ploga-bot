# הפעלת הבוט בענן (24/7 בלי המחשב)

הבוט רץ על **Render** — שירות חינמי שמחובר ל-GitHub שלך.

## שלב 1 — חשבון Render

1. היכנס ל-[render.com](https://render.com) והירשם (אפשר עם חשבון Google/GitHub).
2. אשר את החיבור ל-GitHub אם מתבקש.

## שלב 2 — פריסה מהריפו

1. בלוח ב-Render: **New +** → **Blueprint**.
2. בחר את הריפו: `aviagro/ploga-bot`.
3. Render יזהה את `render.yaml` — לחץ **Apply**.

## שלב 3 — משתני סביבה (חובה — בלי זה הפריסה נכשלת!)

1. ב-Render לחץ על השירות **ploga-bot**
2. בתפריט השמאלי: **Environment**
3. הוסף **שני משתנים** (העתק מהקובץ `.env` במחשב שלך):

| Key | Value |
|-----|-------|
| `TELEGRAM_TOKEN` | המספר הארוך מ-BotFather |
| `SHEET_CSV_URL` | קישור ה-CSV של הגוגל שיטס |

4. **Save, rebuild, and deploy** (או Manual Deploy)

ב-Logs אמור להופיע: `TOKEN set=True` ו-`SHEET_CSV_URL set=True` — אם `False`, המשתנה לא הוגדר.

## שלב 4 — בדיקה

1. חכה שסטטוס השירות יהיה **Live** (ירוק).
2. בטלגרם — שלח לבוט שם חייל.
3. **כבה את הבוט על המחשב** (אם הרצת אותו מקומית) — רק עותק אחד יכול לרוץ.

## אם הבוט לא מגיב

1. ב-Render → **Logs** — חייב להופיע: `הבוט פועל בענן (webhook): https://...`
2. אם יש `Conflict` או `tornado` — לחץ **Manual Deploy** (אחרי עדכון קוד מ-GitHub).
3. ודא ש-`TELEGRAM_TOKEN` ו-`SHEET_CSV_URL` מוגדרים ב-Environment.
4. **אל תריץ** `python bot.py` על המחשב במקביל ל-Render.
5. בדיקה: פתח בדפדפן `https://שם-השירות.onrender.com/health` — אמור להופיע `ok`.

## עלות

תוכנית **Free** — מספיק לשימוש רגיל. אחרי כמה דקות בלי פעילות השרת "נרדם"; הודעה ראשונה בטלגרם עלולה לקחת כמה שניות עד שהוא מתעורר.
