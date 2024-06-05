from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL
from pytonconnect.storage import IStorage

# Подключение к базе данных PostgreSQL
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = SessionLocal()

Base = declarative_base()


# Модель для хранения информации о пользователях
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    grum_balance = Column(Integer, default=0)
    ton_balance = Column(Integer, default=0)
    referrals_count = Column(Integer, default=0)
    language = Column(String)
    ton_link = Column(String)


storage = {}


class TcStorage(IStorage):

    def __init__(self, chat_id: int):
        self.chat_id = chat_id

    def _get_key(self, key: str):
        return str(self.chat_id) + key

    async def set_item(self, key: str, value: str):
        storage[self._get_key(key)] = value

    async def get_item(self, key: str, default_value: str = None):
        return storage.get(self._get_key(key), default_value)

    async def remove_item(self, key: str):
        storage.pop(self._get_key(key))


# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)
