import logging
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== НАСТРОЙКИ (РЕКВИЗИТЫ) ====================
TOKEN = "8892100518:AAFJ6-7pM2hwP9LEJkAPwOloaqiaku9Dy7w"

# Реквизиты для пополнения баланса вручную (если средств недостаточно)
SBP_DETAILS = "💳 **Сбер / Т-Банк (СБП):**\n`+7 (999) 000-00-00`\n(Получатель: Имя Ф.)"
ASIA_DETAILS = "🌏 **Карты стран Азии (Казахстан / Узбекистан / др.):**\nНомер карты: `4400 0000 0000 0000`\n(Банк / Получатель)"

ADMIN_USERNAME = "@arrhiv1"
# ===============================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ----------------- БАЗА ДАННЫХ (SQLite) -----------------
def db_start():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            player_id TEXT,
            balance REAL DEFAULT 0.0
        )
    """)
    # Таблица сохраненных карт покупателей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_cards (
            user_id INTEGER,
            card_number TEXT
        )
    """)
    conn.commit()
    conn.close()

db_start()

class PurchaseState(StatesGroup):
    waiting_for_player_id = State()
    waiting_for_card = State()

# Цены пакетов UC (в рублях)
UC_PRICES = {
    "60": 90.0,
    "325": 450.0,
    "660": 900.0,
    "1800": 2300.0,
    "3850": 4600.0,
    "8100": 9200.0
}

