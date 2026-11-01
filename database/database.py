"""SQLite persistence for farm configurations and saved plans (stdlib only)."""
import json, sqlite3
from pathlib import Path
DEFAULT_DB = Path(__file__).resolve().parent / "agri_shield.db"


def _conn(path=None):
    c = sqlite3.connect(str(path or DEFAULT_DB))
    c.execute("CREATE TABLE IF NOT EXISTS farm_configs(id INTEGER PRIMARY KEY, name TEXT UNIQUE, config TEXT, saved_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS plans(id INTEGER PRIMARY KEY, farm_name TEXT, priority TEXT, plan TEXT, saved_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    return c


def save_config(name, cfg, path=None):
    if not name.strip():
        raise ValueError("name required")
    with _conn(path) as c:
        c.execute("INSERT INTO farm_configs(name,config) VALUES(?,?) ON CONFLICT(name) DO UPDATE SET config=excluded.config, saved_at=CURRENT_TIMESTAMP",
                  (name.strip(), json.dumps(cfg, default=str)))


def list_configs(path=None):
    with _conn(path) as c:
        return [r[0] for r in c.execute("SELECT name FROM farm_configs ORDER BY saved_at DESC, id DESC")]


def load_config(name, path=None):
    with _conn(path) as c:
        r = c.execute("SELECT config FROM farm_configs WHERE name=?", (name,)).fetchone()
    return json.loads(r[0]) if r else None


def save_plan(farm_name, priority, plan_dict, path=None):
    with _conn(path) as c:
        c.execute("INSERT INTO plans(farm_name,priority,plan) VALUES(?,?,?)", (farm_name, priority, json.dumps(plan_dict, default=str)))


def list_plans(path=None):
    with _conn(path) as c:
        return [{"farm": r[0], "priority": r[1], "plan": json.loads(r[2]), "saved_at": r[3]}
                for r in c.execute("SELECT farm_name,priority,plan,saved_at FROM plans ORDER BY id DESC")]
