import random
import hashlib
import json
import os
from collections import defaultdict
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from openai import OpenAI

# ==================== КОНФИГ ====================
API_TOKEN = '8747685010:AAH8bN3x0fihSvUzVitijYQLHXeHFhIV5w4'  # ← ЗАМЕНИ
CHANNEL_LINK = '@vintagedrop61'
CHANNEL_NAME = 'ReSell👾'
BOT_USERNAME = 'R-Game'  # ← ЗАМЕНИ БЕЗ @
DEEPSEEK_API_KEY = "sk-9515baacbf9b44bfbf45caadf97e5012"  # ← ЗАМЕНИ

# DeepSeek клиент
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# ==================== ФАЙЛЫ ДАННЫХ ====================
REPUTATION_FILE = "reputation_data.json"
REFERRAL_FILE = "referrals.json"

# ==================== ПОСТАВЩИКИ ====================
SUPPLIERS = [
    {"name": "🏭 MegaStock", "rating": 9, "price_mult": 1.4, "scam_chance": 0, "emoji": "🏭"},
    {"name": "👕 OldGarage", "rating": 7, "price_mult": 1.15, "scam_chance": 10, "emoji": "👕"},
    {"name": "🎒 Vintager", "rating": 5, "price_mult": 0.85, "scam_chance": 25, "emoji": "🎒"},
    {"name": "💸 DumpPrice", "rating": 3, "price_mult": 0.55, "scam_chance": 50, "emoji": "💸"},
    {"name": "🎲 LuckyBag", "rating": 1, "price_mult": 0.3, "scam_chance": 75, "emoji": "🎲"},
]
VIP_SUPPLIER = {"name": "👑 PremiumStock", "rating": 10, "price_mult": 1.05, "scam_chance": 0, "emoji": "👑"}

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
    {"cat": "👟 Кроссы", "name": "New Balance 990v3", "base_price": 4200},
    {"cat": "🎒 Аксессуары", "name": "Patagonia Hip Pack", "base_price": 2000},
    {"cat": "👖 Джинсы", "name": "Wrangler Retro", "base_price": 1800},
    {"cat": "🧥 Куртки", "name": "Patagonia Down Jacket", "base_price": 5500},
]

CATEGORIES = ["👖 Джинсы", "👕 Худи", "🧥 Куртки", "👟 Кроссы", "🎒 Аксессуары"]

BUYER_NAMES = [
    "Вася", "Петя", "Колян", "Димон", "Антоха", "Серёга", "Макс",
    "Лёха", "Вован", "Гоша", "Мишаня", "Тёмыч", "Даня", "Егор",
    "Никита", "Рустам", "Жека", "Илюха", "Стас", "Артём"
]

BUYER_HAGGLE_MESSAGES = [
    "👤 {name}: Слушай, а за {offer} отдашь? У меня сейчас столько есть.",
    "👤 {name}: Братан, {offer} — и я прямо сейчас забираю. По рукам?",
    "👤 {name}: А чё так дорого? Давай {offer}, я видел дешевле.",
    "👤 {name}: Ну {offer} — последняя цена. Или я ушёл.",
    "👤 {name}: У меня в закладках такой же за {offer} висит. Продашь?",
    "👤 {name}: {offer} и ни копейкой больше. Берёшь?",
    "👤 {name}: Слушай, мне очень надо, но денег {offer} всего. Идёт?",
]

BUYER_ACCEPT_MESSAGES = [
    "👤 {name}: 👌 Договорились! Забираю.",
    "👤 {name}: ✅ По рукам! Сейчас переведу.",
    "👤 {name}: 🔥 Отлично! Давай встретимся сегодня.",
    "👤 {name}: 💯 Беру! Скидывай данные для перевода.",
]

BUYER_DECLINE_MESSAGES = [
    "👤 {name}: 😕 Дороговато. Пойду ещё поищу.",
    "👤 {name}: ❌ Не, не готов столько отдать. Удачи.",
    "👤 {name}: 🤷 Ладно, подумаю. Пока.",
    "👤 {name}: 👋 Слишком дорого. Бывай.",
]

BUYER_NOT_INTERESTED = [
    "👤 {name}: Не, {cat} сейчас не в тему. Давай что-нибудь другое.",
    "👤 {name}: {cat}? Уже купил вчера. Нужны кроссы.",
    "👤 {name}: Слушай, а {cat} есть что-нибудь ещё? Это не моё.",
    "👤 {name}: {cat} не ношу. Может, куртки есть?",
]

MARKET_EVENTS = [
    {"text": "📰 В телеграм-канале @fashion_leaks выложили подборку винтажных джинсов — хайп на джинсы!", "cat": "👖 Джинсы", "mult": 1.5},
    {"text": "📰 Дожди на неделе — спрос на куртки вырос!", "cat": "🧥 Куртки", "mult": 1.4},
    {"text": "📰 Вышел новый альбом у Pharaoh — все хотят кроссовки как у него.", "cat": "👟 Кроссы", "mult": 1.5},
    {"text": "📰 Лето близко — джинсы и худи падают в цене.", "cat": "👖 Джинсы", "mult": 0.6},
    {"text": "📰 Авито ввело комиссию 15% — покупатели стали осторожнее.", "cat": None, "mult": 0.8},
    {"text": "📰 В трендах ретро-аксессуары! Сумки и кепки на пике.", "cat": "🎒 Аксессуары", "mult": 1.6},
    {"text": "📰 Холодная погода задерживается — куртки всё ещё в цене.", "cat": "🧥 Куртки", "mult": 1.3},
    {"text": "📰 В школу скоро — родители ищут худи для детей.", "cat": "👕 Худи", "mult": 1.35},
    {"text": "📰 Кроссовки — переполненный рынок. Демпинг повсюду.", "cat": "👟 Кроссы", "mult": 0.65},
    {"text": "📰 Блогер Литвин засветился в Stüssy — аксессуары летят!", "cat": "🎒 Аксессуары", "mult": 1.5},
    {"text": "📰 Авито-блокировка за накрутку — многие ушли, конкуренция ниже.", "cat": None, "mult": 1.2},
    {"text": "📰 Эконом-режим: покупатели ищут самое дешёвое.", "cat": None, "mult": 0.7},
]

