import random
import hashlib
import json
import os
import asyncio
from collections import defaultdict
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram import F
from openai import OpenAI

# ==================== КОНФИГ ====================
API_TOKEN = '8747685010:AAH8bN3x0fihSvUzVitijYQLHXeHFhIV5w4'  # ← ЗАМЕНИ
CHANNEL_LINK = '@vintagedrop61'
CHANNEL_NAME = 'ReSell👾'
BOT_USERNAME = 'R-Game'  # ← ЗАМЕНИ БЕЗ @
DEEPSEEK_API_KEY = "sk-9515baacbf9b44bfbf45caadf97e5012"  # ← ЗАМЕНИ

client_openai = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# ==================== ФАЙЛЫ ====================
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

MARKET_EVENTS = [
    {"text": "📰 Хайп на винтажные джинсы!", "cat": "👖 Джинсы", "mult": 1.5},
    {"text": "📰 Дожди — спрос на куртки вырос!", "cat": "🧥 Куртки", "mult": 1.4},
    {"text": "📰 Все хотят кроссовки!", "cat": "👟 Кроссы", "mult": 1.5},
    {"text": "📰 Лето близко — джинсы падают.", "cat": "👖 Джинсы", "mult": 0.6},
    {"text": "📰 Авито комиссия 15% — все осторожны.", "cat": None, "mult": 0.8},
    {"text": "📰 Ретро-аксессуары в тренде!", "cat": "🎒 Аксессуары", "mult": 1.6},
    {"text": "📰 Холода — куртки в цене.", "cat": "🧥 Куртки", "mult": 1.3},
    {"text": "📰 Скоро школа — худи дорожают.", "cat": "👕 Худи", "mult": 1.35},
    {"text": "📰 Кроссовки — рынок переполнен.", "cat": "👟 Кроссы", "mult": 0.65},
    {"text": "📰 Блогер в Stüssy — аксессуары летят!", "cat": "🎒 Аксессуары", "mult": 1.5},
    {"text": "📰 Блокировки Авито — конкуренция ниже.", "cat": None, "mult": 1.2},
    {"text": "📰 Эконом-режим — ищут дешёвое.", "cat": None, "mult": 0.7},
]

# ==================== НЕЙРОКЛИЕНТЫ ====================
CLIENT_TYPES = {
    "angry": {
        "name": "злой", "mood_emoji": "😡",
        "system_prompt": "Ты — злой покупатель с Авито. Грубишь, торгуешься жёстко (скидка 30-50%), можешь написать 'дорого, я такое на помойке нашёл'. Если продавец уступает — берёшь но ворчишь. Коротко, 1-2 предложения.",
        "discount_range": (0.5, 0.7), "patience": 3
    },
    "kind": {
        "name": "добрый", "mood_emoji": "😊",
        "system_prompt": "Ты — добрый покупатель. Вежлив, просишь скидку 10-20%, хвалишь товар. Если не договорились — извиняешься и уходишь. Коротко, 1-2 предложения.",
        "discount_range": (0.8, 0.9), "patience": 5
    },
    "sly": {
        "name": "хитрый", "mood_emoji": "😏",
        "system_prompt": "Ты — хитрый перекупщик. Аргументируешь цену рынком, блефуешь ('на другом аккаунте дешевле'), сбиваешь 20-40%. Можешь написать 'за 2000 прямо сейчас забираю, иначе ухожу'. Коротко, как в чате.",
        "discount_range": (0.6, 0.8), "patience": 4
    }
}

# ==================== РЕПУТАЦИЯ ====================
REPUTATION_LEVELS = {
    -100: {"name": "💀 Чёрный список"},
    -50: {"name": "🔴 Ужасная"},
    -10: {"name": "🟠 Плохая"},
    0: {"name": "🟡 Нейтральная"},
    25: {"name": "🟢 Хорошая"},
    50: {"name": "🔵 Отличная"},
    75: {"name": "🟣 Легендарная"},
    90: {"name": "🟡 Золотая"},
    100: {"name": "👑 Бог товарки"},
}

