from async_logic import main_menu, disconnect_wallet, connect_wallet, select_language, settings, is_subscribed
from sync_logic import get_translation, generate_captcha, set_language, get_user_language
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
    await context.set_data({'message': message})

    referral_code = message.get_args()
    if referral_code:
        user = Session.query(User).filter(User.telegram_id == referral_code).first()
        user.referrals_count = int(user.referrals_count) + 1
        user.grum_balance = int(user.grum_balance) + 50
    user = Session.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user:
        user = User(telegram_id=message.from_user.id, language='ru')
        Session.add(user)
        Session.commit()
        await select_language(message)
    else:
        user_language = get_user_language(message.from_user.id, Session)

        captcha, correct_answer = generate_captcha()
        await context.set_data({'correct_answer': correct_answer})
        await message.reply(get_translation(user_language, 'welcome', captcha=captcha))


@dp.message_handler()
async def handle_message(message: types.Message):
    context = dp.current_state(user=message.from_user.id)
    user_data = await context.get_data()
    correct_answer = user_data.get('correct_answer')
    user_language = get_user_language(message.from_user.id, Session)
    username = message.from_user.first_name
    await context.update_data({'message': message})

    try:
        user_input = int(message.text)
        if correct_answer is not None and user_input == correct_answer:
            await message.reply(get_translation(user_language, 'captcha_passed'))
            if await is_subscribed('@nmkyt1', message.from_user.id, bot):
                await main_menu(message.from_user.id, dp)
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
    context = dp.current_state(user=call.from_user.id)
    user_data = await context.get_data()
    message = user_data.get('message')
    correct_answer = user_data.get('correct_answer')

    if call.data == 'check_subscription':
        if await is_subscribed('@nmkyt1', call.from_user.id, bot):
            user = Session.query(User).filter(User.telegram_id == call.from_user.id).first()
            user.grum_balance = int(user.grum_balance) + 50
            Session.commit()
            await main_menu(call.from_user.id, dp)
    elif call.data == 'main_menu':
        await main_menu(call.from_user.id, dp)
    elif call.data == 'lang_ru':
        set_language('ru', call.from_user.id)
        if correct_answer is None:
            captcha, correct_answer = generate_captcha()
            await context.set_data({'correct_answer': correct_answer})
            await message.reply(get_translation('ru', 'welcome', captcha=captcha))
        else:
            await main_menu(call.from_user.id, dp)
    elif call.data == 'lang_eng':
        set_language('en', call.from_user.id)
        if correct_answer is None:
            captcha, correct_answer = generate_captcha()
            await context.set_data({'correct_answer': correct_answer})
            await message.reply(get_translation('en', 'welcome', captcha=captcha))
        else:
            await main_menu(call.from_user.id, dp)
    elif call.data == 'settings':
        await settings(call.from_user.id, message)
    elif call.data == 'select_language':
        await select_language(message)
    elif call.data == 'earn_grum':
        pass
    elif call.data == 'earn_ton':
        pass
    elif call.data == "start":
        await main_menu(call.from_user.id, dp)
    elif call.data == "send_tr":
        pass
    elif call.data == 'disconnect':
        await disconnect_wallet(message)
        await main_menu(call.from_user.id, dp)
    else:
        if call.data == 'connect_wallet':
            await connect_wallet(call.from_user.id, 'Wallet', dp)
    return handle_message


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