# ==================== НЕЙРОКЛИЕНТЫ: ТИПЫ ====================
CLIENT_TYPES = {
    "angry": {
        "name": "злой",
        "system_prompt": """Ты — злой и агрессивный покупатель на Авито. Твои черты:
- Всегда недоволен ценой
- Грубишь, но без мата
- Торгуешься жёстко, сбиваешь цену на 30-50%
- Можешь написать "дорого, я такое на помойке нашёл"
- Если продавец не уступает — уходишь с оскорблением
- Если уступает — берёшь, но всё равно ворчишь
- Никогда не хвали товар
- Отвечай коротко, 1-2 предложения, как в чате""",
        "mood_emoji": "😡",
        "discount_range": (0.5, 0.7),
        "patience": 2
    },
    "kind": {
        "name": "добрый",
        "system_prompt": """Ты — добрый и вежливый покупатель. Твои черты:
- Всегда вежлив, используешь "пожалуйста", "спасибо"
- Торгуешься мягко, просишь скидку 10-20%
- Хвалишь товар: "хорошая вещь", "давно искал"
- Если цена устраивает — сразу берёшь
- Если дорого — извиняешься и уходишь
- Можешь согласиться на встречную цену продавца
- Отвечай коротко, 1-2 предложения""",
        "mood_emoji": "😊",
        "discount_range": (0.8, 0.9),
        "patience": 5
    },
    "sly": {
        "name": "хитрый",
        "system_prompt": """Ты — хитрый перекупщик. Твои черты:
- Пытаешься сбить цену аргументами: "на другом аккаунте дешевле", "таких полно"
- Торгуешься профессионально, сбиваешь на 20-40%
- Можешь блефовать: "за 2000 прямо сейчас забираю, иначе ухожу"
- Торгуешься долго, не уходишь сразу
- Если понимаешь что цена хорошая — берёшь без торга
- Отвечай коротко, как в чате Авито""",
        "mood_emoji": "😏",
        "discount_range": (0.6, 0.8),
        "patience": 4
    }
}

# ==================== РЕПУТАЦИЯ: УРОВНИ И ДОСТИЖЕНИЯ ====================
REPUTATION_LEVELS = {
    -100: {"name": "💀 Чёрный список", "description": "Никто не хочет иметь с тобой дело"},
    -50: {"name": "🔴 Ужасная", "description": "Тебя боятся и поставщики, и клиенты"},
    -10: {"name": "🟠 Плохая", "description": "Клиенты не доверяют, поставщики настороже"},
    0: {"name": "🟡 Нейтральная", "description": "Ты новичок, тебя никто не знает"},
    25: {"name": "🟢 Хорошая", "description": "Тебе начинают доверять"},
    50: {"name": "🔵 Отличная", "description": "Ты проверенный продавец"},
    75: {"name": "🟣 Легендарная", "description": "Твоё имя знают все в товарке"},
    90: {"name": "🟡 Золотая", "description": "Ты — элита перекупщиков"},
    100: {"name": "👑 Бог товарки", "description": "Максимальный уровень доверия"},
}

ACHIEVEMENTS = [
    {"id": "first_sale", "name": "🎯 Первая продажа", "desc": "Продай 1 товар", "target": 1, "reward": 5},
    {"id": "seller_10", "name": "📦 Продавец", "desc": "Продай 10 товаров", "target": 10, "reward": 10},
    {"id": "seller_50", "name": "🏪 Магазин", "desc": "Продай 50 товаров", "target": 50, "reward": 20},
    {"id": "seller_100", "name": "🏭 Оптовик", "desc": "Продай 100 товаров", "target": 100, "reward": 30},
    {"id": "profit_5000", "name": "💰 Навар", "desc": "Заработай 5 000₽ чистыми", "target": 5000, "reward": 5},
    {"id": "profit_50000", "name": "💸 Богач", "desc": "Заработай 50 000₽ чистыми", "target": 50000, "reward": 15},
    {"id": "balance_100k", "name": "🏦 Капитал", "desc": "Накопи 100 000₽ на балансе", "target": 100000, "reward": 25},
    {"id": "ref_5", "name": "🤝 Друг", "desc": "Пригласи 5 друзей", "target": 5, "reward": 10},
    {"id": "ref_20", "name": "👥 Команда", "desc": "Пригласи 20 друзей", "target": 20, "reward": 20},
    {"id": "no_scam_10", "name": "🛡️ Осторожный", "desc": "Проведи 10 сделок без кидалова", "target": 10, "reward": 10},
    {"id": "vip_deal", "name": "👑 VIP-сделка", "desc": "Купи у VIP-поставщика", "target": 1, "reward": 15},
    {"id": "angry_win", "name": "😡 Укротитель", "desc": "Успешно продай злому клиенту", "target": 1, "reward": 10},
    {"id": "haggle_master", "name": "🎯 Мастер торга", "desc": "Выторгуй цену выше предложенной", "target": 1, "reward": 10},
]

# ==================== БОТ ====================
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class GameState(StatesGroup):
    playing = State()

# ==================== ГЛОБАЛЬНЫЕ ХРАНИЛИЩА ====================
players = {}

# Рефералы
referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False})

# Репутация
rep_data = {}

# Нейро-чаты
active_chats = {}

# ==================== ЗАГРУЗКА ДАННЫХ ====================
def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_all():
    global referral_data, rep_data
    ref_raw = load_json(REFERRAL_FILE, {})
    referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False}, ref_raw)
    rep_data = load_json(REPUTATION_FILE, {})

load_all()

# ==================== РЕФЕРАЛЫ: ФУНКЦИИ ====================
def generate_ref_code(user_id):
    return hashlib.md5(str(user_id).encode()).hexdigest()[:8]

def get_ref_link(user_id):
    return f"https://t.me/{BOT_USERNAME}?start=ref_{generate_ref_code(user_id)}"

def get_top_referrers(limit=10):
    stats = [(uid, len(data["invited"])) for uid, data in referral_data.items()]
    stats.sort(key=lambda x: x[1], reverse=True)
    return stats[:limit]

def is_vip(user_id):
    top = get_top_referrers(3)
    return str(user_id) in [str(uid) for uid, _ in top]

# ==================== РЕПУТАЦИЯ: ФУНКЦИИ ====================
def get_user_rep(user_id):
    uid = str(user_id)
    if uid not in rep_data:
        rep_data[uid] = {
            "score": 0, "total_sales": 0, "total_profit": 0,
            "max_balance": 0, "scam_survived": 0, "vip_purchases": 0,
            "angry_deals": 0, "haggle_wins": 0, "achievements": [], "rep_history": []
        }
        save_json(REPUTATION_FILE, rep_data)
    return rep_data[uid]

def get_rep_level(score):
    for t in sorted(REPUTATION_LEVELS.keys(), reverse=True):
        if score >= t:
            return REPUTATION_LEVELS[t]
    return REPUTATION_LEVELS[-100]

def add_rep(user_id, amount, reason=""):
    user = get_user_rep(user_id)
    old_score = user["score"]
    user["score"] = max(-100, min(100, user["score"] + amount))
    user["rep_history"].append({"change": amount, "reason": reason, "total": user["score"]})
    if len(user["rep_history"]) > 20:
        user["rep_history"] = user["rep_history"][-20:]
    save_json(REPUTATION_FILE, rep_data)
    old_level = get_rep_level(old_score)
    new_level = get_rep_level(user["score"])
    return {
        "old_score": old_score, "new_score": user["score"], "change": amount,
        "level_up": old_level["name"] != new_level["name"], "new_level": new_level
    }

