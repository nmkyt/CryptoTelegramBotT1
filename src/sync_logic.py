import random
import json
from models import User, Session, TcStorage
from config import MANIFEST_URL
from pytonconnect import TonConnect


# Функция для генерации капчи
def generate_captcha():
    num1 = random.randint(5, 50)
    num2 = random.randint(5, 50)
    if num1 < num2:
        operation = '+'
    else:
        operation = random.choice(['+', '-'])
    if operation == '+':
        captcha = f"{num1} + {num2} = ?"
        correct_answer = num1 + num2
    else:
        captcha = f"{num1} - {num2} = ?"
        correct_answer = num1 - num2
    return captcha, correct_answer


# Функция для получения перевода
with open('..\\lang\\lang_en.json', 'r', encoding='utf-8') as f:
    lang_en = json.load(f)
with open('..\\lang\\lang_ru.json', 'r', encoding='utf-8') as f:
    lang_ru = json.load(f)

translations = {
    'en': lang_en,
    'ru': lang_ru
}


# Функция для получения перевода
def get_translation(user_language, key, **kwargs):
    return translations[user_language].get(key).format(**kwargs)


# Кэшы
user_language_cache = {}
user_sub_cache = {}


def get_user_language(user_id: int, db: Session):
    if user_id in user_language_cache:
        return user_language_cache[user_id]

    # Запрашиваем язык пользователя из базы данных
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if user:
        language = user.language
        # Сохраняем язык пользователя в кэше
        user_language_cache[user_id] = language
        return language

    return None


def generate_referral_link(bot_username: str, referrer_id: int = None):
    base_link = f"https://t.me/{bot_username}?start="
    if referrer_id:
        return base_link + str(referrer_id)
    return base_link


def get_connector(chat_id: int):
    return TonConnect(MANIFEST_URL, storage=TcStorage(chat_id))
