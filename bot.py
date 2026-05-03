import random
import hashlib
import json
import os
import asyncio
import re
import time as time_module
from collections import defaultdict
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram import F
from openai import OpenAI

# ==================== КОНФИГ ====================
API_TOKEN = '8747685010:AAH8bN3x0fihSvUzVitijYQLHXeHFhIV5w4'
CHANNEL_LINK = '@vintagedrop61'
BOT_USERNAME = 'R-Game'
DEEPSEEK_API_KEY = "sk-8d6e9d7c39c84ec6a0ecba379674346d"

client_openai = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# ==================== ФАЙЛЫ ====================
REPUTATION_FILE = "reputation_data.json"
REFERRAL_FILE = "referrals.json"
LEARNING_FILE = "learning_progress.json"
HOUSES_FILE = "player_houses.json"
AVATARS_FILE = "player_avatars.json"

# ==================== НЕДВИЖИМОСТЬ ====================
HOUSES = [
    {
        "id": "room", "name": "🏚 Комната в общаге", "price": 0, "income_bonus": 0,
        "description": "Бесплатное жильё. Никаких бонусов.",
        "image_url": "AgACAgIAAxkBAAIBfmn3hNlqZXeSCAxLTetoN0kJMG4RAAKWGGsbaAW5SxNdXNthpgjFAQADAgADeQADOwQ"
    },
    {
        "id": "flat", "name": "🏢 Квартира", "price": 10000, "income_bonus": 150,
        "description": "Уютная квартира в спальном районе. +150₽ к ежедневному доходу.",
        "image_url": "AgACAgIAAxkBAAIBeGn3hGvVcFktYFQJP-YNnKti48v1AAKYGWsbUNy4SzN3yqU-dPZwAQADAgADeQADOwQ"
    },
    {
        "id": "house", "name": "🏠 Одноэтажный дом", "price": 35000, "income_bonus": 400,
        "description": "Просторный дом с участком и гаражом. +400₽ к ежедневному доходу.",
        "image_url": "AgACAgIAAxkBAAIBemn3hKeq-IxdQ6l6jB7sD10pQPbHAAKUGGsbaAW5S4jG5ecluTqMAQADAgADeQADOwQ"
    },
    {
        "id": "villa", "name": "🏰 Богатая вилла", "price": 100000, "income_bonus": 1200,
        "description": "Роскошная вилла с бассейном и садом. +1200₽ к ежедневному доходу.",
        "image_url": "AgACAgIAAxkBAAIBfGn3hME0a5rsH1wos1Qyy1AhsYAnAAKVGGsbaAW5SzyFR-E8--65AQADAgADeQADOwQ"
    },
    {
        "id": "yacht", "name": "🛥 Яхта", "price": 250000, "income_bonus": 3000,
        "description": "Собственная яхта у причала. +3000₽ к ежедневному доходу. Статус!",
        "image_url": "AgACAgIAAxkBAAIBfmn3hNlqZXeSCAxLTetoN0kJMG4RAAKWGGsbaAW5SxNdXNthpgjFAQADAgADeQADOwQ"
    },
]

# ==================== АВАТАРЫ ====================
AVATAR_PARTS = {
    "face": {"name": "😶 Лицо", "options": {"default": "Обычное", "smile": "Улыбка", "cool": "Крутое", "angry": "Злое", "surprised": "Удивлённое"}},
    "hair": {"name": "💇 Причёска", "options": {"none": "Лысый", "short": "Короткие", "long": "Длинные", "mohawk": "Ирокез", "cap": "Кепка"}},
    "clothes": {"name": "👕 Одежда", "options": {"tshirt": "Футболка", "hoodie": "Худи", "suit": "Костюм", "jacket": "Куртка", "rich": "Премиум"}},
    "accessory": {"name": "🕶 Аксессуары", "options": {"none": "Ничего", "glasses": "Очки", "sunglasses": "Тёмные очки", "chain": "Цепь", "headphones": "Наушники"}},
    "background": {"name": "🎨 Фон", "options": {"white": "Белый", "gray": "Серый", "blue": "Синий", "green": "Зелёный", "purple": "Фиолетовый"}},
}

DEFAULT_AVATAR = {"face": "default", "hair": "short", "clothes": "tshirt", "accessory": "none", "background": "white"}

def get_avatar_url(avatar_config):
    seed = hashlib.md5(str(avatar_config).encode()).hexdigest()[:10]
    return f"https://api.dicebear.com/7.x/pixel-art/svg?seed={seed}"

# ==================== СОВЕТЫ ====================
GAME_TIPS = {
    "after_buy": ["💡 Купил? Сразу публикуй!", "💡 Не держи товар долго — теряет в цене."],
    "after_publish": ["💡 Пока ждёшь — закупай ещё или иди на подработку!"],
    "during_chat": ["💡 Не соглашайся на первую цену.", "💡 Опиши товар подробно."],
    "after_sale": ["💡 Откладывай 30% прибыли на закуп."],
}

# ==================== ОБУЧЕНИЕ ====================
LESSONS = [
    {"id": 1, "title": "🚀 Основы товарного бизнеса", "text": "📚 <b>ОСНОВЫ ТОВАРКИ</b>\n\n<b>Товарный бизнес</b> — перепродажа вещей.\n\n<b>Где брать товар:</b>\n• Авито\n• Оптовые рынки (Садовод)\n• Китай (Taobao, 1688)\n• Секонд-хенды\n\n💰 Старт: от 1000₽", "reward": 500},
    {"id": 2, "title": "📊 Анализ рынка", "text": "📚 <b>АНАЛИЗ РЫНКА</b>\n\n<b>Сезонность:</b>\n• Осень — куртки\n• Зима — пуховики\n• Весна — демисезон\n• Лето — футболки\n\n💡 Покупай дёшево, продавай когда спрос высокий!", "reward": 500},
    {"id": 3, "title": "🏭 Поставщики", "text": "📚 <b>ПОСТАВЩИКИ</b>\n\n<b>Как не попасть на кидалово:</b>\n• Проси отзывы\n• Начни с малого заказа\n• Не вноси 100% предоплату\n\n⚠️ Слишком низкая цена = подозрительно!", "reward": 700},
    {"id": 4, "title": "💬 Общение с покупателями", "text": "📚 <b>ПРОДАЖИ</b>\n\n<b>Как продать дороже:</b>\n• Хорошие фото\n• Подробное описание\n• Быстрый ответ\n\n💡 Ставь цену на 20% выше — пространство для торга.", "reward": 700},
    {"id": 5, "title": "📈 Продвижение", "text": "📚 <b>ПРОДВИЖЕНИЕ</b>\n\n<b>Бесплатно:</b>\n• Обновляй каждые 24ч\n• Ключевые слова\n\n💡 5-10 объявлений = выше шанс продажи!", "reward": 1000},
]

# ==================== ПОСТАВЩИКИ ====================
SUPPLIERS = [
    {"name": "🏭 MegaStock", "rating": 9, "price_mult": 1.4, "scam_chance": 0, "emoji": "🏭", "desc": "Крупный оптовик. Надёжно, дорого."},
    {"name": "👕 OldGarage", "rating": 7, "price_mult": 1.15, "scam_chance": 10, "emoji": "👕", "desc": "Сток. Баланс цены и риска."},
    {"name": "🎒 Vintager", "rating": 5, "price_mult": 0.85, "scam_chance": 25, "emoji": "🎒", "desc": "Перекуп. Средне."},
    {"name": "💸 DumpPrice", "rating": 3, "price_mult": 0.55, "scam_chance": 50, "emoji": "💸", "desc": "Дёшево, рискованно."},
    {"name": "🎲 LuckyBag", "rating": 1, "price_mult": 0.3, "scam_chance": 75, "emoji": "🎲", "desc": "Почти наверняка кинет."},
]
VIP_SUPPLIER = {"name": "👑 PremiumStock", "rating": 10, "price_mult": 1.05, "scam_chance": 0, "emoji": "👑", "desc": "VIP. Лучшие цены."}