ACHIEVEMENTS = [
    {"id": "first_sale", "name": "🎯 Первая продажа", "target": 1, "reward": 5},
    {"id": "seller_10", "name": "📦 Продавец", "target": 10, "reward": 10},
    {"id": "profit_5000", "name": "💰 Навар", "target": 5000, "reward": 5},
    {"id": "angry_win", "name": "😡 Укротитель", "target": 1, "reward": 10},
    {"id": "haggle_master", "name": "🎯 Мастер торга", "target": 1, "reward": 10},
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
active_chats = {}
# published_items: {user_id: {"item": {...}, "buyers_coming": bool, "buyers_list": [...], "timer_task": asyncio.Task}}
published_items = {}

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

# ==================== РЕФЕРАЛЫ ====================
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

# ==================== РЕПУТАЦИЯ ====================
def get_user_rep(user_id):
    uid = str(user_id)
    if uid not in rep_data:
        rep_data[uid] = {
            "score": 0, "total_sales": 0, "total_profit": 0,
            "max_balance": 0, "scam_survived": 0,
            "angry_deals": 0, "haggle_wins": 0, "achievements": [], "rep_history": []
        }
        save_json(REPUTATION_FILE, rep_data)
    return rep_data[uid]

def get_rep_level(score):
    for t in sorted(REPUTATION_LEVELS.keys(), reverse=True):
        if score >= t: return REPUTATION_LEVELS[t]
    return REPUTATION_LEVELS[-100]

def add_rep(user_id, amount, reason=""):
    user = get_user_rep(user_id)
    user["score"] = max(-100, min(100, user["score"] + amount))
    user["rep_history"].append({"change": amount, "reason": reason, "total": user["score"]})
    if len(user["rep_history"]) > 20: user["rep_history"] = user["rep_history"][-20:]
    save_json(REPUTATION_FILE, rep_data)
    return user["score"]

def get_rep_multiplier(score):
    if score >= 75: return {"supplier_discount": 0.85, "scam_reduce": 0.2, "haggle_bonus": 0.25}
    elif score >= 50: return {"supplier_discount": 0.90, "scam_reduce": 0.4, "haggle_bonus": 0.15}
    elif score >= 25: return {"supplier_discount": 0.95, "scam_reduce": 0.6, "haggle_bonus": 0.05}
    elif score >= 0: return {"supplier_discount": 1.0, "scam_reduce": 0.8, "haggle_bonus": 0.0}
    elif score >= -10: return {"supplier_discount": 1.1, "scam_reduce": 1.0, "haggle_bonus": -0.05}
    else: return {"supplier_discount": 1.5, "scam_reduce": 1.5, "haggle_bonus": -0.3}

def check_achievements(user_id, player_data=None):
    user = get_user_rep(user_id)
    if player_data:
        user["total_sales"] = player_data.get("items_sold", 0)
        user["total_profit"] = player_data.get("total_earned", 0)
        user["max_balance"] = max(user["max_balance"], player_data.get("balance", 0))
    new_ach = []
    for ach in ACHIEVEMENTS:
        if ach["id"] in user["achievements"]: continue
        earned = False
        tid = ach["id"]
        if tid == "first_sale" and user["total_sales"] >= 1: earned = True
        elif tid == "seller_10" and user["total_sales"] >= 10: earned = True
        elif tid == "profit_5000" and user["total_profit"] >= 5000: earned = True
        elif tid == "angry_win" and user["angry_deals"] >= 1: earned = True
        elif tid == "haggle_master" and user["haggle_wins"] >= 1: earned = True
        if earned:
            user["achievements"].append(ach["id"])
            add_rep(user_id, ach["reward"], f"Достижение: {ach['name']}")
            new_ach.append(ach)
    save_json(REPUTATION_FILE, rep_data)
    return new_ach

# ==================== ИГРА ====================
def get_player(user_id):
    if user_id not in players:
        rep = get_user_rep(user_id)
        rep_mult = get_rep_multiplier(rep["score"])
        players[user_id] = {
            "balance": 5000, "reputation": max(0, rep["score"]),
            "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0,
            "items_sold": rep["total_sales"], "scam_times": rep["scam_survived"],
            "market_demand": {cat: 1.0 for cat in CATEGORIES},
            "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0,
            "rep_mult": rep_mult,
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

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏭 ЗАКУПИТЬСЯ", callback_data="action_buy")],
        [InlineKeyboardButton(text="📦 ИНВЕНТАРЬ", callback_data="action_inventory")],
        [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="action_stats"),
         InlineKeyboardButton(text="🏆 РЕПУТАЦИЯ", callback_data="action_rep")],
        [InlineKeyboardButton(text="🔗 РЕФЕРАЛЫ", callback_data="action_ref")],
        [InlineKeyboardButton(text="⏩ СЛЕД. ДЕНЬ", callback_data="action_nextday"),
         InlineKeyboardButton(text="🏁 ЗАВЕРШИТЬ", callback_data="action_end")],
    ])

