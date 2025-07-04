import config
import telebot
from datetime import datetime
from traceback import format_exc
from bs4 import BeautifulSoup
from telebot import types
from geopy.distance import geodesic
import pytubefix
import os
import subprocess
import requests

bot = telebot.TeleBot(config.token)


@bot.message_handler(content_types=['text'])
def get_text_messages(message, full_name=None, start=None, end=None):
    if message.chat.type == "private":
        dtn = datetime.now()
        botlogfile = open('bot.log', 'a', encoding="utf-8")
        none = None
        if message.from_user.last_name is none:
            full_name = message.from_user.first_name
        else:
            full_name = message.from_user.first_name + " " + message.from_user.last_name
        print(dtn.strftime("%d-%m-%Y %H:%M:%S"), 'Юзер ' + full_name, "ID:", message.from_user.id,
              'написал: ' + message.text, file=botlogfile)
        botlogfile.close()
    try:
        if message.chat.type == "private" and (
                message.text == "/start@testidrobot" or
                message.text == "/start" or
                message.text == "Привіт" or
                message.text == "привіт"):
            bot.send_message(message.chat.id,
                             "Привіт, {mention}!\nЯ <b>{1.first_name}</b>, подивись мої команди.".format(
                                 message.from_user, bot.get_me(),
                                 mention=f'<a href="tg://user?id={message.from_user.id}">{full_name}</a>'),
                             parse_mode="HTML")
            if os.path.exists("first_message.log"):
                pass
            elif not os.path.exists("first_message.log"):
                file = open("first_message.log", "w", encoding="utf-8")
                file.close()
            file = open("first_message.log")
            string = file.read()
            search_word = str(message.from_user.id)
            if search_word in string:
                file.close()
            else:
                dtn = datetime.now()
                userlogfile = open('first_message.log', 'a', encoding="utf-8")
                print(dtn.strftime("%d-%m-%Y %H:%M:%S"), "ID:", message.from_user.id, "username:",
                      message.from_user.username, "Name:", full_name, file=userlogfile)
                userlogfile.close()
        elif message.text == "type":
            bot.send_message(message.chat.id, message.chat.type)
        elif (message.text == "/help" or
              message.text == "!help" or
              message.text == "/help@testidrobot"):
            if message.chat.type != "private":
                bot.send_message(message.chat.id,
                                 "Мої команди в чаті:\n"
                                 "!hit або /hit у відповідь іншому учаснику - дати ляпаса\n"
                                 "!top або /top - топ чату")
            else:
                bot.send_message(message.from_user.id, "Напиши привіт")
        elif (message.text == "/hit" or
              message.text == "!hit" or
              message.text == "/hit@testidrobot"):
            filec = open("chats.log", 'r+')
            string = filec.read()
            filec.close()
            chat_id = str(message.chat.id)
            user_id = str(message.from_user.id)
            string.split(" ")
            chats = string.split("\n")
            chats.pop(-1)
            filec = open("chats.log", "w", encoding="utf-8")
            chat_notfound = True
            for chat in chats:
                if chat.find(chat_id) != -1:
                    chat_notfound = False
                    if chat.find(user_id) == -1:
                        chat = chat + str(user_id) + " "
                print(chat, file=filec)
            if chat_notfound:
                print(chat_id, user_id, "", file=filec)
            filec.close()
            fileu = open("users.log", 'r+', encoding="utf-8")
            string = fileu.read()
            search_word1 = str(message.from_user.id)
            string_split = string.split(" ")
            string_split[-1] = ""
            if search_word1 in string:
                n = string_split.index("\n" + str(message.from_user.id))
                n_first = n + 1
                name = ""
                while True:
                    if "\n" not in string_split[n + 2] and string_split[n + 2] != string_split[-1]:
                        n += 1
                        name = name + " " + string_split[n]
                    else:
                        num = string_split[n + 1]
                        nu = n + 1
                        break
                n_last = n
                num = num.replace("'", "")
                num = int(num) + 1
                num_new = str(num)
                string_split.pop(nu)
                string_split.insert(nu, num_new)
                tg_name = str(message.from_user.first_name)
                if message.from_user.last_name is not None:
                    tg_name = tg_name + " " + str(message.from_user.last_name)
                elif message.from_user.last_name is None:
                    tg_name = tg_name
                if name == tg_name:
                    pass
                elif name != tg_name:
                    i_if = 0
                    while True:
                        if i_if <= n_last - n_first:
                            string_split.pop(n_first)
                            i_if += 1
                        else:
                            break
                    i_if = 1
                    i_tg = 0
                    while True:
                        if i_if <= len(tg_name.split(" ")):
                            string_split.insert(n_first, tg_name.split(" ")[i_tg])
                            i_if += 1
                            i_tg += 1
                            n_first += 1
                        else:
                            break
            string_split_update = " ".join(string_split)
            fileu.truncate(0)
            fileu.close()
            fileu = open('users.log', 'a', encoding="utf-8")
            print(string_split_update, file=fileu)
            if search_word1 not in string:
                user_id = message.from_user.id
                user_fn = message.from_user.first_name
                if message.from_user.last_name is None:
                    print(user_id, user_fn, str(1) + " ", file=fileu)
                elif message.from_user.last_name is not None:
                    user_ln = message.from_user.last_name
                    print(user_id, user_fn, user_ln, str(1) + " ", file=fileu)
            else:
                pass
            fileu.close()
            if message.chat.type != "private":
                try:
                    if message.from_user.id == message.reply_to_message.from_user.id:
                        if message.from_user.last_name is not None:
                            bot.send_message(message.chat.id, "{from_} дав ляпаса самому собі".format(
                                from_=f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name} '
                                      f'{message.from_user.last_name}</a>'), parse_mode="html")
                        elif message.from_user.last_name is None:
                            bot.send_message(message.chat.id, "{from_} дав ляпаса самому собі".format(
                                from_=f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}'
                                      f'</a>'), parse_mode="html")
                        else:
                            pass
                    elif (message.from_user.last_name is not None and
                          message.reply_to_message.from_user.last_name is not None):
                        bot.send_message(message.chat.id, "{from_} дав ляпаса {to}".format(
                            from_=f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name} '
                                  f'{message.from_user.last_name}</a>',
                            to=f'<a href="tg://user?id={message.reply_to_message.from_user.id}">'
                               f'{message.reply_to_message.from_user.first_name} '
                               f'{message.reply_to_message.from_user.last_name}</a>'), parse_mode="HTML")
                    elif (message.reply_to_message.from_user.last_name is None and
                          message.from_user.last_name is None):
                        bot.send_message(message.chat.id, "{from_} дав ляпаса {to}".format(
                            from_=f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>',
                            to=f'<a href="tg://user?id={message.reply_to_message.from_user.id}">'
                               f'{message.reply_to_message.from_user.first_name}</a>'), parse_mode="HTML")
                    elif (message.from_user.last_name is not None and
                          message.reply_to_message.from_user.last_name is None):
                        bot.send_message(message.chat.id, "{from_} дав ляпаса {to}".format(
                            from_=f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name} '
                                  f'{message.from_user.last_name}</a>',
                            to=f'<a href="tg://user?id={message.reply_to_message.from_user.id}">'
                               f'{message.reply_to_message.from_user.first_name}</a>'), parse_mode="HTML")
                    elif (message.from_user.last_name is None and
                          message.reply_to_message.from_user.last_name is not None):
                        bot.send_message(message.chat.id, "{from_} дав ляпаса {to}".format(
                            from_=f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>',
                            to=f'<a href="tg://user?id={message.reply_to_message.from_user.id}">'
                               f'{message.reply_to_message.from_user.first_name} '
                               f'{message.reply_to_message.from_user.last_name}</a>'), parse_mode="HTML")
                    else:
                        pass
                except AttributeError:
                    pass
            else:
                pass
        elif (message.text == "!top" or
              message.text == "!топ" or
              message.text == "/top"):
            if message.chat.type != "private":
                filec = open("chats.log", 'r+', encoding="utf-8")
                chats_file = filec.read()
                filec.close()
                fileu = open("users.log", 'r+', encoding="utf-8")
                users_file = fileu.read()
                fileu.close()
                chat_id = message.chat.id
                lines = chats_file.split('\n')
                lines = lines[::-1]
                chat_users = []
                for chat_str in lines:
                    chat = chat_str.split(' ')
                    if str(chat[0]) == str(chat_id):
                        chat.pop(0)
                        chat.pop()
                        chat_users = chat
                        break
                lines = users_file.split('\n')
                lines = lines[::-1]
                users_info = []
                for user_str in lines:
                    user = user_str.split(' ')
                    if user[0] in chat_users:
                        users_info.append([user[0], ' '.join(user[1:-2]), int(user[-2])])
                top_10 = sorted(users_info, key=lambda par: par[2], reverse=True)[0:10]
                my_message = '<b>Топ юзерів:</b>' + "\n"
                n = 1
                for user in top_10:
                    user_id = user[0]
                    user_name = user[1]
                    my_message += str(n) + ". " + "{uwu}".format(
                        uwu=f'<a href="tg://user?id={user_id}">{user_name}</a>') + ' — ' + "<i>" + str(
                        user[2]) + "</i>" + '\n'
                    n += 1
                bot.send_message(message.chat.id, my_message, parse_mode="HTML")
            else:
                pass
        elif message.text.startswith("/yt"):
            try:
                bot.send_message(message.chat.id, "Зачекайте, будь ласка")
                y = message.text.split()
                url = str(y[1])
                part = False
                if str(y[1]) != str(y[-1]):
                    start = str(y[2])
                    end = str(y[3])
                    part = True
                else:
                    pass
                youtube = pytubefix.YouTube(url, use_oauth=True, allow_oauth_cache=True)
                '''for the first attempt you will need to open google.com/device and past 
                your code from console and authorize to any google account'''
                video = youtube.streams.filter(progressive=True).desc().first()
                video.download(config.path_to_project + "/testidrobot/v_download", "video_cache.mp4")
                if part:
                    input_file_y = config.path_to_project + '/testidrobot/v_download/video_cache.mp4'
                    output_file_y = config.path_to_project + '/testidrobot/v_download/video_cache_cut.mp4'
                    ffmpeg_command = [config.ffmpeg_bin, '-i', input_file_y, '-ss', start, '-to', end, output_file_y]
                    subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    vfilec = open(config.path_to_project + "/testidrobot/v_download/video_cache_cut.mp4", "rb")
                    if os.path.getsize(
                            config.path_to_project + "/testidrobot/v_download/video_cache_cut.mp4") < 52428800:
                        bot.send_video(message.chat.id, vfilec)
                    else:
                        bot.send_message(message.chat.id, "Нажаль, відео важить більше 50 МБ (обмеження телеграму)")
                    os.remove(config.path_to_project + "/testidrobot/v_download/video_cache.mp4")
                    vfilec.close()
                    os.remove(config.path_to_project + "/testidrobot/v_download/video_cache_cut.mp4")
                elif not part:
                    vfile = open(config.path_to_project + "/testidrobot/v_download/video_cache.mp4", "rb")
                    if os.path.getsize(config.path_to_project + "/testidrobot/v_download/video_cache.mp4") < 52428800:
                        bot.send_video(message.chat.id, vfile)
                    else:
                        bot.send_message(message.chat.id, "Нажаль, відео важить більше 50 МБ (обмеження телеграму)")
                    vfile.close()
                    os.remove(config.path_to_project + "/testidrobot/v_download/video_cache.mp4")
            except BaseException:
                bot.send_message(message.chat.id,
                                 "Введіть /yt <посилання на відео> [час старту *опціонально] [час кінця *опціонально]")
            bot.delete_message(message.chat.id, message.message_id + 1)
        elif message.text.startswith("/ogg"):
            try:
                bot.send_message(message.chat.id, "Зачекайте, будь ласка")
                y = message.text.split()
                url = str(y[1])
                youtube = pytubefix.YouTube(url, use_oauth=True, allow_oauth_cache=True)
                '''for the first attempt you will need to open google.com/device and past
                 your code from console and authorize to any google account'''
                video = youtube.streams.filter(progressive=True).desc().first()
                video.download(config.path_to_project + "/testidrobot/v_download", "video_cache.mp4")
                vfile = open(config.path_to_project + "/testidrobot/v_download/video_cache.mp4", "rb")
                if os.path.getsize(config.path_to_project + "/testidrobot/v_download/video_cache.mp4") < 21000000:
                    input_file = config.path_to_project + '/testidrobot/v_download/video_cache.mp4'
                    output_file = config.path_to_project + '/testidrobot/a_download/cache.ogg'
                    bitrate = '64k'
                    ffmpeg_command = [config.ffmpeg_bin, '-i', input_file, '-c:a', 'libopus', '-b:a', bitrate, '-vn',
                                      output_file]
                    subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    vfile.close()
                    voicefile = open(config.path_to_project + "/testidrobot/a_download/cache.ogg", "rb")
                    bot.send_voice(message.chat.id, voicefile)
                    voicefile.close()
                    os.remove(config.path_to_project + "/testidrobot/v_download/video_cache.mp4")
                    os.remove(config.path_to_project + "/testidrobot/a_download/cache.ogg")
                else:
                    bot.send_message(message.chat.id, "Нажаль, відео важить більше 20 МБ (обмеження телеграму)")
                    vfile.close()
                    os.remove(config.path_to_project + "/testidrobot/v_download/video_cache.mp4")
            except BaseException:
                bot.send_message(message.chat.id, "Введіть /ogg [посилання на відео]")
            bot.delete_message(message.chat.id, message.message_id + 1)
        elif (message.text == "/time" or
              message.text == "time" or
              message.text == "/time@testidrobot"):
            now = datetime.now()
            bot.send_message(message.chat.id, "UTC - " + now.strftime("%H:%M:%S"))
        elif (message.text == "/id" or
              message.text == "Id" or
              message.text == "id" or
              message.text == "/id@testidrobot"):
            bot.send_message(message.chat.id, "Ваш телеграм ID - <code>{ID}</code>".format(ID=message.from_user.id),
                             parse_mode="HTML")
        elif (message.text == "H" or
              message.text == "h" or
              message.text == "/h"):
            url = 'https://steamcommunity.com/id/Za_XaP'
            r = requests.get(url)
            soup = BeautifulSoup(r.content, features="lxml")
            div = soup.find("div", {"class": "game_info_details"})
            line = [s.strip() for s in div.stripped_strings if s.strip()]
            i = line[0]
            i = i.split()[0]
            if "," in i:
                i = i.replace(",", "")
            bot.send_message(message.from_user.id, "Admin has {} hours in the last game".format(i))
        elif message.text.startswith("/toadm"):
            if not message.text.startswith("/toadm "):
                bot.send_message(message.from_user.id, 'Введіть /toadm текст')
            else:
                x = message.text.split(' ', 1)
                try:
                    bot.send_message(message.from_user.id, "Повідомлення відправлено адміну бота!")
                    bot.send_message(550557267, "Повідомлення від {mention}:\n\n{msg}".format(
                        mention=f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name} '
                                f'{message.from_user.last_name}</a>', msg=x[1]), parse_mode="HTML")
                    bot.forward_message(550557267, message.from_user.id, message.message_id)
                except BaseException:
                    bot.send_message(message.from_user.id, 'Введіть /toadm текст')
        elif message.text.startswith("/touser") and message.from_user.id == 550557267:
            if not message.text.startswith("/touser "):
                bot.send_message(message.from_user.id, 'Введіть /touser ID текст')
            else:
                x = message.text.split(' ', 2)
                try:
                    iduser = int(x[1])
                    bot.send_message(iduser, "Повідомлення від адміна:\n\n{msg}".format(msg=x[2]), parse_mode="HTML")
                    bot.send_message(message.from_user.id, "Повідомлення відправлено юзеру!")
                except BaseException:
                    bot.send_message(message.from_user.id, 'Введіть /touser ID текст')
        elif message.text == "/whereadm":
            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
            button = types.KeyboardButton(text='Відправити розташування', request_location=True)
            markup.add(button)
            bot.send_message(message.from_user.id, 'Відправ своє розташування, та я скажу як далеко адмін!',
                             reply_markup=markup)
        else:
            if message.from_user.id == message.chat.id:
                bot.send_message(message.from_user.id, "Я тебя не розумію. Напиши /help.",
                                 reply_markup=types.ReplyKeyboardRemove())
            else:
                pass
    except telebot.apihelper.ApiTelegramException:
        pass
    except BaseException:
        bot.send_message(message.chat.id,
                         "ERROR! Щось пішло не так...\nЯкщо ви бачите це повідомлення, повідомте про проблему {}! "
                         "Скажіть, яке повідомлення викликало це повідомлення.".format(
                             '<a href="tg://user?id=550557267">адміна</a>'), parse_mode="HTML")
        bot.send_message(550557267, "ID: " + str(message.from_user.id) + " Text: " + message.text + "\n" + format_exc())


