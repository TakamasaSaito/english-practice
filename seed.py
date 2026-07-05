"""Run directly: python seed.py  — clears and re-seeds the database."""
import json
import os
import sqlite3
from pathlib import Path

_data_dir = os.environ.get("DATA_DIR")
if _data_dir:
    Path(_data_dir).mkdir(parents=True, exist_ok=True)
    DB_PATH = str(Path(_data_dir) / "english_practice.db")
else:
    DB_PATH = "english_practice.db"

SEED_PATH = "scenarios_seed.json"

PROFILE_DEFAULT = {
    "name_en": "Takamasa Saito",
    "role_en": "Chief Architect",
    "role_jp": "チーフアーキテクト",
    "focus_en": "IT simplification and enterprise architecture",
    "focus_jp": "ITシンプリフィケーションとエンタープライズアーキテクチャ",
    "base_en": "Tokyo",
    "origin_en": "Kanagawa",
    "university_en": "Doshisha University in Kyoto",
    "purpose_en": "a hackathon to validate AI-driven in-house development",
    "purpose_jp": "AI活用による内製開発の技術検証を行うハッカソン",
    "stay_nights": 4,
    "hobbies_en": "tennis, shogi, and golf",
}


def main():
    data = json.loads(Path(SEED_PATH).read_text(encoding="utf-8"))
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
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
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name_en TEXT NOT NULL, role_en TEXT NOT NULL, role_jp TEXT NOT NULL DEFAULT '',
            focus_en TEXT NOT NULL, focus_jp TEXT NOT NULL DEFAULT '',
            base_en TEXT NOT NULL, origin_en TEXT NOT NULL, university_en TEXT NOT NULL,
            purpose_en TEXT NOT NULL, purpose_jp TEXT NOT NULL DEFAULT '',
            stay_nights INTEGER NOT NULL, hobbies_en TEXT NOT NULL
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
    conn.execute("""
        INSERT OR IGNORE INTO profile
            (id,name_en,role_en,role_jp,focus_en,focus_jp,base_en,origin_en,
             university_en,purpose_en,purpose_jp,stay_nights,hobbies_en)
        VALUES (1,:name_en,:role_en,:role_jp,:focus_en,:focus_jp,:base_en,:origin_en,
            :university_en,:purpose_en,:purpose_jp,:stay_nights,:hobbies_en)
    """, PROFILE_DEFAULT)
    conn.commit()
    conn.close()
    print(f"✓ Seeded {len(data)} scenarios into {DB_PATH}")


if __name__ == "__main__":
    main()