# ==================== ТОВАРЫ ====================
BASE_ITEMS = [
    {"cat": "👖 Джинсы", "name": "Levi's 501 Vintage", "base_price": 2000},
    {"cat": "👖 Джинсы", "name": "Carhartt WIP Denim", "base_price": 3500},
    {"cat": "👕 Худи", "name": "Adidas Originals Hoodie", "base_price": 2500},
    {"cat": "👕 Худи", "name": "Nike ACG Fleece", "base_price": 3000},
    {"cat": "🧥 Куртки", "name": "The North Face Nuptse", "base_price": 5000},
    {"cat": "🧥 Куртки", "name": "Alpha Industries MA-1", "base_price": 4000},
    {"cat": "👟 Кроссы", "name": "Nike Air Max 90", "base_price": 3500},
    {"cat": "👟 Кроссы", "name": "Adidas Samba OG", "base_price": 2800},
    {"cat": "🎒 Аксессуары", "name": "Stüssy Tote Bag", "base_price": 1500},
    {"cat": "🎒 Аксессуары", "name": "New Era 59Fifty Cap", "base_price": 1200},
    {"cat": "👕 Худи", "name": "Supreme Box Logo", "base_price": 1800},
    {"cat": "🧥 Куртки", "name": "Stone Island Soft Shell", "base_price": 6000},
]

CATEGORIES = ["👖 Джинсы", "👕 Худи", "🧥 Куртки", "👟 Кроссы", "🎒 Аксессуары"]

MARKET_EVENTS = [
    {"text": "📰 Хайп на винтажные джинсы!", "cat": "👖 Джинсы", "mult": 1.5},
    {"text": "📰 Дожди — спрос на куртки вырос!", "cat": "🧥 Куртки", "mult": 1.4},
    {"text": "📰 Все хотят кроссовки!", "cat": "👟 Кроссы", "mult": 1.5},
    {"text": "📰 Лето близко — джинсы падают.", "cat": "👖 Джинсы", "mult": 0.6},
    {"text": "📰 Авито комиссия 15% — все осторожны.", "cat": None, "mult": 0.8},
    {"text": "📰 Ретро-аксессуары в тренде!", "cat": "🎒 Аксессуары", "mult": 1.6},
]

# ==================== НЕЙРОКЛИЕНТЫ ====================
CLIENT_TYPES = {
    "angry": {
        "system_prompt": "Ты покупатель на Авито. РЕАЛЬНЫЙ ЧЕЛОВЕК. Недоверчивый, резкий. Торгуешься жёстко. Задавай вопросы о товаре. НЕ ПОВТОРЯЙСЯ. Отвечай 1-3 предложения как в чате.",
        "discount_range": (0.6, 0.8), "patience": 4, "remind_time": (120, 300)
    },
    "kind": {
        "system_prompt": "Ты покупатель на Авито. РЕАЛЬНЫЙ ЧЕЛОВЕК. Вежливый. Просишь скидку 5-15%. Задавай вопросы. Хвали товар. НЕ ПОВТОРЯЙСЯ. Отвечай 1-3 предложения как в чате.",
        "discount_range": (0.85, 0.95), "patience": 6, "remind_time": (180, 420)
    },
    "sly": {
        "system_prompt": "Ты покупатель-перекупщик. РЕАЛЬНЫЙ ЧЕЛОВЕК. Знаешь рынок. Хитрый. Аргументируешь цену. Задавай вопросы. НЕ ПОВТОРЯЙСЯ. Отвечай 1-3 предложения как в чате.",
        "discount_range": (0.7, 0.85), "patience": 5, "remind_time": (150, 360)
    }
}

# ==================== ПОДРАБОТКИ ====================
JOBS = [
    {"id": "flyers", "name": "📦 Расклейка объявлений", "duration": 60, "reward": 200, "emoji": "📦", "steps": ["📦 Взял пачку...", "🏃 Бежишь...", "📌 Клеишь...", "✅ Готово!"]},
    {"id": "delivery", "name": "🚗 Доставка заказов", "duration": 120, "reward": 500, "emoji": "🚗", "steps": ["🚗 Принял заказ...", "📦 Забираешь...", "🛵 Едешь...", "✅ Доставлено!"]},
    {"id": "freelance", "name": "💻 Фриланс", "duration": 300, "reward": 1200, "emoji": "💻", "steps": ["💻 Открыл редактор...", "🎨 Рисуешь...", "📤 Отправляешь...", "✅ Готово!"]},
    {"id": "shop", "name": "🏪 Работа в магазине", "duration": 180, "reward": 700, "emoji": "🏪", "steps": ["🏪 Пришёл...", "📦 Разбираешь...", "💰 Касса...", "✅ Смена окончена!"]},
    {"id": "photo", "name": "📸 Съёмка товаров", "duration": 90, "reward": 350, "emoji": "📸", "steps": ["📸 Настроил свет...", "📷 Снимаешь...", "💻 Обрабатываешь...", "✅ Готово!"]},
]

# ==================== РЕПУТАЦИЯ ====================
REPUTATION_LEVELS = {-100: "💀 ЧС", -50: "🔴 Ужасная", -10: "🟠 Плохая", 0: "🟡 Нейтральная", 25: "🟢 Хорошая", 50: "🔵 Отличная", 75: "🟣 Легенда", 100: "👑 Бог товарки"}
ACHIEVEMENTS = [
    {"id": "first_sale", "name": "🎯 Первая продажа", "target": 1, "reward": 5},
    {"id": "seller_10", "name": "📦 Продавец", "target": 10, "reward": 10},
    {"id": "profit_5000", "name": "💰 Навар", "target": 5000, "reward": 5},
]

# ==================== БОТ ====================
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class GameState(StatesGroup):
    playing = State()

# ==================== ХРАНИЛИЩА ====================
players = {}
referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False})
rep_data = {}
learning_data = {}
active_chats = {}
published_items = {}
last_bot_message = {}
pending_messages = defaultdict(list)
remind_timers = {}
shown_tips = defaultdict(set)
active_chat_for_user = {}
side_jobs = {}
player_houses = {}
player_avatars = {}

# ==================== ЗАГРУЗКА ====================
def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f: return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def load_all():
    global referral_data, rep_data, learning_data, player_houses, player_avatars
    referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False}, load_json(REFERRAL_FILE, {}))
    rep_data = load_json(REPUTATION_FILE, {})
    learning_data = load_json(LEARNING_FILE, {})
    player_houses = load_json(HOUSES_FILE, {})
    player_avatars = load_json(AVATARS_FILE, {})

load_all()

# ==================== ЧИСТКА СООБЩЕНИЙ ====================
async def del_prev(user_id):
    if user_id in last_bot_message:
        try: await bot.delete_message(user_id, last_bot_message[user_id])
        except: pass

async def del_user_msgs(user_id):
    for msg_id in pending_messages.get(user_id, []):
        try: await bot.delete_message(user_id, msg_id)
        except: pass
    pending_messages[user_id] = []

# Кнопка МЕНЮ для каждого сообщения
def menu_btn():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")]
    ])

