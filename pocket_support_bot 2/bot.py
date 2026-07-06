import re
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.types import ReplyKeyboardRemove

import texts
from config import BOT_TOKEN, SUPPORT_USERNAME, REG_LINK_RU, REG_LINK_OTHER
from db import get_trader, link_telegram_chat

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

SUPPORT_LINK = f"https://t.me/{SUPPORT_USERNAME}"

VERIFICATION_IMAGES = [
    "assets/verification_1.jpg",
    "assets/verification_2.jpg",
    "assets/verification_3.jpg",
]


class Flow(StatesGroup):
    waiting_experience = State()
    waiting_geo = State()
    waiting_uid = State()


def persistent_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BTN_FAQ), KeyboardButton(text=texts.BTN_RISKS)],
            [KeyboardButton(text=texts.BTN_SUPPORT)],
        ],
        resize_keyboard=True,
    )


def experience_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BTN_EXPERIENCE_YES)],
            [KeyboardButton(text=texts.BTN_EXPERIENCE_NO)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def geo_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BTN_GEO_RU)],
            [KeyboardButton(text=texts.BTN_GEO_OTHER)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(texts.WELCOME, reply_markup=experience_keyboard())
    await state.set_state(Flow.waiting_experience)


@dp.message(Flow.waiting_experience)
async def handle_experience(message: Message, state: FSMContext):
    if message.text == texts.BTN_EXPERIENCE_YES:
        reply = texts.AFTER_EXPERIENCE_YES
    else:
        # Любой другой ответ (в т.ч. свободный текст про опыт) считаем как "нет опыта"
        reply = texts.AFTER_EXPERIENCE_NO

    await message.answer(reply, reply_markup=ReplyKeyboardRemove())
    await message.answer(texts.ASK_GEO, reply_markup=geo_keyboard())
    await state.set_state(Flow.waiting_geo)


@dp.message(Flow.waiting_geo)
async def handle_geo(message: Message, state: FSMContext):
    if message.text == texts.BTN_GEO_RU:
        link = REG_LINK_RU
        alt_link = REG_LINK_OTHER
    else:
        link = REG_LINK_OTHER
        alt_link = REG_LINK_RU

    await message.answer(
        texts.REGISTRATION_INSTRUCTIONS.format(link=link),
        reply_markup=persistent_menu(),
    )
    await state.set_state(Flow.waiting_uid)
    await state.update_data(uid_attempts=0, alt_link=alt_link)


@dp.message(Flow.waiting_uid, F.text.regexp(r"^\d+$"))
async def handle_uid(message: Message, state: FSMContext):
    uid = message.text.strip()
    trader = await get_trader(uid)

    if trader:
        await link_telegram_chat(uid, message.chat.id)
        await message.answer(texts.UID_FOUND_VERIFICATION)
        for path in VERIFICATION_IMAGES:
            await message.answer_photo(FSInputFile(path))
        await message.answer(texts.AFTER_VERIFICATION_DONE)
        await message.answer(
            texts.AFTER_VERIFICATION_HANDOFF.format(support_link=SUPPORT_LINK)
        )
        await state.clear()
    else:
        data = await state.get_data()
        attempts = data.get("uid_attempts", 0) + 1
        alt_link = data.get("alt_link", REG_LINK_OTHER)
        await state.update_data(uid_attempts=attempts)

        await message.answer(
            texts.UID_NOT_FOUND.format(alt_link=alt_link, support_link=SUPPORT_LINK)
        )

        if attempts >= 2:
            await message.answer(
                texts.ESCALATION_GENERIC.format(support_link=SUPPORT_LINK)
            )


@dp.message(Flow.waiting_uid)
async def handle_uid_wrong_format(message: Message):
    await message.answer(texts.INVALID_UID_FORMAT)


@dp.message(Command("faq"))
@dp.message(F.text == texts.BTN_FAQ)
async def handle_faq(message: Message):
    await message.answer(texts.FAQ_REDIRECT.format(support_link=SUPPORT_LINK))


@dp.message(Command("risks"))
@dp.message(F.text == texts.BTN_RISKS)
async def handle_risks(message: Message):
    await message.answer(texts.RISK_INFO)


@dp.message(Command("support"))
@dp.message(F.text == texts.BTN_SUPPORT)
async def handle_support(message: Message):
    await message.answer(texts.ESCALATION_GENERIC.format(support_link=SUPPORT_LINK))


# Всё, что не попало ни в одно из состояний/команд выше — по умолчанию
# уходит на эскалацию, а не игнорируется и не обрабатывается "как получится".
@dp.message()
async def fallback(message: Message):
    await message.answer(texts.ESCALATION_GENERIC.format(support_link=SUPPORT_LINK))


async def start_bot_polling():
    await dp.start_polling(bot)
