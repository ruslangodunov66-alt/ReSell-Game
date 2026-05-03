import random
import hashlib
import json
import os
import asyncio
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
CHANNEL_NAME = 'ReSell👾'
BOT_USERNAME = 'R-Game'
DEEPSEEK_API_KEY = "sk-9515baacbf9b44bfbf45caadf97e5012"

client_openai = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# ==================== ФАЙЛЫ ====================
REPUTATION_FILE = "reputation_data.json"
REFERRAL_FILE = "referrals.json"
LEARNING_FILE = "learning_progress.json"

# ==================== ОБУЧАЮЩАЯ СИСТЕМА ====================
LESSONS = [
    {
        "id": 1, "title": "🚀 Основы товарного бизнеса",
        "text": (
            "📚 <b>УРОК 1: ОСНОВЫ ТОВАРКИ</b>\n\n"
            "<b>Товарный бизнес (товарка)</b> — это перепродажа вещей.\n\n"
            "🔹 <b>Где брать товар?</b>\n"
            "• Авито (б/у вещи дешевле рынка)\n"
            "• Оптовые рынки (Садовод, Люблино в Москве)\n"
            "• Китай (Taobao, 1688 через карго)\n"
            "• Секонд-хенды и стоки\n"
            "• Telegram-каналы оптовиков\n\n"
            "🔹 <b>Как заработать?</b>\n"
            "Купил дешевле → продал дороже = прибыль\n\n"
            "🔹 <b>С чего начать?</b>\n"
            "1. Выбери нишу (одежда, электроника, хобби)\n"
            "2. Найди где дёшево купить\n"
            "3. Сделай хорошие фото\n"
            "4. Выложи на Авито/Юлу/Telegram\n"
            "5. Общайся с покупателями\n\n"
            "<b>💰 Стартовый бюджет: от 1000₽</b>"
        ),
        "reward": 500
    },
    {
        "id": 2, "title": "📊 Анализ рынка и спрос",
        "text": (
            "📚 <b>УРОК 2: АНАЛИЗ РЫНКА</b>\n\n"
            "<b>Как понять что продавать?</b>\n\n"
            "🔹 <b>Проверь спрос:</b>\n"
            "• Поищи товар на Авито — много объявлений?\n"
            "• Посмотри проданные лоты (фильтр «Проданные»)\n"
            "• Зайди в тематические группы ВК/ТГ\n\n"
            "🔹 <b>Сезонность:</b>\n"
            "• Осенью — куртки, обувь, школа\n"
            "• Зимой — пуховики, подарки\n"
            "• Весной — демисезон, велосипеды\n"
            "• Летом — футболки, купальники\n\n"
            "🔹 <b>Тренды:</b>\n"
            "• Следи за блогерами — что носят?\n"
            "• Смотри за модой в соцсетях\n\n"
            "<b>💡 Совет:</b> Покупай когда дёшево, продавай когда спрос высокий!"
        ),
        "reward": 500
    },
    {
        "id": 3, "title": "🏭 Работа с поставщиками",
        "text": (
            "📚 <b>УРОК 3: ПОСТАВЩИКИ</b>\n\n"
            "<b>Как не попасть на кидалово?</b>\n\n"
            "🔹 <b>Проверка поставщика:</b>\n"
            "• Попроси отзывы и контакты клиентов\n"
            "• Начни с маленького заказа (тестовый)\n"
            "• Проверь по чёрным спискам в ТГ\n"
            "• Никогда не вноси 100% предоплату\n\n"
            "🔹 <b>Типы поставщиков:</b>\n"
            "• 🏭 Крупные оптовики — дёшево, мин. заказ\n"
            "• 👕 Мелкие поставщики — дороже, без мин. заказа\n"
            "• 🎲 Сомнительные — очень дёшево, высокий риск\n\n"
            "<b>⚠️ Правило:</b> Если цена слишком низкая — это подозрительно!"
        ),
        "reward": 700
    },
    {
        "id": 4, "title": "💬 Общение с покупателями",
        "text": (
            "📚 <b>УРОК 4: ПРОДАЖИ И ОБЩЕНИЕ</b>\n\n"
            "<b>Как продать дороже?</b>\n\n"
            "🔹 <b>Фото:</b>\n"
            "• Хороший свет, чистота\n"
            "• Все ракурсы, бирки, дефекты\n"
            "• На человеке или на манекене\n\n"
            "🔹 <b>Описание:</b>\n"
            "• Бренд, размер, состояние\n"
            "• Почему продаёшь (честно)\n"
            "• Ключевые слова для поиска\n\n"
            "🔹 <b>Общение:</b>\n"
            "• Отвечай быстро (в течение часа)\n"
            "• Не груби даже если клиент злой\n"
            "• Предлагай альтернативы\n"
            "• Торгуйся но знай свою минимальную цену\n\n"
            "<b>💡 Лайфхак:</b> Поставь цену на 20% выше желаемой — будет пространство для торга."
        ),
        "reward": 700
    },
    {
        "id": 5, "title": "📈 Продвижение на Авито",
        "text": (
            "📚 <b>УРОК 5: ПРОДВИЖЕНИЕ</b>\n\n"
            "<b>Как поднять объявление в топ?</b>\n\n"
            "🔹 <b>Бесплатные методы:</b>\n"
            "• Обновляй объявление каждые 24 часа\n"
            "• Добавляй ключевые слова в описание\n"
            "• Ставь правильную категорию\n"
            "• Делай много фото (больше 5)\n\n"
            "🔹 <b>Платные методы:</b>\n"
            "• Продвижение на Авито (от 50₽/день)\n"
            "• Турбо-продажа (фиксированная цена)\n"
            "• Выделение цветом\n\n"
            "🔹 <b>Социальные сети:</b>\n"
            "• Telegram-каналы барахолок\n"
            "• Группы ВК своего города\n"
            "• Instagram с хештегами\n\n"
            "<b>💡 Совет:</b> Сделай 5-10 объявлений — чем больше, тем выше шанс продажи!"
        ),
        "reward": 1000
    },
]

# Советы при действиях
TIPS = {
    "buy": [
        "💡 <b>Совет:</b> Всегда проверяй поставщика перед крупной сделкой. Начни с маленького заказа.",
        "💡 <b>Совет:</b> Смотри на сезонность! Куртки зимой продаются лучше чем летом.",
        "💡 <b>Совет:</b> Не вкладывай все деньги в один товар — диверсифицируй!",
    ],
    "publish": [
        "💡 <b>Совет:</b> Сделай 5-10 фото товара при хорошем свете. Это увеличит шанс продажи на 40%.",
        "💡 <b>Совет:</b> В описании укажи все размеры и дефекты — это вызывает доверие.",
        "💡 <b>Совет:</b> Цену ставь на 20% выше желаемой — оставь пространство для торга.",
    ],
    "sale": [
        "💡 <b>Совет:</b> После продажи спроси у клиента отзыв — это повысит доверие к твоему профилю.",
        "💡 <b>Совет:</b> Откладывай 30% прибыли на закуп нового товара.",
        "💡 <b>Совет:</b> Записывай все расходы и доходы в таблицу — видь реальную прибыль.",
    ],
    "chat": [
        "💡 <b>Совет:</b> Если клиент грубит — не отвечай тем же. Вежливость продаёт лучше агрессии.",
        "💡 <b>Совет:</b> Предложи встретиться у метро или в ТЦ — это безопасно для обоих.",
        "💡 <b>Совет:</b> Если клиент просит скидку — попроси что-то взамен (например, быструю оплату).",
    ],
}

