#!/bin/bash
# העלאת שינויים ל-GitHub (ואז Deploy ב-Render)
set -e
cd "$(dirname "$0")"

echo "=== בודק שינויים ==="
git status --short

if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  echo "אין שינויים להעלות."
  exit 0
fi

echo ""
echo "=== מוסיף קבצים ==="
git add bot.py requirements.txt render.yaml DEPLOY.md .gitignore README.md upload.sh העלאה.md 2>/dev/null || true
git add -u bot.py.save requirements.txtcat requirements.txtthon-telegram-bot==21.3 2>/dev/null || true

echo ""
echo "=== commit ==="
git commit -m "$(cat <<'EOF'
Add weapon update via /setweapon and sheet write support.

Includes /help, clearer errors, Google Sheets API for editing נשק and מספר נשק.
EOF
)"

echo ""
echo "=== דוחף ל-GitHub ==="
git push origin main

echo ""
echo "✅ הועלה ל-GitHub."
echo ""
echo "המשך ב-Render:"
echo "  1. https://dashboard.render.com → ploga-bot"
echo "  2. Manual Deploy → Deploy latest commit"
echo "  3. Environment → הוסף GOOGLE_SERVICE_ACCOUNT_JSON (אם עדיין לא)"
echo "  4. בטלגרם: /setweapon"
