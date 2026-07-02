import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

DB_PATH = "english_practice.db"
SEED_PATH = "scenarios_seed.json"

app = FastAPI()


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS scenario (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category    TEXT NOT NULL,
                category_jp TEXT NOT NULL,
                no          INTEGER NOT NULL,
                title_jp    TEXT NOT NULL,
                title_en    TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS turn (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id INTEGER NOT NULL REFERENCES scenario(id),
                seq         INTEGER NOT NULL,
                speaker     TEXT NOT NULL,
                text        TEXT NOT NULL,
                hint        TEXT,
                text_jp     TEXT
            );
            CREATE TABLE IF NOT EXISTS progress (
                scenario_id INTEGER PRIMARY KEY REFERENCES scenario(id),
                cleared     INTEGER NOT NULL DEFAULT 0,
                cleared_at  TEXT
            );
        """)
        # Migrate existing DBs that pre-date the text_jp column
        try:
            conn.execute("ALTER TABLE turn ADD COLUMN text_jp TEXT")
        except Exception:
            pass


def seed_db():
    seed = Path(SEED_PATH)
    if not seed.exists():
        return
    scenarios = json.loads(seed.read_text(encoding="utf-8"))
    with get_db() as conn:
        conn.execute("DELETE FROM turn")
        conn.execute("DELETE FROM scenario")
        conn.execute("DELETE FROM progress")
        for s in scenarios:
            cur = conn.execute(
                "INSERT INTO scenario (category, category_jp, no, title_jp, title_en) VALUES (?,?,?,?,?)",
                (s["category"], s["category_jp"], s["no"], s["title_jp"], s["title_en"]),
            )
            sid = cur.lastrowid
            for i, t in enumerate(s["turns"], 1):
                conn.execute(
                    "INSERT INTO turn (scenario_id, seq, speaker, text, hint, text_jp) VALUES (?,?,?,?,?,?)",
                    (sid, i, t["speaker"], t["text"], t.get("hint"), t.get("text_jp")),
                )
    print(f"Seeded {len(scenarios)} scenarios.")


@app.on_event("startup")
def startup():
    init_db()
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM scenario").fetchone()[0]
    if count == 0:
        seed_db()


# ── API ──────────────────────────────────────────────────────────────────────

@app.get("/api/categories")
def api_categories():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT s.category, s.category_jp,
                   COUNT(s.id)                                    AS total,
                   COALESCE(SUM(p.cleared), 0)                    AS cleared
            FROM   scenario s
            LEFT JOIN progress p ON p.scenario_id = s.id
            GROUP BY s.category, s.category_jp
            ORDER BY s.category
        """).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/scenarios")
def api_scenarios(category: str = ""):
    with get_db() as conn:
        if category:
            rows = conn.execute("""
                SELECT s.*, COALESCE(p.cleared, 0) AS cleared, p.cleared_at
                FROM   scenario s
                LEFT JOIN progress p ON p.scenario_id = s.id
                WHERE  s.category = ?
                ORDER BY s.no
            """, (category,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT s.*, COALESCE(p.cleared, 0) AS cleared, p.cleared_at
                FROM   scenario s
                LEFT JOIN progress p ON p.scenario_id = s.id
                ORDER BY s.category, s.no
            """).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/scenarios/{sid}")
def api_scenario(sid: int):
    with get_db() as conn:
        s = conn.execute("SELECT * FROM scenario WHERE id=?", (sid,)).fetchone()
        if not s:
            raise HTTPException(404, "Scenario not found")
        turns = conn.execute(
            "SELECT * FROM turn WHERE scenario_id=? ORDER BY seq", (sid,)
        ).fetchall()
        prog = conn.execute(
            "SELECT * FROM progress WHERE scenario_id=?", (sid,)
        ).fetchone()
    result = dict(s)
    result["turns"] = [dict(t) for t in turns]
    result["cleared"] = bool(prog["cleared"]) if prog else False
    result["cleared_at"] = prog["cleared_at"] if prog else None
    return result


@app.post("/api/scenarios/{sid}/clear")
def api_clear(sid: int):
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM scenario WHERE id=?", (sid,)).fetchone():
            raise HTTPException(404, "Scenario not found")
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("""
            INSERT INTO progress (scenario_id, cleared, cleared_at) VALUES (?,1,?)
            ON CONFLICT(scenario_id) DO UPDATE SET cleared=1, cleared_at=excluded.cleared_at
        """, (sid, now))
    return {"status": "ok", "cleared_at": now}


@app.post("/api/progress/reset")
def api_reset():
    with get_db() as conn:
        conn.execute("DELETE FROM progress")
    return {"status": "ok"}


# static files last so API routes take priority
app.mount("/", StaticFiles(directory="static", html=True), name="static")
