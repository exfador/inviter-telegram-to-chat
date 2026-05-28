

[![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white&style=for-the-badge)](https://www.python.org/)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-2.0-1c93e3?style=for-the-badge)](https://docs.pyrogram.org/)
[![License](https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge)](LICENSE)
[![Telegram](https://img.shields.io/badge/contact-%40exfador-26A5E4?logo=telegram&logoColor=white&style=for-the-badge)](https://t.me/exfador)

---

**Массовый инвайтер пользователей в Telegram-чаты.** Несколько сессий, residential-прокси с ротацией, обработка всех ошибок Pyrogram, заморозка с TTL вместо вечных банов, авто-восстановление после `PeerFlood` — работает 24/7 без вмешательства.

<table>
<tr>
<td align="center" width="33%">

### 💎 Sponsor
**[neversmm.com](https://neversmm.com)**<br>
самая дешёвая SMM-накрутка

</td>
<td align="center" width="33%">

### 👤 Author
**[@exfador](https://t.me/exfador)**<br>
заказ кастомного софта

</td>
<td align="center" width="33%">

### 📢 Channel
**[@coxerhub](https://t.me/coxerhub)**<br>
новости и релизы

</td>
</tr>
</table>

</div>

---

## ✨ Возможности

- ⚡ **Чистый async** — один цикл `asyncio`, ничего не блокирует
- 👥 **Multi-account** — кладёшь сколько угодно `.session` в `sessions/`, скрипт сам ротирует
- 🧊 **Smart freeze с TTL** — `PeerFlood` не убивает сессию навсегда. Заморозка на 6 часов, скрипт сам просыпается ровно к моменту разморозки
- 🌐 **Rotating residential proxy** — каждый аккаунт получает свой `session-ID` → свой IP
- 🚨 **Полная обработка ошибок Pyrogram** — `303 / 400 / 401 / 403 / 406 / 420 / 500`, классификатор-словарь, никаких голых `except Exception: pass`
- 👁️ **Detect silent privacy fails** — Telegram возвращает успех `add_chat_members` даже если юзер на самом деле не добавился (приватность). Скрипт верифицирует через `get_chat_member`
- 💾 **Persistent state** — `invited.txt` / `failed.txt` / `dead_sessions.txt` / `frozen_sessions.txt` (с unix-таймстампами) переживают рестарт
- 🧹 **Auto-cleanup `users.txt`** — атомарно сжимается по мере обработки (`tmp + os.replace`)
- 🌈 **Цветной логгер** — `DBG / INF / OK / WRN / ERR / CRT` со scope, timestamp и копией в `data/logs/YYYY-MM-DD.log`
- ♻️ **24/7 mode** — top-level `try/except` ловит любой краш, рестартует через `error_retry_delay`
- 🔐 **Auth helper** — `python auth.py` создаёт новые `.session` интерактивно (номер → код → 2FA → готово)
- 🎭 **Custom client fingerprint** — `device_model` / `system_version` / `app_version` пробрасываются в `Client(...)` ровно как в Telethon

---

## 📦 Установка

```bash
git clone https://github.com/YOUR_USERNAME/inviter-tg.git
cd inviter-tg
pip install -r requirements.txt
```

**Требования:** Python 3.11+, Windows / Linux / macOS.

---

## ⚙️ Конфигурация

Главные настройки в [`config.py`](config.py):

```python
api_id   = 2040
api_hash = "b18441a1ff607e10a989891a5462e627"

target_chat = "@your_target_chat"        # куда инвайтить

invite_delay = (5, 15)                   # кулдаун между инвайтами (сек)
max_invites_per_session = 40             # сколько за один прогон на одну сессию

peer_flood_freeze_seconds = 6 * 3600     # PeerFlood → заморозка 6 часов
long_flood_freeze_seconds = 2 * 3600     # большой FloodWait → 2 часа

device_model   = "aboba-linux-custom"
system_version = "1.2.3-zxc-custom"
app_version    = "1.0.1"

proxy_url = "http://user-session-XXXX-ttl-5:pass@host:port"
proxy_rotate_session = True              # каждой сессии — свой exit-IP
```

---

## 🚀 Запуск

```bash
# 1. Создать сессии (если их ещё нет)
python auth.py

# 2. Положить юзернеймы в users.txt (по одному на строку, @ опционален)

# 3. Запустить инвайтер
python main.py
```

Скрипт сам обнаружит все `.session` файлы и начнёт работу. Останавливается через `Ctrl+C`.

---

## 📁 Структура

```
inviter-tg/
├── main.py                       Точка входа + баннер
├── auth.py                       Интерактивный создатель сессий
├── config.py                     Все настройки
├── requirements.txt
├── users.txt                     Список юзернеймов (auto-shrinks)
├── sessions/                     Pyrogram .session файлы
├── data/
│   ├── invited.txt               ✅ кого пригласили
│   ├── failed.txt                ❌ кого нельзя (для is_processed)
│   ├── failed_log.txt            📜 причины фейлов с таймстампом
│   ├── dead_sessions.txt         💀 мёртвые ключи (навсегда)
│   ├── frozen_sessions.txt       🧊 заморожены с unix-expiry
│   └── logs/                     📅 посуточные log-файлы
└── src/
    ├── logger.py                 цветной + файловый логгер
    ├── storage.py                TextSet / TimedSet / AppendLog
    ├── errors.py                 Verdict-классификатор ошибок Pyrogram
    ├── proxy.py                  парсинг прокси-URL + ротация session-ID
    ├── user_loader.py            нормализация username, очередь
    ├── account.py                воркер одного аккаунта
    ├── session_manager.py        обнаружение валидных .session, ETA разморозки
    └── inviter.py                оркестратор run_forever()
```

---

## 🚦 Карта обработки ошибок

| Pyrogram error | Действие |
|---|---|
| `FloodWait` / `SlowmodeWait` | sleep на указанное время → юзер обратно в очередь |
| `FloodWait` > `flood_wait_threshold` (10 мин) | сессия → `frozen_sessions.txt` на 2h |
| `PeerFlood`, `UserRestricted`, любой `NotAcceptable`/`Flood` | сессия → `frozen_sessions.txt` на 6h, переключаемся |
| `AuthKey*`, `SessionExpired`, `SessionRevoked`, `UserDeactivated*`, `Unauthorized` | сессия → `dead_sessions.txt` (навсегда) |
| `UserPrivacyRestricted`, `NotMutualContact`, `UserChannelsTooMuch`, `UserKicked`, `UserBlocked`, `UserBot`, `InputUserDeactivated`, `Peer/UserIdInvalid`, `UsernameInvalid/NotOccupied`, `BotsTooMuch`, `UserAlreadyParticipant` | юзер → `failed.txt`, удаляется из `users.txt` |
| `ChannelPrivate`, `ChatAdminRequired`, `ChatWriteForbidden`, `ChatRestricted`, `ChatAdminInviteRequired`, любой `Forbidden` | критично для таргета → воркер выходит |
| `InternalServerError`, `ConnectionError`, `TimeoutError`, `OSError` | retry через 15 сек |
| `SeeOther` (PHONE_MIGRATE, etc.) | retry через 5 сек |
| **Silent fail** (`add_chat_members` вернул True, но юзер не добавлен) | verify через `get_chat_member`, → `failed.txt` |
| Любая прочая `RPCError` / неизвестное | sleep 10 сек + requeue, не падаем |

---

## 🔄 24/7 автоматизация

Когда все сессии заморожены:

```
[WRN] inviter | zero invites this pass — all sessions frozen.
               next unfreeze at 23:45:12 (sleeping 5h 42m 21s)
```

Скрипт **точно** просыпается к моменту оттаивания ближайшей сессии и продолжает работу. Никакого ручного вмешательства.

---

## 💎 Спонсор

<div align="center">

[![neversmm.com](https://img.shields.io/badge/neversmm.com-SMM%20panel-FF3366?style=for-the-badge&logoColor=white)](https://neversmm.com)

### **самая дешёвая SMM-биржа в СНГ**

</div>

> 🚀 **Подписчики · лайки · просмотры · репосты · комментарии**
>
> 📱 **Все соц-сети:** Telegram, Instagram, TikTok, YouTube, ВКонтакте, Twitter/X, Discord, Twitch
>
> 💰 **Прайс от 0.01 ₽** за единицу — дешевле, чем у конкурентов
>
> ♻️ **Автодоливы** при отписке, гарантия качества
>
> 🔧 **API для разработчиков** — встраивай в свои проекты
>
> ⚡ **Старт заказа от 1 минуты**

### 🔗 https://neversmm.com

---

## 📞 Контакты

<table>
<tr>
<td>💬 <b>Автор · заказ кастомного софта</b></td>
<td><a href="https://t.me/exfador"><code>@exfador</code></a></td>
</tr>
<tr>
<td>📢 <b>Основной канал · новости</b></td>
<td><a href="https://t.me/coxerhub"><code>@coxerhub</code></a></td>
</tr>
<tr>
<td>💎 <b>Спонсор</b></td>
<td><a href="https://neversmm.com">neversmm.com</a></td>
</tr>
</table>

**Хочешь заказать кастомный софт** (инвайтер, парсер, рассыльщик, бот, чекер, авторег, кликер, что угодно на Pyrogram / Telethon / aiogram / requests / playwright) — **пиши в личку [@exfador](https://t.me/exfador)**.

---

## ⚖️ Disclaimer

Софт предоставлен **as is** в образовательных целях. Использование инвайтера может нарушать [Terms of Service Telegram](https://telegram.org/tos) и привести к ограничениям/блокировкам аккаунтов. Ответственность за использование несёт пользователь. Автор не отвечает за заблокированные сессии, потерянные базы и испорченное настроение.

---

<div align="center">

Сделано с ☕ by [**@exfador**](https://t.me/exfador) · Спонсор [**neversmm.com**](https://neversmm.com)

⭐ **Ставь звезду на гитхабе, если зашло**

</div>