# ==================== НЕЙРОКЛИЕНТЫ: СИСТЕМА ПУБЛИКАЦИИ ====================
def generate_neuro_first_msg(client_type, item_name, price, offer):
    msgs = {
        "angry": [
            f"😡 Привет! Увидел твоё объявление — {item_name} за {price}₽. Это чё за цена вообще? Давай {offer}₽ и забираю. Нет — дальше листаю.",
            f"😡 Слушай, {item_name} норм, но {price}₽ — грабёж. У меня {offer}₽. Берёшь?",
        ],
        "kind": [
            f"😊 Здравствуйте! Заинтересовался вашим объявлением: {item_name}. Очень нравится, но {price}₽ дороговато. Может, отдадите за {offer}₽? Пожалуйста!",
            f"😊 Добрый день! Давно ищу {item_name}. У меня бюджет {offer}₽. Возможно договоримся?",
        ],
        "sly": [
            f"😏 Бро, видел твой лот — {item_name}. Рынок щас просел, такие за {offer}₽ уходят. Отдашь за {offer}₽?",
            f"😏 Смотри, у меня кэш {offer}₽ прямо сейчас. За {item_name} отдашь? На соседнем акке дешевле висит.",
        ]
    }
    return random.choice(msgs.get(client_type, msgs["kind"]))

async def send_buyer_message(user_id, buyer_id, client_type, item_name, price):
    """Отправляет первое сообщение от нейроклиента."""
    client = CLIENT_TYPES[client_type]
    rep_mult = get_rep_multiplier(get_user_rep(user_id)["score"])
    discount = random.uniform(*client["discount_range"]) + rep_mult["haggle_bonus"]
    discount = max(0.3, min(0.95, discount))
    offer = int(price * discount)
    offer = (offer // 100) * 100 + 99
    if offer < 100: offer = price // 2
    
    first_msg = generate_neuro_first_msg(client_type, item_name, price, offer)
    
    active_chats[f"{user_id}_{buyer_id}"] = {
        "user_id": user_id,
        "buyer_id": buyer_id,
        "client_type": client_type,
        "item": item_name,
        "price": price,
        "offer": offer,
        "history": [
            {"role": "system", "content": client["system_prompt"]},
            {"role": "assistant", "content": first_msg}
        ],
        "round": 1,
        "max_rounds": client["patience"],
        "finished": False
    }
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласиться", callback_data=f"neuro_accept_{user_id}_{buyer_id}"),
         InlineKeyboardButton(text="❌ Отказаться", callback_data=f"neuro_decline_{user_id}_{buyer_id}")],
    ])
    
    await bot.send_message(
        user_id,
        f"📩 <b>НОВОЕ СООБЩЕНИЕ ОТ ПОКУПАТЕЛЯ!</b>\n\n"
        f"{client['mood_emoji']} <b>Покупатель #{buyer_id}</b> ({client['name'].upper()})\n"
        f"📦 По поводу: {item_name}\n\n"
        f"{first_msg}\n\n"
        f"<i>Ответь на это сообщение, чтобы продолжить диалог.</i>",
        parse_mode="HTML",
        reply_markup=kb
    )

