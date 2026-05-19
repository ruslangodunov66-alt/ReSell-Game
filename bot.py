# unified_bot.py - ПОЛНЫЙ СЕРВЕР + ТЕЛЕГРАМ БОТ ДЛЯ RESELL TYCOON
# Работает на хостинге Bothost. Запускает FastAPI в фоне и aiogram бота.
# Вся игровая логика (гонки, скины, аукцион, трейдинг, таксопарк и т.д.) сохранена.

import asyncio
import threading
import uvicorn
import sqlite3
import json
import random
import hashlib
import time as time_module
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from collections import defaultdict

# ==================== КОНФИГ ====================
API_TOKEN = '8747685010:AAH8bN3x0fihSvUzVitijYQLHXeHFhIV5w4'
BOT_USERNAME = 'buygame61_bot'
ADMIN_ID = 1475910449
DB_PATH = "game.db"

def save_players():
    """Заглушка для совместимости со старым кодом. Данные сохраняются через SQLite."""
    pass

# ==================== БАЗОВЫЕ ДАННЫЕ ====================
CATEGORIES = ["👖 Джинсы", "👕 Худи", "🧥 Куртки", "👟 Кроссы", "🎒 Аксессуары"]

BASE_ITEMS = [
    {"cat": "👖 Джинсы", "name": "Levi's 501 Vintage", "base_price": 2000},
    {"cat": "👖 Джинсы", "name": "Carhartt WIP Denim", "base_price": 3500},
    {"cat": "👕 Худи", "name": "Adidas Originals Hoodie", "base_price": 2500},
    {"cat": "👕 Худи", "name": "Nike ACG Fleece", "base_price": 3000},
    {"cat": "🧥 Куртки", "name": "The North Face Nuptse", "base_price": 5000},
    {"cat": "🧥 Куртки", "name": "Alpha Industries MA-1", "base_price": 4000},
    {"cat": "👟 Кроссы", "name": "Nike Air Max 90", "base_price": 3500},
    {"cat": "👟 Кроссы", "name": "Adidas Samba OG", "base_price": 2800},
]

SUPPLIER_ITEM_RARITIES = {
    "обычный": {"name": "Обычный", "color": "⬜", "price_mult_min": 0.8, "price_mult_max": 1.3, "chance": 55},
    "редкий": {"name": "Редкий", "color": "🟦", "price_mult_min": 1.5, "price_mult_max": 2.5, "chance": 25},
    "эпический": {"name": "Эпический", "color": "🟪", "price_mult_min": 2.5, "price_mult_max": 5.0, "chance": 12},
    "легендарный": {"name": "Легендарный", "color": "🟨", "price_mult_min": 5.0, "price_mult_max": 12.0, "chance": 6},
    "мифический": {"name": "Мифический", "color": "🟥", "price_mult_min": 10.0, "price_mult_max": 30.0, "chance": 2},
}

SKINS = [
    {"id": "default", "name": "Новичок", "price": 0, "rarity": "обычный", "sales_required": 0, "emoji": "👶", "description": "Базовый скин.", "limited": False, "max_count": 0, "image_url": "AgACAgIAAxkBAAIDHGn4w7w3AAGnzzdBPwI4mNZEgoIjsAACzhhrG8bbwEsN1TBcMS6PhwEAAwIAA3kAAzsE"},
    {"id": "hustler", "name": "Темщик", "price": 0, "rarity": "обычный", "sales_required": 5, "emoji": "😎", "description": "⭐ Продано 5 товаров.", "limited": False, "max_count": 0, "image_url": "AgACAgIAAxkBAAIDLGn4xLrV_G5vUn9b0lfZbRt9uSNpAAIjE2sbRxXIS2ta2c2uvaRDAQADAgADeQADOwQ"},
    {"id": "boss", "name": "Мажор", "price": 0, "rarity": "обычный", "sales_required": 15, "emoji": "🕴", "description": "🏅 Продано 15 товаров.", "limited": False, "max_count": 0, "image_url": "AgACAgIAAxkBAAIDIGn4w8SxLumhkkue8rlTXiUqetBaAALQGGsbxtvAS3sUKevJKpGYAQADAgADeQADOwQ"},
    {"id": "coffee", "name": "Кофейный барыга", "price": 25000, "rarity": "редкий", "sales_required": 0, "emoji": "💻", "description": "Редкий скин.", "limited": False, "max_count": 0, "image_url": "AgACAgIAAxkBAAIDImn4w8m4lmlm6AYS1kBkt8Dx7ZyXAAL9GGsbxtvAS_vggWeGPBAgAQADAgADeQADOwQ"},
    {"id": "cyber", "name": "Кибер-барыга", "price": 80000, "rarity": "эпический", "sales_required": 0, "emoji": "🤖", "description": "Эпический скин.", "limited": False, "max_count": 0, "image_url": "AgACAgIAAxkBAAIDxWn45SvUS8m2sFIRTRarzV3ylymgAAJGFGsbRxXISwzuA4OGtBJyAQADAgADeQADOwQ"},
    {"id": "casual", "name": "Кэжуал барыга", "price": 5000, "rarity": "обычный", "sales_required": 0, "emoji": "👕", "description": "Обычный скин.", "limited": False, "max_count": 0, "image_url": "AgACAgIAAxkBAAIDyWn45lfPG9qMGWwqqtVvghaY-OpXAAJPFGsbRxXIS30JjvcuwnwHAQADAgADeQADOwQ"},
    {"id": "cyberpunk", "name": "Барыга-киберпанк", "price": 120000, "rarity": "эпический", "sales_required": 0, "emoji": "🦾", "description": "Эпический скин.", "limited": False, "max_count": 0, "image_url": "AgACAgIAAxkBAAIDy2n45wzQNDGj-mZOhvUo3ToyI8MVAAJTFGsbRxXIS-Qrt13FcYnwAQADAgADeQADOwQ"},
    {"id": "legend", "name": "Бог товарки", "price": 500000, "rarity": "легендарный", "sales_required": 0, "emoji": "👑", "description": "Легендарный скин.", "limited": False, "max_count": 0, "image_url": "AgACAgIAAxkBAAIDJGn4w8wheVk6HY-7qpII5w8hQ4lyAAL_GGsbxtvAS2S7TonuV3alAQADAgADeQADOwQ"},
    {"id": "oldmoney", "name": "Олд мани барыга", "price": 180000, "rarity": "эпический", "sales_required": 0, "emoji": "🎩", "description": "Эпический скин.", "limited": False, "max_count": 0, "image_url": "AgACAgIAAxkBAAIDzWn457hhlWHg6jBASBq0EcTDmWEpAAJUFGsbRxXIS1Xa-QcoURaAAQADAgADeQADOwQ"},
    {"id": "bazaar", "name": "Базарный барыга", "price": 35000, "rarity": "редкий", "sales_required": 0, "emoji": "🗣", "description": "Редкий скин.", "limited": False, "max_count": 0, "image_url": "AgACAgIAAxkBAAID0Wn46ouAFjuzjq1yQyOG4FahoM-CAAJlFGsbRxXIS-9X56WNZeVnAQADAgADeQADOwQ"},
    {"id": "creator", "name": "Создатель", "price": 0, "rarity": "мифический", "sales_required": 0, "emoji": "💎", "description": "💎 МИФИЧЕСКИЙ СКИН.", "limited": True, "max_count": 3, "image_url": "AgACAgIAAxkBAAIDz2n46ShGgxc6Z-mfB73cEzOvS74oAAJjFGsbRxXIS67XdFNB5viXAQADAgADeQADOwQ"},
]

CARS = [
    {"id": "zhiguli", "name": "🚗 ВАЗ-2106 Жигули", "price": 15000, "speed_bonus": 10, "income_per_hour": 50, "rarity": "обычный", "image_url": "AgACAgIAAxkBAAIKH2n7eaZvhsyGLQOFcU8fmz7BKgWhAAIkGGsbH9_QS0gOkG0ns94lAQADAgADeQADOwQ"},
    {"id": "granta", "name": "🚙 Лада Гранта", "price": 35000, "speed_bonus": 15, "income_per_hour": 100, "rarity": "обычный", "image_url": "AgACAgIAAxkBAAIKJWn7e2SPU9Y3sbCRzOFO9-nf5Dw5AAIlGGsbH9_QSzJxHsxEUqGUAQADAgADeQADOwQ"},
    {"id": "cclass", "name": "🚘 Mercedes C-Class 2014", "price": 80000, "speed_bonus": 25, "income_per_hour": 200, "rarity": "редкий", "image_url": "AgACAgIAAxkBAAIKLWn7e3QVhA8tYDpJPzpERwRtMdF3AAIpGGsbH9_QS4t1p3Bhq0TwAQADAgADeQADOwQ"},
    {"id": "mustang", "name": "🏎 Ford Mustang Кабриолет", "price": 120000, "speed_bonus": 30, "income_per_hour": 300, "rarity": "редкий", "image_url": "AgACAgIAAxkBAAIKK2n7e3Ca7ti-KAq0As2CCsNvasMbAAIoGGsbH9_QS6URKdMbGfwQAQADAgADeQADOwQ"},
    {"id": "bmwm4", "name": "🏎 BMW M4", "price": 150000, "speed_bonus": 35, "income_per_hour": 350, "rarity": "эпический", "image_url": "AgACAgIAAxkBAAIKKWn7e2wl9oHh_U4ygjOmTNZ-nAmfAAInGGsbH9_QS07bjw42tsNqAQADAgADeQADOwQ"},
    {"id": "w140", "name": "🚘 Mercedes W140", "price": 180000, "speed_bonus": 35, "income_per_hour": 400, "rarity": "эпический", "image_url": "AgACAgIAAxkBAAIKJ2n7e2jABfB9rbxFh3g5wJsAAUj0CgACJhhrGx_f0Eto1dm5lBmv_AEAAwIAA3kAAzsE"},
    {"id": "challenger", "name": "🏎 Dodge Challenger", "price": 250000, "speed_bonus": 45, "income_per_hour": 600, "rarity": "легендарный", "image_url": "AgACAgIAAxkBAAIKNWn7e5kR4aOlGwVlwdhsbw5fvc_CAAItGGsbH9_QS6hSbI8YfnInAQADAgADeQADOwQ"},
    {"id": "ramtrx", "name": "🛻 Dodge Ram TRX", "price": 300000, "speed_bonus": 50, "income_per_hour": 700, "rarity": "легендарный", "image_url": "AgACAgIAAxkBAAIKM2n7e5NrhSVVTc2wUcRsOaBUHDoKAAIsGGsbH9_QS7sNrOC98FMGAQADAgADeQADOwQ"},
    {"id": "bmwm5", "name": "🏎 BMW M5 F90", "price": 400000, "speed_bonus": 55, "income_per_hour": 900, "rarity": "легендарный", "image_url": "AgACAgIAAxkBAAIKL2n7e3dRS58kxBJIwMbQyfhgSbXHAAIqGGsbH9_QS4JTxjSqqMS3AQADAgADeQADOwQ"},
    {"id": "sclass", "name": "🚘 Mercedes S-Class", "price": 600000, "speed_bonus": 65, "income_per_hour": 1200, "rarity": "легендарный", "image_url": "AgACAgIAAxkBAAIKMWn7e46bcc2IvFRWXnL99PAMfahNAAIrGGsbH9_QS8WFReLP1qWmAQADAgADeQADOwQ"},
    {"id": "bmwx7", "name": "🚙 BMW X7", "price": 800000, "speed_bonus": 70, "income_per_hour": 1500, "rarity": "мифический", "image_url": "AgACAgIAAxkBAAIKOWn7e6XgOfa0orm4ZHTXA7BEWqDoAAIvGGsbH9_QS633taC4w8RrAQADAgADeQADOwQ"},
    {"id": "rollsroyce", "name": "👑 Rolls-Royce Phantom", "price": 1500000, "speed_bonus": 90, "income_per_hour": 3000, "rarity": "мифический", "image_url": "AgACAgIAAxkBAAIKN2n7e6AqWY0zFZGO2P9f4hsCdk8bAAIuGGsbH9_QSzUrOdo8uXGlAQADAgADeQADOwQ"},
    {"id": "aventador", "name": "🏎 Lamborghini Aventador", "price": 5000000, "speed_bonus": 95, "income_per_hour": 5000, "rarity": "мифический", "image_url": "AgACAgIAAxkBAAIKPGn7f2Rs5K3TIz7TUtspqjTQ5WweAAJaE2sbhKXhSz4-e1I_GY--AQADAgADeQADOwQ"},
    {"id": "brabus", "name": "👑 Brabus Mansory", "price": 20000000, "speed_bonus": 99, "income_per_hour": 10000, "rarity": "мифический", "image_url": "AgACAgIAAxkBAAIKPmn7f3zPq6X1RER7yHfJKjbkukAgAAJbE2sbhKXhS9npCM9WIdMXAQADAgADeQADOwQ"},
]

HOUSES = [
    {"id": "room", "name": "🏚 Комната в общаге", "price": 0, "income_bonus": 0, "description": "Бесплатное жильё.", "image_url": "AgACAgIAAxkBAAIDw2n45KI6ja7rOv30n_8DdrWCFQwyAAI-FGsbRxXIS4VB50007zQ3AQADAgADeQADOwQ"},
    {"id": "flat", "name": "🏢 Квартира", "price": 10000, "income_bonus": 150, "description": "Уютная квартира. +150₽/день.", "image_url": "AgACAgIAAxkBAAIBeGn3hGvVcFktYFQJP-YNnKti48v1AAKYGWsbUNy4SzN3yqU-dPZwAQADAgADeQADOwQ"},
    {"id": "house", "name": "🏠 Одноэтажный дом", "price": 35000, "income_bonus": 400, "description": "Дом с гаражом. +400₽/день.", "image_url": "AgACAgIAAxkBAAIBemn3hKeq-IxdQ6l6jB7sD10pQPbHAAKUGGsbaAW5S4jG5ecluTqMAQADAgADeQADOwQ"},
    {"id": "villa", "name": "🏰 Богатая вилла", "price": 100000, "income_bonus": 1200, "description": "Вилла с бассейном. +1200₽/день.", "image_url": "AgACAgIAAxkBAAIBfGn3hME0a5rsH1wos1Qyy1AhsYAnAAKVGGsbaAW5SzyFR-E8--65AQADAgADeQADOwQ"},
    {"id": "yacht", "name": "🛥 Яхта", "price": 250000, "income_bonus": 3000, "description": "Яхта у причала. +3000₽/день.", "image_url": "AgACAgIAAxkBAAIBfmn3hNlqZXeSCAxLTetoN0kJMG4RAAKWGGsbaAW5SxNdXNthpgjFAQADAgADeQADOwQ"},
    {"id": "skyscraper", "name": "🏙 Небоскрёб", "price": 3000000, "income_bonus": 20000, "description": "Небоскрёб в центре города. +20 000₽/день.", "image_url": "AgACAgIAAxkBAAIOGGn80IpHo9UQDHb2EhlAp6cOqCp8AAItF2sb59XpS_EAAVDuV6ZpTwEAAwIAA3kAAzsE"},
]

SHOP_LEVELS = [
    {"id": "none", "name": "Нет магазина", "price": 0, "income_per_hour": 0},
    {"id": "stall", "name": "🛍 Лавка на рынке", "price": 5000, "income_per_hour": 100},
    {"id": "container", "name": "📦 Контейнер на Садоводе", "price": 15000, "income_per_hour": 300},
    {"id": "small_shop", "name": "🏬 Маленький магазин одежды", "price": 50000, "income_per_hour": 800},
    {"id": "store", "name": "🏪 Магазин в ТЦ", "price": 150000, "income_per_hour": 2000},
    {"id": "brand_shop", "name": "👔 Брендовый магазин одежды", "price": 500000, "income_per_hour": 5000},
    {"id": "boutique", "name": "👑 Бутик в центре", "price": 1500000, "income_per_hour": 15000},
]

TAXOPARK_LEVELS = [
    {"id": "none", "name": "Нет таксопарка", "price": 0, "slots": 0, "income_per_car": 0},
    {"id": "small", "name": "🚕 Маленький таксопарк", "price": 500000, "slots": 3, "income_per_car": 5000},
    {"id": "medium", "name": "🚖 Средний таксопарк", "price": 2000000, "slots": 7, "income_per_car": 8000},
    {"id": "large", "name": "🚗 Крупный таксопарк", "price": 10000000, "slots": 15, "income_per_car": 12000},
    {"id": "elite", "name": "👑 Элитный таксопарк", "price": 50000000, "slots": 30, "income_per_car": 20000},
]

