import sqlite3
import streamlit as st

DB_PATH = "krushiai_local.db"

def get_db_connection():
    """Establishes a connection to the local SQLite database file."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes local tables for users and pomegranate disease scans."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Table for local User Accounts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Table for Scan History (Foreign key logic is handled in code)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            disease_type TEXT,
            confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_scan_result(user_id, disease_name, confidence):
    """Saves a single pomegranate disease analysis result to the local database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO scans (user_id, disease_type, confidence) VALUES (?, ?, ?)",
        (str(user_id), str(disease_name), float(confidence))
    )
    conn.commit()
    conn.close()
    st.toast(f"Saved locally: {disease_name}", icon="✅")

def fetch_scan_history(user_id):
    """Retrieves all previous scans for the specific student user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scans WHERE user_id = ? ORDER BY created_at DESC", (str(user_id),))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]