async def spawn_buyers(user_id):
    """Создаёт нейроклиентов для опубликованного товара."""
    await asyncio.sleep(random.randint(60, 180))  # Ждём от 1 до 3 минут
    
    if user_id not in published_items or not published_items[user_id]:
        return
    
    pub = published_items[user_id]
    item = pub["item"]
    
    # Определяем количество покупателей (1-3)
    rep_mult = get_rep_multiplier(get_user_rep(user_id)["score"])
    base_buyers = random.randint(1, 3)
    if rep_mult["haggle_bonus"] > 0.1:
        base_buyers = min(3, base_buyers + 1)  # Хорошая репутация = больше покупателей
    
    buyer_types = random.choices(list(CLIENT_TYPES.keys()), k=base_buyers)
    
    await bot.send_message(
        user_id,
        f"📱 <b>ОБЪЯВЛЕНИЕ НАЧАЛО РАБОТАТЬ!</b>\n\n"
        f"📦 {item['name']} за {item['market_price']}₽\n"
        f"👥 Пишут <b>{base_buyers}</b> чел.\n\n"
        f"<i>Отвечай им в чат — торгуйся, договаривайся!</i>",
        parse_mode="HTML"
    )
    
    pub["buyers_list"] = []
    
    for i, btype in enumerate(buyer_types):
        await asyncio.sleep(random.randint(5, 20))  # Небольшая задержка между покупателями
        buyer_id = i + 1
        pub["buyers_list"].append({"id": buyer_id, "type": btype, "active": True})
        await send_buyer_message(user_id, buyer_id, btype, item["name"], item["market_price"])

# ==================== КОМАНДЫ ====================
@dp.message(Command('start'))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_code = args[1][4:]
        referrer_id = None
        for uid in referral_data:
            if generate_ref_code(uid) == ref_code: referrer_id = uid; break
        if referrer_id and referrer_id != str(user_id) and user_id not in referral_data[referrer_id]["invited"]:
            referral_data[referrer_id]["invited"].append(user_id)
            save_json(REFERRAL_FILE, dict(referral_data))
            if int(referrer_id) in players: players[int(referrer_id)]["balance"] += 500
            try: await bot.send_message(int(referrer_id), f"🎉 Новый реферал! +500₽\n👥 Всего: {len(referral_data[referrer_id]['invited'])}", parse_mode="HTML")
            except: pass
            await message.answer("👋 Привет! Ты по реферальной ссылке.\n/play — играть | /ref — ссылка", parse_mode="HTML")
            return
    await message.answer(f"🎮 <b>ReSell Tycoon</b>\n💰 5 000₽ → 🎯 50 000₽\n\n/play | /ref | /rep", parse_mode="HTML")

@dp.message(Command('play'))
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
    await state.set_state(GameState.playing)
    et = f"\n\n{event['text']}" if event else ""
    vip_txt = "\n👑 VIP!" if is_vip(user_id) else ""
    await message.answer(f"🌟 <b>ДЕНЬ 1</b>\nБаланс: 5000₽{vip_txt}{et}\n\nВыбери:", parse_mode="HTML", reply_markup=get_main_keyboard())

@dp.message(Command('ref'))
async def ref_cmd(message: types.Message):
    user_id = message.from_user.id
    link = get_ref_link(user_id)
    count = len(referral_data[str(user_id)]["invited"])
    vip_user = is_vip(user_id)
    vip_txt = "\n👑 Ты в ТОП-3! VIP открыт!" if vip_user else ""
    await message.answer(f"🔗 <b>ТВОЯ ССЫЛКА:</b>\n<code>{link}</code>\n\n👥 Приглашено: {count}\n💰 Бонус: {count*500}₽{vip_txt}", parse_mode="HTML")

