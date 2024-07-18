from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import sqlite3
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI()

DATABASE = 'bbs.db'

# データベースの初期化
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (thread_id) REFERENCES threads (id)
        )
    ''')
    conn.commit()
    conn.close()

# データモデル
class Post(BaseModel):
    id: int = None
    thread_id: int
    content: str

class Thread(BaseModel):
    id: int = None
    title: str
    posts: List[Post] = []

init_db()

# 静的ファイルの設定
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def read_index():
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/threads", response_model=Thread)
def create_thread(thread: Thread):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO threads (title) VALUES (?)', (thread.title,))
    thread_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {**thread.dict(), 'id': thread_id, 'posts': []}

@app.post("/threads/{thread_id}/posts", response_model=Post)
def create_post(thread_id: int, post: Post):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM threads WHERE id = ?', (thread_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Thread not found")
    cursor.execute('INSERT INTO posts (thread_id, content) VALUES (?, ?)', (thread_id, post.content))
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {**post.dict(), 'id': post_id}

@app.get("/threads", response_model=List[Thread])
def get_threads():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, title FROM threads')
    threads = cursor.fetchall()
    result = []
    for thread in threads:
        cursor.execute('SELECT id, thread_id, content FROM posts WHERE thread_id = ?', (thread[0],))
        posts = cursor.fetchall()
        post_list = [{'id': post[0], 'thread_id': post[1], 'content': post[2]} for post in posts]
        result.append({'id': thread[0], 'title': thread[1], 'posts': post_list})
    conn.close()
    return result

@app.get("/threads/{thread_id}", response_model=Thread)
def get_thread(thread_id: int):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, title FROM threads WHERE id = ?', (thread_id,))
    thread = cursor.fetchone()
    if thread is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Thread not found")
    cursor.execute('SELECT id, thread_id, content FROM posts WHERE thread_id = ?', (thread[0],))
    posts = cursor.fetchall()
    post_list = [{'id': post[0], 'thread_id': post[1], 'content': post[2]} for post in posts]
    conn.close()
    return {'id': thread[0], 'title': thread[1], 'posts': post_list}
