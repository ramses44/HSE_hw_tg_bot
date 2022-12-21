from telebot.async_telebot import AsyncTeleBot, types
from threading import Thread
import asyncio
from translate import Translator
import wikipedia
import random
import requests
import enchant
import logging
import string

API_KEY = "**HIDDEN**"
TOKEN = "**HIDDEN**"


class Status:
    MENU = 0
    TRANSLATING_RE = 1
    TRANSLATING_ER = 2
    FINDING_WIKI = 3
    FINDING_IM = 4
    CHECKING_ORF_RU = 5
    CHECKING_ORF_EN = 6


def generate_random_string(length=16):
    letters_and_digits = string.ascii_letters + string.digits
    rand_string = ''.join(random.sample(letters_and_digits, length))
    return rand_string


def wiki_find(req):
    lst = wikipedia.search(req, results=5)

    for res in lst:
        try:
            return wikipedia.summary(res)
        except wikipedia.exceptions.WikipediaException:
            pass

    return "Ничего не найдено ¯\\_(ツ)_/¯"


def translate(translator, text):
    try:
        return translator.translate(text)
    except:
        return "Не удалось перевести ¯\\_(ツ)_/¯"


def find_image(req):
    params = {
        "engine": "yandex_images",
        "text": req,
        "api_key": API_KEY
    }
    try:
        res = requests.get("https://serpapi.com/search.json", params=params, timeout=120).json()
        return res['images_results'][0]['original']
    except:
        return "Ничего не найдено!"


def check_orf(text, en=False):
    words = map(lambda word: "".join(c for c in word if c.isalpha()), text.split())
    res = ""
    dct = dictionary_en if en else dictionary_ru

    for word in words:
        try:
            if not dct.check(word):
                res += f"Ошибка в слове {word}. Возможно, вы имели в виду {dct.suggest(word)[0]}.\n"
        except:
            res += f"Не удалось проверить слово {word}\n"

    if not res:
        res = "Ошибок нет!"

    return res


def joke():
    with open('anek.txt') as file:
        aneks = file.read().split("\n*-----*\n")
        return "Анекдот:\n" + aneks[random.randrange(len(aneks))]


def set_to_buffer(key, func, *args):
    buffer[key] = func(*args)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dictionary_ru = enchant.Dict("ru_RU")
dictionary_en = enchant.Dict("en_EN")
re_translator = Translator(from_lang="russian", to_lang="english")
er_translator = Translator(from_lang="english", to_lang="russian")
menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
menu.add(types.KeyboardButton("🇬🇧 Перевести фразу"), types.KeyboardButton("🔎 Найти в Википедии"))
menu.add(types.KeyboardButton("🏞 Найти картинку по запросу"), types.KeyboardButton("📕 Проверить орфографию"))
menu.add(types.KeyboardButton("😜 Хочу отдохнуть"))

bot = AsyncTeleBot(TOKEN)
user_status = {}
buffer = {}


@bot.message_handler(commands=['help', 'start'])
async def send_welcome(message):
    user_status[message.chat.id] = Status.MENU
    logger.info(f"User {message.chat.id} in menu now")

    await bot.send_message(message.chat.id, 'Выберите что вам надо', reply_markup=menu)


@bot.message_handler(content_types='text')
async def process_command(message):
    try:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        msg = ""
        status = user_status.get(message.chat.id, Status.MENU)

        logger.info(f"User {message.chat.id} send command {message.text}, while his status is {status}")

        if status == Status.MENU:
            if message.text == "🇬🇧 Перевести фразу":
                markup.add(types.KeyboardButton("🇷🇺 ➜ 🇬🇧"), types.KeyboardButton("🇬🇧 ➜ 🇷🇺"))
                msg = "Выберите с какого на какой язык переводить"
            elif message.text == "🇷🇺 ➜ 🇬🇧":
                msg = "Что переводить?"
                user_status[message.chat.id] = Status.TRANSLATING_RE
            elif message.text == "🇬🇧 ➜ 🇷🇺":
                msg = "Что переводить?"
                user_status[message.chat.id] = Status.TRANSLATING_ER
            elif message.text == "🔎 Найти в Википедии":
                msg = "Что искать? (на английском)"
                user_status[message.chat.id] = Status.FINDING_WIKI
            elif message.text == "🏞 Найти картинку по запросу":
                msg = "Что искать?"
                user_status[message.chat.id] = Status.FINDING_IM
            elif message.text == "📕 Проверить орфографию":
                markup.add(types.KeyboardButton("*🇷🇺*"), types.KeyboardButton("*🇬🇧*"))
                msg = "На каком языке проверять?"
            elif message.text == "*🇷🇺*":
                msg = "Что проверять?"
                user_status[message.chat.id] = Status.CHECKING_ORF_RU
            elif message.text == "*🇬🇧*":
                msg = "Что проверять?"
                user_status[message.chat.id] = Status.CHECKING_ORF_EN
            elif message.text == "😜 Хочу отдохнуть":
                msg = joke()
            else:
                msg = "Неизвестная команда 🙃"
                markup = menu

        else:
            user_status[message.chat.id] = Status.MENU
            markup = menu
            s = generate_random_string()
            buffer[s] = None
            args = []

            if status == Status.TRANSLATING_RE:
                args = [s, translate, re_translator, message.text]
            elif status == Status.TRANSLATING_ER:
                args = [s, translate, er_translator, message.text]
            elif status == Status.FINDING_WIKI:
                args = [s, wiki_find, message.text]
            elif status == Status.FINDING_IM:
                args = [s, find_image, message.text]
            else:
                args = [s, check_orf, message.text, status == Status.CHECKING_ORF_EN]

            await bot.send_message(message.chat.id, "Секунду...")
            Thread(target=set_to_buffer, args=args).start()
            while not buffer[s]:
                await asyncio.sleep(0.5)

            msg = buffer.pop(s)

        await bot.send_message(message.chat.id, msg, reply_markup=markup)

    except Exception as err:
        await bot.send_message(message.chat.id, "Неизвестная ошибка(", reply_markup=menu)
        logger.error(f"User {message.chat.id} send command {message.text}, which raised the error {err}")


asyncio.run(bot.polling())