async def send_msg(user_id, text, parse_mode="HTML", reply_markup=None):
    """Отправляет сообщение с кнопкой МЕНЮ."""
    await del_prev(user_id)
    await del_user_msgs(user_id)
    if reply_markup is None:
        reply_markup = menu_btn()
    msg = await bot.send_message(user_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    last_bot_message[user_id] = msg.message_id
    return msg

async def edit_msg(message, text, parse_mode="HTML", reply_markup=None):
    """Редактирует сообщение. Если не получается — отправляет новое."""
    await del_user_msgs(message.chat.id)
    if reply_markup is None:
        reply_markup = menu_btn()
    try:
        await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        print(f"Edit error: {e}")
        # Если не можем отредактировать — отправляем новое
        await send_msg(message.chat.id, text, parse_mode=parse_mode, reply_markup=reply_markup)

async def send_avatar_photo(user_id, caption="", reply_markup=None):
    """Отправляет фото аватара или текстовую карточку."""
    avatar = get_player_avatar(user_id)
    avatar_url = get_avatar_url(avatar)
    
    if reply_markup is None:
        reply_markup = menu_btn()
    
    try:
        msg = await bot.send_photo(user_id, avatar_url, caption=caption, parse_mode="HTML", reply_markup=reply_markup)
        return msg
    except Exception as e:
        print(f"Avatar photo error: {e}")
        # Текстовая карточка
        parts = []
        for key, data in AVATAR_PARTS.items():
            val = avatar.get(key, "default")
            name = data["options"].get(val, val)
            parts.append(f"{data['name']}: {name}")
        text_card = f"👤 <b>ТВОЙ ПЕРСОНАЖ</b>\n\n" + "\n".join(parts) + "\n\n<i>Редактируй персонажа ниже 👇</i>"
        if caption: text_card = caption
        await del_prev(user_id)
        await del_user_msgs(user_id)
        msg = await bot.send_message(user_id, text_card, parse_mode="HTML", reply_markup=reply_markup)
        last_bot_message[user_id] = msg.message_id
        return msg

# ==================== РЕФЕРАЛЫ ====================
def gen_ref(user_id): return hashlib.md5(str(user_id).encode()).hexdigest()[:8]
def ref_link(user_id): return f"https://t.me/{BOT_USERNAME}?start=ref_{gen_ref(user_id)}"
def top_refs(limit=10):
    s = [(uid, len(d["invited"])) for uid, d in referral_data.items()]
    s.sort(key=lambda x: x[1], reverse=True); return s[:limit]
def is_vip(user_id): return str(user_id) in [str(uid) for uid, _ in top_refs(3)]

# ==================== РЕПУТАЦИЯ ====================
def get_rep(user_id):
    uid = str(user_id)
    if uid not in rep_data:
        rep_data[uid] = {"score": 0, "total_sales": 0, "total_profit": 0, "max_balance": 0, "scam_survived": 0, "angry_deals": 0, "haggle_wins": 0, "lessons_completed": 0, "achievements": [], "rep_history": []}
        save_json(REPUTATION_FILE, rep_data)
    return rep_data[uid]

def rep_level(score):
    for t in sorted(REPUTATION_LEVELS.keys(), reverse=True):
        if score >= t: return REPUTATION_LEVELS[t]
    return REPUTATION_LEVELS[-100]

def add_rep(user_id, amount, reason=""):
    u = get_rep(user_id)
    u["score"] = max(-100, min(100, u["score"] + amount))
    save_json(REPUTATION_FILE, rep_data)

def rep_mult(score):
    if score >= 75: return {"supplier_discount": 0.85, "scam_reduce": 0.2, "haggle_bonus": 0.25}
    elif score >= 50: return {"supplier_discount": 0.90, "scam_reduce": 0.4, "haggle_bonus": 0.15}
    elif score >= 25: return {"supplier_discount": 0.95, "scam_reduce": 0.6, "haggle_bonus": 0.05}
    elif score >= 0: return {"supplier_discount": 1.0, "scam_reduce": 0.8, "haggle_bonus": 0.0}
    else: return {"supplier_discount": 1.5, "scam_reduce": 1.5, "haggle_bonus": -0.3}

def check_ach(user_id, pd=None):
    u = get_rep(user_id)
    if pd: u["total_sales"] = pd.get("items_sold", 0); u["total_profit"] = pd.get("total_earned", 0)
    new_a = []
    for a in ACHIEVEMENTS:
        if a["id"] in u["achievements"]: continue
        earn = False
        if a["id"] == "first_sale" and u["total_sales"] >= 1: earn = True
        elif a["id"] == "seller_10" and u["total_sales"] >= 10: earn = True
        elif a["id"] == "profit_5000" and u["total_profit"] >= 5000: earn = True
        if earn: u["achievements"].append(a["id"]); add_rep(user_id, a["reward"]); new_a.append(a)
    save_json(REPUTATION_FILE, rep_data)
    return new_a

# ==================== ОБУЧЕНИЕ ====================
def get_learning(user_id):
    uid = str(user_id)
    if uid not in learning_data: learning_data[uid] = {"completed": [], "current": 1}; save_json(LEARNING_FILE, learning_data)
    return learning_data[uid]

def complete_lesson(user_id, lesson_id):
    u = get_rep(user_id); l = get_learning(user_id)
    if lesson_id not in l["completed"]:
        l["completed"].append(lesson_id); u["lessons_completed"] = len(l["completed"])
        save_json(LEARNING_FILE, learning_data); save_json(REPUTATION_FILE, rep_data)
        lesson = next((ls for ls in LESSONS if ls["id"] == lesson_id), None)
        if lesson and user_id in players: players[user_id]["balance"] += lesson["reward"]; add_rep(user_id, 3)
        check_ach(user_id); return True
    return False

# ==================== НЕДВИЖИМОСТЬ ====================
def get_player_house(user_id):
    uid = str(user_id)
    if uid not in player_houses: player_houses[uid] = "room"; save_json(HOUSES_FILE, player_houses)
    return player_houses[uid]

def buy_house(user_id, house_id):
    uid = str(user_id)
    house = next((h for h in HOUSES if h["id"] == house_id), None)
    if not house: return False, "Дом не найден"
    if get_player_house(user_id) == house_id: return False, "Уже есть!"
    p = get_player(user_id)
    if p["balance"] < house["price"]: return False, f"Недостаточно денег! Нужно {house['price']}₽"
    p["balance"] -= house["price"]
    player_houses[uid] = house_id
    save_json(HOUSES_FILE, player_houses)
    return True, f"✅ Куплен {house['name']}!"

# ==================== АВАТАРЫ ====================
def get_player_avatar(user_id):
    uid = str(user_id)
    if uid not in player_avatars: player_avatars[uid] = DEFAULT_AVATAR.copy(); save_json(AVATARS_FILE, player_avatars)
    return player_avatars[uid]

def update_avatar_part(user_id, part, value):
    uid = str(user_id)
    if uid not in player_avatars: player_avatars[uid] = DEFAULT_AVATAR.copy()
    player_avatars[uid][part] = value
    save_json(AVATARS_FILE, player_avatars)

# ==================== ИГРА ====================
def get_player(user_id):
    if user_id not in players:
        r = get_rep(user_id)
        players[user_id] = {"balance": 5000, "reputation": max(0, r["score"]), "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0, "items_sold": r["total_sales"], "scam_times": r["scam_survived"], "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
    return players[user_id]

def item_price(base, sup): return int(base * sup["price_mult"])
def market_price(base, demand): return int(base * demand * random.uniform(0.9, 1.3))
def daily_event(): return random.choice(MARKET_EVENTS) if random.random() < 0.6 else None

def apply_event(p, event):
    if event["cat"]: p["market_demand"][event["cat"]] = max(0.3, min(3.0, p["market_demand"][event["cat"]] * event["mult"]))
    else:
        for cat in CATEGORIES: p["market_demand"][cat] = max(0.3, min(3.0, p["market_demand"][cat] * event["mult"]))

def fmt_demand(p):
    lines = []
    for cat, mult in p["market_demand"].items():
        emoji = "🔥" if mult >= 1.5 else "📈" if mult >= 1.2 else "➡️" if mult >= 0.8 else "📉" if mult >= 0.5 else "💀"
        lines.append(f"{emoji} {cat}: x{mult:.1f}")
    return "\n".join(lines)

def get_active_buyers_count(user_id):
    return sum(1 for c in active_chats.values() if c["user_id"] == user_id and not c["finished"])

def main_kb(user_id=None):
    buyers_count = get_active_buyers_count(user_id) if user_id else 0
    chat_label = f"💬 ЧАТЫ ({buyers_count})" if buyers_count > 0 else "💬 ЧАТЫ"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏭 ЗАКУПИТЬСЯ", callback_data="action_buy")],
        [InlineKeyboardButton(text="📦 ИНВЕНТАРЬ", callback_data="action_inventory")],
        [InlineKeyboardButton(text=chat_label, callback_data="action_chats"),
         InlineKeyboardButton(text="💼 ЗАРАБОТОК", callback_data="action_job")],
        [InlineKeyboardButton(text="🏠 НЕДВИЖИМОСТЬ", callback_data="action_houses"),
         InlineKeyboardButton(text="👤 АВАТАР", callback_data="action_avatar")],
        [InlineKeyboardButton(text="📚 ОБУЧЕНИЕ", callback_data="action_learn"),
         InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="action_stats")],
        [InlineKeyboardButton(text="🏆 РЕПУТАЦИЯ", callback_data="action_rep_menu"),
         InlineKeyboardButton(text="🔗 РЕФЕРАЛЫ", callback_data="action_ref_menu")],
        [InlineKeyboardButton(text="📈 СПРОС", callback_data="action_demand")],
        [InlineKeyboardButton(text="⏩ СЛЕД. ДЕНЬ", callback_data="action_nextday"),
         InlineKeyboardButton(text="🏁 ЗАВЕРШИТЬ", callback_data="action_end")],
    ])

