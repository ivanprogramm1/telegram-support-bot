import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    FSInputFile,
    ReplyKeyboardRemove,
)
from aiogram.exceptions import TelegramBadRequest

import texts

from config import (
    BOT_TOKEN,
    SUPPORT_USERNAME,
    OWNER_TELEGRAM_ID,
    CHANNEL_IDS,
    INACTIVITY_DAYS,
    VERIFICATION_IMAGES,
    WORKFLOW_IMAGES,
    FAMILY_VOICES,
)

from db import (
    get_trader,
    link_telegram_chat,
    get_all_chat_ids,
    get_inactive_traders,
)


bot = Bot(token=BOT_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)


SUPPORT_LINK = f"https://t.me/{SUPPORT_USERNAME}"


class Flow(StatesGroup):
    waiting_uid = State()
    waiting_verification_confirm = State()
    waiting_explain = State()
    waiting_deposit_confirm = State()
    waiting_strategy_confirm = State()
    waiting_workflow_confirm = State()
    waiting_rules_confirm = State()
    waiting_channel_choice = State()



# =========================
# КЛАВИАТУРЫ
# =========================


def verification_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=texts.BTN_VERIFIED_DONE
                )
            ],
            [
                KeyboardButton(
                    text=texts.BTN_SUPPORT
                )
            ],
        ],
        resize_keyboard=True,
    )


def explain_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=texts.BTN_EXPLAIN
                )
            ],
            [
                KeyboardButton(
                    text=texts.BTN_PERSONAL
                )
            ],
        ],
        resize_keyboard=True,
    )


def deposit_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=texts.BTN_DEPOSIT_DONE
                )
            ]
        ],
        resize_keyboard=True,
    )


def continue_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="Дальше →"
                )
            ]
        ],
        resize_keyboard=True,
    )


def channel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=texts.BTN_FAMILY
                )
            ],
            [
                KeyboardButton(
                    text=texts.BTN_CHANNEL_OTC
                )
            ],
        ],
        resize_keyboard=True,
    )



# =========================
# START
# =========================


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        texts.WELCOME
    )

    await state.set_state(
        Flow.waiting_uid
    )



# =========================
# SUPPORT / FAQ
# =========================


@dp.message(Command("support"))
@dp.message(F.text == texts.BTN_SUPPORT)
async def support(message: Message):

    await message.answer(
        texts.ESCALATION_GENERIC.format(
            support_link=SUPPORT_LINK
        )
    )



# =========================
# ID POCKET OPTION
# =========================


@dp.message(
    Flow.waiting_uid,
    F.text.regexp(r"^\d+$")
)
async def get_uid(
    message: Message,
    state: FSMContext
):

    uid = message.text.strip()

    trader = await get_trader(uid)


    if trader:

        await link_telegram_chat(
            uid,
            message.chat.id
        )

        await state.update_data(
            uid=uid
        )


        await message.answer(
            texts.UID_FOUND_VERIFICATION
        )


        await message.answer(
            texts.VERIFICATION_IMPORTANCE
        )


        for image in VERIFICATION_IMAGES:
            await message.answer_photo(
                FSInputFile(image)
            )


        await message.answer(
            texts.VERIFICATION_PENDING_PROMPT,
            reply_markup=verification_keyboard()
        )


        await state.set_state(
            Flow.waiting_verification_confirm
        )


    else:

        await message.answer(
            texts.UID_NOT_FOUND
        )



@dp.message(Flow.waiting_uid)
async def wrong_uid(message: Message):

    await message.answer(
        texts.INVALID_UID_FORMAT
    )



# =========================
# ВЕРИФИКАЦИЯ ПРОЙДЕНА
# =========================


@dp.message(
    Flow.waiting_verification_confirm,
    F.text == texts.BTN_VERIFIED_DONE
)
async def verification_done(
    message: Message,
    state: FSMContext
):

    await message.answer(
        "Принято ✅"
    )


    await message.answer(
        texts.AFTER_VERIFICATION_TEXT,
        reply_markup=explain_keyboard()
    )


    await state.set_state(
        Flow.waiting_explain
    )

# =========================
# ЛИЧНО
# =========================


@dp.message(
    Flow.waiting_explain,
    F.text == texts.BTN_PERSONAL
)
async def personal_contact(
    message: Message,
    state: FSMContext
):

    await message.answer(
        f"Хорошо, напиши мне лично:\n{SUPPORT_LINK}"
    )



# =========================
# ПОЯСНИТЬ
# =========================


@dp.message(
    Flow.waiting_explain,
    F.text == texts.BTN_EXPLAIN
)
async def explain(
    message: Message,
    state: FSMContext
):

    await message.answer(
        texts.STRATEGY_INFO
    )


    for image in WORKFLOW_IMAGES:
        await message.answer_photo(
            FSInputFile(image)
        )


    await message.answer(
        texts.DEPOSIT_TEXT,
        reply_markup=deposit_keyboard()
    )


    await state.set_state(
        Flow.waiting_deposit_confirm
    )



