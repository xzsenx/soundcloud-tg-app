import os
import sqlite3
import requests
from flask import Flask, request, jsonify, redirect, send_from_directory, Response
from flask_cors import CORS
from urllib.parse import urlencode

app = Flask(__name__, static_folder="static")
CORS(app)

# --- Конфигурация ---
SC_CLIENT_ID = os.environ.get("SC_CLIENT_ID")
SC_CLIENT_SECRET = os.environ.get("SC_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI")  # https://your-app.railway.app/callback
SC_API_BASE = "https://api.soundcloud.com"

# --- БД ---
DB_PATH = "users.db"


def get_db():
    """Подключение к SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создаём таблицу пользователей при старте."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id TEXT PRIMARY KEY,
            access_token TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


def get_token(telegram_id):
    """Получить access_token пользователя по telegram_id."""
    conn = get_db()
    row = conn.execute(
        "SELECT access_token FROM users WHERE telegram_id = ?", (telegram_id,)
    ).fetchone()
    conn.close()
    if row:
        return row["access_token"]
    return None


def save_token(telegram_id, access_token):
    """Сохранить или обновить токен пользователя."""
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO users (telegram_id, access_token) VALUES (?, ?)",
        (telegram_id, access_token),
    )
    conn.commit()
    conn.close()


def simplify_track(track):
    """Упрощаем данные трека для фронтенда."""
    return {
        "id": track.get("id"),
        "title": track.get("title", "Без названия"),
        "artist": track.get("user", {}).get("username", "Неизвестный"),
        "duration": track.get("duration", 0),
        "artwork": track.get("artwork_url") or "",
    }


# --- Маршруты ---


@app.route("/")
def index():
    """Отдаём фронтенд."""
    return send_from_directory("static", "index.html")


# --- OAuth 2.0 ---


@app.route("/auth")
def auth():
    """
    Начало OAuth. Фронтенд вызывает /auth?telegram_id=123
    Редирект на SoundCloud для авторизации.
    """
    telegram_id = request.args.get("telegram_id")
    if not telegram_id:
        return jsonify({"error": "telegram_id обязателен"}), 400

    params = {
        "client_id": SC_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "state": telegram_id,  # передаём telegram_id через state
    }
    sc_auth_url = f"https://soundcloud.com/connect?{urlencode(params)}"
    return redirect(sc_auth_url)


@app.route("/callback")
def callback():
    """
    Callback от SoundCloud после авторизации.
    Получаем code, меняем на access_token, сохраняем в БД.
    """
    code = request.args.get("code")
    telegram_id = request.args.get("state")

    if not code or not telegram_id:
        return "Ошибка авторизации: нет code или state", 400

    # Обмен code на access_token
    resp = requests.post(
        f"{SC_API_BASE}/oauth2/token",
        data={
            "client_id": SC_CLIENT_ID,
            "client_secret": SC_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code": code,
        },
    )

    if resp.status_code != 200:
        return f"Ошибка получения токена: {resp.text}", 400

    access_token = resp.json().get("access_token")
    save_token(telegram_id, access_token)

    # После успешной авторизации показываем страницу-заглушку
    return """
    <html>
    <body style="display:flex;align-items:center;justify-content:center;height:100vh;
                  font-family:sans-serif;background:#1a1a2e;color:#fff;">
        <div style="text-align:center;">
            <h2>✅ Авторизация успешна!</h2>
            <p>Вернитесь в Telegram и откройте Mini App заново.</p>
        </div>
    </body>
    </html>
    """


# --- API ---


@app.route("/api/check")
def api_check():
    """Проверка, авторизован ли пользователь."""
    telegram_id = request.args.get("telegram_id")
    if not telegram_id:
        return jsonify({"error": "telegram_id обязателен"}), 400

    token = get_token(telegram_id)
    return jsonify({"authorized": token is not None})


@app.route("/api/likes")
def api_likes():
    """Получить лайкнутые треки пользователя."""
    telegram_id = request.args.get("telegram_id")
    token = get_token(telegram_id) if telegram_id else None

    if not token:
        return jsonify({"error": "Не авторизован"}), 401

    resp = requests.get(
        f"{SC_API_BASE}/me/likes/tracks",
        params={"oauth_token": token, "limit": 50},
    )

    if resp.status_code != 200:
        return jsonify({"error": "Ошибка SoundCloud API", "details": resp.text}), resp.status_code

    tracks = resp.json()
    # SoundCloud может вернуть список объектов или collection
    if isinstance(tracks, dict) and "collection" in tracks:
        tracks = tracks["collection"]

    return jsonify([simplify_track(t) for t in tracks if isinstance(t, dict)])


@app.route("/api/playlists")
def api_playlists():
    """Получить плейлисты пользователя."""
    telegram_id = request.args.get("telegram_id")
    token = get_token(telegram_id) if telegram_id else None

    if not token:
        return jsonify({"error": "Не авторизован"}), 401

    resp = requests.get(
        f"{SC_API_BASE}/me/playlists",
        params={"oauth_token": token, "limit": 50},
    )

    if resp.status_code != 200:
        return jsonify({"error": "Ошибка SoundCloud API"}), resp.status_code

    playlists = resp.json()
    if isinstance(playlists, dict) and "collection" in playlists:
        playlists = playlists["collection"]

    result = []
    for pl in playlists:
        if not isinstance(pl, dict):
            continue
        result.append({
            "id": pl.get("id"),
            "title": pl.get("title", "Без названия"),
            "track_count": pl.get("track_count", 0),
            "artwork": pl.get("artwork_url") or "",
            "tracks": [simplify_track(t) for t in pl.get("tracks", []) if isinstance(t, dict)],
        })

    return jsonify(result)


@app.route("/api/search")
def api_search():
    """Поиск треков на SoundCloud."""
    telegram_id = request.args.get("telegram_id")
    query = request.args.get("q", "").strip()
    token = get_token(telegram_id) if telegram_id else None

    if not token:
        return jsonify({"error": "Не авторизован"}), 401
    if not query:
        return jsonify([])

    resp = requests.get(
        f"{SC_API_BASE}/tracks",
        params={"oauth_token": token, "q": query, "limit": 30},
    )

    if resp.status_code != 200:
        return jsonify({"error": "Ошибка поиска"}), resp.status_code

    tracks = resp.json()
    if isinstance(tracks, dict) and "collection" in tracks:
        tracks = tracks["collection"]

    return jsonify([simplify_track(t) for t in tracks if isinstance(t, dict)])


@app.route("/stream/<int:track_id>")
def stream(track_id):
    """
    Проксирование аудио потока с SoundCloud CDN.
    Это ключевая фича — без VPN юзер получает аудио через наш сервер.
    """
    telegram_id = request.args.get("telegram_id")
    token = get_token(telegram_id) if telegram_id else None

    if not token:
        return jsonify({"error": "Не авторизован"}), 401

    # Получаем URL стрима
    stream_resp = requests.get(
        f"{SC_API_BASE}/tracks/{track_id}/stream",
        params={"oauth_token": token},
        allow_redirects=False,
    )

    # SoundCloud отдаёт 302 с реальным URL CDN
    if stream_resp.status_code == 302:
        stream_url = stream_resp.headers.get("Location")
    elif stream_resp.status_code == 200 and stream_resp.headers.get("Content-Type", "").startswith("audio"):
        # Иногда отдаёт сразу аудио
        stream_url = None
        audio_resp = stream_resp
    else:
        return jsonify({"error": "Не удалось получить стрим"}), 404

    # Скачиваем аудио с CDN и проксируем клиенту (chunked)
    if stream_url:
        audio_resp = requests.get(stream_url, stream=True)

    def generate():
        for chunk in audio_resp.iter_content(chunk_size=8192):
            if chunk:
                yield chunk

    content_type = audio_resp.headers.get("Content-Type", "audio/mpeg")
    headers = {"Content-Type": content_type}

    content_length = audio_resp.headers.get("Content-Length")
    if content_length:
        headers["Content-Length"] = content_length

    return Response(generate(), headers=headers)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
