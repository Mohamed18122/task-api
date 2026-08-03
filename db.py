import os
import time
import psycopg
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

DATABASE_URL = os.getenv("DATABASE_URL")

conn = None

for i in range(10):
    try:
        conn = psycopg.connect(DATABASE_URL)
        conn.autocommit = True
        print("Connected to PostgreSQL")
        break
    except psycopg.OperationalError:
        print(f"Waiting for PostgreSQL... ({i+1}/10)")
        time.sleep(2)

if conn is None:
    raise Exception("Could not connect to PostgreSQL")

with conn.cursor() as cur:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL
        )
    """)

    cur.execute("SELECT COUNT(*) FROM tasks")
    count = cur.fetchone()[0]

    if count == 0:
        cur.executemany(
            "INSERT INTO tasks (title, done) VALUES (%s, %s)",
            [
                ("Study", False),
                ("Gym", True),
                ("Sleep", False),
            ],
        )