import telebot
# from telebot import types

from config import token_secret, password, superuser_password, host_mongo, host_pg, pg_user, pg_password, pg_dbname
from config import mongo_name
from pymongo import MongoClient
import psycopg2
from psycopg2 import Error


client = MongoClient(host_mongo)

bot = telebot.TeleBot(token_secret)

db = client[mongo_name]

users = db['users']
superusers = []


# login part

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name} используйте команду /help')


@bot.message_handler(commands=['login'])
def login(message):
    if users.count_documents({'tele_id': message.from_user.id}) > 0:
        bot.send_message(message.chat.id, 'Вы уже зарегистрированы')
    else:
        sent = bot.send_message(message.chat.id, 'Введите пароль')
        bot.register_next_step_handler(sent, log_in)


def log_in(message):
    if message.text == password:
        user = {
            'name': message.from_user.first_name,
            # 'last_name': message.from_user.last_name,
            'tele_id': message.from_user.id,
        }
        users.insert_one(user)
        bot.send_message(message.chat.id, 'Пароль верный, теперь вам доступно больше команд')
    elif message.text != password:
        bot.send_message(message.chat.id, 'Неверный пароль, попробовать еще раз - /login')


@bot.message_handler(commands=['logout'])
def log_out(message):
    if users.count_documents({'tele_id': message.from_user.id}) > 0:
        users.delete_one({'tele_id': message.from_user.id})
    else:
        bot.send_message(message.chat.id, 'Вы не зарегистрированы')

# end of login part


# admin part

@bot.message_handler(commands=['admin'])
def admin1(message):
    if message.from_user.id in superusers:
        bot.send_message(message.chat.id, 'Вы уже получили статус админ')
    else:
        sent = bot.send_message(message.chat.id, 'Введите пароль')
        bot.register_next_step_handler(sent, admin2)


def admin2(message):
    if message.text == superuser_password:
        superusers.append(message.from_user.id)
        bot.send_message(message.chat.id, 'Вы получили статус админ')
    elif message.text != superuser_password:
        bot.send_message(message.chat.id, 'Неверный пароль')


@bot.message_handler(commands=['eye'])
def eye(message):
    if message.from_user.id in superusers:
        for user in users.find({}, {'_id': 0}):
            bot.send_message(message.chat.id, f'{user}')
    else:
        bot.send_message(message.chat.id, 'нельзя')

# end of admin part


@bot.message_handler(commands=['help'])
def help_user(message):
    bot.send_message(message.chat.id, f'''
    Вот что я умею:
    /start - Приветствие
    /login - Войти в систему, открывает дополнительные команды
    /logout - Выйти из системы, доступ к дополнительным командам закроется
    /help - Список всех команд
    /todo - Посмотреть список задач 
    /create - Создать список задач
    /delete - Удалить список задач
    /update - Добавить новую задачу в список
    /remove - Удалить задачу из списка
    Список игр:
    /bigger_number - Большее число
    ''')


# to do part

@bot.message_handler(commands=['create'])
def create_todo(message):
    if users.count_documents({'tele_id': message.from_user.id}) > 0:
        try:
            conn = psycopg2.connect(dbname=pg_dbname, user=pg_user, password=pg_password, host=host_pg)
            cursor = conn.cursor()
            conn.autocommit = True
            cursor.execute(f"""SELECT COUNT(tele_id) FROM list WHERE tele_id = {message.from_user.id};""")
            count = cursor.fetchone()
            if count[0] == 0:
                empty = []
                cursor.execute(
                    f"""INSERT INTO list (tele_id, todo_list) VALUES(%s, %s)""", (message.from_user.id, empty)
                )
                bot.send_message(message.chat.id, 'Список задач создан, используйте /update чтобы добавить задачу')
                conn.commit()
            else:
                bot.send_message(message.chat.id, 'У вас уже есть список задач')
        except (Exception, Error) as error:
            print('Ошибка в postgres', error)
        finally:
            if conn:
                cursor.close()
                conn.close()
    else:
        bot.send_message(message.chat.id, 'Необходимо зарегистрироваться')


@bot.message_handler(commands=['todo'])
def todo_list(message):
    if users.count_documents({'tele_id': message.from_user.id}) > 0:
        try:
            conn = psycopg2.connect(dbname=pg_dbname, user=pg_user, password=pg_password, host=host_pg)
            cursor = conn.cursor()
            conn.autocommit = True
            cursor.execute(f"""SELECT COUNT(tele_id) FROM list WHERE tele_id = {message.from_user.id};""")
            count = cursor.fetchone()
            # print(count)
            if count[0] == 1:
                cursor.execute(
                    f"""SELECT todo_list FROM list WHERE tele_id = {message.from_user.id};"""
                )
                answer = cursor.fetchone()
                answer = answer[0]
                bot.send_message(message.chat.id, f'Ваш список задач: {answer}')
            else:
                bot.send_message(message.chat.id, 'У вас нет списка задач')
        except (Exception, Error) as error:
            print('Ошибка в postgres', error)
        finally:
            if conn:
                cursor.close()
                conn.close()
    else:
        bot.send_message(message.chat.id, 'Необходимо зарегистрироваться')


