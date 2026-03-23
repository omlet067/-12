from email import message
import os
import asyncio
import random
import g4f 
import json
import datetime
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ChatPermissions # Вот это добавилось
from aiogram.filters import Command



# --- НАСТРОЙКИ ---
TOKEN = "8429568936:AAGr-bADwYCLwylgP0etElzWlY3TLseDddM"
DB_FILE = "achievements.json"
TARGET_CHAT_ID = -1003897619286   # ID  группы
OWNER_ID = 7560933378

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Базы данных (инициализация)
user_achievements = {}
stats = {} 
warns = {} 
ai_usage = {}
casino_usage = {}
# Состояние режима тишины (по умолчанию выключен)
is_silent_mode = False

BAN_WORDS = ["муалани", "шесть семь", "амлет гандон"]

ACHIEVEMENTS = {
    "Первая кровь": "Написать 1 сообщение",
    "Флудер": "Написать 50 сообщений",
    "Король чата": "Написать 500 сообщений",
    "Собеседник": "Использовать ИИ 10 раз",
    "Лудоман": "Сыграть в казик 15 раз",
    "Удачливый": "Выбить джекпот в казике",
    "Грязный рот": "Попасться на банворде",
    "Детектив": "Посмотреть чужую инфу через .инфо",
    "Сталкер": "Посмотреть чужие ачивки через реплай",
    "Олд": "Бот запомнил твой ID"
}

# --- СИСТЕМА СОХРАНЕНИЯ ---

def save_data():
    data = {str(uid): list(achs) for uid, achs in user_achievements.items()}
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_data():
    global user_achievements
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                user_achievements = {int(uid): set(achs) for uid, achs in loaded.items()}
        except Exception as e:
            print(f"Ошибка базы: {e}")

def log_message(message: types.Message):
    try:
        with open("chat_log.txt", "a", encoding="utf-8") as f:
            time_str = datetime.datetime.now().strftime("%H:%M:%S")
            f.write(f"[{time_str}] {message.from_user.first_name} (ID:{message.from_user.id}): {message.text}\n")
    except: pass

# --- ФУНКЦИИ ПРОВЕРКИ ---

async def is_admin(message: types.Message):
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ["administrator", "creator"]
    except: return False

async def give_achievement(message: types.Message, ach_name: str):
    uid = message.from_user.id
    if uid not in user_achievements: user_achievements[uid] = set()
    if ach_name not in user_achievements[uid]:
        user_achievements[uid].add(ach_name)
        save_data()
        await message.reply(f"🏆 **ДОСТИЖЕНИЕ!**\n🎖 `{ach_name}`\n📜 {ACHIEVEMENTS[ach_name]}", parse_mode="Markdown")

# --- УПРАВЛЕНИЕ ИЗ ТЕРМИНАЛА ---

async def terminal_control():
    print("--- Пульт управления Glitch активен. Пиши текст и жми Enter ---")
    while True:
        # Читаем ввод без блокировки основного потока бота
        text = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        text = text.strip()
        if text:
            try:
                await bot.send_message(TARGET_CHAT_ID, text)
                print(f"✅ Отправлено: {text}")
            except Exception as e:
                print(f"❌ Ошибка: {e}. Проверь TARGET_CHAT_ID или права бота.")

# --- КОМАНДЫ МОДЕРАЦИИ ---

@dp.message(Command("бан", "кик", prefix="+"))
async def mod_actions(message: types.Message, command: Command):
    if not await is_admin(message) or not message.reply_to_message: return
    user = message.reply_to_message.from_user
    try:
        if command.command == "бан":
            await bot.ban_chat_member(message.chat.id, user.id)
            await message.answer(f"🔨 {user.first_name} отправлен в бан!")
        else:
            await bot.ban_chat_member(message.chat.id, user.id)
            await bot.unban_chat_member(message.chat.id, user.id)
            await message.answer(f"👢 {user.first_name} кикнут!")
    except: await message.reply("Недостаточно прав!")

