import asyncio
from asyncio.log import logger
from pytonconnect import TonConnect
from sync_logic import get_translation, generate_captcha, translations, get_user_language, generate_referral_link, \
    get_connector
from config import API_TOKEN
from models import User, Session
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    context = dp.current_state(user=message.from_user.id)
    referral_code = message.get_args()
    if referral_code:
        user = Session.query(User).filter(User.telegram_id == referral_code).first()
        user.referrals_count += 1
    user = Session.query(User).filter(User.telegram_id == message.from_user.id).first()
    if not user:
        user = User(telegram_id=message.from_user.id, language='en')
        Session.add(user)
        Session.commit()
        user_language = 'ru'
    else:
        user_language = get_user_language(message.from_user.id, Session)
    captcha, correct_answer = generate_captcha()
    await context.set_data({'correct_answer': correct_answer})
    await message.reply(get_translation(user_language, 'welcome', captcha=captcha))


@dp.message_handler(commands=['lang'])
async def set_language(message: types.Message):
    language = message.get_args().lower()
    if language in translations:
        user = Session.query(User).filter(User.telegram_id == message.from_user.id).first()
        user.language = language
        Session.commit()
        context = dp.current_state(user=message.from_user.id)
        await context.update_data(language=language)
        await message.reply(get_translation(language, 'language_set'))
    else:
        await message.reply("Language not supported. Supported languages are: en, ru.")


@dp.message_handler()
async def handle_message(message: types.Message):
    context = dp.current_state(user=message.from_user.id)
    user_data = await context.get_data()
    correct_answer = user_data.get('correct_answer')
    user_language = get_user_language(message.from_user.id, Session)
    username = message.from_user.first_name
    await context.set_data({'message': message})

    try:
        user_input = int(message.text)
        if correct_answer is not None and user_input == correct_answer:
            await message.reply(get_translation(user_language, 'captcha_passed'))
            if await is_subscribed('@nmkyt1', message.from_user.id):
                await main_menu(message.from_user.id)
            else:
                welcome_message = get_translation(user_language, 'welcome_message', username=username)
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(get_translation(user_language, 'sub_check_button'),
                                                        callback_data="check_subscription"))
                await message.reply(welcome_message, reply_markup=keyboard)
        else:
            await message.reply(get_translation(user_language, 'incorrect_answer'))
            captcha, correct_answer = generate_captcha()
            await context.update_data(correct_answer=correct_answer)
            await message.reply(get_translation(user_language, 'welcome', captcha=captcha))
    except ValueError:
        await message.reply(get_translation(user_language, 'numeric_input'))


@dp.callback_query_handler()
async def process_callback(call: types.CallbackQuery):
    await call.answer()
    message = call.message
    if call.data == 'check_subscription':
        if await is_subscribed('@nmkyt1', call.from_user.id):
            await main_menu(call.from_user.id)

    if call.data == 'check_subscription':
        if await is_subscribed('@nmkyt1', call.from_user.id):
            user = Session.query(User).filter(User.telegram_id == call.from_user.id).first()
            user.grum_balance += 50
            Session.commit()
            await main_menu(call.from_user.id)
    elif call.data == "start":
        await main_menu(call.from_user.id)
    elif call.data == "send_tr":
        pass
    elif call.data == 'disconnect':
        await disconnect_wallet(message)
    else:
        if call.data == 'connect_wallet':
            await connect_wallet(call.from_user.id, 'Wallet')
    return handle_message


async def is_subscribed(chat_id, user_id):
    status = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    if status['status'] == 'left':
        return False
    else:
        return True


async def main_menu(user_id):

    context = dp.current_state(user=user_id)
    user_data = await context.get_data()
    message = user_data.get('message')

    connector = get_connector(user_id)
    connected = await connector.restore_connection()

    user = Session.query(User).filter(User.telegram_id == user_id).first()

    user_language = user.language
    grum_balance = user.grum_balance
    ton_balance = user.ton_balance
    referral_link = generate_referral_link('DmitriyLoginov1_Bot', user_id)
    referrals_count = user.referrals_count
    ton_link = user.ton_link

    menu_message = get_translation(user_language,
                                   key='main_menu',
                                   GRUM_balance=grum_balance,
                                   referral=referral_link,
                                   referral_count=referrals_count,
                                   TON_balance=ton_balance,
                                   TON_LINK=ton_link
                                   )

    keyboard = types.InlineKeyboardMarkup()
    # keyboard.add(types.InlineKeyboardButton(get_translation(user_language, 'earn_grum_button')))
    # keyboard.add(types.InlineKeyboardButton(get_translation(user_language, 'earn_ton_button')))
    if connected:
        keyboard.add(types.InlineKeyboardButton(get_translation(user_language, 'send_transaction_button'),
                                                callback_data='send_tr'))
        keyboard.add(types.InlineKeyboardButton(get_translation(user_language, 'disconnect_wallet_button'),
                                                callback_data='disconnect_wallet'))
    else:
        keyboard.add(types.InlineKeyboardButton(text=get_translation(user_language, "connect_wallet_button"),
                                                callback_data='connect_wallet'))
    await message.reply(menu_message, reply_markup=keyboard)


async def connect_wallet(user_id, wallet_name: str):

    context = dp.current_state(user=user_id)
    user_data = await context.get_data()
    message = user_data.get('message')

    connector = get_connector(user_id)

    wallets_list = connector.get_wallets()
    wallet = None

    for w in wallets_list:
        if w['name'] == wallet_name:
            wallet = w

    if wallet is None:
        raise Exception(f'Unknown wallet: {wallet_name}')

    generated_url = await connector.connect(wallet)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Connect', url=generated_url))

    await message.answer(text='Connect wallet within 3 minutes', reply_markup=keyboard)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Start', callback_data='start'))

    for i in range(1, 180):
        await asyncio.sleep(1)
        if connector.connected:
            if connector.account.address:
                wallet_address = connector.account.address
                user = Session.query(User).filter(User.telegram_id == user_id).first()
                user.ton_link = wallet_address
                await message.answer(f'You are connected with address <code>{wallet_address}</code>',
                                     reply_markup=keyboard)
                logger.info(f'Connected with address: {wallet_address}')
            return

    await message.answer(f'Timeout error!', reply_markup=keyboard)


async def disconnect_wallet(message):
    connector = get_connector(message.from_user.id)
    await connector.restore_connection()
    await connector.disconnect()
    await message.answer('You have been successfully disconnected!')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
