import os
import sqlite3
import sys

import flet
import flet as ft
import socket
import asyncio
import logging
from datetime import datetime, timedelta
from auth import view_login, view_register
from roles import (
    view_admin_main,
    view_user_main,
    view_courier_main,
    view_moderator_main,
    view_create_request,
    view_profile,
    view_archive
)
from pathlib import Path
from database import init_db, execute_query



class AppState:
    def __init__(self):
        self.background_task = None
        self.should_run = True


def get_network_ip():
    """Получает локальный IP-адрес машины с несколькими fallback-вариантами"""
    try:
        # Способ 1: через подключение к публичному DNS (лучший вариант)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f"Не удалось получить IP через DNS: {e}")
        try:
            # Способ 2: через hostname
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip.startswith("127."):
                raise ValueError("Это loopback-адрес")
            return ip
        except Exception as e:
            print(f"Не удалось получить IP через hostname: {e}")
            # Способ 3: перебор всех интерфейсов
            try:
                import netifaces
                for interface in netifaces.interfaces():
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in addrs:
                        for addr in addrs[netifaces.AF_INET]:
                            ip = addr['addr']
                            if not ip.startswith("127.") and not ip.startswith("169.254"):
                                return ip
            except ImportError:
                print("Не установлен модуль netifaces")
            except Exception as e:
               print(f"Ошибка при получении IP через netifaces: {e}")

    print("Не удалось определить локальный IP, используется 0.0.0.0")
    return "0.0.0.0"  # Fallback на все интерфейсы


async def archive_completed_and_closed_requests(app_state: AppState):
    """Фоновая задача для архивации заявок"""
    while app_state.should_run:
        try:
            now = datetime.now()
            fifteen_minutes_ago = now - timedelta(days=1)
            fifteen_minutes_ago_str = fifteen_minutes_ago.strftime("%Y-%m-%d %H:%M:%S")

            requests_to_archive = execute_query(
                """SELECT * FROM requests 
                WHERE (status = 'Заявка выполнена' OR status = 'Заявка закрыта') 
                AND modified_date <= ?""",
                (fifteen_minutes_ago_str,),
            )

            for request in requests_to_archive:
                execute_query(
                    """INSERT INTO archived_requests 
                    (doc_date, doc_number, department, executor, phone, org_name_address, 
                    delivery_date, courier, received_mark, delivery_mark, 
                    second_copy_received, modified_date, status,
                    resume_count, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    request[1:],
                )
                execute_query("DELETE FROM requests WHERE id=?", (request[0],))

            await asyncio.sleep(60)

        except Exception as e:
            print(f"Ошибка архивации: {e}")
            await asyncio.sleep(60)


async def main(page: ft.Page):
    # Настройки страницы
    page.title = "Система управления заявками"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1200
    page.window_height = 800
    page.current_user = None

    # Инициализация БД
    init_db()

    # Состояние приложения
    app_state = AppState()

    async def start_background_task():
        app_state.should_run = True
        if app_state.background_task is None or app_state.background_task.done():
            app_state.background_task = asyncio.create_task(
                archive_completed_and_closed_requests(app_state)
            )

    async def stop_background_task():
        app_state.should_run = False
        if app_state.background_task and not app_state.background_task.done():
            app_state.background_task.cancel()
            try:
                await app_state.background_task
            except asyncio.CancelledError:
                pass

    def load_view(route):
        """Загрузка представления для маршрута (синхронная)"""
        view_mapping = {
            "/": view_login,
            "/register": view_register,
            "/admin": view_admin_main,
            "/user": view_user_main,
            "/courier": view_courier_main,
            "/moderator": view_moderator_main,
            "/create_request": view_create_request,
            "/profile": view_profile,
            "/archive": view_archive
        }

        view_func = view_mapping.get(route, view_login)
        return view_func(page)

    async def route_change(e):
        try:
            page.views.clear()
            view = load_view(page.route)
            page.views.append(view)
            if hasattr(page, 'update_async'):
                await page.update_async()
            else:
                page.update()
        except Exception as e:
            print(f"Ошибка при смене страницы: {e}")
            page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка: {str(e)}"))
            if hasattr(page, 'update_async'):
                await page.update_async()
            else:
                page.update()

    page.on_route_change = route_change
    page.on_dispose = lambda e: asyncio.create_task(stop_background_task())
    await start_background_task()
    if hasattr(page, 'go_async'):
        await page.go_async("/")
    else:
        page.go("/")


if __name__ == "__main__":
    # Получаем IP-адрес машины
    host_ip = get_network_ip()
    port = 8500

    print(f"Запуск сервера на http://{host_ip}:{port}")
    print(f"Приложение доступно по адресу: http://{host_ip}:{port}")
    print("Для доступа в локальной сети используйте этот адрес")
    print("Если нужно открыть доступ из интернета, настройте проброс портов на роутере")

    try:
        ft.app(
            target=main,
            view=ft.WEB_BROWSER,
            port=port,
            host=host_ip,  # Используем автоматически определенный IP
            use_color_emoji=True,
            assets_dir="assets",
            route_url_strategy="path"
        )
    except TypeError:
        sqlite3.threadsafety = 3
        # Альтернативный вариант для других версий Flet
        ft.app(
            target=main,
            view=ft.WEB_BROWSER,
            port=port,
            host=host_ip
        )

