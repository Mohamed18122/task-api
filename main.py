from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Task API",
    description="A simple CRUD API for managing tasks.",
    version="1.0"
)

tasks = [
    {"id": 1, "title": "Study", "done": False},
    {"id": 2, "title": "Gym", "done": True},
    {"id": 3, "title": "Sleep", "done": False},
]


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
    return tasks


@app.get("/tasks/{task_id}", summary="Get a task by ID")
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {task_id} not found"}
    )


@app.post("/tasks", status_code=201, summary="Create a new task")
def create_task(task: dict = Body(...)):
    title = task.get("title")

    if title is None or not isinstance(title, str) or title.strip() == "":
        return JSONResponse(
            status_code=400,
            content={"error": "Title cannot be empty"}
        )

    new_task = {
        "id": len(tasks) + 1,
        "title": title.strip(),
        "done": False
    }

    tasks.append(new_task)
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

    for task in tasks:
        if task["id"] == task_id:
            task["title"] = title.strip()
            task["done"] = done
            return task

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {task_id} not found"}
    )


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            tasks.remove(task)
            return

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {task_id} not found"}
    )