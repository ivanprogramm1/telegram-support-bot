import asyncio
import re
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.types import ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest

import texts
from config import (
    BOT_TOKEN,
    SUPPORT_USERNAME,
    REG_LINK_RU,
    REG_LINK_OTHER,
    OWNER_TELEGRAM_ID,
    CHANNEL_IDS,
    INACTIVITY_DAYS,
    VERIFICATION_IMAGES,
    WORKFLOW_IMAGES,
    VOICE_WARNINGS,
)
from db import get_trader, link_telegram_chat, get_all_chat_ids, get_inactive_traders

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

SUPPORT_LINK = f"https://t.me/{SUPPORT_USERNAME}"


class Flow(StatesGroup):
    waiting_experience = State()
    waiting_geo = State()
    waiting_uid = State()
    waiting_age_confirm = State()
    waiting_verification_confirm = State()
    waiting_deposit_confirm = State()
    waiting_strategy_confirm = State()
    waiting_workflow_confirm = State()
    waiting_rules_confirm = State()
    waiting_channel_choice = State()


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


def age_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BTN_AGE_YES)],
            [KeyboardButton(text=texts.BTN_AGE_NO)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def verification_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BTN_VERIFIED_DONE)],
            [KeyboardButton(text=texts.BTN_SUPPORT)],
        ],
        resize_keyboard=True,
    )


def deposit_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts.BTN_DEPOSIT_DONE)]],
        resize_keyboard=True,
    )


def continue_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Дальше →")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def channel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BTN_FAMILY)],
            [KeyboardButton(text=texts.BTN_CHANNEL_OTC)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(texts.WELCOME, reply_markup=experience_keyboard())
    await state.set_state(Flow.waiting_experience)


# Кнопки меню (FAQ / Риски / Поддержка) должны работать ВСЕГДА, на любом шаге —
# поэтому регистрируем их раньше остальных обработчиков, привязанных к состояниям.
# aiogram проверяет хендлеры в порядке регистрации и останавливается на первом
# совпадении, так что порядок здесь важен.
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


def _is_owner(message: Message) -> bool:
    return bool(OWNER_TELEGRAM_ID) and str(message.from_user.id) == str(
        OWNER_TELEGRAM_ID
    )


@dp.message(Command("broadcast"))
async def handle_broadcast(message: Message):
    # Доступно только вам. Рассылает текст всем, кто хоть раз писал боту.
    if not _is_owner(message):
        return

    text_to_send = message.text.removeprefix("/broadcast").strip()
    if not text_to_send:
        await message.answer("Использование: /broadcast текст сообщения")
        return

    chat_ids = await get_all_chat_ids()
    sent, failed = 0, 0
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id, text_to_send)
            sent += 1
        except TelegramBadRequest:
            failed += 1
        await asyncio.sleep(0.05)  # чтобы не упереться в лимиты Telegram

    await message.answer(f"Рассылка завершена. Отправлено: {sent}, не удалось: {failed}")


@dp.message(Command("check_inactive"))
async def handle_check_inactive_manual(message: Message):
    # Доступно только вам. Ручной запуск проверки неактивных (не дожидаясь
    # автоматического фонового прогона).
    if not _is_owner(message):
        return
    await run_inactivity_check(notify_owner=True)


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
        await message.answer(
            texts.UID_FOUND_VERIFICATION, reply_markup=age_keyboard()
        )
        await state.update_data(uid=uid)
        await state.set_state(Flow.waiting_age_confirm)
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


