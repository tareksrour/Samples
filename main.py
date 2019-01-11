import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaAudio, InputMediaPhoto, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler
import requests
import os
from pydub import AudioSegment
import math
import anytree
from ast import literal_eval
import db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
fingerprint = None
cookies = "userlanguageprod=en; country=LB; device=web; _ga=GA1.2.920984962.1511888977; " \
          "_gid=GA1.2.921398994.1511888977; " \
          "amplitude_idanghami.com" \
          "=eyJkZXZpY2VJZCI6IjY1YjRlNDE5LWVhOWQtNGQ5Ni05MDVlLWEwOThmZGZkNmU1MFIiLCJ1c2VySWQiOm51bGwsIm9wdE91dCI6ZmFsc2UsInNlc3Npb25JZCI6MTUxMTg4ODk3NzE0OCwibGFzdEV2ZW50VGltZSI6MTUxMTg4ODk3NzIwOSwiZXZlbnRJZCI6MSwiaWRlbnRpZnlJZCI6MSwic2VxdWVuY2VOdW1iZXIiOjJ9 "
headers = {"Accept": "application/json, text/plain, */*",
           "Accept-Encoding": "utf-8",
           "Accept-Language": "en-US,en,q=0.8,ar,q=0.6",
           "Connection": "keep-alive",
           "Cookie": cookies,
           "Host": "api.anghami.com",
           "Origin": "https://play.anghami.com",
           "Referer": "https://play.anghami.com/explore",
           "User-Agent": "Mozilla/5.0 (Windows NT 10.0, Win64, x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/56.0.2924.87 Safari/537.36"}


def get_download_url(id):
    if not fingerprint:
        get_fingerprint()
    url = "https://api.anghami.com/gateway.php?angh_type=GETdownload&fileid={}&fingerprint=65b4e419-ea9d-4d96-905e-a098fdfd6e50R&lang=en&language=en&method=GET&nocache=true&noloader=true&type=GETdownload".format(
        id)
    return requests.get(url, headers=headers).json()['location']


def start(bot, update):
    update.message.reply_text('Welcome to Music Search Bot, What do you want to do?')


def get_download(bot, update):
    query = update.callback_query
    data = str(query.data).split("=")[1]
    data = literal_eval(data)

    query_str, result, type = db.get_by_id(data['sId'])
    id = data['id']

    for s in result:
        if s['id'] == id:
            song = s
            break
    file = "{} - {}".format(song["title"], song["artist"])
    keys = [[], [InlineKeyboardButton("Reset", callback_data="/reset={}".format(data))]]
    size = len(result)
    setup_keyboard(data, keys, size)

    try:
        file = "{} - {}".format(song["title"], song["artist"])
        open("cache/media/{}.mp3".format(file), 'rb')

    except Exception:
        url = get_download_url(id)
        r = requests.get(url, stream=True)
        with open("cache/media/{}".format(file), "wb") as f:
            for chunk in r.iter_content(4096):
                f.write(chunk)
            f.flush()
            f.close()
        r.close()
        url = "https://anghamicoverart.akamaized.net/?id={}".format(song["coverArt"])
        r = requests.get(url)
        with open("cache/media/{}.jpg".format(id), "wb") as f:
            f.write(r.content)
            f.flush()
            f.close()
        r.close()
        preview = AudioSegment.from_file("cache/media/{}".format(file), "m4a")
        preview.export("cache/media/{}.mp3".format(file), format="mp3",
                       tags={'artist': song['artist'], 'album': song['album'], 'title': song['title']},
                       cover="cache/media/{}.jpg".format(id))
        os.remove("cache/media/{}.jpg".format(id))
        os.remove("cache/media/{}".format(file))
    bot.answer_callback_query(callback_query_id=update.callback_query.id)
    bot.send_audio(chat_id=query.message.chat_id,
                   message_id=query.message.message_id,
                   audio=open("cache/media/{}.mp3".format(file), 'rb'),
                   title=song['title'], performer=song['artist'],
                   thumb="https://anghamicoverart.akamaized.net/?id={}".format(
                       song["coverArt"]), timeout=999)


def type_menu(query_str):
    return [[InlineKeyboardButton("♫ Song", callback_data="/song={}".format(query_str)),
             InlineKeyboardButton("💿 Album", callback_data="/album={}".format(query_str))],
            [InlineKeyboardButton("👨‍🎨 Artist", callback_data="/artist={}".format(query_str)),
             InlineKeyboardButton("📋 Playlist", callback_data="/playlist={}".format(query_str))]]