@dp.message(Command("варн", prefix="+"))
async def add_warn(message: types.Message):
    if not await is_admin(message) or not message.reply_to_message: return
    uid = message.reply_to_message.from_user.id
    warns[uid] = warns.get(uid, 0) + 1
    if warns[uid] >= 3:
        await bot.ban_chat_member(message.chat.id, uid)
        await message.answer(f"🔨 Накоплено 3/3 варна. Бан!")
        warns[uid] = 0
    else:
        await message.answer(f"⚠️ Варн выдан! ({warns[uid]}/3)")

@dp.message(Command("варн", prefix="-"))
async def rem_warn(message: types.Message):
    if not await is_admin(message) or not message.reply_to_message: return
    uid = message.reply_to_message.from_user.id
    if warns.get(uid, 0) > 0:
        warns[uid] -= 1
        await message.answer(f"✅ Варн снят. ({warns[uid]}/3)")

@dp.message(Command("выход", prefix="."))
async def shutdown_bot(message: types.Message):
    # Проверяем, совпадает ли ID отправителя с твоим
    if message.from_user.id != OWNER_ID:
        return await message.reply("⛔ У тебя нет доступа к консоли создателя.")
    
    await message.answer("💤 Завершаю работу... Глитч уходит в оффлайн.")
    save_data() # Сохраняем ачивки перед выходом
    exit() # Выключает скрипт

    # --- ПАНЕЛЬ СОЗДАТЕЛЯ (ТОЛЬКО ДЛЯ OWNER_ID) ---

@dp.message(Command("выдать_ачивку", prefix="."))
async def force_achievement(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    
    # Формат команды: .выдать_ачивку 123456789 Король чата
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("⚠️ Формат: `.выдать_ачивку [ID] [Название]`")
    
    target_id = int(args[1])
    ach_name = args[2]
    
    if ach_name not in ACHIEVEMENTS:
        return await message.reply("❌ Такой ачивки не существует в списке.")
        
    if target_id not in user_achievements: 
        user_achievements[target_id] = set()
    
    user_achievements[target_id].add(ach_name)
    save_data()
    
    # Пытаемся поздравить пользователя, если бот может ему написать
    try:
        await bot.send_message(target_id, f"🎁 Создатель выдал вам достижение: **{ach_name}**!")
        await message.answer(f"✅ Ачивка `{ach_name}` выдана юзеру `{target_id}`")
    except:
        await message.answer(f"✅ Выдано в базу, но не смог отправить уведомление юзеру `{target_id}`")

@dp.message(Command("рассылка", prefix="."))
async def broadcast(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    
    text_to_send = message.text.replace(".рассылка", "").strip()
    if not text_to_send:
        return await message.reply("⚠️ Напиши текст рассылки после команды.")
    
    count = 0
    # Рассылаем всем, кто есть в нашей базе ачивок
    for user_id in user_achievements.keys():
        try:
            await bot.send_message(user_id, f"📢 **ОБЪЯВЛЕНИЕ:**\n\n{text_to_send}")
            count += 1
            await asyncio.sleep(0.05) # Защита от спам-фильтра телеграма
        except:
            continue
            
    await message.answer(f"✅ Рассылка завершена! Получили: {count} чел.")

@dp.message(Command("банлист", prefix="."))
async def show_banlist(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    
    if not warns:
        return await message.answer("Чисто! Нарушителей с варнами нет.")
        
    text = "📝 **СПИСОК НАРУШИТЕЛЕЙ (ВАРНЫ):**\n"
    for uid, count in warns.items():
        if count > 0:
            text += f"• ID: `{uid}` — **{count}/3**\n"
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("тишина", prefix="."))
async def toggle_silent_mode(message: types.Message):
    global is_silent_mode
    if message.from_user.id != OWNER_ID:
        return # Только ты можешь это делать

    is_silent_mode = not is_silent_mode
    
    if is_silent_mode:
        text = "🤐 **РЕЖИМ ТИШИНЫ ВКЛЮЧЕН!**\nТеперь говорить могут только админы. Всем остальным — приятного молчания."
    else:
        text = "🔊 **РЕЖИМ ТИШИНЫ ВЫКЛЮЧЕН.**\nСвобода слова возвращена в чат!"
    
    await message.answer(text, parse_mode="Markdown")

# --- КОМАНДА: РАЗРЕШИТЬ МЕДИА ---
@dp.message(Command("разрешить", prefix="."))
async def grant_media(message: types.Message):
    # Проверка: только ты или админы чата
    is_admin_user = (await bot.get_chat_member(message.chat.id, message.from_user.id)).status in ["administrator", "creator"]
    if message.from_user.id != OWNER_ID and not is_admin_user:
        return

    if not message.reply_to_message:
        return await message.reply("⚠️ Ответь этой командой на сообщение того, кому хочешь дать права!")

    target_user = message.reply_to_message.from_user
    
    try:
        # Устанавливаем персональные "зеленый свет" на всё медиа
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_other_messages=True, # Стикеры и GIF
                can_add_web_page_previews=True
            ),
            use_independent_chat_permissions=True
        )
        await message.answer(f"✅ Пользователю {target_user.first_name} теперь можно кидать медиа!")
    except Exception as e:
        await message.reply(f"❌ Ошибка прав: {e}")