@dp.message(Command('rep'))
async def rep_cmd(message: types.Message):
    user_id = message.from_user.id
    p = players.get(user_id)
    pd = {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]} if p else None
    new_ach = check_achievements(user_id, pd)
    user = get_user_rep(user_id)
    level = get_rep_level(user["score"])
    card = f"🏆 <b>РЕПУТАЦИЯ: {level['name']}</b>\n📊 Очки: {user['score']}/100\n📦 Продаж: {user['total_sales']}\n💰 Прибыль: {user['total_profit']}₽\n🏅 Достижений: {len(user['achievements'])}/{len(ACHIEVEMENTS)}"
    if new_ach:
        card += "\n\n🎉 <b>НОВЫЕ!</b>\n" + "\n".join(f"{a['name']}" for a in new_ach)
    await message.answer(card, parse_mode="HTML")

# ==================== ОБРАБОТКА НЕЙРО-ДИАЛОГОВ ====================
@dp.message(StateFilter(GameState.playing))
async def handle_neuro_chat(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    
    # Ищем активный диалог с нейроклиентом
    active_dialog = None
    dialog_key = None
    for key, chat in active_chats.items():
        if chat["user_id"] == user_id and not chat["finished"]:
            active_dialog = chat
            dialog_key = key
            break
    
    if not active_dialog:
        return  # Нет активного диалога — игнорируем
    
    chat = active_dialog
    client = CLIENT_TYPES[chat["client_type"]]
    chat["history"].append({"role": "user", "content": text})
    chat["round"] += 1
    
    # Проверка на конец диалога
    if chat["round"] > chat["max_rounds"]:
        chat["finished"] = True
        msgs = {"angry": "Всё, надоело! Я пошёл.", "kind": "Ладно, подумаю ещё. Спасибо!", "sly": "Хорошо, удачи. Поищу другого."}
        end_msg = msgs.get(chat["client_type"], "Пока.")
        await message.answer(f"{client['mood_emoji']} <b>Покупатель:</b> {end_msg}\n\n⚠️ Диалог завершён.", parse_mode="HTML")
        return
    
    # Запрос к DeepSeek
    try:
        resp = client_openai.chat.completions.create(
            model="deepseek-chat",
            messages=chat["history"],
            temperature=0.9,
            max_tokens=150
        )
        ai_msg = resp.choices[0].message.content
    except:
        fallbacks = {
            "angry": [f"Короче, {chat['offer']}₽. Берёшь или нет?!", "Не тяни, соглашайся!"],
            "kind": [f"Ну пожалуйста, может уступите? У меня только {chat['offer']}₽.", "Буду очень благодарен!"],
            "sly": [f"Рынок падает. {chat['offer']}₽ — хорошая цена.", f"Я знаю что делаю. {chat['offer']}₽ и разбежимся."]
        }
        ai_msg = random.choice(fallbacks.get(chat["client_type"], [f"Моё предложение {chat['offer']}₽. Идёт?"]))
    
    chat["history"].append({"role": "assistant", "content": ai_msg})
    
    # Проверяем завершение
    finished = False; result = None
    ml = ai_msg.lower()
    agree_words = ["беру", "договорились", "по рукам", "забираю", "согласен", "давай", "идёт"]
    for w in agree_words:
        if w in ml and "?" not in ml: finished = True; result = "sold"; break
    if not finished:
        decline_words = ["нет", "не буду", "ушёл", "пошёл", "пока", "до свидания", "удачи"]
        for w in decline_words:
            if w in ml: finished = True; result = "lost"; break
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласиться", callback_data=f"neuro_accept_{user_id}_{chat['buyer_id']}"),
         InlineKeyboardButton(text="❌ Отказаться", callback_data=f"neuro_decline_{user_id}_{chat['buyer_id']}")],
    ])
    
    if finished:
        chat["finished"] = True
        if result == "sold":
            # Продажа!
            await complete_neuro_sale_from_chat(message, chat)
        else:
            await message.answer(f"{client['mood_emoji']} <b>Покупатель:</b> {ai_msg}\n\n👋 Клиент ушёл.", parse_mode="HTML")
    else:
        await message.answer(
            f"{client['mood_emoji']} <b>Покупатель:</b> {ai_msg}\n\n"
            f"<i>Раунд {chat['round']}/{chat['max_rounds']} | Предложение: {chat['offer']}₽</i>\n"
            f"Ответь в чат или используй кнопки:",
            parse_mode="HTML",
            reply_markup=kb
        )

