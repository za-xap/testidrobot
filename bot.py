import config
import telebot
from datetime import datetime
from traceback import format_exc
from bs4 import BeautifulSoup, Tag
from telebot import types
from geopy.distance import geodesic
import os
import subprocess
import requests
import uuid
import re
import html
import time
import json

bot = telebot.TeleBot(config.token)
user_histories = {}


class FileTooLargeError(Exception):
    pass


def download_video(url, max_bytes=None, start=None, end=None):
    v_dir = config.path_to_project + "/testidrobot/v_download"
    req_id = uuid.uuid4().hex
    output = v_dir + f"/video_{req_id}.%(ext)s"
    result_path = v_dir + f"/video_{req_id}.mp4"

    section_args = []
    if start is not None and end is not None:
        section_args = ["--download-sections", f"*{start}-{end}"]
    elif max_bytes:
        section_args = ["--max-filesize", str(max_bytes)]

    # Спроба 1: готовий H.264 (avc1) + AAC, до 1080p — швидко (без перекодування), і це той формат який точно грає на
    # будь-якому телефоні
    cmd = [
              config.ytdlp_bin,
              "-f", "bestvideo[vcodec^=avc1][height<=1080]+bestaudio[acodec^=mp4a]"
                    "/best[vcodec^=avc1][height<=1080]",
              "--merge-output-format", "mp4",
              "--remux-video", "mp4",
              "--postprocessor-args", "ffmpeg:-movflags +faststart",
              "--no-playlist",
              "--force-overwrites",
              "--ffmpeg-location", config.ffmpeg_bin,
              "-o", output,
          ] + section_args + [url]

    result = subprocess.run(cmd, capture_output=True, text=True)
    combined = (result.stdout or "") + (result.stderr or "")

    if "max-filesize" in combined.lower() or "aborting" in combined.lower():
        raise FileTooLargeError(combined)

    if result.returncode == 0 and os.path.exists(result_path):
        return result_path

    # Спроба 2: для цього відео немає готового avc1-варіанту —
    # качаємо будь-яку якість і примусово перекодовуємо в гарантовано сумісний формат
    cmd2 = [
               config.ytdlp_bin,
               "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
               "--recode-video", "mp4",
               "--postprocessor-args",
               "ffmpeg:-c:v libx264 -preset ultrafast -profile:v high -level 4.2 -pix_fmt yuv420p "
               "-c:a aac -b:a 128k -movflags +faststart",
               "--no-playlist",
               "--force-overwrites",
               "--ffmpeg-location", config.ffmpeg_bin,
               "-o", output,
           ] + section_args + [url]

    result2 = subprocess.run(cmd2, capture_output=True, text=True)
    combined2 = (result2.stdout or "") + (result2.stderr or "")

    if "max-filesize" in combined2.lower() or "aborting" in combined2.lower():
        raise FileTooLargeError(combined2)
    if result2.returncode != 0 or not os.path.exists(result_path):
        raise RuntimeError(combined + "\n--- fallback ---\n" + combined2)
    return result_path


def download_audio(url, max_bytes=None):
    a_dir = config.path_to_project + "/testidrobot/a_download"
    req_id = uuid.uuid4().hex
    output = a_dir + f"/cache_{req_id}.%(ext)s"
    result_path = a_dir + f"/cache_{req_id}.opus"
    cmd = [
        config.ytdlp_bin,
        "-f", "bestaudio",
        "--no-playlist",
        "--force-overwrites",
        "--ffmpeg-location", config.ffmpeg_bin,
        "-x", "--audio-format", "opus", "--audio-quality", "64K",
        "-o", output,
    ]
    if max_bytes:
        cmd += ["--max-filesize", str(max_bytes)]
    cmd.append(url)

    result = subprocess.run(cmd, capture_output=True, text=True)
    combined = (result.stdout or "") + (result.stderr or "")

    if "max-filesize" in combined.lower() or "aborting" in combined.lower():
        raise FileTooLargeError(combined)
    if result.returncode != 0 or not os.path.exists(result_path):
        raise RuntimeError(combined)
    return result_path