@bot.message_handler(commands=['update'])
def update_todo(message):
    if users.count_documents({'tele_id': message.from_user.id}) > 0:
        try:
            conn = psycopg2.connect(dbname=pg_dbname, user=pg_user, password=pg_password, host=host_pg)
            cursor = conn.cursor()
            conn.autocommit = True
            cursor.execute(f"""SELECT COUNT(tele_id) FROM list WHERE tele_id = {message.from_user.id};""")
            count = cursor.fetchone()
            if count[0] == 1:
                sent = bot.send_message(message.chat.id, 'Введите новую задачу')
                bot.register_next_step_handler(sent, updating_todo)
            else:
                bot.send_message(message.chat.id, 'У вас нет списка задач')
        except (Exception, Error) as error:
            print('Ошибка в postgres', error)
        finally:
            if conn:
                cursor.close()
                conn.close()
    else:
        bot.send_message(message.chat.id, 'Необходимо зарегистрироваться')


def updating_todo(message):
    try:
        conn = psycopg2.connect(dbname=pg_dbname, user=pg_user, password=pg_password, host=host_pg)
        cursor = conn.cursor()
        conn.autocommit = True
        cursor.execute(f"""SELECT todo_list FROM list WHERE tele_id = {message.from_user.id};""")
        old_list = cursor.fetchone()
        new_list = old_list[0]
        new_list.append(message.text)
        cursor.execute(f"""UPDATE list SET todo_list = %s WHERE tele_id = %s;""", (new_list, message.from_user.id))
        bot.send_message(message.chat.id, 'Новая задача добавлена')
    except (Exception, Error) as error:
        print('Ошибка в postgres', error)
    finally:
        if conn:
            cursor.close()
            conn.close()


@bot.message_handler(commands=['delete'])
def delete_todo(message):
    if users.count_documents({'tele_id': message.from_user.id}) > 0:
        try:
            conn = psycopg2.connect(dbname=pg_dbname, user=pg_user, password=pg_password, host=host_pg)
            cursor = conn.cursor()
            conn.autocommit = True
            cursor.execute(f"""SELECT COUNT(tele_id) FROM list WHERE tele_id = {message.from_user.id};""")
            count = cursor.fetchone()
            if count[0] == 1:
                cursor.execute(f"""DELETE FROM list WHERE tele_id = {message.from_user.id};""")
                bot.send_message(message.chat.id, 'Список задач удален')
            else:
                bot.send_message(message.chat.id, 'У вас нет списка задач')
        except (Exception, Error) as error:
            print('Ошибка в postgres', error)
        finally:
            if conn:
                cursor.close()
                conn.close()
    else:
        bot.send_message(message.chat.id, 'Необходимо зарегистрироваться')


@bot.message_handler(commands=['remove'])
def remove_todo(message):
    if users.count_documents({'tele_id': message.from_user.id}) > 0:
        try:
            conn = psycopg2.connect(dbname=pg_dbname, user=pg_user, password=pg_password, host=host_pg)
            cursor = conn.cursor()
            conn.autocommit = True
            cursor.execute(f"""SELECT COUNT(tele_id) FROM list WHERE tele_id = {message.from_user.id};""")
            count = cursor.fetchone()
            if count[0] == 1:
                cursor.execute(f"""SELECT todo_list FROM list WHERE tele_id = {message.from_user.id};""")
                old_list = cursor.fetchone()
                if len(old_list) > 0:
                    sent = bot.send_message(message.chat.id, 'Какую задачу нужно удалить из списка')
                    bot.register_next_step_handler(sent, removing_todo)
                else:
                    bot.send_message(message.chat.id, 'В вашем списке нет задач')
            else:
                bot.send_message(message.chat.id, 'У вас нет списка задач')
        except (Exception, Error) as error:
            print('Ошибка в postgres', error)
        finally:
            if conn:
                cursor.close()
                conn.close()
    else:
        bot.send_message(message.chat.id, 'Необходимо зарегистрироваться')


def removing_todo(message):
    try:
        conn = psycopg2.connect(dbname=pg_dbname, user=pg_user, password=pg_password, host=host_pg)
        cursor = conn.cursor()
        conn.autocommit = True
        cursor.execute(f"""SELECT todo_list FROM list WHERE tele_id = {message.from_user.id};""")
        old_list = cursor.fetchone()
        new_list = old_list[0]
        if message.text in new_list:
            new_list.remove(message.text)
            cursor.execute(f"""UPDATE list SET todo_list = %s WHERE tele_id = %s;""", (new_list, message.from_user.id))
            bot.send_message(message.chat.id, 'Задача удалена из списка')
        else:
            bot.send_message(message.chat.id, 'Такой задачи нет в списке')
    except (Exception, Error) as error:
        print('Ошибка в postgres', error)
    finally:
        if conn:
            cursor.close()
            conn.close()

# end of to do part


# useless part

@bot.message_handler(commands=['check'])
def checking(message):
    if users.count_documents({'tele_id': message.from_user.id}) > 0:
        bot.send_message(message.chat.id, 'Вы зарегистрированы')
    else:
        bot.send_message(message.chat.id, 'Необходимо зарегистрироваться')


@bot.message_handler(commands=['bigger_number'])
def game_1(message):
    sent = bot.send_message(message.chat.id, 'Напишите число, кто напишет большее, тот победил')
    bot.register_next_step_handler(sent, playing_game1)


def playing_game1(message):
    user_number = int(message.text)
    user_number += 1
    bot.send_message(message.chat.id, f'{user_number}')
    bot.send_message(message.chat.id, 'Я победил, попробовать еще раз - /bigger_number')


@bot.message_handler(content_types=['text'])
def cant_understand(message):
    bot.send_message(message.chat.id, 'Ничего не понял')

# end of useless part


bot.polling(none_stop=True)
