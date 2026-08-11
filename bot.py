import logging
import sqlite3
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== НАСТРОЙКИ ====================
TOKEN = "8892100518:AAFJ6-7pM2hwP9LEJkAPwOloaqiaku9Dy7w"
ADMIN_CHAT_ID = 1231002682

API_URL = "https://api.your-uc-supplier.com/v1/buy"
API_KEY = "YOUR_SUPPLIER_API_KEY"

SBP_DETAILS = "💳 **Сбер / Т-Банк (СБП):**\n`+7 (963) 258 78 84`\n(Получатель: Нусратулло Носиров.)"
ASIA_DETAILS = "🌏 **Карты стран Азии:**\nНомер карты: `4400 0555 3145 2345`\n(Душанбе Сити)"
ADMIN_USERNAME = "@arrhiv1"  # Установлен измененный юзернейм
SITE_URL = "https://t.me/ALEXUCSHOP"
# ===================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

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
    conn.commit()
    conn.close()

db_start()

class PurchaseState(StatesGroup):
    waiting_for_player_id = State()
    waiting_for_topup_amount = State()
    waiting_for_screenshot = State()
    waiting_for_payment_screenshot = State()

UC_PRICES = {
    "60": 80.0, "120": 159.0,
    "325": 402.0, "385": 478.0,
    "660": 796.0, "720": 878.0,
    "985": 1198.0, "1320": 1592.0,
    "1800": 2014.0, "2125": 2486.0,
    "2460": 2870.0, "3850": 4022.0,
    "4510": 4790.0, "5650": 6134.0,
    "8100": 8054.0, "9900": 10070.0,
    "11950": 12086.0, "16200": 16109.0,
    "24300": 24163.0, "32400": 32218.0,
    "40500": 40272.0, "48600": 48326.0,
    "81000": 80544.0
}

async def auto_buy_uc_from_official_site(player_id: str, uc_type: str) -> bool:
    payload = {"api_key": API_KEY, "player_id": player_id, "package": uc_type}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, timeout=20) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return True
                return False
    except Exception as e:
        logging.error(f"API Error: {e}")
        return False

def get_main_reply_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🛒 Купить UC / VIP / ПП")
    kb.button(text="🔥 Купить популярность")
    kb.button(text="🎮 Пополнить Steam")
    kb.button(text="🌐 Все игры")
    kb.button(text="💬 Помощь")
    kb.button(text="⭐ Отзывы")
    kb.adjust(1, 1, 1, 1, 2)
    return kb.as_markup(resize_keyboard=True)

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
    
    welcome_text = (
        "Добро пожаловать 🔥\n\n"
        "Это автоматический бот пополнения, который мгновенно доставит UC на ваш аккаунт 24/7.\n"
        "Ваши покупки полностью защищены, также вы можете запросить чек на любое пополнение."
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_reply_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "🛒 Купить UC / VIP / ПП")
async def uc_packages_menu(message: types.Message):
    builder = InlineKeyboardBuilder()
    
    items = list(UC_PRICES.items())
    for i in range(0, len(items) - 1, 2):
        row = [
            types.InlineKeyboardButton(text=f"🪙 {items[i][0]} - {int(items[i][1])}₽", callback_data=f"uc_{items[i][0]}"),
            types.InlineKeyboardButton(text=f"🪙 {items[i+1][0]} - {int(items[i+1][1])}₽", callback_data=f"uc_{items[i+1][0]}")
        ]
        builder.row(*row)
        
    if len(items) % 2 != 0:
        last_item = items[-1]
        builder.row(types.InlineKeyboardButton(text=f"🪙 {last_item[0]} - {int(last_item[1])}₽", callback_data=f"uc_{last_item[0]}"))
        
    builder.row(
        types.InlineKeyboardButton(text="🍗 ПОПУЛЯРНОСТЬ", callback_data="menu_popularity"),
        types.InlineKeyboardButton(text="💎 VIP", callback_data="menu_vip")
    )
    builder.row(types.InlineKeyboardButton(text="Перейти на сайт ↗", url=SITE_URL))
    
    text = (
        "✅ **Пополнение происходит автоматически в течение 1-5 минут.**\n\n"
        "⚠️ *Пополнение доступно на все регионы, кроме Китая, Кореи, Тайваня и Вьетнама.*"
    )
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.message(F.text == "🔥 Купить популярность")
async def popular_menu(message: types.Message):
    await message.answer("🔥 Раздел покупки популярности в разработке.", reply_markup=get_main_reply_keyboard())

@dp.callback_query(F.data == "menu_popularity")
async def inline_popularity(callback: types.CallbackQuery):
    await callback.answer("Раздел популярности")
    await callback.message.answer("🔥 Раздел покупки популярности в разработке.")