# ==================== ПОСТАВЩИКИ ====================
SUPPLIERS = [
    {"name": "🏭 MegaStock", "rating": 9, "price_mult": 1.4, "scam_chance": 0, "emoji": "🏭", "desc": "Крупный оптовик. Надёжно, но дорого."},
    {"name": "👕 OldGarage", "rating": 7, "price_mult": 1.15, "scam_chance": 10, "emoji": "👕", "desc": "Стоковый магазин. Хороший баланс цены и риска."},
    {"name": "🎒 Vintager", "rating": 5, "price_mult": 0.85, "scam_chance": 25, "emoji": "🎒", "desc": "Перекупщик с опытом. Средние цены, средний риск."},
    {"name": "💸 DumpPrice", "rating": 3, "price_mult": 0.55, "scam_chance": 50, "emoji": "💸", "desc": "Демпинг-поставщик. Дёшево, но рискованно."},
    {"name": "🎲 LuckyBag", "rating": 1, "price_mult": 0.3, "scam_chance": 75, "emoji": "🎲", "desc": "Кот в мешке. Очень дёшево, почти наверняка кинет."},
]
VIP_SUPPLIER = {"name": "👑 PremiumStock", "rating": 10, "price_mult": 1.05, "scam_chance": 0, "emoji": "👑", "desc": "VIP-поставщик. Лучшие цены, 100% надёжность."}

# ==================== ТОВАРЫ С ОБУЧАЮЩИМИ ОПИСАНИЯМИ ====================
BASE_ITEMS = [
    {"cat": "👖 Джинсы", "name": "Levi's 501 Vintage", "base_price": 2000, "lesson": "Винтажные джинсы Levi's всегда в цене. Проверяй бирку и страну производства."},
    {"cat": "👖 Джинсы", "name": "Carhartt WIP Denim", "base_price": 3500, "lesson": "Carhartt — бренд рабочий одежды, популярен в стритвире. Ищи оригинал, много подделок."},
    {"cat": "👕 Худи", "name": "Adidas Originals Hoodie", "base_price": 2500, "lesson": "Классика спортивного стиля. Трёхполоска всегда продаётся. Смотри на состояние манжет."},
    {"cat": "👕 Худи", "name": "Nike ACG Fleece", "base_price": 3000, "lesson": "ACG (All Conditions Gear) — линейка Nike для активного отдыха. Ценится выше обычных."},
    {"cat": "🧥 Куртки", "name": "The North Face Nuptse", "base_price": 5000, "lesson": "Легендарный пуховик. Осенью-зимой цена взлетает в 2 раза. Проверяй подлинность."},
    {"cat": "🧥 Куртки", "name": "Alpha Industries MA-1", "base_price": 4000, "lesson": "Классическая куртка пилотов. Всегда в моде. Смотри на состояние резинок."},
    {"cat": "👟 Кроссы", "name": "Nike Air Max 90", "base_price": 3500, "lesson": "Культовая модель кроссовок. Размерная сетка маломерит — учитывай при продаже."},
    {"cat": "👟 Кроссы", "name": "Adidas Samba OG", "base_price": 2800, "lesson": "Samba сейчас в тренде. Новые стоят 2x от этих. Проверяй язычок и стельку."},
    {"cat": "🎒 Аксессуары", "name": "Stüssy Tote Bag", "base_price": 1500, "lesson": "Сумка-шоппер от культового бренда. Аксессуары всегда легче продать чем одежду."},
    {"cat": "🎒 Аксессуары", "name": "New Era 59Fifty Cap", "base_price": 1200, "lesson": "Кепки New Era популярны круглый год. Смотри на состояние козырька."},
    {"cat": "👕 Худи", "name": "Supreme Box Logo", "base_price": 1800, "lesson": "Supreme — самый хайповый бренд. Оригинал стоит дорого, много подделок. Проверяй бирку!"},
    {"cat": "🧥 Куртки", "name": "Stone Island Soft Shell", "base_price": 6000, "lesson": "Stone Island — премиум бренд. Наличие патча (нашивки) ОБЯЗАТЕЛЬНО для продажи."},
    {"cat": "👟 Кроссы", "name": "New Balance 990v3", "base_price": 4200, "lesson": "New Balance — комфорт и стиль. Модели из США ценятся выше азиатских."},
    {"cat": "🎒 Аксессуары", "name": "Patagonia Hip Pack", "base_price": 2000, "lesson": "Patagonia — эко-бренд, популярен у молодёжи. Поясные сумки сейчас в тренде."},
    {"cat": "👖 Джинсы", "name": "Wrangler Retro", "base_price": 1800, "lesson": "Wrangler — американская классика. Дешевле Levi's но качество не хуже."},
    {"cat": "🧥 Куртки", "name": "Patagonia Down Jacket", "base_price": 5500, "lesson": "Пуховик Patagonia — тёплый и экологичный. Зимой цена вырастает на 50-70%."},
]

CATEGORIES = ["👖 Джинсы", "👕 Худи", "🧥 Куртки", "👟 Кроссы", "🎒 Аксессуары"]

MARKET_EVENTS = [
    {"text": "📰 Хайп на винтажные джинсы! Самое время продавать Levi's.", "cat": "👖 Джинсы", "mult": 1.5},
    {"text": "📰 Дожди — спрос на куртки вырос. Выставляй быстрее!", "cat": "🧥 Куртки", "mult": 1.4},
    {"text": "📰 Все хотят кроссовки! Отличное время для продажи.", "cat": "👟 Кроссы", "mult": 1.5},
    {"text": "📰 Лето близко — джинсы падают в цене. Закупай дёшево на зиму.", "cat": "👖 Джинсы", "mult": 0.6},
    {"text": "📰 Авито ввело комиссию 15%. Учитывай это в цене!", "cat": None, "mult": 0.8},
    {"text": "📰 Ретро-аксессуары в тренде! Сумки и кепки на пике.", "cat": "🎒 Аксессуары", "mult": 1.6},
]

# ==================== НЕЙРОКЛИЕНТЫ ====================
CLIENT_TYPES = {
    "angry": {
        "system_prompt": "Ты покупатель на Авито. Ты недоволен ценой, грубишь (без мата), торгуешься жёстко, сбиваешь 30-50%. Можешь написать 'дорого'. Если уступают — берёшь. НИКОГДА не говори что ты злой. Коротко, 1-2 предложения.",
        "discount_range": (0.5, 0.7), "patience": 3, "remind_time": (120, 300)
    },
    "kind": {
        "system_prompt": "Ты покупатель, вежливый и добрый. Просишь скидку 10-20%, хвалишь товар. НИКОГДА не говори что ты добрый. Коротко, 1-2 предложения.",
        "discount_range": (0.8, 0.9), "patience": 5, "remind_time": (180, 420)
    },
    "sly": {
        "system_prompt": "Ты покупатель-перекупщик. Хитрый, аргументируешь цену рынком, блефуешь. Сбиваешь 20-40%. НИКОГДА не говори что ты хитрый. Коротко.",
        "discount_range": (0.6, 0.8), "patience": 4, "remind_time": (150, 360)
    }
}