def button(bot, update):
    query = update.callback_query
    if u"/preview" in query.data:
        get_preview(bot, update)
    else:
        if u"/reset" in query.data:
            reset_preview(bot, update)
        else:
            if u"/download" in query.data:
                get_download(bot, update)
            else:
                if u"/song" in query.data:
                    search_for(bot, update, str(query.data).split("=")[1], newSearch=True)
                else:
                    if u'/other_page' in query.data:
                        data = str(query.data).split("=")[1]
                        data = literal_eval(data)
                        search_for(bot, update, search_id=data['sId'], page=data['page'])
                    else:
                        if u'/album' in query.data:
                            search_for(bot, update, str(query.data).split("=")[1], newSearch=True, type='album')
                        else:
                            if u'/back' in query.data:
                                data = str(query.data).split("=")[1]
                                data = literal_eval(data)
                                query_str, result, type = db.get_by_id(data['sId'])

                                keys = type_menu(query_str)
                                bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                                   message_id=update.callback_query.message.message_id)
                                update.callback_query.message.reply_text('Searching for "{}" , choose category!'.format(
                                    query_str), disable_web_page_preview=False, parse_mode=ParseMode.HTML,
                                    reply_markup=InlineKeyboardMarkup(keys))
                            else:
                                if u'/open' in query.data:
                                    open_sub(bot, update)
                                else:
                                    if u'/return' in query.data:
                                        data = str(query.data).split("=")[1]
                                        data = literal_eval(data)
                                        ret = db.get_parent([data['sId']])
                                        search_for(bot, update, search_id=ret[0], page=ret[1])
                                    else:
                                        if u'/artist' in query.data:
                                            search_for(bot, update, str(query.data).split("=")[1],type='artist', newSearch=True)


def open_sub(bot, update, page=0):
    query = update.callback_query
    data = str(query.data).split("=")[1]
    data = literal_eval(data)
    id = data['id']
    search_id, result = get_album_data(id)
    item = result[page]
    db.add_parent(data['sId'], search_id, data['page'])
    data = {'page': page, 'sId': search_id, 'id': item['id']}
    send_back_result(bot, data, item, True, len(result), 'albumdata', update)


def reset_preview(bot, update):
    query = update.callback_query
    data = str(query.data).split("=")[1]
    data = literal_eval(data)
    query_str, result, type = db.get_by_id(data['sId'])
    id = data['id']

    for s in result:
        if s['id'] == id:
            song = s
            break

    keys = [[], [InlineKeyboardButton("Preview", callback_data="/preview={}".format(data)),
                 InlineKeyboardButton("Download", callback_data="/download={}".format(data))]]
    size = len(result)
    setup_keyboard(data, keys, size)
    bot.answer_callback_query(callback_query_id=update.callback_query.id)
    bot.edit_message_media(timeout=999, reply_markup=InlineKeyboardMarkup(keys), chat_id=query.message.chat_id,
                           message_id=query.message.message_id,
                           media=InputMediaPhoto(media="https://anghamicoverart.akamaized.net/?id={}".format(
                               song["coverArt"]), caption="{} - {}".format(song["title"], song["artist"])))


def get_preview(bot, update):
    query = update.callback_query
    data = str(query.data).split("=")[1]
    data = literal_eval(data)
    id = data['id']
    song_data = get_song_data(id)
    query_str, result, type = db.get_by_id(data['sId'])

    keys = [[], [InlineKeyboardButton("Reset", callback_data="/reset={}".format(data)),
                 InlineKeyboardButton("Download", callback_data="/download={}".format(data))]]
    size = len(result)
    setup_keyboard(data, keys, size)
    try:
        open("cache/preview/{}.mp3".format(id), 'rb')
    except Exception as e:
        print(e)
        url = "http://track.anghami.com/rest/v1/GETtrack.view?songid={}".format(id)
        r = requests.get(url)

        with open("cache/preview/{}".format(id), "wb") as f:
            f.write(r.content)
            f.flush()
            f.close()
        r.close()
        preview = AudioSegment.from_file("cache/preview/{}".format(id), "m4a")
        preview.export("cache/preview/{}.mp3".format(id), format="mp3")
        os.remove("cache/preview/{}".format(id))
    bot.answer_callback_query(callback_query_id=update.callback_query.id)
    bot.edit_message_media(timeout=999, reply_markup=InlineKeyboardMarkup(keys), chat_id=query.message.chat_id,
                           message_id=query.message.message_id,
                           media=InputMediaAudio(media=open("cache/preview/{}.mp3".format(id), 'rb'),
                                                 title=song_data['title'], performer=song_data['artist'],
                                                 thumb="https://anghamicoverart.akamaized.net/?id={}".format(
                                                     song_data["coverArt"])))