def get_rep_multiplier(score):
    if score >= 75: return {"supplier_discount": 0.85, "scam_reduce": 0.2, "haggle_bonus": 0.25}
    elif score >= 50: return {"supplier_discount": 0.90, "scam_reduce": 0.4, "haggle_bonus": 0.15}
    elif score >= 25: return {"supplier_discount": 0.95, "scam_reduce": 0.6, "haggle_bonus": 0.05}
    elif score >= 0: return {"supplier_discount": 1.0, "scam_reduce": 0.8, "haggle_bonus": 0.0}
    elif score >= -10: return {"supplier_discount": 1.1, "scam_reduce": 1.0, "haggle_bonus": -0.05}
    elif score >= -50: return {"supplier_discount": 1.25, "scam_reduce": 1.2, "haggle_bonus": -0.15}
    else: return {"supplier_discount": 1.5, "scam_reduce": 1.5, "haggle_bonus": -0.3}

def check_achievements(user_id, player_data=None):
    user = get_user_rep(user_id)
    if player_data:
        user["total_sales"] = player_data.get("items_sold", 0)
        user["total_profit"] = player_data.get("total_earned", 0)
        user["max_balance"] = max(user["max_balance"], player_data.get("balance", 0))
        user["scam_survived"] = player_data.get("scam_times", 0)
    new_ach = []
    for ach in ACHIEVEMENTS:
        if ach["id"] in user["achievements"]:
            continue
        earned = False
        tid = ach["id"]
        if tid == "first_sale" and user["total_sales"] >= 1: earned = True
        elif tid == "seller_10" and user["total_sales"] >= 10: earned = True
        elif tid == "seller_50" and user["total_sales"] >= 50: earned = True
        elif tid == "seller_100" and user["total_sales"] >= 100: earned = True
        elif tid == "profit_5000" and user["total_profit"] >= 5000: earned = True
        elif tid == "profit_50000" and user["total_profit"] >= 50000: earned = True
        elif tid == "balance_100k" and user["max_balance"] >= 100000: earned = True
        elif tid == "no_scam_10" and user["scam_survived"] >= 10: earned = True
        elif tid == "vip_deal" and user["vip_purchases"] >= 1: earned = True
        elif tid == "angry_win" and user["angry_deals"] >= 1: earned = True
        elif tid == "haggle_master" and user["haggle_wins"] >= 1: earned = True
        if earned:
            user["achievements"].append(ach["id"])
            add_rep(user_id, ach["reward"], f"Достижение: {ach['name']}")
            new_ach.append(ach)
    save_json(REPUTATION_FILE, rep_data)
    return new_ach