CLIENT_TYPES = {
    "normal": {
        "max_rounds": 5,
        "phrases": {
            "greet": ["Здравствуйте! Ещё продаёте {item}? Какое состояние?", "Добрый день! {item} — ещё актуально? Интересует состояние."],
            "state_reaction": ["Понял, спасибо. А доставка есть?", "Хорошо, принял. Как насчёт доставки?"],
            "delivery_reaction": ["Понял, спасибо. А почему продаёте, если не секрет?", "Ясно, благодарю. С чем связана продажа?"],
            "reason_reaction": ["Понял, спасибо за честность. Я думаю, цена {price}₽ — нормально.", "Спасибо за информацию! Меня устраивает цена {price}₽."],
            "decline": ["Извините, я передумал. Удачи в продаже.", "Пока подумаю, не уверен."],
            "wait": ["Спасибо, я понял.", "Хорошо, спасибо за ответ."]
        },
        "persuasion_bonus": 0
    },
    "skeptic": {
        "max_rounds": 5,
        "phrases": {
            "greet": ["Здравствуйте! {item} за {price}₽? А почему так дорого?", "Добрый день! {item} — цена высоковата. Что с состоянием?"],
            "state_reaction": ["Хм, ну ладно. А доставка?", "Допустим. По доставке что?"],
            "delivery_reaction": ["Ясно. А почему продаёте? Что-то не так с товаром?", "Понял. Причина продажи какая?"],
            "reason_reaction": ["Ну хорошо, убедили. {price}₽ — беру.", "Ладно, звучит разумно. Забираю за {price}₽."],
            "decline": ["Нет, не убедили. Я пошёл.", "Дорого всё равно. Отказ."],
            "wait": ["Ну не знаю...", "Сомневаюсь я."]
        },
        "persuasion_bonus": 30
    },
    "trader": {
        "max_rounds": 3,
        "phrases": {
            "greet": ["Здравствуйте! {item} — {price}₽? Давайте {offer}₽.", "Привет! {item} за {price}₽? Я готов предложить {offer}₽."],
            "counter": ["Нет, всё равно дорого. {new_offer}₽?", "Я могу поднять до {new_offer}₽. Это предел."],
            "agree": ["Ладно, уговорил. {price}₽ беру.", "Хорошо, давай {price}₽."],
            "decline": ["Нет, не пойдёт. Удачи.", "Дорого, не буду брать. Пока."],
            "wait": ["Я думаю...", "Ну, не знаю."]
        },
        "persuasion_bonus": 0
    }
}

JOBS = [
    {"id": "flyers", "name": "📦 Расклейка объявлений", "duration": 60, "reward": 200, "emoji": "📦"},
    {"id": "delivery", "name": "🚗 Доставка заказов", "duration": 120, "reward": 500, "emoji": "🚗"},
    {"id": "freelance", "name": "💻 Фриланс (дизайн)", "duration": 300, "reward": 1200, "emoji": "💻"},
]

MARKET_EVENTS = [
    {"text": "📰 Хайп на джинсы!", "cat": "👖 Джинсы", "mult": 1.5},
    {"text": "📰 Куртки в цене!", "cat": "🧥 Куртки", "mult": 1.4},
    {"text": "📰 Кроссовки в тренде!", "cat": "👟 Кроссы", "mult": 1.5},
    {"text": "📰 Джинсы падают.", "cat": "👖 Джинсы", "mult": 0.6},
]

TRADING_ITEMS = {
    "👖 Джинсы": {"name": "Джинсы", "base_price": 500, "volatility": 0.15},
    "👕 Футболки": {"name": "Футболки", "base_price": 300, "volatility": 0.12},
    "🧥 Куртки": {"name": "Куртки", "base_price": 800, "volatility": 0.18},
    "👟 Кроссовки": {"name": "Кроссовки", "base_price": 600, "volatility": 0.20},
    "🧢 Кепки": {"name": "Кепки", "base_price": 200, "volatility": 0.10},
}

# ==================== ГЛОБАЛЬНЫЕ ХРАНИЛИЩА ====================
active_races = {}
active_chats = {}
published_items = {}
sold_items = {}
supplier_stock = {"items": [], "last_update": 0}
trading_prices = {}
auction_items = []
supply_drop = {}
side_jobs = {}
last_bot_message = {}
pending_messages = defaultdict(list)

