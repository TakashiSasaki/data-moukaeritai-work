# File: store_records.py
# Script file: store_records.py

import sqlite3
from datetime import datetime
from genpub_core import Record

DB_PATH = "records.db"
DDL = """
CREATE TABLE IF NOT EXISTS records (
    id            TEXT PRIMARY KEY,
    gen_name      TEXT,
    gen_domain    TEXT,
    gen_time      TEXT,
    pub_locator   TEXT,
    pub_time      TEXT,
    data          BLOB
);
"""

def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(DDL)
    conn.commit()
    conn.close()

def insert_record(r: Record) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO records VALUES (?,?,?,?,?,?,?)",
        (
            str(r.id),
            r.gen_name,
            r.gen_domain,
            r.gen_time.isoformat(),
            r.pub_locator,
            r.pub_time.isoformat(),
            r.data,
        ),
    )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    rec = Record(
        gen_name="sensor42",
        gen_domain="example.org",
        gen_time=datetime.utcnow(),
        pub_locator="udp://192.0.2.15:54321",
        pub_time=datetime.utcnow(),
        data=b"example data"
    )
    insert_record(rec)
    print("Record inserted:", rec)
