"""SQLite database layer for the IT Project Risk app."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd

DB_PATH = Path(__file__).with_name("project.db")


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'Analyst',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                owner TEXT NOT NULL,
                stage TEXT NOT NULL,
                budget REAL NOT NULL,
                spent REAL NOT NULL DEFAULT 0,
                progress REAL NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS risk_register (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                probability REAL NOT NULL,
                impact REAL NOT NULL,
                exposure REAL NOT NULL,
                detectability REAL NOT NULL,
                control_strength REAL NOT NULL,
                weight REAL NOT NULL,
                score REAL NOT NULL,
                level TEXT NOT NULL,
                mitigation TEXT,
                owner TEXT,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS project_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                schedule_slippage REAL NOT NULL,
                budget_variance REAL NOT NULL,
                scope_creep REAL NOT NULL,
                requirement_volatility REAL NOT NULL,
                technical_complexity REAL NOT NULL,
                team_turnover REAL NOT NULL,
                stakeholder_engagement REAL NOT NULL,
                vendor_dependency REAL NOT NULL,
                failure_probability REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            """
        )


def seed_demo_data() -> None:
    with get_connection() as conn:
        exists = conn.execute("SELECT COUNT(*) AS total FROM projects").fetchone()["total"]
        if exists:
            return
        conn.executemany(
            """
            INSERT INTO projects(name, owner, stage, budget, spent, progress)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("ERP Modernization", "Ayesha Khan", "Execution", 250000, 142000, 48),
                ("Customer Portal", "Bilal Ahmed", "Testing", 95000, 88000, 78),
                ("Cloud Migration", "Sara Malik", "Planning", 180000, 26000, 18),
            ],
        )


def execute(query: str, values: Iterable = ()) -> int:
    with get_connection() as conn:
        cursor = conn.execute(query, tuple(values))
        return int(cursor.lastrowid)


def fetch_all(query: str, values: Iterable = ()) -> List[Dict]:
    with get_connection() as conn:
        rows = conn.execute(query, tuple(values)).fetchall()
        return [dict(row) for row in rows]


def fetch_one(query: str, values: Iterable = ()) -> Optional[Dict]:
    with get_connection() as conn:
        row = conn.execute(query, tuple(values)).fetchone()
        return dict(row) if row else None


def dataframe(query: str, values: Iterable = ()) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn, params=tuple(values))


def get_projects() -> pd.DataFrame:
    return dataframe("SELECT * FROM projects ORDER BY created_at DESC")


def get_risks() -> pd.DataFrame:
    return dataframe(
        """
        SELECT rr.*, p.name AS project_name
        FROM risk_register rr
        JOIN projects p ON p.id = rr.project_id
        ORDER BY rr.score DESC, rr.created_at DESC
        """
    )


def get_signals() -> pd.DataFrame:
    return dataframe(
        """
        SELECT ps.*, p.name AS project_name
        FROM project_signals ps
        JOIN projects p ON p.id = ps.project_id
        ORDER BY ps.created_at DESC
        """
    )