async def complete_neuro_sale_from_chat(message, chat):
    """Завершает продажу нейроклиенту."""
    user_id = chat["user_id"]
    p = get_player(user_id)
    
    # Ищем товар в опубликованных или инвентаре
    item_name = chat["item"]
    final_price = chat["offer"]
    
    # Сначала проверяем опубликованный товар
    if user_id in published_items and published_items[user_id] and published_items[user_id]["item"]["name"] == item_name:
        item = published_items[user_id]["item"]
        # Убираем из инвентаря
        for i, inv_item in enumerate(p["inventory"]):
            if inv_item["name"] == item_name:
                sold = p["inventory"].pop(i)
                break
        else:
            sold = item
        published_items[user_id] = None
    else:
        # Ищем в инвентаре
        for i, inv_item in enumerate(p["inventory"]):
            if inv_item["name"] == item_name:
                sold = p["inventory"].pop(i)
                break
        else:
            await message.answer("❌ Товар не найден.")
            return
    
    profit = final_price - sold["buy_price"]
    p["balance"] += final_price
    p["total_earned"] += profit
    p["items_sold"] += 1
    p["stat_earned_today"] += profit
    p["stat_sold_today"] += 1
    p["reputation"] = min(100, p["reputation"] + 5)
    
    add_rep(user_id, random.randint(2, 5), f"Продажа нейроклиенту: {item_name}")
    if chat["client_type"] == "angry":
        get_user_rep(user_id)["angry_deals"] += 1
    if final_price > sold["market_price"] * 0.9:
        get_user_rep(user_id)["haggle_wins"] += 1
    
    check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    
    await message.answer(
        f"🎉 <b>ПРОДАНО!</b>\n\n"
        f"📦 {item_name}\n"
        f"💰 Цена: {final_price}₽\n"
        f"💵 Прибыль: {profit}₽\n"
        f"💼 Баланс: {p['balance']}₽",
        parse_mode="HTML"
    )

