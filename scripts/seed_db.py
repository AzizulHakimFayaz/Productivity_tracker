import os
import sys
import sqlite3
import datetime

# Add the project root to sys.path so we can import from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.database import DatabaseManager

def seed_database():
    print("Seeding database with realistic mock data...")
    db = DatabaseManager()
    
    # Clear out all sessions to ensure a fresh chart
    db.cursor.execute('DELETE FROM activity_sessions')
    
    # Today's date starting at 9 AM
    now = datetime.datetime.now()
    start_of_day = now.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Mock Sessions (app, title, category, duration_minutes)
    sessions = [
        ("Code.exe", "backend/engine.py - Productivity App", "coding", 65),
        ("chrome.exe", "Stack Overflow - PyQt6 threaded timers", "learning", 15),
        ("Code.exe", "ui/dashboard_page.py - Productivity App", "coding", 40),
        ("Discord.exe", "Team Chat - #general", "communication", 10),
        ("chrome.exe", "Figma - UI/UX Design System", "writing", 55), # Treating figma as 'writing'/design
        ("chrome.exe", "YouTube - Lofi Hip Hop Radio", "entertainment", 25),
        ("Notion.exe", "Productivity App Architecture Plan", "writing", 30),
        ("Code.exe", "backend/analytics.py - Productivity App", "coding", 50),
    ]
    
    current_time = start_of_day.timestamp()
    
    for app, title, category, dur_mins in sessions:
        dur_secs = dur_mins * 60
        end_time = current_time + dur_secs
        
        db.cursor.execute('''
            INSERT INTO activity_sessions (app, title, category, start_time, end_time, duration)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (app, title, category, current_time, end_time, dur_secs))
        
        # Move forward, optionally adding 2 mins idle between tasks
        current_time = end_time + 120 

    db.conn.commit()
    print("✅ Database successfully seeded with 1 full day of tracked sessions!")

if __name__ == "__main__":
    seed_database()