# ==================== РЕПУТАЦИЯ ====================
REPUTATION_LEVELS = {-100: "💀 ЧС", -50: "🔴 Ужасная", -10: "🟠 Плохая", 0: "🟡 Нейтральная", 25: "🟢 Хорошая", 50: "🔵 Отличная", 75: "🟣 Легенда", 90: "🟡 Золотая", 100: "👑 Бог товарки"}
ACHIEVEMENTS = [
    {"id": "first_sale", "name": "🎯 Первая продажа", "target": 1, "reward": 5},
    {"id": "seller_10", "name": "📦 Продавец", "target": 10, "reward": 10},
    {"id": "profit_5000", "name": "💰 Навар", "target": 5000, "reward": 5},
    {"id": "angry_win", "name": "😡 Укротитель", "target": 1, "reward": 10},
    {"id": "haggle_master", "name": "🎯 Мастер торга", "target": 1, "reward": 10},
    {"id": "lesson_3", "name": "📚 Ученик", "target": 3, "reward": 10},
    {"id": "lesson_all", "name": "🎓 Выпускник", "target": 5, "reward": 25},
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

# ==================== ЗАГРУЗКА ДАННЫХ ====================
def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f: return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def load_all():
    global referral_data, rep_data, learning_data
    referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False}, load_json(REFERRAL_FILE, {}))
    rep_data = load_json(REPUTATION_FILE, {})
    learning_data = load_json(LEARNING_FILE, {})

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

async def send_msg(user_id, text, parse_mode="HTML", reply_markup=None):
    await del_prev(user_id)
    await del_user_msgs(user_id)
    msg = await bot.send_message(user_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    last_bot_message[user_id] = msg.message_id
    return msg

async def edit_msg(message, text, parse_mode="HTML", reply_markup=None):
    await del_user_msgs(message.chat.id)
    try: await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except: pass

# ==================== РЕФЕРАЛЫ ====================
def gen_ref(user_id): return hashlib.md5(str(user_id).encode()).hexdigest()[:8]
def ref_link(user_id): return f"https://t.me/{BOT_USERNAME}?start=ref_{gen_ref(user_id)}"
def top_refs(limit=10):
    s = [(uid, len(d["invited"])) for uid, d in referral_data.items()]
    s.sort(key=lambda x: x[1], reverse=True)
    return s[:limit]
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
    u["rep_history"].append({"change": amount, "reason": reason, "total": u["score"]})
    if len(u["rep_history"]) > 20: u["rep_history"] = u["rep_history"][-20:]
    save_json(REPUTATION_FILE, rep_data)
    return u["score"]

def rep_mult(score):
    if score >= 75: return {"supplier_discount": 0.85, "scam_reduce": 0.2, "haggle_bonus": 0.25}
    elif score >= 50: return {"supplier_discount": 0.90, "scam_reduce": 0.4, "haggle_bonus": 0.15}
    elif score >= 25: return {"supplier_discount": 0.95, "scam_reduce": 0.6, "haggle_bonus": 0.05}
    elif score >= 0: return {"supplier_discount": 1.0, "scam_reduce": 0.8, "haggle_bonus": 0.0}
    else: return {"supplier_discount": 1.5, "scam_reduce": 1.5, "haggle_bonus": -0.3}

def check_ach(user_id, pd=None):
    u = get_rep(user_id)
    if pd:
        u["total_sales"] = pd.get("items_sold", 0)
        u["total_profit"] = pd.get("total_earned", 0)
        u["max_balance"] = max(u["max_balance"], pd.get("balance", 0))
    new_a = []
    for a in ACHIEVEMENTS:
        if a["id"] in u["achievements"]: continue
        earn = False
        if a["id"] == "first_sale" and u["total_sales"] >= 1: earn = True
        elif a["id"] == "seller_10" and u["total_sales"] >= 10: earn = True
        elif a["id"] == "profit_5000" and u["total_profit"] >= 5000: earn = True
        elif a["id"] == "angry_win" and u["angry_deals"] >= 1: earn = True
        elif a["id"] == "haggle_master" and u["haggle_wins"] >= 1: earn = True
        elif a["id"] == "lesson_3" and u["lessons_completed"] >= 3: earn = True
        elif a["id"] == "lesson_all" and u["lessons_completed"] >= 5: earn = True
        if earn:
            u["achievements"].append(a["id"])
            add_rep(user_id, a["reward"], f"Достижение: {a['name']}")
            new_a.append(a)
    save_json(REPUTATION_FILE, rep_data)
    return new_a

# ==================== ОБУЧЕНИЕ ====================
def get_learning(user_id):
    uid = str(user_id)
    if uid not in learning_data:
        learning_data[uid] = {"completed": [], "current": 1}
        save_json(LEARNING_FILE, learning_data)
    return learning_data[uid]

def complete_lesson(user_id, lesson_id):
    u = get_rep(user_id)
    l = get_learning(user_id)
    if lesson_id not in l["completed"]:
        l["completed"].append(lesson_id)
        u["lessons_completed"] = len(l["completed"])
        l["current"] = lesson_id + 1
        save_json(LEARNING_FILE, learning_data)
        save_json(REPUTATION_FILE, rep_data)
        # Награда
        lesson = next((ls for ls in LESSONS if ls["id"] == lesson_id), None)
        if lesson:
            if user_id in players:
                players[user_id]["balance"] += lesson["reward"]
            add_rep(user_id, 3, f"Урок: {lesson['title']}")
        check_ach(user_id)
        return True
    return False

# ==================== ИГРА ====================
def get_player(user_id):
    if user_id not in players:
        r = get_rep(user_id)
        rm = rep_mult(r["score"])
        players[user_id] = {
            "balance": 5000, "reputation": max(0, r["score"]),
            "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0,
            "items_sold": r["total_sales"], "scam_times": r["scam_survived"],
            "market_demand": {cat: 1.0 for cat in CATEGORIES},
            "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0,
            "rep_mult": rm,
        }
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

def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏭 ЗАКУПИТЬСЯ", callback_data="action_buy")],
        [InlineKeyboardButton(text="📦 ИНВЕНТАРЬ", callback_data="action_inventory")],
        [InlineKeyboardButton(text="📚 ОБУЧЕНИЕ", callback_data="action_learn"),
         InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="action_stats")],
        [InlineKeyboardButton(text="📈 СПРОС НА РЫНКЕ", callback_data="action_demand"),
         InlineKeyboardButton(text="🔗 РЕФЕРАЛЫ", callback_data="action_ref_menu")],
        [InlineKeyboardButton(text="⏩ СЛЕД. ДЕНЬ", callback_data="action_nextday"),
         InlineKeyboardButton(text="🏁 ЗАВЕРШИТЬ", callback_data="action_end")],
        [InlineKeyboardButton(text="🏆 РЕПУТАЦИЯ", callback_data="action_rep_menu")],
    ])

