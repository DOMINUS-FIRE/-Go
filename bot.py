import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@dominus_live")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/dominus_live")

if not BOT_TOKEN:
    raise RuntimeError(
        "Не найден BOT_TOKEN. Добавьте переменную BOT_TOKEN в Environment Variables Render."
    )


# Здесь меняешь ссылки на свои реальные партнёрские ссылки МФО.
# Кнопок у микрозаймов нет — они выводятся обычными ссылками в сообщении.
OFFERS = [
    {
        "title": "Быстрый онлайн-займ",
        "description": "Анкета онлайн, решение после проверки данных.",
        "url": "https://example.com/offer-1?utm_source=telegram_bot",
    },
    {
        "title": "Займ на карту",
        "description": (
            "Подходит, если деньги нужны срочно. "
            "Условия смотри на сайте МФО."
        ),
        "url": "https://example.com/offer-2?utm_source=telegram_bot",
    },
    {
        "title": "Подбор займа",
        "description": (
            "Можно сравнить несколько вариантов и выбрать подходящий."
        ),
        "url": "https://example.com/offer-3?utm_source=telegram_bot",
    },
]


bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Простой HTTP-сервер для проверки доступности Web Service на Render."""

    def send_status(self, include_body: bool = True) -> None:
        body = "ZaimGo bot is running\n".encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()

        if include_body:
            self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in {"/", "/health", "/healthz"}:
            self.send_status()
            return

        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Not found\n".encode("utf-8"))

    def do_HEAD(self) -> None:
        self.send_status(include_body=False)

    def log_message(self, format: str, *args) -> None:
        # Не засоряем логи Render запросами проверки состояния.
        return


def start_health_server() -> ThreadingHTTPServer:
    """Открывает порт, который Render передаёт через переменную PORT."""
    port_raw = os.getenv("PORT", "10000")

    try:
        port = int(port_raw)
    except ValueError as error:
        raise RuntimeError(
            f"Переменная PORT должна быть числом, получено: {port_raw!r}"
        ) from error

    server = ThreadingHTTPServer(("0.0.0.0", port), HealthCheckHandler)

    thread = threading.Thread(
        target=server.serve_forever,
        name="render-health-server",
        daemon=True,
    )
    thread.start()

    print(f"HTTP-сервер запущен на 0.0.0.0:{port}")
    return server


def subscription_keyboard() -> InlineKeyboardMarkup:
    """Кнопки для подписки на канал и проверки подписки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Подписаться на канал",
                    url=CHANNEL_URL,
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Я подписался",
                    callback_data="check_subscription",
                )
            ],
        ]
    )


def offers_text() -> str:
    """Микрозаймы выводятся обычными ссылками в тексте."""
    lines = [
        "💸 <b>Актуальные варианты микрозаймов</b>",
        "",
        (
            "Перед оформлением обязательно проверь условия: сумму, срок, "
            "ставку, полную стоимость займа, комиссии и штрафы."
        ),
        "",
    ]

    for index, offer in enumerate(OFFERS, start=1):
        lines.extend(
            [
                f"<b>{index}. {offer['title']}</b>",
                offer["description"],
                f"🔗 {offer['url']}",
                "",
            ]
        )

    lines.extend(
        [
            "⚠️ Информация не является финансовой рекомендацией.",
            "🔞 Только для совершеннолетних пользователей.",
        ]
    )

    return "\n".join(lines)


async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in {"member", "administrator", "creator"}
    except Exception as error:
        print(f"Ошибка проверки подписки пользователя {user_id}: {error}")
        return False


@dp.message(CommandStart())
async def start(message: Message) -> None:
    text = (
        "👋 Привет!\n\n"
        "Чтобы получить список актуальных вариантов микрозаймов, "
        "сначала подпишись на наш канал:\n"
        f"{CHANNEL_URL}\n\n"
        "После подписки нажми кнопку <b>«Я подписался»</b>."
    )
    await message.answer(text, reply_markup=subscription_keyboard())


@dp.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery) -> None:
    if await is_subscribed(callback.from_user.id):
        if callback.message:
            await callback.message.answer(
                offers_text(),
                disable_web_page_preview=True,
            )
        await callback.answer("Подписка подтверждена")
        return

    if callback.message:
        await callback.message.answer(
            "❌ Я пока не вижу подписку.\n\n"
            "Подпишись на канал и нажми "
            "<b>«Я подписался»</b> ещё раз.",
            reply_markup=subscription_keyboard(),
        )

    await callback.answer(
        "Подписка не найдена",
        show_alert=True,
    )


async def main() -> None:
    health_server = start_health_server()

    try:
        print("Telegram-бот запущен")
        await dp.start_polling(bot)
    finally:
        health_server.shutdown()
        health_server.server_close()


if __name__ == "__main__":
    asyncio.run(main())
