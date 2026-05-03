import random
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ==================== КОНФИГ ====================
API_TOKEN = '8747685010:AAH8bN3x0fihSvUzVitijYQLHXeHFhIV5w4'
CHANNEL_LINK = '@vintagedrop61'
CHANNEL_NAME = 'ReSell👾'

# ==================== ДАННЫЕ ====================

# Поставщики (имя, рейтинг 1-10, наценка_множитель, шанс_кидалова_в_%)
SUPPLIERS = [
    {"name": "🏭 MegaStock", "rating": 9, "price_mult": 1.4, "scam_chance": 0, "emoji": "🏭"},
    {"name": "👕 OldGarage", "rating": 7, "price_mult": 1.15, "scam_chance": 10, "emoji": "👕"},
    {"name": "🎒 Vintager", "rating": 5, "price_mult": 0.85, "scam_chance": 25, "emoji": "🎒"},
    {"name": "💸 DumpPrice", "rating": 3, "price_mult": 0.55, "scam_chance": 50, "emoji": "💸"},
    {"name": "🎲 LuckyBag", "rating": 1, "price_mult": 0.3, "scam_chance": 75, "emoji": "🎲"},
]

# Базовые товары (категория, название, базовая_цена)
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
    {"cat": "👕 Худи", "name": "Supreme Box Logo (реплика)", "base_price": 1800},
    {"cat": "🧥 Куртки", "name": "Stone Island Soft Shell", "base_price": 6000},
    {"cat": "👟 Кроссы", "name": "New Balance 990v3", "base_price": 4200},
    {"cat": "🎒 Аксессуары", "name": "Patagonia Hip Pack", "base_price": 2000},
]

# Категории для спроса
CATEGORIES = ["👖 Джинсы", "👕 Худи", "🧥 Куртки", "👟 Кроссы", "🎒 Аксессуары"]

# Имена покупателей
BUYER_NAMES = [
    "Вася", "Петя", "Колян", "Димон", "Антоха", "Серёга", "Макс",
    "Лёха", "Вован", "Гоша", "Мишаня", "Тёмыч", "Даня", "Егор",
    "Никита", "Рустам", "Жека", "Илюха", "Стас", "Артём"
]

# Сообщения покупателей при торге
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

# События рынка
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

# ==================== БОТ ====================
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Состояния игры
class GameState(StatesGroup):
    playing = State()
    choosing_action = State()
    choosing_supplier = State()
    choosing_item = State()
    selling_item = State()
    viewing_inventory = State()

# Хранилище данных игроков (в реальном проекте — БД)
players = {}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_player(user_id):
    if user_id not in players:
        players[user_id] = {
            "balance": 5000,
            "reputation": 0,
            "inventory": [],
            "day": 1,
            "total_earned": 0,
            "total_spent": 0,
            "items_sold": 0,
            "scam_times": 0,
            "market_demand": {cat: 1.0 for cat in CATEGORIES},
            "current_event": None,
            "stat_earned_today": 0,
            "stat_sold_today": 0,
        }
    return players[user_id]

def get_item_price(item_base_price, supplier):
    """Цена товара у поставщика с учётом его множителя."""
    return int(item_base_price * supplier["price_mult"])

def get_market_price(item_base_price, demand_mult):
    """Рыночная цена с учётом спроса."""
    return int(item_base_price * demand_mult * random.uniform(0.9, 1.3))

def generate_daily_event():
    """Генерирует случайное событие дня."""
    if random.random() < 0.6:  # 60% шанс события
        return random.choice(MARKET_EVENTS)
    return None

def apply_market_event(player_data, event):
    """Применяет событие к рыночному спросу."""
    if event["cat"]:
        player_data["market_demand"][event["cat"]] *= event["mult"]
        # Ограничиваем
        player_data["market_demand"][event["cat"]] = max(0.3, min(3.0, player_data["market_demand"][event["cat"]]))
    else:
        for cat in CATEGORIES:
            player_data["market_demand"][cat] *= event["mult"]
            player_data["market_demand"][cat] = max(0.3, min(3.0, player_data["market_demand"][cat]))

