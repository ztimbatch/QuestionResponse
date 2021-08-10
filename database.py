import sqlite3
import os
import psycopg2
from psycopg2.extras import DictCursor
from flask import g


class DatabaseConnection:
    def __init__(self, host):
        self.connection = None
        self.host = host

    def __enter__(self):
        self.connection = sqlite3.connect(self.host)
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.commit()
        self.connection.close()


def connect_db():
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'), cursor_factory=DictCursor)
    conn.autocommit = True
    sql = conn.cursor()
    return conn, sql


def get_db():
    db = connect_db()

    if not hasattr(g, 'postgres_db_conn'):
        g.postgres_db_conn = db[0]

    if not hasattr(g, 'postgres_db_cur'):
        g.postgres_db_cur = db[1]

    return g.postgres_db_cur