# ==================== НЕЙРОКЛИЕНТЫ ====================
def first_msg(client_type, item_name, price, offer):
    msgs = {
        "angry": [f"Здравствуйте! {item_name}. Расскажите о состоянии? {price}₽ — окончательная цена?", f"Привет! Интересует {item_name}. Что по состоянию?"],
        "kind": [f"Добрый день! Очень заинтересовал {item_name}. Расскажите подробнее?", f"Здравствуйте! {item_name} — то что ищу! Состояние хорошее?"],
        "sly": [f"Привет! По {item_name}. Что по состоянию? И готовы обсуждать цену?", f"Здорово! {item_name} интересует. Расскажи что да как."],
    }
    return random.choice(msgs.get(client_type, msgs["kind"]))

async def send_buyer(user_id, buyer_id, client_type, item_name, price, is_reminder=False):
    client = CLIENT_TYPES[client_type]
    chat_key = f"{user_id}_{buyer_id}"
    
    if not is_reminder:
        rm = rep_mult(get_rep(user_id)["score"])
        discount = random.uniform(*client["discount_range"]) + rm["haggle_bonus"]
        discount = max(0.3, min(0.95, discount))
        offer = int(price * discount); offer = (offer // 100) * 100 + 99
        if offer < 100: offer = price // 2
        
        msg = first_msg(client_type, item_name, price, offer)
        active_chats[chat_key] = {"user_id": user_id, "buyer_id": buyer_id, "client_type": client_type, "item": item_name, "price": price, "offer": offer, "history": [{"role": "system", "content": client["system_prompt"]}, {"role": "assistant", "content": msg}], "round": 1, "max_rounds": client["patience"], "finished": False, "reminders_sent": 0, "max_reminders": 2}
        
        await send_msg(user_id, f"📩 <b>НОВОЕ СООБЩЕНИЕ</b>\n\n👤 <b>Покупатель #{buyer_id}</b>\n📦 {item_name}\n\n💬 {msg}\n\n<i>Ответь на это сообщение чтобы начать диалог</i>")
        
        if client["remind_time"]:
            task = asyncio.create_task(do_remind(user_id, buyer_id, random.randint(*client["remind_time"])))
            remind_timers[chat_key] = task
    else:
        chat = active_chats.get(chat_key)
        if not chat or chat["finished"]: return
        msg = f"Извините, я всё ещё жду ответ по {item_name}. Вы тут?"
        chat["history"].append({"role": "assistant", "content": msg}); chat["reminders_sent"] += 1
        await send_msg(user_id, f"🔔 <b>Покупатель #{buyer_id}</b>\n📦 {item_name}\n\n💬 {msg}")
        if chat["reminders_sent"] < chat["max_reminders"]:
            task = asyncio.create_task(do_remind(user_id, buyer_id, random.randint(*client["remind_time"])))
            remind_timers[chat_key] = task

async def do_remind(user_id, buyer_id, delay):
    await asyncio.sleep(delay)
    chat_key = f"{user_id}_{buyer_id}"
    chat = active_chats.get(chat_key)
    if chat and not chat["finished"] and chat["reminders_sent"] < chat["max_reminders"]:
        await send_buyer(user_id, buyer_id, chat["client_type"], chat["item"], chat["price"], is_reminder=True)

async def spawn_buyers(user_id):
    await asyncio.sleep(random.randint(60, 180))
    if user_id not in published_items or not published_items[user_id]: return
    pub = published_items[user_id]; item = pub["item"]
    n = random.randint(1, 3)
    if rep_mult(get_rep(user_id)["score"])["haggle_bonus"] > 0.1: n = min(3, n + 1)
    types = random.choices(list(CLIENT_TYPES.keys()), k=n)
    await send_msg(user_id, f"📱 <b>ОБЪЯВЛЕНИЕ РАБОТАЕТ!</b>\n\n📦 {item['name']}\n💰 {item['market_price']}₽\n👥 Пишут: <b>{n}</b> чел.\n\n<i>Отвечай на сообщения!</i>")
    
    for i, bt in enumerate(types):
        await asyncio.sleep(random.randint(5, 20))
        await send_buyer(user_id, i + 1, bt, item["name"], item["market_price"])

async def complete_sale(user_id, buyer_id, message=None):
    chat_key = f"{user_id}_{buyer_id}"
    chat = active_chats.get(chat_key)
    if not chat: return None
    p = get_player(user_id); item_name = chat["item"]; final = chat["offer"]
    sold = None
    if user_id in published_items and published_items[user_id]:
        sold = published_items[user_id].get("item")
        if sold and sold["name"] == item_name: published_items[user_id] = None
        else: sold = None
    if not sold:
        for i, inv in enumerate(p["inventory"]):
            if inv["name"] == item_name: sold = p["inventory"].pop(i); break
    if not sold:
        if message: await send_msg(user_id, "❌ Товар не найден.")
        return None
    profit = final - sold["buy_price"]
    p["balance"] += final; p["total_earned"] += profit; p["items_sold"] += 1
    p["stat_earned_today"] += profit; p["stat_sold_today"] += 1
    p["reputation"] = min(100, p["reputation"] + 5)
    add_rep(user_id, random.randint(2, 5))
    if chat["client_type"] == "angry": get_rep(user_id)["angry_deals"] += 1
    if final > sold["market_price"] * 0.9: get_rep(user_id)["haggle_wins"] += 1
    check_ach(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"]})
    save_json(REPUTATION_FILE, rep_data)
    if chat_key in remind_timers: remind_timers[chat_key].cancel(); del remind_timers[chat_key]
    chat["finished"] = True
    if user_id in active_chat_for_user: del active_chat_for_user[user_id]
    if message:
        await send_msg(user_id, f"🎉 <b>ПРОДАНО!</b>\n\n📦 {item_name}\n💰 Цена: {final}₽\n💵 Прибыль: {profit}₽\n💼 Баланс: {p['balance']}₽\n⭐ Репутация: {p['reputation']}/100")
    return profit

# ==================== КОМАНДЫ ====================
@dp.message(Command('start'))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id; args = message.text.split()
    
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_code = args[1][4:]
        for uid in referral_data:
            if gen_ref(uid) == ref_code and uid != str(user_id):
                referral_data[uid]["invited"].append(user_id)
                save_json(REFERRAL_FILE, dict(referral_data))
                if int(uid) in players: players[int(uid)]["balance"] += 500
                try: await bot.send_message(int(uid), "🎉 Новый реферал! +500₽", parse_mode="HTML")
                except: pass
                break
    
    p = players.get(user_id)
    await del_user_msgs(user_id)
    
    if p and p.get("day", 0) > 0:
        house = next((h for h in HOUSES if h["id"] == get_player_house(user_id)), HOUSES[0])
        await send_msg(user_id, f"👋 <b>С ВОЗВРАЩЕНИЕМ!</b>\n📅 День {p['day']} | 💰 {p['balance']}₽\n🏠 {house['name']}\n⭐ {rep_level(get_rep(user_id)['score'])}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 ПРОДОЛЖИТЬ", callback_data="continue_game")],
            [InlineKeyboardButton(text="👤 АВАТАР", callback_data="action_avatar")],
            [InlineKeyboardButton(text="📚 ОБУЧЕНИЕ", callback_data="action_learn")],
            [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")],
        ]))
    else:
        await send_msg(user_id, "🎮 <b>RESELL TYCOON</b>\n\nТренажёр товарного бизнеса!\nПокупай недвижимость, настраивай аватара, общайся с нейроклиентами!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 НАЧАТЬ ИГРУ", callback_data="start_new_game")],
            [InlineKeyboardButton(text="👤 НАСТРОИТЬ АВАТАРА", callback_data="action_avatar")],
            [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")],
        ]))