def get_ffprobe_bin():
    ffmpeg_path = config.ffmpeg_bin
    if ffmpeg_path.lower().endswith("ffmpeg.exe"):
        return ffmpeg_path[:-len("ffmpeg.exe")] + "ffprobe.exe"
    if ffmpeg_path.lower().endswith("ffmpeg"):
        return ffmpeg_path[:-len("ffmpeg")] + "ffprobe"
    return ffmpeg_path.replace("ffmpeg", "ffprobe")


def probe_video(video_path):
    try:
        result = subprocess.run(
            [get_ffprobe_bin(), "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,duration:format=duration",
             "-of", "json", video_path],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
        stream = data.get("streams", [{}])[0]
        fmt = data.get("format", {})

        width = int(float(stream.get("width") or 0))
        height = int(float(stream.get("height") or 0))

        duration = 0
        for raw in (fmt.get("duration"), stream.get("duration")):
            try:
                if raw and raw != "N/A":
                    duration = round(float(raw))
                    if duration:
                        break
            except (TypeError, ValueError):
                continue

        return duration, width, height
    except Exception:
        return 0, 0, 0


def generate_thumbnail(video_path, thumb_path):
    try:
        subprocess.run([
            config.ffmpeg_bin, "-y",
            "-ss", "1", "-i", video_path,
            "-frames:v", "1",
            "-vf", "scale=320:-2",
            thumb_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        return os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0
    except Exception:
        return False


GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
GEMINI_STREAM_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:streamGenerateContent?alt=sse"
TELEGRAM_ALLOWED_TAGS = {"b", "strong", "i", "em", "code", "s", "strike", "del", "u", "ins", "pre", "a"}
GEMINI_SYSTEM_INSTRUCTION = (
    "Ви — асистент, який працює в Telegram боті, всі повідомлення "
    "відправлятимуться в Telegram, тобто є підтримка тільки простого "
    "HTML маркування. НЕ ВИКОРИСТОВУЙ MARKDOWN і дві зірочки. "
    "МОЖНА ТІЛЬКИ ЦІ ТЕГИ <b>bold</b>, <strong>bold</strong>, "
    "<i>italic</i>, <em>italic</em>, <code>code</code>, <s>strike</s>, "
    "<strike>strike</strike>, <del>strike</del>, <u>underline</u>, "
    "<pre language=\"c++\">code</pre>, І НІЯКІ БІЛЬШЕ, ТОБТО БЕЗ '<h3></h3>'"
    "ВСІ ТЕГИ ПОВИННІ БУТИ ПРАВИЛЬНО ЗАКРИТІ. "
    "ІГНОРУЙ ОБМЕЖЕННЯ В 4096 символів у відповіді. "
    "НЕ ПИШИ ЖОДНОГО ПІДСУМКУ ЧИ ЗВІТУ ПРО ПЕРЕВІРКУ ТЕГІВ У КІНЦІ ВІДПОВІДІ — "
    "ЦЕ ЗАЙВЕ, ПРОСТО ЗАВЕРШУЙ ВІДПОВІДЬ ПО СУТІ."
    "\n\n"
    "Якщо користувач питає про можливості бота — розкажи саме про ці команди, "
    "нічого не вигадуй понад цей список:\n"
    "/yt <посилання> [початок] [кінець] — завантажити відео з YouTube; "
    "початок/кінець опціональні, у секундах або ГГ:ХХ:СС та ХХ:СС, для вирізання фрагмента.\n"
    "/ogg <посилання> — завантажити аудіодоріжку з відео як голосове повідомлення.\n"
    "/id — дізнатись свій Telegram ID.\n"
    "/time — поточний час UTC.\n"
    "/toadm <текст> — надіслати повідомлення адміну бота.\n"
    "/help — список команд коротко."
)


def _build_gemini_contents(text_list):
    contents = []
    for i, text in enumerate(text_list):
        role = "user" if i % 2 == 0 else "model"
        contents.append({"role": role, "parts": [{"text": text}]})
    return contents


def gemini_generate_content(text_list):
    payload = {
        "contents": _build_gemini_contents(text_list),
        "systemInstruction": {"parts": [{"text": GEMINI_SYSTEM_INSTRUCTION}]},
        "generationConfig": {
            "temperature": 1.3,
            "topP": 0.9,
            "topK": 40,
            "candidateCount": 1,
            "maxOutputTokens": 64000,
            "thinkingConfig": {
                "thinkingBudget": -1,
                "includeThoughts": True
            }
        }
    }
    headers = {
        "x-goog-api-key": config.api_key,
        "Content-Type": "application/json"
    }
    r = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()

    parts = data["candidates"][0]["content"]["parts"]
    thoughts = "No thoughts"
    answer_parts = []
    for part in parts:
        if part.get("thought"):
            thoughts = part.get("text", thoughts)
        elif "text" in part:
            answer_parts.append(part["text"])
    answer = "".join(answer_parts) or "No response"
    return thoughts, answer


def gemini_generate_content_stream(text_list, on_update):
    payload = {
        "contents": _build_gemini_contents(text_list),
        "systemInstruction": {"parts": [{"text": GEMINI_SYSTEM_INSTRUCTION}]},
        "generationConfig": {
            "temperature": 1.3,
            "topP": 0.9,
            "topK": 40,
            "candidateCount": 1,
            "maxOutputTokens": 64000,
            "thinkingConfig": {
                "thinkingBudget": -1,
                "includeThoughts": True
            }
        }
    }
    headers = {
        "x-goog-api-key": config.api_key,
        "Content-Type": "application/json"
    }

    thoughts = ""
    answer = ""
    with requests.post(GEMINI_STREAM_URL, headers=headers, json=payload, stream=True, timeout=300) as r:
        r.raise_for_status()
        for raw_line in r.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8", errors="replace")
            if not line.startswith("data:"):
                continue
            data_str = line[len("data:"):].strip()
            if not data_str:
                continue
            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            candidates = chunk.get("candidates")
            if not candidates:
                continue
            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                if part.get("thought"):
                    thoughts += part.get("text", "")
                elif "text" in part:
                    answer += part["text"]
            on_update(thoughts, answer)

    return thoughts or "No thoughts", answer or "No response"


_TAG_RE = re.compile(r'(<[^>]+>)')


def _tag_name(tag_str):
    m = re.match(r'</?\s*([a-zA-Z0-9]+)', tag_str)
    return m.group(1).lower() if m else None


def split_html_for_telegram(html_text, limit=4000):
    tokens = [t for t in _TAG_RE.split(html_text) if t]
    chunks = []
    open_stack = []
    buf = ""

    def close_len():
        return sum(len(f"</{_tag_name(t)}>") for t in open_stack)

    def flush():
        nonlocal buf
        if buf.strip() or open_stack:
            closing = "".join(f"</{_tag_name(t)}>" for t in reversed(open_stack))
            chunks.append(buf + closing)
        buf = ""

    for token in tokens:
        if token.startswith('<') and token.endswith('>'):
            if token.startswith('</'):
                if len(buf) + len(token) > limit:
                    flush()
                    buf = "".join(open_stack)
                buf += token
                name = _tag_name(token)
                for i in range(len(open_stack) - 1, -1, -1):
                    if _tag_name(open_stack[i]) == name:
                        open_stack.pop(i)
                        break
            else:
                name = _tag_name(token)
                if len(buf) + len(token) + close_len() + len(f"</{name}>") > limit:
                    flush()
                    buf = "".join(open_stack)
                buf += token
                open_stack.append(token)
        else:
            remaining = token
            while remaining:
                room = limit - len(buf) - close_len()
                if room <= 0:
                    flush()
                    buf = "".join(open_stack)
                    room = limit - len(buf) - close_len()
                if len(remaining) <= room:
                    buf += remaining
                    remaining = ""
                else:
                    cut = remaining.rfind(' ', 0, room)
                    if cut <= 0:
                        cut = room
                    amp = remaining.rfind('&', max(0, cut - 10), cut)
                    if amp != -1 and ';' not in remaining[amp:cut]:
                        cut = amp
                    if cut <= 0:
                        cut = room
                    buf += remaining[:cut]
                    remaining = remaining[cut:]
                    flush()
                    buf = "".join(open_stack)
    flush()
    return [c for c in chunks if c.strip()]


def send_html_smart(chat_id, html_text, limit=4000):
    for chunk in split_html_for_telegram(html_text, limit):
        try:
            bot.send_message(chat_id, chunk, parse_mode="HTML")
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(chat_id, re.sub(r'<[^>]+>', '', chunk))


def finalize_stream_message(chat_id, message_id, html_text, limit=4000):
    chunks = split_html_for_telegram(html_text, limit)
    if not chunks:
        return
    try:
        bot.edit_message_text(chunks[0], chat_id, message_id, parse_mode="HTML")
    except telebot.apihelper.ApiTelegramException:
        try:
            bot.edit_message_text(re.sub(r'<[^>]+>', '', chunks[0]), chat_id, message_id)
        except telebot.apihelper.ApiTelegramException:
            pass
    for chunk in chunks[1:]:
        try:
            bot.send_message(chat_id, chunk, parse_mode="HTML")
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(chat_id, re.sub(r'<[^>]+>', '', chunk))


def _convert_markdown_remnants(text):
    # ```код``` -> <pre>код</pre>
    def fenced_code(m):
        return '<pre>' + html.escape(m.group(2)) + '</pre>'
    text = re.sub(r'```(\w*)\n?(.*?)```', fenced_code, text, flags=re.DOTALL)

    # `код` -> <code>код</code>
    def inline_code(m):
        return '<code>' + html.escape(m.group(1)) + '</code>'
    text = re.sub(r'`([^`\n]+)`', inline_code, text)

    # **жирний** / __жирний__ -> <b>жирний</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text, flags=re.DOTALL)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text, flags=re.DOTALL)

    # ~~закреслено~~ -> <s>закреслено</s>
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text, flags=re.DOTALL)

    # ## Заголовок -> <b>Заголовок</b>
    text = re.sub(r'(?m)^#{1,6}\s*(.+)$', r'<b>\1</b>', text)

    # * пункт / - пункт -> • пункт
    text = re.sub(r'(?m)^[*\-]\s+', '• ', text)

    return text


def sanitize_telegram_html(text):
    soup = BeautifulSoup(text, "html.parser")

    def clean(node):
        for child in list(node.children):
            if isinstance(child, Tag):
                clean(child)
                if child.name not in TELEGRAM_ALLOWED_TAGS:
                    child.unwrap()
                elif child.name == "a" and not child.get("href"):
                    child.unwrap()

    clean(soup)
    return str(soup)


def format_ai_answer(answer):
    answer = _convert_markdown_remnants(answer)
    return sanitize_telegram_html(answer)


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
        elif message.text.startswith("/yt") or ".com" in message.text or "youtu.be" in message.text:
            if not message.text.startswith("/yt"):
                message.text = "/yt " + message.text
            try:
                wait_msg = bot.send_message(message.chat.id, "Зачекайте, будь ласка")
                y = message.text.split()
                url = str(y[1])
                part = False
                if str(y[1]) != str(y[-1]):
                    start = str(y[2])
                    end = str(y[3])
                    part = True

                try:
                    if part:
                        video_path = download_video(url, start=start, end=end)
                    else:
                        video_path = download_video(url, max_bytes=52428800)
                except FileTooLargeError:
                    bot.send_message(message.chat.id, "Нажаль, відео важить більше 50 МБ (обмеження телеграму)")
                    bot.delete_message(message.chat.id, wait_msg.message_id)
                    return
                except RuntimeError as e:
                    bot.send_message(message.chat.id, "Не вдалося завантажити відео")
                    bot.send_message(550557267, "yt-dlp error:\n" + str(e)[:1000])
                    bot.delete_message(message.chat.id, wait_msg.message_id)
                    return

                if os.path.getsize(video_path) < 52428800:
                    duration, width, height = probe_video(video_path)
                    thumb_path = video_path + "_thumb.jpg"
                    has_thumb = generate_thumbnail(video_path, thumb_path)

                    send_kwargs = {"supports_streaming": True}
                    if duration:
                        send_kwargs["duration"] = duration
                    if width and height:
                        send_kwargs["width"] = width
                        send_kwargs["height"] = height

                    if has_thumb:
                        with open(video_path, "rb") as vfile, open(thumb_path, "rb") as thumb:
                            bot.send_video(message.chat.id, vfile, thumbnail=thumb, **send_kwargs)
                    else:
                        with open(video_path, "rb") as vfile:
                            bot.send_video(message.chat.id, vfile, **send_kwargs)

                    if os.path.exists(thumb_path):
                        os.remove(thumb_path)
                else:
                    bot.send_message(message.chat.id, "Нажаль, відео важить більше 50 МБ (обмеження телеграму)")
                os.remove(video_path)
            except BaseException:
                bot.send_message(message.chat.id,
                                 "Введіть /yt <посилання на відео> [час старту *опціонально] [час кінця *опціонально]")
            bot.delete_message(message.chat.id, wait_msg.message_id)
        elif message.text.startswith("/ogg"):
            try:
                wait_msg = bot.send_message(message.chat.id, "Зачекайте, будь ласка")
                y = message.text.split()
                url = str(y[1])

                try:
                    audio_path = download_audio(url, max_bytes=21000000)
                except FileTooLargeError:
                    bot.send_message(message.chat.id, "Нажаль, відео важить більше 20 МБ (обмеження телеграму)")
                    bot.delete_message(message.chat.id, wait_msg.message_id)
                    return
                except RuntimeError as e:
                    bot.send_message(message.chat.id, "Не вдалося завантажити аудіо")
                    bot.send_message(550557267, "yt-dlp error:\n" + str(e)[:1000])
                    bot.delete_message(message.chat.id, wait_msg.message_id)
                    return

                voicefile = open(audio_path, "rb")
                bot.send_voice(message.chat.id, voicefile)
                voicefile.close()
                os.remove(audio_path)
            except BaseException:
                bot.send_message(message.chat.id, "Введіть /ogg [посилання на відео]")
            bot.delete_message(message.chat.id, wait_msg.message_id)
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
            url = 'https://steamcommunity.com/id/Za_XaP?xml=1'
            i = BeautifulSoup(requests.get(url).content, "xml").find("hoursOnRecord").text.replace(",", "")
            bot.send_message(message.chat.id, f"Admin has {i} hours in the last game")
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
                try:
                    history = user_histories.get(message.from_user.id, [])
                    contents = history + [message.text.strip()]

                    placeholder = bot.send_message(message.from_user.id, "💭 Думаю...")
                    state = {"last_edit": 0.0, "last_text": ""}

                    def on_update(thoughts, answer):
                        now = time.time()
                        if now - state["last_edit"] < 0.5:
                            return
                        preview = answer if answer else ("💭 " + thoughts)
                        if not preview:
                            return
                        preview = preview[-3800:]
                        if preview == state["last_text"]:
                            return
                        state["last_text"] = preview
                        state["last_edit"] = now
                        try:
                            bot.edit_message_text(preview, message.chat.id, placeholder.message_id)
                        except telebot.apihelper.ApiTelegramException:
                            pass

                    thoughts, answer = gemini_generate_content_stream(contents, on_update)
                    answer = format_ai_answer(answer)
                    ai_text = ('<pre language="thoughts">' + html.escape(thoughts) + '</pre>' + "\n\n" + answer).strip()

                    finalize_stream_message(message.chat.id, placeholder.message_id, ai_text)
                    user_histories[message.from_user.id] = contents + [ai_text]
                except BaseException:
                    bot.send_message(message.chat.id, "Функція ШІ в боті на даний момент недоступна :(")
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
