import os
import sqlite3
from venv import logger

import bcrypt
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
import asyncio
import configparser
from pathlib import Path


# Жестко задаем путь к базе данных
DB_PATH = r'Myapp\database.db'


def get_connection():
    """Создание соединения с жестко заданным путем"""
    try:
        # Проверяем доступность сетевого пути
        if DB_PATH.startswith('\\\\') and not os.path.exists(os.path.dirname(DB_PATH)):
            raise ConnectionError(f"Сетевой путь недоступен: {DB_PATH}")

        conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    except sqlite3.Error as e:
        print(f"Ошибка подключения к БД: {e}")
        raise





def init_db():
    """Инициализация базы данных."""
    conn = get_connection()
    cur = conn.cursor()

    # Таблица пользователей
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        fullname TEXT NOT NULL,
        department TEXT NOT NULL,
        role TEXT NOT NULL,
        phone TEXT
    )
    """)
    cur.execute("""
       CREATE TABLE IF NOT EXISTS notifications (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           user_id INTEGER NOT NULL,  
           message TEXT NOT NULL,     
           is_read BOOLEAN DEFAULT FALSE,  
           created_at TEXT DEFAULT CURRENT_TIMESTAMP  
    )
       """)

    # Таблица заявок
    cur.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_date TEXT,
        doc_number TEXT,
        department TEXT,
        executor TEXT,
        phone TEXT,
        org_name_address TEXT,
        delivery_date TEXT,
        courier TEXT,
        received_mark TEXT,        
        delivery_mark TEXT,       
        second_copy_received TEXT,
        modified_date TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT,
        resume_count INTEGER DEFAULT 0,
        comment TEXT
    )
    """)

    # Таблица архивных заявок
    cur.execute("""
    CREATE TABLE IF NOT EXISTS archived_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_date TEXT,
        doc_number TEXT,
        department TEXT,
        executor TEXT,
        phone TEXT,
        org_name_address TEXT,
        delivery_date TEXT,
        courier TEXT,
        received_mark TEXT,        
        delivery_mark TEXT,        
        second_copy_received TEXT,
        modified_date TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT,
        resume_count INTEGER DEFAULT 0,
        comment TEXT,
        archived_date TEXT DEFAULT CURRENT_TIMESTAMP  -- Дата архивации
    )
    """)

    # Таблица адресов
    cur.execute("""
    CREATE TABLE IF NOT EXISTS addresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        address TEXT UNIQUE NOT NULL
    )
    """)

    # Проверка наличия пользователя root
    cur.execute("SELECT * FROM users WHERE login = ?", ("root",))
    root_user = cur.fetchone()
    if not root_user:
        hashed_password = hash_password("root1")
        cur.execute("""
            INSERT INTO users (login, password, fullname, department, role, phone)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("root", hashed_password, "Root Admin", "Админ. отдел", "admin", ""))

    conn.commit()
    conn.close()

from typing import NamedTuple, Optional

class User(NamedTuple):
    """Типизированная модель пользователя."""
    id: int
    login: str
    password: str  # Захешированный пароль
    fullname: str
    department: str
    role: str  # 'admin', 'user', 'courier', 'moderator'
    phone: Optional[str] = None  # Необязательное поле

def hash_password(password: str) -> str:
    """Хеширование пароля."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed_password: str) -> bool:
    """Проверка пароля."""
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

def get_user_by_login(login: str) -> Optional[Tuple]:
    """Получить пользователя по логину."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE login=?", (login,))
    user = cursor.fetchone()
    conn.close()
    return user

def execute_query(query: str, params: Tuple = ()) -> List[Tuple]:
    """Выполнить SQL-запрос и вернуть результат."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchall()
    conn.commit()
    conn.close()
    return result

def load_users() -> List[Tuple]:
    """Загрузить всех пользователей."""
    return execute_query("SELECT * FROM users")

def load_requests(filter_str: Optional[str] = None) -> List[Tuple]:
    """Загрузить заявки с фильтрацией."""
    query = "SELECT * FROM requests"
    params = ()
    if filter_str:
        query += " WHERE doc_number LIKE ? OR executor LIKE ? OR status LIKE ?"
        params = (f"%{filter_str}%", f"%{filter_str}%", f"%{filter_str}%")
    return execute_query(query, params)

def reset_password(user_id: int):
    """Сбросить пароль пользователя."""
    hashed_password = hash_password("12345678")
    execute_query("UPDATE users SET password=? WHERE id=?", (hashed_password, user_id))



def load_addresses() -> List[str]:
    """Загрузить все адреса из базы данных."""
    return execute_query("SELECT address FROM addresses")

def add_address(address: str):
    """Добавить новый адрес в базу данных, если его еще нет."""
    # Проверяем, существует ли адрес
    existing_address = execute_query("SELECT * FROM addresses WHERE address = ?", (address,))
    if not existing_address:
        execute_query("INSERT INTO addresses (address) VALUES (?)", (address,))


def create_request(doc_date: str, doc_number: str, department: str, executor: str, phone: str, org_name_address: str, delivery_date: str):
    """Создать новую заявку."""
    execute_query(
        """INSERT INTO requests (doc_date, doc_number, department, executor, phone, org_name_address, delivery_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (doc_date, doc_number, department, executor, phone, org_name_address, delivery_date, "новая заявка"),
    )
    # Отправка уведомления администратору
    admin_user = get_user_by_login("admin")  # Пример: уведомление администратору
    if admin_user:
        create_notification(admin_user[0], f"Создана новая заявка: {doc_number}")


import asyncio
from datetime import datetime, timedelta

async def archive_completed_and_closed_requests():
    """Асинхронная задача для архивации заявок со статусами 'Заявка выполнена' и 'заявка закрыта'."""
    while True:
        try:
            # Получаем текущее время
            now = datetime.now()

            # Вычисляем время, которое было 15 минут назад
            fifteen_minutes_ago = now - timedelta(minutes=15)

            # Форматируем время для SQL-запроса
            fifteen_minutes_ago_str = fifteen_minutes_ago.strftime("%Y-%m-%d %H:%M:%S")

            # Находим заявки, которые нужно архивировать
            requests_to_archive = execute_query(
                """SELECT * FROM requests 
                WHERE (status = 'Заявка выполнена' OR status = 'заявка закрыта') 
                AND modified_date <= ?""",
                (fifteen_minutes_ago_str,),
            )

            # Перемещаем заявки в архив
            for request in requests_to_archive:
                execute_query(
                    """INSERT INTO archived_requests (
                        doc_date, doc_number, department, executor, phone, org_name_address, 
                        delivery_date, courier, received_mark, refusal_reason, delivery_mark, 
                        non_delivery_reason, second_copy_received, modified_date, status,
                        resume_count, comment
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    request[1:],  # Пропускаем первый элемент (id)
                )

                # Удаляем заявку из основной таблицы
                execute_query("DELETE FROM requests WHERE id=?", (request[0],))

            # Ждем 1 минуту перед следующей проверкой
            await asyncio.sleep(60)

        except Exception as e:
            print(f"Ошибка при архивации заявок: {e}")
            await asyncio.sleep(60)  # Ждем перед повторной попыткой 