@dp.message(Command('play'))
async def play_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id; await del_user_msgs(user_id)
    r = get_rep(user_id)
    players[user_id] = {"balance": 5000, "reputation": max(0, r["score"]), "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0, "items_sold": r["total_sales"], "scam_times": r["scam_survived"], "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
    p = players[user_id]
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    await state.set_state(GameState.playing)
    house = next((h for h in HOUSES if h["id"] == get_player_house(user_id)), HOUSES[0])
    await send_msg(user_id, f"🌟 <b>ДЕНЬ 1</b>\n💰 5 000₽\n🏠 {house['name']}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}\n\n👇 1. 🏭 Закупись → 2. 📦 Инвентарь → 3. Опубликуй → 4. 💬 Отвечай!", reply_markup=main_kb(user_id))

@dp.message(Command('check'))
async def check_job_cmd(message: types.Message):
    user_id = message.from_user.id; await del_user_msgs(user_id)
    if user_id not in side_jobs or side_jobs[user_id].get("done", True):
        return await send_msg(user_id, "💼 Нет активной работы.\nЗайди в 💼 ЗАРАБОТОК!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💼 ЗАРАБОТОК", callback_data="action_job")],
            [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")],
        ]))
    
    job_data = side_jobs[user_id]; job = JOBS[job_data["job_type"]]
    elapsed = int(time_module.time() - job_data["start_time"])
    
    if elapsed >= job["duration"] and not job_data["done"]:
        job_data["done"] = True
        if user_id in players: players[user_id]["balance"] += job["reward"]; players[user_id]["stat_earned_today"] += job["reward"]
        await send_msg(user_id, f"✅ <b>РАБОТА ЗАВЕРШЕНА!</b>\n\n{job['emoji']} {job['name']}\n💰 Заработано: {job['reward']}₽\n💼 Баланс: {players[user_id]['balance']}₽\n\n<i>Можешь взять новую подработку!</i>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💼 ЕЩЁ ЗАРАБОТОК", callback_data="action_job")],
            [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")],
        ]))
    else:
        remaining = job["duration"] - elapsed
        current_step = min(len(job["steps"]) - 1, int(elapsed / (job["duration"] / len(job["steps"]))))
        await send_msg(user_id, f"⏳ <b>РАБОТАЕМ...</b>\n\n{job['emoji']} {job['name']}\n{job['steps'][current_step]}\n\nОсталось: {remaining} сек.\n💰 Награда: {job['reward']}₽\n\n<i>Напиши /check позже</i>")

# ==================== ОСНОВНОЙ ЧАТ ====================
@dp.message(StateFilter(GameState.playing))
async def handle_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id; text = message.text.strip()
    pending_messages[user_id].append(message.message_id)
    
    if user_id in active_chat_for_user:
        chat_key = active_chat_for_user[user_id]
        if chat_key in active_chats and not active_chats[chat_key]["finished"]:
            await process_chat(user_id, chat_key, text, message); return
    
    for key, chat in active_chats.items():
        if chat["user_id"] == user_id and not chat["finished"]:
            await process_chat(user_id, key, text, message); return

async def process_chat(user_id, chat_key, text, message):
    chat = active_chats[chat_key]; buyer_id = chat["buyer_id"]
    client = CLIENT_TYPES[chat["client_type"]]
    chat["history"].append({"role": "user", "content": text}); chat["round"] += 1
    
    for w in ["продано", "продаю", "согласен", "договорились", "по рукам", "забирай", "отдаю", "продам", "бери", "хорошо", "ок", "давай"]:
        if w in text.lower():
            chat["finished"] = True
            if chat_key in remind_timers: remind_timers[chat_key].cancel()
            if user_id in active_chat_for_user: del active_chat_for_user[user_id]
            await send_msg(user_id, f"👤 <b>Покупатель #{buyer_id}:</b> Отлично! Договорились на {chat['offer']}₽. Когда можно забрать?")
            await complete_sale(user_id, buyer_id, message); return
    
    if chat["round"] >= 5:
        chat["finished"] = True
        if chat_key in remind_timers: remind_timers[chat_key].cancel()
        if user_id in active_chat_for_user: del active_chat_for_user[user_id]
        if random.random() < 0.6:
            await send_msg(user_id, f"👤 <b>Покупатель #{buyer_id}:</b> Ладно, давайте {chat['offer']}₽. Договорились. Когда забирать?")
            await complete_sale(user_id, buyer_id, message)
        else:
            await send_msg(user_id, f"👤 <b>Покупатель #{buyer_id}:</b> Извините, я передумал.\n\n👋 Диалог завершён.")
        return
    
    try:
        system_prompt = client["system_prompt"] + f"\n\nКонтекст: Товар - {chat['item']}. Твоя цена: {chat['offer']}₽, продавец хочет {chat['price']}₽. Сообщение {chat['round']} из 5. Веди ЕСТЕСТВЕННЫЙ диалог."
        messages = [{"role": "system", "content": system_prompt}] + chat["history"][-3:]
        resp = client_openai.chat.completions.create(model="deepseek-chat", messages=messages, temperature=0.7, max_tokens=100)
        ai_msg = resp.choices[0].message.content
    except:
        fallbacks = {"angry": [f"Слушай, {chat['offer']}₽. Берёшь?"], "kind": [f"Ну так что? {chat['offer']}₽?"], "sly": [f"Давай {chat['offer']}₽ и разойдёмся."]}
        ai_msg = random.choice(fallbacks.get(chat["client_type"], [f"{chat['offer']}₽."]))
    
    chat["history"].append({"role": "assistant", "content": ai_msg})
    
    prices = re.findall(r'(\d{3,5})₽', ai_msg)
    for p in prices:
        new_price = int(p)
        if chat["offer"] < new_price <= chat["price"]: chat["offer"] = new_price
    
    finished = False
    for w in ["беру", "договорились", "по рукам", "забираю", "согласен", "давай", "идёт"]:
        if w in ai_msg.lower() and "?" not in ai_msg.lower(): finished = True; break
    
    if finished:
        chat["finished"] = True
        if chat_key in remind_timers: remind_timers[chat_key].cancel()
        if user_id in active_chat_for_user: del active_chat_for_user[user_id]
        await send_msg(user_id, f"👤 <b>Покупатель #{buyer_id}:</b> {ai_msg}")
        await complete_sale(user_id, buyer_id, message)
    else:
        await send_msg(user_id, f"👤 <b>Покупатель #{buyer_id}:</b> {ai_msg}\n\n<i>Осталось сообщений: {5 - chat['round']}</i>")

