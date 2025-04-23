import logging
import requests
from flask import Flask, request
from telegram import Bot, Update, LabeledPrice, ReplyKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, PreCheckoutQueryHandler, MessageHandler, Filters
import threading
import os
import psycopg2
from datetime import datetime

# Устанавливаем уровень логирования
logging.basicConfig(level=logging.DEBUG)

TOKEN = '7963889304:AAHb-55yJ0y7NvwQqu6I8tIFcIQNCk3pMjQ'
bot = Bot(token=TOKEN)

app = Flask(__name__)

# Dispatcher
dispatcher = Dispatcher(bot, None, workers=1, use_context=True)

# Подключение к базе данных PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Создание таблицы при первом запуске
cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        username TEXT,
        amount INTEGER,
        currency TEXT,
        payment_time TIMESTAMP
    )
''')
conn.commit()

# Товары
products = {
    "Стикеры": 50,
    "Футболка": 150,
    "Кружка": 100
}

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    logging.info("Обработан запрос от Telegram: %s", update)
    return 'ok'


@app.route('/')
def index():
    return 'Бот работает!'


def start(update, context):
    keyboard = [[item] for item in products.keys()]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("Привет! Выберите товар для покупки:", reply_markup=reply_markup)


def pay(update, context):
    product_name = update.message.text
    if product_name not in products:
        update.message.reply_text("Пожалуйста, выберите товар из списка, отправив команду /start.")
        return

    chat_id = update.message.chat_id
    title = f"Покупка: {product_name}"
    description = f"Вы покупаете {product_name}"
    payload = "custom_payload"
    provider_token = "6450350554:LIVE:548841"
    currency = "KGS"
    price = products[product_name]

    prices = [LabeledPrice(product_name, price * 100)]

    logging.info(f"Отправка инвойса: {product_name} за {price} KGS пользователю {chat_id}")

    try:
        bot.send_invoice(
            chat_id, title, description, payload,
            provider_token, currency, prices
        )
    except Exception as e:
        logging.error(f"Ошибка при отправке инвойса: {e}")
        update.message.reply_text(f"Произошла ошибка: {e}")


def precheckout_callback(update, context):
    query = update.pre_checkout_query
    if query.invoice_payload != "custom_payload":
        query.answer(ok=False, error_message="Что-то пошло не так...")
    else:
        query.answer(ok=True)


def successful_payment_callback(update, context):
    payment = update.message.successful_payment
    user = update.message.from_user

    logging.info(f"Платёж от {user.username} ({user.id}) на сумму {payment.total_amount / 100} {payment.currency}")

    # Сохраняем в базу данных
    cursor.execute('''
        INSERT INTO payments (user_id, username, amount, currency, payment_time)
        VALUES (%s, %s, %s, %s, %s)
    ''', (user.id, user.username, payment.total_amount, payment.currency, datetime.now()))
    conn.commit()

    update.message.reply_text("Оплата прошла успешно!")


# Обработчики
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('pay', pay))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, pay))
dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))

# Запуск бота в отдельном потоке
def run_bot():
    app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    thread = threading.Thread(target=run_bot)
    thread.start()