def format_rep_card(user_id, player_data=None):
    user = get_user_rep(user_id)
    level = get_rep_level(user["score"])
    mult = get_rep_multiplier(user["score"])
    bar_len = 10
    filled = int((user["score"] + 100) / 200 * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    lines = [
        f"🏆 <b>РЕПУТАЦИЯ: {level['name']}</b>",
        f"📊 Очки: {user['score']}/100",
        f"[{bar}]",
        f"",
        f"📋 <b>Статистика:</b>",
        f"📦 Продаж: {user['total_sales']}",
        f"💰 Прибыль: {user['total_profit']}₽",
        f"💼 Макс. баланс: {user['max_balance']}₽",
        f"⚠️ Кидалова пережито: {user['scam_survived']}",
        f"",
        f"🎁 <b>Бонусы:</b>",
        f"🏭 Скидка у поставщиков: {int((1-mult['supplier_discount'])*100)}%",
        f"🛡️ Защита от кидка: {int((1-mult['scam_reduce'])*100)}%",
        f"🗣 Бонус к торгу: {int(mult['haggle_bonus']*100)}%",
        f"",
        f"🏅 Достижений: {len(user['achievements'])}/{len(ACHIEVEMENTS)}",
    ]
    if user["achievements"]:
        lines.append(f"\n🏅 <b>Достижения:</b>")
        for ach_id in user["achievements"][-5:]:
            ach = next((a for a in ACHIEVEMENTS if a["id"] == ach_id), None)
            if ach: lines.append(f"  {ach['name']}")
    return "\n".join(lines)

def format_rep_history(user_id):
    user = get_user_rep(user_id)
    if not user["rep_history"]:
        return "📜 История пуста."
    lines = ["📜 <b>ИСТОРИЯ:</b>\n"]
    for e in user["rep_history"][-10:]:
        sign = "+" if e["change"] >= 0 else ""
        lines.append(f"{sign}{e['change']} реп. — {e['reason']} (Всего: {e['total']})")
    return "\n".join(lines)

def get_top_reputation(limit=10):
    stats = [(int(uid), d["score"], d["total_sales"], d["total_profit"]) for uid, d in rep_data.items()]
    stats.sort(key=lambda x: x[1], reverse=True)
    return stats[:limit]

# ==================== НЕЙРОКЛИЕНТЫ: ФУНКЦИИ ====================
def neuro_first_message(client_type, item_name, price, offer):
    msgs = {
        "angry": [
            f"Это чё за цена? {price}₽ за {item_name}? Да я такие за {offer}₽ беру. Отдавай за {offer} или я пошёл.",
            f"Слушай, {price}₽ — это грабёж. Давай {offer}₽ и я забираю. Нет — дальше листаю.",
            f"За {price}₽ я тебе что, лох? Такие за {offer}₽ на каждом углу. Берёшь {offer}?",
        ],
        "kind": [
            f"Здравствуйте! Очень нравится {item_name}, но {price}₽ дороговато. Может, отдадите за {offer}₽? Пожалуйста!",
            f"Добрый день! Ищу такой {item_name} давно. У меня бюджет {offer}₽. Возможно договоримся?",
            f"Здравствуйте! {item_name} — то что надо. Но не могли бы вы уступить до {offer}₽? Буду очень благодарен!",
        ],
        "sly": [
            f"Слушай, {item_name} норм, но на соседнем аккаунте такой же за {offer}₽ висит. Сможешь за {offer}₽ отдать?",
            f"Бро, {price}₽ — ну такое. У меня кэш {offer}₽ прямо сейчас. Забираю, если согласен.",
            f"Я мониторю рынок, {item_name} уходит в среднем за {offer}₽. Давай по рынку?",
        ]
    }
    return random.choice(msgs.get(client_type, msgs["kind"]))

def neuro_fallback(client_type, offer):
    msgs = {
        "angry": [
            f"Короче, моё предложение {offer}₽. Согласен — забираю. Нет — я пошёл.",
            "Давай быстрее, у меня ещё 10 вкладок открыто. Берёшь мою цену или нет?",
        ],
        "kind": [
            "Я понимаю вашу позицию. Но может всё-таки уступите немного?",
            "А если я прямо сейчас оплачу? Может, сделаете скидку?",
        ],
        "sly": [
            f"Смотри, рынок диктует. У меня кэш, я забираю сейчас. {offer}₽ — моё предложение.",
            "Я перекупаю, мне ещё заработать надо. Твоя цена минус 20% — и по рукам.",
        ]
    }
    return random.choice(msgs.get(client_type, msgs["kind"]))

def start_neuro_chat(user_id, item_name, item_price, client_type=None):
    if client_type is None:
        client_type = random.choice(list(CLIENT_TYPES.keys()))
    client = CLIENT_TYPES[client_type]
    rep_mult = get_rep_multiplier(get_user_rep(user_id)["score"])
    if rep_mult["haggle_bonus"] > 0.1 and client_type == "angry" and random.random() < rep_mult["haggle_bonus"]:
        client_type = "sly"; client = CLIENT_TYPES[client_type]
    if rep_mult["haggle_bonus"] < 0 and client_type == "kind" and random.random() < abs(rep_mult["haggle_bonus"]):
        client_type = "angry"; client = CLIENT_TYPES[client_type]
    discount = random.uniform(*client["discount_range"]) + rep_mult["haggle_bonus"]
    discount = max(0.3, min(0.95, discount))
    offer = int(item_price * discount)
    offer = (offer // 100) * 100 + 99
    if offer < 100: offer = item_price // 2
    first_msg = neuro_first_message(client_type, item_name, item_price, offer)
    active_chats[user_id] = {
        "client_type": client_type, "item": item_name, "price": item_price,
        "offer": offer, "history": [
            {"role": "system", "content": client["system_prompt"]},
            {"role": "user", "content": f"[Товар: {item_name}, Цена: {item_price}₽, Предложение: {offer}₽]"},
            {"role": "assistant", "content": first_msg}
        ], "round": 1, "max_rounds": client["patience"], "finished": False
    }
    return {"message": first_msg, "client_type": client_type, "client_name": client["name"],
            "emoji": client["mood_emoji"], "offer": offer, "round": 1, "max_rounds": client["patience"]}

def neuro_chat(user_id, user_message):
    if user_id not in active_chats or active_chats[user_id]["finished"]:
        return {"error": "Нет диалога"}
    chat = active_chats[user_id]; client = CLIENT_TYPES[chat["client_type"]]
    chat["history"].append({"role": "user", "content": user_message}); chat["round"] += 1
    if chat["round"] > chat["max_rounds"]:
        chat["finished"] = True
        msgs = {
            "angry": ["Всё, надоел. Я пошёл.", "Да ну тебя. Пошёл я отсюда."],
            "kind": ["Ладно, я подумаю ещё. Спасибо!", "Понял, хорошо. Поищу ещё, до свидания."],
            "sly": ["Ну хорошо, удачи. Я ещё посмотрю.", "Ладно, найдём другого продавца."]
        }
        return {"finished": True, "result": "lost", "message": random.choice(msgs.get(chat["client_type"], ["Пока."])), "emoji": "👋"}
    try:
        resp = client.chat.completions.create(model="deepseek-chat", messages=chat["history"], temperature=0.9, max_tokens=150)
        ai_msg = resp.choices[0].message.content
    except:
        ai_msg = neuro_fallback(chat["client_type"], chat["offer"])
    chat["history"].append({"role": "assistant", "content": ai_msg})
    finished, result = False, None
    ml = ai_msg.lower()
    agree = ["беру", "договорились", "по рукам", "забираю", "согласен", "давай", "идёт"]
    decline = ["нет", "не буду", "ушёл", "пошёл", "пока", "до свидания", "удачи"]
    for w in agree:
        if w in ml and "?" not in ml: finished, result = True, "sold"; break
    if not finished:
        for w in decline:
            if w in ml and len(ml) < 200: finished, result = True, "lost"; break
    if finished: chat["finished"] = True
    return {"finished": finished, "result": result, "message": ai_msg, "round": chat["round"], "emoji": client["mood_emoji"]}

def get_chat_status(user_id):
    if user_id not in active_chats or active_chats[user_id]["finished"]: return None
    c = active_chats[user_id]
    return {"client_type": c["client_type"], "item": c["item"], "price": c["price"],
            "current_offer": c["offer"], "round": c["round"], "max_rounds": c["max_rounds"],
            "emoji": CLIENT_TYPES[c["client_type"]]["mood_emoji"]}

def end_chat(user_id):
    if user_id in active_chats: del active_chats[user_id]

# ==================== ИГРА: ФУНКЦИИ ====================
def get_player(user_id):
    if user_id not in players:
        rep = get_user_rep(user_id)
        rep_mult = get_rep_multiplier(rep["score"])
        players[user_id] = {
            "balance": 5000, "reputation": max(0, rep["score"]),
            "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0,
            "items_sold": rep["total_sales"], "scam_times": rep["scam_survived"],
            "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None,
            "stat_earned_today": 0, "stat_sold_today": 0, "rep_mult": rep_mult,
        }
    return players[user_id]

def get_item_price(base, sup):
    return int(base * sup["price_mult"])

def get_market_price(base, demand):
    return int(base * demand * random.uniform(0.9, 1.3))

def generate_daily_event():
    return random.choice(MARKET_EVENTS) if random.random() < 0.6 else None

def apply_market_event(p, event):
    if event["cat"]:
        p["market_demand"][event["cat"]] = max(0.3, min(3.0, p["market_demand"][event["cat"]] * event["mult"]))
    else:
        for cat in CATEGORIES:
            p["market_demand"][cat] = max(0.3, min(3.0, p["market_demand"][cat] * event["mult"]))

def format_inventory(inv):
    if not inv: return "📦 Инвентарь пуст."
    return "📦 <b>ИНВЕНТАРЬ:</b>\n" + "\n".join(
        f"{i}. {it['name']} | Закуп: {it['buy_price']}₽ | Рынок: ~{it['market_price']}₽"
        for i, it in enumerate(inv, 1)
    )

def format_stats(p):
    return (
        f"📊 <b>СТАТИСТИКА</b>\n💰 Баланс: {p['balance']}₽\n⭐ Репутация: {p['reputation']}/100\n"
        f"📅 День: {p['day']}\n📦 Инвентарь: {len(p['inventory'])}\n"
        f"💸 Заработано: {p['total_earned']}₽\n🛒 Потрачено: {p['total_spent']}₽\n"
        f"📋 Продано: {p['items_sold']} шт.\n⚠️ Кидалова: {p['scam_times']}"
    )

def get_main_keyboard(user_id=None):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🏭 ЗАКУП", callback_data="action_buy"),
        InlineKeyboardButton("📦 ИНВЕНТАРЬ", callback_data="action_inventory"),
        InlineKeyboardButton("🧠 НЕЙРОКЛИЕНТ", callback_data="action_neuro"),
        InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="action_stats"),
        InlineKeyboardButton("🏆 РЕПУТАЦИЯ", callback_data="action_rep"),
        InlineKeyboardButton("🔗 РЕФЕРАЛЫ", callback_data="action_ref"),
        InlineKeyboardButton("⏩ СЛЕД. ДЕНЬ", callback_data="action_nextday"),
        InlineKeyboardButton("🏁 ЗАВЕРШИТЬ", callback_data="action_end"),
    )
    return kb

