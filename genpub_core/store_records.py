"""
Module: store_records.py

This script provides initialization and insertion functionality for the GenPub Core schema using SQLite.

Features:
  - Initializes a local SQLite database file (`records.db`) with the required `records` table.
  - Defines `init_db()` to create the table if it does not already exist.
  - Defines `insert_record(r: Record)` to insert a `Record` instance into the database.
  - Demonstrates usage when run as a script: creates a sample `Record`, inserts it, and prints confirmation.

Usage:
    from genpub_core import Record, URI
    from datetime import datetime
    import store_records

    store_records.init_db()
    rec = Record(
        gen_name="sensor42",
        gen_domain="example.org",
        gen_time=datetime.utcnow(),
        pub_locator=URI("udp://192.0.2.15:54321"),
        pub_time=datetime.utcnow(),
        data=b"example payload"
    )
    store_records.insert_record(rec)

Run from the command line:
    $ python store_records.py
"""

import sqlite3
from datetime import datetime
from genpub_core import Record

# Path to the SQLite database file
DB_PATH = "records.db"

# SQL statement to create the 'records' table matching GenPub Core schema
DDL = """
CREATE TABLE IF NOT EXISTS records (
    id            TEXT PRIMARY KEY,
    gen_name      TEXT NOT NULL,
    gen_domain    TEXT NOT NULL,
    gen_time      TEXT NOT NULL,
    pub_locator   TEXT NOT NULL,
    pub_time      TEXT NOT NULL,
    data          BLOB NOT NULL
);
"""

def init_db() -> None:
    """
    Initialize the SQLite database by creating the 'records' table.
    If the table already exists, this function has no effect.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(DDL)
    conn.commit()
    conn.close()


def insert_record(r: Record) -> None:
    """
    Insert a GenPub Core Record into the SQLite database.

    Args:
        r (Record): An instance of genpub_core.Record to be stored.

    The Record's fields are serialized as follows:
      - r.id           -> TEXT (UUID string)
      - r.gen_name     -> TEXT
      - r.gen_domain   -> TEXT
      - r.gen_time     -> TEXT (ISO 8601 UTC string)
      - r.pub_locator  -> TEXT (URI string)
      - r.pub_time     -> TEXT (ISO 8601 UTC string)
      - r.data         -> BLOB
    """
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
    # Example usage: initialize DB and insert a sample record
    init_db()
    sample = Record(
        gen_name="sensor42",
        gen_domain="example.org",
        gen_time=datetime.utcnow(),
        pub_locator=URI("udp://192.0.2.15:54321"),
        pub_time=datetime.utcnow(),
        data=b"example payload"
    )
    insert_record(sample)
    print("Inserted record with ID:", sample.id)
