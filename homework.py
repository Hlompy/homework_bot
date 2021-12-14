import logging
import os
import time

import requests
import telegram

from telegram import ReplyKeyboardMarkup
from telegram.ext import CommandHandler, Updater

from dotenv import load_dotenv

from exceptions import ResponseStatusError

load_dotenv()

logging.basicConfig(
    format='%(asctime)s, %(name)s, %(levelname)s, %(message)s',
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    encoding='UTF-8'
)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения"""
    bot.send_message(
        TELEGRAM_CHAT_ID,
        message
    )


def get_api_answer(current_timestamp):
    """Запрос к API"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        raise ResponseStatusError('Статус страницы не 200')
    return response.json()


def check_response(response):
    """Проверка ответа"""
    if not isinstance(response, dict):
        raise TypeError(
            'Ответ API - не словарь'
        )
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            'Домашка пришла не в виде списка'
        )
    if not 'homeworks':
        raise KeyError(
            'Неправильный ключ'
        )
    return response.get('homeworks')


def parse_status(homework):
    """Статус домашки"""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError('Ключ homework_name отсутствует')
    if homework_status not in HOMEWORK_STATUSES.keys():
        raise KeyError('Ключ status отсутствует')
    elif homework_status == 'approved':
        verdict = HOMEWORK_STATUSES.get('approved')
    elif homework_status == 'reviewing':
        verdict = HOMEWORK_STATUSES.get('reviewing')
    elif homework_status == 'rejected':
        verdict = HOMEWORK_STATUSES.get('rejected')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN is not None:
        logging.info('Tokens - OK')
        return True
    else:
        logging.error('ERROR')
    return False


def main():
    """Основная логика работы бота."""
    updater = Updater(TELEGRAM_TOKEN)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    button = ReplyKeyboardMarkup([['/homework']], resize_keyboard=True)

    while True:
        try:
            response = get_api_answer(current_timestamp)
            for homework in check_response(response):
                send_message(bot, parse_status(homework))
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            bot.send_message(TELEGRAM_CHAT_ID, message, reply_markup=button)
            time.sleep(RETRY_TIME)

        updater.dispatcher.add_handler(
            CommandHandler('start', send_message)
        )
        updater.dispatcher.add_handler(
            CommandHandler('homework', parse_status)
        )
        updater.start_polling()
        updater.idle()


if __name__ == '__main__':
    main()
