import logging
import requests
from flask import Flask, request
from telegram import Bot, Update, LabeledPrice
from telegram.ext import Dispatcher, CommandHandler, PreCheckoutQueryHandler, MessageHandler, Filters
import threading

TOKEN = '7963889304:AAHb-55yJ0y7NvwQqu6I8tIFcIQNCk3pMjQ'
bot = Bot(token=TOKEN)

app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

logging.basicConfig(level=logging.INFO)


@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'


@app.route('/')
def index():
    return 'Бот работает!'


def start(update, context):
    update.message.reply_text("Привет! Введите /pay чтобы начать оплату.")


def pay(update, context):
    chat_id = update.message.chat_id
    title = "FreedomPay Тест"
    description = "Оплата товара"
    payload = "custom_payload"
    provider_token = "FREEDOMPAY_PROVIDER_TOKEN"
    currency = "KGS"
    price = 1000  # 10 сомов

    prices = [LabeledPrice("Товар", price * 100)]
    bot.send_invoice(
        chat_id, title, description, payload,
        provider_token, currency, prices
    )


def precheckout_callback(update, context):
    query = update.pre_checkout_query
    if query.invoice_payload != "custom_payload":
        query.answer(ok=False, error_message="Что-то пошло не так...")
    else:
        query.answer(ok=True)


def successful_payment_callback(update, context):
    update.message.reply_text("Оплата прошла успешно!")


dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('pay', pay))
dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))


# Запуск бота в отдельном потоке
def run_bot():
    app.run(host='0.0.0.0', port=5000)


if __name__ == "__main__":
    thread = threading.Thread(target=run_bot)
    thread.start()
