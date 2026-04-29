import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from settings import BOT_TOKEN, ADMIN_IDS
from game_db import init_db, register_user, get_user, update_user, add_exp, get_market_offers, generate_market, earn_achievement

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
init_db()

# --- Клавиатуры ---
def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Купить товар", callback_data="buy_menu")],
        [InlineKeyboardButton(text="💰 Мой бизнес", callback_data="my_business")],
        [InlineKeyboardButton(text="📊 Лидеры", callback_data="leaders")]
    ])

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

# --- Хендлеры ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    register_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "🧑‍💼 *Добро пожаловать в товарный бизнес!*\n\n"
        "Покупай товар по выгодной цене 🔥\n"
        "Продавай дороже 💰\n"
        "Прокачивай навыки 📈\n"
        "Стань лучшим предпринимателем!\n\n"
        "👇 *Выбери действие:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard()
    )

@dp.callback_query(F.data == "buy_menu")
async def buy_menu(callback: types.CallbackQuery):
    offers = get_market_offers()
    if not offers:
        await callback.message.edit_text("⚠️ Рынок пуст. Попробуй позже.")
        await callback.answer()
        return
    text = "🛒 *Доступные товары для покупки:*\n\n"
    for o in offers:
        exp_date = o['expires_at'].strftime("%d.%m %H:%M")
        text += f"📦 *{o['product']}*\n"
        text += f"💰 Цена: {o['price']}$\n"
        text += f"📊 Спрос: {o['demand']}\n"
        text += f"⏳ До {exp_date}\n\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить рынок (10 💎)", callback_data="refresh_market")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "refresh_market")
async def refresh_market(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or user['balance'] < 10:
        await callback.answer("❌ Не хватает 10 💎 для обновления!", show_alert=True)
        return
    update_user(callback.from_user.id, balance=user['balance']-10)
    generate_market()
    await callback.answer("✅ Рынок обновлён!", show_alert=True)
    await buy_menu(callback)

@dp.callback_query(F.data == "my_business")
async def my_business(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка данных")
        return
    text = (
        "🏢 *Твой бизнес*\n\n"
        f"💰 Баланс: {user['balance']} 💎\n"
        f"📊 Уровень: {user['level']}\n"
        f"⭐ Опыт: {user['exp']}/{user['level']*100}\n"
        f"🤝 Навык продаж: {user['sell_skill']}\n"
        f"📦 Навык закупок: {user['buy_skill']}\n"
        f"🏆 Побед: {user['wins']}\n"
        f"😞 Поражений: {user['losses']}\n"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Прокачать навык продаж", callback_data="up_sell")],
        [InlineKeyboardButton(text="🏭 Прокачать навык закупок", callback_data="up_buy")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "up_sell")
async def upgrade_sell(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    cost = user['sell_skill'] * 100
    if user['balance'] >= cost:
        new_skill = user['sell_skill'] + 1
        new_balance = user['balance'] - cost
        update_user(callback.from_user.id, balance=new_balance, sell_skill=new_skill)
        await callback.answer(f"✅ Навык продаж повышен до {new_skill}!", show_alert=True)
        await my_business(callback)
    else:
        await callback.answer(f"❌ Не хватает {cost} 💎", show_alert=True)

@dp.callback_query(F.data == "up_buy")
async def upgrade_buy(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    cost = user['buy_skill'] * 100
    if user['balance'] >= cost:
        new_skill = user['buy_skill'] + 1
        new_balance = user['balance'] - cost
        update_user(callback.from_user.id, balance=new_balance, buy_skill=new_skill)
        await callback.answer(f"✅ Навык закупок повышен до {new_skill}!", show_alert=True)
        await my_business(callback)
    else:
        await callback.answer(f"❌ Не хватает {cost} 💎", show_alert=True)

@dp.callback_query(F.data == "leaders")
async def leaders(callback: types.CallbackQuery):
    conn = game_db.sqlite3.connect(game_db.DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT username, balance, level FROM users ORDER BY balance DESC LIMIT 10')
    rows = cur.fetchall()
    conn.close()
    text = "🏅 *ТОП предпринимателей*\n\n"
    for i, (uname, bal, lvl) in enumerate(rows, 1):
        text += f"{i}. @{uname} — {bal} 💎 (уровень {lvl})\n"
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🧑‍💼 *Товарный бизнес*\n\n👇 *Выбери действие:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard()
    )
    await callback.answer()

# --- Случайное событие (шанс 10% при любой команде) ---
@dp.callback_query()
async def random_event_handler(callback: types.CallbackQuery):
    if random.random() < 0.1:
        user = get_user(callback.from_user.id)
        if user:
            event_type = random.choice(['profit', 'loss'])
            if event_type == 'profit':
                bonus = random.randint(50, 200)
                update_user(callback.from_user.id, balance=user['balance'] + bonus)
                await callback.answer(f"🎉 Удачная сделка! +{bonus} 💎", show_alert=True)
            else:
                penalty = random.randint(30, 150)
                new_balance = max(user['balance'] - penalty, 0)
                update_user(callback.from_user.id, balance=new_balance)
                await callback.answer(f"⚠️ Штраф от налоговой! -{penalty} 💎", show_alert=True)

async def main():
    print("🚀 Товарный бизнес-бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())