@dp.callback_query(F.data == "menu_vip")
async def inline_vip(callback: types.CallbackQuery):
    await callback.answer("Раздел VIP")
    await callback.message.answer("💎 Раздел VIP пополнения в разработке.")

@dp.message(F.text == "🎮 Пополнить Steam")
async def steam_menu(message: types.Message):
    await message.answer("🎮 Раздел пополнения Steam в разработке.", reply_markup=get_main_reply_keyboard())

@dp.message(F.text == "🌐 Все игры")
async def all_games_menu(message: types.Message):
    await message.answer("🌐 Список всех доступных игр:", reply_markup=get_main_reply_keyboard())

@dp.message(F.text == "💬 Помощь")
async def help_menu(message: types.Message):
    help_text = (
        "1) Зачисление может идти до 3 минут, если вы приобрели 720UC, то сначала вам придет 660UC, а потом 60 UC, также с другими паками, например: 180UC = 60 UC + 60 UC + 60 UC\n\n"
        "На аккаунт приходят все uc\n"
        "В «подарок за покупку» засчитает часть\n"
        "С 325 юс засчитывается 300\n"
        "С 660 юс засчитывается 600\n"
        "С 1800 юс засчитывается 1500\n"
        "С 3850 юс засчитывается 3000\n"
        "С 8100 юс засчитывается 6000\n\n"
        "2) Мы платим комиссию за использование платежной системы, поэтому цены могут быть чуть выше\n\n"
        f"3) Более 100.000 заказов были сделаны через бота и 100% людей получили свои UC, если у вас что-то произошло, просто напишите {ADMIN_USERNAME}"
    )
    await message.answer(help_text, reply_markup=get_main_reply_keyboard())

@dp.message(F.text == "⭐ Отзывы")
async def reviews_menu(message: types.Message):
    await message.answer("⭐ Ссылка на канал с отзывами наших клиентов: (t.me/ALEXUCSHOP)", reply_markup=get_main_reply_keyboard())