def format_inventory(inventory):
    if not inventory:
        return "📦 Инвентарь пуст."
    lines = []
    for i, item in enumerate(inventory, 1):
        lines.append(f"{i}. {item['name']} | Закуп: {item['buy_price']}₽ | Рынок: ~{item['market_price']}₽")
    return "📦 <b>ТВОЙ ИНВЕНТАРЬ:</b>\n" + "\n".join(lines)

def format_stats(p):
    return (
        f"📊 <b>СТАТИСТИКА</b>\n"
        f"💰 Баланс: {p['balance']}₽\n"
        f"⭐ Репутация: {p['reputation']}/100\n"
        f"📅 День: {p['day']}\n"
        f"📦 Товаров в инвентаре: {len(p['inventory'])}\n"
        f"💸 Всего заработано: {p['total_earned']}₽\n"
        f"🛒 Всего потрачено на закуп: {p['total_spent']}₽\n"
        f"📋 Продано товаров: {p['items_sold']} шт.\n"
        f"⚠️ Раз кинули поставщики: {p['scam_times']}"
    )

# ==================== КОМАНДЫ ====================

@dp.message_handler(commands=['start'])
async def start_game(message: types.Message):
    await message.answer(
        f"🎮 <b>ReSell Tycoon</b> — Симулятор перекупщика\n\n"
        f"Ты — товарщик с бюджетом 5 000₽.\n"
        f"Твоя цель — раскрутиться до 50 000₽.\n\n"
        f"🔹 Закупай товары у поставщиков\n"
        f"🔹 Продавай их покупателям (приходят сами)\n"
        f"🔹 Следи за рыночным спросом\n"
        f"🔹 Остерегайся кидал-поставщиков\n\n"
        f"Готов? Жми <b>/play</b> чтобы начать!",
        parse_mode="HTML"
    )

@dp.message_handler(commands=['play'])
async def new_game(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    players[user_id] = {
        "balance": 5000,
        "reputation": 20,
        "inventory": [],
        "day": 1,
        "total_earned": 0,
        "total_spent": 0,
        "items_sold": 0,
        "scam_times": 0,
        "market_demand": {cat: 1.0 for cat in CATEGORIES},
        "current_event": None,
        "stat_earned_today": 0,
        "stat_sold_today": 0,
    }
    p = players[user_id]

    # Генерируем событие дня
    event = generate_daily_event()
    p["current_event"] = event
    if event:
        apply_market_event(p, event)

    await state.update_data(user_id=user_id)
    await GameState.playing.set()

    event_text = f"\n\n{event['text']}" if event else ""
    await message.answer(
        f"🌟 <b>ДЕНЬ {p['day']}</b>\n"
        f"Твой стартовый баланс: {p['balance']}₽{event_text}\n\n"
        f"Выбери действие:",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

def get_main_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🏭 ЗАКУПИТЬСЯ У ПОСТАВЩИКОВ", callback_data="action_buy"),
        InlineKeyboardButton("📦 МОЙ ИНВЕНТАРЬ", callback_data="action_inventory"),
        InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="action_stats"),
        InlineKeyboardButton("⏩ СЛЕДУЮЩИЙ ДЕНЬ", callback_data="action_nextday"),
        InlineKeyboardButton("🏆 ЗАВЕРШИТЬ ИГРУ", callback_data="action_end"),
    )
    return kb

# ==================== ГЛАВНОЕ МЕНЮ ====================