async def send_msg(user_id, text, parse_mode="HTML", reply_markup=None):
    msg = await bot.send_message(user_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    last_bot_message[user_id] = msg.message_id
    return msg

# ==================== МОДЕЛИ PYDANTIC ДЛЯ API ====================
class PlayerAction(BaseModel):
    platform: str
    platform_id: int
    action: str
    data: Dict[str, Any] = {}

# ==================== БАЗА ДАННЫХ SQLITE ====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE,
            vk_id INTEGER UNIQUE,
            nickname TEXT DEFAULT 'Торгаш',
            shop_name TEXT DEFAULT 'Без названия',
            balance INTEGER DEFAULT 5000,
            day INTEGER DEFAULT 1,
            inventory TEXT DEFAULT '[]',
            car_collection TEXT DEFAULT '[]',
            current_car TEXT DEFAULT 'none',
            house TEXT DEFAULT 'room',
            shop_level TEXT DEFAULT 'none',
            taxopark TEXT DEFAULT '{"level":"none","cars":[]}',
            skin TEXT DEFAULT 'default',
            skin_inventory TEXT DEFAULT '["default"]',
            reputation_score INTEGER DEFAULT 0,
            total_sales INTEGER DEFAULT 0,
            total_profit INTEGER DEFAULT 0,
            total_earned INTEGER DEFAULT 0,
            items_sold INTEGER DEFAULT 0,
            market_demand TEXT DEFAULT '{"👖 Джинсы":1.0,"👕 Худи":1.0,"🧥 Куртки":1.0,"👟 Кроссы":1.0,"🎒 Аксессуары":1.0}',
            current_event TEXT,
            stat_earned_today INTEGER DEFAULT 0,
            stat_sold_today INTEGER DEFAULT 0,
            trading_portfolio TEXT DEFAULT '{}',
            trading_invested INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS friends (
            player_id INTEGER, friend_id INTEGER,
            FOREIGN KEY (player_id) REFERENCES players(id),
            PRIMARY KEY (player_id, friend_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS races (
            id TEXT PRIMARY KEY, creator_id INTEGER, opponent_id INTEGER,
            creator_car TEXT, opponent_car TEXT, bet INTEGER, prize_pool INTEGER,
            phase INTEGER DEFAULT 0, creator_score INTEGER DEFAULT 0, opponent_score INTEGER DEFAULT 0,
            creator_actions TEXT DEFAULT '[]', opponent_actions TEXT DEFAULT '[]',
            status TEXT DEFAULT 'wait', winner_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            player_id INTEGER PRIMARY KEY, invited TEXT DEFAULT '[]', bonus_claimed INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS skins (
            player_id INTEGER, skin_id TEXT, equipped INTEGER DEFAULT 0,
            PRIMARY KEY (player_id, skin_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auction (
            id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id INTEGER,
            item_name TEXT, item_data TEXT, start_price INTEGER, current_bid INTEGER,
            bidder_id INTEGER, end_time INTEGER, active INTEGER DEFAULT 1
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning (
            player_id INTEGER PRIMARY KEY, completed TEXT DEFAULT '[]'
        )
    ''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_or_create_player(platform: str, platform_id: int) -> int:
    conn = get_db()
    cursor = conn.cursor()
    field = 'tg_id' if platform == 'tg' else 'vk_id'
    cursor.execute(f"SELECT id FROM players WHERE {field} = ?", (platform_id,))
    row = cursor.fetchone()
    if row:
        conn.close()
        return row['id']
    cursor.execute(f"INSERT INTO players ({field}, nickname, shop_name) VALUES (?, ?, ?)",
                   (platform_id, f"Игрок_{platform_id}", "Моя лавка"))
    conn.commit()
    player_id = cursor.lastrowid
    cursor.execute("INSERT INTO referrals (player_id, invited) VALUES (?, '[]')", (player_id,))
    cursor.execute("INSERT INTO learning (player_id, completed) VALUES (?, '[]')", (player_id,))
    cursor.execute("INSERT INTO skins (player_id, skin_id, equipped) VALUES (?, 'default', 1)", (player_id,))
    conn.commit()
    conn.close()
    return player_id

def get_player_data(player_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        data = dict(row)
        for field in ['inventory', 'car_collection', 'taxopark', 'market_demand', 'skin_inventory', 'trading_portfolio']:
            if field in data and data[field]:
                try:
                    data[field] = json.loads(data[field])
                except:
                    pass
        return data
    return None

def update_player_data(player_id: int, data: Dict[str, Any]):
    conn = get_db()
    cursor = conn.cursor()
    fields = []
    values = []
    for key, value in data.items():
        fields.append(f"{key} = ?")
        if isinstance(value, (list, dict)):
            values.append(json.dumps(value, ensure_ascii=False))
        else:
            values.append(value)
    values.append(player_id)
    query = f"UPDATE players SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    conn.close()

def get_referral_data(player_id: int) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT invited, bonus_claimed FROM referrals WHERE player_id = ?", (player_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"invited": json.loads(row['invited']) if row['invited'] else [], "bonus_claimed": bool(row['bonus_claimed'])}
    return {"invited": [], "bonus_claimed": False}

def update_referral_data(player_id: int, data: Dict[str, Any]):
    conn = get_db()
    cursor = conn.cursor()
    invited = json.dumps(data.get("invited", []))
    bonus_claimed = 1 if data.get("bonus_claimed", False) else 0
    cursor.execute("UPDATE referrals SET invited = ?, bonus_claimed = ? WHERE player_id = ?", (invited, bonus_claimed, player_id))
    conn.commit()
    conn.close()

def get_skins(player_id: int) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT skin_id, equipped FROM skins WHERE player_id = ?", (player_id,))
    rows = cursor.fetchall()
    conn.close()
    skins = []
    for row in rows:
        skin_info = next((s for s in SKINS if s["id"] == row['skin_id']), None)
        if skin_info:
            skins.append({"id": row['skin_id'], "name": skin_info["name"], "emoji": skin_info["emoji"], "equipped": bool(row['equipped'])})
    return skins

def add_skin(player_id: int, skin_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO skins (player_id, skin_id, equipped) VALUES (?, ?, 0)", (player_id, skin_id))
    conn.commit()
    conn.close()

def equip_skin(player_id: int, skin_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE skins SET equipped = 0 WHERE player_id = ?", (player_id,))
    cursor.execute("UPDATE skins SET equipped = 1 WHERE player_id = ? AND skin_id = ?", (player_id, skin_id))
    update_player_data(player_id, {"skin": skin_id})
    conn.commit()
    conn.close()

def get_learning_data(player_id: int) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT completed FROM learning WHERE player_id = ?", (player_id,))
    row = cursor.fetchone()
    conn.close()
    return {"completed": json.loads(row['completed']) if row and row['completed'] else []}

def update_learning_data(player_id: int, data: Dict[str, Any]):
    conn = get_db()
    cursor = conn.cursor()
    completed = json.dumps(data.get("completed", []))
    cursor.execute("UPDATE learning SET completed = ? WHERE player_id = ?", (completed, player_id))
    conn.commit()
    conn.close()

def get_friends(player_id: int) -> List[int]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT friend_id FROM friends WHERE player_id = ?", (player_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row['friend_id'] for row in rows]

def update_friends(player_id: int, friends: List[int]):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM friends WHERE player_id = ?", (player_id,))
    for friend_id in friends:
        cursor.execute("INSERT INTO friends (player_id, friend_id) VALUES (?, ?)", (player_id, friend_id))
    conn.commit()
    conn.close()

def find_user_by_nickname(nickname: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nickname FROM players WHERE nickname = ?", (nickname,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row['id'], "nickname": row['nickname']}
    return None

# ==================== ГЕНЕРАЦИЯ ТОВАРОВ У ПОСТАВЩИКОВ ====================
def generate_supplier_items():
    items = []
    for _ in range(random.randint(6, 10)):
        rarities = list(SUPPLIER_ITEM_RARITIES.keys())
        weights = [SUPPLIER_ITEM_RARITIES[r]["chance"] for r in rarities]
        rarity = random.choices(rarities, weights=weights, k=1)[0]
        rd = SUPPLIER_ITEM_RARITIES[rarity]
        base = random.choice(BASE_ITEMS)
        mp = int(base["base_price"] * random.uniform(rd["price_mult_min"], rd["price_mult_max"]))
        bp = int(mp * random.uniform(0.6, 0.85))
        items.append({
            "id": random.randint(10000, 99999),
            "name": f"{rd['color']} {base['cat']} {base['name']}",
            "cat": base["cat"],
            "buy_price": bp,
            "market_price": mp,
            "rarity": rarity,
            "rarity_color": rd["color"],
            "end_time": time_module.time() + random.randint(300, 900)
        })
    supplier_stock["items"] = items
    supplier_stock["last_update"] = time_module.time()

def check_supplier_update():
    if time_module.time() - supplier_stock.get("last_update", 0) >= 300 or not supplier_stock.get("items"):
        generate_supplier_items()
        return True
    if supplier_stock.get("items"):
        supplier_stock["items"] = [i for i in supplier_stock["items"] if i["end_time"] > time_module.time()]
    return False

def get_supplier_items():
    check_supplier_update()
    return supplier_stock.get("items", [])

# ==================== ТРЕЙДИНГ ====================
def init_trading():
    if not trading_prices:
        for cat, data in TRADING_ITEMS.items():
            trading_prices[cat] = {
                "price": data["base_price"],
                "trend": random.uniform(-0.05, 0.05),
                "history": [data["base_price"]] * 5
            }

def update_trading():
    for cat, data in trading_prices.items():
        item = TRADING_ITEMS[cat]
        change = random.uniform(-item["volatility"], item["volatility"])
        data["trend"] += random.uniform(-0.02, 0.02)
        data["trend"] = max(-0.1, min(0.1, data["trend"]))
        new_price = int(data["price"] * (1 + change + data["trend"]))
        new_price = max(item["base_price"] // 3, new_price)
        data["price"] = new_price
        data["history"].append(new_price)
        if len(data["history"]) > 10:
            data["history"].pop(0)

def get_trader(player_id: int):
    player = get_player_data(player_id)
    if not player:
        return {"portfolio": {}, "invested": 0}
    portfolio = player.get("trading_portfolio", {})
    invested = player.get("trading_invested", 0)
    return {"portfolio": portfolio, "invested": invested}

def save_trader(player_id: int, portfolio: dict, invested: int):
    update_player_data(player_id, {"trading_portfolio": portfolio, "trading_invested": invested})

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ИГРЫ ====================
def get_display_name(player_data: Dict[str, Any]) -> str:
    nick = player_data.get("nickname")
    if nick:
        return nick
    tg_id = player_data.get("tg_id")
    vk_id = player_data.get("vk_id")
    if tg_id:
        return f"ID:{tg_id}"
    return f"ID:{vk_id}"

def get_car_bonus(car_id: str) -> int:
    car = next((c for c in CARS if c["id"] == car_id), None)
    return car["speed_bonus"] if car else 0

def calculate_race_score(car_id: str, action: str, phase: int) -> Tuple[int, str]:
    speed = get_car_bonus(car_id)
    base = 50 + speed
    luck = random.randint(-15, 15)
    if action == "boost":
        base *= 1.3
        if random.random() < 0.2:
            base *= 0.5
            return int(base + luck), "⚠️ Двигатель перегрет!"
    elif action == "nitro":
        base *= 1.5
        return int(base + luck), "🔥 НИТРО! +50%"
    else:
        base *= 1.1
        return int(base + luck), "🛡 Ровный ход"
    return int(base + luck), "✅"

def rate_description(desc: str) -> int:
    score = 3
    if len(desc) >= 30:
        score += 1
    if len(desc) >= 80:
        score += 1
    keywords = ["состояние", "размер", "цвет", "бренд", "качество", "материал", "новый"]
    score += min(3, sum(1 for w in keywords if w in desc.lower()))
    return min(10, max(1, score))

def get_quality_bonus(quality: int) -> Dict[str, Any]:
    if quality >= 9:
        return {"name": "🔥 Легендарное", "buyers_bonus": 3}
    elif quality >= 7:
        return {"name": "⭐ Отличное", "buyers_bonus": 2}
    elif quality >= 5:
        return {"name": "👍 Хорошее", "buyers_bonus": 1}
    return {"name": "👌 Обычное", "buyers_bonus": 0}

def daily_event():
    if random.random() < 0.6:
        return random.choice(MARKET_EVENTS)
    return None

def apply_event(player: Dict[str, Any], event: Dict[str, Any]):
    if event and event.get("cat"):
        market_demand = player.get("market_demand", {})
        if event["cat"] in market_demand:
            market_demand[event["cat"]] = max(0.3, min(3.0, market_demand[event["cat"]] * event["mult"]))
            update_player_data(player["id"], {"market_demand": market_demand})

def fmt_demand(player: Dict[str, Any]) -> str:
    market_demand = player.get("market_demand", {})
    lines = []
    for cat, mult in market_demand.items():
        if mult >= 1.5:
            emoji = "🔥"
        elif mult >= 1.2:
            emoji = "📈"
        elif mult >= 0.8:
            emoji = "➡️"
        elif mult >= 0.5:
            emoji = "📉"
        else:
            emoji = "💀"
        lines.append(f"{emoji} {cat}: x{mult:.1f}")
    return "\n".join(lines)

def get_avito_rating(sales: int) -> str:
    if sales == 0: return "⭐ Новый продавец"
    elif sales < 3: return "⭐ 1.0"
    elif sales < 5: return "⭐⭐ 2.0"
    elif sales < 10: return "⭐⭐⭐ 3.0"
    elif sales < 25: return "⭐⭐⭐⭐ 4.0"
    elif sales < 50: return "⭐⭐⭐⭐ 4.5"
    elif sales < 100: return "⭐⭐⭐⭐⭐ 4.8"
    elif sales < 250: return "👑 ⭐⭐⭐⭐⭐ 5.0"
    else: return "💎 👑 ⭐⭐⭐⭐⭐ 5.0"

def get_rep_level(sales: int) -> str:
    if sales == 0: return "🆕 Новичок"
    elif sales < 5: return "🔰 Начинающий"
    elif sales < 15: return "⭐ Проверенный"
    elif sales < 50: return "🏅 Надёжный"
    elif sales < 100: return "👑 Профессионал"
    elif sales < 250: return "💎 Легенда"
    else: return "🌟 Бог Авито"

def collect_income(player: Dict[str, Any]) -> int:
    house_id = player.get("house", "room")
    house = next((h for h in HOUSES if h["id"] == house_id), HOUSES[0])
    house_income = house["income_bonus"]
    shop_level_id = player.get("shop_level", "none")
    shop_level = next((s for s in SHOP_LEVELS if s["id"] == shop_level_id), SHOP_LEVELS[0])
    shop_income = shop_level["income_per_hour"]
    car_id = player.get("current_car", "none")
    car = next((c for c in CARS if c["id"] == car_id), None)
    car_income = car["income_per_hour"] if car and car["income_per_hour"] > 0 else 0
    taxopark_data = player.get("taxopark", {"level": "none", "cars": []})
    taxopark_level = next((l for l in TAXOPARK_LEVELS if l["id"] == taxopark_data.get("level")), TAXOPARK_LEVELS[0])
    taxopark_income = taxopark_level["income_per_car"] * len(taxopark_data.get("cars", []))
    total_income = house_income + shop_income + car_income + taxopark_income
    if total_income > 0:
        balance = player.get("balance", 0)
        update_player_data(player["id"], {"balance": balance + total_income})
    return total_income

async def complete_sale_action(player_id: int, player: Dict[str, Any], chat: Dict[str, Any], buyer_id: int):
    inventory = player.get("inventory", [])
    sold_item = None
    for i, inv in enumerate(inventory):
        if chat["item"] in inv["name"] or inv["name"] in chat["item"]:
            sold_item = inventory.pop(i)
            break
    if not sold_item:
        return {"success": False, "message": "Товар не найден", "sold": False}
    final_price = chat["offer"]
    profit = final_price - sold_item["buy_price"]
    balance = player.get("balance", 0)
    total_sales = player.get("total_sales", 0) + 1
    total_profit = player.get("total_profit", 0) + profit
    update_player_data(player_id, {
        "balance": balance + final_price, "inventory": inventory,
        "total_sales": total_sales, "total_profit": total_profit,
        "total_earned": player.get("total_earned", 0) + profit, "items_sold": total_sales
    })
    chat["finished"] = True
    if player_id in published_items:
        del published_items[player_id]
    return {
        "success": True,
        "message": f"🎉 ПРОДАНО! Получено {final_price}₽, прибыль {profit}₽",
        "sold": True, "profit": profit, "final_price": final_price, "balance": balance + final_price
    }

async def finish_job_async(player_id: int, job_idx: int):
    await asyncio.sleep(JOBS[job_idx]["duration"])
    if player_id in side_jobs and not side_jobs[player_id].get("done", True):
        side_jobs[player_id]["done"] = True
        player = get_player_data(player_id)
        if player:
            reward = JOBS[job_idx]["reward"]
            update_player_data(player_id, {"balance": player.get("balance", 0) + reward})

# ==================== FASTAPI ЭНДПОИНТЫ ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    generate_supplier_items()
    init_trading()
    asyncio.create_task(update_trading_loop())
    yield

app = FastAPI(title="Resell Tycoon API", lifespan=lifespan)

async def update_trading_loop():
    while True:
        await asyncio.sleep(60)
        update_trading()

@app.get("/")
async def root():
    return {"message": "Resell Tycoon API", "status": "running", "version": "3.0"}

@app.get("/player/{platform}/{platform_id}")
async def get_player_info(platform: str, platform_id: int):
    player_id = get_or_create_player(platform, platform_id)
    player = get_player_data(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player

@app.post("/api/action")
async def handle_action(action: PlayerAction):
    player_id = get_or_create_player(action.platform, action.platform_id)
    player = get_player_data(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # ---------- БАЛАНС И СТАТЫ ----------
    if action.action == "get_balance":
        return {"success": True, "balance": player.get("balance", 0)}
    
    elif action.action == "get_stats":
        return {
            "success": True,
            "stats": {
                "balance": player.get("balance", 0),
                "day": player.get("day", 1),
                "inventory_count": len(player.get("inventory", [])),
                "items_sold": player.get("total_sales", 0),
                "total_earned": player.get("total_earned", 0),
                "nickname": player.get("nickname"),
                "shop_name": player.get("shop_name"),
                "total_profit": player.get("total_profit", 0),
                "reputation_score": player.get("reputation_score", 0),
                "house": player.get("house", "room"),
                "shop_level": player.get("shop_level", "none"),
                "current_car": player.get("current_car", "none"),
                "car_collection_count": len(player.get("car_collection", []))
            }
        }
    
    elif action.action == "get_shop_name":
        return {"success": True, "shop_name": player.get("shop_name", "Без названия")}
    
    elif action.action == "set_shop_name":
        name = action.data.get("name", "")
        if len(name) < 2:
            return {"success": False, "message": "Минимум 2 символа"}
        if len(name) > 30:
            return {"success": False, "message": "Максимум 30 символов"}
        update_player_data(player_id, {"shop_name": name})
        return {"success": True, "message": f"✅ Магазин: {name}", "shop_name": name}
    
    elif action.action == "set_nickname":
        nickname = action.data.get("nickname", "")
        if len(nickname) < 2:
            return {"success": False, "message": "Минимум 2 символа"}
        if len(nickname) > 20:
            return {"success": False, "message": "Максимум 20 символов"}
        update_player_data(player_id, {"nickname": nickname})
        return {"success": True, "message": f"✅ Никнейм: {nickname}", "nickname": nickname}
    
    elif action.action == "next_day":
        income = collect_income(player)
        day = player.get("day", 1)
        new_day = day + 1
        market_demand = player.get("market_demand", {})
        for cat in CATEGORIES:
            if cat in market_demand:
                market_demand[cat] = max(0.3, min(3.0, market_demand[cat] * random.uniform(0.85, 1.15)))
        event = daily_event()
        if event and event.get("cat") and event["cat"] in market_demand:
            market_demand[event["cat"]] = max(0.3, min(3.0, market_demand[event["cat"]] * event["mult"]))
        inventory = player.get("inventory", [])
        if inventory and random.random() < 0.2:
            for item in inventory:
                item["market_price"] = int(item["market_price"] * random.uniform(0.7, 0.95))
        update_player_data(player_id, {
            "balance": player.get("balance", 0) + income,
            "day": new_day,
            "market_demand": market_demand,
            "inventory": inventory,
            "current_event": event
        })
        return {
            "success": True,
            "message": f"День {new_day}, доход: {income}₽",
            "day": new_day,
            "balance": player.get("balance", 0) + income,
            "income": income
        }
    
    elif action.action == "collect_income":
        income = collect_income(player)
        return {"success": True, "message": f"✅ Собрано {income}₽", "income": income, "balance": player.get("balance", 0)}
    
    elif action.action == "get_demand":
        market_demand = player.get("market_demand", {})
        return {"success": True, "demand": market_demand, "formatted": fmt_demand(player)}
    
    # ---------- ПОСТАВЩИКИ ----------
    elif action.action == "get_suppliers":
        items = get_supplier_items()
        return {"success": True, "suppliers": items}
    
    elif action.action == "buy_from_supplier":
        item_id = action.data.get("item_id")
        suppliers = get_supplier_items()
        item = next((i for i in suppliers if i["id"] == item_id), None)
        if not item:
            return {"success": False, "message": "Товар уже купили или время истекло!"}
        balance = player.get("balance", 0)
        if balance < item["buy_price"]:
            return {"success": False, "message": f"❌ Недостаточно денег! Нужно {item['buy_price']}₽"}
        inventory = player.get("inventory", [])
        inventory.append({
            "name": item["name"],
            "cat": item["cat"],
            "buy_price": item["buy_price"],
            "market_price": item["market_price"]
        })
        update_player_data(player_id, {"balance": balance - item["buy_price"], "inventory": inventory})
        supplier_stock["items"] = [i for i in supplier_stock.get("items", []) if i["id"] != item_id]
        return {"success": True, "message": f"✅ Куплен {item['name']} за {item['buy_price']}₽", "balance": balance - item["buy_price"]}
    
    # ---------- ИНВЕНТАРЬ ----------
    elif action.action == "get_inventory":
        return {"success": True, "inventory": player.get("inventory", [])}
    
    elif action.action == "publish_item":
        item_idx = action.data.get("item_idx")
        description = action.data.get("description", "")
        inventory = player.get("inventory", [])
        if item_idx >= len(inventory):
            return {"success": False, "message": "Товар не найден"}
        item = inventory[item_idx]
        quality = rate_description(description)
        quality_bonus = get_quality_bonus(quality)
        published_items[player_id] = {
            "item": item.copy(),
            "description": description,
            "quality": quality,
            "created_at": time_module.time()
        }
        return {
            "success": True,
            "message": f"📢 ОПУБЛИКОВАНО!\n📦 {item['name']}\n💰 {item['market_price']}₽\n📝 Качество: {quality_bonus['name']} ({quality}/10)\n⏳ Жди покупателей!"
        }
    
    elif action.action == "get_published_item":
        pub = published_items.get(player_id)
        if not pub:
            return {"success": False, "message": "Нет активных объявлений"}
        return {"success": True, "item": pub["item"], "quality": pub.get("quality", 0)}
    
    elif action.action == "unpublish_item":
        if player_id in published_items:
            del published_items[player_id]
        return {"success": True, "message": "Объявление снято с публикации"}
    
    # ---------- ПОКУПАТЕЛИ (ЧАТЫ) ----------
    elif action.action == "get_chats":
        chats = []
        for key, chat in active_chats.items():
            if chat.get("user_id") == player_id and not chat.get("finished"):
                chats.append({
                    "buyer_id": chat.get("buyer_id"),
                    "item": chat.get("item"),
                    "offer": chat.get("offer"),
                    "round": chat.get("round", 0),
                    "max_rounds": chat.get("max_rounds", 0),
                    "client_type": chat.get("client_type")
                })
        return {"success": True, "chats": chats}
    
    elif action.action == "start_chat":
        buyer_id = action.data.get("buyer_id")
        chat_key = f"{player_id}_{buyer_id}"
        if chat_key in active_chats and not active_chats[chat_key].get("finished"):
            return {"success": True, "message": "Чат уже открыт"}
        pub = published_items.get(player_id)
        if not pub:
            return {"success": False, "message": "Нет активных объявлений"}
        client_type = random.choices(["normal", "skeptic", "trader"], weights=[60, 25, 15], k=1)[0]
        item = pub["item"]
        price = item["market_price"]
        if client_type == "trader":
            discount = random.uniform(0.7, 0.9)
            offer = int(price * discount)
            offer = (offer // 100) * 100 + 99
            if offer < 100: offer = price // 2
        else:
            offer = price
        client = CLIENT_TYPES[client_type]
        msg = random.choice(client["phrases"]["greet"]).format(item=item["name"], price=price, offer=offer)
        active_chats[chat_key] = {
            "user_id": player_id, "buyer_id": buyer_id, "client_type": client_type,
            "item": item["name"], "price": price, "offer": offer,
            "round": 1, "max_rounds": client["max_rounds"], "finished": False,
            "phase": "greet", "history": [{"role": "assistant", "content": msg}]
        }
        return {"success": True, "message": msg, "buyer_id": buyer_id, "offer": offer}
    
    elif action.action == "send_chat_message":
        buyer_id = action.data.get("buyer_id")
        text = action.data.get("text", "")
        chat_key = f"{player_id}_{buyer_id}"
        if chat_key not in active_chats:
            return {"success": False, "message": "Чат не найден"}
        chat = active_chats[chat_key]
        if chat.get("finished"):
            return {"success": False, "message": "Чат уже завершён"}
        chat["round"] += 1
        client_type = chat["client_type"]
        client = CLIENT_TYPES[client_type]
        phrases = client["phrases"]
        price = chat["price"]
        offer = chat["offer"]
        if text.lower() == "согласен":
            return await complete_sale_action(player_id, player, chat, buyer_id)
        if chat["round"] >= chat["max_rounds"]:
            if client_type == "trader":
                success = random.random() < 0.5 if offer >= price * 0.7 else False
            else:
                total_len = sum(len(msg.get("content", "")) for msg in chat.get("history", []) if msg.get("role") == "user")
                quality = min(100, total_len / 2)
                bonus = client.get("persuasion_bonus", 0)
                success_chance = quality - bonus
                success = random.randint(1, 100) <= success_chance
            if success:
                final_price = offer if client_type == "trader" else price
                ai_msg = random.choice(phrases.get("agree", ["Ладно, беру!"])).replace("{price}", str(final_price))
                inventory = player.get("inventory", [])
                sold_item = None
                for i, inv in enumerate(inventory):
                    if chat["item"] in inv["name"] or inv["name"] in chat["item"]:
                        sold_item = inventory.pop(i)
                        break
                if sold_item:
                    profit = final_price - sold_item["buy_price"]
                    balance = player.get("balance", 0)
                    total_sales = player.get("total_sales", 0) + 1
                    total_profit = player.get("total_profit", 0) + profit
                    update_player_data(player_id, {
                        "balance": balance + final_price, "inventory": inventory,
                        "total_sales": total_sales, "total_profit": total_profit,
                        "total_earned": player.get("total_earned", 0) + profit, "items_sold": total_sales
                    })
                    chat["finished"] = True
                    if player_id in published_items:
                        del published_items[player_id]
                    return {
                        "success": True, "message": ai_msg, "sold": True,
                        "profit": profit, "final_price": final_price, "balance": balance + final_price
                    }
            ai_msg = random.choice(phrases.get("decline", ["Нет, не убедили."]))
            chat["finished"] = True
            return {"success": True, "message": ai_msg, "sold": False}
        # Обычный диалог
        if client_type == "normal":
            if chat["round"] == 2:
                ai_msg = random.choice(phrases["state_reaction"])
            elif chat["round"] == 3:
                ai_msg = random.choice(phrases["delivery_reaction"])
            elif chat["round"] == 4:
                ai_msg = random.choice(phrases["reason_reaction"]).replace("{price}", str(price))
            else:
                ai_msg = random.choice(phrases["wait"])
        elif client_type == "skeptic":
            if chat["round"] == 2:
                ai_msg = random.choice(phrases["state_reaction"])
            elif chat["round"] == 3:
                ai_msg = random.choice(phrases["delivery_reaction"])
            elif chat["round"] == 4:
                ai_msg = random.choice(phrases["reason_reaction"]).replace("{price}", str(price))
            else:
                ai_msg = random.choice(phrases["wait"])
        else:
            seller_prices = re.findall(r'(\d+)', text)
            if seller_prices:
                seller_price = int(seller_prices[0])
                if seller_price < price:
                    new_offer = max(offer, int(seller_price * 0.9))
                    new_offer = (new_offer // 100) * 100 + 99
                    ai_msg = random.choice(phrases["counter"]).format(new_offer=new_offer)
                    chat["offer"] = new_offer
                else:
                    ai_msg = random.choice(phrases["wait"])
            else:
                ai_msg = random.choice(phrases["wait"])
        chat["history"].append({"role": "assistant", "content": ai_msg})
        return {"success": True, "message": ai_msg, "sold": False, "offer": chat["offer"]}
    
    # ---------- АВТОМОБИЛИ ----------
    elif action.action == "get_cars":
        return {"success": True, "cars": CARS}
    
    elif action.action == "buy_car":
        car_id = action.data.get("car_id")
        car = next((c for c in CARS if c["id"] == car_id), None)
        if not car:
            return {"success": False, "message": "Машина не найдена"}
        balance = player.get("balance", 0)
        if balance < car["price"]:
            return {"success": False, "message": f"Недостаточно денег! Нужно {car['price']}₽"}
        car_collection = player.get("car_collection", [])
        car_collection.append(car_id)
        new_balance = balance - car["price"]
        update_player_data(player_id, {"balance": new_balance, "car_collection": car_collection})
        if len(car_collection) == 1 or player.get("current_car") == "none":
            update_player_data(player_id, {"current_car": car_id})
        return {"success": True, "message": f"✅ {car['name']} куплена!", "balance": new_balance}
    
    elif action.action == "get_car_collection":
        car_collection = player.get("car_collection", [])
        cars_data = []
        for car_id in car_collection:
            car = next((c for c in CARS if c["id"] == car_id), None)
            if car:
                cars_data.append({"id": car_id, "name": car["name"], "is_current": car_id == player.get("current_car", "none")})
        return {"success": True, "cars": cars_data}
    
    elif action.action == "set_current_car":
        car_id = action.data.get("car_id")
        car_collection = player.get("car_collection", [])
        if car_id not in car_collection:
            return {"success": False, "message": "У вас нет этой машины!"}
        update_player_data(player_id, {"current_car": car_id})
        car = next((c for c in CARS if c["id"] == car_id), None)
        return {"success": True, "message": f"✅ {car['name'] if car else car_id} теперь ваша текущая машина!"}
    
    elif action.action == "get_current_car":
        current_car = player.get("current_car", "none")
        car = next((c for c in CARS if c["id"] == current_car), None)
        return {"success": True, "car": car, "car_id": current_car}
    
    # ---------- НЕДВИЖИМОСТЬ ----------
    elif action.action == "get_houses":
        return {"success": True, "houses": HOUSES}
    
    elif action.action == "buy_house":
        house_id = action.data.get("house_id")
        house = next((h for h in HOUSES if h["id"] == house_id), None)
        if not house:
            return {"success": False, "message": "Дом не найден"}
        if player.get("house") == house_id:
            return {"success": False, "message": "У вас уже есть этот дом"}
        balance = player.get("balance", 0)
        if balance < house["price"]:
            return {"success": False, "message": f"Недостаточно денег! Нужно {house['price']}₽"}
        update_player_data(player_id, {"balance": balance - house["price"], "house": house_id})
        return {"success": True, "message": f"✅ {house['name']} куплен!", "balance": balance - house["price"]}
    
    elif action.action == "get_current_house":
        house_id = player.get("house", "room")
        house = next((h for h in HOUSES if h["id"] == house_id), HOUSES[0])
        return {"success": True, "house": house}
    
    # ---------- МАГАЗИНЫ ----------
    elif action.action == "get_shops":
        return {"success": True, "shops": SHOP_LEVELS}
    
    elif action.action == "get_current_shop":
        shop_level_id = player.get("shop_level", "none")
        shop = next((s for s in SHOP_LEVELS if s["id"] == shop_level_id), SHOP_LEVELS[0])
        return {"success": True, "shop": shop}
    
    elif action.action == "buy_shop":
        shop_id = action.data.get("shop_id")
        shop = next((s for s in SHOP_LEVELS if s["id"] == shop_id), None)
        if not shop:
            return {"success": False, "message": "Магазин не найден"}
        if player.get("shop_level") == shop_id:
            return {"success": False, "message": "У вас уже есть этот магазин"}
        balance = player.get("balance", 0)
        if balance < shop["price"]:
            return {"success": False, "message": f"Недостаточно денег! Нужно {shop['price']}₽"}
        update_player_data(player_id, {"balance": balance - shop["price"], "shop_level": shop_id})
        return {"success": True, "message": f"✅ {shop['name']} куплен!", "balance": balance - shop["price"]}
    
    # ---------- ТАКСОПАРК ----------
    elif action.action == "get_taxopark_levels":
        return {"success": True, "levels": TAXOPARK_LEVELS}
    
    elif action.action == "get_taxopark":
        taxopark = player.get("taxopark", {"level": "none", "cars": []})
        level = next((l for l in TAXOPARK_LEVELS if l["id"] == taxopark.get("level")), TAXOPARK_LEVELS[0])
        return {"success": True, "taxopark": taxopark, "level_info": level}
    
    elif action.action == "buy_taxopark":
        level_id = action.data.get("level_id")
        level = next((l for l in TAXOPARK_LEVELS if l["id"] == level_id), None)
        if not level:
            return {"success": False, "message": "Уровень не найден"}
        taxopark = player.get("taxopark", {"level": "none", "cars": []})
        if taxopark.get("level") == level_id:
            return {"success": False, "message": "У вас уже есть этот таксопарк"}
        balance = player.get("balance", 0)
        if balance < level["price"]:
            return {"success": False, "message": f"Недостаточно денег! Нужно {level['price']}₽"}
        update_player_data(player_id, {"balance": balance - level["price"], "taxopark": {"level": level_id, "cars": taxopark.get("cars", [])}})
        return {"success": True, "message": f"✅ {level['name']} куплен!", "balance": balance - level["price"]}
    
    elif action.action == "add_car_to_taxopark":
        car_id = action.data.get("car_id")
        taxopark = player.get("taxopark", {"level": "none", "cars": []})
        level = next((l for l in TAXOPARK_LEVELS if l["id"] == taxopark.get("level")), TAXOPARK_LEVELS[0])
        if level["slots"] == 0:
            return {"success": False, "message": "Купите таксопарк сначала!"}
        if len(taxopark.get("cars", [])) >= level["slots"]:
            return {"success": False, "message": f"Нет мест! Максимум {level['slots']} авто."}
        car_collection = player.get("car_collection", [])
        total_owned = car_collection.count(car_id)
        in_park = taxopark.get("cars", []).count(car_id)
        if in_park >= total_owned:
            return {"success": False, "message": "Купите ещё такую машину в автосалоне!"}
        if level["id"] == "elite":
            car = next((c for c in CARS if c["id"] == car_id), None)
            if car and car["price"] < 500000:
                return {"success": False, "message": "Элитный таксопарк — только премиум-авто (от 500 000₽)!"}
        cars = taxopark.get("cars", [])
        cars.append(car_id)
        update_player_data(player_id, {"taxopark": {"level": taxopark.get("level"), "cars": cars}})
        return {"success": True, "message": "✅ Машина добавлена в таксопарк!"}
    
    elif action.action == "remove_car_from_taxopark":
        car_id = action.data.get("car_id")
        taxopark = player.get("taxopark", {"level": "none", "cars": []})
        cars = taxopark.get("cars", [])
        if car_id not in cars:
            return {"success": False, "message": "Этой машины нет в таксопарке"}
        cars.remove(car_id)
        update_player_data(player_id, {"taxopark": {"level": taxopark.get("level"), "cars": cars}})
        return {"success": True, "message": "✅ Машина убрана из таксопарка"}
    
    # ---------- СКИНЫ ----------
    elif action.action == "get_skins":
        return {"success": True, "skins": SKINS}
    
    elif action.action == "get_player_skins":
        player_skins = get_skins(player_id)
        current_skin = player.get("skin", "default")
        return {"success": True, "skins": player_skins, "current": current_skin}
    
    elif action.action == "buy_skin":
        skin_id = action.data.get("skin_id")
        skin = next((s for s in SKINS if s["id"] == skin_id), None)
        if not skin:
            return {"success": False, "message": "Скин не найден"}
        if player.get("skin") == skin_id:
            return {"success": False, "message": "Уже надет!"}
        if skin.get("limited"):
            count = sum(1 for s in get_skins(player_id) if s["id"] == skin_id)
            if count >= skin["max_count"]:
                return {"success": False, "message": f"Лимит исчерпан! ({skin['max_count']} шт.)"}
        if skin.get("sales_required", 0) > 0:
            total_sales = player.get("total_sales", 0)
            if total_sales < skin["sales_required"]:
                return {"success": False, "message": f"Нужно {skin['sales_required']} продаж! (у тебя {total_sales})"}
        balance = player.get("balance", 0)
        if skin["price"] > 0 and balance < skin["price"]:
            return {"success": False, "message": f"Недостаточно! Нужно {skin['price']}₽"}
        if skin["price"] > 0:
            update_player_data(player_id, {"balance": balance - skin["price"]})
        add_skin(player_id, skin_id)
        equip_skin(player_id, skin_id)
        return {"success": True, "message": f"✅ {skin['name']} куплен и надет!", "balance": balance - skin["price"] if skin["price"] > 0 else balance}
    
    elif action.action == "equip_skin":
        skin_id = action.data.get("skin_id")
        player_skins = get_skins(player_id)
        if not any(s["id"] == skin_id for s in player_skins):
            return {"success": False, "message": "У вас нет этого скина"}
        equip_skin(player_id, skin_id)
        return {"success": True, "message": "✅ Скин надет!"}
    
    # ---------- РЕПУТАЦИЯ ----------
    elif action.action == "get_reputation":
        total_sales = player.get("total_sales", 0)
        total_profit = player.get("total_profit", 0)
        return {
            "success": True,
            "total_sales": total_sales,
            "total_profit": total_profit,
            "rating": get_avito_rating(total_sales),
            "level": get_rep_level(total_sales)
        }
    
    # ---------- ПОДРАБОТКИ ----------
    elif action.action == "get_jobs":
        return {"success": True, "jobs": JOBS}
    
    elif action.action == "start_job":
        job_idx = action.data.get("job_idx")
        if job_idx is None or job_idx >= len(JOBS):
            return {"success": False, "message": "Работа не найдена"}
        if player_id in side_jobs and not side_jobs[player_id].get("done", True):
            return {"success": False, "message": "Вы уже работаете!"}
        side_jobs[player_id] = {"job_type": job_idx, "start_time": time_module.time(), "done": False}
        asyncio.create_task(finish_job_async(player_id, job_idx))
        job = JOBS[job_idx]
        return {"success": True, "message": f"💼 {job['emoji']} {job['name']} начата! Через {job['duration']} сек. получите {job['reward']}₽", "duration": job["duration"]}
    
    elif action.action == "check_job":
        if player_id not in side_jobs:
            return {"success": False, "message": "Нет активной работы"}
        job = side_jobs[player_id]
        if job.get("done"):
            reward = JOBS[job["job_type"]]["reward"]
            del side_jobs[player_id]
            return {"success": True, "finished": True, "reward": reward}
        else:
            elapsed = time_module.time() - job["start_time"]
            remaining = max(0, JOBS[job["job_type"]]["duration"] - elapsed)
            return {"success": True, "finished": False, "remaining": int(remaining)}
    
    # ---------- ТРЕЙДИНГ ----------
    elif action.action == "get_trading_prices":
        return {"success": True, "prices": trading_prices}
    
    elif action.action == "buy_trading_item":
        category = action.data.get("category")
        amount = action.data.get("amount", 0)
        if category not in trading_prices:
            return {"success": False, "message": "Категория не найдена"}
        price = trading_prices[category]["price"]
        total = price * amount
        balance = player.get("balance", 0)
        if balance < total:
            return {"success": False, "message": f"Недостаточно денег! Нужно {total}₽"}
        trader = get_trader(player_id)
        portfolio = trader["portfolio"]
        portfolio[category] = portfolio.get(category, 0) + amount
        save_trader(player_id, portfolio, trader["invested"] + total)
        update_player_data(player_id, {"balance": balance - total})
        return {"success": True, "message": f"✅ Куплено {amount} ед. {category} за {total}₽", "balance": balance - total}
    
    elif action.action == "sell_trading_item":
        category = action.data.get("category")
        amount = action.data.get("amount", 0)
        if category not in trading_prices:
            return {"success": False, "message": "Категория не найдена"}
        trader = get_trader(player_id)
        portfolio = trader["portfolio"]
        if portfolio.get(category, 0) < amount:
            return {"success": False, "message": "Недостаточно товара"}
        price = trading_prices[category]["price"]
        total = price * amount
        portfolio[category] -= amount
        if portfolio[category] == 0:
            del portfolio[category]
        save_trader(player_id, portfolio, trader["invested"])
        balance = player.get("balance", 0)
        update_player_data(player_id, {"balance": balance + total})
        return {"success": True, "message": f"✅ Продано {amount} ед. {category} за {total}₽", "balance": balance + total}
    
    elif action.action == "get_trading_portfolio":
        trader = get_trader(player_id)
        return {"success": True, "portfolio": trader["portfolio"], "invested": trader["invested"]}
    
    # ---------- РАЗБОР ПОСТАВКИ ----------
    elif action.action == "start_supply":
        if player_id in supply_drop and supply_drop[player_id].get("active"):
            return {"success": False, "message": "У вас уже есть активная поставка!"}
        balance = player.get("balance", 0)
        if balance < 10000:
            return {"success": False, "message": "Нужно 10 000₽ для покупки поставки!"}
        update_player_data(player_id, {"balance": balance - 10000})
        items_in_box = []
        for _ in range(random.randint(1, 3)):
            rarities = list(SUPPLIER_ITEM_RARITIES.keys())
            weights = [SUPPLIER_ITEM_RARITIES[r]["chance"] for r in rarities]
            rarity = random.choices(rarities, weights=weights, k=1)[0]
            rd = SUPPLIER_ITEM_RARITIES[rarity]
            base = random.choice(BASE_ITEMS)
            mp = random.randint(3000, 20000)
            items_in_box.append({
                "name": f"{rd['color']} {base['cat']} {base['name']}",
                "cat": base["cat"],
                "buy_price": int(mp * 0.5),
                "market_price": mp,
                "rarity": rarity
            })
        supply_drop[player_id] = {"items": items_in_box, "found": [], "clicks": 0, "active": True}
        return {"success": True, "message": f"📦 Поставка куплена за 10 000₽! Внутри {len(items_in_box)} товаров. Жмите кнопку разбора.", "items_count": len(items_in_box)}
    
    elif action.action == "supply_click":
        drop = supply_drop.get(player_id)
        if not drop or not drop.get("active"):
            return {"success": False, "message": "Нет активной поставки"}
        drop["clicks"] += 1
        found_item = None
        if random.random() < 0.4 and drop["items"]:
            found_item = drop["items"].pop(random.randint(0, len(drop["items"])-1))
            drop["found"].append(found_item)
        remaining = 10 - drop["clicks"]
        if remaining <= 0:
            inventory = player.get("inventory", [])
            for item in drop["found"]:
                inventory.append(item)
            update_player_data(player_id, {"inventory": inventory})
            supply_drop[player_id]["active"] = False
            return {
                "success": True,
                "finished": True,
                "found": drop["found"],
                "message": f"📦 Поставка разобрана! Найдено {len(drop['found'])} вещей."
            }
        else:
            if found_item:
                msg_part = f"Найдено: {found_item['name']}!"
            else:
                msg_part = "Ничего..."
            return {
                "success": True,
                "finished": False,
                "remaining": remaining,
                "found_item": found_item,
                "found_count": len(drop["found"]),
                "message": f"🔍 Клик {drop['clicks']}/10. {msg_part}"
            }
    
    # ---------- ОБУЧЕНИЕ ----------
    elif action.action == "get_learning":
        learning = get_learning_data(player_id)
        return {"success": True, "completed": learning.get("completed", [])}
    
    elif action.action == "complete_lesson":
        lesson_id = action.data.get("lesson_id")
        reward = action.data.get("reward", 0)
        learning = get_learning_data(player_id)
        completed = learning.get("completed", [])
        if lesson_id in completed:
            return {"success": False, "message": "Урок уже пройден"}
        completed.append(lesson_id)
        update_learning_data(player_id, {"completed": completed})
        balance = player.get("balance", 0)
        update_player_data(player_id, {"balance": balance + reward})
        return {"success": True, "message": f"✅ Урок пройден! Получено {reward}₽", "balance": balance + reward}
    
    # ---------- РЕФЕРАЛЫ ----------
    elif action.action == "get_referral_data":
        ref_data = get_referral_data(player_id)
        return {"success": True, "invited": ref_data["invited"], "count": len(ref_data["invited"])}
    
    elif action.action == "claim_referral_bonus":
        ref_data = get_referral_data(player_id)
        if ref_data["bonus_claimed"]:
            return {"success": False, "message": "Бонус уже получен"}
        balance = player.get("balance", 0)
        bonus = len(ref_data["invited"]) * 10000
        update_player_data(player_id, {"balance": balance + bonus})
        update_referral_data(player_id, {"invited": ref_data["invited"], "bonus_claimed": True})
        return {"success": True, "message": f"✅ Получено {bonus}₽ за {len(ref_data['invited'])} приглашённых", "balance": balance + bonus}
    
    # ---------- ДРУЗЬЯ ----------
    elif action.action == "get_friends":
        friends = get_friends(player_id)
        return {"success": True, "friends": friends}
    
    elif action.action == "add_friend":
        friend_name = action.data.get("friend_name")
        friend_info = find_user_by_nickname(friend_name)
        if not friend_info:
            return {"success": False, "message": "Игрок не найден"}
        friend_id = friend_info["id"]
        if friend_id == player_id:
            return {"success": False, "message": "Нельзя добавить себя!"}
        friends = get_friends(player_id)
        if friend_id in friends:
            return {"success": False, "message": "Уже в друзьях!"}
        friends.append(friend_id)
        update_friends(player_id, friends)
        return {"success": True, "message": "✅ Добавлен в друзья!"}
    
    elif action.action == "remove_friend":
        friend_id = action.data.get("friend_id")
        friends = get_friends(player_id)
        if friend_id not in friends:
            return {"success": False, "message": "Не в друзьях!"}
        friends.remove(friend_id)
        update_friends(player_id, friends)
        return {"success": True, "message": "Удалён из друзей."}
    
    # ---------- ГОНКИ ----------
    elif action.action == "get_races":
        races = []
        for race_id, race in active_races.items():
            races.append({
                "id": race_id, "creator": race.get("creator"), "opponent": race.get("opponent"),
                "creator_car": race.get("creator_car"), "bet": race.get("bet"), "status": race.get("status")
            })
        return {"success": True, "races": races}
    
    elif action.action == "create_race":
        car_id = action.data.get("car_id")
        bet = action.data.get("bet", 5000)
        if bet < 5000:
            return {"success": False, "message": "Минимальная ставка: 5 000₽"}
        car_collection = player.get("car_collection", [])
        if car_id not in car_collection:
            return {"success": False, "message": "Этой машины нет в гараже!"}
        balance = player.get("balance", 0)
        if balance < bet:
            return {"success": False, "message": "Недостаточно денег!"}
        race_id = f"race_{player_id}_{int(time_module.time() * 1000)}"
        active_races[race_id] = {
            "creator": player_id, "opponent": None, "creator_car": car_id, "opponent_car": None,
            "bet": bet, "phase": 0, "creator_score": 0, "opponent_score": 0,
            "creator_actions": [], "opponent_actions": [], "prize_pool": bet,
            "status": "wait", "created_at": time_module.time()
        }
        update_player_data(player_id, {"balance": balance - bet})
        return {"success": True, "race_id": race_id, "message": "🏎 Гонка создана!", "balance": balance - bet}
    
    elif action.action == "join_race":
        race_id = action.data.get("race_id")
        car_id = action.data.get("car_id")
        race = active_races.get(race_id)
        if not race:
            return {"success": False, "message": "Гонка не найдена!"}
        if race["status"] != "wait":
            return {"success": False, "message": "Гонка уже началась!"}
        if race["creator"] == player_id:
            return {"success": False, "message": "Нельзя гонять с собой!"}
        car_collection = player.get("car_collection", [])
        if car_id not in car_collection:
            return {"success": False, "message": "Этой машины нет в гараже!"}
        balance = player.get("balance", 0)
        if balance < race["bet"]:
            return {"success": False, "message": "Недостаточно денег!"}
        update_player_data(player_id, {"balance": balance - race["bet"]})
        race["opponent"] = player_id
        race["opponent_car"] = car_id
        race["status"] = "phase_1"
        race["phase"] = 1
        race["prize_pool"] = race["bet"] * 2
        return {"success": True, "message": "🏎 Вы в гонке!", "race": race, "balance": balance - race["bet"]}
    
    elif action.action == "get_race":
        race_id = action.data.get("race_id")
        race = active_races.get(race_id)
        if not race:
            return {"success": False, "message": "Гонка не найдена"}
        return {"success": True, "race": race}
    
    elif action.action == "race_action":
        race_id = action.data.get("race_id")
        race_action_type = action.data.get("race_action")
        race = active_races.get(race_id)
        if not race:
            return {"success": False, "message": "Гонка не найдена!"}
        is_creator = player_id == race["creator"]
        car_id = race["creator_car"] if is_creator else race["opponent_car"]
        if race_action_type == "nitro":
            fee = int(race["bet"] * 0.05)
            balance = player.get("balance", 0)
            update_player_data(player_id, {"balance": balance - fee})
            race["prize_pool"] += fee
        score, msg = calculate_race_score(car_id, race_action_type, race["phase"])
        if is_creator:
            race["creator_score"] += score
            race["creator_actions"].append(race_action_type)
        else:
            race["opponent_score"] += score
            race["opponent_actions"].append(race_action_type)
        if race["phase"] >= 3:
            creator_total = race["creator_score"]
            opponent_total = race["opponent_score"]
            if creator_total > opponent_total:
                winner_id = race["creator"]
            elif opponent_total > creator_total:
                winner_id = race["opponent"]
            else:
                winner_id = None
            if winner_id:
                winner_player = get_player_data(winner_id)
                if winner_player:
                    update_player_data(winner_id, {"balance": winner_player.get("balance", 0) + race["prize_pool"]})
                race["winner"] = winner_id
                race["status"] = "finished"
            else:
                creator_player = get_player_data(race["creator"])
                opponent_player = get_player_data(race["opponent"])
                if creator_player:
                    update_player_data(race["creator"], {"balance": creator_player.get("balance", 0) + race["bet"]})
                if opponent_player:
                    update_player_data(race["opponent"], {"balance": opponent_player.get("balance", 0) + race["bet"]})
                race["status"] = "draw"
            return {
                "success": True, "finished": True, "winner": winner_id,
                "creator_score": race["creator_score"], "opponent_score": race["opponent_score"],
                "prize_pool": race["prize_pool"], "message": f"Фаза {race['phase']}: {msg} +{score} очков!"
            }
        else:
            race["phase"] += 1
            return {
                "success": True, "finished": False, "phase": race["phase"],
                "creator_score": race["creator_score"], "opponent_score": race["opponent_score"],
                "message": f"Фаза {race['phase']}: {msg} +{score} очков!"
            }
    
    # ---------- ПЕРЕВОД ДЕНЕГ ----------
    elif action.action == "transfer":
        to_player_id = action.data.get("to_player_id")
        amount = action.data.get("amount", 0)
        if amount < 100:
            return {"success": False, "message": "Минимальная сумма перевода: 100₽"}
        balance = player.get("balance", 0)
        if balance < amount:
            return {"success": False, "message": f"Недостаточно денег! У вас: {balance}₽"}
        to_player = get_player_data(to_player_id)
        if not to_player:
            return {"success": False, "message": "Получатель не найден"}
        update_player_data(player_id, {"balance": balance - amount})
        update_player_data(to_player_id, {"balance": to_player.get("balance", 0) + amount})
        return {"success": True, "message": f"✅ Переведено {amount}₽", "balance": balance - amount}
    
    # ---------- АУКЦИОН ----------
    elif action.action == "get_auction_items":
        return {"success": True, "auction_items": auction_items}
    
    elif action.action == "add_auction_item":
        item_idx = action.data.get("item_idx")
        start_price = action.data.get("start_price", 0)
        inventory = player.get("inventory", [])
        if item_idx >= len(inventory):
            return {"success": False, "message": "Товар не найден"}
        item = inventory.pop(item_idx)
        update_player_data(player_id, {"inventory": inventory})
        auction_items.append({
            "seller_id": player_id, "item": item,
            "start_price": start_price if start_price > 0 else item["market_price"],
            "current_bid": start_price if start_price > 0 else item["market_price"],
            "bidder_id": None, "end_time": time_module.time() + 3600, "active": True
        })
        return {"success": True, "message": "✅ Лот выставлен на аукцион!"}
    
    elif action.action == "bid_auction":
        item_index = action.data.get("item_index")
        bid = action.data.get("bid", 0)
        if item_index >= len(auction_items):
            return {"success": False, "message": "Лот не найден"}
        item = auction_items[item_index]
        if item["seller_id"] == player_id:
            return {"success": False, "message": "Нельзя ставить на свой лот!"}
        min_bid = int(item["current_bid"] * 1.1)
        if bid < min_bid:
            return {"success": False, "message": f"Минимальная ставка: {min_bid}₽"}
        balance = player.get("balance", 0)
        if balance < bid:
            return {"success": False, "message": f"Недостаточно денег! Нужно {bid}₽"}
        if item["bidder_id"]:
            prev_bidder = item["bidder_id"]
            prev_player = get_player_data(prev_bidder)
            if prev_player:
                update_player_data(prev_bidder, {"balance": prev_player.get("balance", 0) + item["current_bid"]})
        update_player_data(player_id, {"balance": balance - bid})
        item["current_bid"] = bid
        item["bidder_id"] = player_id
        return {"success": True, "message": f"✅ Ставка {bid}₽ принята!", "balance": balance - bid}
    
    elif action.action == "get_player_by_nickname":
        nickname = action.data.get("nickname")
        player_info = find_user_by_nickname(nickname)
        if not player_info:
            return {"success": False, "message": "Игрок не найден"}
        return {"success": True, "player": {"id": player_info["id"], "nickname": player_info["nickname"]}}
    
    elif action.action == "get_leaderboard":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nickname, total_sales, total_profit FROM players ORDER BY total_sales DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()
        top = [{"id": row["id"], "nickname": row["nickname"], "sales": row["total_sales"], "profit": row["total_profit"]} for row in rows]
        return {"success": True, "leaderboard": top}
    
    # ---------- ДОБАВЛЕНИЕ БАЛАНСА (ДЛЯ БОНУСОВ) ----------
    elif action.action == "add_balance":
        amount = action.data.get("amount", 0)
        balance = player.get("balance", 0)
        update_player_data(player_id, {"balance": balance + amount})
        return {"success": True, "balance": balance + amount}
    
    # ---------- ДОБАВЛЕНИЕ РЕФЕРАЛА С БОНУСАМИ ----------
    elif action.action == "add_referral":
        inviter_id = action.data.get("inviter_id")
        new_player_id = action.data.get("new_player_id")
        if not inviter_id or not new_player_id:
            return {"success": False, "message": "Ошибка параметров"}
        ref_data = get_referral_data(inviter_id)
        invited = ref_data.get("invited", [])
        if new_player_id not in invited:
            invited.append(new_player_id)
            update_referral_data(inviter_id, {"invited": invited, "bonus_claimed": False})
            inviter = get_player_data(inviter_id)
            if inviter:
                update_player_data(inviter_id, {"balance": inviter.get("balance", 0) + 10000})
            new_player = get_player_data(new_player_id)
            if new_player:
                update_player_data(new_player_id, {"balance": new_player.get("balance", 0) + 5000})
            return {"success": True, "message": "Реферал добавлен, бонусы начислены"}
        return {"success": False, "message": "Уже приглашен"}

    else:
        return {"success": False, "message": f"Неизвестное действие: {action.action}"}

# ==================== TELEGRAM БОТ ====================
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    waiting_for_description = State()
    waiting_for_auction_price = State()
    waiting_for_custom_amount = State()
    waiting_for_nickname = State()
    waiting_for_shopname = State()
    waiting_for_transfer_amount = State()
    waiting_for_transfer_nickname = State()

def make_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏭 ЗАКУП", callback_data="buy_menu"), InlineKeyboardButton(text="📦 ИНВЕНТАРЬ", callback_data="inventory_menu")],
        [InlineKeyboardButton(text="💰 БАЛАНС", callback_data="balance"), InlineKeyboardButton(text="🚗 АВТО", callback_data="cars_menu")],
        [InlineKeyboardButton(text="🏠 НЕДВИЖИМОСТЬ", callback_data="houses_menu"), InlineKeyboardButton(text="🏪 МАГАЗИН", callback_data="shop_menu")],
        [InlineKeyboardButton(text="🏎 ГОНКИ", callback_data="race_menu"), InlineKeyboardButton(text="👤 СКИНЫ", callback_data="skins_menu")],
        [InlineKeyboardButton(text="👥 ДРУЗЬЯ", callback_data="friends_menu"), InlineKeyboardButton(text="🔗 РЕФЕРАЛЫ", callback_data="referral_menu")],
        [InlineKeyboardButton(text="📊 СТАТЫ", callback_data="stats"), InlineKeyboardButton(text="⭐ РЕПУТАЦИЯ", callback_data="reputation")],
        [InlineKeyboardButton(text="📚 ОБУЧЕНИЕ", callback_data="learning_menu"), InlineKeyboardButton(text="🔨 АУКЦИОН", callback_data="auction_menu")],
        [InlineKeyboardButton(text="⏩ ДЕНЬ ВПЕРЁД", callback_data="next_day"), InlineKeyboardButton(text="💼 РАБОТА", callback_data="jobs_menu")],
        [InlineKeyboardButton(text="🎮 МИНИ-ИГРЫ", callback_data="minigames_menu"), InlineKeyboardButton(text="🏆 ЛИДЕРЫ", callback_data="leaderboard_menu")],
        [InlineKeyboardButton(text="💸 ПЕРЕВОД", callback_data="transfer_menu"), InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="back_to_menu")],
    ])

async def api_call(user_id: int, action: str, data: dict = None) -> dict:
    req_action = PlayerAction(platform="tg", platform_id=user_id, action=action, data=data or {})
    return await handle_action(req_action)

@dp.message(Command('start'))
async def start_cmd(message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_code = args[1][4:]
        try:
            inviter_id = int(ref_code)
            if inviter_id != user_id:
                check = await api_call(user_id, "get_stats")
                if not check.get("success") or check.get("stats", {}).get("balance", 0) == 5000:
                    await api_call(user_id, "add_referral", {"inviter_id": inviter_id, "new_player_id": user_id})
                    await message.answer("🎁 Вы перешли по реферальной ссылке! Получено +5 000₽")
        except:
            pass
    result = await api_call(user_id, "get_stats")
    if result.get("success"):
        s = result.get("stats", {})
        text = (f"🎮 <b>RESELL TYCOON</b>\n\n👤 {s.get('nickname', 'Торгаш')}\n"
                f"💰 Баланс: {s.get('balance', 0):,}₽\n📅 День: {s.get('day', 1)}\n"
                f"📦 Товаров: {s.get('inventory_count', 0)}\n📋 Продано: {s.get('items_sold', 0)}\n"
                f"💸 Прибыль: {s.get('total_earned', 0):,}₽\n\n<i>Выбери действие в меню 👇</i>")
        await message.answer(text, parse_mode="HTML", reply_markup=make_main_kb())
    else:
        await message.answer("❌ Ошибка подключения к серверу")

@dp.message(Command('menu'))
async def menu_cmd(message: Message):
    await message.answer("📋 <b>Главное меню</b>", parse_mode="HTML", reply_markup=make_main_kb())

@dp.message(Command('nick'))
async def nick_cmd(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("👤 Введи новый никнейм: /nick ТвойНик")
        return
    nickname = args[1]
    r = await api_call(message.from_user.id, "set_nickname", {"nickname": nickname})
    if r.get("success"):
        await message.answer(r.get("message"), parse_mode="HTML")
    else:
        await message.answer(f"❌ {r.get('message')}")

@dp.message(Command('shopname'))
async def shopname_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🏪 Введи новое название магазина: /shopname Название")
        return
    name = args[1]
    r = await api_call(message.from_user.id, "set_shop_name", {"name": name})
    if r.get("success"):
        await message.answer(r.get("message"), parse_mode="HTML")
    else:
        await message.answer(f"❌ {r.get('message')}")

@dp.message(Command('pay'))
async def pay_command(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("❌ Используйте: /pay ник сумма")
        return
    target_name = args[1]
    try:
        amount = int(args[2])
    except:
        await message.answer("❌ Сумма должна быть числом")
        return
    if amount < 100:
        await message.answer("❌ Минимальная сумма перевода: 100₽")
        return
    user_info = await api_call(message.from_user.id, "get_player_by_nickname", {"nickname": target_name})
    if not user_info.get("success"):
        await message.answer("❌ Игрок не найден")
        return
    target_id = user_info.get("player", {}).get("id")
    if not target_id:
        await message.answer("❌ Игрок не найден")
        return
    r = await api_call(message.from_user.id, "transfer", {"to_player_id": target_id, "amount": amount})
    if r.get("success"):
        await message.answer(f"✅ {r.get('message')}\n💰 Ваш баланс: {r.get('balance', 0):,}₽", parse_mode="HTML")
    else:
        await message.answer(f"❌ {r.get('message', 'Ошибка')}")

@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    result = await api_call(user_id, "get_stats")
    if result.get("success"):
        s = result.get("stats", {})
        text = (f"🎮 <b>RESELL TYCOON</b>\n\n👤 {s.get('nickname', 'Торгаш')}\n"
                f"💰 Баланс: {s.get('balance', 0):,}₽\n📅 День: {s.get('day', 1)}\n"
                f"📦 Товаров: {s.get('inventory_count', 0)}\n📋 Продано: {s.get('items_sold', 0)}\n"
                f"💸 Прибыль: {s.get('total_earned', 0):,}₽\n\n<i>Выбери действие в меню 👇</i>")
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=make_main_kb())
        await callback.answer()
    else:
        await callback.answer("Ошибка", show_alert=True)

@dp.callback_query(lambda c: c.data == "balance")
async def balance_callback(callback: CallbackQuery):
    r = await api_call(callback.from_user.id, "get_balance")
    if r.get("success"):
        await callback.message.edit_text(f"💰 Ваш баланс: {r.get('balance', 0):,}₽", parse_mode="HTML")
        await callback.answer()
    else:
        await callback.answer("Ошибка", show_alert=True)

@dp.callback_query(lambda c: c.data == "stats")
async def stats_callback(callback: CallbackQuery):
    r = await api_call(callback.from_user.id, "get_stats")
    if r.get("success"):
        s = r.get("stats", {})
        text = (f"📊 <b>СТАТИСТИКА</b>\n\n👤 {s.get('nickname', 'Торгаш')}\n📱 {s.get('shop_name', 'Без названия')}\n"
                f"💰 {s.get('balance', 0):,}₽\n📅 День {s.get('day', 1)}\n📦 {s.get('inventory_count', 0)} товаров\n"
                f"📋 Продано: {s.get('items_sold', 0)}\n💸 Прибыль: {s.get('total_earned', 0):,}₽\n"
                f"🏠 {s.get('house', 'room')}\n🏪 {s.get('shop_level', 'none')}\n🚗 {s.get('current_car', 'none')}\n"
                f"🎮 Машин: {s.get('car_collection_count', 0)}")
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")]]))
        await callback.answer()
    else:
        await callback.answer("Ошибка", show_alert=True)

@dp.callback_query(lambda c: c.data == "reputation")
async def reputation_callback(callback: CallbackQuery):
    r = await api_call(callback.from_user.id, "get_reputation")
    if r.get("success"):
        text = (f"⭐ <b>РЕПУТАЦИЯ АВИТО</b>\n\nУровень: <b>{r.get('level', 'Новичок')}</b>\n"
                f"Рейтинг: {r.get('rating', '⭐ Новый продавец')}\n📦 Продаж: {r.get('total_sales', 0)}\n"
                f"💰 Прибыль: {r.get('total_profit', 0):,}₽\n\n<i>5 продаж → Темщик, 15 продаж → Мажор</i>")
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 СКИНЫ", callback_data="skins_menu")], [InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")]]))
        await callback.answer()
    else:
        await callback.answer("Ошибка", show_alert=True)

@dp.callback_query(lambda c: c.data == "next_day")
async def next_day_callback(callback: CallbackQuery):
    r = await api_call(callback.from_user.id, "next_day")
    if r.get("success"):
        await callback.message.edit_text(f"☀️ <b>ДЕНЬ {r.get('day')}</b>\n💰 Баланс: {r.get('balance', 0):,}₽\n💵 Доход: +{r.get('income', 0)}₽", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")]]))
        await callback.answer()
    else:
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)

@dp.callback_query(lambda c: c.data == "buy_menu")
async def buy_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    res = await api_call(user_id, "get_suppliers")
    if not res.get("success"):
        await callback.answer("Ошибка", show_alert=True)
        return
    items = res.get("suppliers", [])
    if not items:
        await callback.message.edit_text("🏭 <b>ПОСТАВЩИКИ</b>\n\nТовары обновляются...", parse_mode="HTML")
        await callback.answer()
        return
    text = "🏭 <b>ПОСТАВЩИКИ</b>\n<i>Обновление каждые 5 мин.</i>\n\n"
    kb = []
    for it in items[:8]:
        tl = max(0, int(it.get("end_time", 0) - time_module.time()))
        mins = tl // 60
        text += f"{it.get('rarity_color', '⬜')} {it.get('name')} — {it.get('buy_price')}₽ ({mins}м)\n"
        kb.append([InlineKeyboardButton(text=f"🛒 {it.get('name')[:30]} - {it.get('buy_price')}₽", callback_data=f"buy_{it.get('id')}")])
    kb.append([InlineKeyboardButton(text="🔄 ОБНОВИТЬ", callback_data="buy_menu")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_item_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    item_id = int(callback.data.split("_")[1])
    r = await api_call(user_id, "buy_from_supplier", {"item_id": item_id})
    if r.get("success"):
        await callback.message.edit_text(f"✅ {r.get('message')}\n💰 Баланс: {r.get('balance', 0):,}₽", parse_mode="HTML")
        await callback.answer("✅ Куплено!")
    else:
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)

@dp.callback_query(lambda c: c.data == "inventory_menu")
async def inventory_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "get_inventory")
    if not r.get("success"):
        await callback.answer("Ошибка", show_alert=True)
        return
    inv = r.get("inventory", [])
    if not inv:
        await callback.message.edit_text("📦 <b>ИНВЕНТАРЬ ПУСТ</b>\n\nКупи товары у поставщиков! 👇", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏭 ЗАКУП", callback_data="buy_menu")], [InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")]]))
        await callback.answer()
        return
    text = "📦 <b>ИНВЕНТАРЬ</b>\n\n"
    kb = []
    for i, it in enumerate(inv):
        text += f"{i+1}. {it.get('name')}\n   Закуп: {it.get('buy_price')}₽ | Рынок: ~{it.get('market_price')}₽\n\n"
        kb.append([InlineKeyboardButton(text=f"📢 ОПУБЛИКОВАТЬ: {it.get('name')[:25]}", callback_data=f"publish_{i}")])
        kb.append([InlineKeyboardButton(text=f"🔨 НА АУКЦИОН: {it.get('name')[:20]}", callback_data=f"auction_sell_item_{i}")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("publish_"))
async def publish_item_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    item_idx = int(callback.data.split("_")[1])
    await state.update_data(publish_item_idx=item_idx)
    await state.set_state(Form.waiting_for_description)
    await callback.message.edit_text("✍️ <b>ОПИШИ ТОВАР</b>\n\nНапиши описание в чат (чем подробнее, тем выше шанс продажи)", parse_mode="HTML")
    await callback.answer()

@dp.message(StateFilter(Form.waiting_for_description))
async def handle_description(message: Message, state: FSMContext):
    user_id = message.from_user.id
    desc = message.text.strip()
    data = await state.get_data()
    item_idx = data.get("publish_item_idx", 0)
    r = await api_call(user_id, "publish_item", {"item_idx": item_idx, "description": desc})
    if r.get("success"):
        await message.answer(r.get("message"), parse_mode="HTML")
    else:
        await message.answer(f"❌ {r.get('message', 'Ошибка')}")
    await state.clear()

@dp.callback_query(lambda c: c.data == "chats_menu")
async def chats_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "get_chats")
    if not r.get("success"):
        await callback.answer("Нет активных чатов", show_alert=True)
        return
    chats = r.get("chats", [])
    if not chats:
        await callback.message.edit_text("💬 <b>ЧАТЫ С ПОКУПАТЕЛЯМИ</b>\n\nНет активных диалогов.\nОпубликуй товар в 📦 Инвентаре!", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")]]))
        await callback.answer()
        return
    text = "💬 <b>ДИАЛОГИ</b>\n\n"
    kb = []
    for ch in chats:
        buyer_id = ch.get("buyer_id")
        item = ch.get("item", "")
        offer = ch.get("offer", 0)
        rnd = ch.get("round", 0)
        max_rnd = ch.get("max_rounds", 0)
        text += f"👤 #{buyer_id}\n📦 {item}\n💰 {offer}₽ | Раунд {rnd}/{max_rnd}\n\n"
        kb.append([InlineKeyboardButton(text=f"💬 Ответить #{buyer_id}", callback_data=f"open_chat_{buyer_id}")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("open_chat_"))
async def open_chat_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    buyer_id = int(callback.data.split("_")[2])
    r = await api_call(user_id, "start_chat", {"buyer_id": buyer_id})
    if not r.get("success"):
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)
        return
    msg = r.get("message")
    offer = r.get("offer")
    await state.update_data(current_buyer_id=buyer_id)
    await callback.message.edit_text(f"👤 <b>Покупатель #{buyer_id}</b>\n\n{msg}\n\n<i>Напишите ответ или «согласен» для продажи за {offer}₽</i>", parse_mode="HTML")
    await callback.answer()

@dp.message()
async def handle_chat_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    buyer_id = data.get("current_buyer_id")
    if not buyer_id:
        return
    text = message.text.strip()
    r = await api_call(user_id, "send_chat_message", {"buyer_id": buyer_id, "text": text})
    if r.get("success"):
        if r.get("sold"):
            await message.answer(f"🎉 <b>ПРОДАЖА!</b>\n{r.get('message')}\n💰 Баланс: {r.get('balance', 0):,}₽", parse_mode="HTML")
            await state.update_data(current_buyer_id=None)
        else:
            await message.answer(f"👤 <b>Покупатель #{buyer_id}</b>\n\n{r.get('message')}")
    else:
        await message.answer(f"❌ {r.get('message', 'Ошибка')}")
        if "завершён" in r.get("message", ""):
            await state.update_data(current_buyer_id=None)

@dp.callback_query(lambda c: c.data == "cars_menu")
async def cars_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    cars = CARS
    if not hasattr(cars_menu_callback, "page"):
        cars_menu_callback.page = {}
    page = cars_menu_callback.page.get(user_id, 0)
    total = len(cars)
    if page < 0: page = 0
    if page >= total: page = total - 1
    if total == 0:
        await callback.message.edit_text("🚗 Автомобили временно недоступны.", parse_mode="HTML")
        await callback.answer()
        return
    car = cars[page]
    p = await api_call(user_id, "get_stats")
    balance = p.get("stats", {}).get("balance", 0) if p.get("success") else 0
    collection = await api_call(user_id, "get_car_collection")
    owned = car["id"] in collection.get("cars", []) if collection.get("success") else []
    current_car = await api_call(user_id, "get_current_car")
    is_current = current_car.get("car_id") == car["id"] if current_car.get("success") else False
    txt = f"🛒 <b>АВТОСАЛОН</b>\n📄 {page+1}/{total}\n\n{car['name']}\n⭐ {car['rarity'].upper()}\n⚡ Ускорение: {car['speed_bonus']}%\n💰 Доход: {car['income_per_hour']}₽/час\n"
    if is_current:
        txt += "\n✅ <b>ТВОЯ ТЕКУЩАЯ МАШИНА</b>"
        act = None
    elif owned:
        txt += "\n✅ <b>КУПЛЕНО</b> (в гараже)"
        act = InlineKeyboardButton(text="🚗 СДЕЛАТЬ ТЕКУЩЕЙ", callback_data=f"set_car_{car['id']}") if not is_current else None
    elif balance >= car["price"]:
        txt += f"\n💰 Цена: {car['price']:,}₽"
        act = InlineKeyboardButton(text="🛒 КУПИТЬ", callback_data=f"buy_car_{car['id']}")
    else:
        txt += f"\n❌ Нужно {car['price']:,}₽ (не хватает {car['price'] - balance:,}₽)"
        act = None
    txt += f"\n\n💼 Баланс: {balance:,}₽"
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"car_page_{page-1}"))
    if page < total - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"car_page_{page+1}"))
    kb = []
    if nav:
        kb.append(nav)
    if act:
        kb.append([act])
    kb.append([InlineKeyboardButton(text="🏠 МОЙ ГАРАЖ", callback_data="garage_menu")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    if car.get("image_url"):
        try:
            await callback.message.delete()
            msg = await bot.send_photo(user_id, car["image_url"], caption=txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            last_bot_message[user_id] = msg.message_id
        except:
            await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    cars_menu_callback.page[user_id] = page
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("car_page_"))
async def car_page_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    page = int(callback.data.split("_")[2])
    cars_menu_callback.page[user_id] = page
    await cars_menu_callback(callback)

@dp.callback_query(lambda c: c.data.startswith("buy_car_"))
async def buy_car_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    car_id = callback.data.split("_")[2]
    r = await api_call(user_id, "buy_car", {"car_id": car_id})
    if r.get("success"):
        await callback.message.edit_text(f"✅ {r.get('message')}\n💰 Баланс: {r.get('balance', 0):,}₽", parse_mode="HTML")
        await callback.answer("✅ Куплено!")
    else:
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)

@dp.callback_query(lambda c: c.data == "garage_menu")
async def garage_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "get_car_collection")
    if not r.get("success"):
        await callback.answer("Ошибка", show_alert=True)
        return
    cars = r.get("cars", [])
    if not cars:
        await callback.message.edit_text("🏠 <b>ГАРАЖ ПУСТ</b>\n\nКупи машины в автосалоне! 👇", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 АВТОСАЛОН", callback_data="cars_menu")],
            [InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")]
        ]))
        await callback.answer()
        return
    if not hasattr(garage_menu_callback, "page"):
        garage_menu_callback.page = {}
    page = garage_menu_callback.page.get(user_id, 0)
    total = len(cars)
    if page < 0: page = 0
    if page >= total: page = total - 1
    car_ref = cars[page]
    full_car = next((c for c in CARS if c["id"] == car_ref["id"]), None)
    if not full_car:
        await callback.answer("Ошибка: машина не найдена", show_alert=True)
        return
    full_car["is_current"] = car_ref.get("is_current", False)
    text = f"🏠 <b>ТВОЙ ГАРАЖ</b>\n📄 {page+1}/{total}\n\n{full_car['name']}\n⭐ {full_car.get('rarity', 'обычный').upper()}\n⚡ Ускорение: {full_car.get('speed_bonus', 0)}%\n💰 Доход: {full_car.get('income_per_hour', 0)}₽/час\n"
    if full_car.get("is_current"):
        text += "\n✅ <b>ТЕКУЩАЯ МАШИНА</b>"
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"garage_page_{page-1}"))
    if page < total - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"garage_page_{page+1}"))
    kb = []
    if nav:
        kb.append(nav)
    if not full_car.get("is_current"):
        kb.append([InlineKeyboardButton(text="🚗 СДЕЛАТЬ ТЕКУЩЕЙ", callback_data=f"set_car_{full_car['id']}")])
    kb.append([InlineKeyboardButton(text="🚕 ТАКСОПАРК", callback_data="taxopark_menu")])
    kb.append([InlineKeyboardButton(text="🔙 В АВТОСАЛОН", callback_data="cars_menu")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    if full_car.get("image_url"):
        try:
            await callback.message.delete()
            msg = await bot.send_photo(user_id, full_car["image_url"], caption=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            last_bot_message[user_id] = msg.message_id
        except:
            await send_msg(user_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await send_msg(user_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    garage_menu_callback.page[user_id] = page
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("garage_page_"))
async def garage_page_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    page = int(callback.data.split("_")[2])
    garage_menu_callback.page[user_id] = page
    await garage_menu_callback(callback)

@dp.callback_query(lambda c: c.data.startswith("set_car_"))
async def set_car_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    car_id = callback.data.split("_")[2]
    r = await api_call(user_id, "set_current_car", {"car_id": car_id})
    if r.get("success"):
        await callback.message.edit_text(f"✅ {r.get('message')}", parse_mode="HTML")
        await callback.answer()
    else:
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)

@dp.callback_query(lambda c: c.data == "taxopark_menu")
async def taxopark_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "get_taxopark")
    if not r.get("success"):
        await callback.answer("Ошибка", show_alert=True)
        return
    tax = r.get("taxopark", {})
    level_info = r.get("level_info", {})
    text = f"🚕 <b>ТАКСОПАРК</b>\n\nТекущий: {level_info.get('name', 'Нет')}\n"
    if level_info.get("slots", 0) > 0:
        text += f"📊 Слотов: {len(tax.get('cars', []))}/{level_info.get('slots', 0)}\n💰 Доход: {level_info.get('income_per_car', 0)}₽/час с машины\n"
        if tax.get("cars"):
            text += "\n<b>Машины в таксопарке:</b>\n" + "\n".join(f"• {c}" for c in tax.get("cars", []))
    kb = []
    levels_res = await api_call(user_id, "get_taxopark_levels")
    if levels_res.get("success"):
        for lvl in levels_res.get("levels", []):
            if lvl.get("price", 0) > 0 and lvl.get("id") != tax.get("level"):
                kb.append([InlineKeyboardButton(text=f"⬆️ {lvl.get('name')} - {lvl.get('price'):,}₽", callback_data=f"buy_taxopark_{lvl.get('id')}")])
    kb.append([InlineKeyboardButton(text="➕ ДОБАВИТЬ МАШИНУ", callback_data="taxopark_add_menu")])
    kb.append([InlineKeyboardButton(text="🔙 В ГАРАЖ", callback_data="garage_menu")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("buy_taxopark_"))
async def buy_taxopark_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    level_id = callback.data.split("_")[2]
    r = await api_call(user_id, "buy_taxopark", {"level_id": level_id})
    if r.get("success"):
        await callback.answer("✅ Куплено!")
        await taxopark_menu_callback(callback)
    else:
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)

@dp.callback_query(lambda c: c.data == "taxopark_add_menu")
async def taxopark_add_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    cars_res = await api_call(user_id, "get_car_collection")
    if not cars_res.get("success"):
        await callback.answer("Ошибка", show_alert=True)
        return
    cars = cars_res.get("cars", [])
    if not cars:
        await callback.answer("Нет машин в гараже", show_alert=True)
        return
    text = "➕ <b>ВЫБЕРИ МАШИНУ ДЛЯ ТАКСОПАРКА:</b>\n\n"
    kb = []
    for car in cars:
        text += f"• {car.get('name')}\n"
        kb.append([InlineKeyboardButton(text=f"➕ {car.get('name')}", callback_data=f"add_taxopark_{car.get('id')}")])
    kb.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="taxopark_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("add_taxopark_"))
async def add_taxopark_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    car_id = callback.data.split("_")[2]
    r = await api_call(user_id, "add_car_to_taxopark", {"car_id": car_id})
    if r.get("success"):
        await callback.answer("✅ Добавлено!")
        await taxopark_menu_callback(callback)
    else:
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)

@dp.callback_query(lambda c: c.data == "houses_menu")
async def houses_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    houses = HOUSES
    if not hasattr(houses_menu_callback, "page"):
        houses_menu_callback.page = {}
    page = houses_menu_callback.page.get(user_id, 0)
    total = len(houses)
    if page < 0: page = 0
    if page >= total: page = total - 1
    if total == 0:
        await callback.message.edit_text("🏠 Недвижимость временно недоступна.", parse_mode="HTML")
        await callback.answer()
        return
    house = houses[page]
    p = await api_call(user_id, "get_stats")
    balance = p.get("stats", {}).get("balance", 0) if p.get("success") else 0
    current_house = await api_call(user_id, "get_current_house")
    current_id = current_house.get("house", {}).get("id") if current_house.get("success") else "room"
    owned = house["id"] == current_id
    txt = f"🏠 <b>НЕДВИЖИМОСТЬ</b>\n📄 {page+1}/{total}\n\n{house['name']}\n💰 Доход: +{house['income_bonus']}₽/день\n"
    if house.get("description"):
        txt += f"{house['description']}\n"
    if owned:
        txt += "\n✅ <b>ТВОЁ ЖИЛЬЁ</b>"
        act = None
    elif balance >= house["price"]:
        txt += f"\n💰 Цена: {house['price']:,}₽"
        act = InlineKeyboardButton(text="🛒 КУПИТЬ", callback_data=f"buy_house_{house['id']}")
    else:
        txt += f"\n❌ Нужно {house['price']:,}₽ (не хватает {house['price'] - balance:,}₽)"
        act = None
    txt += f"\n\n💼 Баланс: {balance:,}₽"
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"house_page_{page-1}"))
    if page < total - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"house_page_{page+1}"))
    kb = []
    if nav:
        kb.append(nav)
    if act:
        kb.append([act])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    if house.get("image_url"):
        try:
            await callback.message.delete()
            msg = await bot.send_photo(user_id, house["image_url"], caption=txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            last_bot_message[user_id] = msg.message_id
        except:
            await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    houses_menu_callback.page[user_id] = page
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("house_page_"))
async def house_page_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    page = int(callback.data.split("_")[2])
    houses_menu_callback.page[user_id] = page
    await houses_menu_callback(callback)

