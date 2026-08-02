from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse
import sqlite3

app = FastAPI(
    title="Task API",
    description="A simple CRUD API for managing tasks.",
    version="1.0"
)

conn = sqlite3.connect("tasks.db", check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    done INTEGER NOT NULL
)
""")

cursor.execute("SELECT COUNT(*) FROM tasks")
count = cursor.fetchone()[0]

if count == 0:
    cursor.executemany(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        [
            ("Study", 0),
            ("Gym", 1),
            ("Sleep", 0)
        ]
    )
    conn.commit()

@app.get("/", summary="API information")
def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": [
            "/health",
            "/tasks",
            "/tasks/{task_id}"
        ]
    }


@app.get("/health", summary="Health check")
def health():
    return {"status": "ok"}


@app.get("/tasks", summary="Get all tasks")
def get_tasks():
    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "done": bool(row["done"])
        }
        for row in rows
    ]


@app.get("/tasks/{task_id}", summary="Get a task by ID")
def get_task(task_id: int):
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()

    if row is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"}
        )

    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"])
    }


@app.post("/tasks", status_code=201, summary="Create a new task")
def create_task(task: dict = Body(...)):
    title = task.get("title")

    if title is None or not isinstance(title, str) or title.strip() == "":
        return JSONResponse(
            status_code=400,
            content={"error": "Title cannot be empty"}
        )

    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (title.strip(), 0)
    )
    conn.commit()

    task_id = cursor.lastrowid

    return {
        "id": task_id,
        "title": title.strip(),
        "done": False
    }


@app.put("/tasks/{task_id}", summary="Update a task")
def update_task(task_id: int, updated_task: dict = Body(...)):
    title = updated_task.get("title")
    done = updated_task.get("done")

    if (
        title is None
        or not isinstance(title, str)
        or title.strip() == ""
        or done is None
        or not isinstance(done, bool)
    ):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid request body"}
        )

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()

    if row is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"}
        )

    cursor.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (title.strip(), int(done), task_id)
    )
    conn.commit()

    return {
        "id": task_id,
        "title": title.strip(),
        "done": done
    }


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()

    if row is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"}
        )

    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()

    return