@dp.callback_query_handler(lambda c: c.data == "action_buy", state=GameState.playing)
async def show_suppliers(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=1)
    for s in SUPPLIERS:
        kb.add(InlineKeyboardButton(
            f"{s['emoji']} {s['name']} | Рейтинг: {s['rating']}/10 | Шанс кидка: {s['scam_chance']}%",
            callback_data=f"supplier_{SUPPLIERS.index(s)}"
        ))
    kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="action_back"))

    await callback.message.edit_text(
        "🏭 <b>ПОСТАВЩИКИ:</b>\n\n"
        "Чем выше рейтинг — тем надёжнее, но дороже.\n"
        "Чем ниже рейтинг — тем дешевле, но могут кинуть.\n\n"
        "Выбирай поставщика:",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.callback_query_handler(lambda c: c.data.startswith("supplier_"), state=GameState.playing)
async def show_supplier_items(callback: CallbackQuery, state: FSMContext):
    supplier_idx = int(callback.data.split("_")[1])
    supplier = SUPPLIERS[supplier_idx]

    await state.update_data(current_supplier_idx=supplier_idx)

    # Показываем 4 случайных товара от этого поставщика
    items = random.sample(BASE_ITEMS, min(4, len(BASE_ITEMS)))

    kb = InlineKeyboardMarkup(row_width=1)
    for i, item in enumerate(items):
        price = get_item_price(item["base_price"], supplier)
        kb.add(InlineKeyboardButton(
            f"{item['cat']} {item['name']} — {price}₽",
            callback_data=f"buyitem_{i}"
        ))
    kb.add(InlineKeyboardButton("🔄 Обновить товары", callback_data=f"supplier_{supplier_idx}"))
    kb.add(InlineKeyboardButton("🔙 К поставщикам", callback_data="action_buy"))
    kb.add(InlineKeyboardButton("🏠 В меню", callback_data="action_back"))

    # Сохраняем товары в состоянии
    await state.update_data(supplier_items=items)

    await callback.message.edit_text(
        f"{supplier['emoji']} <b>{supplier['name']}</b>\n"
        f"⭐ Рейтинг: {supplier['rating']}/10\n"
        f"⚠️ Шанс кидка: {supplier['scam_chance']}%\n\n"
        f"Выбери товар для закупа:",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.callback_query_handler(lambda c: c.data.startswith("buyitem_"), state=GameState.playing)
async def buy_item(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item_idx = int(callback.data.split("_")[1])
    supplier_idx = data.get("current_supplier_idx", 0)
    items = data.get("supplier_items", [])

    if item_idx >= len(items):
        await callback.answer("Ошибка загрузки товара. Попробуй снова.")
        return

    item = items[item_idx]
    supplier = SUPPLIERS[supplier_idx]
    price = get_item_price(item["base_price"], supplier)
    user_id = callback.from_user.id
    p = get_player(user_id)

    if p["balance"] < price:
        await callback.answer("❌ Недостаточно денег для закупа!")
        return

    # Проверяем кидалово
    if random.randint(1, 100) <= supplier["scam_chance"]:
        # КИНУЛИ!
        p["balance"] -= price
        p["total_spent"] += price
        p["scam_times"] += 1
        p["reputation"] = max(0, p["reputation"] - 5)
        await callback.message.edit_text(
            f"💀 <b>ТЕБЯ КИНУЛИ!</b>\n\n"
            f"Поставщик {supplier['name']} взял деньги и пропал.\n"
            f"Ты потерял {price}₽.\n"
            f"Текущий баланс: {p['balance']}₽\n\n"
            f"Урок: не доверяй поставщикам с низким рейтингом.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🏠 В меню", callback_data="action_back")
            )
        )
        await check_game_over(callback, p)
        return

    # Успешная покупка
    p["balance"] -= price
    p["total_spent"] += price
    demand = p["market_demand"].get(item["cat"], 1.0)
    market_price = get_market_price(item["base_price"], demand)

    p["inventory"].append({
        "name": f"{item['cat']} {item['name']}",
        "cat": item["cat"],
        "buy_price": price,
        "market_price": market_price,
        "base_price": item["base_price"],
    })

    await callback.message.edit_text(
        f"✅ <b>ТОВАР КУПЛЕН!</b>\n\n"
        f"📦 {item['cat']} {item['name']}\n"
        f"💰 Цена закупа: {price}₽\n"
        f"📊 Рыночная цена: ~{market_price}₽\n"
        f"💼 Твой баланс: {p['balance']}₽\n"
        f"📦 В инвентаре: {len(p['inventory'])} товаров",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔄 Купить ещё у этого поставщика", callback_data=f"supplier_{supplier_idx}"),
            InlineKeyboardButton("🏠 В меню", callback_data="action_back")
        )
    )