async def check_game_over(callback, p):
    if p["balance"] >= 50000:
        await callback.message.answer(
            f"🏆 <b>ПОБЕДА!</b> Ты достиг 50 000₽!\nГотов к реальным продажам? 👉 {CHANNEL_LINK}",
            parse_mode="HTML"
        )
    elif p["balance"] <= 0:
        await callback.message.answer(
            f"💀 <b>БАНКРОТ</b>\nВ реальности начни без вложений в {CHANNEL_NAME}\n/play — ещё раз",
            parse_mode="HTML"
        )

# ==================== КОМАНДЫ БОТА ====================
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()
    if args.startswith("ref_"):
        ref_code = args[4:]
        referrer_id = None
        for uid in referral_data:
            if generate_ref_code(uid) == ref_code: referrer_id = uid; break
        if referrer_id and referrer_id != user_id and user_id not in referral_data[referrer_id]["invited"]:
            referral_data[referrer_id]["invited"].append(user_id)
            save_json(REFERRAL_FILE, dict(referral_data))
            if referrer_id in players: players[referrer_id]["balance"] += 500
            try: await bot.send_message(referrer_id, f"🎉 Новый реферал! +500₽\n👥 Всего: {len(referral_data[referrer_id]['invited'])}", parse_mode="HTML")
            except: pass
            await message.answer("👋 Привет! Ты по реферальной ссылке.\n\n🎮 ReSell Tycoon — симулятор перекупщика\nЦель: 5 000₽ → 50 000₽\n\n/play — играть\n/ref — твоя ссылка\n/rep — репутация\n/chat — нейроклиент", parse_mode="HTML")
            return
    await message.answer(
        f"🎮 <b>ReSell Tycoon</b>\nСимулятор перекупщика\n\n"
        f"💰 Старт: 5 000₽ | 🎯 Цель: 50 000₽\n\n"
        f"🔹 /play — начать игру\n🔹 /ref — рефералы\n🔹 /rep — репутация\n"
        f"🔹 /chat — нейроклиент\n🔹 /rating — топ рефереров",
        parse_mode="HTML"
    )

@dp.message_handler(commands=['play'])
async def play_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    rep = get_user_rep(user_id)
    players[user_id] = {
        "balance": 5000, "reputation": max(0, rep["score"]), "inventory": [],
        "day": 1, "total_earned": 0, "total_spent": 0,
        "items_sold": rep["total_sales"], "scam_times": rep["scam_survived"],
        "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None,
        "stat_earned_today": 0, "stat_sold_today": 0,
        "rep_mult": get_rep_multiplier(rep["score"]),
    }
    p = players[user_id]
    event = generate_daily_event(); p["current_event"] = event
    if event: apply_market_event(p, event)
    await GameState.playing.set()
    event_text = f"\n\n{event['text']}" if event else ""
    vip_txt = "\n👑 VIP-статус!" if is_vip(user_id) else ""
    await message.answer(
        f"🌟 <b>ДЕНЬ {p['day']}</b>\nБаланс: {p['balance']}₽{vip_txt}{event_text}\n\nВыбери действие:",
        parse_mode="HTML", reply_markup=get_main_keyboard(user_id)
    )

# ==================== РЕФЕРАЛЫ: КОМАНДЫ ====================
@dp.message_handler(commands=['ref'])
async def ref_cmd(message: types.Message):
    user_id = message.from_user.id
    link = get_ref_link(user_id)
    count = len(referral_data[str(user_id)]["invited"])
    vip_user = is_vip(user_id)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("📋 СКОПИРОВАТЬ", callback_data=f"copy_ref_{user_id}"))
    kb.add(InlineKeyboardButton("🏆 РЕЙТИНГ", callback_data="show_rating"))
    vip_txt = "\n👑 Ты в ТОП-3! VIP-поставщик открыт!\n" if vip_user else ""
    await message.answer(
        f"🔗 <b>ТВОЯ ССЫЛКА:</b>\n<code>{link}</code>\n\n👥 Приглашено: {count}\n💰 Бонус: {count*500}₽\n{vip_txt}"
        f"🎁 Топ-3 получают VIP-поставщика!",
        parse_mode="HTML", reply_markup=kb
    )

@dp.message_handler(commands=['rating'])
async def rating_cmd(message: types.Message):
    top = get_top_referrers(10)
    if not top: return await message.answer("🏆 Рейтинг пуст. Будь первым! /ref")
    lines = ["🏆 <b>ТОП-10 РЕФЕРЕРОВ:</b>\n"]
    medals = ["🥇","🥈","🥉"] + ["▫️"]*7
    for i, (uid, count) in enumerate(top):
        try:
            u = await bot.get_chat(uid); name = f"@{u.username}" if u.username else u.first_name
        except: name = f"ID:{uid}"
        lines.append(f"{medals[i]} {name} — <b>{count}</b>")
    await message.answer("\n".join(lines), parse_mode="HTML")

@dp.callback_query_handler(lambda c: c.data == "show_rating")
async def rating_btn(callback: CallbackQuery):
    await rating_cmd(callback.message)

@dp.callback_query_handler(lambda c: c.data.startswith("copy_ref_"))
async def copy_ref_btn(callback: CallbackQuery):
    uid = int(callback.data.split("_")[2])
    await callback.message.answer(f"📋 Ссылка:\n<code>{get_ref_link(uid)}</code>", parse_mode="HTML")
    await callback.answer("Скопируй 👆")

