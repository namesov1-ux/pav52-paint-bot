"""
Telegram бот для подбора автоэмали
Деплой на Railway — финальная версия с подробным логированием
"""

import asyncio
import logging
import re
import os
import sys
import traceback  # Добавлено для детальных ошибок
import aiogram
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

# ============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ (РАСШИРЕННАЯ)
# ============================================================================
# Создаем обработчики для вывода в stdout и stderr
stdout_handler = logging.StreamHandler(sys.stdout)
stderr_handler = logging.StreamHandler(sys.stderr)

# Настраиваем формат логирования
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
stdout_handler.setFormatter(logging.Formatter(log_format))
stderr_handler.setFormatter(logging.Formatter(log_format))

# Настраиваем корневой логгер
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(stdout_handler)
root_logger.addHandler(stderr_handler)

# Создаем логгер для нашего приложения
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Включаем DEBUG уровень для детального логирования

# Логируем начало работы
logger.info("=" * 60)
logger.info("🚀 ЗАПУСК БОТА НА RAILWAY")
logger.info("=" * 60)
logger.info(f"🐍 Python версия: {sys.version}")
logger.info(f"📦 Платформа: {sys.platform}")
logger.info(f"📂 Текущая директория: {os.getcwd()}")
logger.info(f"📋 Файлы в директории: {os.listdir('.')}")

