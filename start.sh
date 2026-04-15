#!/bin/bash
echo ""
echo "==================================================="
echo "  QARZ HISOBCHI BOT v5.0 - Linux/Mac"
echo "==================================================="
echo ""

# Python tekshirish
if ! command -v python3 &> /dev/null; then
    echo "[XATO] Python3 topilmadi!"
    echo "sudo apt install python3 python3-pip"
    exit 1
fi

# .env tekshirish
if [ ! -f ".env" ]; then
    echo "[XATO] .env fayli topilmadi!"
    echo ".env.example ni .env ga nusxalab, token kiriting"
    exit 1
fi

# Kutubxonalar
echo "Kutubxonalar tekshirilmoqda..."
pip3 install -r requirements.txt -q

echo ""
echo "Bot ishga tushmoqda... (To'xtatish: Ctrl+C)"
echo "==================================================="
echo ""
python3 bot.py
