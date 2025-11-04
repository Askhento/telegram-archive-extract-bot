import telebot
from telebot import types, util
import requests
from remotezip import RemoteZip
import os
import shutil
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')


def format_bytes(size):
    # 2**10 = 1024
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return size, power_labels[n]+'bytes'


def getFileList(url, file_id):
    res = []
    with RemoteZip(url) as zip:
        for zip_info in zip.infolist():
            if (zip_info.file_size == 0):
                continue
            base_file_name = (zip_info.filename).split("/")[-1]
            (size, scale) = format_bytes(zip_info.file_size)
            res.append(
                (f"{base_file_name}, {size} {scale}\n", zip_info.filename))

    return res


def extractZip(file, url):
    with RemoteZip(url) as zip:
        return zip.extract(file, "temp")


def testContentRange(url):
    # url = "https://tools.ietf.org/html/rfc7233"
    headers = {"Range": "bytes=0-500"}
    r = requests.get(url, headers=headers)
    print(r.text)


def displayFIlePicker(message: types.Message, files: list, archive_url: str):
    # print(files)
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    buttons = [types.InlineKeyboardButton(
        display_name, callback_data=base_filename) for (display_name, base_filename) in files]
    keyboard.add(*buttons)

    bot.send_message(
        message.chat.id,
        f"{archive_url}\nChoose file from list : ",
        reply_markup=keyboard,
        reply_parameters=types.ReplyParameters(message_id=message.message_id),

    )


debug_mode = True


def debug_print(*args, **kwargs):
    if debug_mode:
        print(*args, **kwargs)


keep_temps = False

# You can set parse_mode by default. HTML or MARKDOWN
bot = telebot.TeleBot(TOKEN, parse_mode=None)

# current_user_archive = {}


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(
        message, "Forward or send ZIP archive to get specific files from it")

# func=lambda message: message.forward_from or message.forward_from_chat


@bot.message_handler(content_types=['document'])
def handle_forwarded_file(message:  types.Message):
    archive_name = message.document.file_name
    if (not archive_name.endswith(".zip")):
        bot.reply_to(message, "Only ZIP files currently supported!")
        return
    # Example for a forwarded document file
    if message.document:
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)

        archive_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        # current_user_archive[message.from_user.id] = archive_url
        # bot.reply_to(message, f"Forwarded file URL: {archive_url}")

        files = getFileList(archive_url, file_id)

        # bot.reply_to(message, files)
        displayFIlePicker(message, files, archive_url)

    else:
        bot.reply_to(message, "No document found in the forwarded message")


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call: types.CallbackQuery):

    bot.answer_callback_query(call.id, f"Loading : {call.data}")

    filename = call.data
    archive_url = call.message.text.split("\n")[0]

    debug_print(f"will extract {filename} at {archive_url}")

    local_file = extractZip(filename, archive_url)
    debug_print("LOCAL", local_file)

    parent_dir = os.path.dirname(local_file)
    debug_print("PARENT", parent_dir)
    with open(local_file, "r") as f:
        bot.send_document(call.message.chat.id, f)

    if not keep_temps:
        shutil.rmtree("temp")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Start remote ZIP bot")
    parser.add_argument('--debug', action='store_true',
                        help='Show debug messages ')
    parser.add_argument('--keeptemp', action='store_true',
                        help='Keep temp files')

    args = parser.parse_args()

    global debug_mode
    debug_mode = args.debug

    global keep_temps
    keep_temps = args.keeptemp

    bot.infinity_polling(interval=5)


if __name__ == "__main__":
    main()