def setup_keyboard(data, keys, size):
    del data['id']
    page = data['page']
    if page != 0:
        data['page'] = page - 1
        keys[0].append(InlineKeyboardButton("<", callback_data="/other_page={}".format(data)))
    if page < size - 1:
        data['page'] = page + 1
        keys[0].append(InlineKeyboardButton(">", callback_data="/other_page={}".format(data)))
    if keys[0] == []:
        del keys[0]


def help(bot, update):
    update.message.reply_text("Use /start to test this bot.")


def message(bot, update):
    if update.message.text:
        query_str = update.message.text
        keys = [[InlineKeyboardButton("♫ Song", callback_data="/song={}".format(query_str)),
                 InlineKeyboardButton("💿 Album", callback_data="/album={}".format(query_str))],
                [InlineKeyboardButton("👨‍🎨 Artist", callback_data="/artist={}".format(query_str)),
                 InlineKeyboardButton("📋 Playlist", callback_data="/playlist={}".format(query_str))]]
        update.message.reply_text('Searching for "{}" , choose category!'.format(
            update.message.text), disable_web_page_preview=False, parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keys))

    else:
        update.message.reply_text("Only text search is supported!")


def keymap(type, data):
    if type == 'song':
        return [[], [InlineKeyboardButton("👁 Preview", callback_data="/preview={}".format(data)),
                     InlineKeyboardButton("⏬ Download", callback_data="/download={}".format(data))],
                [InlineKeyboardButton("🔙 Back", callback_data="/back={}".format(data))]]
    else:
        if type == 'albumdata':
            return [[], [InlineKeyboardButton("👁 Preview", callback_data="/preview={}".format(data)),
                         InlineKeyboardButton("⏬ Download", callback_data="/download={}".format(data))],
                    [InlineKeyboardButton("🔙 Return", callback_data="/return={}".format(data))]]
    return [[], [InlineKeyboardButton("🔙 Back", callback_data="/back={}".format(data)),
                 InlineKeyboardButton("📂 Open", callback_data="/open={}".format(data))]]


def search_for(bot, update, query=None, type="song", page=0, newSearch=False, search_id=None):
    if not fingerprint:
        get_fingerprint()
    if search_id:
        query, result, type = db.get_by_id(search_id)
    else:
        search_id, result = db.get_by_query(query, type)
    if newSearch or not result:
        url = "https://api.anghami.com/gateway.php?type=GETsearch&query={}&output=JSONhp&edge=1&count=18&language=en&lang=en&angh_type=GETsearch&fingerprint=65b4e419-ea9d-4d96-905e-a098fdfd6e50R".format(
            query)
        r = requests.get(url, headers=headers)
        result = []
        for section in r.json()["sections"]:
            if not section["type"] == type:
                continue
            for item in section['data']:
                if type == 'song':
                    s = {'id': item['id'], 'coverArt': item['coverArt'], 'album': item['album'],
                         'artist': item['artist'], 'title': item['title']}
                else:
                    if type == 'album':
                        s = {'id': item['id'], 'coverArt': item['coverArt'],
                             'artist': item['artist'], 'title': item['title']}
                    else:
                        if type == 'artist':
                            s = {'id': item['id'], 'coverArt': item['ArtistArt'],
                                 'title': item['name']}
                        else:
                            if type=='playlist':
                                s = {'id': item['id'], 'coverArt': item['coverArt'],
                                     'artist': item['details'], 'title': item['title']}
                result.append(s)
        search_id = db.insert(query, result, type)
    size = len(result)
    if size == 0:
        bot.answer_callback_query(callback_query_id=update.callback_query.id)
        bot.edit_message_text(text='No {} result,Please Choose different Category for "{}"!'.format(type, query),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id,
                              reply_markup=InlineKeyboardMarkup(type_menu(query)))
        return
    item = result[page]
    data = {'page': page, 'sId': search_id, 'id': item['id']}

    send_back_result(bot, data, item, newSearch, size, type, update)


