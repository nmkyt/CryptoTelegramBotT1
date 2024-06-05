import asyncio
from asyncio.log import logger
from sync_logic import get_translation, generate_referral_link, get_connector, get_user_language
from models import User, Session
from aiogram import types


async def connect_wallet(user_id, wallet_name: str, dp):
    context = dp.current_state(user=user_id)
    user_data = await context.get_data()
    message = user_data.get('message')
    user_language = get_user_language(message.from_user.id, Session)

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
    keyboard.add(types.InlineKeyboardButton(get_translation(user_language, 'connect_button'), url=generated_url))
    keyboard.add(types.InlineKeyboardButton(get_translation(user_language, 'main_menu_button'),
                                            callback_data='main_menu'))

    await message.answer(get_translation(user_language, 'connect_wallet_text'), reply_markup=keyboard)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(get_translation(user_language, 'main_menu_button'),
                                            callback_data='main_menu'))

    for i in range(1, 180):
        await asyncio.sleep(1)
        if connector.connected:
            if connector.account.address:
                wallet_address = connector.account.address
                user = Session.query(User).filter(User.telegram_id == user_id).first()
                user.ton_link = wallet_address
                await message.answer(get_translation(user_language, 'connection_success', wallet_address=wallet_address),
                                     reply_markup=keyboard)
                logger.info(f'Connected with address: {wallet_address}')
            return

    await message.answer(get_translation(user_language, 'timeout_error'), reply_markup=keyboard)


async def disconnect_wallet(message):
    user_language = get_user_language(message.from_user.id, Session)
    connector = get_connector(message.from_user.id)
    await connector.restore_connection()
    await connector.disconnect()
    await message.answer(get_translation(user_language, 'disconnection_success'))


async def select_language(message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('Русский', callback_data='lang_ru'))
    keyboard.add(types.InlineKeyboardButton('English', callback_data='lang_eng'))
    await message.reply('Выберите язык | Select language', reply_markup=keyboard)


async def is_subscribed(chat_id, user_id, bot):
    status = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    if status['status'] == 'left':
        return False
    else:
        return True


async def settings(user_id, message):
    connector = get_connector(user_id)
    connected = await connector.restore_connection()
    user_language = get_user_language(message.from_user.id, Session)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(get_translation(user_language, 'change_lang_button'),
                                            callback_data='select_language'))
    if connected:
        keyboard.add(types.InlineKeyboardButton(get_translation(user_language, 'disconnect_wallet_button'),
                                                callback_data='disconnect'))
    keyboard.add(types.InlineKeyboardButton(get_translation(user_language, 'main_menu_button'),
                                            callback_data='main_menu'))
    await message.reply(get_translation(user_language, 'settings_menu'), reply_markup=keyboard)


async def main_menu(user_id, dp):
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
    keyboard.add(types.InlineKeyboardButton(get_translation(user_language, 'earn_grum_button'),
                                            callback_data='earn_grum'))
    keyboard.add(types.InlineKeyboardButton(get_translation(user_language, 'earn_ton_button'),
                                            callback_data='earn_ton'))
    if connected:
        keyboard.add(types.InlineKeyboardButton(get_translation(user_language, 'send_transaction_button'),
                                                callback_data='send_tr'))
    else:
        keyboard.add(types.InlineKeyboardButton(text=get_translation(user_language, "connect_wallet_button"),
                                                callback_data='connect_wallet'))
    keyboard.add(types.InlineKeyboardButton(get_translation(user_language, 'settings_button'),
                                            callback_data='settings'))
    await message.reply(menu_message, reply_markup=keyboard)