# ==================== РЕПУТАЦИЯ: КОМАНДЫ ====================
@dp.message_handler(commands=['rep'])
async def rep_cmd(message: types.Message):
    user_id = message.from_user.id
    p = players.get(user_id)
    pd = {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"], "scam_times": p["scam_times"]} if p else None
    new_ach = check_achievements(user_id, pd)
    card = format_rep_card(user_id, pd)
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📜 История", callback_data="rep_history"))
    kb.add(InlineKeyboardButton("🏆 Топ репутации", callback_data="rep_top"))
    if new_ach:
        card += "\n\n🎉 <b>НОВЫЕ ДОСТИЖЕНИЯ!</b>\n" + "\n".join(f"{a['name']} (+{a['reward']})" for a in new_ach)
    await message.answer(card, parse_mode="HTML", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "rep_history")
async def rep_history_btn(callback: CallbackQuery):
    await callback.message.edit_text(format_rep_history(callback.from_user.id), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_rep")))

@dp.callback_query_handler(lambda c: c.data == "rep_top")
async def rep_top_btn(callback: CallbackQuery):
    top = get_top_reputation(10)
    if not top: return await callback.answer("Нет данных")
    lines = ["🏆 <b>ТОП-10 ПО РЕПУТАЦИИ:</b>\n"]
    medals = ["🥇","🥈","🥉"] + ["▫️"]*7
    for i, (uid, score, sales, profit) in enumerate(top):
        level = get_rep_level(score)
        lines.append(f"{medals[i]} ID:{uid} — {score} ({level['name']}) | Продаж: {sales}")
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_rep")))

@dp.callback_query_handler(lambda c: c.data == "back_to_rep")
async def back_to_rep_btn(callback: CallbackQuery):
    await rep_cmd(callback.message)

# ==================== НЕЙРОКЛИЕНТ: КОМАНДЫ ====================
@dp.message_handler(commands=['chat'])
async def neuro_start_cmd(message: types.Message):
    user_id = message.from_user.id
    p = get_player(user_id)
    if not p["inventory"]: return await message.answer("📦 Нет товаров. Закупись! /play")
    item = random.choice(p["inventory"])
    data = start_neuro_chat(user_id, item["name"], item["market_price"])
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("💰 Предложить", callback_data="neuro_offer"))
    kb.add(InlineKeyboardButton("✅ Согласиться", callback_data="neuro_accept"))
    kb.add(InlineKeyboardButton("❌ Отказаться", callback_data="neuro_decline"))
    kb.add(InlineKeyboardButton("📊 Инфо", callback_data="neuro_info"))
    await message.answer(
        f"🧠 <b>НЕЙРОКЛИЕНТ</b>\n📦 {item['name']}\n💰 Цена: {item['market_price']}₽\n"
        f"Тип: {data['client_name'].upper()} {data['emoji']}\n\n"
        f"{data['emoji']} <b>Клиент:</b> {data['message']}\n\n"
        f"<i>Раунд {data['round']}/{data['max_rounds']}</i>\nПиши ответ в чат или жми кнопку:",
        parse_mode="HTML", reply_markup=kb
    )

@dp.message_handler(state=GameState.playing)
async def neuro_text_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in active_chats or active_chats[user_id]["finished"]: return
    resp = neuro_chat(user_id, message.text)
    if "error" in resp: return await message.answer("Диалог завершён. /chat — новый")
    kb = InlineKeyboardMarkup(row_width=2)
    if resp["finished"]:
        if resp["result"] == "sold":
            kb.add(InlineKeyboardButton("🎉 Оформить продажу", callback_data="neuro_complete"))
        else:
            kb.add(InlineKeyboardButton("🔄 Новый клиент", callback_data="new_neuro"))
        kb.add(InlineKeyboardButton("🔙 Меню", callback_data="action_back"))
    else:
        kb.add(InlineKeyboardButton("💰 Предложить", callback_data="neuro_offer"))
        kb.add(InlineKeyboardButton("✅ Согласиться", callback_data="neuro_accept"))
        kb.add(InlineKeyboardButton("❌ Отказаться", callback_data="neuro_decline"))
    txt = f"{resp['emoji']} <b>Клиент:</b> {resp['message']}"
    if resp["finished"]: txt += f"\n\n⚠️ Диалог завершён! {'🎉 Готов купить!' if resp['result'] == 'sold' else '👋 Ушёл.'}"
    await message.answer(txt, parse_mode="HTML", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "action_neuro", state=GameState.playing)
async def neuro_btn(callback: CallbackQuery):
    await neuro_start_cmd(callback.message)

@dp.callback_query_handler(lambda c: c.data == "neuro_offer", state=GameState.playing)
async def neuro_offer_btn(callback: CallbackQuery):
    s = get_chat_status(callback.from_user.id)
    if not s: return await callback.answer("Нет диалога")
    await callback.message.answer(f"Цена: {s['price']}₽ | Предложение: {s['current_offer']}₽\nНапиши встречную цену (число):")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "neuro_accept", state=GameState.playing)
async def neuro_accept_btn(callback: CallbackQuery):
    user_id = callback.from_user.id
    s = get_chat_status(user_id)
    if not s: return await callback.answer("Нет диалога")
    await neuro_chat(user_id, f"Согласен на {s['current_offer']}₽")
    await neuro_complete_sale(callback, s)

@dp.callback_query_handler(lambda c: c.data == "neuro_decline", state=GameState.playing)
async def neuro_decline_btn(callback: CallbackQuery):
    user_id = callback.from_user.id
    neuro_chat(user_id, "Нет, не устраивает.")
    end_chat(user_id)
    await callback.message.edit_text("❌ Отказано. /chat — новый клиент")

@dp.callback_query_handler(lambda c: c.data == "neuro_info", state=GameState.playing)
async def neuro_info_btn(callback: CallbackQuery):
    s = get_chat_status(callback.from_user.id)
    if not s: return await callback.answer("Нет диалога")
    cl = CLIENT_TYPES[s["client_type"]]
    await callback.answer(f"{cl['name'].upper()} {cl['mood_emoji']} | Терпение: {s['round']}/{s['max_rounds']} | Скидка: {int((1-cl['discount_range'][0])*100)}-{int((1-cl['discount_range'][1])*100)}%", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == "neuro_complete", state=GameState.playing)
async def neuro_complete_btn(callback: CallbackQuery):
    s = get_chat_status(callback.from_user.id)
    if s: await neuro_complete_sale(callback, s)
    else: await callback.answer("Диалог не найден")

@dp.callback_query_handler(lambda c: c.data == "new_neuro")
async def new_neuro_btn(callback: CallbackQuery):
    await neuro_start_cmd(callback.message)

async def neuro_complete_sale(callback, status):
    user_id = callback.from_user.id
    p = get_player(user_id)
    for i, item in enumerate(p["inventory"]):
        if item["name"] == status["item"]:
            sold = p["inventory"].pop(i)
            profit = status["current_offer"] - sold["buy_price"]
            p["balance"] += status["current_offer"]
            p["total_earned"] += profit; p["items_sold"] += 1
            p["reputation"] = min(100, p["reputation"] + 5)
            add_rep(user_id, random.randint(2, 5), f"Продажа нейроклиенту: {sold['name']}")
            if status["client_type"] == "angry":
                get_user_rep(user_id)["angry_deals"] += 1
                add_rep(user_id, 3, "Успешная продажа злому клиенту")
            if status["current_offer"] > status["price"] * 0.9:
                get_user_rep(user_id)["haggle_wins"] += 1
            check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"], "scam_times": p["scam_times"]})
            save_json(REPUTATION_FILE, rep_data)
            end_chat(user_id)
            await callback.message.answer(
                f"🎉 <b>ПРОДАНО!</b>\n📦 {sold['name']}\n💰 Цена: {status['current_offer']}₽\n💵 Прибыль: {profit}₽\n💼 Баланс: {p['balance']}₽",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🔄 Новый клиент", callback_data="new_neuro"),
                    InlineKeyboardButton("🏠 Меню", callback_data="action_back")
                )
            )
            return
    await callback.message.answer("Товар не найден."); end_chat(user_id)

