#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_media_schema.py
SQLite schema verification for media_object with external key constraints.
"""

import sqlite3
import time
import sys

def run_verification():
    con = sqlite3.connect(":memory:")
    con.isolation_level = None  # autocommit mode
    cur = con.cursor()

    # Capabilities
    cur.execute("SELECT sqlite_version()")
    version = cur.fetchone()[0]
    major, minor, patch = map(int, version.split("."))
    strict_ok = (major, minor, patch) >= (3, 37, 0)
    generated_ok = (major, minor, patch) >= (3, 31, 0)
    print(f"SQLite version: {version} STRICT:{strict_ok} GENERATED_COLUMNS:{generated_ok}")

    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute("PRAGMA recursive_triggers = OFF")

    # DDL
    ddl = f"""
    CREATE TABLE media_type_major (
      name TEXT PRIMARY KEY
    ) {'STRICT' if strict_ok else ''};

    CREATE TABLE media_type_minor (
      major TEXT NOT NULL REFERENCES media_type_major(name) ON UPDATE CASCADE ON DELETE CASCADE,
      minor TEXT NOT NULL,
      {"full TEXT GENERATED ALWAYS AS (major || '/' || minor) VIRTUAL," if generated_ok else ""}
      PRIMARY KEY (major, minor)
    ) {'STRICT' if strict_ok else ''};

    CREATE TABLE charset_canonical (
      name TEXT PRIMARY KEY,
      is_unicode INTEGER NOT NULL DEFAULT 0 CHECK (is_unicode IN (0,1)),
      notes TEXT
    ) {'STRICT' if strict_ok else ''};

    CREATE TABLE charset_alias (
      alias TEXT PRIMARY KEY,
      canonical TEXT NOT NULL REFERENCES charset_canonical(name) ON UPDATE CASCADE ON DELETE CASCADE
    ) {'STRICT' if strict_ok else ''};

    CREATE TABLE transfer_encoding_def (
      name TEXT PRIMARY KEY,
      is_base64_variant INTEGER NOT NULL DEFAULT 0 CHECK (is_base64_variant IN (0,1)),
      notes TEXT
    ) {'STRICT' if strict_ok else ''};

    CREATE TABLE media_object (
      type_major        TEXT,
      type_minor        TEXT,
      charset           TEXT,
      transfer_encoding TEXT,
      data_bytes        BLOB NOT NULL,
      timestamp_ms      INTEGER NOT NULL DEFAULT (CAST((julianday('now') - 2440587.5) * 86400000 AS INTEGER)),

      CHECK (type_major IS NOT NULL OR type_minor IS NULL),
      CHECK (charset IS NULL OR type_major = 'text'),
      CHECK (typeof(data_bytes) = 'blob'),
      CHECK (timestamp_ms >= 0 AND timestamp_ms < 5000000000000),

      FOREIGN KEY (type_major) REFERENCES media_type_major(name)
          ON UPDATE CASCADE ON DELETE NO ACTION,
      FOREIGN KEY (type_major, type_minor) REFERENCES media_type_minor(major, minor)
          ON UPDATE CASCADE ON DELETE SET NULL,
      FOREIGN KEY (charset) REFERENCES charset_canonical(name)
          ON UPDATE CASCADE ON DELETE SET NULL,
      FOREIGN KEY (transfer_encoding) REFERENCES transfer_encoding_def(name)
          ON UPDATE CASCADE ON DELETE SET NULL
    ) {'STRICT' if strict_ok else ''};

    CREATE TRIGGER trg_media_object_touch
    AFTER UPDATE ON media_object
    FOR EACH ROW
    BEGIN
      UPDATE media_object
         SET timestamp_ms = CAST((julianday('now') - 2440587.5) * 86400000 AS INTEGER)
       WHERE rowid = NEW.rowid;
    END;
    """
    cur.executescript(ddl)

    # Seed data
    cur.executemany("INSERT INTO media_type_major(name) VALUES (?)",
                    [(x,) for x in ('application','audio','font','image','message','model','multipart','text','video')])
    cur.executemany("INSERT INTO media_type_minor(major, minor) VALUES (?,?)",
                    [('text','plain'),('image','png'),('application','json')])
    cur.executemany("INSERT INTO charset_canonical(name,is_unicode) VALUES (?,?)",
                    [('utf-8',1),('us-ascii',0)])
    cur.executemany("INSERT INTO transfer_encoding_def(name,is_base64_variant) VALUES (?,?)",
                    [('binary',0),('base64',1)])

    # Tests
    print("\n[TEST] valid insert text/plain with utf-8")
    cur.execute("INSERT INTO media_object(type_major,type_minor,charset,transfer_encoding,data_bytes) VALUES ('text','plain','utf-8','binary',X'')")

    print("[TEST] valid insert image/png with NULL charset")
    cur.execute("INSERT INTO media_object(type_major,type_minor,charset,transfer_encoding,data_bytes) VALUES ('image','png',NULL,'binary',X'89504E47')")

    print("[TEST] trigger updates timestamp_ms")
    cur.execute("SELECT rowid,timestamp_ms FROM media_object ORDER BY rowid LIMIT 1")
    rid, t0 = cur.fetchone()
    time.sleep(0.02)
    cur.execute("UPDATE media_object SET charset='utf-8' WHERE rowid=?", (rid,))
    cur.execute("SELECT timestamp_ms FROM media_object WHERE rowid=?", (rid,))
    t1 = cur.fetchone()[0]
    print("timestamp_ms delta =", t1 - t0)

    print("\nAll tests executed successfully.")

if __name__ == "__main__":
    run_verification()
