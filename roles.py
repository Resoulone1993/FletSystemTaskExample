import time
import flet as ft
from datetime import datetime
import re
import threading
from flet import (
    Text, ElevatedButton, DataTable, DataRow, DataCell, DataColumn, Column, Row, Dropdown, dropdown, SnackBar,
    TextField, AlertDialog, TextButton, PopupMenuButton, PopupMenuItem, icons, border,colors, ListView,ButtonStyle,Container,
ScrollMode,  IconButton
)
from database import load_users, reset_password, execute_query, hash_password, check_password, load_requests, load_addresses,add_address
from requests import edit_request, delete_request, export_requests_to_csv, create_request

def view_admin_main(page):
    """Главная страница администратора."""
    users = load_users()
    requests = load_requests()
    selected_table = "пользователи"  # По умолчанию отображаем таблицу пользователей

    def show_resume_comment_dialog(comment):
        """Показать диалог с комментарием."""
        dialog = AlertDialog(
            title=Text("Комментарий"),
            content=Text(comment),
            actions=[
                TextButton("Закрыть", on_click=lambda e: setattr(page, "dialog", None)),
            ],
            open=True,
        )
        page.dialog = dialog
        page.overlay.append(dialog)
        page.update()

    def refresh_users():
        """Обновить список пользователей."""
        nonlocal users
        users = load_users()
        page.views[-1].controls[1].controls[1].rows = create_user_rows()
        page.update()

    def refresh_requests():
        """Обновить список заявок."""
        nonlocal requests
        requests = load_requests()
        page.views[-1].controls[1].controls[1].rows = create_request_rows()
        page.update()

    def create_user_rows():
        """Создать строки таблицы пользователей."""
        return [
            DataRow(
                cells=[
                    DataCell(Text(str(u[0]))),  # ID
                    DataCell(Text(u[1])),  # Логин
                    DataCell(Text(u[3])),  # ФИО
                    DataCell(Text(u[4])),  # Отдел
                    DataCell(
                        Dropdown(
                            value=u[5],
                            options=[
                                dropdown.Option("user"),
                                dropdown.Option("courier"),
                                dropdown.Option("moderator"),
                                dropdown.Option("admin"),
                            ],
                            on_change=lambda e, uid=u[0]: on_change_role(uid, e.control.value),
                            disabled=u[1] == "root",  # Запрещаем изменение роли для root
                        )
                    ),
                    DataCell(
                        Row(
                            [
                                ElevatedButton(
                                    "Сбросить пароль",
                                    on_click=lambda e, uid=u[0]: on_reset_password(uid),
                                    disabled=check_password("12345678", u[2]) or u[1] == "root",  # Запрещаем сброс пароля для root
                                ),
                                ElevatedButton(
                                    "Удалить",
                                    on_click=lambda e, uid=u[0]: on_delete_user(uid),
                                    disabled=u[1] == "root",  # Запрещаем удаление для root
                                ),
                            ]
                        )
                    ),
                ]
            )
            for u in users
        ]

    def create_request_rows():
        """Создать строки таблицы заявок."""
        return [
            DataRow(
                cells=[
                    DataCell(Text(str(r[0]))),  # ID
                    DataCell(Text(r[1] or "")),  # Дата документа
                    DataCell(Text(r[2] or "")),  # Номер документа
                    DataCell(Text(r[3] or "")),  # Отдел
                    DataCell(Text(r[4] or "")),  # Исполнитель
                    DataCell(Text(r[5] or "")),  # Телефон
                    DataCell(Text(r[6] or "")),  # Название и адрес
                    DataCell(Text(r[7] or "")),  # Срок доставки
                    DataCell(Text(r[15] or "")),  # Статус
                    DataCell(
                        Row(
                            [

                                ElevatedButton("Редактировать", on_click=lambda e, rid=r[0]: on_edit_request(rid)),
                                ElevatedButton("Удалить", on_click=lambda e, rid=r[0]: on_delete_request(rid)),
                                IconButton(
                                    icon=icons.COMMENT,
                                    on_click=lambda e, comment=r[17]: show_resume_comment_dialog(comment),
                                    visible=bool(r[17])), # Видима только если комментарий есть
                                # Остальные кнопки (редактирование, удаление)
                            ]
                        )
                    ),
                ]
            )
            for r in requests
        ]



    def on_reset_password(user_id):
        """Сбросить пароль пользователя."""
        reset_password(user_id)
        refresh_users()  # Обновляем список пользователей
        show_snack(page,"Пароль сброшен на 12345678!")

        page.update()

    def on_delete_user(user_id):
        """Удалить пользователя."""
        execute_query("DELETE FROM users WHERE id=?", (user_id,))
        refresh_users()  # Обновляем список пользователей
        show_snack(page,"Пользователь удалён!")

        page.update()

    def on_change_role(user_id, new_role):
        """Изменить роль пользователя."""
        execute_query("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
        refresh_users()  # Обновляем список пользователей
        show_snack(page,f"Роль пользователя изменена на {new_role}!")

        page.update()

        # Принудительно обновляем страницу, если роль изменена для текущего пользователя
        if page.current_user and page.current_user[0] == user_id:  # Используем индекс 0 для id
            page.go("/")  # Переход на главную страницу
            page.go("/admin")  # Возврат на страницу администратора (или другую нужную страницу)

    def on_edit_request(request_id):
        """Открыть диалог редактирования заявки."""
        print(f"Редактирование заявки с ID: {request_id}")  # Отладочный вывод

        # Получаем данные заявки из базы данных
        request = execute_query("SELECT * FROM requests WHERE id=?", (request_id,))
        if not request:
            print("Заявка не найдена!")  # Отладочный вывод
            show_snack(page,"Заявка не найдена!")

            page.update()
            return

        request = request[0]  # Извлекаем первую (и единственную) запись

        # Поля для редактирования
        doc_date_field = TextField(label="Дата документа", value=request[1])
        doc_number_field = TextField(label="Номер документа", value=request[2])
        phone_field = TextField(label="Телефон", value=request[5])
        org_address_field = TextField(label="Адрес организации", value=request[6])
        delivery_date_field = TextField(label="Срок доставки", value=request[7])

        def save_changes(e):
            """Сохранить изменения заявки."""
            edit_request(
                request_id,
                doc_date_field.value,
                doc_number_field.value,
                phone_field.value,
                org_address_field.value,
                delivery_date_field.value,
            )
            refresh_requests()  # Обновляем список заявок
            show_snack(page,"Заявка обновлена!")

            page.dialog = None  # Закрываем диалог
            dialog = None
            page.update()  # Обновляем страницу

        # Диалоговое окно для редактирования
        dialog = AlertDialog(
            title=Text("Редактировать заявку"),
            content=Column(
                [
                    doc_date_field,
                    doc_number_field,
                    phone_field,
                    org_address_field,
                    delivery_date_field,
                ]
            ),
            actions=[
                TextButton("Сохранить", on_click=save_changes),
                TextButton("Отмена", on_click=lambda e: setattr(page, "dialog", None)),
            ],
            open=True,  # Убедимся, что диалог открыт
        )

        # Добавляем диалог в корневой элемент страницы
        page.dialog = dialog
        page.update()
        print("Диалоговое окно создано и добавлено в overlay")  # Отладочный вывод

    def on_delete_request(request_id):
        """Удалить заявку."""
        delete_request(request_id)
        refresh_requests()  # Обновляем список заявок
        page.snack_bar = SnackBar(Text("Заявка удалена!"))
        page.snack_bar.open = True
        page.update()

    def on_create_request():
        """Создать новую заявку."""
        doc_date_field = TextField(label="Дата документа")
        doc_number_field = TextField(label="Номер документа")
        phone_field = TextField(label="Телефон")
        org_address_field = Dropdown(
            label="Название и адрес",
            options=[dropdown.Option("Пример 1"), dropdown.Option("Пример 2")],
        )
        delivery_date_field = TextField(label="Срок доставки")

        def save_new_request(e):
            create_request(
                doc_date_field.value,
                doc_number_field.value,
                "",  # Отдел (можно оставить пустым или добавить поле)
                "",  # Исполнитель (можно оставить пустым или добавить поле)
                phone_field.value,
                org_address_field.value,
                delivery_date_field.value,
            )
            refresh_requests()  # Обновляем список заявок
            show_snack(page,"Заявка создана!")

            page.update()

        page.dialog = AlertDialog(
            title=Text("Создать заявку"),
            content=Column(
                [doc_date_field, doc_number_field, phone_field, org_address_field, delivery_date_field]
            ),
            actions=[
                TextButton("Создать", on_click=save_new_request),
                TextButton("Отмена", on_click=lambda e: setattr(page, "dialog", None)),
            ],
        )
        page.update()

    def on_switch_table(e):
        """Переключение между таблицами."""
        nonlocal selected_table
        selected_table = e.control.text.lower()  # "Пользователи" или "Заявки"
        page.views[-1].controls[1].controls[1].columns = (
            columns_users if selected_table == "пользователи" else columns_requests
        )
        page.views[-1].controls[1].controls[1].rows = (
            create_user_rows() if selected_table == "пользователи" else create_request_rows()
        )
        page.update()

    # Столбцы для таблиц
    columns_users = [
        DataColumn(Text("ID")),
        DataColumn(Text("Логин")),
        DataColumn(Text("ФИО")),
        DataColumn(Text("Отдел")),
        DataColumn(Text("Роль")),
        DataColumn(Text("Действия")),
    ]

    columns_requests = [
        DataColumn(Text("ID")),
        DataColumn(Text("Дата документа")),
        DataColumn(Text("Номер документа")),
        DataColumn(Text("Отдел")),
        DataColumn(Text("Исполнитель")),
        DataColumn(Text("Телефон")),
        DataColumn(Text("Адрес")),
        DataColumn(Text("Срок доставки")),
        DataColumn(Text("Статус")),
        DataColumn(Text("Действия")),
    ]

    return Column(
        [
            # Верхняя панель с кнопкой меню
            Row(
                [
                    PopupMenuButton(
                        items=[
                            PopupMenuItem(text="Пользователи", on_click=on_switch_table),
                            PopupMenuItem(text="Заявки", on_click=on_switch_table),
                            PopupMenuItem(text="Архив заявок", on_click=lambda e: page.go("/archive")),
                            # Добавляем пункт меню
                        ],
                        icon=icons.MENU,  # Иконка "три полоски"
                    ),
                    ElevatedButton("Выйти", on_click=lambda e: page.go("/")),
                ],
                alignment="spaceBetween",
            ),
            # Основное содержимое
            Column(
                [
                    # Кнопка "Создать заявку" только для раздела "Заявки"
                    ElevatedButton("Создать заявку", on_click=lambda e: on_create_request()) if selected_table == "заявки" else Text(""),
                    DataTable(
                        columns=columns_users if selected_table == "пользователи" else columns_requests,
                        rows=create_user_rows() if selected_table == "пользователи" else create_request_rows(),
                    ),
                ],
                expand=True,  # Занимает оставшуюся высоту
            ),
        ],
        expand=True,  # Занимает всю доступную высоту
    )
def view_user_main(page):
    """Главная страница пользователя."""
    if not page.current_user:
        page.go("/")
        return

    user = page.current_user
    requests = load_requests()
    selected_view = "Мои заявки"  # По умолчанию отображаем "Мои заявки"

    # Создаем таблицу заявок
    data_table = DataTable(
        columns=[
            DataColumn(Text("ID", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Дата\nдокумента", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Номер\nдокумента", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Отдел", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Исполнитель", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Телефон", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Адрес", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Срок\nдоставки", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Курьер", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Получено", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Отметка\nдоставки", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Второй\nэкземпляр", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Дата\nизменения", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Статус", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Действия", max_lines=3, overflow="ellipsis")),
        ],
        rows=[],
        column_spacing=10,  # Расстояние между столбцами
        horizontal_margin=10,  # Отступы по горизонтали
        heading_row_color=colors.BLUE_50,  # Цвет заголовка
        heading_row_height=80,  # Высота заголовка (увеличена для переноса текста)
    )

    def refresh_data(e=None):
        """Обновить данные и таблицу"""
        nonlocal requests
        requests = load_requests()
        data_table.rows = create_request_rows()
        show_snack(page,"Данные обновлены!")

        page.update()

    def refresh_requests():
        """Обновить список заявок."""
        nonlocal requests
        requests = load_requests()
        data_table.rows = create_request_rows()
        page.update()

    def create_request_rows():
        """Создать строки таблицы заявок."""
        if selected_view == "Мои заявки":
            filtered_requests = [r for r in requests if r[4] == user[3]]  # Фильтр по executor (ФИО пользователя)
        elif selected_view == "Заявки отдела":
            filtered_requests = [r for r in requests if r[3] == user[4]]  # Фильтр по department (отдел пользователя)
        else:
            filtered_requests = []

        return [
            DataRow(
                cells=[
                    DataCell(Text(str(r[0]))),  # ID
                    DataCell(Text(r[1] or "")),  # Дата документа
                    DataCell(Text(r[2] or "")),  # Номер документа
                    DataCell(Text(r[3] or "")),  # Отдел
                    DataCell(Text(r[4] or "")),  # Исполнитель
                    DataCell(Text(r[5] or "")),  # Телефон
                    DataCell(
                        ElevatedButton(
                            "Посмотреть адрес",
                            on_click=lambda e, addr=r[6]: show_address_dialog(addr),
                        )
                    ),  # Адрес как ссылка
                    DataCell(Text(r[7] or "")),  # Срок доставки
                    DataCell(Text(r[8] or "")),  # Курьер
                    DataCell(Text(r[9] or "")),  # Получено
                    DataCell(Text(r[10] or "")),  # Отметка доставки
                    DataCell(Text(r[11] or "")),  # Второй экземпляр
                    DataCell(Text(r[12] or "")),  # Дата изменения
                    DataCell(Text(r[13] or "")),  # Статус
                    DataCell(
                        Row(
                            [
                                # Кнопка для просмотра комментария (видима только если комментарий есть)
                                IconButton(
                                    icon=icons.COMMENT,
                                    on_click=lambda e, comment=r[15]: show_resume_comment_dialog(comment),
                                    visible=bool(r[15]),  # Видима только если комментарий есть
                                ),
                                # Остальные кнопки (редактирование, подтверждение и т.д.)
                                IconButton(
                                    icon=icons.EDIT,
                                    on_click=lambda e, rid=r[0]: on_edit_request(rid),
                                    disabled=r[13] in ["Заявка выполнена", "Заявка закрыта","В работе","Возобновлено"]
                                ),
                                IconButton(
                                    icon=icons.CHECK,
                                    on_click=lambda e, rid=r[0]: on_confirm_second_copy(rid),
                                    disabled=not (r[13] == "В работе" and r[9] == "Получен" and r[10] == "Доставлено"),
                                ),
                                IconButton(
                                    icon=icons.REFRESH,
                                    on_click=lambda e, rid=r[0]: on_resume_request_dialog(rid),
                                    disabled=not (r[13] == "В работе" and r[9] == "Не получен"),
                                ),
                            ]
                        )
                    ),
                ],
                color=(
                    colors.BLUE_100 if r[13] == "Новая заявка"
                    else colors.ORANGE_100 if r[13] == "В работе"
                    else colors.GREEN_100 if r[13] == "Заявка выполнена"
                    else None
                ),
            )
            for r in filtered_requests
        ]

    def on_resume_request(request_id, comment):
        """Возобновить заявку с комментарием."""
        try:
            # Получаем данные текущего пользователя
            user_data = page.current_user  # Предполагаем, что user_data - это кортеж (id, login, password, fullname, ...)
            user_name = user_data[3] if len(user_data) > 3 else "Неизвестный пользователь"

            # Получаем текущие данные заявки
            request_data = execute_query(
                "SELECT resume_count, comment FROM requests WHERE id=?",
                (request_id,)
            )

            if not request_data:
                show_snack(page, "Заявка не найдена", is_error=True)
                return

            resume_count, current_comment = request_data[0]
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Формируем новый комментарий с сохранением истории
            new_comment = f"{current_comment or ''}\n{current_time} - {user_name}: {comment}"

            if resume_count < 3:
                # Обновляем заявку
                execute_query(
                    """UPDATE requests 
                    SET status=?, modified_date=?, comment=?, 
                    resume_count=resume_count + 1 
                    WHERE id=?""",
                    ("Возобновлено", current_time, new_comment.strip(), request_id),
                )
                show_snack(page, f"Заявка {request_id} возобновлена")
            else:
                # Закрываем заявку
                new_comment += f"\n{current_time} - Система: Заявка закрыта (Пользователь не выполнил условия доставки)"
                execute_query(
                    """UPDATE requests 
                    SET status=?, modified_date=?, comment=? 
                    WHERE id=?""",
                    ("Заявка закрыта", current_time, new_comment.strip(), request_id),
                )
                show_snack(page, f"Заявка {request_id} закрыта", is_error=True)

            refresh_requests()
            page.update()

        except Exception as e:
            show_snack(page, f"Ошибка: {str(e)}", is_error=True)
            page.update()

    def show_resume_comment_dialog(comment):
        """Показать диалог с комментарием."""
        show_overlay_dialog(
            page=page,
            title=f"Комментарий",
            content=Text(comment),

            confirm_text="Закрыть ",
            cancel_text=" ",
            width=650
        )

    def on_resume_request_dialog(request_id):
        """Открыть диалог для возобновления заявки."""
        # Поле для комментария
        comment_field = TextField(label="Комментарий", multiline=True)

        def confirm_resume(e):
            """Подтвердить возобновление заявки."""
            comment = comment_field.value.strip()
            if not comment:
                show_snack(page,"Комментарий не может быть пустым!")

                page.update()
                return

            on_resume_request(request_id, comment)  # Передаем request_id и comment
            refresh_requests()  # Обновляем список заявок
            show_snack(page,"Заявка возобновлена!")

            page.dialog = None  # Закрываем диалог
            page.update()

        # Диалоговое окно для возобновления заявки
        form_content = ft.Column(
            controls=[
                Column(
                    [
                        Text("Введите комментарий:"),
                        comment_field,
                    ]),
            ],
            spacing=10
        )

        show_overlay_dialog(
            page=page,
            title=f"Возобновление заявки",
            content=form_content,
            confirm_action=confirm_resume,
            confirm_text="Сохранить",
            cancel_text="Отмена",
            width=650
        )



    def show_address_dialog(address):
        """Показать диалог с адресом."""
        show_overlay_dialog(
            page=page,
            title=f"Адрес",
            content=Text(address),

            confirm_text="Закрыть ",
            cancel_text=" ",
            width=650
        )

    def on_edit_request(request_id):
        """Открыть диалог редактирования заявки."""
        request = execute_query("SELECT * FROM requests WHERE id=?", (request_id,))
        if not request:
            show_snack(page, "Заявка не найдена!")
            return

        request = request[0]

        # Функция для парсинга адресов
        def parse_addresses(address_str):
            address1 = ""
            address2 = ""
            if not address_str:
                return address1, address2

            lines = address_str.split('\n')
            for line in lines:
                if line.startswith("Адрес: "):
                    address1 = line[7:].strip()
                elif line.startswith("Адрес2: "):
                    address2 = line[8:].strip()
                elif address1 == "":
                    address1 = line.strip()
                else:
                    address2 = line.strip()
            return address1, address2

        # Парсим существующие адреса
        existing_address1, existing_address2 = parse_addresses(request[6])

        # Основные поля
        doc_date_field = TextField(label="Дата документа", value=request[1])
        doc_number_field = TextField(label="Номер документа", value=request[2])
        phone_text = Text(f"Телефон: {request[5]}")
        delivery_date_field = TextField(label="Срок доставки", value=request[7])

        # Поля для адресов
        address1_field = TextField(label="Адрес 1", value=existing_address1)
        address2_field = TextField(label="Адрес 2", value=existing_address2)

        # Изначально скрываем второе поле, если адрес не был заполнен
        address2_field.visible = bool(existing_address2)

        # Кнопка для добавления/удаления второго адреса
        toggle_address_btn = ElevatedButton(
            "Добавить второй адрес" if not existing_address2 else "Удалить второй адрес",
            on_click=lambda e: toggle_second_address()
        )

        def toggle_second_address():
            """Переключает видимость второго адресного поля"""
            if address2_field.visible:
                address2_field.visible = False
                address2_field.value = ""
                toggle_address_btn.text = "Добавить второй адрес"
            else:
                address2_field.visible = True
                toggle_address_btn.text = "Удалить второй адрес"
            page.update()

        def save_changes(e):
            """Сохраняет изменения заявки"""
            try:
                # Проверяем, что хотя бы один адрес указан
                if not address1_field.value.strip() and not address2_field.value.strip():
                    show_snack(page, "Необходимо указать хотя бы один адрес!")
                    return

                # Формируем строку с адресами
                addresses = []
                if address1_field.value.strip():
                    addresses.append(f"Адрес: {address1_field.value.strip()}")
                if address2_field.visible and address2_field.value.strip():
                    addresses.append(f"Адрес2: {address2_field.value.strip()}")

                org_address = "\n".join(addresses)

                # Обновляем заявку
                edit_request(
                    request_id,
                    doc_date_field.value,
                    doc_number_field.value,
                    request[5],  # Телефон
                    org_address,
                    delivery_date_field.value,
                )
                refresh_requests()
                show_snack(page, "Заявка успешно обновлена!", False)
                close_overlay_dialog(page)
            except Exception as ex:
                show_snack(page, f"Ошибка при сохранении: {str(ex)}")

        # Собираем форму
        form_controls = [
            doc_date_field,
            doc_number_field,
            phone_text,
            address1_field,
            address2_field,
            toggle_address_btn,
            delivery_date_field,
        ]

        form_content = ft.Column(
            controls=form_controls,
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
            height=400
        )

        show_overlay_dialog(
            page=page,
            title=f"Редактирование заявки #{request_id}",
            content=form_content,
            confirm_action=save_changes,
            confirm_text="Сохранить",
            cancel_text="Отмена"
        )



    def on_confirm_second_copy(request_id):
        """Открыть диалог подтверждения второго экземпляра."""
        print(f"Подтверждение второго экземпляра для заявки с ID: {request_id}")  # Отладочный вывод

        def confirm_ok(e):
            """Обработка нажатия на 'ОК'."""
            execute_query(
                "UPDATE requests SET status=?, second_copy_received=?, modified_date=? WHERE id=?",
                ("Заявка выполнена", "получен 2 экз.", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), request_id),
            )
            refresh_requests()  # Обновляем список заявок
            show_snack(page,"Статус заявки обновлен!")

            page.dialog = None  # Закрываем диалог
            page.update()

        def close_dialog(e):
            """Обработка закрытия диалога."""
            page.dialog = None
            page.update()

        form_content = ft.Column(
            controls=[
                Text(
            "Если вы подтверждаете завершение заявки, значит вы получили второй экземпляр!\n\n"
            "Чтобы подтвердить получение, нажмите ОК.\n"

        )
            ],
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
            height=300
        )

        # Текст для диалогового окна


        show_overlay_dialog(
            page=page,
            title=f"Подтверждение завершения заявки #{request_id}",
            content=form_content,
            confirm_action=confirm_ok,
            confirm_text="OK",
            cancel_text="Отмена"
        )

        # Диалоговое окно для подтверждения второго экземпляра


    def on_switch_view(view):
        """Переключение между видами заявок."""
        nonlocal selected_view
        selected_view = view
        data_table.rows = create_request_rows()
        page.update()

    def on_show_profile():
        """Переход на страницу профиля."""
        page.go("/profile")

    def on_create_request():
        """Переход на страницу создания заявки."""
        page.go("/create_request")

    data_table.rows = create_request_rows()

    # Обертка для таблицы с вертикальным и горизонтальным скроллом
    scrollable_table = Column(
        expand=True,  # Занимает всю доступную высоту
        scroll=True,  # Включаем скролл
    )
    scrollable_table.controls.append(data_table)  # Добавляем таблицу в Column

    return Column(
        [
            # Верхняя панель с кнопкой меню
            Row(
                [
                    PopupMenuButton(
                        items=[
                            PopupMenuItem(text="Создать заявку", on_click=lambda e: on_create_request()),
                            PopupMenuItem(text="Мои заявки", on_click=lambda e: on_switch_view("Мои заявки")),
                            PopupMenuItem(text="Заявки отдела", on_click=lambda e: on_switch_view("Заявки отдела")),
                            PopupMenuItem(text="Профиль", on_click=lambda e: on_show_profile()),
                            PopupMenuItem(text="Архив заявок", on_click=lambda e: page.go("/archive")),
                        ],
                        icon=icons.MENU,  # Иконка "три полоски"
                    ),
                    Row([
                        ElevatedButton(
                            "Обновить",
                            icon=icons.REFRESH,
                            on_click=refresh_data,
                        ),
                        ElevatedButton("Выйти", on_click=lambda e: page.go("/")),
                    ]),
                ],
                alignment="spaceBetween",
            ),
            ListView([data_table], expand=True),
        ],
        expand=True,
    )
