from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from datetime import datetime
import psycopg
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

class TaskCreate(BaseModel):
    title: str = None

class TaskUpdate(BaseModel):
    title: str = None
    done: bool = None
    
class UserCredentials(BaseModel):
    email: str
    password: str

# Connect to the database via psycopg
def open_db():
    db_url = os.getenv("DATABASE_URL")
    return psycopg.connect(db_url)

# Initialize and create the database with default tasks
def init_db():
    current_time = datetime.now().isoformat()
    connection = open_db()
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS tasks (id SERIAL PRIMARY KEY, title TEXT, done BOOLEAN, created_at TEXT, updated_at TEXT)")
    cursor.execute("SELECT COUNT(*) FROM tasks")
    checker = cursor.fetchone()
    if checker[0] == 0:
        cursor.execute("INSERT INTO tasks (title, done, created_at, updated_at) VALUES ('Learn HTTP', TRUE, %s, %s)", (current_time, current_time))
        cursor.execute("INSERT INTO tasks (title, done, created_at, updated_at) VALUES ('Build API', FALSE, %s, %s)", (current_time, current_time))
        cursor.execute("INSERT INTO tasks (title, done, created_at, updated_at) VALUES ('Test with Swagger', FALSE, %s, %s)", (current_time, current_time))
    connection.commit()
    connection.close()
init_db()

@app.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}

@app.get("/health")
def health_check():
    try:
        connection = open_db()
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        connection.close()
        return{"status": "ok","db": "ok"}
    except Exception:
        return{"status": "ok","db": "down"}
    

# get all the tasks, search for a specific task(s), get filtered tasks by status
@app.get("/tasks")
def tasks(search: str = None, done: bool = None, sort: bool = None):
    connection = open_db()
    cursor = connection.cursor()
    if search is not None:
        user_search = f"%{search}%"
        cursor.execute("SELECT * FROM tasks WHERE title LIKE %s", (user_search,))
    elif done is not None:
        cursor.execute("SELECT * FROM tasks WHERE done = %s", (int(done),))
    elif sort is not None:
        cursor.execute("SELECT * FROM tasks ORDER BY title")
    else:
        cursor.execute("SELECT * FROM tasks")
    results = cursor.fetchall()
    connection.close()
    dict_results = []
    keys = ['id', 'title', 'done']
    for item in results:
        sub_dict = dict(zip(keys, item))
        sub_dict['done'] = bool(sub_dict['done'])
        dict_results.append(sub_dict)
    return dict_results

# get tasks by id
@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    connection = open_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
    result = cursor.fetchone()
    connection.close()
    
    if result is None:
            return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
        
    keys = ['id', 'title', 'done']
    sub_dict = dict(zip(keys, result))
    sub_dict['done'] = bool(sub_dict['done'])
    return sub_dict

# create new tasks
@app.post("/tasks")
def create_task(task_data: TaskCreate):
    current_time = datetime.now().isoformat()
    if task_data.title is None or task_data.title.strip() == "":
        return JSONResponse(status_code=400, content={"error": "Bad Request"})
    connection = open_db()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO tasks (title, done, created_at, updated_at) VALUES (%s, %s, %s, %s) RETURNING id", (task_data.title, False, current_time, current_time))
    connection.commit()
    current_id = cursor.fetchone()[0]
    new_task = {"id": current_id, "title": task_data.title, "done": False, "created_at": current_time, "updated_at": current_time}
    connection.close()
    return JSONResponse(status_code=201, content=new_task)

# update a selected tasks
@app.put("/tasks/{task_id}")
def update_task(task_id: int, task_data: TaskUpdate):
    current_time = datetime.now().isoformat()
    connection = open_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
    result = cursor.fetchone()
    
    if result is None:
        connection.close()
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})

    if task_data.title is not None:
        if task_data.title.strip() == "":
            connection.close()
            return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})
        new_title = task_data.title
    else:
        new_title = result[1]
        
    if task_data.done is not None:
        new_status = bool(task_data.done)
    else:
        new_status = bool(result[2])
    
    cursor.execute("UPDATE tasks SET title = %s, done = %s, updated_at = %s WHERE id = %s", (new_title, new_status, current_time ,task_id))
    connection.commit()
    connection.close()
    selected_task = {'id':task_id, 'title': new_title, 'done': new_status, 'created_at': result[3], 'updated_at': current_time}
    return JSONResponse(status_code=200, content=selected_task)

# delete a task 
@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    connection = open_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
    result = cursor.fetchone()
    if result is not None:
        cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        connection.commit()
        connection.close()
        return Response(status_code=204)
    else:
        connection.close()
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})

# get the status or total counts of the tasks
@app.get("/stats")
def get_status():
    connection = open_db()
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks")
    result = cursor.fetchone()
    connection.close()
    return {"total_tasks": result[0]}