# ==================== НЕЙРОКЛИЕНТЫ ====================
def first_msg(client_type, item_name, price, offer):
    msgs = {
        "angry": [f"Здравствуйте! {item_name} за {price}₽? Цена завышена. Готов предложить {offer}₽.", f"Привет! {item_name} — {price}₽ дорого. Давайте {offer}₽?"],
        "kind": [f"Добрый день! {item_name} — отличная вещь! Но {price}₽ дороговато. Может {offer}₽?", f"Здравствуйте! Ищу {item_name}. Бюджет {offer}₽. Договоримся?"],
        "sly": [f"Привет! По {item_name}. Рынок щас — {offer}₽. Отдашь?", f"Здорово! {item_name} интересен. Кэш {offer}₽ прямо сейчас."],
    }
    return random.choice(msgs.get(client_type, msgs["kind"]))

def remind_msg(client_type, item_name, offer):
    msgs = {
        "angry": [f"Жду ответ по {item_name}. {offer}₽. Решайте!", f"Ну что? {item_name} за {offer}₽. Я серьёзно."],
        "kind": [f"Извините! {item_name} за {offer}₽ ещё в силе? :)", f"Напомню: {item_name}, моя цена {offer}₽."],
        "sly": [f"По {item_name} — нашёл вариант. Давай за {offer}₽?", f"Рынок меняется. {item_name} за {offer}₽. Решайся!"],
    }
    return random.choice(msgs.get(client_type, msgs["kind"]))

async def send_buyer(user_id, buyer_id, client_type, item_name, price, is_reminder=False):
    client = CLIENT_TYPES[client_type]
    chat_key = f"{user_id}_{buyer_id}"
    
    if not is_reminder:
        rm = rep_mult(get_rep(user_id)["score"])
        discount = random.uniform(*client["discount_range"]) + rm["haggle_bonus"]
        discount = max(0.3, min(0.95, discount))
        offer = int(price * discount)
        offer = (offer // 100) * 100 + 99
        if offer < 100: offer = price // 2
        
        msg = first_msg(client_type, item_name, price, offer)
        
        active_chats[chat_key] = {
            "user_id": user_id, "buyer_id": buyer_id, "client_type": client_type,
            "item": item_name, "price": price, "offer": offer,
            "history": [{"role": "system", "content": client["system_prompt"]}, {"role": "assistant", "content": msg}],
            "round": 1, "max_rounds": client["patience"], "finished": False,
            "reminders_sent": 0, "max_reminders": 2
        }
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 ОТВЕТИТЬ ПОКУПАТЕЛЮ", callback_data=f"nr_{user_id}_{buyer_id}")],
            [InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"nd_{user_id}_{buyer_id}")],
        ])
        
        await send_msg(user_id,
            f"📩 <b>НОВЫЙ ПОКУПАТЕЛЬ #{buyer_id}</b>\n\n"
            f"📦 {item_name} | 💰 Твоя цена: {price}₽\n\n"
            f"💬 <i>«{msg}»</i>\n\n"
            f"👉 Нажми <b>«ОТВЕТИТЬ»</b> и напиши ответ!",
            reply_markup=kb)
        
        if client["remind_time"]:
            task = asyncio.create_task(do_remind(user_id, buyer_id, random.randint(*client["remind_time"])))
            remind_timers[chat_key] = task
    else:
        chat = active_chats.get(chat_key)
        if not chat or chat["finished"]: return
        msg = remind_msg(client_type, item_name, chat["offer"])
        chat["history"].append({"role": "assistant", "content": msg})
        chat["reminders_sent"] += 1
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 ОТВЕТИТЬ", callback_data=f"nr_{user_id}_{buyer_id}")],
            [InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"nd_{user_id}_{buyer_id}")],
        ])
        
        await send_msg(user_id, f"🔔 <b>НАПОМИНАНИЕ #{buyer_id}</b>\n📦 {item_name}\n\n💬 <i>«{msg}»</i>\n\nНажми «ОТВЕТИТЬ»!", reply_markup=kb)
        
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
    pub = published_items[user_id]
    item = pub["item"]
    rm = rep_mult(get_rep(user_id)["score"])
    n = random.randint(1, 3)
    if rm["haggle_bonus"] > 0.1: n = min(3, n + 1)
    types = random.choices(list(CLIENT_TYPES.keys()), k=n)
    
    await send_msg(user_id,
        f"📱 <b>ОБЪЯВЛЕНИЕ РАБОТАЕТ!</b>\n\n"
        f"📦 {item['name']}\n💰 Цена: {item['market_price']}₽\n👥 Пишут: <b>{n}</b> чел.\n\n"
        f"{random.choice(TIPS['chat'])}\n\n<i>Отвечай им, торгуйся!</i>")
    
    pub["buyers_list"] = []
    for i, bt in enumerate(types):
        await asyncio.sleep(random.randint(5, 20))
        bid = i + 1
        pub["buyers_list"].append({"id": bid, "type": bt, "active": True})
        await send_buyer(user_id, bid, bt, item["name"], item["market_price"])