@dp.callback_query(lambda c: c.data.startswith("buy_house_"))
async def buy_house_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    house_id = callback.data.split("_")[2]
    r = await api_call(user_id, "buy_house", {"house_id": house_id})
    if r.get("success"):
        await callback.message.edit_text(f"✅ {r.get('message')}\n💰 Баланс: {r.get('balance', 0):,}₽", parse_mode="HTML")
        await callback.answer("✅ Куплено!")
    else:
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)

@dp.callback_query(lambda c: c.data == "shop_menu")
async def shop_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "get_shops")
    if not r.get("success"):
        await callback.answer("Ошибка", show_alert=True)
        return
    shops = r.get("shops", [])
    cur = await api_call(user_id, "get_current_shop")
    current_shop = cur.get("shop") if cur.get("success") else None
    text = "🏪 <b>МАГАЗИН ОДЕЖДЫ</b>\n\n"
    if current_shop and current_shop.get("id") != "none":
        text += f"Текущий: {current_shop.get('name')}\n💰 Доход: {current_shop.get('income_per_hour')}₽/час\n\n"
    kb = []
    for shop in shops:
        if shop.get("id") == "none":
            continue
        status = "✅ " if current_shop and current_shop.get("id") == shop.get("id") else ""
        text += f"{status}{shop.get('name')}\n💰 {shop.get('price'):,}₽ | 📈 +{shop.get('income_per_hour')}₽/час\n\n"
        if not (current_shop and current_shop.get("id") == shop.get("id")):
            kb.append([InlineKeyboardButton(text=f"🛒 КУПИТЬ {shop.get('name')} - {shop.get('price'):,}₽", callback_data=f"buy_shop_{shop.get('id')}")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("buy_shop_"))
async def buy_shop_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    shop_id = callback.data.split("_")[2]
    r = await api_call(user_id, "buy_shop", {"shop_id": shop_id})
    if r.get("success"):
        await callback.message.edit_text(f"✅ {r.get('message')}\n💰 Баланс: {r.get('balance', 0):,}₽", parse_mode="HTML")
        await callback.answer("✅ Куплено!")
    else:
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)