# ==================== ИГРА: ДЕЙСТВИЯ ====================
@dp.callback_query_handler(lambda c: c.data == "action_buy", state=GameState.playing)
async def show_suppliers(callback: CallbackQuery):
    user_id = callback.from_user.id
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    kb = InlineKeyboardMarkup(row_width=1)
    for s in supps:
        kb.add(InlineKeyboardButton(f"{s['emoji']} {s['name']} | ⭐{s['rating']} | Кид:{s['scam_chance']}%", callback_data=f"supplier_{supps.index(s)}"))
    kb.add(InlineKeyboardButton("🔙 Меню", callback_data="action_back"))
    vip_txt = "\n👑 VIP-поставщик доступен!\n" if is_vip(user_id) else ""
    await callback.message.edit_text(f"🏭 <b>ПОСТАВЩИКИ:</b>{vip_txt}\nВыше рейтинг — надёжнее, но дороже.", parse_mode="HTML", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("supplier_"), state=GameState.playing)
async def show_supplier_items(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    sup = supps[idx]
    items = random.sample(BASE_ITEMS, min(4, len(BASE_ITEMS)))
    kb = InlineKeyboardMarkup(row_width=1)
    for i, it in enumerate(items):
        kb.add(InlineKeyboardButton(f"{it['cat']} {it['name']} — {get_item_price(it['base_price'], sup)}₽", callback_data=f"buyitem_{i}"))
    kb.add(InlineKeyboardButton("🔄 Обновить", callback_data=f"supplier_{idx}"))
    kb.add(InlineKeyboardButton("🔙 К поставщикам", callback_data="action_buy"))
    kb.add(InlineKeyboardButton("🏠 Меню", callback_data="action_back"))
    await state.update_data(current_supplier_idx=idx, supplier_items=items)
    await callback.message.edit_text(
        f"{sup['emoji']} <b>{sup['name']}</b>\n⭐{sup['rating']}/10 | ⚠️Кид:{sup['scam_chance']}%\nВыбери товар:",
        parse_mode="HTML", reply_markup=kb
    )

@dp.callback_query_handler(lambda c: c.data.startswith("buyitem_"), state=GameState.playing)
async def buy_item(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item_idx = int(callback.data.split("_")[1])
    sup_idx = data.get("current_supplier_idx", 0)
    items = data.get("supplier_items", [])
    user_id = callback.from_user.id
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    sup = supps[sup_idx]
    if item_idx >= len(items): return await callback.answer("Ошибка")
    item = items[item_idx]
    p = get_player(user_id)
    price = int(get_item_price(item["base_price"], sup) * p["rep_mult"]["supplier_discount"])
    if p["balance"] < price: return await callback.answer("❌ Мало денег!")
    eff_scam = int(sup["scam_chance"] * p["rep_mult"]["scam_reduce"])
    if random.randint(1, 100) <= eff_scam:
        p["balance"] -= price; p["total_spent"] += price; p["scam_times"] += 1
        p["reputation"] = max(0, p["reputation"] - 5)
        add_rep(user_id, -5, f"Кинул {sup['name']}")
        await callback.message.edit_text(
            f"💀 <b>КИНУЛИ!</b>\n{sup['name']} пропал.\nПотеряно: {price}₽\nБаланс: {p['balance']}₽\n⚠️ Репутация -5",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🏠 Меню", callback_data="action_back"))
        )
        return await check_game_over(callback, p)
    p["balance"] -= price; p["total_spent"] += price
    demand = p["market_demand"].get(item["cat"], 1.0)
    p["inventory"].append({"name": f"{item['cat']} {item['name']}", "cat": item["cat"], "buy_price": price, "market_price": get_market_price(item["base_price"], demand), "base_price": item["base_price"]})
    if sup["rating"] >= 8: add_rep(user_id, 1, f"Покупка у {sup['name']}")
    if sup["name"] == VIP_SUPPLIER["name"]:
        get_user_rep(user_id)["vip_purchases"] += 1; add_rep(user_id, 2, "VIP-покупка")
    check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"], "scam_times": p["scam_times"]})
    save_json(REPUTATION_FILE, rep_data)
    await callback.message.edit_text(
        f"✅ <b>КУПЛЕНО!</b>\n📦 {item['cat']} {item['name']}\n💰 Закуп: {price}₽\n💼 Баланс: {p['balance']}₽\n📦 Инвентарь: {len(p['inventory'])}",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔄 Ещё", callback_data=f"supplier_{sup_idx}"),
            InlineKeyboardButton("🏠 Меню", callback_data="action_back")
        )
    )

@dp.callback_query_handler(lambda c: c.data == "action_inventory", state=GameState.playing)
async def show_inventory(callback: CallbackQuery):
    p = get_player(callback.from_user.id)
    if not p["inventory"]:
        return await callback.message.edit_text("📦 Пусто.", reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🏭 Закупиться", callback_data="action_buy"),
            InlineKeyboardButton("🏠 Меню", callback_data="action_back")
        ))
    kb = InlineKeyboardMarkup(row_width=1)
    for i, it in enumerate(p["inventory"]):
        kb.add(InlineKeyboardButton(f"{it['name']} | Закуп:{it['buy_price']}₽ | ~{it['market_price']}₽", callback_data=f"sell_{i}"))
    kb.add(InlineKeyboardButton("🏠 Меню", callback_data="action_back"))
    await callback.message.edit_text(format_inventory(p["inventory"]) + "\n\nВыбери для продажи:", parse_mode="HTML", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("sell_"), state=GameState.playing)
async def try_sell(callback: CallbackQuery, state: FSMContext):
    item_idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    p = get_player(user_id)
    if item_idx >= len(p["inventory"]): return await callback.answer("Нет товара")
    item = p["inventory"][item_idx]
    buyer = random.choice(BUYER_NAMES)
    demand = p["market_demand"].get(item["cat"], 1.0)
    if random.random() > min(0.9, demand * 0.6):
        msg = random.choice(BUYER_NOT_INTERESTED).format(name=buyer, cat=item["cat"])
        return await callback.message.edit_text(msg + "\n\nПопробуй другой товар.", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("📦 Инвентарь", callback_data="action_inventory"), InlineKeyboardButton("🏠 Меню", callback_data="action_back")))
    offer = int(item["market_price"] * random.uniform(0.7, 1.1))
    await state.update_data(selling_item_idx=item_idx, buyer_offer=offer, buyer_name=buyer)
    msg = random.choice(BUYER_HAGGLE_MESSAGES).format(name=buyer, offer=offer)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("✅ Да", callback_data="accept_offer"))
    kb.add(InlineKeyboardButton("📈 Торг +10%", callback_data="haggle_up"))
    kb.add(InlineKeyboardButton("❌ Нет", callback_data="decline_offer"))
    await callback.message.edit_text(
        f"👤 <b>{buyer}</b>\n📦 {item['name']}\n💰 Закуп: {item['buy_price']}₽ | Рынок: ~{item['market_price']}₽\n\n{msg}\n\nОтвет:",
        parse_mode="HTML", reply_markup=kb
    )

@dp.callback_query_handler(lambda c: c.data == "accept_offer", state=GameState.playing)
async def accept_offer(callback: CallbackQuery, state: FSMContext):
    await complete_sale(callback, state, 0)