async def complete_sale(user_id, buyer_id, message=None):
    chat_key = f"{user_id}_{buyer_id}"
    chat = active_chats.get(chat_key)
    if not chat: return None
    
    p = get_player(user_id)
    item_name = chat["item"]
    final = chat["offer"]
    
    sold = None
    if user_id in published_items and published_items[user_id] and published_items[user_id]["item"]["name"] == item_name:
        sold = published_items[user_id]["item"]
        published_items[user_id] = None
    
    # Ищем в инвентаре
    for i, inv in enumerate(p["inventory"]):
        if inv["name"] == item_name:
            sold = p["inventory"].pop(i)
            break
    
    if not sold:
        if message: await send_msg(user_id, "❌ Ошибка: товар не найден в инвентаре.")
        return None
    
    profit = final - sold["buy_price"]
    p["balance"] += final
    p["total_earned"] += profit
    p["items_sold"] += 1
    p["stat_earned_today"] += profit
    p["stat_sold_today"] += 1
    p["reputation"] = min(100, p["reputation"] + 5)
    
    add_rep(user_id, random.randint(2, 5), f"Продажа: {item_name}")
    if chat["client_type"] == "angry": get_rep(user_id)["angry_deals"] += 1
    if final > sold["market_price"] * 0.9: get_rep(user_id)["haggle_wins"] += 1
    
    check_ach(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    
    if chat_key in remind_timers:
        remind_timers[chat_key].cancel()
        del remind_timers[chat_key]
    
    chat["finished"] = True
    
    if message:
        await send_msg(user_id,
            f"🎉 <b>ПРОДАНО!</b>\n\n📦 {item_name}\n💰 Цена: {final}₽\n💵 Прибыль: {profit}₽\n💼 Баланс: {p['balance']}₽\n⭐ Репутация: {p['reputation']}/100\n\n{random.choice(TIPS['sale'])}")
    
    return profit

# ==================== КОМАНДЫ ====================
@dp.message(Command('start'))
async def start_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_code = args[1][4:]
        referrer_id = None
        for uid in referral_data:
            if gen_ref(uid) == ref_code: referrer_id = uid; break
        if referrer_id and referrer_id != str(user_id) and user_id not in referral_data[referrer_id]["invited"]:
            referral_data[referrer_id]["invited"].append(user_id)
            save_json(REFERRAL_FILE, dict(referral_data))
            if int(referrer_id) in players: players[int(referrer_id)]["balance"] += 500
            try: await bot.send_message(int(referrer_id), f"🎉 Новый реферал! +500₽\n👥 Всего: {len(referral_data[referrer_id]['invited'])}", parse_mode="HTML")
            except: pass
    
    p = players.get(user_id)
    await del_user_msgs(user_id)
    
    if p and p.get("day", 0) > 0:
        r = get_rep(user_id)
        lvl = rep_level(r["score"])
        vip = is_vip(user_id)
        txt = f"👋 <b>С ВОЗВРАЩЕНИЕМ!</b>\n\n📅 День {p['day']} | 💰 {p['balance']}₽\n📦 Товаров: {len(p['inventory'])} | 📋 Продано: {p['items_sold']}\n⭐ Репутация: {lvl}\n{'👑 VIP!' if vip else ''}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 ПРОДОЛЖИТЬ", callback_data="continue_game")],
            [InlineKeyboardButton(text="📚 ОБУЧЕНИЕ", callback_data="action_learn")],
            [InlineKeyboardButton(text="🔄 НАЧАТЬ ЗАНОВО", callback_data="restart_game_confirm")],
        ])
        await send_msg(user_id, txt, reply_markup=kb)
    else:
        l = get_learning(user_id)
        txt = (
            "🎮 <b>RESELL TYCOON — ТРЕНАЖЁР ТОВАРНОГО БИЗНЕСА</b>\n\n"
            "Научись зарабатывать на перепродаже вещей!\n\n"
            "📖 <b>ЧТО ТЫ УЗНАЕШЬ:</b>\n"
            "• Где закупать товар дёшево\n"
            "• Как анализировать рынок\n"
            "• Как общаться с покупателями\n"
            "• Как продвигать объявления\n\n"
            "💰 <b>КАК ИГРАТЬ:</b>\n"
            "1. Пройди обучение (📚)\n"
            "2. Закупись у поставщиков\n"
            "3. Опубликуй товар в инвентаре\n"
            "4. Общайся с покупателями\n\n"
            f"📚 Пройдено уроков: {len(l['completed'])}/{len(LESSONS)}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 ПРОЙТИ ОБУЧЕНИЕ", callback_data="action_learn")],
            [InlineKeyboardButton(text="🚀 НАЧАТЬ ИГРУ", callback_data="start_new_game")],
            [InlineKeyboardButton(text="🔗 РЕФЕРАЛЫ", callback_data="ref_info")],
        ])
        await send_msg(user_id, txt, reply_markup=kb)

@dp.message(Command('play'))
async def play_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await del_user_msgs(user_id)
    r = get_rep(user_id)
    players[user_id] = {
        "balance": 5000, "reputation": max(0, r["score"]), "inventory": [],
        "day": 1, "total_earned": 0, "total_spent": 0,
        "items_sold": r["total_sales"], "scam_times": r["scam_survived"],
        "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None,
        "stat_earned_today": 0, "stat_sold_today": 0,
        "rep_mult": rep_mult(r["score"]),
    }
    p = players[user_id]
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    await state.set_state(GameState.playing)
    et = f"\n\n📰 {event['text']}" if event else ""
    vip_txt = "\n👑 VIP!" if is_vip(user_id) else ""
    demand = fmt_demand(p)
    await send_msg(user_id,
        f"🌟 <b>ДЕНЬ 1</b>\n💰 Баланс: 5 000₽{vip_txt}{et}\n\n"
        f"📊 <b>СПРОС НА РЫНКЕ:</b>\n{demand}\n\n"
        f"👇 <b>Что делать:</b>\n"
        f"1. Жми 🏭 ЗАКУПИТЬСЯ\n"
        f"2. Купи товары (смотри спрос!)\n"
        f"3. Зайди в 📦 ИНВЕНТАРЬ\n"
        f"4. Нажми на товар → Опубликовать\n"
        f"5. Жди покупателей и общайся!\n\n"
        f"📚 Не забудь пройти ОБУЧЕНИЕ!",
        reply_markup=main_kb())

@dp.message(Command('ref'))
async def ref_cmd(message: types.Message):
    user_id = message.from_user.id
    await del_user_msgs(user_id)
    link = ref_link(user_id)
    count = len(referral_data[str(user_id)]["invited"])
    vip = "👑 Ты в ТОП-3! VIP!" if is_vip(user_id) else ""
    await send_msg(user_id, f"🔗 <b>РЕФЕРАЛЫ:</b>\n\n<code>{link}</code>\n\n👥 Приглашено: {count}\n💰 Бонус: {count*500}₽\n{vip}")

@dp.message(Command('rep'))
async def rep_cmd(message: types.Message):
    user_id = message.from_user.id
    await del_user_msgs(user_id)
    p = players.get(user_id)
    pd = {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]} if p else None
    new_a = check_ach(user_id, pd)
    u = get_rep(user_id)
    lvl = rep_level(u["score"])
    rm = rep_mult(u["score"])
    bar = "█" * int((u["score"]+100)/200*10) + "░" * (10-int((u["score"]+100)/200*10))
    txt = f"🏆 <b>РЕПУТАЦИЯ: {lvl}</b>\n📊 [{bar}] {u['score']}/100\n\n📦 Продаж: {u['total_sales']}\n💰 Прибыль: {u['total_profit']}₽\n📚 Уроков: {u['lessons_completed']}/{len(LESSONS)}\n🏅 Достижений: {len(u['achievements'])}/{len(ACHIEVEMENTS)}"
    if new_a: txt += "\n\n🎉 <b>НОВЫЕ!</b>\n" + "\n".join(f"{a['name']} (+{a['reward']})" for a in new_a)
    await send_msg(user_id, txt)

@dp.message(Command('learn'))
async def learn_cmd(message: types.Message):
    user_id = message.from_user.id
    await del_user_msgs(user_id)
    await show_learning_menu(message, user_id)

async def show_learning_menu(message_or_callback, user_id):
    l = get_learning(user_id)
    kb = []
    for lesson in LESSONS:
        done = lesson["id"] in l["completed"]
        status = "✅" if done else "📖"
        kb.append([InlineKeyboardButton(text=f"{status} Урок {lesson['id']}: {lesson['title']}", callback_data=f"lesson_{lesson['id']}")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="back_to_start")])
    
    txt = f"📚 <b>ОБУЧЕНИЕ ТОВАРНОМУ БИЗНЕСУ</b>\n\nПройдено: {len(l['completed'])}/{len(LESSONS)}\n\n<i>Каждый урок — реальные знания + бонус к игре!</i>"
    
    if hasattr(message_or_callback, 'edit_text'):
        await edit_msg(message_or_callback, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("lesson_"))