def send_back_result(bot, data, item, newSearch, size, type, update):
    keys = keymap(type, data)
    setup_keyboard(data, keys, size)
    markup = InlineKeyboardMarkup(keys)
    if item['artist']:
        caption="{} - {}".format(item["title"], item["artist"])
    else:
        caption="{}".format(item["title"])
    if newSearch:
        bot.delete_message(chat_id=update.callback_query.message.chat_id,
                           message_id=update.callback_query.message.message_id)
        bot.send_photo(
            photo="https://anghamicoverart.akamaized.net/?id={}".format(item["coverArt"]),
            caption=caption,
            chat_id=update.callback_query.message.chat_id,
            reply_markup=markup)
    else:
        bot.answer_callback_query(callback_query_id=update.callback_query.id)
        bot.edit_message_media(
            media=InputMediaPhoto(media="https://anghamicoverart.akamaized.net/?id={}".format(item["coverArt"]),
                                  caption=caption),
            chat_id=update.callback_query.message.chat_id,
            message_id=update.callback_query.message.message_id,
            reply_markup=markup)


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def get_album_data(id):
    search_id, result = db.get_by_query(query=str(id), type='albumdata')
    if result:
        return search_id, result
    url = 'https://api.anghami.com/gateway.php?albumId={}&angh_type=GETalbumdata&extras=&fingerprint=65b4e419-ea9d-4d96-905e-a098fdfd6e50R&lang=en&language=en&output=jsonhp&type=GETalbumdata'.format(
        id)
    r = requests.get(url, headers=headers)
    result = []
    response = r.json()
    for section in response['sections']:
        if section['type'] != 'song':
            continue
        for item in section['data']:
            s = {'id': item['id'], 'coverArt': item['coverArt'], 'artist': item['artist'], 'title': item['title']}
            result.append(s)
    return db.insert(str(id), result, 'albumdata'), result


def get_fingerprint():
    global fingerprint, cookies
    url = "https://api.anghami.com/gateway.php?angh_type=POSTfingerprint&fp=eyJkZXZpY2VJZCI6IjY1YjRlNDE5LWVhOWQtNGQ5Ni05MDVlLWEwOThmZGZkNmU1MFIiLCJ1c2VySWQiOm51bGwsIm9wdE91dCI6ZmFsc2UsInNlc3Npb25JZCI6MTUxMTg4ODk3NzE0OCwibGFzdEV2ZW50VGltZSI6MTUxMTg4ODk3NzE0OCwiZXZlbnRJZCI6MCwiaWRlbnRpZnlJZCI6MCwic2VxdWVuY2VOdW1iZXIiOjB9&hash=v1uXvoNcgRNOog%2BfxReLdpgeOJzbprspLpSm0XIA3bAZ6jYl33RRN4FR8gYXF%2BrQ6RWzsB1Ybhxj3NiJ5BPDBiqsol1PftBXyo3UqM03jZxznrbjc%2B2os2XFNhjYBxfbOQPl%2Fq9kNBNUP%2BrReabW365uDGuj01CC2DoWqZu1%2BV2vgl9unfVDKTncPazYgiP%2FU65CJozvYEIP0DSZ1dSNsTWdSM6GfyIwK0TkPW4G%2B077ubl%2F9K4GZ5uX70JQIAhKM%2BJ0lozMFbJFQdK5gRsNYNF34hMeAm31ZR6OKPYEQd9CTBEcrxh3TtCDC1iXdSaqHsHcqw%3D%3D&type=POSTfingerprint"
    r = requests.get(url, headers=headers)
    fingerprint = r.json()['fingerprint']
    j = 'fingerprint:{}; '.format(fingerprint)
    a = ["=".join(x) for x in r.cookies.items()]
    cookies = "; ".join(["; ".join(a), j, cookies])
    headers['cookies'] = cookies


def get_song_data(id):
    url = "https://api.anghami.com/gateway.php?type=GETsongdata&songid={}&output=jsonhp&testnewhp=1&disablecountryfilter=1&language=en&lang=en&angh_type=GETsongdata&fingerprint=65b4e419-ea9d-4d96-905e-a098fdfd6e50R".format(
        id)
    r = requests.get(url, headers=headers)
    return r.json()


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater("696728563:AAEOYdUO4HHfNCeZBI0289RgFRwm4FURhYo")

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_handler(MessageHandler([], message))
    updater.dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == '__main__':
    if not os.path.exists('cache'):
        os.mkdir('cache')
        os.mkdir('cache/preview')
        os.mkdir('cache/media')
    else:
        if not os.path.exists('cache/preview'):
            os.mkdir('cache/preview')
        if not os.path.exists('cache/media'):
            os.mkdir('cache/media')
    main()
