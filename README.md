# SoundCloud Telegram Mini App

Telegram Mini App для прослушивания SoundCloud без VPN в России.

Принцип: бэкенд на сервере вне РФ проксирует аудиопотоки с SoundCloud CDN. Пользователь один раз авторизуется через SoundCloud (с VPN), после чего слушает музыку через Mini App без VPN.

## Структура

```
soundcloud-tg-app/
├── app.py              # Flask бэкенд (API + проксирование аудио)
├── bot.py              # Telegram бот (кнопка Mini App)
├── static/
│   └── index.html      # Фронтенд (Telegram Mini App)
├── requirements.txt
├── Procfile
├── .env.example
└── README.md
```

## Настройка

### 1. SoundCloud App

1. Зайди на https://soundcloud.com/you/apps (нужен VPN)
2. Создай новое приложение
3. Запиши `Client ID` и `Client Secret`
4. В Redirect URI укажи: `https://your-app.railway.app/callback`

### 2. Telegram Bot

1. Открой [@BotFather](https://t.me/BotFather)
2. `/newbot` — создай бота
3. Запиши токен бота
4. `/setmenubutton` — (опционально) настрой кнопку меню

### 3. Деплой на Railway

1. Создай аккаунт на [railway.app](https://railway.app)
2. Создай новый проект → Deploy from GitHub repo
3. Добавь переменные окружения:

| Переменная | Значение |
|---|---|
| `SC_CLIENT_ID` | Client ID из SoundCloud |
| `SC_CLIENT_SECRET` | Client Secret из SoundCloud |
| `REDIRECT_URI` | `https://<your-railway-domain>/callback` |
| `BOT_TOKEN` | Токен Telegram бота |
| `WEBAPP_URL` | `https://<your-railway-domain>` |

4. Railway автоматически подхватит Procfile и запустит web + worker

### 4. Настройка Mini App в BotFather

1. Открой BotFather
2. `/mybots` → выбери бота → Bot Settings → Menu Button
3. Укажи URL: `https://<your-railway-domain>`

## Как работает

1. Пользователь нажимает `/start` в боте
2. Бот показывает кнопку «Открыть SoundCloud»
3. Открывается Mini App
4. Если не авторизован — кнопка «Войти через SoundCloud» (нужен VPN в первый раз)
5. После авторизации — лайки, плейлисты, поиск и плеер работают без VPN
6. Аудио проксируется через бэкенд: пользователь → Railway → SoundCloud CDN

## Локальная разработка

```bash
pip install -r requirements.txt

# Создай .env файл из .env.example и заполни переменные
cp .env.example .env

# Запуск Flask
python app.py

# Запуск бота (в отдельном терминале)
python bot.py
```

Для тестирования фронтенда без Telegram можно открыть:
```
http://localhost:5000/?tg_id=123456789
```
