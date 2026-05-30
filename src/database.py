import sqlite3
import json
import os

DB_PATH = "voice_users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Create users table
    # embeddings will be stored as a JSON string of float arrays
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            embedding TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_user(name, embedding_vector):
    """Saves a new user and their voice fingerprint to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    embedding_json = json.dumps(embedding_vector.tolist() if hasattr(embedding_vector, 'tolist') else embedding_vector)
    
    cursor.execute('INSERT INTO users (name, embedding) VALUES (?, ?)', (name, embedding_json))
    conn.commit()
    conn.close()

def get_all_users():
    """Returns a list of all registered users and their parsed embeddings."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, embedding FROM users')
    rows = cursor.fetchall()
    conn.close()
    
    users = []
    for row in rows:
        users.append({
            "id": row[0],
            "name": row[1],
            "embedding": json.loads(row[2])
        })
    return users

def delete_user(user_id):
    """Deletes a user from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

# Initialize the database when the module is loaded
init_db()
