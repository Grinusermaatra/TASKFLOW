import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import (
    DB_PATH,
    add_task,
    delete_task,
    get_task_by_id,
    get_tasks,
    init_db,
    update_task,
)


class TaskDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._temp.name) / "test.db"

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_init_creates_database_and_table(self) -> None:
        init_db(self.db_path)
        self.assertTrue(self.db_path.is_file())
        self.assertFalse(DB_PATH.exists())
        connection = sqlite3.connect(self.db_path)
        try:
            columns = [
                row[1] for row in connection.execute("PRAGMA table_info(tasks)")
            ]
        finally:
            connection.close()
        self.assertEqual(
            columns,
            [
                "id",
                "title",
                "description",
                "priority",
                "status",
                "due_date",
                "created_at",
                "updated_at",
            ],
        )
        init_db(self.db_path)

    def test_add_and_list_tasks(self) -> None:
        init_db(self.db_path)
        task_id = add_task(
            "  Comprar leche  ",
            description="En el mercado",
            priority="alta",
            status="pendiente",
            due_date="2026-11-10",
            db_path=self.db_path,
        )
        tasks = get_tasks(self.db_path)
        self.assertEqual(len(tasks), 1)
        self.assertIsInstance(tasks[0], sqlite3.Row)
        self.assertEqual(tasks[0]["id"], task_id)
        self.assertEqual(tasks[0]["title"], "Comprar leche")
        self.assertEqual(tasks[0]["description"], "En el mercado")
        self.assertEqual(tasks[0]["priority"], "alta")
        self.assertEqual(tasks[0]["status"], "pendiente")
        self.assertEqual(tasks[0]["due_date"], "2026-11-10")
        self.assertTrue(tasks[0]["created_at"])
        self.assertEqual(tasks[0]["created_at"], tasks[0]["updated_at"])

    def test_get_task_by_id(self) -> None:
        init_db(self.db_path)
        task_id = add_task(
            "Escribir informe",
            priority="baja",
            status="pendiente",
            db_path=self.db_path,
        )
        row = get_task_by_id(task_id, self.db_path)
        self.assertIsNotNone(row)
        assert row is not None
        self.assertIsInstance(row, sqlite3.Row)
        self.assertEqual(row["title"], "Escribir informe")
        self.assertIsNone(get_task_by_id(9999, self.db_path))

    def test_update_task(self) -> None:
        init_db(self.db_path)
        task_id = add_task(
            "Borrador",
            priority="media",
            status="pendiente",
            db_path=self.db_path,
        )
        original = get_task_by_id(task_id, self.db_path)
        assert original is not None
        updated = update_task(
            task_id,
            title="Borrador final",
            status="en_progreso",
            priority="alta",
            db_path=self.db_path,
        )
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(updated["title"], "Borrador final")
        self.assertEqual(updated["status"], "en_progreso")
        self.assertEqual(updated["priority"], "alta")
        self.assertEqual(updated["created_at"], original["created_at"])
        self.assertNotEqual(updated["updated_at"], original["updated_at"])
        self.assertIsNone(update_task(9999, title="Nadie", db_path=self.db_path))

    def test_delete_task(self) -> None:
        init_db(self.db_path)
        task_id = add_task(
            "Borrar",
            priority="baja",
            status="completada",
            db_path=self.db_path,
        )
        self.assertTrue(delete_task(task_id, self.db_path))
        self.assertIsNone(get_task_by_id(task_id, self.db_path))
        self.assertEqual(get_tasks(self.db_path), [])
        self.assertFalse(delete_task(task_id, self.db_path))

    def test_invalid_priority(self) -> None:
        init_db(self.db_path)
        with self.assertRaises(ValueError):
            add_task(
                "Tarea",
                priority="urgente",
                status="pendiente",
                db_path=self.db_path,
            )
        self.assertEqual(get_tasks(self.db_path), [])

    def test_invalid_status(self) -> None:
        init_db(self.db_path)
        with self.assertRaises(ValueError):
            add_task(
                "Tarea",
                priority="baja",
                status="hecho",
                db_path=self.db_path,
            )
        self.assertEqual(get_tasks(self.db_path), [])

    def test_empty_title(self) -> None:
        init_db(self.db_path)
        with self.assertRaises(ValueError):
            add_task("   ", priority="baja", status="pendiente", db_path=self.db_path)
        with self.assertRaises(ValueError):
            add_task("", db_path=self.db_path)
        task_id = add_task("Visible", db_path=self.db_path)
        with self.assertRaises(ValueError):
            update_task(task_id, title="  ", db_path=self.db_path)
        self.assertEqual(get_tasks(self.db_path)[0]["title"], "Visible")


if __name__ == "__main__":
    unittest.main()
