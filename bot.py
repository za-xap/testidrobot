import config
import telebot
from datetime import datetime
from random import random, randint
from time import sleep
from traceback import format_exc
import pytube
import os
import subprocess
bot = telebot.TeleBot(config.token)
@bot.message_handler(content_types=['text'])
def get_text_messages(message):
   try:
    if message.text == "/start@testidrobot" or message.text == "/start" or message.text == "Привіт" or message.text == "привіт":
      bot.send_message(message.chat.id, "Привіт, {mention}!\nЯ <b>{1.first_name}</b>, подивись мої команди.".format(message.from_user, bot.get_me(), mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name} {message.from_user.last_name}</a>'), parse_mode="HTML")
    elif message.text == "type":
      bot.send_message(message.chat.id, message.chat.type)
    elif message.text == "/help" or  message.text == "!help" or message.text == "/help@testidrobot":
     if message.chat.type != "private":
      bot.send_message(message.chat.id, "Мої команди в чаті:\n!hit або /hit у відповідь іншому учаснику - дати ляпаса\n!top або /top - топ чату")
     else:
      bot.send_message(message.from_user.id, "Напиши привіт")
    elif message.text == "/hit" or message.text == "!hit" or message.text == "/hit@testidrobot":
     filec = open("chats.log", 'r+')
     string = filec.read()
     filec.close()
     chat_id = str(message.chat.id)
     user_id = str(message.from_user.id)
     string_split = string.split(" ")
     chats = string.split("\n")
     chats.pop(-1)
     filec = open("chats.log", "w")
     chat_notfound = True
     for chat in chats:
         if chat.find(chat_id) != -1:
             chat_notfound = False
             if chat.find(user_id) == -1:
                 chat = chat + str(user_id) + " "
         print(chat, file = filec)
     if chat_notfound:
         print(chat_id, user_id, "", file = filec)
     filec.close()
     fileu = open("users.log", 'r+')
     string = fileu.read()
     search_word1 = str(message.from_user.id)
     string_split = string.split(" ")
     string_split[-1] = ""
     if search_word1 in string:
      n = string_split.index("\n" + str(message.from_user.id))
      n_first = n + 1
      name = ""
      while True:
       if "\n" not in string_split[n+2] and string_split[n+2] != string_split[-1]:
        n += 1
        name = name + " " + string_split[n]
       else:
        num = string_split[n+1]
        nu = n + 1
        break
      n_last = n
      name = name[1:]
      num = num.replace("'", "")
      num = int(num) + 1
      num_new = str(num)
      string_split.pop(nu)
      string_split.insert(nu, num_new)
      tg_name = str(message.from_user.first_name)
      if message.from_user.last_name is not None:
       tg_name = tg_name + " " + str(message.from_user.last_name)
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
     fileu = open('users.log', 'a')
     print(string_split_update, file = fileu)
     if search_word1 not in string:
      user_id = message.from_user.id
      user_fn = message.from_user.first_name
      if message.from_user.last_name is None:
          user_ln = ""
      else:
          user_ln = message.from_user.last_name
      print(user_id, user_fn, user_ln, str(1) + " ", file = fileu)
     else:
      pass
     fileu.close()
     if message.chat.type != "private":
      try:
       if message.from_user.id == message.reply_to_message.from_user.id:
        if message.from_user.last_name is not None:
          bot.send_message(message.chat.id, "{fron} дав ляпаса самому собі".format(fron=f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name} {message.from_user.last_name}</a>'), parse_mode="html")
        elif message.from_user.last_name is None:
          bot.send_message(message.chat.id, "{fron} дав ляпаса самому собі".format(fron=f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'), parse_mode="html")
        else:
          pass
       elif message.from_user.last_name is not None and message.reply_to_message.from_user.last_name is not None:
        bot.send_message(message.chat.id, "{fron} дав ляпаса {to}".format(fron=f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name} {message.from_user.last_name}</a>', to=f'<a href="tg://user?id={message.reply_to_message.from_user.id}">{message.reply_to_message.from_user.first_name} {message.reply_to_message.from_user.last_name}</a>'), parse_mode="HTML")
       elif message.reply_to_message.from_user.last_name is None and message.from_user.last_name is None:
        bot.send_message(message.chat.id, "{fron} дав ляпаса {to}".format(fron=f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>', to=f'<a href="tg://user?id={message.reply_to_message.from_user.id}">{message.reply_to_message.from_user.first_name}</a>'), parse_mode="HTML")
       elif message.from_user.last_name is not None and message.reply_to_message.from_user.last_name is None:
        bot.send_message(message.chat.id, "{fron} дав ляпаса {to}".format(fron=f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name} {message.from_user.last_name}</a>', to=f'<a href="tg://user?id={message.reply_to_message.from_user.id}">{message.reply_to_message.from_user.first_name}</a>'), parse_mode="HTML")
       elif message.from_user.last_name is None and message.reply_to_message.from_user.last_name is not None:
        bot.send_message(message.chat.id, "{fron} дав ляпаса {to}".format(fron=f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>', to=f'<a href="tg://user?id={message.reply_to_message.from_user.id}">{message.reply_to_message.from_user.first_name} {message.reply_to_message.from_user.last_name}</a>'), parse_mode="HTML")
       else:
        pass
      except AttributeError:
       pass
     else:
      pass
    elif message.text == "!top" or message.text == "!топ" or message.text == "/top" or message.text == "/top@testidrobot":
     if message.chat.type != "private":
      filec = open("chats.log", 'r+')
      chats_file = filec.read()
      filec.close()
      fileu = open("users.log", 'r+')
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
          users_info.append([user[0],' '.join(user[1:-2]),int(user[-2])])
      top_10 = sorted(users_info,key = lambda par : par[2],reverse=True)[0:10]
      my_message = '<b>Топ юзерів:</b>' + "\n"
      n = 1
      for user in top_10:
        user_id = user[0]
        user_name = user[1]
        my_message += str(n) + ". " + "{uwu}".format(uwu = f'<a href="tg://user?id={user_id}">{user_name}</a>') + ' — ' + "<i>" + str(user[2]) + "</i>" + '\n'
        n += 1
      bot.send_message(message.chat.id, my_message, parse_mode="HTML")
     else:
      pass
    elif message.text.startswith("/yt"):
      try:
       y = message.text.split()
       url = str(y[1])
       youtube = pytube.YouTube(url)
       video = youtube.streams.filter(progressive=True).desc().first()
       bot.send_message(message.chat.id, "Зачекайте, будь ласка")
       video.download("/home/zaka/bots/testidrobot/v_download", "video_cache.mp4")
       vfile = open("/home/zaka/bots/testidrobot/v_download/video_cache.mp4", "rb")
       if os.path.getsize("/home/zaka/bots/testidrobot/v_download/video_cache.mp4") < 52428800:
         bot.send_video(message.chat.id, vfile)
       else:
         bot.send_message(message.chat.id, "Нажаль, відео важить більше 50 МБ (обмеження телеграму)")
       vfile.close()
       os.remove("/home/zaka/bots/testidrobot/v_download/video_cache.mp4")
      except BaseException:
       bot.send_message(message.chat.id, "Введіть /yt [посилання на відео]")
    elif message.text.startswith("/ogg"):
      try:
       y = message.text.split()
       url = str(y[1])
       youtube = pytube.YouTube(url)
       video = youtube.streams.filter(progressive=True).desc().first()
       bot.send_message(message.chat.id, "Зачекайте, будь ласка")
       video.download("/home/zaka/bots/testidrobot/v_download", "video_cache.mp4")
       vfile = open("/home/zaka/bots/testidrobot/v_download/video_cache.mp4", "rb")
       if os.path.getsize("/home/zaka/bots/testidrobot/v_download/video_cache.mp4") < 21000000:
         input_file = '/home/zaka/bots/testidrobot/v_download/video_cache.mp4'
         output_file = '/home/zaka/bots/testidrobot/a_download/cache.ogg'
         bitrate = '64k'
         ffmpeg_command = ['ffmpeg', '-i', input_file, '-c:a', 'libopus', '-b:a', bitrate, '-vn', output_file]
         subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
         vfile.close()
         voicefile = open("/home/zaka/bots/testidrobot/a_download/cache.ogg", "rb")
         bot.send_voice(message.chat.id, voicefile)
         voicefile.close()
         os.remove("/home/zaka/bots/testidrobot/v_download/video_cache.mp4")
         os.remove("/home/zaka/bots/testidrobot/a_download/cache.ogg")
       else:
         bot.send_message(message.chat.id, "Нажаль, відео важить більше 20 МБ (обмеження телеграму)")
         vfile.close()
         os.remove("/home/zaka/bots/testidrobot/v_download/video_cache.mp4")
      except BaseException:
       bot.send_message(message.chat.id, "Введіть /ogg [посилання на відео]")
    elif message.text == "/time" or message.text == "time" or message.text == "/time@testidrobot":
      now = datetime.now()
      bot.send_message(message.chat.id, "UTC - " + now.strftime("%H:%M:%S"))
    elif message.text == "/id" or message.text == "Id" or message.text == "id" or message.text == "/id@testidrobot":
      ID = message.from_user.id
      bot.send_message(message.chat.id, "Ваш телеграм ID - <code>{ID}</code>".format(ID = message.from_user.id), parse_mode="HTML")
    elif message.text.startswith("/calc"):
      x = message.text.split()
      try:
        bot.send_message(message.from_user.id, "a+b=<b>{}</b>\na-b=<b>{}</b>\na*b=<b>{}</b>\na/b=<b>{}</b>\naᵇ=<b>{}</b>\nbª=<b>{}</b>\n√a=<b>{}</b>\n√b=<b>{}</b>".format(float(x[1])+float(x[2]), float(x[1])-float(x[2]), float(x[1])*float(x[2]), float(x[1])/float(x[2]), float(x[1])**float(x[2]), float(x[2])**float(x[1]), float(x[1])**0.5, float(x[2])**0.5), parse_mode="HTML")
      except ZeroDivisionError:
          bot.send_message(message.from_user.id, "a+b={}\na-b={}\na*b={}\na/b=На нуль ділити не можна!\naᵇ={}\nbª={}\n√a={}\n√b={}".format(float(x[1])+float(x[2]), float(x[1])-float(x[2]), float(x[1])*float(x[2]), float(x[1])**float(x[2]), float(x[2])**float(x[1]), float(x[1])**0.5, float(x[2])**0.5), parse_mode="HTML")
      except OverflowError:
            bot.send_message(message.from_user.id, "a+b={}\na-b={}\na*b={}\na/b={}\naᵇ=ДУЖЕ багато\nbª=ДУЖЕ багато\n√a={}\n√b={}".format(float(x[1])+float(x[2]), float(x[1])-float(x[2]), float(x[1])*float(x[2]), float(x[1])/float(x[2]), float(x[1])**0.5, float(x[2])**0.5), parse_mode="HTML")
      except ValueError:
        bot.send_message(message.from_user.id, "Введіть /calc число число")
      except IndexError: 
        bot.send_message(message.from_user.id, "Введіть /calc число число")
    else:
      if message.from_user.id == message.chat.id:
        bot.send_message(message.from_user.id, "Я тебя не розумію. Напиши /help.")
      else:
        pass
   except BaseException:
       bot.send_message(message.chat.id, "ERROR! Щось пішло не так...\nЯкщо ви бачите це повідомлення, повідомте про проблему {}! Скажіть, яке повідомлення викликало це повідомлення.".format('<a href="tg://user?id=550557267">адміна</a>'), parse_mode="HTML")
       bot.send_message(550557267, "ID: " + str(message.from_user.id) + " Text: " + message.text + "\n" + format_exc())
bot.polling(none_stop=True, interval=0)
