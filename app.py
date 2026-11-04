import sqlite3
from datetime import date

import streamlit as st

import database

PRIORITY_LABELS = {
    "baja": "Baja",
    "media": "Media",
    "alta": "Alta",
}
STATUS_LABELS = {
    "pendiente": "Pendiente",
    "en_progreso": "En progreso",
    "completada": "Completada",
}
PRIORITY_COLORS = {
    "baja": "green",
    "media": "orange",
    "alta": "red",
}
STATUS_COLORS = {
    "pendiente": "gray",
    "en_progreso": "blue",
    "completada": "green",
}
SECTIONS = ("Dashboard", "Mis tareas", "Nueva tarea")


def parse_due(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def is_overdue(task: sqlite3.Row, today: date) -> bool:
    if task["status"] == "completada":
        return False
    due = parse_due(task["due_date"])
    if due is None:
        return False
    return due < today


def show_flash() -> None:
    message = st.session_state.pop("taskflow_flash", None)
    if message:
        st.success(message)


def show_dashboard(tasks: list[sqlite3.Row], today: date) -> None:
    st.header("Dashboard")
    st.write("Bienvenido a TaskFlow.")
    overdue = sum(1 for task in tasks if is_overdue(task, today))
    counts = {
        "Total": len(tasks),
        "Pendientes": sum(1 for task in tasks if task["status"] == "pendiente"),
        "En progreso": sum(1 for task in tasks if task["status"] == "en_progreso"),
        "Completadas": sum(1 for task in tasks if task["status"] == "completada"),
        "Vencidas": overdue,
    }
    labels = list(counts)
    for start in range(0, len(labels), 2):
        columns = st.columns(2)
        for column, label in zip(columns, labels[start : start + 2]):
            column.metric(label, counts[label])
    st.caption("Una tarea está vencida si tiene fecha límite anterior a hoy y no está completada.")


def task_matches(
    task: sqlite3.Row,
    query: str,
    status: str,
    priority: str,
) -> bool:
    if query and query not in task["title"].casefold():
        return False
    if status != "Todas" and task["status"] != status:
        return False
    if priority != "Todas" and task["priority"] != priority:
        return False
    return True


def render_task(task: sqlite3.Row, today: date) -> None:
    task_id = int(task["id"])
    with st.container(border=True):
        st.subheader(task["title"])
        badges = st.columns(2)
        badges[0].badge(
            PRIORITY_LABELS.get(task["priority"], task["priority"]),
            color=PRIORITY_COLORS.get(task["priority"], "gray"),
        )
        badges[1].badge(
            STATUS_LABELS.get(task["status"], task["status"]),
            color=STATUS_COLORS.get(task["status"], "gray"),
        )
        if task["description"]:
            st.write(task["description"])
        else:
            st.caption("Sin descripción")
        due = parse_due(task["due_date"])
        if due is None:
            st.caption("Sin fecha límite")
        elif is_overdue(task, today):
            st.warning(f"Fecha límite: {due.strftime('%d/%m/%Y')} (vencida)")
        else:
            st.write(f"Fecha límite: {due.strftime('%d/%m/%Y')}")

        with st.expander("Editar"):
            with st.form(f"editar-{task_id}"):
                title = st.text_input("Título", value=task["title"])
                description = st.text_area(
                    "Descripción",
                    value=task["description"] or "",
                )
                priority = st.selectbox(
                    "Prioridad",
                    database.PRIORITIES,
                    index=database.PRIORITIES.index(task["priority"])
                    if task["priority"] in database.PRIORITIES
                    else 1,
                    format_func=lambda value: PRIORITY_LABELS[value],
                )
                status = st.selectbox(
                    "Estado",
                    database.STATUSES,
                    index=database.STATUSES.index(task["status"])
                    if task["status"] in database.STATUSES
                    else 0,
                    format_func=lambda value: STATUS_LABELS[value],
                )
                due_input = st.date_input("Fecha límite", value=due)
                submitted = st.form_submit_button("Guardar cambios")
            if submitted:
                save_task(task, title, description, priority, status, due_input)

        confirmed = st.checkbox(
            "Confirmo que quiero eliminar esta tarea",
            key=f"confirmar-{task_id}",
        )
        if st.button(
            "Eliminar",
            key=f"eliminar-{task_id}",
            disabled=not confirmed,
        ):
            if not confirmed:
                return
            if database.delete_task(task_id):
                st.session_state["taskflow_flash"] = "Tarea eliminada."
                st.rerun()
            st.error("No se eliminó ninguna tarea.")


def save_task(
    task: sqlite3.Row,
    title: str,
    description: str,
    priority: str,
    status: str,
    due_input: date | None,
) -> None:
    due_date = due_input.isoformat() if due_input else None
    kept_due_date = due_input is None and bool(task["due_date"])
    try:
        updated = database.update_task(
            int(task["id"]),
            title=title,
            description=description.strip(),
            priority=priority,
            status=status,
            due_date=due_date,
        )
    except ValueError as exc:
        st.error(str(exc))
        return
    if updated is None:
        st.error("No se encontró la tarea.")
        return
    message = "Tarea actualizada."
    if kept_due_date:
        message += " La fecha límite anterior se conservó."
    st.session_state["taskflow_flash"] = message
    st.rerun()


def show_tasks(tasks: list[sqlite3.Row], today: date) -> None:
    st.header("Mis tareas")
    query = st.text_input("Buscar por título").strip().casefold()
    status = st.selectbox(
        "Estado",
        ("Todas", *database.STATUSES),
        format_func=lambda value: STATUS_LABELS.get(value, value),
    )
    priority = st.selectbox(
        "Prioridad",
        ("Todas", *database.PRIORITIES),
        format_func=lambda value: PRIORITY_LABELS.get(value, value),
    )
    visible = [
        task for task in tasks if task_matches(task, query, status, priority)
    ]
    if not tasks:
        st.info("Todavía no hay tareas. Crea la primera en Nueva tarea.")
        return
    if not visible:
        st.info("Ninguna tarea coincide con la búsqueda o los filtros.")
        return
    for task in visible:
        render_task(task, today)


def show_new_task() -> None:
    st.header("Nueva tarea")
    with st.form("nueva-tarea", clear_on_submit=True):
        title = st.text_input("Título")
        description = st.text_area("Descripción")
        priority = st.selectbox(
            "Prioridad",
            database.PRIORITIES,
            index=1,
            format_func=lambda value: PRIORITY_LABELS[value],
        )
        due = st.date_input("Fecha límite", value=None)
        submitted = st.form_submit_button("Guardar tarea")
    if not submitted:
        return
    try:
        task_id = database.add_task(
            title,
            description=description.strip() or None,
            priority=priority,
            status="pendiente",
            due_date=due.isoformat() if due else None,
        )
    except ValueError as exc:
        st.error(str(exc))
        return
    st.session_state["taskflow_flash"] = f"Tarea creada (n.º {task_id})."
    st.rerun()


def main() -> None:
    st.set_page_config(page_title="TaskFlow", layout="centered")
    database.init_db()
    st.title("TaskFlow")
    show_flash()
    st.sidebar.radio("Navegación", SECTIONS, key="seccion")
    st.sidebar.caption("Los datos se guardan en SQLite.")
    section = st.session_state["seccion"]
    today = date.today()
    if section == "Nueva tarea":
        show_new_task()
        return
    tasks = database.get_tasks()
    if section == "Dashboard":
        show_dashboard(tasks, today)
        return
    show_tasks(tasks, today)


main()
