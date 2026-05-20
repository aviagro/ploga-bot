# 🤖 בוט טלגרם לחיפוש בגוגל שיטס

## ✨ מה הבוט עושה
- מחפש בגוגל שיטס שלך לפי כל מונח
- מחזיר את הפרטים של השורה המתאימה בפורמט נקי
- תומך בחיפוש בכל העמודות (לא תלוי רישיות)

---

## ☁️ הרצה בענן 24/7 (מומלץ)

בלי להשאיר את המחשב דלוק — עקוב אחרי המדריך: **[DEPLOY.md](DEPLOY.md)** (Render + GitHub).

---

## 🚀 התקנה והרצה (מקומית על המחשב)

### שלב 1 — צור בוט בטלגרם
1. פתח שיחה עם [@BotFather](https://t.me/BotFather)
2. שלח `/newbot`
3. תן שם לבוט (לדוגמה: `My Sheet Bot`)
4. תן username שמסתיים ב-`bot` (לדוגמה: `mysheet_bot`)
5. העתק את ה-**Token** שקיבלת

### שלב 2 — הגדר את הגוגל שיטס
1. פתח את הגיליון שלך ב-Google Sheets
2. לחץ על **Share** (שתף) > **Anyone with the link** > **Viewer**
3. העתק את ה-URL, למשל:
   ```
   https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit
   ```
4. קח את ה-ID (החלק בין `/d/` ל-`/edit`):
   ```
   1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
   ```

### שלב 3 — עדכן את קובץ `.env`
```env
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
SHEET_CSV_URL=https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/export?format=csv
SEARCH_COLUMN=שם  # (אופציונלי — ריק = חיפוש בכל העמודות)
```

### שלב 4 — התקן תלויות
```bash
pip install -r requirements.txt
```

### שלב 5 — הרץ את הבוט
```bash
python bot.py
```

---

## 📋 פקודות הבוט

| פקודה | תיאור |
|-------|--------|
| `/start` | הצגת מסך פתיחה |
| `/search [מונח]` | חיפוש לפי מונח |
| `/list` | הצגת כל הרשומות (עד 20) |
| `/columns` | הצגת מבנה הגיליון |
| `/help` | עזרה |
| **טקסט חופשי** | חיפוש אוטומטי |

---

## 💡 טיפים

- **חיפוש חופשי**: פשוט שלח כל טקסט והבוט יחפש בכל הגיליון
- **עדכון בזמן אמת**: הבוט קורא מהגיליון בכל חיפוש — שינויים בגיליון מתעדכנים מיד
- **כמה גיליונות**: שנה את `SHEET_CSV_URL` לכל גיליון שרצית

---

## 🔧 התאמות אפשריות

ב-`bot.py` תוכל לשנות:
- `SEARCH_COLUMN` — עמודה ספציפית לחיפוש
- `head(20)` בפקודת `/list` — כמה רשומות להציג
- `format_record()` — איך להציג כל רשומה