@dp.callback_query(lambda c: c.data == "skins_menu")
async def skins_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    skins = SKINS
    rarity_order = {"обычный": 0, "редкий": 1, "эпический": 2, "легендарный": 3, "мифический": 4}
    skins.sort(key=lambda x: rarity_order.get(x.get("rarity", "обычный"), 0))
    if not hasattr(skins_menu_callback, "page"):
        skins_menu_callback.page = {}
    page = skins_menu_callback.page.get(user_id, 0)
    total = len(skins)
    if page < 0: page = 0
    if page >= total: page = total - 1
    if total == 0:
        await callback.message.edit_text("👤 Скины временно недоступны.", parse_mode="HTML")
        await callback.answer()
        return
    skin = skins[page]
    player_skins = await api_call(user_id, "get_player_skins")
    owned_skins = [s["id"] for s in player_skins.get("skins", [])] if player_skins.get("success") else []
    current = player_skins.get("current", "default") if player_skins.get("success") else "default"
    p = await api_call(user_id, "get_stats")
    balance = p.get("stats", {}).get("balance", 0) if p.get("success") else 0
    rep = await api_call(user_id, "get_reputation")
    total_sales = rep.get("total_sales", 0) if rep.get("success") else 0
    txt = f"👤 <b>МАГАЗИН СКИНОВ</b>\n📄 {page+1}/{total}\n\n{skin['emoji']} <b>{skin['name']}</b>\n⭐ {skin['rarity'].upper()}\n📝 {skin['description']}\n"
    if skin["id"] == current:
        txt += "\n✅ <b>НАДЕТ</b>"
        act = None
    elif skin["id"] in owned_skins:
        txt += "\n✅ <b>В ИНВЕНТАРЕ</b>"
        act = InlineKeyboardButton(text="👕 НАДЕТЬ", callback_data=f"equip_skin_{skin['id']}")
    elif skin.get("sales_required", 0) > 0:
        if total_sales >= skin["sales_required"]:
            txt += "\n🎁 <b>ДОСТУПЕН!</b>"
            act = InlineKeyboardButton(text="🎁 ПОЛУЧИТЬ", callback_data=f"buy_skin_{skin['id']}")
        else:
            txt += f"\n🔒 Нужно {skin['sales_required']} продаж (у тебя {total_sales})"
            act = None
    else:
        if skin.get("limited"):
            txt += f"\n🔒 <b>ТОЛЬКО ПО ВЫДАЧЕ</b>"
            act = None
        else:
            if balance >= skin["price"]:
                txt += f"\n💰 Цена: {skin['price']:,}₽"
                act = InlineKeyboardButton(text="🛒 КУПИТЬ", callback_data=f"buy_skin_{skin['id']}")
            else:
                txt += f"\n❌ {skin['price']:,}₽ (не хватает {skin['price'] - balance:,}₽)"
                act = None
    txt += f"\n\n💼 Баланс: {balance:,}₽ | ⭐ Продано: {total_sales}"
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"skin_page_{page-1}"))
    if page < total - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"skin_page_{page+1}"))
    kb = []
    if nav:
        kb.append(nav)
    if act:
        kb.append([act])
    kb.append([InlineKeyboardButton(text="🎒 ИНВЕНТАРЬ СКИНОВ", callback_data="skin_inventory")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    if skin.get("image_url"):
        try:
            await callback.message.delete()
            msg = await bot.send_photo(user_id, skin["image_url"], caption=txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            last_bot_message[user_id] = msg.message_id
        except:
            await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    skins_menu_callback.page[user_id] = page
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("skin_page_"))
async def skin_page_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    page = int(callback.data.split("_")[2])
    skins_menu_callback.page[user_id] = page
    await skins_menu_callback(callback)

@dp.callback_query(lambda c: c.data.startswith("buy_skin_"))
async def buy_skin_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    skin_id = callback.data.split("_")[2]
    r = await api_call(user_id, "buy_skin", {"skin_id": skin_id})
    if r.get("success"):
        await callback.message.edit_text(f"✅ {r.get('message')}\n💰 Баланс: {r.get('balance', 0):,}₽", parse_mode="HTML")
        await callback.answer("✅ Куплено!")
    else:
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("equip_skin_"))
async def equip_skin_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    skin_id = callback.data.split("_")[2]
    r = await api_call(user_id, "equip_skin", {"skin_id": skin_id})
    if r.get("success"):
        await callback.message.edit_text(f"✅ {r.get('message')}", parse_mode="HTML")
        await callback.answer()
    else:
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)