# ============================================================================
# ПРОВЕРКА ТОКЕНА С ПОДРОБНЫМ ЛОГИРОВАНИЕМ
# ============================================================================
logger.info("🔍 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
logger.info(f"📊 Все доступные переменные: {list(os.environ.keys())}")

# Проверяем наличие BOT_TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN")
logger.info(f"🔑 BOT_TOKEN {'НАЙДЕН' if BOT_TOKEN else 'НЕ НАЙДЕН'}")

if BOT_TOKEN:
    logger.info(f"✅ Длина токена: {len(BOT_TOKEN)} символов")
    logger.info(f"✅ Первые 10 символов: {BOT_TOKEN[:10]}...")
else:
    logger.error("❌ КРИТИЧЕСКАЯ ОШИБКА: BOT_TOKEN не найден в переменных окружения!")
    logger.error("📝 Инструкция: Добавьте BOT_TOKEN во вкладке Variables проекта Railway")
    logger.error("🔄 После добавления перезапустите бота кнопкой Redeploy")
    sys.exit(1)

logger.info("✅ BOT_TOKEN успешно загружен и проверен")

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ БОТА С ЛОГИРОВАНИЕМ
# ============================================================================
logger.info("🔧 ИНИЦИАЛИЗАЦИЯ КОМПОНЕНТОВ БОТА")

try:
    logger.info("🔄 Создание экземпляра Bot...")
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    logger.info("✅ Bot создан успешно")
    
    logger.info("🔄 Создание MemoryStorage...")
    storage = MemoryStorage()
    logger.info("✅ MemoryStorage создан успешно")
    
    logger.info("🔄 Создание Dispatcher...")
    dp = Dispatcher(storage=storage)
    logger.info("✅ Dispatcher создан успешно")
    
    logger.info("✅ Все компоненты бота инициализированы")
    
except Exception as e:
    logger.error(f"❌ Ошибка при инициализации бота: {e}")
    logger.error(f"📝 Traceback: {traceback.format_exc()}")
    sys.exit(1)

# ============================================================================
# КЛАССЫ СОСТОЯНИЙ FSM (без изменений)
# ============================================================================
class OrderStates(StatesGroup):
    """Состояния диалога для сбора информации о заказе"""
    # Начальные вопросы
    know_code = State()           # Знает ли код краски?
    
    # Сбор персональных данных
    waiting_name = State()         # Ожидание имени
    waiting_phone = State()        # Ожидание телефона
    
    # Ветка "Знает код краски"
    waiting_marka = State()        # Ожидание марки машины
    waiting_year = State()         # Ожидание года выпуска
    waiting_kod = State()          # Ожидание кода краски
    waiting_quantity = State()     # Ожидание количества краски
    waiting_priority = State()     # Ожидание выбора приоритета (цена/качество)
    
    # Ветка "Не знает код краски" - альтернативный путь
    waiting_alternative = State()  # Ожидание ответа после подсказки
    
    # Ветка VIN (если пользователь хочет ввести VIN)
    waiting_vin = State()          # Ожидание VIN-кода
    
    # Финальные вопросы
    waiting_final_question = State()  # Ожидание ответа "остались ли вопросы"


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (без изменений)
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
# СОЗДАНИЕ КЛАВИАТУР (без изменений)
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
# ОБРАБОТЧИКИ КОМАНД С ЛОГИРОВАНИЕМ
# ============================================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    
    logger.info(f"👤 Пользователь {user_id} (@{username}) запустил команду /start")
    
    await state.clear()
    logger.info(f"🧹 Состояние очищено для пользователя {user_id}")
    
    await message.answer(
        "Здравствуйте, Вам необходима автоэмаль для покраски Вашего автомобиля.\n"
        "Вы знаете код краски?",
        reply_markup=get_yes_no_keyboard()
    )
    logger.info(f"📤 Отправлен вопрос о знании кода краски пользователю {user_id}")
    
    await state.set_state(OrderStates.know_code)
    logger.info(f"🔄 Установлено состояние know_code для пользователя {user_id}")


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Команда помощи"""
    user_id = message.from_user.id
    logger.info(f"👤 Пользователь {user_id} запросил помощь")
    
    await message.answer(
        "❓ <b>Помощь по боту</b>\n\n"
        "Этот бот поможет вам подобрать автоэмаль для вашего автомобиля.\n"
        "Команды:\n"
        "/start - начать заново\n"
        "/help - эта справка\n\n"
        "Если у вас возникли вопросы, вы можете позвонить нам или приехать в магазин.",
        reply_markup=get_main_keyboard()
    )
    logger.info(f"📤 Отправлена справка пользователю {user_id}")


@dp.message(Command("contacts"))
async def cmd_contacts(message: types.Message):
    """Контакты магазина"""
    user_id = message.from_user.id
    logger.info(f"👤 Пользователь {user_id} запросил контакты")
    
    await message.answer(
        "📞 <b>Наши контакты</b>\n\n"
        "🏠 Адрес: г. Павлово, ул. Карла Маркса, д.3\n"
        "🕒 Часы работы:\n"
        "   Пн-Пт: 9:00 - 18:00\n"
        "   Сб-Вс: 9:00 - 14:00\n\n"
        "Приносите образец краски для точного подбора!"
    )
    logger.info(f"📤 Отправлены контакты пользователю {user_id}")


# ============================================================================
# ОБРАБОТЧИКИ CALLBACK С ЛОГИРОВАНИЕМ
# ============================================================================
@dp.callback_query(lambda c: c.data in ["yes", "no"])
async def process_know_code(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа на вопрос "Знаете код краски?" """
    user_id = callback.from_user.id
    answer = callback.data
    
    logger.info(f"👤 Пользователь {user_id} ответил на вопрос о коде краски: '{answer}'")
    await callback.answer()
    
    if callback.data == "yes":
        logger.info(f"✅ Пользователь {user_id} знает код краски")
        await callback.message.edit_text(
            "Отлично! Давайте познакомимся.\n"
            "Укажите пожалуйста Вашу фамилию и имя (например: Иванов Алексей)"
        )
        logger.info(f"📤 Запрошено имя у пользователя {user_id}")
        await state.set_state(OrderStates.waiting_name)
    
    else:  # no
        logger.info(f"❌ Пользователь {user_id} не знает код краски")
        await callback.message.edit_text(
            "Можно по марке машины в интернете найти, где находится номер краски на автомобиле.\n"
            "Вы нашли код краски?",
            reply_markup=get_yes_no_keyboard()
        )
        logger.info(f"📤 Отправлена подсказка пользователю {user_id}")
        await state.set_state(OrderStates.waiting_alternative)


@dp.callback_query(lambda c: c.data in ["yes_question", "no_question"])
async def process_final_question(callback: types.CallbackQuery, state: FSMContext):
    """Обработка финального вопроса "У вас остались вопросы?" """
    user_id = callback.from_user.id
    answer = callback.data
    
    logger.info(f"👤 Пользователь {user_id} ответил на финальный вопрос: '{answer}'")
    await callback.answer()
    
    if callback.data == "yes_question":
        logger.info(f"❓ Пользователь {user_id} хочет задать вопрос")
        await callback.message.edit_text("Задайте Ваш вопрос")
        logger.info(f"📤 Запрошен вопрос у пользователя {user_id}")
        await state.set_state(OrderStates.waiting_final_question)
    
    else:  # no_question
        logger.info(f"✅ Пользователь {user_id} не имеет вопросов")
        await callback.message.edit_text(
            "Мы оперативно свяжемся с вами, чтобы ответить на все вопросы и подтвердить заказ.\n"
            "Перед изготовлением потребуется предоплата из расчета 200р за каждые заказанные 100гр краски "
            "(если изготовление при Вас, предоплата не требуется)"
        )
        logger.info(f"📤 Отправлено завершающее сообщение пользователю {user_id}")
        await state.clear()
        logger.info(f"🧹 Состояние очищено для пользователя {user_id}")


@dp.callback_query(lambda c: c.data in ["quality", "price"])
async def process_priority(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора приоритета (цена/качество)"""
    user_id = callback.from_user.id
    priority = "качество" if callback.data == "quality" else "цена"
    
    logger.info(f"👤 Пользователь {user_id} выбрал приоритет: '{priority}'")
    await callback.answer()
    
    data = await state.get_data()
    logger.info(f"📦 Текущие данные пользователя {user_id}: {data}")
    
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
        logger.info(f"📤 Отправлен ответ с приоритетом 'качество' пользователю {user_id}")
    
    else:  # price
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
        logger.info(f"📤 Отправлен ответ с приоритетом 'цена' пользователю {user_id}")
    
    await state.set_data(data)
    logger.info(f"💾 Обновленные данные пользователя {user_id}: {data}")
    await state.set_state(OrderStates.waiting_final_question)


@dp.callback_query(lambda c: c.data in ["find_by_marka", "enter_vin", "visit_shop"])
async def process_alternative(callback: types.CallbackQuery, state: FSMContext):
    """Обработка альтернативных вариантов, когда код краски не известен"""
    user_id = callback.from_user.id
    choice = callback.data
    
    logger.info(f"👤 Пользователь {user_id} выбрал альтернативный путь: '{choice}'")
    await callback.answer()
    
    if callback.data == "find_by_marka":
        logger.info(f"🔍 Пользователь {user_id} выбрал поиск по марке")
        await callback.message.edit_text(
            "Давайте сначала познакомимся.\n"
            "Укажите пожалуйста Вашу фамилию и имя (например: Иванов Алексей)"
        )
        logger.info(f"📤 Запрошено имя у пользователя {user_id}")
        await state.set_state(OrderStates.waiting_name)
    
    elif callback.data == "enter_vin":
        logger.info(f"🔢 Пользователь {user_id} выбрал ввод VIN")
        await callback.message.edit_text(
            "напишите VIN код 17 символов, Цифры 0-9 и буквы A-Z (латиница), ЗА ИСКЛЮЧЕНИЕМ I, O, Q"
        )
        logger.info(f"📤 Запрошен VIN у пользователя {user_id}")
        await state.set_state(OrderStates.waiting_vin)
    
    else:  # visit_shop
        logger.info(f"🏪 Пользователь {user_id} выбрал визит в магазин")
        await callback.message.edit_text(
            "Хорошо, мы будем ждать вас!\n"
            "Адрес: г. Павлово, ул. Карла Маркса, д.3\n\n"
            "Режим работы:\n"
            "Пн-Пт: 9:00 - 18:00\n"
            "Сб-Вс: 9:00 - 14:00"
        )
        logger.info(f"📤 Отправлена информация о магазине пользователю {user_id}")
        await state.clear()
        logger.info(f"🧹 Состояние очищено для пользователя {user_id}")


# ============================================================================
# ОБРАБОТЧИКИ ТЕКСТОВЫХ СООБЩЕНИЙ С ЛОГИРОВАНИЕМ
# ============================================================================
@dp.message(OrderStates.waiting_name)
async def process_name(message: types.Message, state: FSMContext):
    """Обработка ввода имени и фамилии"""
    user_id = message.from_user.id
    name = message.text.strip()
    
    logger.info(f"👤 Пользователь {user_id} ввел имя: '{name}'")
    
    if validate_name(name):
        logger.info(f"✅ Имя '{name}' прошло валидацию")
        await state.update_data(user_name=name)
        logger.info(f"💾 Имя сохранено в данных пользователя {user_id}")
        
        await message.answer(
            f"Спасибо, {name}. Ваш телефон?",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
                resize_keyboard=True
            )
        )
        logger.info(f"📤 Запрошен телефон у пользователя {user_id}")
        await state.set_state(OrderStates.waiting_phone)
    else:
        logger.warning(f"⚠️ Имя '{name}' не прошло валидацию")
        await message.answer(
            "Пожалуйста, укажите фамилию и имя в правильном формате (например: Иванов Алексей)"
        )
        logger.info(f"📤 Повторный запрос имени пользователю {user_id}")


@dp.message(OrderStates.waiting_phone)
async def process_phone(message: types.Message, state: FSMContext):
    """Обработка ввода телефона"""
    user_id = message.from_user.id
    phone = message.text.strip()
    
    logger.info(f"👤 Пользователь {user_id} ввел телефон: '{phone}'")
    
    if validate_phone(phone):
        logger.info(f"✅ Телефон '{phone}' прошел валидацию")
        await state.update_data(phone=phone)
        logger.info(f"💾 Телефон сохранен в данных пользователя {user_id}")
        
        data = await state.get_data()
        logger.info(f"📦 Текущие данные пользователя {user_id}: {data}")
        
        await message.answer(
            "укажите марку машины (латиница или кириллица, например: ЛАДА или GAC)"
        )
        logger.info(f"📤 Запрошена марка машины у пользователя {user_id}")
        await state.set_state(OrderStates.waiting_marka)
    else:
        logger.warning(f"⚠️ Телефон '{phone}' не прошел валидацию")
        await message.answer(
            "Пожалуйста, укажите российский телефон в формате: 8XXXXXXXXXX или +7XXXXXXXXXX"
        )
        logger.info(f"📤 Повторный запрос телефона пользователю {user_id}")


@dp.message(OrderStates.waiting_phone, lambda message: message.contact)
async def process_contact(message: types.Message, state: FSMContext):
    """Обработка отправки контакта через кнопку"""
    user_id = message.from_user.id
    contact = message.contact
    phone = contact.phone_number
    
    logger.info(f"👤 Пользователь {user_id} отправил контакт: телефон '{phone}', имя '{contact.first_name}'")
    
    await state.update_data(phone=phone, user_name=contact.first_name)
    logger.info(f"💾 Контактные данные сохранены для пользователя {user_id}")
    
    data = await state.get_data()
    logger.info(f"📦 Текущие данные пользователя {user_id}: {data}")
    
    await message.answer(
        f"Спасибо! Теперь укажите марку машины (например: ЛАДА или GAC)"
    )
    logger.info(f"📤 Запрошена марка машины у пользователя {user_id}")
    await state.set_state(OrderStates.waiting_marka)


@dp.message(OrderStates.waiting_marka)
async def process_marka(message: types.Message, state: FSMContext):
    """Обработка ввода марки машины"""
    user_id = message.from_user.id
    marka = message.text.strip()
    
    logger.info(f"👤 Пользователь {user_id} ввел марку: '{marka}'")
    
    if validate_marka(marka):
        logger.info(f"✅ Марка '{marka}' прошла валидацию")
        await state.update_data(user_marka_mashiny=marka)
        logger.info(f"💾 Марка сохранена в данных пользователя {user_id}")
        
        await message.answer("год выпуска?")
        logger.info(f"📤 Запрошен год выпуска у пользователя {user_id}")
        await state.set_state(OrderStates.waiting_year)
    else:
        logger.warning(f"⚠️ Марка '{marka}' не прошла валидацию")
        await message.answer("Пожалуйста, укажите марку машины (только буквы, например: ЛАДА)")
        logger.info(f"📤 Повторный запрос марки пользователю {user_id}")


@dp.message(OrderStates.waiting_year)
async def process_year(message: types.Message, state: FSMContext):
    """Обработка ввода года выпуска"""
    user_id = message.from_user.id
    year = message.text.strip()
    
    logger.info(f"👤 Пользователь {user_id} ввел год: '{year}'")
    
    if validate_year(year):
        logger.info(f"✅ Год '{year}' прошел валидацию")
        await state.update_data(user_god_mashiny=year)
        logger.info(f"💾 Год сохранен в данных пользователя {user_id}")
        
        await message.answer("код краски?")
        logger.info(f"📤 Запрошен код краски у пользователя {user_id}")
        await state.set_state(OrderStates.waiting_kod)
    else:
        logger.warning(f"⚠️ Год '{year}' не прошел валидацию")
        await message.answer("Пожалуйста, укажите год выпуска цифрами (например: 2020)")
        logger.info(f"📤 Повторный запрос года пользователю {user_id}")


@dp.message(OrderStates.waiting_kod)
async def process_kod(message: types.Message, state: FSMContext):
    """Обработка ввода кода краски"""
    user_id = message.from_user.id
    kod = message.text.strip()
    
    logger.info(f"👤 Пользователь {user_id} ввел код краски: '{kod}'")
    
    if validate_kod(kod):
        logger.info(f"✅ Код краски '{kod}' прошел валидацию")
        await state.update_data(user_kod_kraski=kod)
        logger.info(f"💾 Код краски сохранен в данных пользователя {user_id}")
        
        await message.answer(
            "Нужное количество краски в граммах, кратно 50 и не менее 50 гр (например: 300 или 150)"
        )
        logger.info(f"📤 Запрошено количество краски у пользователя {user_id}")
        await state.set_state(OrderStates.waiting_quantity)
    else:
        logger.warning(f"⚠️ Код краски '{kod}' не прошел валидацию")
        await message.answer(
            "Пожалуйста, введите код краски (только цифры и буквы латиницей, например: 123ABC)"
        )
        logger.info(f"📤 Повторный запрос кода краски пользователю {user_id}")


@dp.message(OrderStates.waiting_quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    """Обработка ввода количества краски"""
    user_id = message.from_user.id
    quantity = message.text.strip()
    
    logger.info(f"👤 Пользователь {user_id} ввел количество: '{quantity}'")
    
    if validate_quantity(quantity):
        logger.info(f"✅ Количество '{quantity}' прошло валидацию")
        await state.update_data(user_kraska_gramm=quantity)
        logger.info(f"💾 Количество сохранено в данных пользователя {user_id}")
        
        await message.answer(
            "У нас имеется две стойки для подбора краски: HYMAX (500р/100гр) и CORSO (300р/100гр).\n"
            "На какой стойке получится лучший вариант, мы на данном этапе не сможем сказать.\n"
            "Уточните: приоритет будет по цене или по качеству?",
            reply_markup=get_priority_keyboard()
        )
        logger.info(f"📤 Запрошен приоритет у пользователя {user_id}")
        await state.set_state(OrderStates.waiting_priority)
    else:
        logger.warning(f"⚠️ Количество '{quantity}' не прошло валидацию")
        await message.answer(
            "Пожалуйста, укажите количество краски, кратное 50 и не менее 50 (например: 100, 150, 200)"
        )
        logger.info(f"📤 Повторный запрос количества пользователю {user_id}")


@dp.message(OrderStates.waiting_vin)
async def process_vin(message: types.Message, state: FSMContext):
    """Обработка ввода VIN-кода"""
    user_id = message.from_user.id
    vin = message.text.strip().upper()
    
    logger.info(f"👤 Пользователь {user_id} ввел VIN: '{vin}'")
    
    if validate_vin(vin):
        logger.info(f"✅ VIN '{vin}' прошел валидацию")
        await state.update_data(user_vin=vin)
        logger.info(f"💾 VIN сохранен в данных пользователя {user_id}")
        
        await message.answer("укажите марку машины?")
        logger.info(f"📤 Запрошена марка машины у пользователя {user_id}")
        await state.set_state(OrderStates.waiting_marka)
    else:
        logger.warning(f"⚠️ VIN '{vin}' не прошел валидацию")
        await message.answer(
            "Пожалуйста, введите корректный VIN-код:\n"
            "17 символов, цифры 0-9 и буквы A-Z (кроме I, O, Q)"
        )
        logger.info(f"📤 Повторный запрос VIN пользователю {user_id}")


@dp.message(OrderStates.waiting_final_question)
async def process_final_question(message: types.Message, state: FSMContext):
    """Обработка финального вопроса от пользователя"""
    user_id = message.from_user.id
    question = message.text
    
    logger.info(f"👤 Пользователь {user_id} задал вопрос: '{question[:50]}...'")
    
    await state.update_data(user_questions=question)
    logger.info(f"💾 Вопрос сохранен в данных пользователя {user_id}")
    
    data = await state.get_data()
    user_name = data.get('user_name', '')
    logger.info(f"📦 Итоговые данные пользователя {user_id}: {data}")
    
    await message.answer(
        f"Спасибо за вопрос, {user_name}! Мы ответим вам в ближайшее время.\n\n"
        "Мы оперативно свяжемся с вами, чтобы ответить на все вопросы и подтвердить заказ.\n"
        "Перед изготовлением потребуется предоплата из расчета 200р за каждые заказанные 100гр краски "
        "(если изготовление при Вас, предоплата не требуется)"
    )
    logger.info(f"📤 Отправлен ответ на вопрос пользователю {user_id}")
    
    await state.clear()
    logger.info(f"🧹 Состояние очищено для пользователя {user_id}")


@dp.message(OrderStates.waiting_alternative)
async def process_alternative_response(message: types.Message, state: FSMContext):
    """Обработка ответа на подсказку о поиске кода краски"""
    user_id = message.from_user.id
    text = message.text.lower()
    
    logger.info(f"👤 Пользователь {user_id} ответил на подсказку: '{text}'")
    
    if text in ['да', 'yes', 'yeah', 'ага', 'угу']:
        logger.info(f"✅ Пользователь {user_id} нашел код краски")
        await message.answer(
            "Давайте познакомимся.\n"
            "Укажите пожалуйста Вашу фамилию и имя (например: Иванов Алексей)"
        )
        logger.info(f"📤 Запрошено имя у пользователя {user_id}")
        await state.set_state(OrderStates.waiting_name)
    
    elif text in ['нет', 'no', 'not', 'не нашел', 'не знаю']:
        logger.info(f"❌ Пользователь {user_id} не нашел код краски")
        await message.answer(
            "Тогда вы можете:\n"
            "1. Принести лючок бензобака или другую деталь для определения цвета\n"
            "2. Ввести VIN-код автомобиля\n"
            "3. Приехать в магазин",
            reply_markup=get_alternative_keyboard()
        )
        logger.info(f"📤 Отправлены альтернативные варианты пользователю {user_id}")
        await state.set_state(OrderStates.waiting_alternative)
    
    else:
        logger.warning(f"⚠️ Пользователь {user_id} дал нераспознанный ответ")
        await message.answer(
            "Я вас не понял. Вы нашли код краски?",
            reply_markup=get_yes_no_keyboard()
        )
        logger.info(f"📤 Повторный запрос пользователю {user_id}")


# ============================================================================
# ОБРАБОТЧИК ПО УМОЛЧАНИЮ С ЛОГИРОВАНИЕМ
# ============================================================================
@dp.message()
async def handle_unknown(message: types.Message):
    """Обработчик для любых других сообщений (вне состояний)"""
    user_id = message.from_user.id
    text = message.text[:50] if message.text else "[не текст]"
    
    logger.info(f"👤 Пользователь {user_id} отправил нераспознанное сообщение: '{text}...'")
    
    await message.answer(
        "Я вас не понял. Пожалуйста, используйте команду /start для начала работы.",
        reply_markup=get_main_keyboard()
    )
    logger.info(f"📤 Отправлено сообщение о непонимании пользователю {user_id}")


# ============================================================================
# ЗАПУСК БОТА С РАСШИРЕННЫМ ЛОГИРОВАНИЕМ
# ============================================================================
async def on_startup():
    """Действия при запуске бота"""
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК БОТА")
    logger.info("=" * 60)
    
    try:
        logger.info(f"🤖 Версия aiogram: {aiogram.__version__}")
    except AttributeError:
        logger.info("🤖 Версия aiogram: неизвестна")
    
    # Проверка соединения с Telegram API
    try:
        logger.info("🔄 Проверка соединения с Telegram API...")
        me = await bot.get_me()
        logger.info(f"✅ Бот авторизован как: @{me.username} (ID: {me.id})")
        logger.info(f"📝 Имя