@dp.callback_query(F.data.startswith("uc_"))
async def select_uc(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    uc_type = callback.data.split("_")[1]
    await state.update_data(chosen_uc=uc_type)
    
    await callback.message.answer(
        "🆔 Пожалуйста, введите ваш **Player ID** в PUBG Mobile:\n(Пример: `5123456789`)",
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
    conn.commit()
    
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    balance = row[0] if row else 0.0
    conn.close()
    
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💳 Оплатить переводом ({int(price)} ₽)", callback_data=f"pay_card_{chosen_uc}")
    if balance >= price:
        builder.button(text=f"💰 Оплатить с баланса ({int(price)} ₽)", callback_data=f"pay_bal_{chosen_uc}")
    builder.button(text="💳 Пополнить баланс", callback_data="top_up")
    builder.adjust(1)

    await message.answer(
        f"✅ **Данные сохранены!**\n\n📦 Пакет: **{chosen_uc} UC**\n🆔 ID: `{player_id}`\n💰 Баланс: **{balance} ₽**\n\nВыберите способ оплаты:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("pay_bal_"))
async def pay_with_balance(callback: types.CallbackQuery):
    uc_type = callback.data.split("_")[2]
    price = UC_PRICES.get(uc_type, 0)
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, player_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row or row[0] < price or not row[1]:
        await callback.answer("❌ Недостаточно средств или не указан Player ID!", show_alert=True)
        conn.close()
        return
        
    balance, player_id = row[0], row[1]
    new_balance = balance - price
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text("⏳ **Обработка заказа...** Отправка UC на ваш аккаунт.", parse_mode="Markdown")
    
    success = await auto_buy_uc_from_official_site(player_id, uc_type)
    
    if success:
        await callback.message.edit_text(
            f"🎉 **Покупка успешна!**\n\n📦 Пакет: **{uc_type} UC**\n🆔 ID: `{player_id}`\n💰 Баланс: **{new_balance} ₽**\n\n🚀 UC успешно отправлены в игру!",
            parse_mode="Markdown"
        )
    else:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (price, user_id))
        conn.commit()
        conn.close()
        await callback.message.edit_text("❌ **Ошибка при отправке UC.** Средства возвращены на баланс.", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("pay_card_"))
async def pay_with_card_request(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    uc_type = callback.data.split("_")[2]
    price = UC_PRICES.get(uc_type, 0)
    
    await state.update_data(chosen_uc=uc_type, price=price)
    await state.set_state(PurchaseState.waiting_for_payment_screenshot)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="buy_uc_back")
    
    await callback.message.edit_text(
        f"💳 **Оплата заказа ({uc_type} UC)**\n\nСумма: **{int(price)} ₽**\n\n{SBP_DETAILS}\n\n📸 **Отправьте скриншот чека** в этот чат:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.message(PurchaseState.waiting_for_payment_screenshot, F.photo)
async def process_payment_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chosen_uc = data.get("chosen_uc")
    price = data.get("price")
    user_id = message.from_user.id
    username = message.from_user.username or "Без имени"
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT player_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    player_id = row[0] if row else "Не найден"
    conn.close()
    
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить и отправить UC", callback_data=f"autobuy_{user_id}_{chosen_uc}")
    builder.adjust(1)
    
    await bot.send_photo(
        ADMIN_CHAT_ID,
        photo=message.photo[-1].file_id,
        caption=f"🛒 **НОВЫЙ ЗАКАЗ НА UC!**\n\n👤 От: @{username} (`{user_id}`)\n🆔 Игр. ID: `{player_id}`\n📦 Пакет: {chosen_uc} UC\n💵 Сумма: {int(price)} ₽",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    
    await message.answer("✅ **Скриншот отправлен администратору!** После проверки UC автоматически отправятся в игру.", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("autobuy_"))
async def admin_trigger_autobuy(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[1])
    chosen_uc = parts[2]
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT player_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row[0]:
        await callback.answer("❌ У пользователя не найден Player ID!", show_alert=True)
        return
        
    player_id = row[0]
    await callback.answer("⏳ Отправка UC...", show_alert=True)
    
    success = await auto_buy_uc_from_official_site(player_id, chosen_uc)
    
    if success:
        try:
            await bot.send_message(user_id, f"🎉 **Оплата подтверждена!**\n\n📦 Пакет **{chosen_uc} UC** успешно отправлен на ваш ID (`{player_id}`). Приятной игры!", parse_mode="Markdown")
        except Exception:
            pass
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ **СТАТУС: UC отправлены автоматически!**", reply_markup=None)
    else:
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ **СТАТУС: Ошибка API поставщика!**", reply_markup=None)

@dp.callback_query(F.data == "top_up")
async def top_up_balance(callback: types.CallbackQuery):
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 СБП / Карты РФ", callback_data="method_sbp")
    builder.button(text="🌏 Карты Азии", callback_data="method_asia")
    builder.button(text="⬅️ Назад", callback_data="profile")
    builder.adjust(1)
    await callback.message.edit_text("💳 **Пополнение баланса**\n\nВыберите способ перевода:", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("method_"))
async def method_select(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    method = callback.data.split("_")[1]
    details = SBP_DETAILS if method == "sbp" else ASIA_DETAILS
    await state.update_data(method=method)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Отмена", callback_data="top_up")
    await callback.message.edit_text(f"{details}\n\n💵 **Введите сумму пополнения в рублях:**", reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.set_state(PurchaseState.waiting_for_topup_amount)

@dp.message(PurchaseState.waiting_for_topup_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректное число:", parse_mode="Markdown")
        return
        
    await state.update_data(topup_amount=amount)
    await state.set_state(PurchaseState.waiting_for_screenshot)
    await message.answer(f"✅ Сумма: **{amount} ₽**\n\n📸 Отправьте скриншот чека:", parse_mode="Markdown")

@dp.message(PurchaseState.waiting_for_screenshot, F.photo)
async def process_topup_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("topup_amount")
    user_id = message.from_user.id
    username = message.from_user.username or "Без имени"
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Зачислить баланс", callback_data=f"conf_{user_id}_{amount}")
    
    await bot.send_photo(
        ADMIN_CHAT_ID, photo=message.photo[-1].file_id,
        caption=f"🔔 **Заявка на пополнение!**\n\n👤 От: @{username} (`{user_id}`)\n💵 Сумма: **{amount} ₽**",
        reply_markup=builder.as_markup(), parse_mode="Markdown"
    )
    await message.answer("✅ Чек отправлен администратору!", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("conf_"))
async def confirm_topup(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id, amount = int(parts[1]), float(parts[2])
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    new_balance = cursor.fetchone()[0]
    conn.close()
    
    try:
        await bot.send_message(user_id, f"🎉 **Баланс пополнен!**\n➕ Зачислено: **{amount} ₽**\n💰 Баланс: **{new_balance} ₽**", parse_mode="Markdown")
    except Exception:
        pass
    await callback.message.edit_caption(caption=callback.message.caption + f"\n\n✅ **Зачислено ({amount} ₽)**", reply_markup=None)
    await callback.answer("Успешно!")

@dp.callback_query(F.data == "profile")
async def profile(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT player_id, balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    player_id = row[0] if row and row[0] else "Не указан ❌"
    balance = row[1] if row and row[1] is not None else 0.0
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Пополнить баланс", callback_data="top_up")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"👤 **Ваш профиль:**\n\n🆔 Telegram ID: `{user_id}`\n🎮 PUBG Player ID: `{player_id}`\n💰 Баланс: **{balance} ₽**",
        reply_markup=builder.as_markup(), parse_mode="Markdown"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