def view_courier_main(page):
    """Главная страница курьера."""
    # Проверка авторизации
    if not page.current_user:
        page.go("/")
        return

    # Основные данные
    all_requests = load_requests()
    filtered_requests = all_requests.copy()
    selected_filter = "Все заявки"
    show_dsp_only = False
    blinking_rows = set()
    search_query = ""

    def on_search_change(e):
        nonlocal search_query
        search_query = e.control.value.lower()
        apply_filters()

    # Элементы интерфейса
    search_field = TextField(
        label="Поиск по таблице",
        hint_text="Введите текст для поиска...",
        expand=True,
        on_change=on_search_change,
        prefix_icon=icons.SEARCH,
    )

    data_table = DataTable(
        columns=[
            DataColumn(Text("ID", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Дата\nдокумента", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Номер\nдокумента", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Отдел", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Исполнитель", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Телефон", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Адрес", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Срок\nдоставки", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Курьер", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Получено", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Отметка\nдоставки", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Второй\nэкземпляр", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Дата\nизменения", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Статус", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Действия", max_lines=3, overflow="ellipsis")),
        ],
        rows=[],
        column_spacing=10,
        heading_row_color=colors.BLUE_50,
    )

    # Функции обновления данных
    def refresh_data(e=None):
        nonlocal all_requests, filtered_requests
        all_requests = load_requests()
        apply_filters()
        show_snack(page, "Данные обновлены!")
        page.update()

    def apply_filters():
        nonlocal filtered_requests, blinking_rows
        filtered_requests = all_requests.copy()

        # Применяем фильтр по статусу
        if selected_filter == "Новые заявки":
            filtered_requests = [r for r in filtered_requests if r[13] == "Новая заявка"]
        elif selected_filter == "Заявки в работе":
            filtered_requests = [r for r in filtered_requests if r[13] == "В работе"]
        elif selected_filter == "Выполненные заявки":
            filtered_requests = [r for r in filtered_requests if r[13] == "Заявка выполнена"]

        # Применяем фильтр ДСП
        if show_dsp_only:
            filtered_requests = [r for r in filtered_requests if "дсп" in (r[2] or "").lower()]

        # Применяем поиск по таблице
        if search_query:
            filtered_requests = [
                r for r in filtered_requests
                if any(search_query in str(cell).lower()
                       for cell in [r[0], r[1], r[2], r[3], r[4], r[5], r[6],
                                    r[7], r[8], r[9], r[10], r[11], r[12], r[13]])
            ]

        # Обновляем множество мигающих строк
        blinking_rows = {r[0] for r in filtered_requests
                         if "дсп" in (r[2] or "").lower()
                         and r[13] in ["Новая заявка", "Возобновлено"]}

        update_table()

    def update_table():
        data_table.rows = [
            DataRow(
                cells=[
                    DataCell(Text(str(r[0]))),  # ID
                    DataCell(Text(r[1] or "")),  # Дата документа
                    DataCell(Text(r[2] or "")),  # Номер документа
                    DataCell(Text(r[3] or "")),  # Отдел
                    DataCell(Text(r[4] or "")),  # Исполнитель
                    DataCell(Text(r[5] or "")),  # Телефон
                    DataCell(
                        ElevatedButton(
                            "Посмотреть адрес",
                            on_click=lambda e, addr=r[6]: show_address_dialog(addr),
                        )
                    ),  # Адрес как ссылка
                    DataCell(Text(r[7] or "")),  # Срок доставки
                    DataCell(Text(r[8] or "")),  # Курьер
                    DataCell(Text(r[9] or "")),  # Получено
                    DataCell(Text(r[10] or "")),  # Отметка доставки
                    DataCell(Text(r[11] or "")),  # Второй экземпляр
                    DataCell(Text(r[12] or "")),  # Дата изменения
                    DataCell(Text(r[13] or "")),  # Статус
                    DataCell(
                        Row([
                            IconButton(
                                icons.WORK,
                                on_click=lambda e, rid=r[0]: on_take_to_work(rid),
                                disabled=r[13] == "Заявка выполнена",
                            ),
                            IconButton(
                                icons.COMMENT,
                                on_click=lambda e, c=r[15]: show_comment_dialog(c),
                                visible=bool(r[15]))
                        ])
                    )
                ],
                color=get_blinking_color(r) if r[0] in blinking_rows else get_row_color(r[13])
            )
            for r in filtered_requests
        ]
        page.update()

    def get_blinking_color(request):
        """Возвращает мигающий цвет для строк с ДСП"""
        if request[0] not in blinking_rows:
            return None

        current_time = time.time()
        # Мигание с периодом 1 секунда (0.5 сек видно, 0.5 сек нет)
        if int(current_time * 2) % 2 == 0:
            return colors.YELLOW_100
        return None

    def get_row_color(status):
        """Цвет строки в зависимости от статуса (без мигания)"""
        return {
            "Новая заявка": colors.BLUE_100,
            "В работе": colors.ORANGE_100,
            "Заявка выполнена": colors.GREEN_100,
            "Возобновлено": colors.BLUE_100
        }.get(status, None)

    # Запускаем анимацию мигания
    def start_blinking():
        while True:
            # Обновляем только если страница активна
            if hasattr(page, 'controls') and data_table.rows:
                for row in data_table.rows:
                    row_id = int(row.cells[0].content.value)
                    if row_id in blinking_rows:
                        row.color = get_blinking_color(next(r for r in filtered_requests if r[0] == row_id))
                page.update()
            time.sleep(0.5)  # Частота обновления - 2 раза в секунду

    # Запускаем мигание в отдельном потоке
    import threading
    threading.Thread(target=start_blinking, daemon=True).start()

    # Диалоги (сохранены оригинальные реализации)
    def show_address_dialog(address):
        show_overlay_dialog(
            page=page,
            title="Адрес",
            content=Text(address),
            confirm_text="Закрыть",
            cancel_text="",
            width=650
        )

    def show_comment_dialog(comment):
        show_overlay_dialog(
            page=page,
            title="Комментарий",
            content=Text(comment),
            confirm_text="Закрыть",
            cancel_text="",
            width=650
        )

    # Обработка заявки (полностью сохранена оригинальная реализация)
    def on_take_to_work(request_id):
        """Взятие заявки с сохранением причин в комментарии в формате: Дата - Курьер: Комментарий"""
        try:
            # Получаем данные пользователя
            user = page.current_user
            user_c = user[3] if len(user) > 3 else "Неизвестный курьер"
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Получаем текущие данные заявки
            request = execute_query("SELECT received_mark, delivery_mark, comment FROM requests WHERE id=?",
                                    (request_id,))
            if not request:
                show_snack(page, "Заявка не найдена!", is_error=True)
                return

            request_data = request[0]
            current_received_mark = request_data[0] or " "
            current_delivery_mark = request_data[1] or " "
            current_comment = request_data[2] or ""

            # Элементы формы с текущими значениями из БД
            received_mark_field = Dropdown(
                label="Отметка о получении",
                options=[dropdown.Option("Получен"), dropdown.Option("Не получен")],
                value=current_received_mark
            )

            refusal_reason_field = TextField(label="Причина отказа", value="")

            delivery_mark_dropdown = Dropdown(
                label="Отметка о доставке",
                options=[dropdown.Option("Доставлено"), dropdown.Option("Не доставлено")],
                value=current_delivery_mark
            )

            non_delivery_reason_dropdown = Dropdown(
                label="Причина не доставки",
                options=[
                    dropdown.Option("Адресат отсутствует по указанному адресу"),
                    dropdown.Option("Адресат принимает корреспонденцию только по электронной почте"),
                    dropdown.Option("Отказ адресата от получения корреспонденции"),
                    dropdown.Option("Исполнитель вручил документ лично"),
                    dropdown.Option("Иное")

                ],
                value=""
            )

            custom_reason_field = TextField(
                label="Укажите причину",
                visible=False
            )

            def on_dropdown_change(e):
                custom_reason_field.visible = (non_delivery_reason_dropdown.value == "Иное")
                page.update()

            non_delivery_reason_dropdown.on_change = on_dropdown_change

            def save_changes(e):
                try:
                    # Формируем комментарий в нужном формате
                    new_comment_lines = []

                    if refusal_reason_field.value:
                        new_comment_lines.append(
                            f"{current_time} - {user_c}: Причина отказа - {refusal_reason_field.value}")

                    if non_delivery_reason_dropdown.value:
                        reason = non_delivery_reason_dropdown.value
                        if custom_reason_field.visible and custom_reason_field.value:
                            reason += f" ({custom_reason_field.value})"
                        new_comment_lines.append(f"{current_time} - {user_c}: Причина не доставки - {reason}")

                    updated_comment = (
                        current_comment + "\n" + "\n".join(new_comment_lines)
                        if current_comment
                        else "\n".join(new_comment_lines)
                    )

                    # Обновляем данные в БД
                    execute_query(
                        """UPDATE requests SET
                           received_mark=?,
                           delivery_mark=?,
                           modified_date=?,
                           status=?,
                           courier=?,
                           comment=?
                        WHERE id=?""",
                        (
                            received_mark_field.value,
                            delivery_mark_dropdown.value,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Заявка закрыта" if delivery_mark_dropdown.value == "Не доставлено" else "В работе",
                            user_c,
                            updated_comment.strip(),
                            request_id
                        )
                    )

                    refresh_data()
                    show_snack(page, "Данные сохранены!")
                    page.dialog = None
                    page.update()

                except Exception as e:
                    show_snack(page, f"Ошибка: {str(e)}", is_error=True)

            # Форма с текущими значениями
            form_content = Column([
                received_mark_field,
                refusal_reason_field,
                delivery_mark_dropdown,
                non_delivery_reason_dropdown,
                custom_reason_field
            ], spacing=10)

            show_overlay_dialog(
                page=page,
                title=f"Обработка заявки #{request_id}",
                content=form_content,
                confirm_action=save_changes,
                width=650
            )

        except Exception as e:
            show_snack(page, f"Ошибка открытия формы: {str(e)}", is_error=True)

    # Фильтры
    def switch_filter(e):
        nonlocal selected_filter, show_dsp_only
        selected_filter = e.control.text
        show_dsp_only = False  # Сбрасываем фильтр ДСП при выборе другого фильтра
        apply_filters()
        page.update()

    def toggle_dsp(e):
        nonlocal show_dsp_only, selected_filter
        show_dsp_only = not show_dsp_only
        if show_dsp_only:
            selected_filter = "Все заявки"  # Сбрасываем другие фильтры при включении ДСП
        apply_filters()
        page.update()

    # Инициализация
    refresh_data()



    return Column(
        [
            Row(
                [
                    PopupMenuButton(
                        items=[
                            PopupMenuItem(text="Все заявки", on_click=switch_filter),
                            PopupMenuItem(text="Новые заявки", on_click=switch_filter),
                            PopupMenuItem(text="Заявки в работе", on_click=switch_filter),
                            PopupMenuItem(text="Выполненные заявки", on_click=switch_filter),
                            PopupMenuItem(text="Профиль", on_click=lambda e: page.go("/profile")),
                            PopupMenuItem(text="Архив заявок", on_click=lambda e: page.go("/archive")),
                        ],
                        icon=icons.MENU
                    ),
                    search_field,
                    Row([
                        ElevatedButton(
                            "Только ДСП",
                            on_click=toggle_dsp,
                            style=ButtonStyle(
                                bgcolor=colors.YELLOW_100 if show_dsp_only else None
                            )
                        ),
                        ElevatedButton("Обновить", on_click=refresh_data),
                        ElevatedButton("Выйти", on_click=lambda e: page.go("/")),
                    ]),
                ],
                alignment="spaceBetween",
            ),
            ListView([data_table], expand=True)

        ],
        expand=True
    )
