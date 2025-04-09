from flet import TextField, Dropdown, ElevatedButton, Column, DataTable, DataRow, DataCell, DataColumn, AlertDialog, TextButton, Row
from database import execute_query

def create_request(doc_date: str, doc_number: str, department: str, executor: str, phone: str, org_name_address: str, delivery_date: str):
    """Создать новую заявку."""
    execute_query(
        """INSERT INTO requests (doc_date, doc_number, department, executor, phone, org_name_address, delivery_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (doc_date, doc_number, department, executor, phone, org_name_address, delivery_date, "Новая заявка"),
    )

def edit_request(request_id: int, doc_date: str, doc_number: str, phone: str, org_name_address: str, delivery_date: str):
    """Редактировать заявку."""
    execute_query(
        """UPDATE requests
        SET doc_date=?, doc_number=?, phone=?, org_name_address=?, delivery_date=?
        WHERE id=?""",
        (doc_date, doc_number, phone, org_name_address, delivery_date, request_id),
    )

def delete_request(request_id: int):
    """Удалить заявку."""
    execute_query("DELETE FROM requests WHERE id=?", (request_id,))

def export_requests_to_csv(filename: str = "requests.csv"):
    """Экспорт заявок в CSV."""
    import csv
    requests = execute_query("SELECT * FROM requests")
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["ID", "Номер документа", "Исполнитель", "Статус"])
        for r in requests:
            writer.writerow([r[0], r[2], r[4], r[13]])
