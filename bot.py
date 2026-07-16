import os
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
import asyncio

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@dominus_live")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/dominus_live")

if not BOT_TOKEN:
    raise RuntimeError("Не найден BOT_TOKEN. Проверьте файл .env рядом с bot.py")

# Здесь меняешь ссылки на свои реальные партнёрские ссылки МФО.
# Кнопок у микрозаймов НЕ будет — они выводятся обычными ссылками в сообщении.
OFFERS = [
    {
        "title": "Быстрый онлайн-займ",
        "description": "Анкета онлайн, решение после проверки данных.",
        "url": "https://example.com/offer-1?utm_source=telegram_bot",
    },
    {
        "title": "Займ на карту",
        "description": "Подходит, если деньги нужны срочно. Условия смотри на сайте МФО.",
        "url": "https://example.com/offer-2?utm_source=telegram_bot",
    },
    {
        "title": "Подбор займа",
        "description": "Можно сравнить несколько вариантов и выбрать подходящий.",
        "url": "https://example.com/offer-3?utm_source=telegram_bot",
    },
]

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


def subscription_keyboard() -> InlineKeyboardMarkup:
    """Кнопки оставляем только для подписки на канал и проверки подписки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")],
        ]
    )


def offers_text() -> str:
    """Микрозаймы выводятся обычными ссылками в тексте, без inline-кнопок."""
    lines = [
        "💸 <b>Актуальные варианты микрозаймов</b>",
        "",
        "Перед оформлением обязательно проверь условия: сумму, срок, ставку, полную стоимость займа, комиссии и штрафы.",
        "",
    ]

    for i, offer in enumerate(OFFERS, start=1):
        lines.extend([
            f"<b>{i}. {offer['title']}</b>",
            offer["description"],
            f"🔗 {offer['url']}",
            "",
        ])

    lines.extend([
        "⚠️ Информация не является финансовой рекомендацией.",
        "🔞 Только для совершеннолетних пользователей.",
    ])

    return "\n".join(lines)


async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in {"member", "administrator", "creator"}
    except Exception:
        return False


@dp.message(CommandStart())
async def start(message: Message):
    text = (
        "👋 Привет!\n\n"
        "Чтобы получить список актуальных вариантов микрозаймов, сначала подпишись на наш канал:\n"
        f"{CHANNEL_URL}\n\n"
        "После подписки нажми кнопку <b>«Я подписался»</b>."
    )
    await message.answer(text, reply_markup=subscription_keyboard())


@dp.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        await callback.message.answer(offers_text(), disable_web_page_preview=True)
        await callback.answer("Подписка подтверждена")
    else:
        await callback.message.answer(
            "❌ Я пока не вижу подписку.\n\n"
            "Подпишись на канал и нажми <b>«Я подписался»</b> ещё раз.",
            reply_markup=subscription_keyboard(),
        )
        await callback.answer("Подписка не найдена", show_alert=True)


async def main():
    print("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