# ==================== CALLBACK-ОБРАБОТЧИКИ ====================
@dp.callback_query(F.data == "action_buy", StateFilter(GameState.playing))
async def show_suppliers(callback: CallbackQuery):
    user_id = callback.from_user.id
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    kb = []
    for s in supps:
        kb.append([InlineKeyboardButton(text=f"{s['emoji']} {s['name']} | ⭐{s['rating']} | Кид:{s['scam_chance']}%", callback_data=f"supplier_{supps.index(s)}")])
    kb.append([InlineKeyboardButton(text="🔙 Меню", callback_data="action_back")])
    vip_txt = "\n👑 VIP доступен!" if is_vip(user_id) else ""
    await callback.message.edit_text(f"🏭 <b>ПОСТАВЩИКИ:</b>{vip_txt}\nРейтинг ↑ = надёжнее, но дороже.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("supplier_"), StateFilter(GameState.playing))
async def show_supplier_items(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    sup = supps[idx]
    items = random.sample(BASE_ITEMS, min(4, len(BASE_ITEMS)))
    kb = []
    for i, it in enumerate(items):
        kb.append([InlineKeyboardButton(text=f"{it['cat']} {it['name']} — {get_item_price(it['base_price'], sup)}₽", callback_data=f"buyitem_{i}")])
    kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"supplier_{idx}")])
    kb.append([InlineKeyboardButton(text="🔙 Поставщики", callback_data="action_buy")])
    kb.append([InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")])
    await state.update_data(current_supplier_idx=idx, supplier_items=items)
    await callback.message.edit_text(f"{sup['emoji']} <b>{sup['name']}</b>\n⭐{sup['rating']}/10 | ⚠️Кид:{sup['scam_chance']}%\nВыбери:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("buyitem_"), StateFilter(GameState.playing))
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
        await callback.message.edit_text(f"💀 <b>КИНУЛИ!</b>\n{sup['name']} пропал.\n-{price}₽ | Баланс: {p['balance']}₽", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")]]))
        return
    p["balance"] -= price; p["total_spent"] += price
    demand = p["market_demand"].get(item["cat"], 1.0)
    market_price = get_market_price(item["base_price"], demand)
    p["inventory"].append({
        "name": f"{item['cat']} {item['name']}", "cat": item["cat"],
        "buy_price": price, "market_price": market_price, "base_price": item["base_price"]
    })
    if sup["rating"] >= 8: add_rep(user_id, 1, "Надёжный поставщик")
    check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    await callback.message.edit_text(f"✅ <b>КУПЛЕНО!</b>\n📦 {item['cat']} {item['name']}\n💰 Закуп: {price}₽\n📊 Рынок: ~{market_price}₽\n💼 Баланс: {p['balance']}₽", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Ещё", callback_data=f"supplier_{sup_idx}")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")]
    ]))

@dp.callback_query(F.data == "action_inventory", StateFilter(GameState.playing))
async def show_inventory(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    if not p["inventory"]:
        return await callback.message.edit_text("📦 Инвентарь пуст.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏭 Закупиться", callback_data="action_buy")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")]
        ]))
    kb = []
    for i, it in enumerate(p["inventory"]):
        status = "📢 Опубликован" if user_id in published_items and published_items[user_id] and published_items[user_id]["item"]["name"] == it["name"] else "📱 Опубликовать"
        kb.append([InlineKeyboardButton(
            text=f"{it['name']} | Закуп:{it['buy_price']}₽ | ~{it['market_price']}₽ | {status}",
            callback_data=f"inventory_{i}"
        )])
    kb.append([InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")])
    txt = "📦 <b>ИНВЕНТАРЬ:</b>\n"
    for i, it in enumerate(p["inventory"]):
        txt += f"{i+1}. {it['name']} | Закуп: {it['buy_price']}₽ | Рынок: ~{it['market_price']}₽\n"
    txt += "\nНажми на товар, чтобы опубликовать его на Авито!"
    await callback.message.edit_text(txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("inventory_"), StateFilter(GameState.playing))
async def publish_item(callback: CallbackQuery):
    user_id = callback.from_user.id
    item_idx = int(callback.data.split("_")[1])
    p = get_player(user_id)
    
    if item_idx >= len(p["inventory"]): return await callback.answer("Товар не найден")
    
    item = p["inventory"][item_idx]
    
    # Проверяем, не опубликован ли уже
    if user_id in published_items and published_items[user_id] and published_items[user_id]["item"]["name"] == item["name"]:
        return await callback.answer("Этот товар уже опубликован!")
    
    # Публикуем
    published_items[user_id] = {
        "item": item.copy(),
        "buyers_coming": False,
        "buyers_list": [],
    }
    
    await callback.message.edit_text(
        f"📢 <b>ТОВАР ОПУБЛИКОВАН!</b>\n\n"
        f"📦 {item['name']}\n"
        f"💰 Цена: {item['market_price']}₽\n\n"
        f"⏳ Ожидайте покупателей в течение 1-3 минут...\n"
        f"💬 Они напишут вам в этот чат!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 В инвентарь", callback_data="action_inventory")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="action_back")],
        ])
    )
    
    # Запускаем таймер на появление покупателей
    asyncio.create_task(spawn_buyers(user_id))
    await callback.answer("Опубликовано! Жди покупателей 📱")