# --- КОМАНДА: ВЕРНУТЬ ЗАПРЕТ (МУТ НА МЕДИА) ---
@dp.message(Command("запретить", prefix="."))
async def revoke_media(message: types.Message):
    is_admin_user = (await bot.get_chat_member(message.chat.id, message.from_user.id)).status in ["administrator", "creator"]
    if message.from_user.id != OWNER_ID and not is_admin_user:
        return

    if not message.reply_to_message:
        return await message.reply("⚠️ Ответь этой командой на сообщение того, кого надо ограничить!")

    target_user = message.reply_to_message.from_user
    
    try:
        # Возвращаем режим "Только текст"
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=False
            ),
            use_independent_chat_permissions=True
        )
        await message.answer(f"🚫 {target_user.first_name} снова переведен в режим 'Только текст'.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

# --- ИНФОРМАЦИЯ И КАЗИНО ---

@dp.message(Command("ачивки", prefix="."))
async def show_achs(message: types.Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    if message.reply_to_message: await give_achievement(message, "Сталкер")
    unlocked = user_achievements.get(target.id, set())
    if not unlocked: return await message.reply("Ачивок пока нет.")
    text = f"🏆 **АЧИВКИ {target.first_name.upper()}:**\n" + "\n".join([f"✅ `{a}`" for a in unlocked])
    await message.reply(text, parse_mode="Markdown")

@dp.message(Command("инфо", prefix="."))
async def get_info(message: types.Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    if message.reply_to_message: await give_achievement(message, "Детектив")
    try:
        chat = await bot.get_chat(target.id)
        bio = chat.bio or "Пусто"
    except: bio = "Скрыто"
    await message.reply(f"👤 {target.first_name}\n🆔 `{target.id}`\n📝 О себе: {bio}", parse_mode="Markdown")

@dp.message(Command("казик", prefix="+"))
async def play_casino(message: types.Message):
    uid = message.from_user.id
    
    # Считаем использование для ачивки
    casino_usage[uid] = casino_usage.get(uid, 0) + 1
    if casino_usage[uid] == 15: 
        await give_achievement(message, "Лудоман")
    
    # Генерируем результат
    icons = ["💎", "🎰", "🍋", "🍒", "🍎"]
    res = [random.choice(icons) for _ in range(3)]
    
    # Условия выигрыша
    jackpot = (res[0] == res[1] == res[2])  # Все три совпали
    small_win = (res[0] == res[1] or res[1] == res[2] or res[0] == res[2]) # Любые два совпали
    
    # Формируем ответ
    result_line = f"| {' | '.join(res)} |"
    
    if jackpot:
        await give_achievement(message, "Удачливый")
        msg = f"{result_line}\n\n🔥 **ДЖЕКПОТ!** Вы сорвали куш! 💰"
    elif small_win:
        msg = f"{result_line}\n\n✨ **ПОЧТИ!** Совпало два символа! Лови утешительный приз 💵"
    else:
        msg = f"{result_line}\n\nПроиграл... 🤡 Попробуй еще раз!"
        
    await message.reply(msg, parse_mode="Markdown")

# --- ГЛАВНЫЙ ОБРАБОТЧИК ---
@dp.message()
async def handle_everything(message: types.Message):
    global is_silent_mode
    
    # 1. ПРОВЕРКА НА ГЛОБАЛЬНЫЙ МУТ
    if is_silent_mode:
        # Проверяем, является ли автор сообщения админом или создателем
        if not await is_admin(message) and message.from_user.id != OWNER_ID:
            try:
                await message.delete() # Удаляем сообщение нарушителя тишины
                return # Выходим из функции, чтобы бот не обрабатывал текст дальше
            except:
                pass # Если нет прав на удаление, просто идем дальше
    
    # --- ДАЛЬШЕ ИДЕТ ТВОЙ ОБЫЧНЫЙ КОД (статистика, ачивки, ИИ) ---
    if not message.text: return
    log_message(message)
    # ... и так далее

@dp.message()
async def handle_everything(message: types.Message):
    if not message.text: return
    log_message(message)
    
    # Дебаг в консоль (чтобы видеть ID чатов)
    print(f"💬 {message.chat.id} | {message.from_user.first_name}: {message.text}")
    
    uid = message.from_user.id
    text_lower = message.text.lower()

    # Статистика и Олд
    if uid not in stats: stats[uid] = [message.from_user.first_name, 0]
    stats[uid][1] += 1
    await give_achievement(message, "Олд")
    if stats[uid][1] == 1: await give_achievement(message, "Первая кровь")
    if stats[uid][1] == 50: await give_achievement(message, "Флудер")

    # Бан-ворды
    if any(word in text_lower for word in BAN_WORDS):
        await give_achievement(message, "Грязный рот")
        try: await message.delete()
        except: pass
        return

    # Быстрые ответы
    responses = {"67": "подшарил!", "кто гей": "чел ниже", "окак": "ахаха угар"}
    if text_lower in responses: return await message.reply(responses[text_lower])

    # ИИ (по точкам или в ЛС)
    if message.chat.type == "private" or message.text.startswith("."):
        if message.text.startswith((".инфо", ".ачивки")): return
        try:
            ai_usage[uid] = ai_usage.get(uid, 0) + 1
            if ai_usage[uid] >= 10: await give_achievement(message, "Собеседник")
            await bot.send_chat_action(message.chat.id, "typing")
            res = await g4f.ChatCompletion.create_async(model=g4f.models.gpt_4, messages=[{"role": "user", "content": message.text.lstrip(".")}])
            await message.reply(str(res))
        except: await message.reply("ИИ приуныл...")

async def main():
    load_data()
    print("--- Glitch Bot Online ---")
    await asyncio.gather(dp.start_polling(bot), terminal_control())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Выключение...")

@dp.chat_member()
async def welcome_restrict(event: types.ChatMemberUpdated):
    # Проверяем: новый статус - участник, старый - не был в чате
    if event.new_chat_member.status == "member" and event.old_chat_member.status in ["left", "kicked", None]:
        user = event.new_chat_member.user
        
        try:
            # Накладываем ограничения
            await bot.restrict_chat_member(
                chat_id=event.chat.id,
                user_id=user.id,
                permissions=types.ChatPermissions(
                    can_send_messages=True,         
                    can_send_media_messages=False,  
                    can_send_audios=False,
                    can_send_documents=False,
                    can_send_photos=False,
                    can_send_videos=False,
                    can_send_video_notes=False,
                    can_send_voice_notes=False,
                    can_send_polls=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False
                ),
                use_independent_chat_permissions=True
            )
            
            await bot.send_message(
                event.chat.id, 
                f"👋 Привет, {user.first_name}!\nТы в режиме 'Только текст'. Чтобы кидать медиа, дождись одобрения админов или OWNER_ID."
            )
        except Exception as e:
            print(f"⚠️ Ошибка ограничения: {e}")