async def show_lesson(callback: CallbackQuery):
    user_id = callback.from_user.id
    lesson_id = int(callback.data.split("_")[1])
    lesson = next((l for l in LESSONS if l["id"] == lesson_id), None)
    if not lesson: return await callback.answer("Урок не найден")
    
    l = get_learning(user_id)
    done = lesson_id in l["completed"]
    
    kb = []
    if not done:
        kb.append([InlineKeyboardButton(text="✅ ЗАВЕРШИТЬ УРОК", callback_data=f"complete_lesson_{lesson_id}")])
    kb.append([InlineKeyboardButton(text="🔙 К УРОКАМ", callback_data="action_learn")])
    
    txt = lesson["text"]
    if done: txt += "\n\n✅ <b>УРОК ПРОЙДЕН!</b>"
    else: txt += f"\n\n💰 <b>Награда за прохождение: +{lesson['reward']}₽</b>"
    
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("complete_lesson_"))
async def complete_lesson_btn(callback: CallbackQuery):
    user_id = callback.from_user.id
    lesson_id = int(callback.data.split("_")[2])
    result = complete_lesson(user_id, lesson_id)
    if result:
        lesson = next((l for l in LESSONS if l["id"] == lesson_id), None)
        await callback.answer(f"Урок пройден! +{lesson['reward']}₽")
        await show_learning_menu(callback.message, user_id)
    else:
        await callback.answer("Урок уже был пройден")

# ==================== ОБРАБОТКА ЧАТА ====================
@dp.callback_query(F.data.startswith("nr_"))
async def neuro_reply(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id = int(parts[1]); buyer_id = int(parts[2])
    chat_key = f"{user_id}_{buyer_id}"
    if chat_key not in active_chats or active_chats[chat_key]["finished"]:
        await callback.answer("Диалог завершён"); return
    chat = active_chats[chat_key]
    await state.set_state(GameState.playing)
    await send_msg(user_id, f"💬 <b>ДИАЛОГ С ПОКУПАТЕЛЕМ #{buyer_id}</b>\n📦 {chat['item']}\n💰 Твоя цена: {chat['price']}₽ | Предложение: {chat['offer']}₽\n\n<i>Напиши ответ. Торгуйся, убеждай!</i>")
    await callback.answer()

@dp.message(StateFilter(GameState.playing))
async def handle_chat(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    pending_messages[user_id].append(message.message_id)
    
    active = None; key = None
    for k, c in active_chats.items():
        if c["user_id"] == user_id and not c["finished"]: active = c; key = k; break
    if not active: return
    
    active["history"].append({"role": "user", "content": text})
    active["round"] += 1
    
    if active["round"] > active["max_rounds"]:
        active["finished"] = True
        msgs = {"angry": "Всё, надоело. Я пошёл.", "kind": "Ладно, подумаю. Спасибо!", "sly": "Хорошо, удачи."}
        if key in remind_timers: remind_timers[key].cancel()
        await send_msg(user_id, f"👤 <b>Покупатель #{active['buyer_id']}:</b> {msgs.get(active['client_type'], 'Пока.')}\n\n⚠️ Диалог завершён.")
        return
    
    try:
        resp = client_openai.chat.completions.create(model="deepseek-chat", messages=active["history"], temperature=0.9, max_tokens=200)
        ai_msg = resp.choices[0].message.content
    except:
        ai_msg = f"Моё предложение {active['offer']}₽. Берёшь?"
    
    active["history"].append({"role": "assistant", "content": ai_msg})
    
    finished = False; result = None
    ml = ai_msg.lower()
    for w in ["беру", "договорились", "по рукам", "забираю", "согласен"]:
        if w in ml: finished = True; result = "sold"; break
    if not finished:
        for w in ["нет", "не буду", "ушёл", "пошёл", "пока"]:
            if w in ml: finished = True; result = "lost"; break
    
    if finished:
        active["finished"] = True
        if key in remind_timers: remind_timers[key].cancel()
        if result == "sold":
            await complete_sale(user_id, active["buyer_id"], message)
        else:
            await send_msg(user_id, f"👤 <b>Покупатель #{active['buyer_id']}:</b> {ai_msg}\n\n👋 Клиент ушёл.")
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 ПРОДОЛЖИТЬ", callback_data=f"nr_{user_id}_{active['buyer_id']}")],
            [InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"nd_{user_id}_{active['buyer_id']}")],
        ])
        await send_msg(user_id, f"👤 <b>Покупатель #{active['buyer_id']}:</b> {ai_msg}\n\n<i>Раунд {active['round']}/{active['max_rounds']} | Предложение: {active['offer']}₽</i>", reply_markup=kb)

@dp.callback_query(F.data.startswith("nd_"))
async def neuro_decline(callback: CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[1]); buyer_id = int(parts[2])
    chat_key = f"{user_id}_{buyer_id}"
    if chat_key in active_chats:
        active_chats[chat_key]["finished"] = True
        if chat_key in remind_timers: remind_timers[chat_key].cancel()
    await send_msg(user_id, "❌ Вы отказались. Клиент ушёл.")
    await callback.answer()

# ==================== CALLBACK-ОБРАБОТЧИКИ ====================
@dp.callback_query(F.data == "start_new_game")
async def start_new_game_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    r = get_rep(user_id)
    players[user_id] = {
        "balance": 5000, "reputation": max(0, r["score"]), "inventory": [],
        "day": 1, "total_earned": 0, "total_spent": 0,
        "items_sold": r["total_sales"], "scam_times": r["scam_survived"],
        "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None,
        "stat_earned_today": 0, "stat_sold_today": 0,
        "rep_mult": rep_mult(r["score"]),
    }
    p = players[user_id]
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    await state.set_state(GameState.playing)
    et = f"\n\n📰 {event['text']}" if event else ""
    vip_txt = "\n👑 VIP!" if is_vip(user_id) else ""
    demand = fmt_demand(p)
    await edit_msg(callback.message, f"🚀 <b>ИГРА НАЧАЛАСЬ!</b>\n\n🌟 День 1 | 💰 5 000₽{vip_txt}{et}\n\n📊 <b>СПРОС:</b>\n{demand}\n\n👇 1. Закупись → 2. Инвентарь → 3. Опубликуй!", reply_markup=main_kb())
    await callback.answer("🚀")

@dp.callback_query(F.data == "continue_game")
async def continue_game_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    p = players.get(user_id)
    if not p: return await callback.answer("Нет игры!")
    await state.set_state(GameState.playing)
    et = f"\n\n{p['current_event']['text']}" if p.get("current_event") else ""
    vip_txt = "\n👑 VIP" if is_vip(user_id) else ""
    demand = fmt_demand(p)
    await edit_msg(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽{vip_txt}{et}\n\n📊 <b>СПРОС:</b>\n{demand}\n\nВыбери:", reply_markup=main_kb())
    await callback.answer("🎮")

@dp.callback_query(F.data == "restart_game_confirm")
async def restart_confirm(callback: CallbackQuery):
    await edit_msg(callback.message, "⚠️ <b>СБРОСИТЬ?</b>\n\nБаланс и инвентарь потеряются. Репутация сохранится.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚠️ ДА", callback_data="restart_game_yes")], [InlineKeyboardButton(text="❌ НЕТ", callback_data="continue_game")]]))