# ==================== ЧАТЫ ====================
@dp.callback_query(F.data == "action_chats", StateFilter(GameState.playing))
async def show_chats(callback: CallbackQuery):
    user_id = callback.from_user.id
    active_list = [(k, c) for k, c in active_chats.items() if c["user_id"] == user_id and not c["finished"]]
    if not active_list:
        return await edit_msg(callback.message, "💬 <b>ЧАТЫ</b>\n\nНет активных диалогов.\nОпубликуй товар в 📦 Инвентаре!")
    txt = f"💬 <b>ЧАТЫ ({len(active_list)}):</b>\n\n"
    kb = []
    for key, chat in active_list:
        txt += f"👤 <b>#{chat['buyer_id']}</b> | 📦 {chat['item']}\n💰 {chat['offer']}₽\n\n"
        kb.append([InlineKeyboardButton(text=f"👤 Покупатель #{chat['buyer_id']} — {chat['item']}", callback_data=f"open_chat_{user_id}_{chat['buyer_id']}")])
    kb.append([InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("open_chat_"))
async def open_chat(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id = int(parts[2]); buyer_id = int(parts[3])
    chat_key = f"{user_id}_{buyer_id}"
    if chat_key not in active_chats or active_chats[chat_key]["finished"]: return await callback.answer("Диалог завершён")
    active_chat_for_user[user_id] = chat_key
    await state.set_state(GameState.playing)
    chat = active_chats[chat_key]
    await send_msg(user_id, f"💬 <b>ЧАТ С ПОКУПАТЕЛЕМ #{buyer_id}</b>\n\n📦 {chat['item']}\n💰 Твоя цена: {chat['price']}₽ | Предложение: {chat['offer']}₽\n\n<i>Пиши «продано» или «согласен» чтобы продать!</i>")
    await callback.answer("Чат открыт!")

# ==================== НЕДВИЖИМОСТЬ (КАТАЛОГ) ====================
@dp.callback_query(F.data == "action_houses", StateFilter(GameState.playing))
async def show_houses_catalog(callback: CallbackQuery, page: int = 0):
    user_id = callback.from_user.id; current_id = get_player_house(user_id); p = get_player(user_id)
    if page < 0: page = 0
    if page >= len(HOUSES): page = len(HOUSES) - 1
    house = HOUSES[page]; owned = current_id == house["id"]
    
    if owned:
        status_text = "✅ <b>ЭТО ТВОЁ ЖИЛЬЁ</b>"; action_btn = None
    else:
        if p["balance"] >= house["price"]:
            status_text = f"💰 <b>Цена: {house['price']}₽</b> (хватает!)"; action_btn = InlineKeyboardButton(text=f"🛒 КУПИТЬ ЗА {house['price']}₽", callback_data=f"buy_house_{house['id']}")
        else:
            need = house["price"] - p["balance"]; status_text = f"💰 <b>Цена: {house['price']}₽</b>\n❌ Не хватает: {need}₽"; action_btn = None
    
    txt = f"🏠 <b>КАТАЛОГ НЕДВИЖИМОСТИ</b>\n📄 {page + 1} из {len(HOUSES)}\n\n{house['name']}\n{house['description']}\n\n{status_text}\n\n💼 Баланс: {p['balance']}₽\n🏠 Жильё: {next((h['name'] for h in HOUSES if h['id'] == current_id), 'Нет')}"
    
    nav_buttons = []
    if page > 0: nav_buttons.append(InlineKeyboardButton(text="⬅️ НАЗАД", callback_data=f"house_page_{page - 1}"))
    if page < len(HOUSES) - 1: nav_buttons.append(InlineKeyboardButton(text="ВПЕРЁД ➡️", callback_data=f"house_page_{page + 1}"))
    
    kb = []
    if nav_buttons: kb.append(nav_buttons)
    if action_btn: kb.append([action_btn])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    
    try:
        if house["image_url"].startswith("AgAC"):
            msg = await bot.send_photo(user_id, house["image_url"], caption=txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        else:
            msg = await bot.send_photo(user_id, house["image_url"], caption=txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await del_prev(user_id); last_bot_message[user_id] = msg.message_id
        try: await callback.message.delete()
        except: pass
    except Exception as e:
        print(f"House photo error: {e}")
        await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("house_page_"), StateFilter(GameState.playing))
async def house_page_btn(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    await show_houses_catalog(callback, page)

@dp.callback_query(F.data.startswith("buy_house_"), StateFilter(GameState.playing))
async def buy_house_btn(callback: CallbackQuery):
    user_id = callback.from_user.id; house_id = callback.data.replace("buy_house_", "")
    success, msg = buy_house(user_id, house_id)
    if success:
        current_page = next((i for i, h in enumerate(HOUSES) if h["id"] == house_id), 0)
        await callback.answer(msg)
        await show_houses_catalog(callback, current_page)
    else:
        await callback.answer(msg, show_alert=True)

# ==================== АВАТАР (ИСПРАВЛЕНО) ====================
@dp.callback_query(F.data == "action_avatar")
async def show_avatar_menu_start(callback: CallbackQuery):
    """Показывает аватар — работает и в игре и без неё."""
    user_id = callback.from_user.id
    avatar = get_player_avatar(user_id)
    
    txt = "👤 <b>ТВОЙ ПИКСЕЛЬНЫЙ ПЕРСОНАЖ</b>\n\n<i>Выбери что изменить:</i>"
    
    kb = []
    for part_key, part_data in AVATAR_PARTS.items():
        current_value = avatar.get(part_key, "default")
        current_name = part_data["options"].get(current_value, current_value)
        kb.append([InlineKeyboardButton(
            text=f"{part_data['name']}: {current_name}",
            callback_data=f"avatar_part_{part_key}"
        )])
    
    # Проверяем состояние игры для правильной кнопки возврата
    p = players.get(user_id)
    if p and p.get("day", 0) > 0:
        kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    else:
        kb.append([InlineKeyboardButton(text="🏠 НА ГЛАВНУЮ", callback_data="back_to_start")])
    
    # Отправляем фото или текстовую карточку
    await send_avatar_photo(user_id, txt, InlineKeyboardMarkup(inline_keyboard=kb))
    
    # Удаляем сообщение с кнопкой меню
    try: await callback.message.delete()
    except: pass
    
    await callback.answer()

@dp.callback_query(F.data.startswith("avatar_part_"))
async def show_avatar_options(callback: CallbackQuery):
    user_id = callback.from_user.id
    part_key = callback.data.replace("avatar_part_", "")
    part_data = AVATAR_PARTS.get(part_key)
    
    if not part_data:
        return await callback.answer("Ошибка!")
    
    avatar = get_player_avatar(user_id)
    
    txt = f"👤 <b>ВЫБЕРИ {part_data['name'].upper()}</b>"
    
    kb = []
    for opt_key, opt_name in part_data["options"].items():
        selected = "✅ " if avatar.get(part_key) == opt_key else ""
        kb.append([InlineKeyboardButton(
            text=f"{selected}{opt_name}",
            callback_data=f"set_avatar_{part_key}_{opt_key}"
        )])
    kb.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="action_avatar")])
    
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("set_avatar_"))
async def set_avatar_part(callback: CallbackQuery):
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    
    if len(parts) >= 4:
        part_key = parts[2]
        opt_key = "_".join(parts[3:])
        
        if part_key in AVATAR_PARTS and opt_key in AVATAR_PARTS[part_key]["options"]:
            update_avatar_part(user_id, part_key, opt_key)
            await callback.answer("✅ Обновлено!")
            await show_avatar_options(callback)
        else:
            await callback.answer("❌ Ошибка данных")
    else:
        await callback.answer("❌ Ошибка данных")

# ==================== ПОДРАБОТКИ ====================
async def job_animation(user_id, job_idx):
    job = JOBS[job_idx]
    interval = job["duration"] / len(job["steps"])
    for i, step in enumerate(job["steps"]):
        await asyncio.sleep(interval)
        if user_id not in side_jobs or side_jobs[user_id].get("done", True): return
        if i < len(job["steps"]) - 1:
            try: await send_msg(user_id, f"💼 {job['emoji']} {job['name']}\n\n{step}")
            except: pass
    if user_id in side_jobs and not side_jobs[user_id].get("done", True):
        side_jobs[user_id]["done"] = True
        if user_id in players: players[user_id]["balance"] += job["reward"]
        await send_msg(user_id, f"✅ <b>РАБОТА ЗАВЕРШЕНА!</b>\n💰 +{job['reward']}₽")