@bot.message_handler(content_types=['location'])
def get_location_messages(message):
    if message.chat.type == "private":
        botlogfile = open('bot.log', 'a', encoding="utf-8")
        dtn = datetime.now()
        none = None
        if message.from_user.last_name is none:
            full_name = message.from_user.first_name
        else:
            full_name = message.from_user.first_name + " " + message.from_user.last_name
        print(dtn.strftime("%d-%m-%Y %H:%M:%S"), 'Юзер ' + full_name, "ID:", message.from_user.id,
              'прислал точку: ' + str(message.location.latitude), str(message.location.longitude), file=botlogfile)
        botlogfile.close()
        try:
            if message.location is not None:
                adm = (50.05920, 36.28530)
                us = (message.location.latitude, message.location.longitude)
                bot.send_message(message.from_user.id, "Адмін знаходиться від цієї точки в {d} кілометрах".format(
                    d=round(geodesic(adm, us).km, 1)), parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
        except BaseException:
            bot.send_message(message.from_user.id,
                             "ERROR! Щось пішло не так...\nЯкщо ви бачите це повідомлення, повідомте про проблему {}! "
                             "Скажіть, яке повідомлення викликало це повідомлення.".format(
                                 '<a href="tg://user?id=550557267">адміна</a>'), parse_mode="HTML")
            bot.send_message(550557267, "ID: " + str(message.from_user.id) + " LOCATION" + "\n" + format_exc())


@bot.message_handler(content_types=['audio'])
def get_audio_messages(message):
    if message.chat.type == "private":
        botlogfile = open('bot.log', 'a', encoding="utf-8")
        dtn = datetime.now()
        none = None
        if message.audio.file_name is not none:
            audio_name = str(message.audio.file_name)
        else:
            audio_name = "НЕТ НАЗВАНИЯ"
        if message.from_user.last_name is none:
            full_name = message.from_user.first_name
        else:
            full_name = message.from_user.first_name + " " + message.from_user.last_name
        print(dtn.strftime("%d-%m-%Y %H:%M:%S"), 'Юзер ' + full_name, "ID:", message.from_user.id,
              'прислал аудио: ' + audio_name, 'AUDIO ID: ' + str(message.audio.file_id), file=botlogfile)
        botlogfile.close()
        try:
            file_info = bot.get_file(message.audio.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            with open(config.path_to_project + '/testidrobot/a_download/cache.mp3', 'wb') as new_file:
                new_file.write(downloaded_file)
                new_file.close()
            vfile = open(config.path_to_project + "/testidrobot/a_download/cache.mp3", "rb")
            if os.path.getsize(config.path_to_project + "/testidrobot/a_download/cache.mp3") < 400000000:
                input_file = config.path_to_project + '/testidrobot/a_download/cache.mp3'
                output_file = config.path_to_project + '/testidrobot/a_download/cache.ogg'
                bitrate = '64k'
                ffmpeg_command = [config.ffmpeg_bin, '-i', input_file, '-c:a', 'libopus', '-b:a', bitrate, '-vn',
                                  output_file]
                subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                vfile.close()
                voicefile = open(config.path_to_project + "/testidrobot/a_download/cache.ogg", "rb")
                bot.send_voice(message.chat.id, voicefile)
                voicefile.close()
                os.remove(config.path_to_project + "/testidrobot/a_download/cache.mp3")
                os.remove(config.path_to_project + "/testidrobot/a_download/cache.ogg")
            else:
                bot.send_message(message.chat.id, "Нажаль, відео важить більше 50 МБ (обмеження телеграму)")
                vfile.close()
                os.remove(config.path_to_project + "/testidrobot/a_download/cache.mp3")
        except BaseException:
            bot.send_message(message.chat.id,
                             "ERROR! Щось пішло не так...\nЯкщо ви бачите це повідомлення, повідомте про проблему {}! "
                             "Скажіть, яке повідомлення викликало це повідомлення.".format(
                                 '<a href="tg://user?id=550557267">адміна</a>'), parse_mode="HTML")
            bot.send_message(550557267,
                             "ID: " + str(
                                 message.from_user.id) + " File: " + message.audio.file_name + "\n" + format_exc())


bot.polling(none_stop=True, interval=0)