@dp.callback_query(F.data == "restart_game_yes")
async def restart_yes(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id in players: del players[callback.from_user.id]
    await start_new_game_btn(callback, state)

@dp.callback_query(F.data == "action_learn")
async def learn_btn(callback: CallbackQuery):
    await show_learning_menu(callback.message, callback.from_user.id)

@dp.callback_query(F.data == "ref_info")
async def ref_info(callback: CallbackQuery):
    await ref_cmd(callback.message)

@dp.callback_query(F.data == "back_to_start")
async def back_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = players.get(user_id)
    if p and p.get("day", 0) > 0:
        r = get_rep(user_id)
        lvl = rep_level(r["score"])
        await edit_msg(callback.message, f"👋 <b>МЕНЮ</b>\n\n📅 День {p['day']} | 💰 {p['balance']}₽\n⭐ {lvl}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎮 ПРОДОЛЖИТЬ", callback_data="continue_game")], [InlineKeyboardButton(text="📚 ОБУЧЕНИЕ", callback_data="action_learn")]]))
    else:
        await edit_msg(callback.message, "🎮 <b>RESELL TYCOON</b>\n\nГотов начать?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 НАЧАТЬ", callback_data="start_new_game")], [InlineKeyboardButton(text="📚 ОБУЧЕНИЕ", callback_data="action_learn")]]))