@dp.message(Flow.waiting_age_confirm, F.text == texts.BTN_AGE_NO)
async def handle_underage(message: Message, state: FSMContext):
    await message.answer(
        texts.UNDERAGE_ESCALATION.format(support_link=SUPPORT_LINK),
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.clear()


@dp.message(Flow.waiting_age_confirm, F.text == texts.BTN_AGE_YES)
async def handle_adult_confirmed(message: Message, state: FSMContext):
    await message.answer(texts.VERIFICATION_IMPORTANCE)
    for path in VERIFICATION_IMAGES:
        await message.answer_photo(FSInputFile(path))
    await message.answer(
        texts.VERIFICATION_PENDING_PROMPT,
        reply_markup=verification_keyboard(),
    )
    await state.set_state(Flow.waiting_verification_confirm)


@dp.message(Flow.waiting_age_confirm)
async def handle_age_other_text(message: Message):
    await message.answer(texts.UID_FOUND_VERIFICATION, reply_markup=age_keyboard())


@dp.message(Flow.waiting_verification_confirm, F.text == texts.BTN_VERIFIED_DONE)
async def handle_verification_done(message: Message, state: FSMContext):
    await message.answer(
        texts.VERIFICATION_HANDOFF, reply_markup=deposit_keyboard()
    )
    await state.set_state(Flow.waiting_deposit_confirm)


@dp.message(Flow.waiting_verification_confirm)
async def handle_verification_other_text(message: Message):
    await message.answer(
        texts.VERIFICATION_PENDING_PROMPT, reply_markup=verification_keyboard()
    )


@dp.message(Flow.waiting_deposit_confirm, F.text == texts.BTN_DEPOSIT_DONE)
async def handle_deposit_check(message: Message, state: FSMContext):
    data = await state.get_data()
    uid = data.get("uid")
    trader = await get_trader(uid) if uid else None

    # Проверяем, пришёл ли FTD (депозит) через постбек
    if trader and trader.get("ftd_amount") and float(trader.get("ftd_amount") or 0) > 0:
        await message.answer(
            texts.STRATEGY_INFO, reply_markup=continue_keyboard()
        )
        await state.set_state(Flow.waiting_strategy_confirm)
    else:
        await message.answer(texts.DEPOSIT_NOT_YET, reply_markup=deposit_keyboard())


@dp.message(Flow.waiting_deposit_confirm)
async def handle_deposit_other_text(message: Message):
    await message.answer(texts.VERIFICATION_HANDOFF, reply_markup=deposit_keyboard())


@dp.message(Flow.waiting_strategy_confirm, F.text == "Дальше →")
async def handle_strategy_continue(message: Message, state: FSMContext):
    await message.answer(texts.WORKFLOW_INFO)
    for path in WORKFLOW_IMAGES:
        await message.answer_photo(FSInputFile(path))
    await message.answer("Дальше →", reply_markup=continue_keyboard())
    await state.set_state(Flow.waiting_workflow_confirm)


@dp.message(Flow.waiting_strategy_confirm)
async def handle_strategy_other_text(message: Message):
    await message.answer(texts.STRATEGY_INFO, reply_markup=continue_keyboard())


@dp.message(Flow.waiting_workflow_confirm, F.text == "Дальше →")
async def handle_workflow_continue(message: Message, state: FSMContext):
    await message.answer(texts.RULES_WARNING)
    for path in VOICE_WARNINGS:
        await message.answer_voice(FSInputFile(path))
    await message.answer("Дальше →", reply_markup=continue_keyboard())
    await state.set_state(Flow.waiting_rules_confirm)


@dp.message(Flow.waiting_workflow_confirm)
async def handle_workflow_other_text(message: Message):
    await message.answer("Дальше →", reply_markup=continue_keyboard())


@dp.message(Flow.waiting_rules_confirm, F.text == "Дальше →")
async def handle_rules_continue(message: Message, state: FSMContext):
    await message.answer("Выбери канал:", reply_markup=channel_keyboard())
    await state.set_state(Flow.waiting_channel_choice)


@dp.message(Flow.waiting_rules_confirm)
async def handle_rules_other_text(message: Message):
    await message.answer(texts.RULES_WARNING)
    await message.answer("Дальше →", reply_markup=continue_keyboard())


@dp.message(Flow.waiting_channel_choice)
async def handle_channel_choice(message: Message, state: FSMContext):
    data = await state.get_data()
    uid = data.get("uid")
    trader = await get_trader(uid) if uid else None
    
    balance = float(trader.get("balance") or trader.get("ftd_amount") or 0) if trader else 0

    if message.text == texts.BTN_FAMILY:
        await message.answer(
            f"{texts.CHANNEL_FAMILY}:\n{texts.CHANNEL_FAMILY_LINK}\n\n"
            f"Робот:\n{texts.ROBOT_LINK}",
            reply_markup=ReplyKeyboardRemove(),
        )
        await message.answer(
            f"Всё готово! Дальше обсудим лично, напиши мне:\n{SUPPORT_LINK}"
        )
        await state.clear()

    elif message.text == texts.BTN_CHANNEL_OTC:
        if balance >= 200:
            await message.answer(
                f"{texts.CHANNEL_OTC}:\n{texts.CHANNEL_OTC_LINK}",
                reply_markup=ReplyKeyboardRemove(),
            )
            await message.answer(
                f"Всё готово! Дальше обсудим лично, напиши мне:\n{SUPPORT_LINK}"
            )
            await state.clear()
        else:
            await message.answer(texts.CHANNEL_BALANCE_LOW, reply_markup=channel_keyboard())
    else:
        await message.answer("Выбери один из каналов:", reply_markup=channel_keyboard())



def _is_owner(message: Message) -> bool:
    return bool(OWNER_TELEGRAM_ID) and str(message.from_user.id) == str(
        OWNER_TELEGRAM_ID
    )


@dp.message(Command("broadcast"))
async def handle_broadcast(message: Message):
    # Доступно только вам. Рассылает текст всем, кто хоть раз писал боту.
    if not _is_owner(message):
        return

    text_to_send = message.text.removeprefix("/broadcast").strip()
    if not text_to_send:
        await message.answer("Использование: /broadcast текст сообщения")
        return

    chat_ids = await get_all_chat_ids()
    sent, failed = 0, 0
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id, text_to_send)
            sent += 1
        except TelegramBadRequest:
            failed += 1
        await asyncio.sleep(0.05)  # чтобы не упереться в лимиты Telegram

    await message.answer(f"Рассылка завершена. Отправлено: {sent}, не удалось: {failed}")