# ==================== ИНВЕНТАРЬ И ПРОДАЖА ====================

@dp.callback_query_handler(lambda c: c.data == "action_inventory", state=GameState.playing)
async def show_inventory(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    p = get_player(user_id)

    if not p["inventory"]:
        await callback.message.edit_text(
            "📦 Инвентарь пуст. Сначала закупись у поставщиков!",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🏭 К поставщикам", callback_data="action_buy"),
                InlineKeyboardButton("🏠 В меню", callback_data="action_back")
            ),
            parse_mode="HTML"
        )
        return

    kb = InlineKeyboardMarkup(row_width=1)
    for i, item in enumerate(p["inventory"]):
        kb.add(InlineKeyboardButton(
            f"{item['name']} | Закуп: {item['buy_price']}₽ | ~{item['market_price']}₽",
            callback_data=f"sell_{i}"
        ))
    kb.add(InlineKeyboardButton("🏠 В меню", callback_data="action_back"))

    await callback.message.edit_text(
        format_inventory(p["inventory"]) + "\n\nВыбери товар, чтобы попытаться продать:",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.callback_query_handler(lambda c: c.data.startswith("sell_"), state=GameState.playing)
async def try_sell_item(callback: CallbackQuery, state: FSMContext):
    item_idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    p = get_player(user_id)

    if item_idx >= len(p["inventory"]):
        await callback.answer("Товар не найден.")
        return

    item = p["inventory"][item_idx]
    buyer_name = random.choice(BUYER_NAMES)

    # Шанс что покупатель вообще заинтересован
    demand = p["market_demand"].get(item["cat"], 1.0)
    interest_chance = min(0.9, demand * 0.6)

    if random.random() > interest_chance:
        # Покупатель не заинтересован в категории
        msg_template = random.choice(BUYER_NOT_INTERESTED)
        await callback.message.edit_text(
            msg_template.format(name=buyer_name, cat=item["cat"]) + "\n\nПопробуй продать другой товар.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("📦 В инвентарь", callback_data="action_inventory"),
                InlineKeyboardButton("🏠 В меню", callback_data="action_back")
            )
        )
        return

    # Покупатель предлагает цену (70-110% от рыночной)
    offer_mult = random.uniform(0.7, 1.1)
    offer_price = int(item["market_price"] * offer_mult)

    await state.update_data(selling_item_idx=item_idx, buyer_offer=offer_price, buyer_name=buyer_name)

    msg_template = random.choice(BUYER_HAGGLE_MESSAGES)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Согласиться", callback_data="accept_offer"),
        InlineKeyboardButton("📈 Торговаться (+10%)", callback_data="haggle_up"),
        InlineKeyboardButton("❌ Отказаться", callback_data="decline_offer"),
    )

    await callback.message.edit_text(
        f"👤 Покупатель: <b>{buyer_name}</b>\n\n"
        f"📦 Товар: {item['name']}\n"
        f"💰 Твоя цена закупа: {item['buy_price']}₽\n"
        f"📊 Рыночная: ~{item['market_price']}₽\n\n"
        f"{msg_template.format(name=buyer_name, offer=offer_price)}\n\n"
        f"Твой ответ:",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.callback_query_handler(lambda c: c.data == "accept_offer", state=GameState.playing)
async def accept_offer(callback: CallbackQuery, state: FSMContext):
    await complete_sale(callback, state, haggle_success=True, haggle_bonus=0)

@dp.callback_query_handler(lambda c: c.data == "haggle_up", state=GameState.playing)
async def haggle_up(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    buyer_name = data.get("buyer_name", "Покупатель")
    offer = data.get("buyer_offer", 0)
    new_offer = int(offer * 1.1)

    # Шанс что покупатель согласится на повышение (зависит от репутации)
    user_id = callback.from_user.id
    p = get_player(user_id)
    haggle_chance = 0.3 + (p["reputation"] / 100) * 0.4  # 30-70%

    if random.random() < haggle_chance:
        await state.update_data(buyer_offer=new_offer)
        await complete_sale(callback, state, haggle_success=True, haggle_bonus=new_offer - offer)
    else:
        # Покупатель уходит
        await callback.message.edit_text(
            f"👤 {buyer_name}: ❌ Не, так не пойдёт. Я пошёл.\n\nПокупатель ушёл. Попробуй с другим товаром.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("📦 В инвентарь", callback_data="action_inventory"),
                InlineKeyboardButton("🏠 В меню", callback_data="action_back")
            )
        )

@dp.callback_query_handler(lambda c: c.data == "decline_offer", state=GameState.playing)
async def decline_offer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    buyer_name = data.get("buyer_name", "Покупатель")
    await callback.message.edit_text(
        f"👤 {buyer_name}: 👋 Ладно, бывай.\n\nТы отказался от предложения.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("📦 В инвентарь", callback_data="action_inventory"),
            InlineKeyboardButton("🏠 В меню", callback_data="action_back")
        )
    )

