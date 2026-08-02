from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse


app = FastAPI(
    title="Task API",
    description="A simple CRUD API for managing tasks.",
    version="1.0"
)

from db import conn
from psycopg.rows import dict_row

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
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SELECT * FROM tasks")
        rows = cursor.fetchall()

    return rows


@app.get("/tasks/{task_id}", summary="Get a task by ID")
def get_task(task_id: int):
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "SELECT * FROM tasks WHERE id = %s",
            (task_id,)
        )
        row = cursor.fetchone()

    if row is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"}
        )

    return row


@app.post("/tasks", status_code=201, summary="Create a new task")
def create_task(task: dict = Body(...)):
    title = task.get("title")

    if title is None or not isinstance(title, str) or title.strip() == "":
        return JSONResponse(
            status_code=400,
            content={"error": "Title cannot be empty"}
        )

    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *",
            (title.strip(), False)
        )
        new_task = cursor.fetchone()

    return new_task


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

    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "UPDATE tasks SET title=%s, done=%s WHERE id=%s RETURNING *",
            (title.strip(), done, task_id)
        )
        row = cursor.fetchone()

    if row is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"}
        )

    return row


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM tasks WHERE id=%s", (task_id,))

        if cursor.rowcount == 0:
            return JSONResponse(
                status_code=404,
                content={"error": f"Task {task_id} not found"}
            )

    return