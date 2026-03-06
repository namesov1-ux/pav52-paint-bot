"""
Telegram бот для подбора автоэмали
Деплой на Railway — финальная версия с подробным логированием
"""

import asyncio
import logging
import re
import os
import sys
import traceback
import aiogram
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# ПРОВЕРКА ТОКЕНА
# ============================================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("❌ КРИТИЧЕСКАЯ ОШИБКА: BOT_TOKEN не найден в переменных окружения!")
    logger.error("Добавьте BOT_TOKEN во вкладке Variables проекта Railway и перезапустите бота")
    sys.exit(1)

logger.info("✅ BOT_TOKEN успешно загружен")

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ БОТА
# ============================================================================
try:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    logger.info("✅ Бот и диспетчер инициализированы")
except Exception as e:
    logger.error(f"❌ Ошибка при инициализации бота: {e}")
    sys.exit(1)


# ============================================================================
# КЛАССЫ СОСТОЯНИЙ FSM
# ============================================================================
class OrderStates(StatesGroup):
    """Состояния диалога для сбора информации о заказе"""
    know_code = State()
    waiting_name = State()
    waiting_phone = State()
    waiting_marka = State()
    waiting_year = State()
    waiting_kod = State()
    waiting_quantity = State()
    waiting_priority = State()
    waiting_alternative = State()
    waiting_vin = State()
    waiting_final_question = State()


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================
def validate_phone(phone: str) -> bool:
    pattern = r'^((\+7|7|8)+([0-9]){10})$'
    return bool(re.match(pattern, phone.strip()))


def validate_name(name: str) -> bool:
    pattern = r'^[а-яА-ЯёЁa-zA-Z]+ [а-яА-ЯёЁa-zA-Z]+ ?[а-яА-ЯёЁa-zA-Z]+$'
    return bool(re.match(pattern, name.strip()))


def validate_marka(marka: str) -> bool:
    pattern = r'^[a-zA-Zа-яА-ЯёЁ]+$'
    return bool(re.match(pattern, marka.strip()))


def validate_year(year: str) -> bool:
    pattern = r'^[1-9]+[0-9]*$'
    return bool(re.match(pattern, year.strip()))


def validate_kod(kod: str) -> bool:
    pattern = r'^[a-zA-Z0-9]+$'
    return bool(re.match(pattern, kod.strip()))


def validate_quantity(quantity: str) -> bool:
    pattern = r'^(50|[1-9][0-9]*[05]0)$'
    return bool(re.match(pattern, quantity.strip()))


def validate_vin(vin: str) -> bool:
    pattern = r'^[A-HJ-NPR-Z0-9]{17}$'
    return bool(re.match(pattern, vin.strip().upper()))


# ============================================================================
# СОЗДАНИЕ КЛАВИАТУР
# ============================================================================
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚗 Заказать автоэмаль")],
            [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="📞 Контакты")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_yes_no_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ ДА", callback_data="yes")],
            [InlineKeyboardButton(text="❌ НЕТ", callback_data="no")]
        ]
    )
    return keyboard


def get_priority_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ КАЧЕСТВО", callback_data="quality")],
            [InlineKeyboardButton(text="💰 ЦЕНА", callback_data="price")]
        ]
    )
    return keyboard


def get_final_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ ДА, есть вопрос", callback_data="yes_question")],
            [InlineKeyboardButton(text="❌ НЕТ, все понятно", callback_data="no_question")]
        ]
    )
    return keyboard


def get_alternative_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Найду по марке", callback_data="find_by_marka")],
            [InlineKeyboardButton(text="📋 Введу VIN", callback_data="enter_vin")],
            [InlineKeyboardButton(text="🏢 Приеду в магазин", callback_data="visit_shop")]
        ]
    )
    return keyboard