async def complete_sale(callback: CallbackQuery, state: FSMContext, haggle_success, haggle_bonus):
    data = await state.get_data()
    item_idx = data.get("selling_item_idx", 0)
    buyer_name = data.get("buyer_name", "Покупатель")
    final_offer = data.get("buyer_offer", 0)
    user_id = callback.from_user.id
    p = get_player(user_id)

    if item_idx >= len(p["inventory"]):
        await callback.answer("Ошибка. Товар уже не в инвентаре.")
        return

    item = p["inventory"].pop(item_idx)
    p["balance"] += final_offer
    profit = final_offer - item["buy_price"]
    p["total_earned"] += profit
    p["items_sold"] += 1
    p["stat_earned_today"] += profit
    p["stat_sold_today"] += 1

    # Повышаем репутацию за успешную продажу
    p["reputation"] = min(100, p["reputation"] + random.randint(1, 5))

    msg_template = random.choice(BUYER_ACCEPT_MESSAGES)
    haggle_text = f"\n🔥 Удалось выбить на {haggle_bonus}₽ больше!" if haggle_bonus > 0 else ""

    await callback.message.edit_text(
        f"{msg_template.format(name=buyer_name)}\n\n"
        f"📦 Продан: {item['name']}\n"
        f"💰 Цена продажи: {final_offer}₽\n"
        f"💵 Прибыль: {profit}₽{haggle_text}\n"
        f"💼 Баланс: {p['balance']}₽\n"
        f"⭐ Репутация: {p['reputation']}/100",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("📦 В инвентарь", callback_data="action_inventory"),
            InlineKeyboardButton("🏠 В меню", callback_data="action_back")
        )
    )

    await check_game_over(callback, p)

# ==================== СТАТИСТИКА И ДНИ ====================

@dp.callback_query_handler(lambda c: c.data == "action_stats", state=GameState.playing)
async def show_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)

    demand_lines = []
    for cat, mult in p["market_demand"].items():
        emoji = "📈" if mult > 1.0 else "📉" if mult < 1.0 else "➡️"
        demand_lines.append(f"{emoji} {cat}: x{mult:.1f}")

    await callback.message.edit_text(
        format_stats(p) + "\n\n📊 <b>СПРОС НА РЫНКЕ:</b>\n" + "\n".join(demand_lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🏠 В меню", callback_data="action_back")
        )
    )

