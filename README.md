# TASKFLOW

TaskFlow es un gestor de tareas sencillo. Usa Python 3.12, Streamlit 1.66.1 y SQLite.

La base de datos es `data/taskflow.db`. Al arrancar, `app.py` llama a `init_db` en `database.py`, que crea ese archivo si no existe.

## Uso

Linux:

```bash
source .venv/bin/activate
```

Windows:

```bat
.venv\Scripts\activate
```

Después:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
