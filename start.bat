@echo off
title Qarz Hisobchi Bot v5.0
color 0A
echo.
echo  ===================================================
echo   QARZ HISOBCHI BOT v5.0 - Windows
echo  ===================================================
echo.

REM Python borligini tekshirish
python --version >nul 2>&1
if errorlevel 1 (
    echo  [XATO] Python topilmadi!
    echo  https://python.org dan yuklab oling
    pause
    exit
)

REM .env fayli borligini tekshirish
if not exist ".env" (
    echo  [XATO] .env fayli topilmadi!
    echo  .env.example ni .env ga nusxalab, token kiriting
    pause
    exit
)

REM Kutubxonalarni o'rnatish
echo  Kutubxonalar tekshirilmoqda...
pip install -r requirements.txt -q

echo.
echo  Bot ishga tushmoqda...
echo  Toxtatish uchun: Ctrl+C
echo  ===================================================
echo.
python bot.py

if errorlevel 1 (
    echo.
    echo  [XATO] Bot to'xtadi!
    pause
)