@dp.callback_query(F.data == "action_job", StateFilter(GameState.playing))
async def show_jobs(callback: CallbackQuery):
    user_id = callback.from_user.id
    kb = []
    for j, job in enumerate(JOBS):
        kb.append([InlineKeyboardButton(text=f"{job['emoji']} {job['name']} — {job['reward']}₽ ({job['duration']} сек)", callback_data=f"start_job_{j}")])
    kb.append([InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")])
    
    active_job = ""
    if user_id in side_jobs and not side_jobs[user_id].get("done", True):
        job_data = side_jobs[user_id]; job = JOBS[job_data["job_type"]]
        elapsed = int(time_module.time() - job_data["start_time"]); remaining = max(0, job["duration"] - elapsed)
        active_job = f"\n\n⏳ <b>Работаю:</b> {job['emoji']} {job['name']}\nОсталось: {remaining} сек.\nНапиши /check чтобы проверить"
    
    await edit_msg(callback.message, f"💼 <b>ПОДРАБОТКИ</b>\n\nЗаработай пока ждёшь покупателей!\nВыбери работу:{active_job}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("start_job_"))
async def start_job(callback: CallbackQuery):
    user_id = callback.from_user.id; job_idx = int(callback.data.split("_")[2])
    job = JOBS[job_idx]
    if user_id in side_jobs and not side_jobs[user_id].get("done", True):
        remaining = job["duration"] - int(time_module.time() - side_jobs[user_id]["start_time"])
        if remaining > 0: return await callback.answer(f"Уже работаешь! Осталось {remaining} сек.")
    side_jobs[user_id] = {"job_type": job_idx, "start_time": time_module.time(), "done": False}
    await send_msg(user_id, f"💼 <b>ПРИСТУПИЛ!</b>\n{job['emoji']} {job['name']}\n⏱ {job['duration']} сек.\n💰 {job['reward']}₽\n\n<i>Напиши /check через {job['duration']} сек.</i>")
    asyncio.create_task(job_animation(user_id, job_idx))
    await callback.answer("Приступил!")

# ==================== РЕПУТАЦИЯ, РЕФЕРАЛЫ ====================
@dp.callback_query(F.data == "action_rep_menu")
async def rep_menu_callback(callback: CallbackQuery):
    p = players.get(callback.from_user.id)
    new_a = check_ach(callback.from_user.id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"]} if p else None)
    u = get_rep(callback.from_user.id)
    txt = f"🏆 <b>РЕПУТАЦИЯ: {rep_level(u['score'])}</b>\n📊 {u['score']}/100\n📦 Продаж: {u['total_sales']}\n💰 Прибыль: {u['total_profit']}₽"
    if new_a: txt += "\n\n🎉 <b>НОВЫЕ!</b>\n" + "\n".join(f"{a['name']}" for a in new_a)
    await edit_msg(callback.message, txt)

@dp.callback_query(F.data == "action_ref_menu")
async def ref_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    count = len(referral_data[str(user_id)]["invited"]); vip = "👑 Ты в ТОП-3! VIP!" if is_vip(user_id) else ""
    await edit_msg(callback.message, f"🔗 <b>РЕФЕРАЛЫ:</b>\n\n<code>{ref_link(user_id)}</code>\n\n👥 Приглашено: {count}\n💰 Бонус: {count*500}₽\n{vip}")

# ==================== ОСТАЛЬНЫЕ CALLBACK-ОБРАБОТЧИКИ ====================
@dp.callback_query(F.data == "action_stats", StateFilter(GameState.playing))
async def show_stats(callback: CallbackQuery):
    p = get_player(callback.from_user.id)
    house = next((h for h in HOUSES if h["id"] == get_player_house(callback.from_user.id)), HOUSES[0])
    ref_n = len(referral_data[str(callback.from_user.id)]["invited"])
    await edit_msg(callback.message, f"📊 <b>СТАТИСТИКА:</b>\n💰 {p['balance']}₽\n📦 Товаров: {len(p['inventory'])}\n📅 День: {p['day']}\n📋 Продано: {p['items_sold']}\n💸 Прибыль: {p['total_earned']}₽\n🏠 {house['name']}\n👥 Рефералы: {ref_n}")

@dp.callback_query(F.data == "action_demand", StateFilter(GameState.playing))
async def show_demand(callback: CallbackQuery):
    p = get_player(callback.from_user.id)
    await edit_msg(callback.message, f"📊 <b>РЫНОК — День {p['day']}</b>\n\n{fmt_demand(p)}")

@dp.callback_query(F.data == "start_new_game")
async def start_new_game_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; r = get_rep(user_id)
    players[user_id] = {"balance": 5000, "reputation": max(0, r["score"]), "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0, "items_sold": r["total_sales"], "scam_times": r["scam_survived"], "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
    p = players[user_id]
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    await state.set_state(GameState.playing)
    house = next((h for h in HOUSES if h["id"] == get_player_house(user_id)), HOUSES[0])
    await edit_msg(callback.message, f"🚀 <b>ИГРА НАЧАЛАСЬ!</b>\n🌟 День 1 | 💰 5 000₽\n🏠 {house['name']}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(user_id))
    await callback.answer("🚀")

@dp.callback_query(F.data == "continue_game")
async def continue_game_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; p = players.get(user_id)
    if not p: return await callback.answer("Нет игры!")
    await state.set_state(GameState.playing)
    house = next((h for h in HOUSES if h["id"] == get_player_house(user_id)), HOUSES[0])
    await edit_msg(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽\n🏠 {house['name']}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(user_id))
    await callback.answer("🎮")

@dp.callback_query(F.data == "restart_game_confirm")
async def restart_confirm(callback: CallbackQuery):
    await edit_msg(callback.message, "⚠️ <b>СБРОСИТЬ ПРОГРЕСС?</b>\n\nБаланс и инвентарь потеряются.\nРепутация и рефералы сохранятся.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ ДА, СБРОСИТЬ", callback_data="restart_game_yes")],
        [InlineKeyboardButton(text="❌ НЕТ", callback_data="continue_game")],
        [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")],
    ]))

@dp.callback_query(F.data == "restart_game_yes")
async def restart_yes(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id in players: del players[callback.from_user.id]
    await start_new_game_btn(callback, state)

@dp.callback_query(F.data == "action_learn")
async def learn_btn(callback: CallbackQuery):
    l = get_learning(callback.from_user.id)
    kb = []
    for lesson in LESSONS:
        done = lesson["id"] in l["completed"]
        kb.append([InlineKeyboardButton(text=f"{'✅' if done else '📖'} {lesson['title']}", callback_data=f"lesson_{lesson['id']}")])
    kb.append([InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="back_to_start")])
    await edit_msg(callback.message, f"📚 <b>ОБУЧЕНИЕ</b>\nПройдено: {len(l['completed'])}/{len(LESSONS)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("lesson_"))
async def show_lesson(callback: CallbackQuery):
    lesson = next((l for l in LESSONS if l["id"] == int(callback.data.split("_")[1])), None)
    if not lesson: return await callback.answer("Не найден")
    l = get_learning(callback.from_user.id); done = lesson["id"] in l["completed"]
    kb = []
    if not done: kb.append([InlineKeyboardButton(text="✅ ЗАВЕРШИТЬ (+₽)", callback_data=f"complete_lesson_{lesson['id']}")])
    kb.append([InlineKeyboardButton(text="🔙 К УРОКАМ", callback_data="action_learn")])
    kb.append([InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, lesson["text"] + (f"\n\n💰 +{lesson['reward']}₽" if not done else "\n✅ Пройден!"), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("complete_lesson_"))
async def complete_lesson_btn(callback: CallbackQuery):
    if complete_lesson(callback.from_user.id, int(callback.data.split("_")[2])):
        await callback.answer("Урок пройден!"); await learn_btn(callback)
    else: await callback.answer("Уже пройден")

@dp.callback_query(F.data == "ref_info")
async def ref_info(callback: CallbackQuery):
    await edit_msg(callback.message, f"🔗 Твоя ссылка:\n<code>{ref_link(callback.from_user.id)}</code>\n\n💰 +500₽ за друга")

@dp.callback_query(F.data == "back_to_start")
async def back_start(callback: CallbackQuery):
    p = players.get(callback.from_user.id)
    if p and p.get("day", 0) > 0:
        await edit_msg(callback.message, f"👋 <b>МЕНЮ</b>\n📅 День {p['day']} | 💰 {p['balance']}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 ПРОДОЛЖИТЬ", callback_data="continue_game")],
            [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")],
        ]))
    else:
        await edit_msg(callback.message, "🎮 <b>RESELL TYCOON</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 НАЧАТЬ", callback_data="start_new_game")],
            [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")],
        ]))

