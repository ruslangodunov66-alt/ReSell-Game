import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

import game_db
from settings import BOT_TOKEN, ADMIN_IDS

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
game_db.init_db()
game_db.generate_market()  # создаём рынок при старте

# ---------- КЛАВИАТУРЫ ----------
def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить у поставщиков", callback_data="buy_menu")],
        [InlineKeyboardButton(text="💰 Продать товар клиенту", callback_data="sell_menu")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile")],
        [InlineKeyboardButton(text="🏆 Лидеры", callback_data="leaders")]
    ])

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

# ---------- СТАРТ ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    game_db.register_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "🧑‍💼 *Торговый симулятор*\n\n"
        "Ты — предприниматель.\n"
        "🛒 Покупай товары у поставщиков (цена зависит от их рейтинга)\n"
        "💰 Продавай клиентам (цена зависит от сезона и навыка продаж)\n"
        "📈 Повышай навыки за опыт (опыт дают сделки)\n"
        "🤝 Приглашай друзей — ускоряй прокачку\n\n"
        "👇 *Выбери действие:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard()
    )

# ---------- ПОКУПКА ТОВАРА ----------
@dp.callback_query(F.data == "buy_menu")
async def buy_menu(callback: types.CallbackQuery):
    offers = game_db.get_market_offers(callback.from_user.id)
    if not offers:
        await callback.message.edit_text("⚠️ Рынок пуст. Попробуйте позже.")
        await callback.answer()
        return
    text = "🛒 *Товары от поставщиков:*\n\n"
    for o in offers[:20]:
        text += f"📦 {o['product']}\n💰 {o['price']} 💎\n🍂 Сезон: {o['season']}\n⏳ До {o['expires_at'].strftime('%H:%M')}\n\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить рынок (20 💎)", callback_data="refresh_market")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "refresh_market")
async def refresh_market(callback: types.CallbackQuery):
    user = game_db.get_user(callback.from_user.id)
    if not user or user['balance'] < 20:
        await callback.answer("❌ Не хватает 20 💎 для обновления!", show_alert=True)
        return
    game_db.update_user(callback.from_user.id, balance=user['balance'] - 20)
    game_db.generate_market()
    await callback.answer("✅ Рынок обновлён!", show_alert=True)
    await buy_menu(callback)

# ---------- ПРОДАЖА ТОВАРА (генерация клиента) ----------
@dp.callback_query(F.data == "sell_menu")
async def sell_menu(callback: types.CallbackQuery):
    inv = game_db.get_inventory(callback.from_user.id)
    if not inv:
        await callback.message.edit_text("📭 *Инвентарь пуст.* Купите товары у поставщиков.", parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
        await callback.answer()
        return
    text = "📦 *Ваши товары:*\n\n"
    for item in inv:
        text += f"• {item['product']} — {item['quantity']} шт.\n"
    keyboard = []
    for item in inv:
        keyboard.append([InlineKeyboardButton(text=f"Продать {item['product']}", callback_data=f"choose_{item['product']}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@dp.callback_query(F.data.startswith("choose_"))
async def choose_product(callback: types.CallbackQuery):
    product = callback.data[7:]
    # Генерируем предложение от клиента
    offer = game_db.generate_customer_offer(callback.from_user.id, product)
    if not offer:
        await callback.answer("❌ Не удалось создать предложение", show_alert=True)
        return
    await callback.answer(f"👤 {offer['customer']} предлагает {offer['price']} 💎 за {product}!\nИспользуйте /sell_confirm для принятия.", show_alert=True)

@dp.message(Command("sell_confirm"))
async def confirm_sale(message: types.Message):
    user_id = message.from_user.id
    offer = game_db.get_offer(user_id)
    if not offer:
        await message.answer("❌ Нет активного предложения. Сначала выберите товар для продажи.")
        return
    product = offer['product']
    price = offer['price']
    if not game_db.remove_from_inventory(user_id, product):
        await message.answer("❌ Товар уже продан или его нет в инвентаре.")
        game_db.clear_offer(user_id)
        return
    user = game_db.get_user(user_id)
    game_db.update_user(user_id, balance=user['balance'] + price)
    level_up = game_db.add_exp(user_id, 25)  # опыт за продажу
    game_db.earn_achievement(user_id, "Первая продажа")
    msg = f"✅ Продажа {product} за {price} 💎 совершена!\n📈 Опыт +25"
    if level_up:
        msg += f"\n🎉 *Уровень повышен до {level_up}!*"
    await message.answer(msg, parse_mode=ParseMode.MARKDOWN)
    game_db.clear_offer(user_id)

# ---------- ПРОФИЛЬ И ПРОКАЧКА ----------
@dp.callback_query(F.data == "my_profile")
async def my_profile(callback: types.CallbackQuery):
    user = game_db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка данных")
        return
    text = (
        "👤 *Ваш профиль*\n\n"
        f"💰 Баланс: {user['balance']} 💎\n"
        f"📊 Уровень: {user['level']}\n"
        f"⭐ Опыт: {user['exp']}/{user['level']*100}\n"
        f"🤝 Навык продаж: {user['sell_skill']}\n"
        f"📦 Навык закупок: {user['buy_skill']}\n"
        f"👥 Приглашено друзей: {user.get('referrals', 0)}\n"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Повысить навык продаж (200 опыта)", callback_data="up_sell")],
        [InlineKeyboardButton(text="🏭 Повысить навык закупок (200 опыта)", callback_data="up_buy")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "up_sell")
async def upgrade_sell(callback: types.CallbackQuery):
    user = game_db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return
    if user['sell_skill'] >= 10:
        await callback.answer("✅ Навык продаж уже максимальный (10)!", show_alert=True)
        return
    if user['exp'] < 200:
        await callback.answer("❌ Не хватает 200 опыта!", show_alert=True)
        return
    new_skill = user['sell_skill'] + 1
    new_exp = user['exp'] - 200
    game_db.update_user(callback.from_user.id, sell_skill=new_skill, exp=new_exp)
    await callback.answer(f"✅ Навык продаж повышен до {new_skill}!", show_alert=True)
    await my_profile(callback)

@dp.callback_query(F.data == "up_buy")
async def upgrade_buy(callback: types.CallbackQuery):
    user = game_db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return
    if user['buy_skill'] >= 10:
        await callback.answer("✅ Навык закупок уже максимальный (10)!", show_alert=True)
        return
    if user['exp'] < 200:
        await callback.answer("❌ Не хватает 200 опыта!", show_alert=True)
        return
    new_skill = user['buy_skill'] + 1
    new_exp = user['exp'] - 200
    game_db.update_user(callback.from_user.id, buy_skill=new_skill, exp=new_exp)
    await callback.answer(f"✅ Навык закупок повышен до {new_skill}!", show_alert=True)
    await my_profile(callback)

# ---------- ЛИДЕРЫ ----------
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

# ---------- НАЗАД ----------
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🧑‍💼 *Торговый симулятор*\n\n👇 *Выбери действие:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard()
    )
    await callback.answer()

async def main():
    print("🚀 Торговый симулятор запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())