@dp.message(Command("check_inactive"))
async def handle_check_inactive_manual(message: Message):
    # Доступно только вам. Ручной запуск проверки неактивных (не дожидаясь
    # автоматического фонового прогона).
    if not _is_owner(message):
        return
    await run_inactivity_check(notify_owner=True)


# Всё, что не попало ни в одно из состояний/команд выше — по умолчанию
# уходит на эскалацию, а не игнорируется и не обрабатывается "как получится".
@dp.message()
async def fallback(message: Message):
    await message.answer(texts.ESCALATION_GENERIC.format(support_link=SUPPORT_LINK))


async def run_inactivity_check(notify_owner: bool = False):
    """
    Проверяет, у кого давно (INACTIVITY_DAYS) не было ни одного
    postback-события, и убирает таких пользователей из указанных каналов
    (CHANNEL_IDS). Требует, чтобы бот был администратором в этих каналах.
    """
    if not CHANNEL_IDS:
        return

    inactive = await get_inactive_traders(INACTIVITY_DAYS)
    removed_count = 0

    for trader in inactive:
        chat_id = trader.get("telegram_chat_id")
        if not chat_id:
            continue
        for channel_id in CHANNEL_IDS:
            try:
                await bot.ban_chat_member(channel_id, int(chat_id))
                await bot.unban_chat_member(channel_id, int(chat_id))
                removed_count += 1
            except TelegramBadRequest:
                # Пользователя не было в канале, или бот не админ, или другая
                # проблема — пропускаем, не роняем весь цикл проверки
                continue

    if notify_owner and OWNER_TELEGRAM_ID:
        try:
            await bot.send_message(
                OWNER_TELEGRAM_ID,
                f"Проверка неактивности завершена. Неактивных найдено: "
                f"{len(inactive)}. Удалений из каналов выполнено: {removed_count}.",
            )
        except TelegramBadRequest:
            pass


async def inactivity_background_loop():
    # Проверяет неактивных раз в сутки, пока бот работает
    while True:
        await asyncio.sleep(24 * 60 * 60)
        await run_inactivity_check(notify_owner=True)


async def start_bot_polling():
    asyncio.create_task(inactivity_background_loop())
    await dp.start_polling(bot)



import asyncio

async def verification_reminder(bot, chat_id, uid, get_trader):
    await asyncio.sleep(3600)
    trader = await get_trader(uid)
    if trader and trader.get("verified") != "Yes":
        await bot.send_message(chat_id, "Привет! Как твои успехи?\nНе забудь пройти верификацию.\n\nЕсли что-то не получается — напиши мне:\n@max_supportTraide")
    await asyncio.sleep(7200)
    trader = await get_trader(uid)
    if trader and trader.get("verified") != "Yes":
        await bot.send_message(chat_id, "Привет! Получилось пройти верификацию?\nЕсли есть сложности — напиши мне:\n@max_supportTraide")

async def deposit_reminder(bot, chat_id, uid, get_trader):
    await asyncio.sleep(3600)
    trader = await get_trader(uid)
    if trader and float(trader.get("ftd_amount") or 0) <= 0:
        await bot.send_message(chat_id, "Привет! Удалось пополнить баланс?\n\nЕсли возникли проблемы — напиши мне:\n@max_supportTraide")
    await asyncio.sleep(7200)
    trader = await get_trader(uid)
    if trader and float(trader.get("ftd_amount") or 0) <= 0:
        await bot.send_message(chat_id, "Привет! Как продвигается пополнение?\n\nЕсли появились сложности — напиши мне:\n@max_supportTraide")