# ============================================================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    logger.info(f"Пользователь {message.from_user.id} запустил бота")
    
    await message.answer(
        "Здравствуйте, Вам необходима автоэмаль для покраски Вашего автомобиля.\n"
        "Вы знаете код краски?",
        reply_markup=get_yes_no_keyboard()
    )
    await state.set_state(OrderStates.know_code)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "❓ <b>Помощь по боту</b>\n\n"
        "Этот бот поможет вам подобрать автоэмаль для вашего автомобиля.\n"
        "Команды:\n"
        "/start - начать заново\n"
        "/help - эта справка\n\n"
        "Если у вас возникли вопросы, вы можете позвонить нам или приехать в магазин.",
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("contacts"))
async def cmd_contacts(message: types.Message):
    await message.answer(
        "📞 <b>Наши контакты</b>\n\n"
        "🏠 Адрес: г. Павлово, ул. Карла Маркса, д.3\n"
        "🕒 Часы работы:\n"
        "   Пн-Пт: 9:00 - 18:00\n"
        "   Сб-Вс: 9:00 - 14:00\n\n"
        "Приносите образец краски для точного подбора!"
    )


# ============================================================================
# ОБРАБОТЧИКИ CALLBACK
# ============================================================================
@dp.callback_query(lambda c: c.data in ["yes", "no"])
async def process_know_code(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    if callback.data == "yes":
        await callback.message.edit_text(
            "Отлично! Давайте познакомимся.\n"
            "Укажите пожалуйста Вашу фамилию и имя (например: Иванов Алексей)"
        )
        await state.set_state(OrderStates.waiting_name)
    else:
        await callback.message.edit_text(
            "Можно по марке машины в интернете найти, где находится номер краски на автомобиле.\n"
            "Вы нашли код краски?",
            reply_markup=get_yes_no_keyboard()
        )
        await state.set_state(OrderStates.waiting_alternative)


@dp.callback_query(lambda c: c.data in ["yes_question", "no_question"])
async def process_final_question(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    if callback.data == "yes_question":
        await callback.message.edit_text("Задайте Ваш вопрос")
        await state.set_state(OrderStates.waiting_final_question)
    else:
        await callback.message.edit_text(
            "Мы оперативно свяжемся с вами, чтобы ответить на все вопросы и подтвердить заказ.\n"
            "Перед изготовлением потребуется предоплата из расчета 200р за каждые заказанные 100гр краски "
            "(если изготовление при Вас, предоплата не требуется)"
        )
        await state.clear()


@dp.callback_query(lambda c: c.data in ["quality", "price"])
async def process_priority(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    data = await state.get_data()
    
    if callback.data == "quality":
        data['priority'] = 'качество'
        await callback.message.edit_text(
            "Хорошо, мы будем ориентироваться на качество.\n"
            "Вы можете передать нам образец (если не известен код краски) по адресу:\n"
            "г. Павлово, ул. Карла Маркса, д.3\n\n"
            "Режим работы:\n"
            "Пн-Пт: 9:00 - 18:00\n"
            "Сб-Вс: 9:00 - 14:00\n\n"
            "У вас остались вопросы?",
            reply_markup=get_final_keyboard()
        )
    else:
        data['priority'] = 'цена'
        await callback.message.edit_text(
            "Хорошо, мы будем ориентироваться на цену.\n"
            "Вы можете передать нам образец (если не известен код краски) по адресу:\n"
            "г. Павлово, ул. Карла Маркса, д.3\n\n"
            "Режим работы:\n"
            "Пн-Пт: 9:00 - 18:00\n"
            "Сб-Вс: 9:00 - 14:00\n\n"
            "У вас остались вопросы?",
            reply_markup=get_final_keyboard()
        )
    
    await state.set_data(data)
    await state.set_state(OrderStates.waiting_final_question)


@dp.callback_query(lambda c: c.data in ["find_by_marka", "enter_vin", "visit_shop"])
async def process_alternative(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    if callback.data == "find_by_marka":
        await callback.message.edit_text(
            "Давайте сначала познакомимся.\n"
            "Укажите пожалуйста Вашу фамилию и имя (например: Иванов Алексей)"
        )
        await state.set_state(OrderStates.waiting_name)
    elif callback.data == "enter_vin":
        await callback.message.edit_text(
            "напишите VIN код 17 символов, Цифры 0-9 и буквы A-Z (латиница), ЗА ИСКЛЮЧЕНИЕМ I, O, Q"
        )
        await state.set_state(OrderStates.waiting_vin)
    else:
        await callback.message.edit_text(
            "Хорошо, мы будем ждать вас!\n"
            "Адрес: г. Павлово, ул. Карла Маркса, д.3\n\n"
            "Режим работы:\n"
            "Пн-Пт: 9:00 - 18:00\n"
            "Сб-Вс: 9:00 - 14:00"
        )
        await state.clear()


# ============================================================================
# ОБРАБОТЧИКИ ТЕКСТОВЫХ СООБЩЕНИЙ
# ============================================================================
@dp.message(OrderStates.waiting_name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    
    if validate_name(name):
        await state.update_data(user_name=name)
        await message.answer(
            f"Спасибо, {name}. Ваш телефон?",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
                resize_keyboard=True
            )
        )
        await state.set_state(OrderStates.waiting_phone)
    else:
        await message.answer(
            "Пожалуйста, укажите фамилию и имя в правильном формате (например: Иванов Алексей)"
        )


@dp.message(OrderStates.waiting_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    
    if validate_phone(phone):
        await state.update_data(phone=phone)
        await message.answer(
            "укажите марку машины (латиница или кириллица, например: ЛАДА или GAC)"
        )
        await state.set_state(OrderStates.waiting_marka)
    else:
        await message.answer(
            "Пожалуйста, укажите российский телефон в формате: 8XXXXXXXXXX или +7XXXXXXXXXX"
        )


@dp.message(OrderStates.waiting_phone, lambda message: message.contact)
async def process_contact(message: types.Message, state: FSMContext):
    contact = message.contact
    phone = contact.phone_number
    
    await state.update_data(phone=phone, user_name=contact.first_name)
    await message.answer(
        f"Спасибо! Теперь укажите марку машины (например: ЛАДА или GAC)"
    )
    await state.set_state(OrderStates.waiting_marka)


@dp.message(OrderStates.waiting_marka)
async def process_marka(message: types.Message, state: FSMContext):
    marka = message.text.strip()
    
    if validate_marka(marka):
        await state.update_data(user_marka_mashiny=marka)
        await message.answer("год выпуска?")
        await state.set_state(OrderStates.waiting_year)
    else:
        await message.answer("Пожалуйста, укажите марку машины (только буквы, например: ЛАДА)")


@dp.message(OrderStates.waiting_year)
async def process_year(message: types.Message, state: FSMContext):
    year = message.text.strip()
    
    if validate_year(year):
        await state.update_data(user_god_mashiny=year)
        await message.answer("код краски?")
        await state.set_state(OrderStates.waiting_kod)
    else:
        await message.answer("Пожалуйста, укажите год выпуска цифрами (например: 2020)")


@dp.message(OrderStates.waiting_kod)
async def process_kod(message: types.Message, state: FSMContext):
    kod = message.text.strip()
    
    if validate_kod(kod):
        await state.update_data(user_kod_kraski=kod)
        await message.answer(
            "Нужное количество краски в граммах, кратно 50 и не менее 50 гр (например: 300 или 150)"
        )
        await state.set_state(OrderStates.waiting_quantity)
    else:
        await message.answer(
            "Пожалуйста, введите код краски (только цифры и буквы латиницей, например: 123ABC)"
        )


@dp.message(OrderStates.waiting_quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    quantity = message.text.strip()
    
    if validate_quantity(quantity):
        await state.update_data(user_kraska_gramm=quantity)
        await message.answer(
            "У нас имеется две стойки для подбора краски: HYMAX (500р/100гр) и CORSO (300р/100гр).\n"
            "На какой стойке получится лучший вариант, мы на данном этапе не сможем сказать.\n"
            "Уточните: приоритет будет по цене или по качеству?",
            reply_markup=get_priority_keyboard()
        )
        await state.set_state(OrderStates.waiting_priority)
    else:
        await message.answer(
            "Пожалуйста, укажите количество краски, кратное 50 и не менее 50 (например: 100, 150, 200)"
        )


@dp.message(OrderStates.waiting_vin)
async def process_vin(message: types.Message, state: FSMContext):
    vin = message.text.strip().upper()
    
    if validate_vin(vin):
        await state.update_data(user_vin=vin)
        await message.answer("укажите марку машины?")
        await state.set_state(OrderStates.waiting_marka)
    else:
        await message.answer(
            "Пожалуйста, введите корректный VIN-код:\n"
            "17 символов, цифры 0-9 и буквы A-Z (кроме I, O, Q)"
        )


@dp.message(OrderStates.waiting_final_question)
async def process_final_question(message: types.Message, state: FSMContext):
    await state.update_data(user_questions=message.text)
    
    data = await state.get_data()
    user_name = data.get('user_name', '')
    
    await message.answer(
        f"Спасибо за вопрос, {user_name}! Мы ответим вам в ближайшее время.\n\n"
        "Мы оперативно свяжемся с вами, чтобы ответить на все вопросы и подтвердить заказ.\n"
        "Перед изготовлением потребуется предоплата из расчета 200р за каждые заказанные 100гр краски "
        "(если изготовление при Вас, предоплата не требуется)"
    )
    await state.clear()


@dp.message(OrderStates.waiting_alternative)
async def process_alternative_response(message: types.Message, state: FSMContext):
    text = message.text.lower()
    
    if text in ['да', 'yes', 'yeah', 'ага', 'угу']:
        await message.answer(
            "Давайте познакомимся.\n"
            "Укажите пожалуйста Вашу фамилию и имя (например: Иванов Алексей)"
        )
        await state.set_state(OrderStates.waiting_name)
    elif text in ['нет', 'no', 'not', 'не нашел', 'не знаю']:
        await message.answer(
            "Тогда вы можете:\n"
            "1. Принести лючок бензобака или другую деталь для определения цвета\n"
            "2. Ввести VIN-код автомобиля\n"
            "3. Приехать в магазин",
            reply_markup=get_alternative_keyboard()
        )
        await state.set_state(OrderStates.waiting_alternative)
    else:
        await message.answer(
            "Я вас не понял. Вы нашли код краски?",
            reply_markup=get_yes_no_keyboard()
        )


@dp.message()
async def handle_unknown(message: types.Message):
    await message.answer(
        "Я вас не понял. Пожалуйста, используйте команду /start для начала работы.",
        reply_markup=get_main_keyboard()
    )


# ============================================================================
# ЗАПУСК БОТА
# ============================================================================
async def on_startup():
    """Действия при запуске бота"""
    logger.info("=" * 50)
    logger.info("🚀 Бот успешно запущен на Railway!")
    try:
        logger.info(f"🤖 Версия aiogram: {aiogram.__version__}")
    except AttributeError:
        logger.info("🤖 Версия aiogram: неизвестна (библиотека загружена)")
    
 # Удаляем вебхук, если он есть
    try:
        logger.info("🔄 Проверка вебхука...")
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            logger.info(f"⚠️ Обнаружен вебхук: {webhook_info.url}")
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Вебхук удален")
        else:
            logger.info("✅ Вебхуков нет")
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при удалении вебхука: {e}")

    # Проверка соединения с Telegram API
    try:
        me = await bot.get_me()
        logger.info(f"✅ Бот авторизован как: @{me.username} (ID: {me.id})")
        logger.info(f"📝 Имя бота: {me.full_name}")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к Telegram API: {e}")
    
    logger.info("=" * 50)


async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("👋 Бот остановлен")


async def main():
    """Главная функция запуска бота"""
    try:
        await on_startup()
        
        # Небольшая задержка перед стартом polling
        await asyncio.sleep(1)
        
        await dp.start_polling(
            bot,
            skip_updates=True,
            handle_signals=False,
            close_bot_session=True
        )
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в main: {e}")
        raise
    finally:
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Необработанная ошибка: {e}")
        sys.exit(1)