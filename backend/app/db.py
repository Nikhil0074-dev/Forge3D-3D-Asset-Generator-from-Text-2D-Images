import json, sqlite3, threading, time, uuid
from . import config

_lock = threading.RLock()
SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, generation_type TEXT, prompt TEXT, provider TEXT, handle TEXT,
  status TEXT, progress INTEGER, message TEXT, error_message TEXT, options TEXT, asset_id TEXT,
  created_at REAL, completed_at REAL);
CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY, job_id TEXT, name TEXT, generation_type TEXT, provider TEXT,
  format TEXT, file_path TEXT, thumbnail_path TEXT, file_size INTEGER, prompt TEXT, stats TEXT, created_at REAL);
"""


def conn():
    c = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _lock, conn() as c:
        c.executescript(SCHEMA)


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _row(r):
    d = dict(r) if r else None
    if d:
        for k in ("options", "stats"):
            if k in d and isinstance(d[k], str):
                d[k] = json.loads(d[k])
    return d


def q(sql, args=(), one=False, commit=False):
    with _lock:
        c = conn()
        try:
            cur = c.execute(sql, args)
            if commit:
                c.commit()
            rows = cur.fetchall()
        finally:
            c.close()
    rows = [_row(r) for r in rows]
    return (rows[0] if rows else None) if one else rows


def create_job(gtype, prompt, provider, options):
    jid = new_id("job")
    q("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
      (jid, gtype, prompt, provider, None, "queued", 0, "Request accepted", None, json.dumps(options), None, time.time(), None), commit=True)
    return jid


def update_job(jid, **kw):
    cols = ",".join(f"{k}=?" for k in kw)
    q(f"UPDATE jobs SET {cols} WHERE id=?", (*kw.values(), jid), commit=True)


def get_job(jid):
    return q("SELECT * FROM jobs WHERE id=?", (jid,), one=True)


def create_asset(**a):
    a.setdefault("id", new_id("asset"))
    a["created_at"] = time.time()
    a["stats"] = json.dumps(a["stats"])
    cols = list(a)
    q(f"INSERT INTO assets({','.join(cols)}) VALUES({','.join('?' * len(cols))})", tuple(a.values()), commit=True)
    return a["id"]


def get_asset(aid):
    return q("SELECT * FROM assets WHERE id=?", (aid,), one=True)


def list_assets(search="", gtype=""):
    sql, args = "SELECT * FROM assets WHERE 1=1", []
    if search:
        sql += " AND (name LIKE ? OR prompt LIKE ?)"
        args += [f"%{search}%"] * 2
    if gtype:
        sql += " AND generation_type=?"
        args.append(gtype)
    return q(sql + " ORDER BY created_at DESC", tuple(args))


def rename_asset(aid, name):
    q("UPDATE assets SET name=? WHERE id=?", (name, aid), commit=True)


def delete_asset(aid):
    q("DELETE FROM assets WHERE id=?", (aid,), commit=True)
