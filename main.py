from fastapi import FastAPI, Body, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = FastAPI(
    title="Task API",
    description="A simple CRUD API for managing tasks.",
    version="1.0"
)

security = HTTPBearer()

from db import conn, supabase
from psycopg.rows import dict_row

from pydantic import BaseModel

class AuthRequest(BaseModel):
    email: str
    password: str

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


@app.post("/auth/signup", status_code=201, summary="Sign up")
def signup(user: AuthRequest):
    if not user.email or not user.password:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and password are required"}
        )

    try:
        response = supabase.auth.sign_up(
            {
                "email": user.email,
                "password": user.password,
            }
        )

        return response.user

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )


@app.post("/auth/login", summary="Log in")
def login(user: AuthRequest):
    if not user.email or not user.password:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and password are required"}
        )

    try:
        response = supabase.auth.sign_in_with_password(
            {
                "email": user.email,
                "password": user.password,
            }
        )

        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
        }

    except Exception:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid login credentials"}
        )

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

@app.get("/public/info")
def public_info():
    return {
        "message": "Welcome stranger! This info is public."
    }


@app.get("/protected/profile")
def protected_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        response = supabase.auth.get_user(token)
        user = response.user

        return {
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at,
        }

    except Exception as e:
        return JSONResponse(
            status_code=401,
            content={"error": str(e)}
        )

        

    return