@dp.callback_query(lambda c: c.data == "skin_inventory")
async def skin_inventory_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "get_player_skins")
    if not r.get("success"):
        await callback.answer("Ошибка", show_alert=True)
        return
    skins = r.get("skins", [])
    current = r.get("current", "default")
    if not skins:
        await callback.message.edit_text("🎒 <b>ИНВЕНТАРЬ СКИНОВ ПУСТ</b>\n\nКупи скины в магазине! 👇", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 В МАГАЗИН", callback_data="skins_menu")], [InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")]]))
        await callback.answer()
        return
    text = "🎒 <b>ТВОИ СКИНЫ:</b>\n\n"
    kb = []
    for skin in skins:
        active = "✅ НАДЕТ" if skin["id"] == current else ""
        text += f"{skin.get('emoji', '👤')} {skin.get('name')} ({skin.get('rarity', 'обычный')}) {active}\n"
        if skin["id"] != current:
            kb.append([InlineKeyboardButton(text=f"👕 НАДЕТЬ: {skin.get('emoji')} {skin.get('name')}", callback_data=f"equip_skin_{skin.get('id')}")])
    kb.append([InlineKeyboardButton(text="🔙 В МАГАЗИН СКИНОВ", callback_data="skins_menu")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "jobs_menu")
async def jobs_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "get_jobs")
    if not r.get("success"):
        await callback.answer("Ошибка", show_alert=True)
        return
    jobs = r.get("jobs", [])
    text = "💼 <b>ПОДРАБОТКИ</b>\n\nВыбери работу:\n"
    kb = []
    for i, job in enumerate(jobs):
        text += f"{job.get('emoji')} {job.get('name')} — {job.get('reward')}₽ ({job.get('duration')}с)\n"
        kb.append([InlineKeyboardButton(text=f"{job.get('emoji')} {job.get('name')} — {job.get('reward')}₽", callback_data=f"start_job_{i}")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("start_job_"))
async def start_job_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    job_idx = int(callback.data.split("_")[2])
    r = await api_call(user_id, "start_job", {"job_idx": job_idx})
    if r.get("success"):
        await callback.message.edit_text(f"💼 <b>РАБОТА НАЧАТА!</b>\n{r.get('message')}", parse_mode="HTML")
        asyncio.create_task(check_job_completion(callback.message, user_id))
        await callback.answer()
    else:
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)

