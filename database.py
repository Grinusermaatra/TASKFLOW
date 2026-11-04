import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# Base SQLite del proyecto: data/taskflow.db (junto a este archivo).
DB_PATH = Path(__file__).resolve().parent / "data" / "taskflow.db"

PRIORITIES = ("baja", "media", "alta")
STATUSES = ("pendiente", "en_progreso", "completada")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_title(title: str) -> str:
    if not isinstance(title, str):
        raise ValueError("El título debe ser texto")
    cleaned = title.strip()
    if not cleaned:
        raise ValueError("El título no puede estar vacío")
    return cleaned


def _validate_priority(priority: str) -> str:
    if priority not in PRIORITIES:
        raise ValueError("Prioridad inválida")
    return priority


def _validate_status(status: str) -> str:
    if status not in STATUSES:
        raise ValueError("Estado inválido")
    return status


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path: Path = DB_PATH) -> None:
    """Crea el directorio, el archivo SQLite y la tabla tasks si no existen."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = _connect(db_path)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                due_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def add_task(
    title: str,
    description: str | None = None,
    priority: str = "media",
    status: str = "pendiente",
    due_date: str | None = None,
    db_path: Path = DB_PATH,
) -> int:
    """Inserta una tarea y devuelve su id."""
    title = _validate_title(title)
    priority = _validate_priority(priority)
    status = _validate_status(status)
    timestamp = _now()
    connection = _connect(db_path)
    try:
        cursor = connection.execute(
            """
            INSERT INTO tasks (
                title, description, priority, status, due_date, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, description, priority, status, due_date, timestamp, timestamp),
        )
        connection.commit()
        return int(cursor.lastrowid)
    finally:
        connection.close()


def get_tasks(db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    """Devuelve todas las tareas, de la más antigua a la más nueva."""
    connection = _connect(db_path)
    try:
        rows = connection.execute(
            "SELECT * FROM tasks ORDER BY id"
        ).fetchall()
        return list(rows)
    finally:
        connection.close()


def get_task_by_id(task_id: int, db_path: Path = DB_PATH) -> sqlite3.Row | None:
    """Devuelve una tarea o None si no existe."""
    connection = _connect(db_path)
    try:
        return connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
    finally:
        connection.close()


def update_task(
    task_id: int,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
    db_path: Path = DB_PATH,
) -> sqlite3.Row | None:
    """Actualiza una tarea existente y refresca updated_at. None si no existe."""
    assignments: list[str] = []
    values: list[object] = []
    if title is not None:
        assignments.append("title = ?")
        values.append(_validate_title(title))
    if description is not None:
        assignments.append("description = ?")
        values.append(description)
    if priority is not None:
        assignments.append("priority = ?")
        values.append(_validate_priority(priority))
    if status is not None:
        assignments.append("status = ?")
        values.append(_validate_status(status))
    if due_date is not None:
        assignments.append("due_date = ?")
        values.append(due_date)
    assignments.append("updated_at = ?")
    values.append(_now())
    values.append(task_id)

    connection = _connect(db_path)
    try:
        existing = connection.execute(
            "SELECT id FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        if existing is None:
            return None
        connection.execute(
            f"UPDATE tasks SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        connection.commit()
        return connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
    finally:
        connection.close()


def delete_task(task_id: int, db_path: Path = DB_PATH) -> bool:
    """Borra una tarea. Devuelve True si eliminó una fila."""
    connection = _connect(db_path)
    try:
        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()