@dp.callback_query(F.data.startswith("neuro_accept_"))
async def neuro_accept_callback(callback: CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[2])
    buyer_id = int(parts[3])
    dialog_key = f"{user_id}_{buyer_id}"
    
    if dialog_key not in active_chats or active_chats[dialog_key]["finished"]:
        return await callback.answer("Диалог уже завершён")
    
    chat = active_chats[dialog_key]
    # Отправляем согласие
    chat["history"].append({"role": "user", "content": f"Согласен на {chat['offer']}₽"})
    chat["finished"] = True
    
    await complete_neuro_sale_from_chat(callback.message, chat)
    await callback.answer("Продано!")

@dp.callback_query(F.data.startswith("neuro_decline_"))
async def neuro_decline_callback(callback: CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[2])
    buyer_id = int(parts[3])
    dialog_key = f"{user_id}_{buyer_id}"
    
    if dialog_key in active_chats:
        active_chats[dialog_key]["finished"] = True
    
    await callback.message.edit_text("❌ Вы отказались. Клиент ушёл.")
    await callback.answer()

@dp.callback_query(F.data == "action_stats", StateFilter(GameState.playing))
async def show_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    ref_n = len(referral_data[str(user_id)]["invited"])
    vip = "👑 ДА" if is_vip(user_id) else "❌ Нет"
    await callback.message.edit_text(
        f"💰 Баланс: {p['balance']}₽\n⭐ Реп: {p['reputation']}/100\n📅 День: {p['day']}\n📦 Товаров: {len(p['inventory'])}\n📋 Продано: {p['items_sold']}\n💸 Прибыль: {p['total_earned']}₽\n👥 Рефералы: {ref_n}\n👑 VIP: {vip}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")]])
    )

@dp.callback_query(F.data == "action_rep")
async def rep_btn(callback: CallbackQuery):
    await rep_cmd(callback.message)

@dp.callback_query(F.data == "action_ref")
async def ref_btn(callback: CallbackQuery):
    await ref_cmd(callback.message)

@dp.callback_query(F.data == "action_nextday", StateFilter(GameState.playing))
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
    # Очищаем опубликованные товары
    if user_id in published_items: published_items[user_id] = None
    check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    await callback.message.edit_text(f"{summary}\n\n☀️ <b>ДЕНЬ {p['day']}</b>{vip_txt}{et}\n\nВыбери:", parse_mode="HTML", reply_markup=get_main_keyboard())

@dp.callback_query(F.data == "action_end", StateFilter(GameState.playing))
async def end_game(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    p = get_player(user_id)
    await state.clear()
    if p["balance"] >= 50000: result = "🏆 <b>ПОБЕДА!</b>"
    elif p["balance"] <= 0: result = "💀 <b>БАНКРОТ!</b>"
    else: result = "🎮 Игра окончена."
    check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    await callback.message.edit_text(f"{result}\n💰 Баланс: {p['balance']}₽\n📦 Продаж: {p['items_sold']}\n\nРеальные продажи → {CHANNEL_LINK}\n/play — ещё раз", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Ещё раз", callback_data="restart_game")]]))

@dp.callback_query(F.data == "restart_game")
async def restart_game(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in players: del players[user_id]
    await callback.message.edit_text("🔄 Напиши /play")

@dp.callback_query(F.data == "action_back", StateFilter(GameState.playing))
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    et = f"\n\n{p['current_event']['text']}" if p.get("current_event") else ""
    vip_txt = "\n👑 VIP" if is_vip(user_id) else ""
    await callback.message.edit_text(f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽{vip_txt}{et}\n\nДействие:", parse_mode="HTML", reply_markup=get_main_keyboard())

# ==================== ЗАПУСК ====================
async def main():
    print("🎮 ReSell Tycoon + Нейроклиенты запущены!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())