# backend/models/base.py
import sqlite3
from flask import g, current_app

def get_db():
    """Получить соединение с базой данных"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(current_app.config['DATABASE_PATH'])
        db.row_factory = sqlite3.Row
    return db

def query_db(query, args=(), one=False):
    """Выполнить запрос к базе данных"""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def commit_db():
    """Зафиксировать изменения в базе данных"""
    get_db().commit()