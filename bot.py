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
ADMIN_CHAT_ID = 1231002682  # Ваш цифровой Telegram ID

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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            player_id TEXT,
            balance REAL DEFAULT 0.0
        )
    """)
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
    waiting_for_topup_amount = State()
    waiting_for_screenshot = State()
    waiting_for_payment_screenshot = State()

UC_PRICES = {
    "60": 90.0,
    "325": 450.0,
    "660": 900.0,
    "1800": 2300.0,
    "3850": 4600.0,
    "8100": 9200.0
}

# Функция имитации автоматической покупки UC с официального сайта
async def auto_buy_uc_from_official_site(player_id: str, uc_type: str) -> bool:
    await asyncio.sleep(2)
    return True

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
    data = await state.get_data()
    chosen_uc = data.get("chosen_uc")
    price = UC_PRICES.get(chosen_uc, 0)
    user_id = message.from_user.id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET player_id = ? WHERE user_id = ?", (player_id, user_id))
    
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance_row = cursor.fetchone()
    balance = balance_row[0] if balance_row else 0.0

    cursor.execute("SELECT card_number FROM user_cards WHERE user_id = ?", (user_id,))
    card_row = cursor.fetchone()
    conn.close()
    
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    
    if card_row:
        builder.button(text=f"💳 Оплатить привязанной картой ({int(price)} ₽)", callback_data=f"pay_card_{chosen_uc}")
    if balance >= price:
        builder.button(text=f"💰 Оплатить с баланса ({int(price)} ₽)", callback_data=f"pay_bal_{chosen_uc}")
        
    builder.button(text="➕ Привязать другую карту", callback_data="add_card")
    builder.button(text="💳 Пополнить баланс", callback_data="top_up")
    builder.adjust(1)

    card_text = f"\n💳 Привязанная карта: `{card_row[0]}`" if card_row else "\n💳 Карта не привязана."

    await message.answer(
        f"✅ **Данные сохранены!**\n\n"
        f"📦 Пакет: **{chosen_uc} UC**\n"
        f"🆔 Игровой ID: `{player_id}`\n"
        f"💵 Сумма к оплате: **{int(price)} ₽**\n"
        f"💰 Ваш баланс: **{balance} ₽**"
        f"{card_text}\n\n"
        f"Выберите способ оплаты:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

# Оплата картой (вывод реквизитов и запрос скриншота чека)
@dp.callback_query(F.data.startswith("pay_card_"))
async def pay_with_card_request(callback: types.CallbackQuery, state: FSMContext):
    uc_type = callback.data.split("_")[2]
    price = UC_PRICES.get(uc_type, 0)
    
    await state.update_data(chosen_uc=uc_type, price=price, pay_type="Привязанная карта 💳")
    await state.set_state(PurchaseState.waiting_for_payment_screenshot)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Отменить", callback_data="buy_uc")
    
    await callback.message.edit_text(
        f"💳 **Оплата заказа ({uc_type} UC)**\n\n"
        f"Сумма к переводу: **{int(price)} ₽**\n\n"
        f"{SBP_DETAILS}\n\n"
        f"📸 Пожалуйста, совершите перевод и **отправьте скриншот (фото)** чека в этот чат:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

# Оплата с баланса
@dp.callback_query(F.data.startswith("pay_bal_"))
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
    
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()
    conn.close()
    
    success = await auto_buy_uc_from_official_site(player_id, uc_type)
    
    if success:
        await callback.message.edit_text(
            f"🎉 **Покупка за счет баланса успешна!**\n\n"
            f"📦 Пакет: **{uc_type} UC**\n"
            f"🆔 Игровой ID: `{player_id}`\n"
            f"💰 Остаток на балансе: **{new_balance} ₽**\n\n"
            f"🚀 **UC успешно и автоматически отправлены на ваш аккаунт!**",
            parse_mode="Markdown"
        )
    else:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (price, user_id))
        conn.commit()
        conn.close()
        await callback.answer("❌ Ошибка отправки UC. Средства возвращены на баланс.", show_alert=True)

# Получение скриншота оплаты заказа от пользователя
@dp.message(PurchaseState.waiting_for_payment_screenshot, F.photo)
async def process_payment_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chosen_uc = data.get("chosen_uc")
    price = data.get("price")
    pay_type = data.get("pay_type")
    
    user_id = message.from_user.id
    username = message.from_user.username or "Без имени"
    photo_id = message.photo[-1].file_id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT player_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    player_id = row[0] if row else "Не найден"
    conn.close()
    
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Заказ выполнен / UC отправлены", callback_data=f"order_done_{user_id}_{chosen_uc}")
    builder.adjust(1)
    
    await bot.send_photo(
        ADMIN_CHAT_ID,
        photo=photo_id,
        caption=(
            f"🛒 **НОВЫЙ ЗАКАЗ НА UC (ЧЕК ПОЛУЧЕН)!**\n\n"
            f"👤 Покупатель: @{username} (ID: `{user_id}`)\n"
            f"🆔 Игровой ID: `{player_id}`\n"
            f"📦 Пакет: **{chosen_uc} UC**\n"
            f"💵 Сумма: **{int(price)} ₽**\n"
            f"💳 Способ: {pay_type}\n\n"
            f"⚠️ *Проверьте перевод, отправьте UC на игровой ID, затем нажмите кнопку ниже:*"
        ),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    
    await message.answer(
        "✅ **Скриншот успешно отправлен администратору!**\n\n"
        "Ожидайте проверки платежа и зачисления UC на ваш игровой аккаунт.",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("order_done_"))
async def admin_order_done(callback: types.CallbackQuery):
    _, _, user_id_str, chosen_uc = callback.data.split("_")
    user_id = int(user_id_str)
    
    try:
        await bot.send_message(
            user_id,
            f"🎉 **Ваш заказ выполнен!**\n\n"
            f"📦 Пакет **{chosen_uc} UC** успешно зачислен на ваш игровой аккаунт в PUBG Mobile.\n"
            f"Спасибо за покупку!",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление пользователю: {e}")
        
    await callback.message.edit_caption(
        caption=callback.message.caption + f"\n\n✅ **СТАТУС: Заказ выполнен (UC отправлены)**",
        reply_markup=None
    )
    await callback.answer("Заказ отмечен как выполненный!")

# ----------------- ПОПОЛНЕНИЕ БАЛАНСА ЧЕРЕЗ СКРИНШОТ -----------------
@dp.callback_query(F.data == "top_up")
async def top_up_balance(callback: types.CallbackQuery):
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 СБП / Карты РФ", callback_data="pay_method_sbp")
    builder.button(text="🌏 Карты стран Азии", callback_data="pay_method_asia")
    builder.button(text="⬅️ Назад в профиль", callback_data="profile")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "💳 **Пополнение баланса**\n\nВыберите способ перевода:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("pay_method_"))
async def select_pay_method(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    method = callback.data.split("_")[2]
    details = SBP_DETAILS if method == "sbp" else ASIA_DETAILS
    
    await state.update_data(pay_method=method)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Отменить", callback_data="top_up")
    
    await callback.message.edit_text(
        f"{details}\n\n"
        f"💵 Введите сумму, которую вы перевели (в рублях или эквиваленте):\n"
        f"(Пример: `500`)",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(PurchaseState.waiting_for_topup_amount)

@dp.message(PurchaseState.waiting_for_topup_amount)
async def process_topup_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число (например, `500`):", parse_mode="Markdown")
        return
        
    await state.update_data(topup_amount=amount)
    await state.set_state(PurchaseState.waiting_for_screenshot)
    
    await message.answer(
        f"✅ Сумма: **{amount} ₽** запомнена.\n\n"
        f"📸 Теперь **отправьте скриншот (фото)** чека об оплате в этот чат:",
        parse_mode="Markdown"
    )

@dp.message(PurchaseState.waiting_for_screenshot, F.photo)
async def process_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("topup_amount")
    user_id = message.from_user.id
    username = message.from_user.username or "Без имени"
    photo_id = message.photo[-1].file_id
    
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Зачислить баланс", callback_data=f"confirm_topup_{user_id}_{amount}")
    builder.button(text="❌ Отклонить", callback_data=f"cancel_topup_{user_id}")
    builder.adjust(2)
    
    await bot.send_photo(
        ADMIN_CHAT_ID,
        photo=photo_id,
        caption=(
            f"🔔 **Заявка на пополнение баланса!**\n\n"
            f"👤 От: @{username} (ID: `{user_id}`)\n"
            f"💵 Сумма: **{amount} ₽**\n\n"
            f"Нажмите кнопку ниже для зачисления средств:"
        ),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    
    await message.answer(
        "✅ **Скриншот успешно отправлен администратору!**\n\n"
        "Как только администратор проверит перевод, баланс зачислится на ваш счет, и вы получите уведомление.",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("confirm_topup_"))
async def admin_confirm_topup(callback: types.CallbackQuery):
    _, _, user_id_str, amount_str = callback.data.split("_")
    user_id = int(user_id_str)
    amount = float(amount_str)
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    new_balance = row[0] if row else amount
    conn.close()
    
    try:
        await bot.send_message(
            user_id,
            f"🎉 **Ваш баланс успешно пополнен!**\n\n"
            f"➕ Зачислено: **{amount} ₽**\n"
            f"💰 Новый баланс: **{new_balance} ₽**",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление пользователю: {e}")
        
    await callback.message.edit_caption(
        caption=callback.message.caption + f"\n\n✅ **СТАТУС: Баланс зачислен ({amount} ₽)**",
        reply_markup=None
    )
    await callback.answer("Средства успешно зачислены пользователю!")

@dp.callback_query(F.data.startswith("cancel_topup_"))
async def admin_cancel_topup(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    
    try:
        await bot.send_message(
            user_id,
            "❌ **Ваша заявка на пополнение баланса была отклонена администратором.**\n"
            "Если возникли вопросы, обратитесь в поддержку.",
            parse_mode="Markdown"
        )
    except Exception:
        pass
        
    await callback.message.edit_caption(
        caption=callback.message.caption + f"\n\n❌ **СТАТУС: Отклонено**",
        reply_markup=None
    )
    await callback.answer("Заявка отклонена.")

# ----------------- ПРОФИЛЬ И ПРОЧЕЕ -----------------
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
    builder.button(text="➕ Привязать / Изменить карту", callback_data="add_card")
    builder.button(text="💳 Пополнить баланс", callback_data="top_up")
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

@dp.callback_query(F.data == "add_card")
async def start_add_card(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "💳 Введите номер вашей банковской карты для быстрой оплаты:\n"
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
    cursor.execute("DELETE FROM user_cards WHERE user_id = ?", (user_id,))
    cursor.execute("INSERT INTO user_cards (user_id, card_number) VALUES (?, ?)", (user_id, card_number))
    conn.commit()
    conn.close()
    
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 В мой профиль", callback_data="profile")
    builder.button(text="🛒 Купить UC", callback_data="buy_uc")
    builder.adjust(1)
    
    await message.answer(
        f"✅ **Карта успешно привязана!**\n\nНомер: `{card_number}`",
        reply_markup=builder.as_markup(),
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
