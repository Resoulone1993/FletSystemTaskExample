import threading
from flet import Page, TextField, ElevatedButton, Column, Text, SnackBar, Dropdown, dropdown, TextButton
from database import get_user_by_login, check_password, hash_password, execute_query
import flet as ft


def view_login(page: ft.Page):
    """Страница авторизации с точным центрированием."""
    # Цветовая схема
    PRIMARY_COLOR = "#4361ee"
    SECONDARY_COLOR = "#3a0ca3"
    BACKGROUND_COLOR = "#f8f9fa"
    CARD_COLOR = "#ffffff"
    TEXT_COLOR = "#212529"

    # Настройка страницы
    page.bgcolor = BACKGROUND_COLOR
    page.padding = 0
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=PRIMARY_COLOR,
            secondary=SECONDARY_COLOR,
        )
    )

    # Поля формы
    login_field = ft.TextField(
        label="Логин",
        width=300,
        border_radius=10,
        filled=True,
        bgcolor=CARD_COLOR,
        border_color=SECONDARY_COLOR,
        focused_border_color=PRIMARY_COLOR,
        prefix_icon=ft.icons.PERSON,
        on_submit=lambda e: login_click(e),
    )

    password_field = ft.TextField(
        label="Пароль",
        width=300,
        password=True,
        can_reveal_password=True,
        border_radius=10,
        filled=True,
        bgcolor=CARD_COLOR,
        border_color=SECONDARY_COLOR,
        focused_border_color=PRIMARY_COLOR,
        prefix_icon=ft.icons.LOCK,
        on_submit=lambda e: login_click(e),
    )

    # Функция входа (без изменений)
    def login_click(e):
        if page is None or getattr(page, '_closed', False):
            return

        user = get_user_by_login(login_field.value.strip())
        if not user or not check_password(password_field.value, user[2]):
            show_snack(page, "Ошибка! Неверный логин или пароль.", is_error=True)
            return

        page.current_user = user
        show_snack(page, f"Добро пожаловать, {user[3]}!")
        role = user[5]

        if hasattr(page, 'go_async'):
            page.run_task(lambda: page.go_async(f"/{role}"))
        else:
            page.go(f"/{role}")

    # Стилизованная кнопка
    def create_button(text, icon=None, on_click=None, width=300):
        return ft.ElevatedButton(
            text=text,
            icon=icon,
            on_click=on_click,
            width=width,
            style=ft.ButtonStyle(
                bgcolor=PRIMARY_COLOR,
                color=ft.colors.WHITE,
                padding=15,
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
        )

    # Создаем карточку с формой
    login_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.icons.LOGIN, size=40, color=PRIMARY_COLOR),
                            ft.Text("Авторизация", size=24, weight=ft.FontWeight.BOLD),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Divider(height=20, color="transparent"),
                    login_field,
                    password_field,
                    ft.Divider(height=20, color="transparent"),
                    create_button("Войти", ft.icons.LOGIN, login_click),
                    ft.Divider(height=10, color="transparent"),
                    ft.Row(
                        [
                            ft.Text("Нет аккаунта?", color=TEXT_COLOR),
                            ft.TextButton(
                                "Зарегистрироваться",
                                on_click=lambda e: page.go("/register") if not hasattr(page, 'go_async')
                                else page.run_task(lambda: page.go_async("/register")),
                                style=ft.ButtonStyle(color=PRIMARY_COLOR),
                            )
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=40,
            width=400,
        ),
        elevation=5,
        color=CARD_COLOR,
    )

    # Основная структура для центрирования
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(width=50),  # Левая пустая область
                login_card,
                ft.Container(width=50),  # Правая пустая область
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.center,
        expand=True,
    )