@dp.callback_query_handler(lambda c: c.data == "haggle_up", state=GameState.playing)
async def haggle_up(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    offer = data.get("buyer_offer", 0)
    new_offer = int(offer * 1.1)
    user_id = callback.from_user.id
    p = get_player(user_id)
    chance = 0.3 + (p["reputation"] / 100) * 0.4 + p["rep_mult"]["haggle_bonus"]
    if random.random() < chance:
        await state.update_data(buyer_offer=new_offer)
        await complete_sale(callback, state, new_offer - offer)
    else:
        await callback.message.edit_text(f"👤 Покупатель: ❌ Не, дорого. Ушёл.", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("📦 Инвентарь", callback_data="action_inventory"), InlineKeyboardButton("🏠 Меню", callback_data="action_back")))

@dp.callback_query_handler(lambda c: c.data == "decline_offer", state=GameState.playing)
async def decline_offer(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("👤 Покупатель: 👋 Ладно, бывай.", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("📦 Инвентарь", callback_data="action_inventory"), InlineKeyboardButton("🏠 Меню", callback_data="action_back")))

async def complete_sale(callback, state, haggle_bonus):
    data = await state.get_data()
    item_idx = data.get("selling_item_idx", 0)
    buyer = data.get("buyer_name", "Покупатель")
    final = data.get("buyer_offer", 0)
    user_id = callback.from_user.id
    p = get_player(user_id)
    if item_idx >= len(p["inventory"]): return await callback.answer("Ошибка")
    item = p["inventory"].pop(item_idx)
    p["balance"] += final
    profit = final - item["buy_price"]
    p["total_earned"] += profit; p["items_sold"] += 1
    p["stat_earned_today"] += profit; p["stat_sold_today"] += 1
    p["reputation"] = min(100, p["reputation"] + random.randint(1, 5))
    add_rep(user_id, random.randint(1, 4), f"Продажа: {item['name']} за {final}₽")
    if haggle_bonus > 0:
        add_rep(user_id, 3, "Успешный торг")
        get_user_rep(user_id)["haggle_wins"] += 1
    check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"], "scam_times": p["scam_times"]})
    save_json(REPUTATION_FILE, rep_data)
    msg = random.choice(BUYER_ACCEPT_MESSAGES).format(name=buyer)
    bonus_txt = f"\n🔥 +{haggle_bonus}₽ торгом!" if haggle_bonus else ""
    await callback.message.edit_text(
        f"{msg}\n\n📦 {item['name']}\n💰 Цена: {final}₽\n💵 Прибыль: {profit}₽{bonus_txt}\n💼 Баланс: {p['balance']}₽\n⭐ Реп: {p['reputation']}/100",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("📦 Инвентарь", callback_data="action_inventory"), InlineKeyboardButton("🏠 Меню", callback_data="action_back"))
    )
    await check_game_over(callback, p)

@dp.callback_query_handler(lambda c: c.data == "action_stats", state=GameState.playing)
async def show_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    dl = [f"{'📈' if m>1 else '📉' if m<1 else '➡️'} {c}: x{m:.1f}" for c, m in p["market_demand"].items()]
    ref_n = len(referral_data[str(user_id)]["invited"])
    vip = "👑 ДА" if is_vip(user_id) else "❌ Нет"
    await callback.message.edit_text(
        f"{format_stats(p)}\n\n👥 Рефералы: {ref_n}\n👑 VIP: {vip}\n\n📊 <b>СПРОС:</b>\n" + "\n".join(dl),
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔗 Рефералы", callback_data="action_ref"),
            InlineKeyboardButton("🏆 Репутация", callback_data="action_rep"),
            InlineKeyboardButton("🏠 Меню", callback_data="action_back")
        )
    )

@dp.callback_query_handler(lambda c: c.data == "action_ref", state="*")
async def ref_from_menu(callback: CallbackQuery):
    await ref_cmd(callback.message)

@dp.callback_query_handler(lambda c: c.data == "action_rep", state="*")
async def rep_from_menu(callback: CallbackQuery):
    await rep_cmd(callback.message)

@dp.callback_query_handler(lambda c: c.data == "action_nextday", state=GameState.playing)
async def next_day(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    summary = f"🌙 <b>ИТОГИ ДНЯ {p['day']}</b>\n💰 Заработано: {p['stat_earned_today']}₽\n📋 Продано: {p['stat_sold_today']} шт.\n💼 Баланс: {p['balance']}₽"
    p["day"] += 1; p["stat_earned_today"] = 0; p["stat_sold_today"] = 0
    for c in CATEGORIES: p["market_demand"][c] = max(0.3, min(3.0, p["market_demand"][c] * random.uniform(0.85, 1.15)))
    event = generate_daily_event(); p["current_event"] = event
    if event: apply_market_event(p, event)
    et = f"\n\n{event['text']}" if event else ""
    if p["inventory"] and random.random() < 0.2:
        for it in p["inventory"]: it["market_price"] = int(it["market_price"] * random.uniform(0.7, 0.95))
        et += "\n⚠️ Товары залежались — потеря в цене."
    vip_txt = "\n👑 VIP" if is_vip(user_id) else ""
    check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"], "scam_times": p["scam_times"]})
    save_json(REPUTATION_FILE, rep_data)
    await callback.message.edit_text(f"{summary}\n\n☀️ <b>ДЕНЬ {p['day']}</b>{vip_txt}{et}\n\nВыбери действие:", parse_mode="HTML", reply_markup=get_main_keyboard(user_id))

@dp.callback_query_handler(lambda c: c.data == "action_end", state=GameState.playing)
async def end_game(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    p = get_player(user_id)
    await state.finish()
    if p["balance"] >= 50000: result = "🏆 <b>ПОБЕДА!</b> Ты раскрутился!"
    elif p["balance"] <= 0: result = "💀 <b>БАНКРОТ!</b>"
    else: result = "🎮 Игра окончена."
    check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"], "scam_times": p["scam_times"]})
    save_json(REPUTATION_FILE, rep_data)
    await callback.message.edit_text(
        f"{result}\n\n{format_stats(p)}\n👥 Рефералы: {len(referral_data[str(user_id)]['invited'])}\n\n"
        f"🔗 Ссылка:\n<code>{get_ref_link(user_id)}</code>\n\n"
        f"Реальный заработок → {CHANNEL_LINK}",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔄 Ещё раз", callback_data="restart_game"),
            InlineKeyboardButton("🔗 Рефералы", callback_data="action_ref")
        )
    )

@dp.callback_query_handler(lambda c: c.data == "restart_game")
async def restart_game(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in players: del players[user_id]
    await callback.message.edit_text("🔄 Напиши /play")

@dp.callback_query_handler(lambda c: c.data == "action_back", state=GameState.playing)
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    et = f"\n\n{p['current_event']['text']}" if p.get("current_event") else ""
    vip_txt = "\n👑 VIP" if is_vip(user_id) else ""
    await callback.message.edit_text(f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽{vip_txt}{et}\n\nДействие:", parse_mode="HTML", reply_markup=get_main_keyboard(user_id))

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    print("🎮 ReSell Tycoon Full готов!")
    executor.start_polling(dp, skip_updates=True)