def view_moderator_main(page):
    """Главная страница модератора."""
    requests = load_requests()
    selected_filter = "Все заявки"

    def refresh_data(e=None):
        nonlocal requests
        requests = load_requests()
        data_table.rows = create_request_rows(requests)
        show_snack(page, "Данные обновлены!")
        page.update()
    def show_address_dialog(address):
        show_overlay_dialog(
            page=page,
            title="Адрес",
            content=Text(address),
            confirm_text="Закрыть",
            cancel_text="",
            width=650
        )

    def show_comment_dialog(comment):
        show_overlay_dialog(
            page=page,
            title="Комментарий",
            content=Text(comment),
            confirm_text="Закрыть",
            cancel_text="",
            width=650
        )

    def create_request_rows(filtered_requests):
        return [
            DataRow(
                cells=[
                    DataCell(Text(str(r[0]))),
                    DataCell(Text(r[1] or "")),
                    DataCell(Text(r[2] or "")),
                    DataCell(Text(r[3] or "")),
                    DataCell(Text(r[4] or "")),
                    DataCell(Text(r[5] or "")),
                    DataCell(
                        ElevatedButton(
                            "Посмотреть адрес",
                            on_click=lambda e, addr=r[6]: show_address_dialog(addr),
                        )
                    ),  # Адрес как ссылка
                    DataCell(Text(r[7] or "")),
                    DataCell(Text(r[8] or "")),
                    DataCell(Text(r[9] or "")),
                    DataCell(Text(r[10] or "")),
                    DataCell(Text(r[11] or "")),
                    DataCell(Text(r[12] or "")),
                    DataCell(Text(r[13] or "")),
                    DataCell(
                        Row(
                            [
                                IconButton(
                                    icon=icons.DELETE,
                                    icon_color=colors.RED,
                                    on_click=lambda e, rid=r[0]: confirm_delete_request(rid, r[13]),
                                    disabled=r[13] not in ["Новая заявка"],  # Можно удалять только новые
                                ),
                                IconButton(
                                    icon=icons.ARCHIVE,
                                    icon_color=colors.BLUE,
                                    on_click=lambda e, rid=r[0]: confirm_archive_request(rid, r[13]),

                                    # Только выполненные/закрытые
                                ),
                                IconButton(
                                    icons.COMMENT,
                                    on_click=lambda e, c=r[15]: show_comment_dialog(c),
                                    visible=bool(r[15])
                                ),
                            ]
                        )
                    ),
                ],
                color=get_row_color(r[13]),
            )
            for r in filtered_requests
        ]

    def get_row_color(status):
        return {
            "Новая заявка": colors.BLUE_100,
            "В работе": colors.ORANGE_100,
            "Заявка выполнена": colors.GREEN_100,
            "Заявка закрыта": colors.RED_100,
        }.get(status, None)

    def confirm_delete_request(request_id, status):
        if status not in ["Новая заявка"]:
            show_snack(page, "Можно удалять только новые заявки!", is_error=True)
            return

        def delete(e):
            try:
                execute_query("DELETE FROM requests WHERE id=?", (request_id,))
                refresh_data()
                page.dialog = None
                show_snack(page, "Заявка удалена!")
                page.update()
            except Exception as e:
                show_snack(page, f"Ошибка удаления: {str(e)}", is_error=True)

        show_overlay_dialog(
            page=page,
            title="Подтверждение удаления",
            content=Text("Вы уверены, что хотите удалить эту новую заявку?"),
            confirm_action=delete,
            confirm_text="Удалить",
            cancel_text="Отмена",
            width=400
        )

    def confirm_archive_request(request_id, status_from_ui):
        """Подтверждение и выполнение архивации заявки с проверкой реального статуса из БД."""
        print(f"Попытка архивации заявки {request_id}. Статус из UI: '{status_from_ui}'")

        try:
            # 1. Получаем актуальные данные из БД
            request = execute_query("SELECT status FROM requests WHERE id=?", (request_id,))
            if not request:
                show_snack(page, "Заявка не найдена!", is_error=True)
                return

            actual_status = request[0][0]
            print(f"Фактический статус из БД: '{actual_status}'")

            # 2. Проверяем, можно ли архивировать
            allowed_statuses = ["Заявка выполнена", "Заявка закрыта"]
            if actual_status not in allowed_statuses:
                error_msg = f"Заявка имеет статус '{actual_status}'. Архивация возможна только для: {', '.join(allowed_statuses)}"
                print(error_msg)
                show_snack(page, error_msg, is_error=True)
                return

            # 3. Если статус подходит - показываем диалог подтверждения
            def perform_archive(e):
                try:
                    # Получаем полные данные заявки
                    full_request = execute_query("SELECT * FROM requests WHERE id=?", (request_id,))
                    if not full_request:
                        show_snack(page, "Заявка исчезла из базы данных!", is_error=True)
                        return

                    request_data = full_request[0]
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # Формируем архивный комментарий
                    original_comment = request_data[15] if request_data[15] else ""
                    archive_comment = f"{original_comment}\n{current_time} - Архивация"

                    # Переносим в архив (исправленный SQL-запрос)
                    execute_query(
                        """INSERT INTO archived_requests (
                            doc_date, doc_number, department, executor, phone, org_name_address,
                            delivery_date, courier, received_mark, delivery_mark,
                            second_copy_received, modified_date, status,
                            resume_count, comment, archived_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            request_data[1], request_data[2], request_data[3], request_data[4],
                            request_data[5], request_data[6], request_data[7], request_data[8],
                            request_data[9], request_data[10], request_data[11], request_data[12],
                            request_data[13], request_data[14], archive_comment, current_time
                        )
                    )

                    # Удаляем из основной таблицы
                    execute_query("DELETE FROM requests WHERE id=?", (request_id,))

                    # Обновляем UI
                    refresh_data()
                    page.dialog = None
                    show_snack(page, f"Заявка #{request_id} перемещена в архив!")
                    page.update()

                except Exception as e:
                    show_snack(page, f"Ошибка при архивации: {str(e)}", is_error=True)

            # Диалог подтверждения
            show_overlay_dialog(
                page=page,
                title=f"Архивация заявки #{request_id}",
                content=Text(f"Подтвердите архивацию заявки со статусом: {actual_status}"),
                confirm_action=perform_archive,
                confirm_text="Архивировать",
                cancel_text="Отмена",
                width=450
            )

        except Exception as e:
            show_snack(page, f"Ошибка проверки статуса: {str(e)}", is_error=True)

    def on_switch_filter(filter_name):
        """Переключение между фильтрами."""
        nonlocal selected_filter
        selected_filter = filter_name

        if filter_name == "Все заявки":
            filtered_requests = requests  # Показываем все заявки
        elif filter_name == "Новые заявки":
            filtered_requests = [r for r in requests if r[13] == "Новая заявка"]
        elif filter_name == "В работе":
            filtered_requests = [r for r in requests if r[13] == "В работе"]
        elif filter_name == "Выполненные заявки":
            filtered_requests = [r for r in requests if r[13] == "Заявка выполнена"]
        elif filter_name == "Закрытые заявки":
            filtered_requests = [r for r in requests if r[13] == "Заявка закрыта"]
        elif filter_name == "архив заявок":
            filtered_requests = execute_query("SELECT * FROM archived_requests")
        else:
            filtered_requests = requests  # По умолчанию показываем все заявки

        data_table.rows = create_request_rows(filtered_requests)  # Передаем filtered_requests
        page.update()

    # Инициализация таблицы с отфильтрованными заявками
    filtered_requests = requests  # По умолчанию показываем все заявки
    data_table = DataTable(
        columns=[
            DataColumn(Text("ID", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Дата\nдокумента", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Номер\nдокумента", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Отдел", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Исполнитель", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Телефон", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Адрес", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Срок\nдоставки", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Курьер", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Получено", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Отметка\nдоставки", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Второй\nэкземпляр", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Дата\nизменения", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Статус", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Действия", max_lines=3, overflow="ellipsis")),
        ],
        rows=create_request_rows(filtered_requests),  # Передаем filtered_requests
        column_spacing=10,  # Расстояние между столбцами
        horizontal_margin=10,  # Отступы по горизонтали
        heading_row_color=colors.BLUE_50,  # Цвет заголовка
        heading_row_height=80,  # Высота заголовка (увеличена для переноса текста)
    )

    # Остальная логика view_moderator_main
    return Column(
        [
            Row(
                [
                    PopupMenuButton(
                        items=[
                            PopupMenuItem(text="Все заявки", on_click=lambda e: on_switch_filter("Все заявки")),
                            PopupMenuItem(text="Новые заявки", on_click=lambda e: on_switch_filter("Новые заявки")),
                            PopupMenuItem(text="В работе", on_click=lambda e: on_switch_filter("В работе")),
                            PopupMenuItem(text="Выполненные заявки", on_click=lambda e: on_switch_filter("Выполненные заявки")),
                            PopupMenuItem(text="Закрытые заявки", on_click=lambda e: on_switch_filter("Закрытые заявки")),
                            PopupMenuItem(text="Архив заявок", on_click=lambda e: page.go("/archive")),
                            PopupMenuItem(text="Профиль", on_click=lambda e: page.go("/profile")),
                        ],
                        icon=icons.MENU,
                    ),
                    Row([
                        ElevatedButton(
                            "Обновить",
                            icon=icons.REFRESH,
                            on_click=refresh_data,
                        ),
                        ElevatedButton("Выйти", on_click=lambda e: page.go("/")),
                    ]),


                ],
                alignment="spaceBetween",
            ),
            ListView([data_table], expand=True)
        ],
        expand=True,
    )


def view_create_request(page: ft.Page):
    """Страница создания заявки с современным дизайном."""
    from datetime import datetime
    import re

    user = page.current_user
    addresses = load_addresses()

    # Цветовая схема
    PRIMARY_COLOR = "#4361ee"
    SECONDARY_COLOR = "#3a0ca3"
    ACCENT_COLOR = "#f72585"
    BACKGROUND_COLOR = "#f8f9fa"
    CARD_COLOR = "#ffffff"
    TEXT_COLOR = "#212529"

    # Настройки страницы
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=PRIMARY_COLOR,
            secondary=SECONDARY_COLOR,
            surface=TEXT_COLOR,
        ),
        text_theme=ft.TextTheme(body_medium=ft.TextStyle(color=TEXT_COLOR))
    )
    page.bgcolor = BACKGROUND_COLOR
    page.padding = 20

    # Флаг для второго адреса
    show_second_address = False

    def is_valid_date(date_str: str) -> bool:
        try:
            datetime.strptime(date_str, "%d.%m.%Y")
            return True
        except ValueError:
            return False

    def create_date_field(label: str) -> ft.TextField:
        return ft.TextField(
            label=label,
            hint_text="ДД.ММ.ГГГГ",
            border_color=SECONDARY_COLOR,
            focused_border_color=PRIMARY_COLOR,
            text_size=14,
            border_radius=10,
            filled=True,
            bgcolor=CARD_COLOR,
            on_change=lambda e: format_date_input(e),
        )

    def format_date_input(e):
        value = e.control.value
        cleaned = re.sub(r"[^\d]", "", value)
        formatted = ""
        for i, char in enumerate(cleaned):
            if i in (2, 4):
                formatted += "."
            formatted += char
            if len(cleaned) > 8:
                formatted = formatted[:10]
        if len(formatted) == 10 and not is_valid_date(formatted):
            show_snack(page, "Некорректная дата!", is_error=True)
            formatted = ""
        e.control.value = formatted
        e.control.update()

    # Создаем стилизованные поля
    doc_number_field = ft.TextField(
        label="Номер документа",
        border_color=SECONDARY_COLOR,
        focused_border_color=PRIMARY_COLOR,
        text_size=14,
        border_radius=10,
        filled=True,
        bgcolor=CARD_COLOR,
    )

    doc_date_field = create_date_field("Дата документа")
    delivery_date_field = create_date_field("Срок доставки")

    # Стилизованная кнопка
    def create_button(text, icon=None, on_click=None, bgcolor=PRIMARY_COLOR, width=None):
        return ft.ElevatedButton(
            text=text,
            icon=icon,
            on_click=on_click,
            width=width,
            style=ft.ButtonStyle(
                bgcolor=bgcolor,
                color=ft.colors.WHITE,
                padding=20,
                shape=ft.RoundedRectangleBorder(radius=10),
                shadow_color=ft.colors.BLACK12,
                elevation=2,
            ),
        )

    # Блок адреса
    def create_address_block(title, prefix=""):
        org_field = ft.TextField(
            label=f"Название организации {prefix}",
            border_color=SECONDARY_COLOR,
            visible=False,
            text_size=14,
            border_radius=10,
            filled=True,
            bgcolor=CARD_COLOR,
        )

        addr_field = ft.TextField(
            label=f"Адрес организации {prefix}",
            border_color=SECONDARY_COLOR,
            visible=False,
            text_size=14,
            border_radius=10,
            filled=True,
            bgcolor=CARD_COLOR,
        )

        dropdown = ft.Dropdown(
            label=f"Выберите адрес {prefix}",
            options=[ft.dropdown.Option(addr[0]) for addr in addresses],
            border_color=SECONDARY_COLOR,
            text_size=14,
            border_radius=10,
            filled=True,
            bgcolor=CARD_COLOR,
        )

        toggle_btn = ft.IconButton(
            icon=ft.icons.ADD,
            icon_color=PRIMARY_COLOR,
            tooltip="Добавить новый адрес",
            on_click=lambda e: toggle_address_mode(
                org_field, addr_field, dropdown, toggle_btn),
            style=ft.ButtonStyle(
                shape=ft.CircleBorder(),
                padding=10,
            )
        )

        card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text(title, weight=ft.FontWeight.BOLD, size=16, color=PRIMARY_COLOR),
                    ft.Row([dropdown, toggle_btn], alignment=ft.MainAxisAlignment.START),
                    org_field,
                    addr_field
                ], spacing=10),
                padding=15,
            ),
            elevation=2,
            color=CARD_COLOR,
        )

        return card, dropdown, org_field, addr_field

    def toggle_address_mode(org, addr, dropdown, btn):
        if dropdown.visible:
            dropdown.visible = False
            org.visible = True
            addr.visible = True
            btn.icon = ft.icons.ARROW_BACK
            btn.tooltip = "Выбрать из списка"
        else:
            dropdown.visible = True
            org.visible = False
            addr.visible = False
            btn.icon = ft.icons.ADD
            btn.tooltip = "Добавить новый адрес"
        page.update()

    # Создаем блоки адресов
    main_address_card, address1_dropdown, org_name1, address1 = create_address_block("Основной адрес доставки")
    extra_address_card, address2_dropdown, org_name2, address2 = create_address_block("Дополнительный адрес",
                                                                                      "(необязательно)")
    extra_address_card.visible = False

    def toggle_extra_address(e):
        nonlocal show_second_address
        show_second_address = not show_second_address
        extra_address_card.visible = show_second_address
        add_extra_btn.visible = not show_second_address
        page.update()

    add_extra_btn = create_button(
        "Добавить дополнительный адрес",
        icon=ft.icons.ADD,
        on_click=toggle_extra_address,
        bgcolor=SECONDARY_COLOR,
        width=300
    )

    def save_new_request(e):
        """Создать новую заявку."""
        # Обрабатываем основной адрес
        if address1_dropdown.visible:
            main_address = address1_dropdown.value
            if not main_address:
                show_snack(page, "Необходимо выбрать основной адрес!", is_error=True)
                return
        else:
            org_name = org_name1.value.strip()
            addr = address1.value.strip()
            if not org_name or not addr:
                show_snack(page, "Для основного адреса укажите название и адрес!", is_error=True)
                return
            main_address = f"{org_name}, {addr}"
            add_address(main_address)

        # Обрабатываем дополнительный адрес (если есть)
        extra_address = None
        if show_second_address:
            if address2_dropdown.visible:
                extra_address = address2_dropdown.value
                if not extra_address:
                    show_snack(page, "Необходимо выбрать дополнительный адрес!", is_error=True)
                    return
            else:
                org_name = org_name2.value.strip()
                addr = address2.value.strip()
                if not org_name or not addr:
                    show_snack(page, "Для дополнительного адреса укажите название и адрес!", is_error=True)
                    return
                extra_address = f"{org_name}, {addr}"
                add_address(extra_address)

        # Формируем строку адресов для БД
        org_address = f"адрес: {main_address}"
        if extra_address:
            org_address += f"\nадрес2: {extra_address}"

        # Проверяем обязательные поля
        if not all([doc_number_field.value, doc_date_field.value, delivery_date_field.value]):
            show_snack(page, "Все обязательные поля должны быть заполнены!", is_error=True)
            return

        if not is_valid_date(doc_date_field.value) or not is_valid_date(delivery_date_field.value):
            show_snack(page, "Ошибка! Некорректная дата!", is_error=True)
            return

        # Получаем телефон пользователя
        user_phone = user[6] if len(user) > 6 else ""

        # Создаем заявку
        create_request(
            doc_date_field.value,
            doc_number_field.value,
            user[4],  # Отдел
            user[3],  # ФИО
            user_phone,
            org_address,
            delivery_date_field.value,
        )
        show_snack(page, "Заявка успешно создана!")
        page.go("/user")

    return ft.Column(
        [
            ft.Row(
                [
                    ft.Text("Создание заявки", size=24, weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR),
                    ft.IconButton(
                        icon=ft.icons.ARROW_BACK,
                        on_click=lambda e: page.go("/user"),
                        tooltip="Назад",
                        icon_color=PRIMARY_COLOR,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),

            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Основная информация", size=18, weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR),
                        doc_number_field,
                        ft.Row([doc_date_field, delivery_date_field], spacing=20),
                    ], spacing=15),
                    padding=20,
                ),
                elevation=2,
                color=CARD_COLOR,
            ),

            main_address_card,

            ft.Row([add_extra_btn], alignment=ft.MainAxisAlignment.CENTER),

            extra_address_card,

            ft.Row(
                [
                    create_button(
                        "Создать заявку",
                        icon=ft.icons.CHECK_CIRCLE_OUTLINE,
                        on_click=save_new_request,
                        width=200
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        ],
        spacing=20,
        scroll=ft.ScrollMode.AUTO,
    )
def get_back_route(user):
    """Возвращает маршрут для кнопки 'Назад' в зависимости от роли пользователя."""
    if user[5] == "admin":
        return "/admin"
    elif user[5] == "user":
        return "/user"
    elif user[5] == "courier":
        return "/courier"
    elif user[5] == "moderator":
        return "/moderator"
    else:
        return "/"  # По умолчанию — на главную страницу


def view_profile(page: ft.Page):
    """Страница профиля пользователя с современным дизайном."""
    user = page.current_user

    # Цветовая схема
    PRIMARY_COLOR = "#4a6fa5"
    SECONDARY_COLOR = "#166088"
    BACKGROUND_COLOR = "#f8f9fa"
    CARD_COLOR = "#ffffff"
    TEXT_COLOR = "#2d3142"

    # Настройка стилей
    page.bgcolor = BACKGROUND_COLOR
    page.padding = 20

    # Поля формы
    old_password_field = ft.TextField(
        label="Старый пароль",
        password=True,
        can_reveal_password=True,
        border_radius=10,
        filled=True,
        bgcolor=CARD_COLOR,
        border_color=SECONDARY_COLOR,
        focused_border_color=PRIMARY_COLOR,
        width=250
    )

    new_password_field = ft.TextField(
        label="Новый пароль",
        password=True,
        can_reveal_password=True,
        border_radius=10,
        filled=True,
        bgcolor=CARD_COLOR,
        border_color=SECONDARY_COLOR,
        focused_border_color=PRIMARY_COLOR,
        hint_text="Минимум 8 символов",
        width=250
    )

    phone_field = ft.TextField(
        label="Внутренний телефон (4 цифры)",
        value=user[6] if len(user) > 6 and user[6] else "",
        border_radius=10,
        filled=True,
        bgcolor=CARD_COLOR,
        border_color=SECONDARY_COLOR,
        focused_border_color=PRIMARY_COLOR,
        width=250,
        input_filter=ft.NumbersOnlyInputFilter(),
        max_length=4,
        hint_text="Только цифры"
    )

    def change_password(e):
        """Обработчик смены пароля."""
        if not check_password(old_password_field.value, user[2]):
            show_snack(page, "Ошибка! Старый пароль неверный!", is_error=True)
            return

        if len(new_password_field.value) < 8:
            show_snack(page, "Пароль должен содержать минимум 8 символов!", is_error=True)
            return

        hashed_password = hash_password(new_password_field.value)
        execute_query("UPDATE users SET password=? WHERE id=?", (hashed_password, user[0]))

        # Очищаем поля
        old_password_field.value = ""
        new_password_field.value = ""

        show_snack(page, "Пароль успешно изменён!")
        page.update()

    def change_phone(e):
        """Обработчик изменения внутреннего телефона."""
        new_phone = phone_field.value.strip()

        if not new_phone:
            show_snack(page, "Поле телефона не может быть пустым!", is_error=True)
            return

        if len(new_phone) != 4 or not new_phone.isdigit():
            show_snack(page, "Введите ровно 4 цифры для внутреннего телефона!", is_error=True)
            return

        try:
            execute_query("UPDATE users SET phone=? WHERE id=?", (new_phone, user[0]))

            # Обновляем данные пользователя
            updated_user = list(user)
            updated_user[6] = new_phone
            page.current_user = tuple(updated_user)

            show_snack(page, "Внутренний телефон успешно обновлён!")
            page.update()
        except Exception as ex:
            show_snack(page, f"Ошибка при обновлении: {str(ex)}", is_error=True)
            page.update()

    # Стилизованная карточка с информацией
    info_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.ListTile(
                    leading=ft.Icon(ft.icons.PERSON, color=PRIMARY_COLOR),
                    title=ft.Text("Основная информация", weight=ft.FontWeight.BOLD),
                ),
                ft.Divider(),
                ft.ListTile(
                    leading=ft.Icon(ft.icons.ACCOUNT_CIRCLE, color=SECONDARY_COLOR),
                    title=ft.Text("Логин"),
                    subtitle=ft.Text(user[1], style=ft.TextStyle(color=TEXT_COLOR)),
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.icons.BADGE, color=SECONDARY_COLOR),
                    title=ft.Text("ФИО"),
                    subtitle=ft.Text(user[3], style=ft.TextStyle(color=TEXT_COLOR)),
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.icons.GROUP, color=SECONDARY_COLOR),
                    title=ft.Text("Отдел"),
                    subtitle=ft.Text(user[4], style=ft.TextStyle(color=TEXT_COLOR)),
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.icons.SECURITY, color=SECONDARY_COLOR),
                    title=ft.Text("Роль"),
                    subtitle=ft.Text(user[5], style=ft.TextStyle(color=TEXT_COLOR)),
                ),
            ]),
            padding=15,
        ),
        elevation=2,
        color=CARD_COLOR,
    )

    # Стилизованная кнопка
    def create_button(text, icon=None, on_click=None, width=None):
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

    # Блок изменения телефона
    phone_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("Изменить внутренний телефон", size=16, weight=ft.FontWeight.BOLD),
                phone_field,
                create_button("Сохранить телефон", ft.icons.PHONE, change_phone, 250),
            ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20,
            width=300
        ),
        elevation=2,
        color=CARD_COLOR,
    )

    # Блок изменения пароля
    password_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("Изменить пароль", size=16, weight=ft.FontWeight.BOLD),
                old_password_field,
                new_password_field,
                create_button("Изменить пароль", ft.icons.LOCK, change_password, 250),
            ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20,
            width=300
        ),
        elevation=2,
        color=CARD_COLOR,
    )

    return ft.Column(
        [
            ft.Row(
                [
                    ft.Text("Мой профиль", size=24, weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR),
                    ft.IconButton(
                        icon=ft.icons.ARROW_BACK,
                        on_click=lambda e: page.go(get_back_route(user)),
                        icon_color=PRIMARY_COLOR,
                        tooltip="Назад",
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),

            info_card,

            ft.Row(
                [
                    phone_card,
                    password_card,
                ],
                spacing=20,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        ],
        spacing=20,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
def close_dialog(page: ft.Page):
    page.dialog.open = False
    page.update()


def show_alert(
        page: ft.Page,
        title: str,
        content: str,
        confirm_text: str = "ОК",
        cancel_text: str = None,
        on_confirm: callable = None,
        on_cancel: callable = None,
        content_padding: int = 20,
        width: int = 400
):
    """Универсальный AlertDialog для всего приложения"""

    # 1. Создаем действия (кнопки)
    actions = []

    if cancel_text:
        actions.append(
            ft.TextButton(
                cancel_text,
                style=ft.ButtonStyle(color=ft.colors.RED_700),
                on_click=lambda e: [on_cancel(e) if on_cancel else None, close_dialog(page)]
            )
        )

    actions.append(
        ft.TextButton(
            confirm_text,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.BLUE_700
            ),
            on_click=lambda e: [on_confirm(e) if on_confirm else None, close_dialog(page)]
        )
    )

    # 2. Создаем диалог с гарантированным отображением поверх всех элементов
    dialog = ft.AlertDialog(
        modal=True,  # Блокирует взаимодействие с другими элементами
        title=ft.Text(title, style=ft.TextThemeStyle.HEADLINE_MEDIUM),
        content=ft.Text(content, size=16),
        content_padding=ft.padding.all(content_padding),
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=10),
        elevation=50,  # Увеличиваем тень для лучшего выделения
        bgcolor=ft.colors.SURFACE_VARIANT,
        shadow_color=ft.colors.BLACK54,  # Более темная тень
        inset_padding=20,
        scrollable=True,
        open=True,
    )

    # 3. Настройка страницы перед показом диалога
    page.dialog = dialog

    # 4. Принудительное обновление с задержкой
    def show_dialog():
        time.sleep(0.1)  # Короткая задержка
        dialog.open = True
        page.update()

    threading.Thread(target=show_dialog).start()


def show_form_dialog(
        page: ft.Page,
        title: str,
        form_content: ft.Control,
        confirm_text: str = "Сохранить",
        cancel_text: str = "Отмена",
        on_confirm: callable = None,
        on_cancel: callable = None,
        width: int = 600,
        height: int = 400
):
    """Показывает диалог с формой поверх всех элементов"""

    def confirm_wrapper(e):
        if on_confirm:
            on_confirm(e)
        close_dialog(page)

    def cancel_wrapper(e):
        if on_cancel:
            on_cancel(e)
        close_dialog(page)

    # 1. Создаем скроллируемую область
    scrollable_content = ft.Column(
        controls=[form_content],
        scroll=ft.ScrollMode.AUTO,
        height=height,
        expand=True
    )

    # 2. Создаем диалог с повышенным elevation
    dialog = ft.AlertDialog(
        modal=True,  # Блокирует взаимодействие с другими элементами
        title=ft.Text(title, size=20, weight="bold"),
        content=ft.Container(
            content=scrollable_content,
            width=width,
            padding=20
        ),
        actions=[
            ft.TextButton(
                cancel_text,
                on_click=cancel_wrapper,
                style=ft.ButtonStyle(color=ft.colors.RED_700)
            ),
            ft.ElevatedButton(
                confirm_text,
                on_click=confirm_wrapper,
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.BLUE_700
                )
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=10),
        elevation=50,  # Увеличиваем тень
        bgcolor=ft.colors.SURFACE_VARIANT,
        shadow_color=ft.colors.BLACK54,
        inset_padding=20
    )

    # 3. Настройка страницы перед показом
    page.dialog = dialog

    # 4. Принудительное отображение с задержкой
    def ensure_visible():
        time.sleep(0.1)
        dialog.open = True
        page.update()

    threading.Thread(target=ensure_visible, daemon=True).start()


def show_overlay_dialog(
        page: ft.Page,
        title: str,
        content: ft.Control,
        confirm_action: callable = None,
        confirm_text: str = "Сохранить",
        cancel_text: str = "Отмена",
        width: int = 600
):
    """Показывает кастомный диалог поверх всех элементов через Overlay"""

    # 1. Создаем контейнер для диалога
    dialog_content = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(title, size=20, weight="bold"),
                ft.Divider(height=1),
                content,
                ft.Row(
                    controls=[
                        ft.TextButton(
                            cancel_text,
                            on_click=lambda e: close_overlay_dialog(page),
                            style=ft.ButtonStyle(color=ft.colors.RED_700)
                        ),
                        ft.ElevatedButton(
                            confirm_text,
                            on_click=lambda e: [confirm_action(e) if confirm_action else None,
                                                close_overlay_dialog(page)],
                            style=ft.ButtonStyle(
                                bgcolor=ft.colors.BLUE_700,
                                color=ft.colors.WHITE
                            )
                        )
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=10
                )
            ],
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
            height=400
        ),
        width=width,
        padding=20,
        bgcolor=ft.colors.SURFACE_VARIANT,
        border_radius=10,
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=15,
            color=ft.colors.BLACK54,
            offset=ft.Offset(0, 3)
        )
    )

    # 2. Создаем overlay с полупрозрачным фоном
    overlay = ft.Stack(
        controls=[
            # Затемненный фон
            ft.Container(
                bgcolor=ft.colors.with_opacity(0.5, ft.colors.BLACK),
                on_click=lambda e: close_overlay_dialog(page),
                expand=True
            ),
            # Центрированный диалог (используем Container с alignment вместо Center)
            ft.Container(
                content=dialog_content,
                alignment=ft.alignment.center
            )
        ],
        expand=True
    )

    # 3. Добавляем overlay на страницу
    if not hasattr(page, 'active_overlay'):
        page.active_overlay = overlay
        page.overlay.append(page.active_overlay)
    else:
        # Обновляем существующий overlay
        page.overlay.remove(page.active_overlay)
        page.active_overlay = overlay
        page.overlay.append(page.active_overlay)

    page.update()


def close_overlay_dialog(page: ft.Page):
    """Закрывает overlay диалог"""
    if hasattr(page, 'active_overlay'):
        page.overlay.remove(page.active_overlay)
        delattr(page, 'active_overlay')
        page.update()


def close_overlay_dialog(page: ft.Page):
    """Закрывает overlay диалог"""
    if hasattr(page, 'active_overlay'):
        page.overlay.remove(page.active_overlay)
        delattr(page, 'active_overlay')
        page.update()

def view_archive(page):
    """Страница архива с рабочим поиском и скроллом"""
    user = page.current_user
    all_requests = execute_query("SELECT * FROM archived_requests")
    def show_address_dialog(address):
        show_overlay_dialog(
            page=page,
            title="Адрес",
            content=Text(address),
            confirm_text="Закрыть",
            cancel_text="",
            width=650
        )

    def show_comment_dialog(comment):
        show_overlay_dialog(
            page=page,
            title="Комментарий",
            content=Text(comment),
            confirm_text="Закрыть",
            cancel_text="",
            width=650
        )


    # Строка поиска
    search_field = TextField(
        label="Поиск по архиву",
        hint_text="Введите текст для поиска...",
        expand=True,
        border_color=colors.BLUE_400,
        prefix_icon=icons.SEARCH,
    )

    # Таблица с данными
    data_table = DataTable(
        columns=[
            DataColumn(Text("ID", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Дата\nдокумента", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Номер\nдокумента", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Отдел", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Исполнитель", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Телефон", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Адрес", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Срок\nдоставки", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Курьер", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Получено", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Отметка\nдоставки", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Второй\nэкземпляр", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Дата\nизменения", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Статус", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Дата \nАрхивации", max_lines=3, overflow="ellipsis")),
            DataColumn(Text("Действия", max_lines=3, overflow="ellipsis")),
        ],
        rows=[], # Передаем filtered_requests
        column_spacing=10,  # Расстояние между столбцами
        horizontal_margin=10,  # Отступы по горизонтали
        heading_row_color=colors.BLUE_50,  # Цвет заголовка
        heading_row_height=80,  # Высота заголовка (увеличена для переноса текста)
    )

    def create_rows(requests):
        return [
            DataRow(
                cells=[
                    DataCell(Text(str(r[0]))),
                    DataCell(Text(r[1] or "")),
                    DataCell(Text(r[2] or "")),
                    DataCell(Text(r[3] or "")),
                    DataCell(Text(r[4] or "")),
                    DataCell(Text(r[5] or "")),
                    DataCell(
                        ElevatedButton(
                            "Посмотреть адрес",
                            on_click=lambda e, addr=r[6]: show_address_dialog(addr),
                        )
                    ),  # Адрес как ссылка
                    DataCell(Text(r[7] or "")),
                    DataCell(Text(r[8] or "")),
                    DataCell(Text(r[9] or "")),
                    DataCell(Text(r[10] or "")),
                    DataCell(Text(r[11] or "")),
                    DataCell(Text(r[12] or "")),
                    DataCell(Text(r[13] or "")),
                    DataCell(Text(r[16] or "")),
                    DataCell(
                        Row(
                            [


                                IconButton(
                                    icons.COMMENT,
                                    on_click=lambda e, c=r[15]: show_comment_dialog(c),
                                    visible=bool(r[15])
                                ),
                            ]
                        )
                    ),
                ],

            ) for r in requests
        ]

    def filter_table(e):
        search_text = search_field.value.lower()
        filtered = [
            r for r in all_requests
            if any(search_text in str(cell).lower()
                   for cell in r if cell is not None)
        ] if search_text else all_requests
        data_table.rows = create_rows(filtered)
        page.update()

    search_field.on_change = filter_table
    data_table.rows = create_rows(all_requests)

    # Правильная реализация прокрутки
    scrollable_content = Column(
        controls=[data_table],
        scroll=ScrollMode.AUTO,
        expand=True,
    )

    return Column(
        controls=[
            Row(
                controls=[
                    Text("Архив заявок", size=24, weight="bold"),
                    ElevatedButton("Назад", on_click=lambda e: page.go(get_back_route(user)))
                ],
                alignment="spaceBetween",
            ),
            Row(
                controls=[
                    search_field,
                    IconButton(
                        icon=icons.CLEAR,
                        on_click=lambda e: [
                            setattr(search_field, 'value', ''),
                            filter_table(e)
                        ]
                    )
                ],
                alignment="center",
            ),
            # Контейнер с фиксированной высотой и прокруткой
            Container(
                content=scrollable_content,
                height=page.window_height * 0.7,
                border=border.all(1, colors.GREY_300),
                padding=10,
                expand=True,
            )
        ],
        spacing=20,
        expand=True,
    )


def show_snack(page, message: str, is_error: bool = None):
    """Умный SnackBar с правильным определением цвета"""

    # Если is_error не указан, определяем автоматически
    if is_error is None:
        error_keywords = ["error", "ошибка", "неверно", "invalid", "fail"]
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