def view_register(page: Page):
    """Страница регистрации."""

    def format_login_input(e):
        value = e.control.value
        # Удаляем все дефисы для обработки
        clean_value = value.replace("-", "")

        # Вставляем дефисы в нужных позициях
        formatted = []
        for i, char in enumerate(clean_value):
            if i == 4 or i == 6:  # Дефисы после 4 и 6 символов
                formatted.append("-")
            formatted.append(char)
            if len(formatted) >= 11:  # Ограничение длины
                break

        # Обновляем значение поля
        new_value = "".join(formatted)
        if new_value != value:
            e.control.value = new_value
            e.control.update()

    login_field = TextField(
        label="XXXX-XX-XXX",
        width=400,
        on_change=format_login_input,
        hint_text="Введите номер в формате XXXX-XX-XXX",
        max_length=11  # XXXX-XX-XXX = 11 символов
    )

    password_field = TextField(label="Введите пароль", width=400, password=True, can_reveal_password=True)
    fullname_field = TextField(label="Фамилия ИО", width=400)
    phone_field = TextField(label="Телефон ХХХХ", width=400)  # Новое поле для телефона
    department_field = Dropdown(
        label="Отдел",
        width=400,
        options=[
            dropdown.Option("Руководство"),
            dropdown.Option("Финансовый отдел"),
            dropdown.Option("Отдел кадров"),
            dropdown.Option("Общий отдел"),
           # иные отделы...
        ],
    )

    def register_user(e):
        login_val = login_field.value.strip()
        password_val = password_field.value.strip()
        fullname_val = fullname_field.value.strip()
        phone_val = phone_field.value.strip()  # Получаем значение телефона
        dept_val = department_field.value

        if not all([login_val, password_val, fullname_val, dept_val, phone_val]):  # Проверяем все поля
            show_snack(page, "Ошибка! Все поля должны быть заполнены!")
            return

        if get_user_by_login(login_val):
            show_snack(page, "Ошибка! Такой логин уже существует.")
            return

        hashed_password = hash_password(password_val)
        execute_query(
            "INSERT INTO users (login, password, fullname, department, role, phone) VALUES (?, ?, ?, ?, ?, ?)",
            (login_val, hashed_password, fullname_val, dept_val, "user", phone_val),  # Добавляем телефон
        )
        show_snack(page, "Регистрация успешно выполнена!")
        page.go("/")

    return Column(
        [
            Text("Регистрация", size=20, weight="bold"),
            login_field,
            password_field,
            fullname_field,
            phone_field,  # Добавляем поле для телефона
            department_field,
            ElevatedButton("Зарегистрировать", on_click=register_user),
            TextButton("Назад к логину", on_click=lambda e: page.go("/")),
        ],
        alignment="center",
        horizontal_alignment="center",
    )

    def register_user(e):
        login_val = login_field.value.strip()
        password_val = password_field.value.strip()
        fullname_val = fullname_field.value.strip()
        dept_val = department_field.value

        if not all([login_val, password_val, fullname_val, dept_val]):
            show_snack(page, "Ошибка! Все поля должны быть заполнены!")
            return

        if get_user_by_login(login_val):
            show_snack(page, "Ошибка! Такой логин уже существует.")
            return

        hashed_password = hash_password(password_val)
        execute_query(
            "INSERT INTO users (login, password, fullname, department, role) VALUES (?, ?, ?, ?, ?)",
            (login_val, hashed_password, fullname_val, dept_val, "user"),
        )
        show_snack(page, "Регистрация успешно выполнена!")
        page.go("/")

    return Column(
        [
            Text("Регистрация", size=20, weight="bold"),
            login_field,
            password_field,
            fullname_field,
            department_field,
            ElevatedButton("Зарегистрировать", on_click=register_user),
            TextButton("Назад к логину", on_click=lambda e: page.go("/")),
        ],
        alignment="center",
        horizontal_alignment="center",
    )


def show_snack(page, message: str, is_error: bool = None):
    """Умный SnackBar с правильным определением цвета"""

    # Если is_error не указан, определяем автоматически
    if is_error is None:
        error_keywords = ["error", "ошибка", "неверно", "invalid", "fail", "Неверный"]
        is_error = any(keyword in message.lower() for keyword in error_keywords)

    # Настройки стиля
    bg_color = ft.colors.RED_700 if is_error else ft.colors.GREEN_700
    icon = ft.icons.ERROR if is_error else ft.icons.CHECK_CIRCLE
    duration = 4000 if is_error else 2000

    # Создаем SnackBar
    snack = ft.SnackBar(
        ft.Row([
            ft.Icon(icon, color=ft.colors.WHITE),
            ft.Text(message, color=ft.colors.WHITE)
        ]),
        bgcolor=bg_color,
        duration=duration,
        behavior=ft.SnackBarBehavior.FLOATING,
        elevation=30
    )

    # Показываем
    page.snack_bar = snack
    page.snack_bar.open = True
    page.update()

    # Добавляем в overlay
    if not hasattr(page, 'overlay_notifications'):
        page.overlay_notifications = ft.Stack([])
        page.overlay.append(page.overlay_notifications)

    page.overlay_notifications.controls.append(snack)
    page.update()

    # Плавное появление
    snack.opacity = 1
    page.update()

    # Автоматическое скрытие через 3 секунды
    def close():
        time.sleep(3)
        snack.opacity = 0
        page.update()
        time.sleep(0.3)  # Ждем завершения анимации
        page.overlay_notifications.controls.remove(snack)
        page.update()

    threading.Thread(target=close).start()


import flet as ft
import time


