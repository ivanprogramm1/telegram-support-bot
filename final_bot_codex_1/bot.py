import asyncio
import logging
import re

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
)
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import texts

from config import (
    BOT_TOKEN,
    SUPPORT_USERNAME,
    OWNER_TELEGRAM_IDS,
    CHANNEL_IDS,
    INACTIVITY_DAYS,
    INACTIVITY_CHECK_INTERVAL_DAYS,
    VERIFICATION_IMAGES,
    WORKFLOW_IMAGES,
    FAMILY_VOICES,
)

from db import (
    get_trader,
    link_telegram_chat,
    allow_manual_referral,
    get_all_chat_ids,
    get_inactive_traders,
    get_stats,
)

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)


SUPPORT_LINK = f"https://t.me/{SUPPORT_USERNAME}"


def parse_money(value):
    if value is None:
        return 0

    normalized = re.sub(
        r"[^0-9.,-]",
        "",
        str(value)
    )

    if not normalized:
        return 0

    if "," in normalized and "." in normalized:
        normalized = normalized.replace(",", "")
    else:
        normalized = normalized.replace(",", ".")

    try:
        return float(normalized)
    except ValueError:
        return 0


def trader_balance(trader):
    if not trader:
        return 0

    for field in (
        "balance",
        "ftd_amount",
        "sum_of_deposits",
        "commission",
    ):
        amount = parse_money(
            trader.get(field)
        )

        if amount > 0:
            return amount

    deposits_count = parse_money(
        trader.get("count_of_deposits")
    )

    if deposits_count > 0:
        return deposits_count

    return 0


def has_postback_data(trader):
    if not trader:
        return False

    postback_fields = (
        "reg_date",
        "activity_date",
        "country",
        "verified",
        "balance",
        "ftd_amount",
        "ftd_date",
        "count_of_deposits",
        "sum_of_deposits",
        "sum_of_bonuses",
        "count_of_bonuses",
        "self_excluded",
        "commission",
        "link_type",
        "link",
    )

    return any(
        str(trader.get(field) or "").strip()
        for field in postback_fields
    )


def is_manual_referral_allowed(trader):
    if not trader:
        return False

    return str(trader.get("manual_allowed") or "").lower() == "yes"


class Flow(StatesGroup):
    waiting_uid = State()
    waiting_verification_confirm = State()
    waiting_explain = State()
    waiting_deposit_confirm = State()
    waiting_strategy_confirm = State()
    waiting_workflow_confirm = State()
    waiting_rules_confirm = State()
    waiting_channel_choice = State()
    waiting_broadcast_text = State()



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
                    text=texts.BTN_SUPPORT
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


def admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Статистика"),
                KeyboardButton(text="📣 Рассылка"),
            ],
            [
                KeyboardButton(text="🧹 Проверить неактивных"),
                KeyboardButton(text="📋 Команды"),
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


@dp.message(Command("admin"))
async def admin_panel_from_any_step(
    message: Message,
    state: FSMContext
):

    if not is_owner(message):
        return


    await state.clear()


    await message.answer(
        "Админ-панель открыта. Выбери действие:",
        reply_markup=admin_keyboard()
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
    
    logger.info(f"🔍 Проверяю UID по постбекам: {uid}")

    trader = await get_trader(uid)

    await link_telegram_chat(
        uid,
        message.chat.id
    )

    if not has_postback_data(trader) and not is_manual_referral_allowed(trader):

        logger.warning(f"❌ UID без постбека Pocket и ручного допуска: {uid}")

        await message.answer(
            texts.UID_NOT_FOUND
        )

        return

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
        texts.LAST_STEP_TEXT,
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
        texts.STRATEGY_AFTER_IMAGES,
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


    balance = trader_balance(trader)


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


    balance = trader_balance(trader)


    # СЕМЬЯ + РОБОТ

    if message.text == texts.BTN_FAMILY:


        await message.answer(
            texts.CHANNEL_FAMILY_TEXT
        )


        await message.answer(
            texts.RULES_WARNING
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
                texts.CHANNEL_OTC_TEXT
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
        str(message.from_user.id)
        in {str(owner_id) for owner_id in OWNER_TELEGRAM_IDS}
    )


@dp.message(F.text == "📋 Команды")
async def admin_commands(
    message: Message
):

    if not is_owner(message):
        return


    await message.answer(
        "Команды админа:\n\n"
        "/admin — открыть админ-панель\n"
        "/allow ID — добавить старого реферала вручную\n"
        "/broadcast текст — отправить рассылку всем пользователям\n"
        "/check_inactive — проверить и удалить неактивных из каналов\n\n"
        "Кнопки в панели:\n"
        "📊 Статистика — показать количество UID и пользователей\n"
        "📣 Рассылка — отправить сообщение через удобный режим\n"
        "🧹 Проверить неактивных — ручной запуск чистки\n"
        "📋 Команды — показать эту подсказку",
        reply_markup=admin_keyboard()
    )


@dp.message(Command("allow"))
async def allow_referral(
    message: Message
):

    if not is_owner(message):
        return


    uid = (
        message.text
        .replace("/allow", "")
        .strip()
    )


    if not uid or not uid.isdigit():

        await message.answer(
            "Использование:\n/allow ID\n\nНапример:\n/allow 127671970"
        )

        return


    await allow_manual_referral(uid)


    await message.answer(
        f"UID {uid} добавлен как старый реферал ✅\nТеперь он сможет пройти сценарий в боте."
    )


@dp.message(F.text == "📊 Статистика")
async def admin_stats(
    message: Message
):

    if not is_owner(message):
        return


    stats = await get_stats()


    await message.answer(
        "Статистика:\n"
        f"Всего UID в таблице: {stats['total']}\n"
        f"Пользователей с Telegram: {stats['with_chats']}\n"
        f"С депозитом: {stats['with_deposit']}"
    )


@dp.message(F.text == "📣 Рассылка")
async def admin_broadcast_start(
    message: Message,
    state: FSMContext
):

    if not is_owner(message):
        return


    await state.set_state(
        Flow.waiting_broadcast_text
    )


    await message.answer(
        "Отправь текст рассылки одним сообщением."
    )


@dp.message(
    Flow.waiting_broadcast_text
)
async def admin_broadcast_send(
    message: Message,
    state: FSMContext
):

    if not is_owner(message):
        return


    text = (message.text or "").strip()


    if not text:

        await message.answer(
            "Нужен текст сообщения."
        )

        return


    await state.clear()


    sent = await send_broadcast(text)


    await message.answer(
        f"Рассылка завершена. Отправлено: {sent}",
        reply_markup=admin_keyboard()
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



    sent = await send_broadcast(text)


    await message.answer(
        f"Отправлено: {sent}"
    )


async def send_broadcast(text: str):

    users = await get_all_chat_ids()


    sent = 0


    for chat_id in users:

        try:

            await bot.send_message(
                chat_id,
                text
            )

            sent += 1


        except (TelegramBadRequest, TelegramForbiddenError):

            pass


        await asyncio.sleep(
            0.05
        )


    return sent



# =========================
# УДАЛЕНИЕ НЕАКТИВНЫХ
# =========================


async def run_inactivity_check():


    users = await get_inactive_traders(
        INACTIVITY_DAYS
    )

    removed = 0


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


            except (TelegramBadRequest, TelegramForbiddenError):

                pass


        removed += 1


    return removed


async def inactivity_scheduler():

    while True:

        await asyncio.sleep(
            INACTIVITY_CHECK_INTERVAL_DAYS * 24 * 60 * 60
        )


        try:

            removed = await run_inactivity_check()

            logger.info(
                f"🧹 Автопроверка неактивных завершена. Удалено: {removed}"
            )


        except Exception:

            logger.exception(
                "Ошибка при автопроверке неактивных"
            )


@dp.message(F.text == "🧹 Проверить неактивных")
async def admin_manual_check_button(
    message: Message
):

    if not is_owner(message):
        return


    removed = await run_inactivity_check()


    await message.answer(
        f"Проверка завершена. Удалено: {removed}",
        reply_markup=admin_keyboard()
    )



@dp.message(Command("check_inactive"))
async def manual_check(
    message: Message
):

    if not is_owner(message):
        return


    removed = await run_inactivity_check()


    await message.answer(
        f"Проверка завершена. Удалено: {removed}"
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