@dp.callback_query_handler(lambda c: c.data == "action_nextday", state=GameState.playing)
async def next_day(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    p = get_player(user_id)

    # Итоги дня
    day_summary = (
        f"🌙 <b>ИТОГИ ДНЯ {p['day']}</b>\n"
        f"💰 Заработано сегодня: {p['stat_earned_today']}₽\n"
        f"📋 Продано товаров: {p['stat_sold_today']} шт.\n"
        f"💼 Баланс: {p['balance']}₽"
    )

    # Сброс дневной статистики
    p["day"] += 1
    p["stat_earned_today"] = 0
    p["stat_sold_today"] = 0

    # Обновляем спрос (немного случайности)
    for cat in CATEGORIES:
        p["market_demand"][cat] *= random.uniform(0.85, 1.15)
        p["market_demand"][cat] = max(0.3, min(3.0, p["market_demand"][cat]))

    # Новое событие
    event = generate_daily_event()
    p["current_event"] = event
    if event:
        apply_market_event(p, event)

    event_text = f"\n\n{event['text']}" if event else ""

    # Если инвентарь не пуст — шанс что какой-то товар потерял в цене (залежался)
    if p["inventory"] and random.random() < 0.2:
        for item in p["inventory"]:
            item["market_price"] = int(item["market_price"] * random.uniform(0.7, 0.95))
        event_text += "\n\n⚠️ Некоторые товары в инвентаре потеряли в цене (залежались)."

    await callback.message.edit_text(
        f"{day_summary}\n\n☀️ <b>ДЕНЬ {p['day']}</b>{event_text}\n\nВыбери действие:",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query_handler(lambda c: c.data == "action_end", state=GameState.playing)
async def end_game(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    p = get_player(user_id)
    await state.finish()

    if p["balance"] >= 50000:
        result = "🏆 <b>ПОБЕДА!</b> Ты раскрутился до 50 000₽ и стал королём товарки!"
    elif p["balance"] <= 0:
        result = "💀 <b>БАНКРОТ!</b> Ты потерял все деньги. Не расстраивайся — это игра."
    else:
        result = "🎮 Игра окончена. Неплохой результат!"

    await callback.message.edit_text(
        f"{result}\n\n{format_stats(p)}\n\n"
        f"Хочешь попробовать в реальности?\n"
        f"Заходи в {CHANNEL_NAME} — бери вещи на реализацию и зарабатывай без вложений!\n"
        f"👉 {CHANNEL_LINK}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔄 Сыграть ещё раз", callback_data="restart_game")
        )
    )

@dp.callback_query_handler(lambda c: c.data == "restart_game")
async def restart_game(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in players:
        del players[user_id]
    await callback.message.edit_text("Перезапуск... Напиши /play чтобы начать новую игру!")

@dp.callback_query_handler(lambda c: c.data == "action_back", state=GameState.playing)
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    event = p.get("current_event")
    event_text = f"\n\n{event['text']}" if event else ""
    await callback.message.edit_text(
        f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽{event_text}\n\nВыбери действие:",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

async def check_game_over(callback, p):
    if p["balance"] >= 50000:
        await callback.message.answer(
            f"🏆 <b>ПОЗДРАВЛЯЮ!</b>\n\n"
            f"Ты достиг 50 000₽! Ты — легенда товарки!\n\n"
            f"Готов к реальным продажам? Заходи в {CHANNEL_NAME} 👉 {CHANNEL_LINK}",
            parse_mode="HTML"
        )
    elif p["balance"] <= 0:
        await callback.message.answer(
            f"💀 <b>БАНКРОТ</b>\n\n"
            f"Деньги кончились. Но это всего лишь игра!\n"
            f"В реальности ты можешь начать без вложений — в {CHANNEL_NAME} дают товары на реализацию.\n"
            f"Попробуй: {CHANNEL_LINK}\n\n"
            f"Напиши /play чтобы сыграть снова.",
            parse_mode="HTML"
        )

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    print("🎮 ReSell Tycoon запущен!")
    executor.start_polling(dp, skip_updates=True)