@dp.callback_query(F.data == "action_buy", StateFilter(GameState.playing))
async def show_suppliers(callback: CallbackQuery):
    user_id = callback.from_user.id
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    kb = []
    for s in supps:
        kb.append([InlineKeyboardButton(text=f"{s['emoji']} {s['name']} | ⭐{s['rating']}/10 | Кид:{s['scam_chance']}%", callback_data=f"sup_{supps.index(s)}")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="action_back")])
    vip_txt = "\n👑 VIP-поставщик доступен!" if is_vip(user_id) else ""
    await edit_msg(callback.message, f"🏭 <b>ПОСТАВЩИКИ:</b>{vip_txt}\n\n⭐ Рейтинг ↑ = надёжнее\n⚠️ Шанс кидка — могут взять деньги и пропасть!\n\n{random.choice(TIPS['buy'])}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("sup_"), StateFilter(GameState.playing))
async def show_items(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    sup = supps[idx]
    items = random.sample(BASE_ITEMS, min(4, len(BASE_ITEMS)))
    p = get_player(user_id)
    kb = []
    for i, it in enumerate(items):
        pr = int(item_price(it["base_price"], sup) * p["rep_mult"]["supplier_discount"])
        mp = market_price(it["base_price"], p["market_demand"].get(it["cat"], 1.0))
        kb.append([InlineKeyboardButton(text=f"{it['cat']} {it['name']} — {pr}₽ (рынок ~{mp}₽)", callback_data=f"bi_{i}")])
    kb.append([InlineKeyboardButton(text="🔄 ОБНОВИТЬ", callback_data=f"sup_{idx}")])
    kb.append([InlineKeyboardButton(text="🔙 К ПОСТАВЩИКАМ", callback_data="action_buy")])
    await state.update_data(sup_idx=idx, sup_items=items)
    await edit_msg(callback.message, f"{sup['emoji']} <b>{sup['name']}</b>\n{sup['desc']}\n⭐ {sup['rating']}/10 | ⚠️ Кид:{sup['scam_chance']}%\n\nВыбери товар:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("bi_"), StateFilter(GameState.playing))
async def buy_item(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item_idx = int(callback.data.split("_")[1])
    sup_idx = data.get("sup_idx", 0)
    items = data.get("sup_items", [])
    user_id = callback.from_user.id
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    sup = supps[sup_idx]
    if item_idx >= len(items): return await callback.answer("Ошибка")
    item = items[item_idx]
    p = get_player(user_id)
    price = int(item_price(item["base_price"], sup) * p["rep_mult"]["supplier_discount"])
    if p["balance"] < price: return await callback.answer("❌ Мало денег!")
    eff_scam = int(sup["scam_chance"] * p["rep_mult"]["scam_reduce"])
    if random.randint(1, 100) <= eff_scam:
        p["balance"] -= price; p["total_spent"] += price; p["scam_times"] += 1
        p["reputation"] = max(0, p["reputation"] - 5)
        add_rep(user_id, -5, f"Кинул {sup['name']}")
        await edit_msg(callback.message, f"💀 <b>КИНУЛИ!</b>\n{sup['name']} пропал.\n-{price}₽ | 💼 {p['balance']}₽\n\n💡 <b>Урок:</b> Всегда проверяй поставщика! Начни с малого заказа.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))
        return
    p["balance"] -= price; p["total_spent"] += price
    demand = p["market_demand"].get(item["cat"], 1.0)
    mp = market_price(item["base_price"], demand)
    # ДОБАВЛЯЕМ ТОВАР В ИНВЕНТАРЬ
    p["inventory"].append({
        "name": f"{item['cat']} {item['name']}",
        "cat": item["cat"],
        "buy_price": price,
        "market_price": mp,
        "base_price": item["base_price"]
    })
    if sup["rating"] >= 8: add_rep(user_id, 1, "Надёжный поставщик")
    check_ach(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    await edit_msg(callback.message,
        f"✅ <b>ТОВАР КУПЛЕН!</b>\n\n"
        f"📦 {item['cat']} {item['name']}\n"
        f"💰 Закуп: {price}₽ | 📊 Рынок: ~{mp}₽\n"
        f"💼 Баланс: {p['balance']}₽\n"
        f"📦 В инвентаре: {len(p['inventory'])} товаров\n\n"
        f"{item.get('lesson', '')}\n\n"
        f"👇 <b>ДАЛЬШЕ:</b>\n"
        f"👉 Зайди в 📦 <b>ИНВЕНТАРЬ</b>\n"
        f"👉 Нажми на товар → <b>Опубликовать</b>\n"
        f"👉 Жди покупателей!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 ПЕРЕЙТИ В ИНВЕНТАРЬ", callback_data="action_inventory")],
            [InlineKeyboardButton(text="🔄 Купить ещё", callback_data=f"sup_{sup_idx}")],
            [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")],
        ]))

@dp.callback_query(F.data == "action_inventory", StateFilter(GameState.playing))
async def show_inventory(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    if not p["inventory"]:
        return await edit_msg(callback.message,
            "📦 <b>ИНВЕНТАРЬ ПУСТ</b>\n\nТут будут твои товары.\nСначала закупись! 👇",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏭 ЗАКУПИТЬСЯ", callback_data="action_buy")],
                [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")],
            ]))
    kb = []
    for i, it in enumerate(p["inventory"]):
        pub = user_id in published_items and published_items[user_id] and published_items[user_id]["item"]["name"] == it["name"]
        status = "📢 ОПУБЛИКОВАН" if pub else "📱 ОПУБЛИКОВАТЬ"
        kb.append([InlineKeyboardButton(text=f"{it['name']} | Закуп:{it['buy_price']}₽ | ~{it['market_price']}₽ | {status}", callback_data=f"inv_{i}")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    txt = "📦 <b>ИНВЕНТАРЬ:</b>\n\n" + "\n".join(f"{i+1}. {it['name']}\n   Закуп: {it['buy_price']}₽ | Рынок: ~{it['market_price']}₽" for i, it in enumerate(p["inventory"]))
    txt += "\n\n👇 <b>Нажми на товар чтобы опубликовать на Авито!</b>"
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("inv_"), StateFilter(GameState.playing))
async def publish_item(callback: CallbackQuery):
    user_id = callback.from_user.id
    item_idx = int(callback.data.split("_")[1])
    p = get_player(user_id)
    if item_idx >= len(p["inventory"]): return await callback.answer("Товар не найден")
    item = p["inventory"][item_idx]
    if user_id in published_items and published_items[user_id] and published_items[user_id]["item"]["name"] == item["name"]:
        return await callback.answer("Уже опубликован!")
    published_items[user_id] = {"item": item.copy(), "buyers_list": []}
    await edit_msg(callback.message,
        f"📢 <b>ОПУБЛИКОВАНО НА АВИТО!</b>\n\n"
        f"📦 {item['name']}\n💰 Цена: {item['market_price']}₽\n\n"
        f"⏳ <b>Жди 1-3 минуты</b> — придут покупатели!\n"
        f"💬 Они напишут в этот чат.\n\n"
        f"{random.choice(TIPS['publish'])}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 В ИНВЕНТАРЬ", callback_data="action_inventory")],
            [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")],
        ]))
    asyncio.create_task(spawn_buyers(user_id))
    await callback.answer("Опубликовано!")

@dp.callback_query(F.data == "action_stats", StateFilter(GameState.playing))
async def show_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    ref_n = len(referral_data[str(user_id)]["invited"])
    vip = "👑 ДА" if is_vip(user_id) else "❌ Нет"
    l = get_learning(user_id)
    await edit_msg(callback.message,
        f"📊 <b>СТАТИСТИКА:</b>\n\n💰 Баланс: {p['balance']}₽\n📦 Товаров: {len(p['inventory'])}\n📅 День: {p['day']}\n📋 Продано: {p['items_sold']}\n💸 Прибыль: {p['total_earned']}₽\n🛒 Потрачено: {p['total_spent']}₽\n👥 Рефералы: {ref_n}\n📚 Уроки: {len(l['completed'])}/{len(LESSONS)}\n👑 VIP: {vip}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))

@dp.callback_query(F.data == "action_rep_menu")
async def rep_menu(callback: CallbackQuery):
    await rep_cmd(callback.message)

@dp.callback_query(F.data == "action_ref_menu")
async def ref_menu(callback: CallbackQuery):
    await ref_cmd(callback.message)

@dp.callback_query(F.data == "action_demand", StateFilter(GameState.playing))
async def show_demand(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    lines = []; tips = []
    for cat, mult in p["market_demand"].items():
        if mult >= 1.5: emoji = "🔥"; s = "Ажиотаж!"; tips.append(f"💡 {cat}: продавай дороже!")
        elif mult >= 1.2: emoji = "📈"; s = "Растёт"
        elif mult >= 0.8: emoji = "➡️"; s = "Стабильно"
        elif mult >= 0.5: emoji = "📉"; s = "Падает"; tips.append(f"⚠️ {cat}: покупай дёшево")
        else: emoji = "💀"; s = "Мёртвый"; tips.append(f"🚫 {cat}: не покупай")
        lines.append(f"{emoji} <b>{cat}</b>: x{mult:.1f} ({s})")
    et = f"\n\n📰 <b>Событие:</b>\n{p['current_event']['text']}" if p.get("current_event") else ""
    tt = "\n\n".join(tips) if tips else ""
    await edit_msg(callback.message, f"📊 <b>РЫНОК — День {p['day']}</b>\n\n"+"\n".join(lines)+et+(f"\n\n💡 <b>Советы:</b>\n{tt}" if tt else ""), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))

@dp.callback_query(F.data == "action_nextday", StateFilter(GameState.playing))
async def next_day(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    summary = f"🌙 <b>ИТОГИ ДНЯ {p['day']}</b>\n💰 Заработано: {p['stat_earned_today']}₽\n📋 Продано: {p['stat_sold_today']} шт.\n💼 Баланс: {p['balance']}₽"
    p["day"] += 1; p["stat_earned_today"] = 0; p["stat_sold_today"] = 0
    for c in CATEGORIES: p["market_demand"][c] = max(0.3, min(3.0, p["market_demand"][c] * random.uniform(0.85, 1.15)))
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    et = f"\n\n📰 {event['text']}" if event else ""
    if p["inventory"] and random.random() < 0.2:
        for it in p["inventory"]: it["market_price"] = int(it["market_price"] * random.uniform(0.7, 0.95))
        et += "\n⚠️ Залежавшиеся товары подешевели."
    if user_id in published_items: published_items[user_id] = None
    check_ach(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    demand = fmt_demand(p)
    await edit_msg(callback.message, f"{summary}\n\n☀️ <b>ДЕНЬ {p['day']}</b>{et}\n\n📊 <b>СПРОС:</b>\n{demand}\n\nВыбери:", reply_markup=main_kb())

@dp.callback_query(F.data == "action_end", StateFilter(GameState.playing))
async def end_game(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    p = get_player(user_id)
    await state.clear()
    if p["balance"] >= 50000: r = "🏆 <b>ПОБЕДА!</b> Ты заработал 50 000₽!"
    elif p["balance"] <= 0: r = "💀 <b>БАНКРОТ!</b>"
    else: r = "🎮 Игра окончена."
    check_ach(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    await edit_msg(callback.message, f"{r}\n\n💰 {p['balance']}₽ | 📋 Продаж: {p['items_sold']}\n\n👉 {CHANNEL_LINK} — реальные продажи!\n/play — ещё раз", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 ЕЩЁ РАЗ", callback_data="restart_game")]]))

@dp.callback_query(F.data == "restart_game")
async def restart_game(callback: CallbackQuery):
    if callback.from_user.id in players: del players[callback.from_user.id]
    await callback.message.edit_text("🔄 Напиши /play")

@dp.callback_query(F.data == "action_back", StateFilter(GameState.playing))
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    et = f"\n\n{p['current_event']['text']}" if p.get("current_event") else ""
    vip_txt = "\n👑 VIP" if is_vip(user_id) else ""
    demand = fmt_demand(p)
    await edit_msg(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽{vip_txt}{et}\n\n📊 <b>СПРОС:</b>\n{demand}\n\nВыбери:", reply_markup=main_kb())

# ==================== ЗАПУСК ====================
async def main():
    print("🎮 ReSell Tycoon + Обучение запущены!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())