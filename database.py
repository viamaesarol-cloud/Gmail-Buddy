import sqlite3
import os

DB_PATH = "gmail.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id TEXT PRIMARY KEY,
            sender TEXT,
            sender_email TEXT,
            subject TEXT,
            date TEXT,
            snippet TEXT,
            is_read INTEGER DEFAULT 0,
            labels TEXT,
            category TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS senders (
            email TEXT PRIMARY KEY,
            name TEXT,
            count INTEGER DEFAULT 0,
            unread INTEGER DEFAULT 0,
            category TEXT DEFAULT 'unchecked'
        )
    """)

    conn.commit()
    conn.close()
    print("Database ready.")

def save_emails(emails):
    conn = get_connection()
    cursor = conn.cursor()
    for email in emails:
        cursor.execute("""
            INSERT OR REPLACE INTO emails 
            (id, sender, sender_email, subject, date, snippet, is_read, labels, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            email['id'],
            email['sender'],
            email['sender_email'],
            email['subject'],
            email['date'],
            email['snippet'],
            email['is_read'],
            email['labels'],
            email.get('category', 'unchecked')
        ))
    conn.commit()
    conn.close()

def get_senders():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sender_email, sender, COUNT(*) as count,
               SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) as unread,
               category
        FROM emails
        GROUP BY sender_email
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def set_sender_category(sender_email, category):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE emails SET category = ? WHERE sender_email = ?
    """, (category, sender_email))
    conn.commit()
    conn.close()

def get_emails_by_sender(sender_email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM emails WHERE sender_email = ? ORDER BY date DESC
    """, (sender_email,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

if __name__ == "__main__":
    init_db()

def delete_emails_from_db(sender_email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM emails WHERE sender_email = ?", (sender_email,))
    conn.commit()
    conn.close()

def init_undo_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS undo_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_email TEXT,
            message_ids TEXT,
            deleted_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_undo(sender_email, message_ids):
    import json
    from datetime import datetime
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM undo_cache WHERE sender_email = ?", (sender_email,))
    cursor.execute(
        "INSERT INTO undo_cache (sender_email, message_ids, deleted_at) VALUES (?, ?, ?)",
        (sender_email, json.dumps(message_ids), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_undo(sender_email):
    import json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT message_ids FROM undo_cache WHERE sender_email = ?", (sender_email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None

def clear_undo(sender_email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM undo_cache WHERE sender_email = ?", (sender_email,))
    conn.commit()
    conn.close()
