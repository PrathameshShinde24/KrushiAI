import sqlite3
import streamlit as st
from utils.database import DB_PATH

def sign_in(email, password):
    """Verifies student credentials against the local SQLite users table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, created_at FROM users WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        # Structure mimicking the user object for app.py
        class LocalUser:
            def __init__(self, id, email, created_at):
                self.id = id
                self.email = email
                self.created_at = created_at
        
        class AuthResponse:
            def __init__(self, user):
                self.user = user
            
        return AuthResponse(LocalUser(user[0], user[1], user[2]))
    st.error("Invalid email or password.")
    return None

def sign_up(email, password, name):
    """Registers a new team member into the local database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        st.error("This email is already registered locally.")
        return False
    finally:
        conn.close()