# =========================
# ПРОВЕРКА ДЕПОЗИТА
# =========================


@dp.message(
    Flow.waiting_deposit_confirm,
    F.text == texts.BTN_DEPOSIT_DONE
)
async def check_deposit(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    uid = data.get("uid")


    trader = await get_trader(uid)


    balance = 0


    if trader:

        balance = float(
            trader.get("balance")
            or trader.get("ftd_amount")
            or 0
        )


    if trader and balance > 0:


        await message.answer(
            "Отлично, баланс вижу ✅\nВыбери, куда вступить:",
            reply_markup=channel_keyboard()
        )


        await state.set_state(
            Flow.waiting_channel_choice
        )


    else:


        await message.answer(
            texts.DEPOSIT_NOT_YET,
            reply_markup=deposit_keyboard()
        )



# =========================
# ВЫБОР КАНАЛОВ
# =========================


@dp.message(
    Flow.waiting_channel_choice
)
async def channel_choice(
    message: Message,
    state: FSMContext
):


    data = await state.get_data()

    uid = data.get("uid")


    trader = await get_trader(uid)


    balance = 0


    if trader:

        balance = float(
            trader.get("balance")
            or trader.get("ftd_amount")
            or 0
        )


    # СЕМЬЯ + РОБОТ

    if message.text == texts.BTN_FAMILY:


        await message.answer(
            f"{texts.CHANNEL_FAMILY}\n\n"
            f"{texts.CHANNEL_FAMILY_LINK}\n\n"
            f"Робот:\n{texts.ROBOT_LINK}"
        )


        await message.answer(
            texts.FAMILY_WARNING
        )


        for voice in FAMILY_VOICES:

            await message.answer_voice(
                FSInputFile(voice)
            )


        await message.answer(
            f"Если будут вопросы — пиши мне:\n{SUPPORT_LINK}"
        )


        # НЕ очищаем состояние,
        # чтобы человек мог нажать OTC после семьи

        return



    # OTC

    if message.text == texts.BTN_CHANNEL_OTC:


        if balance >= 200:


            await message.answer(
                f"{texts.CHANNEL_OTC}\n\n"
                f"{texts.CHANNEL_OTC_LINK}"
            )


            await message.answer(
                f"Готово ✅\n"
                f"Если будут вопросы:\n{SUPPORT_LINK}"
            )


            await state.clear()


        else:


            await message.answer(
                texts.CHANNEL_BALANCE_LOW,
                reply_markup=channel_keyboard()
            )


        return



    await message.answer(
        "Выбери один из вариантов:",
        reply_markup=channel_keyboard()
    )



# =========================
# АДМИН
# =========================


def is_owner(message: Message):

    return (
        OWNER_TELEGRAM_ID
        and str(message.from_user.id)
        == str(OWNER_TELEGRAM_ID)
    )



@dp.message(Command("broadcast"))
async def broadcast(
    message: Message
):


    if not is_owner(message):
        return


    text = (
        message.text
        .replace("/broadcast", "")
        .strip()
    )


    if not text:

        await message.answer(
            "Использование:\n/broadcast текст"
        )

        return



    users = await get_all_chat_ids()


    sent = 0


    for chat_id in users:

        try:

            await bot.send_message(
                chat_id,
                text
            )

            sent += 1


        except TelegramBadRequest:

            pass


        await asyncio.sleep(
            0.05
        )


    await message.answer(
        f"Отправлено: {sent}"
    )



# =========================
# УДАЛЕНИЕ НЕАКТИВНЫХ
# =========================


async def run_inactivity_check():


    users = await get_inactive_traders(
        INACTIVITY_DAYS
    )


    for user in users:


        chat_id = user.get(
            "telegram_chat_id"
        )


        if not chat_id:
            continue



        for channel in CHANNEL_IDS:


            try:

                await bot.ban_chat_member(
                    channel,
                    int(chat_id)
                )


                await bot.unban_chat_member(
                    channel,
                    int(chat_id)
                )


            except TelegramBadRequest:

                pass



@dp.message(Command("check_inactive"))
async def manual_check(
    message: Message
):

    if not is_owner(message):
        return


    await run_inactivity_check()


    await message.answer(
        "Проверка завершена"
    )



# =========================
# FALLBACK
# =========================


@dp.message()
async def fallback(
    message: Message
):

    await message.answer(
        texts.ESCALATION_GENERIC.format(
            support_link=SUPPORT_LINK
        )
    )



# =========================
# ЗАПУСК
# =========================


async def start_bot_polling():

    await dp.start_polling(
        bot
    )
