"""Run directly: python seed.py  — clears and re-seeds the database."""
import json
import sqlite3
from pathlib import Path

DB_PATH = "english_practice.db"
SEED_PATH = "scenarios_seed.json"


def main():
    data = json.loads(Path(SEED_PATH).read_text(encoding="utf-8"))
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    # Migrate existing DBs that pre-date the text_jp column
    try:
        conn.execute("ALTER TABLE turn ADD COLUMN text_jp TEXT")
        conn.commit()
    except Exception:
        pass
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS scenario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL, category_jp TEXT NOT NULL,
            no INTEGER NOT NULL, title_jp TEXT NOT NULL, title_en TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS turn (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_id INTEGER NOT NULL REFERENCES scenario(id),
            seq INTEGER NOT NULL, speaker TEXT NOT NULL,
            text TEXT NOT NULL, hint TEXT, text_jp TEXT
        );
        CREATE TABLE IF NOT EXISTS progress (
            scenario_id INTEGER PRIMARY KEY REFERENCES scenario(id),
            cleared INTEGER NOT NULL DEFAULT 0, cleared_at TEXT
        );
        DELETE FROM turn;
        DELETE FROM progress;
        DELETE FROM scenario;
    """)
    for s in data:
        cur = conn.execute(
            "INSERT INTO scenario (category,category_jp,no,title_jp,title_en) VALUES(?,?,?,?,?)",
            (s["category"], s["category_jp"], s["no"], s["title_jp"], s["title_en"]),
        )
        sid = cur.lastrowid
        for i, t in enumerate(s["turns"], 1):
            conn.execute(
                "INSERT INTO turn (scenario_id,seq,speaker,text,hint,text_jp) VALUES(?,?,?,?,?,?)",
                (sid, i, t["speaker"], t["text"], t.get("hint"), t.get("text_jp")),
            )
    conn.commit()
    conn.close()
    print(f"✓ Seeded {len(data)} scenarios into {DB_PATH}")


if __name__ == "__main__":
    main()