@dp.callback_query(F.data == "action_buy", StateFilter(GameState.playing))
async def show_suppliers(callback: CallbackQuery):
    user_id = callback.from_user.id; supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    kb = []
    for s in supps:
        kb.append([InlineKeyboardButton(text=f"{s['emoji']} {s['name']} | ⭐{s['rating']} | Кид:{s['scam_chance']}%", callback_data=f"sup_{supps.index(s)}")])
    kb.append([InlineKeyboardButton(text="🔙 МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, f"🏭 <b>ПОСТАВЩИКИ:</b>{' 👑 VIP!' if is_vip(user_id) else ''}\n\n⭐ Рейтинг ↑ = надёжнее\n⚠️ Шанс кидка — могут пропасть с деньгами!", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("sup_"), StateFilter(GameState.playing))
async def show_items(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; idx = int(callback.data.split("_")[1])
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    sup = supps[idx]; items = random.sample(BASE_ITEMS, min(4, len(BASE_ITEMS)))
    p = get_player(user_id); kb = []
    for i, it in enumerate(items):
        pr = int(item_price(it["base_price"], sup) * rep_mult(get_rep(user_id)["score"])["supplier_discount"])
        mp = market_price(it["base_price"], p["market_demand"].get(it["cat"], 1.0))
        kb.append([InlineKeyboardButton(text=f"{it['cat']} {it['name']} — {pr}₽ (~{mp}₽)", callback_data=f"bi_{i}")])
    kb.append([InlineKeyboardButton(text="🔄 ОБНОВИТЬ", callback_data=f"sup_{idx}")])
    kb.append([InlineKeyboardButton(text="🔙 К ПОСТАВЩИКАМ", callback_data="action_buy")])
    kb.append([InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")])
    await state.update_data(sup_idx=idx, sup_items=items)
    await edit_msg(callback.message, f"{sup['emoji']} <b>{sup['name']}</b>\n{sup['desc']}\n⭐ {sup['rating']}/10 | ⚠️ Кид:{sup['scam_chance']}%\n\nВыбери товар:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("bi_"), StateFilter(GameState.playing))
async def buy_item(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item_idx = int(callback.data.split("_")[1]); sup_idx = data.get("sup_idx", 0)
    items = data.get("sup_items", []); user_id = callback.from_user.id
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    sup = supps[sup_idx]
    if item_idx >= len(items): return await callback.answer("Ошибка")
    item = items[item_idx]; p = get_player(user_id)
    price = int(item_price(item["base_price"], sup) * rep_mult(get_rep(user_id)["score"])["supplier_discount"])
    if p["balance"] < price: return await callback.answer("❌ Мало денег!")
    eff_scam = int(sup["scam_chance"] * rep_mult(get_rep(user_id)["score"])["scam_reduce"])
    if random.randint(1, 100) <= eff_scam:
        p["balance"] -= price; p["total_spent"] += price; p["scam_times"] += 1; p["reputation"] = max(0, p["reputation"] - 5)
        add_rep(user_id, -5, f"Кинул {sup['name']}")
        await edit_msg(callback.message, f"💀 <b>КИНУЛИ!</b>\n{sup['name']} пропал с деньгами.\n-{price}₽ | 💼 {p['balance']}₽\n\n💡 <b>Урок:</b> Проверяй поставщика! Начни с малого заказа.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))
        return
    p["balance"] -= price; p["total_spent"] += price
    mp = market_price(item["base_price"], p["market_demand"].get(item["cat"], 1.0))
    p["inventory"].append({"name": f"{item['cat']} {item['name']}", "cat": item["cat"], "buy_price": price, "market_price": mp, "base_price": item["base_price"]})
    if sup["rating"] >= 8: add_rep(user_id, 1, "Надёжный поставщик")
    check_ach(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"]})
    save_json(REPUTATION_FILE, rep_data)
    await edit_msg(callback.message, f"✅ <b>КУПЛЕНО!</b>\n\n📦 {item['cat']} {item['name']}\n💰 Закуп: {price}₽ | 📊 Рынок: ~{mp}₽\n💼 Баланс: {p['balance']}₽\n📦 В инвентаре: {len(p['inventory'])} товаров\n\n👇 <b>ДАЛЬШЕ:</b> Зайди в 📦 ИНВЕНТАРЬ и опубликуй!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📦 В ИНВЕНТАРЬ", callback_data="action_inventory")], [InlineKeyboardButton(text="🔄 Купить ещё", callback_data=f"sup_{sup_idx}")], [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))

@dp.callback_query(F.data == "action_inventory", StateFilter(GameState.playing))
async def show_inventory(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    if not p["inventory"]:
        return await edit_msg(callback.message, "📦 <b>ИНВЕНТАРЬ ПУСТ</b>\n\nТут будут твои товары.\nСначала закупись у поставщиков! 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏭 ЗАКУПИТЬСЯ", callback_data="action_buy")], [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))
    kb = []
    for i, it in enumerate(p["inventory"]):
        pub = user_id in published_items and published_items[user_id] and published_items[user_id].get("item", {}).get("name") == it["name"]
        kb.append([InlineKeyboardButton(text=f"{it['name']} | {it['buy_price']}₽ → ~{it['market_price']}₽ | {'📢 ОПУБЛИКОВАН' if pub else '📱 ОПУБЛИКОВАТЬ'}", callback_data=f"inv_{i}")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    txt = "📦 <b>ИНВЕНТАРЬ:</b>\n\n" + "\n".join(f"{i+1}. {it['name']}\n   Закуп: {it['buy_price']}₽ | Рынок: ~{it['market_price']}₽" for i, it in enumerate(p["inventory"]))
    txt += "\n\n👇 <b>Нажми на товар чтобы опубликовать!</b>"
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("inv_"), StateFilter(GameState.playing))
async def publish_item(callback: CallbackQuery):
    user_id = callback.from_user.id; item_idx = int(callback.data.split("_")[1])
    p = get_player(user_id)
    if item_idx >= len(p["inventory"]): return await callback.answer("Товар не найден")
    item = p["inventory"][item_idx]
    if user_id in published_items and published_items[user_id] and published_items[user_id].get("item", {}).get("name") == item["name"]:
        return await callback.answer("Уже опубликован!")
    published_items[user_id] = {"item": item.copy()}
    await edit_msg(callback.message, f"📢 <b>ОПУБЛИКОВАНО!</b>\n\n📦 {item['name']}\n💰 {item['market_price']}₽\n\n⏳ Жди 1-3 минуты — придут покупатели!\n💬 Они напишут тебе в этот чат.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 ЧАТЫ", callback_data="action_chats")],
        [InlineKeyboardButton(text="📦 ИНВЕНТАРЬ", callback_data="action_inventory")],
        [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")],
    ]))
    asyncio.create_task(spawn_buyers(user_id))
    await callback.answer("Опубликовано!")

@dp.callback_query(F.data == "action_nextday", StateFilter(GameState.playing))
async def next_day(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    house = next((h for h in HOUSES if h["id"] == get_player_house(user_id)), HOUSES[0])
    bonus = house["income_bonus"]
    p["balance"] += bonus; p["day"] += 1; p["stat_earned_today"] = bonus; p["stat_sold_today"] = 0
    for c in CATEGORIES: p["market_demand"][c] = max(0.3, min(3.0, p["market_demand"][c] * random.uniform(0.85, 1.15)))
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    if p["inventory"] and random.random() < 0.2:
        for it in p["inventory"]: it["market_price"] = int(it["market_price"] * random.uniform(0.7, 0.95))
    if user_id in published_items: published_items[user_id] = None
    check_ach(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"]})
    save_json(REPUTATION_FILE, rep_data)
    await edit_msg(callback.message, f"☀️ <b>ДЕНЬ {p['day']}</b> | 💰 {p['balance']}₽\n🏠 Бонус от {house['name']}: +{bonus}₽\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(user_id))

@dp.callback_query(F.data == "action_end", StateFilter(GameState.playing))
async def end_game(callback: CallbackQuery, state: FSMContext):
    p = get_player(callback.from_user.id); await state.clear()
    r = "🏆 <b>ПОБЕДА!</b>" if p["balance"] >= 50000 else "💀 <b>БАНКРОТ!</b>" if p["balance"] <= 0 else "🎮 Игра окончена."
    check_ach(callback.from_user.id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"]})
    save_json(REPUTATION_FILE, rep_data)
    await edit_msg(callback.message, f"{r}\n💰 {p['balance']}₽\n📦 Продаж: {p['items_sold']}\n\n/play — ещё раз", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 ЕЩЁ РАЗ", callback_data="restart_game")],
        [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")],
    ]))

@dp.callback_query(F.data == "restart_game")
async def restart_game(callback: CallbackQuery):
    if callback.from_user.id in players: del players[callback.from_user.id]
    await callback.message.edit_text("🔄 Напиши /play")

@dp.callback_query(F.data == "action_back", StateFilter(GameState.playing))
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    house = next((h for h in HOUSES if h["id"] == get_player_house(user_id)), HOUSES[0])
    et = f"\n\n{p['current_event']['text']}" if p.get("current_event") else ""
    await edit_msg(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽\n🏠 {house['name']}{et}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(user_id))

# ==================== ПОЛУЧЕНИЕ ССЫЛОК НА ФОТО ====================
@dp.message(F.photo)
async def get_photo_links(message: types.Message):
    photo = message.photo[-1]
    file_id = photo.file_id
    file = await bot.get_file(file_id)
    direct_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"
    await message.answer(f"✅ <b>Ссылки на фото:</b>\n\n<b>1. ID для кода (лучше использовать его):</b>\n<code>{file_id}</code>\n\n<b>2. Прямая ссылка (URL):</b>\n{direct_url}", parse_mode="HTML")

# ==================== ЗАПУСК ====================
async def main():
    print("🎮 ReSell Tycoon запущен!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())