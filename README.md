# 🏦 Qarz Hisobchi Bot v5.0

> Telegram guruh va shaxsiy chat uchun qarz hisoblagich bot

---

## 🚀 Tez ishga tushirish

### 1. Bot yaratish (BotFather)
1. Telegramda [@BotFather](https://t.me/BotFather) ga yozing
2. `/newbot` → ism va username bering
3. **Token** ni nusxalab oling

### 2. MUHIM: Guruh uchun Privacy Mode o'chirish
```
BotFather da:
  /mybots → botingizni tanlang
  Bot Settings → Group Privacy → Turn OFF
```
Bu bo'lmasa guruhda xabarlarni o'qimaydi!

### 3. O'rnatish

**Windows:**
```bat
1. .env.example faylini .env nomi bilan saqlang
2. BOT_TOKEN=... ga tokeningizni yozing
3. start.bat ni ikki marta bosing
```

**Linux/Mac:**
```bash
cp .env.example .env
nano .env          # tokenni kiriting
pip3 install -r requirements.txt
python3 bot.py
```

---

## 💬 Qarz yozish formatlari

| Format | Misol |
|--------|-------|
| Kalit so'z bilan | `Alisher 500000 qarz` |
| Krill | `Nodira 150000 қарз` |
| Million | `Bobur 1.5 mln karz` |
| Kalit so'zsiz (YANGI!) | `Inomjon 6000` |
| Biriktirilgan (YANGI!) | `inomjon6000` |
| @username | `@sardor 300000 qarz` |

**To'lov:**
| Format | Misol |
|--------|-------|
| berdi | `Alisher 200000 berdi` |
| to'ladi | `Nodira 500000 to'ladi` |
| qaytardi | `Bobur qaytardi 100000` |

---

## 📊 Buyruqlar

| Buyruq | Tavsif |
|--------|--------|
| `/start` | Boshlash |
| `/qosh` | Qarz qo'shish (bosqichma-bosqich) |
| `/qarzlar` | Ro'yxat |
| `/top` | TOP-5 qarzdorlar 🏆 |
| `/tarix 5` | #5 qarzning to'lov tarixi |
| `/muddat` | Muddati o'tgan qarzlar ⚠️ |
| `/bekor` | Oxirgi amalni bekor qilish ↩️ |
| `/backup` | Zaxira nusxa 💾 |
| `/import` | Excel/CSV import 📥 |
| `/eslatma 5 [xabar]` | Shaxsiy eslatma 📨 |
| `/til` | Til tanlash 🌐 |

---

## 🗂 Fayl strukturasi

```
qarz_bot/
├── bot.py          # Asosiy bot (v5.0)
├── database.py     # SQLite baza
├── reporter.py     # Hisobot, grafik, PDF, Excel
├── lang.py         # Ko'p til (UZ/RU/EN)
├── requirements.txt
├── .env.example    # Token shablon
├── .env            # Sizning tokeningiz (git ga yuklamang!)
├── start.bat       # Windows ishga tushirish
├── start.sh        # Linux/Mac ishga tushirish
├── bot.log         # Log fayl (avtomatik yaratiladi)
└── qarz_bot.db     # Ma'lumotlar bazasi (avtomatik)
```

---

## ⚠️ Muhim eslatmalar

1. **Privacy Mode** — guruhda xabar o'qish uchun o'chirilishi shart
2. **.env faylini** hech qachon internet ga yuklamang
3. **backup** ni muntazam oling: `/backup`
4. Bot **admin** bo'lishi shart emas, lekin guruhda bo'lishi kerak

---

## 🖥 24/7 ishlash (ixtiyoriy)

```bash
# screen bilan (Linux)
screen -S qarz_bot
python3 bot.py
# Ctrl+A, D — fonga o'tish

# Qaytish
screen -r qarz_bot
```

---

## ☁️ Render ga deploy (bepul tarif)

1. Loyihani GitHub ga yuklang (`.env` gitga kirmasin).
2. [Render dashboard](https://dashboard.render.com/) da **New + → Blueprint** tanlang.
3. Shu repozitoriyani ulang. `render.yaml` avtomatik o'qiladi.
4. Environment variable kiriting:
   - `BOT_TOKEN` = BotFather bergan token
5. Deploy tugagach bot webhook avtomatik yoqiladi (Render URL orqali).

Eslatma:
- `WEBHOOK_URL` ni qo'lda kiritish shart emas (Render URL avtomatik olinadi).
- Free tarifda servis uyquga ketishi mumkin, birinchi so'rovda uyg'onishi uchun vaqt ketadi.