async def check_job_completion(msg: types.Message, user_id: int):
    await asyncio.sleep(1)
    for _ in range(60):
        await asyncio.sleep(2)
        r = await api_call(user_id, "check_job")
        if r.get("success") and r.get("finished"):
            await msg.answer(f"✅ <b>РАБОТА ЗАВЕРШЕНА!</b>\n💰 +{r.get('reward')}₽", parse_mode="HTML")
            return
        elif r.get("success") and not r.get("finished"):
            continue
        else:
            break

@dp.callback_query(lambda c: c.data == "trading_menu")
async def trading_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "get_trading_prices")
    if not r.get("success"):
        await callback.answer("Ошибка", show_alert=True)
        return
    prices = r.get("prices", {})
    port = await api_call(user_id, "get_trading_portfolio")
    portfolio = port.get("portfolio", {}) if port.get("success") else {}
    text = "📊 <b>БИРЖА ТОВАРОВ</b>\n\n"
    kb = []
    for cat, data in prices.items():
        trend = "📈" if data.get("trend", 0) > 0 else "📉"
        owned = portfolio.get(cat, 0)
        text += f"{trend} {cat}: <b>{data.get('price', 0)}₽</b> | У тебя: {owned} ед.\n"
        kb.append([InlineKeyboardButton(text=f"🟢 КУПИТЬ {cat}", callback_data=f"trade_buy_{cat}"),
                   InlineKeyboardButton(text=f"🔴 ПРОДАТЬ {cat}", callback_data=f"trade_sell_{cat}")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("trade_buy_"))
async def trade_buy_callback(callback: CallbackQuery, state: FSMContext):
    cat = callback.data.replace("trade_buy_", "")
    await state.update_data(trade_category=cat, trade_action="buy")
    await callback.message.answer(f"✍️ Введи количество {cat} для покупки:")
    await state.set_state(Form.waiting_for_custom_amount)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("trade_sell_"))
async def trade_sell_callback(callback: CallbackQuery, state: FSMContext):
    cat = callback.data.replace("trade_sell_", "")
    await state.update_data(trade_category=cat, trade_action="sell")
    await callback.message.answer(f"✍️ Введи количество {cat} для продажи:")
    await state.set_state(Form.waiting_for_custom_amount)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "minigames_menu")
async def minigames_menu_callback(callback: CallbackQuery):
    text = ("🎮 <b>МИНИ-ИГРЫ</b>\n\n📦 <b>РАЗБЕРИ ПОСТАВКУ</b>\n💰 Цена: 10 000₽\n"
            "🎁 Секретный бокс от поставщика\n🔄 Шанс найти вещь: 40%\n\n"
            "📊 <b>ТРЕЙДИНГ</b>\n💵 Покупай и продавай товары\n📈 Следи за рынком и зарабатывай\n\n"
            "🏎 <b>ГОНКИ</b>\n⚡ Гоняй с друзьями на своих машинах")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 РАЗОБРАТЬ ПОСТАВКУ (10 000₽)", callback_data="start_supply")],
        [InlineKeyboardButton(text="📊 ТРЕЙДИНГ", callback_data="trading_menu")],
        [InlineKeyboardButton(text="🏎 ГОНКИ", callback_data="race_menu")],
        [InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "start_supply")
async def start_supply_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "start_supply")
    if r.get("success"):
        await callback.message.edit_text(f"📦 <b>ПОСТАВКА КУПЛЕНА!</b>\n{r.get('message')}\n\n<i>Нажми на кнопку, чтобы разбирать коробку</i>", parse_mode="HTML",
                                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📦 РАЗОБРАТЬ (10 кликов)", callback_data="supply_click")], [InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")]]))
        await callback.answer()
    else:
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)