# ----------------- КОМАНДА /START -----------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?, 0.0)", (user_id, username))
    conn.commit()
    conn.close()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Купить UC", callback_data="buy_uc")
    builder.button(text="👤 Мой профиль", callback_data="profile")
    builder.button(text="🛠 Поддержка", callback_data="support")
    builder.adjust(1, 2)
    
    await message.answer(
        "👋 **Добро пожаловать в официальный бот по покупке UC!**\n\n"
        "Пожалуйста, выберите нужный раздел:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

# ----------------- МЕНЮ ПОКУПКИ UC -----------------
@dp.callback_query(F.data == "buy_uc")
async def uc_packages(callback: types.CallbackQuery):
    await callback.answer()
    builder = InlineKeyboardBuilder()
    for uc, price in UC_PRICES.items():
        builder.button(text=f"{uc} UC - {int(price)} ₽", callback_data=f"uc_{uc}")
    builder.button(text="⬅️ Назад", callback_data="back_home")
    builder.adjust(2, 2, 2, 1)
    
    await callback.message.edit_text(
        "📦 **Выберите нужный пакет UC:**",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("uc_"))
async def select_uc(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    uc_type = callback.data.split("_")[1]
    await state.update_data(chosen_uc=uc_type)
    
    await callback.message.answer(
        "🆔 Пожалуйста, введите ваш **Player ID** в PUBG Mobile:\n"
        "(Пример: `5123456789`)",
        parse_mode="Markdown"
    )
    await state.set_state(PurchaseState.waiting_for_player_id)

@dp.message(PurchaseState.waiting_for_player_id)
async def process_player_id(message: types.Message, state: FSMContext):
    player_id = message.text.strip()
    await state.update_data(player_id=player_id)
    data = await state.get_data()
    chosen_uc = data.get("chosen_uc")
    price = UC_PRICES.get(chosen_uc, 0)
    
    # Сохраняем player_id в базу
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET player_id = ? WHERE user_id = ?", (player_id, message.from_user.id))
    # Проверяем баланс и сохраненную карту пользователя
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id))
    balance_row = cursor.fetchone()
    balance = balance_row[0] if balance_row else 0.0

    cursor.execute("SELECT card_number FROM user_cards WHERE user_id = ?", (message.from_user.id,))
    card_row = cursor.fetchone()
    conn.close()
    
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    
    # Если баланс позволяет — даем кнопку быстрой покупки
    if balance >= price:
        builder.button(text=f"✅ Купить с баланса ({int(price)} ₽)", callback_data=f"pay_balance_{chosen_uc}")
    else:
        builder.button(text="💳 Пополнить баланс", callback_data="top_up")
        
    if card_row:
        builder.button(text="💳 Оплатить сохраненной картой", callback_data=f"pay_card_{chosen_uc}")
        
    builder.button(text="🛒 Выбрать другой пакет", callback_data="buy_uc")
    builder.adjust(1)

    card_info = f"\n💳 Ваша карта: `{card_row[0]}`" if card_row else "\n💳 Карты не привязаны (можно привязать в профиле)"

    await message.answer(
        f"✅ **Данные получены!**\n\n"
        f"📦 Пакет: **{chosen_uc} UC**\n"
        f"🆔 Игровой ID: `{player_id}`\n"
        f"💰 Стоимость: **{int(price)} ₽**\n"
        f"💰 Ваш баланс: **{balance} ₽**"
        f"{card_info}\n\n"
        f"Выберите способ завершения покупки:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

# Покупка за счет внутреннего баланса
@dp.callback_query(F.data.startswith("pay_balance_"))
async def pay_with_balance(callback: types.CallbackQuery):
    uc_type = callback.data.split("_")[2]
    price = UC_PRICES.get(uc_type, 0)
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, player_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row or row[0] < price:
        await callback.answer("❌ Недостаточно средств на балансе!", show_alert=True)
        conn.close()
        return
        
    new_balance = row[0] - price
    player_id = row[1]
    
    # Списываем баланс
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(
        f"🎉 **Покупка успешно завершена!**\n\n"
        f"📦 Пакет: **{uc_type} UC**\n"
        f"🆔 ID: `{player_id}`\n"
        f"💸 Списано: **{int(price)} ₽**\n"
        f"💰 Остаток на балансе: **{new_balance} ₽**\n\n"
        f" UC скоро поступят на ваш аккаунт в PUBG Mobile!",
        parse_mode="Markdown"
    )

# Покупка с привязанной карты (симуляция прямого списания/автономной покупки)
@dp.callback_query(F.data.startswith("pay_card_"))
async def pay_with_saved_card(callback: types.CallbackQuery):
    uc_type = callback.data.split("_")[2]
    price = UC_PRICES.get(uc_type, 0)
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT player_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    player_id = row[0] if row else "Не указан"
    conn.close()
    
    await callback.message.edit_text(
        f"✅ **Оплата с привязанной карты прошла успешно!**\n\n"
        f"📦 Пакет: **{uc_type} UC**\n"
        f"🆔 ID: `{player_id}`\n"
        f"💳 Оплачено: **{int(price)} ₽**\n\n"
        f"🚀 Заказ передан в обработку, UC будут зачислены в течение пары минут!",
        parse_mode="Markdown"
    )

# ----------------- ПРОФИЛЬ И УПРАВЛЕНИЕ КАРТАМИ -----------------
@dp.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT player_id, balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    cursor.execute("SELECT card_number FROM user_cards WHERE user_id = ?", (user_id,))
    card_row = cursor.fetchone()
    conn.close()
    
    player_id = row[0] if row and row[0] else "Не зарегистрирован ❌"
    balance = row[1] if row and row[1] is not None else 0.0
    card_number = card_row[0] if card_row else "Не привязана ❌"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Пополнить баланс", callback_data="top_up")
    builder.button(text="➕ Добавить / Изменить карту", callback_data="add_card")
    builder.button(text="⬅️ Назад", callback_data="back_home")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"👤 **Ваш профиль:**\n\n"
        f"🆔 Telegram ID: `{user_id}`\n"
        f"🎮 PUBG Player ID: `{player_id}`\n"
        f"💳 Моя карта: `{card_number}`\n"
        f"💰 Баланс: **{balance} ₽**",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

# Добавление карты пользователем
@dp.callback_query(F.data == "add_card")
async def start_add_card(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "💳 Пожалуйста, введите номер вашей банковской карты (или кошелька):\n"
        "(Пример: `4400 1122 3344 5566`)",
        parse_mode="Markdown"
    )
    await state.set_state(PurchaseState.waiting_for_card)

@dp.message(PurchaseState.waiting_for_card)
async def process_card_input(message: types.Message, state: FSMContext):
    card_number = message.text.strip()
    user_id = message.from_user.id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    # Удаляем старую карту, если была, и записываем новую
    cursor.execute("DELETE FROM user_cards WHERE user_id = ?", (user_id,))
    cursor.execute("INSERT INTO user_cards (user_id, card_number) VALUES (?, ?)", (user_id, card_number))
    conn.commit()
    conn.close()
    
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 В профиль", callback_data="profile")
    builder.adjust(1)
    
    await message.answer(
        f"✅ **Карта успешно сохранена!**\n\n"
        f"Номер: `{card_number}`\n\n"
        f"Теперь вы можете быстро использовать ее для покупок.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

# Пополнение баланса
@dp.callback_query(F.data == "top_up")
async def top_up_balance(callback: types.CallbackQuery):
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 СБП / Карты РФ", callback_data="pay_sbp")
    builder.button(text="🌏 Карты стран Азии", callback_data="pay_asia")
    builder.button(text="⬅️ Назад в профиль", callback_data="profile")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "💳 **Пополнение баланса**\n\n"
        "Выберите способ перевода для пополнения счета:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "pay_sbp")
async def pay_sbp(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        f"🇷🇺 **Оплата через СБП или карты РФ:**\n\n"
        f"{SBP_DETAILS}\n\n"
        f"📸 После перевода отправьте скриншот/чек администратору: {ADMIN_USERNAME} для зачисления средств на баланс.",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "pay_asia")
async def pay_asia(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        f"🌏 **Оплата картами стран Азии:**\n\n"
        f"{ASIA_DETAILS}\n\n"
        f"📸 После перевода отправьте скриншот/чек администратору: {ADMIN_USERNAME} для зачисления средств на баланс.",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "back_home")
async def back_home(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Купить UC", callback_data="buy_uc")
    builder.button(text="👤 Мой профиль", callback_data="profile")
    builder.button(text="🛠 Поддержка", callback_data="support")
    builder.adjust(1, 2)
    
    await callback.message.edit_text(
        "👋 **Главное меню:**\n\nПожалуйста, выберите нужный раздел:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "support")
async def support_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(f"🛠 Для связи с администратором: {ADMIN_USERNAME}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