@dp.callback_query(lambda c: c.data == "supply_click")
async def supply_click_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "supply_click")
    if not r.get("success"):
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)
        return
    if r.get("finished"):
        found = r.get("found", [])
        text = f"📦 <b>ПОСТАВКА РАЗОБРАНА!</b>\n\n🎁 Найдено {len(found)} вещей:\n" + "\n".join(f"• {it.get('name')} (~{it.get('market_price')}₽)" for it in found)
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")]]))
        await callback.answer()
    else:
        remaining = r.get("remaining", 0)
        found_item = r.get("found_item")
        found_count = r.get("found_count", 0)
        msg = f"🔍 Кликов осталось: {remaining}\n🎁 Найдено вещей: {found_count}\n"
        if found_item:
            msg += f"✅ Найден {found_item.get('name')}!"
        else:
            msg += "❌ Ничего..."
        await callback.message.edit_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"📦 РАЗОБРАТЬ (ещё {remaining})", callback_data="supply_click")], [InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")]]))
        await callback.answer()

@dp.callback_query(lambda c: c.data == "race_menu")
async def race_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "get_races")
    races = r.get("races", []) if r.get("success") else []
    text = "🏎 <b>ГОНКИ</b>\n\nТвои гонки:\n"
    my = [rc for rc in races if rc.get("creator") == user_id or rc.get("opponent") == user_id]
    if my:
        for rc in my:
            text += f"🏎 Ставка: {rc.get('bet')}₽ | Статус: {rc.get('status')}\n"
    else:
        text += "Нет активных гонок\n"
    kb = [[InlineKeyboardButton(text="🏎 СОЗДАТЬ ГОНКУ", callback_data="race_create")]]
    for rc in races:
        if rc.get("status") == "wait" and rc.get("creator") != user_id:
            kb.append([InlineKeyboardButton(text=f"🏎 Ставка {rc.get('bet')}₽", callback_data=f"race_join_{rc.get('id')}")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "race_create")
async def race_create_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    cars = await api_call(user_id, "get_car_collection")
    cars_list = cars.get("cars", []) if cars.get("success") else []
    if not cars_list:
        await callback.answer("Нет машин в гараже!", show_alert=True)
        return
    text = "🏎 <b>ВЫБЕРИ МАШИНУ И СТАВКУ</b>\n\n"
    kb = []
    for car in cars_list:
        kb.append([InlineKeyboardButton(text=f"{car.get('name')} — ставка 5 000₽", callback_data=f"race_start_{car.get('id')}_5000")])
        kb.append([InlineKeyboardButton(text=f"{car.get('name')} — ставка 25 000₽", callback_data=f"race_start_{car.get('id')}_25000")])
    kb.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="race_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("race_start_"))
async def race_start_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    car_id = parts[2]
    bet = int(parts[3])
    r = await api_call(user_id, "create_race", {"car_id": car_id, "bet": bet})
    if r.get("success"):
        race_id = r.get("race_id")
        await callback.message.edit_text(f"🏎 <b>ГОНКА СОЗДАНА!</b>\nID: {race_id}\nСтавка: {bet}₽\n\nОтправь другу: /race join {race_id}", parse_mode="HTML")
        await callback.answer()
    else:
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("race_join_"))
async def race_join_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    race_id = callback.data.replace("race_join_", "")
    cars = await api_call(user_id, "get_car_collection")
    cars_list = cars.get("cars", []) if cars.get("success") else []
    if not cars_list:
        await callback.answer("Нет машин в гараже!", show_alert=True)
        return
    text = "🏎 <b>ВЫБЕРИ МАШИНУ ДЛЯ УЧАСТИЯ</b>\n\n"
    kb = []
    for car in cars_list:
        kb.append([InlineKeyboardButton(text=f"{car.get('name')}", callback_data=f"race_confirm_{race_id}|{car.get('id')}")])
    kb.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="race_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("race_confirm_"))
async def race_confirm_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data.replace("race_confirm_", "")
    race_id, car_id = data.split("|")
    r = await api_call(user_id, "join_race", {"race_id": race_id, "car_id": car_id})
    if r.get("success"):
        race = r.get("race")
        await callback.message.edit_text(f"🏎 <b>ГОНКА НАЧАЛАСЬ!</b>\nСтавка: {race.get('bet')}₽\n\nФаза 1/3. Выбери действие:", parse_mode="HTML")
        await race_phase_menu(callback.message, race_id, user_id)
        await callback.answer()
    else:
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)

async def race_phase_menu(msg: types.Message, race_id: str, user_id: int):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 ГАЗ В ПОЛ (+30%, риск 20%)", callback_data=f"race_action_{race_id}_boost")],
        [InlineKeyboardButton(text="🛡 РОВНЫЙ ХОД (+10%)", callback_data=f"race_action_{race_id}_normal")],
        [InlineKeyboardButton(text="🔥 НИТРО (+50%, -5% ставки)", callback_data=f"race_action_{race_id}_nitro")],
    ])
    await msg.answer("🏎 <b>ФАЗА 1</b>\nВыбери действие:", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("race_action_"))
async def race_action_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    race_id = parts[2]
    action = parts[3]
    r = await api_call(user_id, "race_action", {"race_id": race_id, "race_action": action})
    if not r.get("success"):
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)
        return
    if r.get("finished"):
        winner = r.get("winner")
        text = (f"🏁 <b>ГОНКА ЗАВЕРШЕНА!</b>\n"
                f"Ваши очки: {r.get('creator_score' if user_id == winner else 'opponent_score', 0)}\n"
                f"Соперник: {r.get('opponent_score' if user_id == winner else 'creator_score', 0)}\n"
                f"🏆 Победитель: {'Вы' if winner == user_id else 'Соперник'}\n"
                f"💰 Призовой фонд: {r.get('prize_pool', 0)}₽")
        await callback.message.edit_text(text, parse_mode="HTML")
        await callback.answer()
    else:
        phase = r.get("phase")
        await callback.message.edit_text(f"🏎 <b>ФАЗА {phase}/3</b>\n{r.get('message')}\n\nВыбери следующее действие:", parse_mode="HTML")
        await race_phase_menu(callback.message, race_id, user_id)
        await callback.answer()

@dp.callback_query(lambda c: c.data == "auction_menu")
async def auction_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "get_auction_items")
    items = r.get("auction_items", []) if r.get("success") else []
    if not items:
        text = "🔨 <b>АУКЦИОН</b>\n\nНет активных лотов."
        kb = [[InlineKeyboardButton(text="📤 ВЫСТАВИТЬ", callback_data="auction_sell")], [InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")]]
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await callback.answer()
        return
    text = "🔨 <b>АУКЦИОН</b>\n\n"
    kb = []
    for idx, it in enumerate(items):
        tl = max(0, int(it.get("end_time", 0) - time_module.time()))
        h, m = divmod(tl, 3600)
        text += f"📦 Лот #{idx+1}: {it.get('item', {}).get('name', '?')}\n💰 {it.get('current_bid', 0)}₽\n⏳ {int(h)}ч {int(m)}м\n\n"
        if it.get("seller_id") != user_id:
            kb.append([InlineKeyboardButton(text=f"💰 СТАВИТЬ (мин. {int(it.get('current_bid',0)*1.1)}₽)", callback_data=f"auction_bid_{idx}")])
    kb.append([InlineKeyboardButton(text="📤 ВЫСТАВИТЬ", callback_data="auction_sell")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "auction_sell")
async def auction_sell_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    inv_res = await api_call(user_id, "get_inventory")
    inv = inv_res.get("inventory", []) if inv_res.get("success") else []
    if not inv:
        await callback.answer("Нет товаров для выставления", show_alert=True)
        return
    text = "📤 <b>ВЫБЕРИ ТОВАР ДЛЯ АУКЦИОНА</b>\n\n"
    kb = []
    for i, it in enumerate(inv):
        kb.append([InlineKeyboardButton(text=f"📦 {it.get('name')} (~{it.get('market_price')}₽)", callback_data=f"auction_sell_item_{i}")])
    kb.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="auction_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("auction_sell_item_"))
async def auction_sell_item(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    item_idx = int(callback.data.split("_")[3])
    await state.update_data(auction_item_idx=item_idx)
    await state.set_state(Form.waiting_for_auction_price)
    await callback.message.answer("✍️ Введи начальную цену для лота (или 0 для рыночной):")
    await callback.answer()

@dp.message(StateFilter(Form.waiting_for_auction_price))
async def handle_auction_price(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        price = int(message.text.strip())
    except:
        await message.answer("❌ Введи число.")
        return
    data = await state.get_data()
    item_idx = data.get("auction_item_idx")
    r = await api_call(user_id, "add_auction_item", {"item_idx": item_idx, "start_price": price})
    if r.get("success"):
        await message.answer("✅ Лот выставлен на аукцион!")
    else:
        await message.answer(f"❌ {r.get('message', 'Ошибка')}")
    await state.clear()
    await message.answer("✅ Операция выполнена.\nИспользуйте кнопку 🔨 АУКЦИОН в главном меню, чтобы продолжить.")

@dp.callback_query(lambda c: c.data.startswith("auction_bid_"))
async def auction_bid_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    item_index = int(callback.data.split("_")[2])
    await state.update_data(auction_index=item_index)
    await state.set_state(Form.waiting_for_custom_amount)
    await callback.message.answer("✍️ Введи сумму ставки (минимальная ставка +10% от текущей цены):")
    await callback.answer()

@dp.message(StateFilter(Form.waiting_for_custom_amount))
async def handle_trade_or_auction_amount(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        amount = int(message.text.strip())
        if amount <= 0: raise ValueError
    except:
        await message.answer("❌ Введи положительное число.")
        return
    data = await state.get_data()
    if "trade_category" in data:
        cat = data.get("trade_category")
        action = data.get("trade_action")
        if action == "buy":
            r = await api_call(user_id, "buy_trading_item", {"category": cat, "amount": amount})
        else:
            r = await api_call(user_id, "sell_trading_item", {"category": cat, "amount": amount})
        if r.get("success"):
            await message.answer(f"✅ {r.get('message')}\n💰 Баланс: {r.get('balance', 0):,}₽", parse_mode="HTML")
        else:
            await message.answer(f"❌ {r.get('message', 'Ошибка')}")
        await state.clear()
        await message.answer("✅ Операция выполнена")
    elif "auction_index" in data:
        item_index = data.get("auction_index")
        r = await api_call(user_id, "bid_auction", {"item_index": item_index, "bid": amount})
        if r.get("success"):
            await message.answer(f"✅ {r.get('message')}\n💰 Баланс: {r.get('balance', 0):,}₽", parse_mode="HTML")
        else:
            await message.answer(f"❌ {r.get('message', 'Ошибка')}")
        await state.clear()
        await message.answer("✅ Операция выполнена.\n🔨 Для продолжения нажмите кнопку АУКЦИОН в главном меню.")
    else:
        await state.clear()
        await message.answer("❌ Неизвестная операция.")

@dp.callback_query(lambda c: c.data == "friends_menu")
async def friends_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "get_friends")
    if not r.get("success"):
        await callback.answer("Ошибка", show_alert=True)
        return
    friends = r.get("friends", [])
    if not friends:
        text = "👥 <b>ДРУЗЬЯ</b>\n\nУ тебя пока нет друзей!\n\nДобавить друга:\n<code>/friend add ник</code>"
        kb = [[InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")]]
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await callback.answer()
        return
    text = f"👥 <b>ТВОИ ДРУЗЬЯ ({len(friends)}):</b>\n\n"
    kb = []
    for fid in friends:
        text += f"• ID: {fid}\n"
        kb.append([InlineKeyboardButton(text=f"👤 ID:{fid}", callback_data=f"view_friend_{fid}")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("view_friend_"))
async def view_friend_callback(callback: CallbackQuery):
    friend_id = int(callback.data.split("_")[2])
    await callback.message.answer(f"👤 Профиль друга ID:{friend_id}\n(подробности позже)")
    await callback.answer()

@dp.message(Command('friend'))
async def friend_cmd(message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Используй: /friend add ник  или  /friend remove ник")
        return
    action = args[1]
    if action == "add" and len(args) >= 3:
        friend_name = args[2]
        r = await api_call(message.from_user.id, "add_friend", {"friend_name": friend_name})
        await message.answer(r.get("message", "Ошибка"))
    elif action == "remove" and len(args) >= 3:
        friend_name = args[2]
        user_info = await api_call(message.from_user.id, "get_player_by_nickname", {"nickname": friend_name})
        if user_info.get("success"):
            friend_id = user_info.get("player", {}).get("id")
            if friend_id:
                r = await api_call(message.from_user.id, "remove_friend", {"friend_id": friend_id})
                await message.answer(r.get("message", "Ошибка"))
            else:
                await message.answer("Игрок не найден")
        else:
            await message.answer("Игрок не найден")
    else:
        await message.answer("Неверная команда. Пример: /friend add Барыга")

@dp.callback_query(lambda c: c.data == "referral_menu")
async def referral_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "get_referral_data")
    if not r.get("success"):
        await callback.answer("Ошибка", show_alert=True)
        return
    invited = r.get("invited", [])
    count = r.get("count", 0)
    total_bonus = count * 10000
    text = (f"🔗 <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>\n\n"
            f"Твоя ссылка:\n<code>https://t.me/{BOT_USERNAME}?start=ref_{user_id}</code>\n\n"
            f"👥 Приглашено: {count} чел.\n"
            f"💰 Заработано: {total_bonus:,}₽\n"
            f"⭐ Бонус: +5 репутации за друга\n\n"
            f"<b>🎁 Награды:</b>\n"
            f"• Ты получаешь <b>10 000₽</b> за каждого друга\n"
            f"• Друг получает <b>5 000₽</b> стартового бонуса")
    kb = [[InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")]]
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "learning_menu")
async def learning_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "get_learning")
    completed = r.get("completed", []) if r.get("success") else []
    lessons = [
        {"id": 1, "title": "🚀 Основы", "reward": 500, "text": "Основы товарного бизнеса"},
        {"id": 2, "title": "📊 Рынок", "reward": 500, "text": "Анализ рынка и спрос"}
    ]
    text = "📚 <b>ОБУЧЕНИЕ ТОВАРНОМУ БИЗНЕСУ</b>\n\n"
    kb = []
    for lesson in lessons:
        status = "✅" if lesson["id"] in completed else "📖"
        text += f"{status} {lesson['title']} — {lesson['text']} (+{lesson['reward']}₽)\n"
        if lesson["id"] not in completed:
            kb.append([InlineKeyboardButton(text=f"ПРОЙТИ {lesson['title']}", callback_data=f"complete_lesson_{lesson['id']}_{lesson['reward']}")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("complete_lesson_"))
async def complete_lesson_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    lesson_id = int(parts[2])
    reward = int(parts[3])
    r = await api_call(user_id, "complete_lesson", {"lesson_id": lesson_id, "reward": reward})
    if r.get("success"):
        await callback.message.edit_text(f"✅ {r.get('message')}\n💰 Баланс: {r.get('balance', 0):,}₽", parse_mode="HTML")
        await callback.answer()
    else:
        await callback.answer(r.get("message", "Ошибка"), show_alert=True)

@dp.callback_query(lambda c: c.data == "leaderboard_menu")
async def leaderboard_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    r = await api_call(user_id, "get_leaderboard")
    if not r.get("success"):
        await callback.answer("Ошибка", show_alert=True)
        return
    top = r.get("leaderboard", [])
    if not top:
        text = "🏆 <b>ТОП-10 ПРОДАВЦОВ</b>\n\nПока нет данных."
    else:
        text = "🏆 <b>ТОП-10 ПРОДАВЦОВ</b>\n\n"
        for i, p in enumerate(top):
            name = p.get("nickname", f"ID:{p.get('id')}")
            sales = p.get("sales", 0)
            profit = p.get("profit", 0)
            text += f"{i+1}. {name} — {sales} продаж, {profit:,}₽\n"
    kb = [[InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="back_to_menu")]]
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "transfer_menu")
async def transfer_menu_callback(callback: CallbackQuery):
    await callback.message.answer("💸 <b>ПЕРЕВОД ДЕНЕГ</b>\n\nВведите команду:\n<code>/pay ник сумма</code>\n\nПример: /pay Барыга 5000", parse_mode="HTML")
    await callback.answer()

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000)

async def main():
    thread = threading.Thread(target=run_fastapi, daemon=True)
    thread.start()
    print("🚀 FastAPI сервер запущен на http://0.0.0.0:8000")
    print("🤖 Telegram бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())