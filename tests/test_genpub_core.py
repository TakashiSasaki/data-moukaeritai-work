import pytest
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
from datetime import datetime
from uuid import UUID

from genpub_core import Record, URI, SCHEMA_URI, SCHEMA_ID


def test_valid_record_roundtrip():
    r = Record(
        gen_name="sensorA",
        gen_domain="example.org",
        gen_time=datetime.utcnow(),
        pub_locator=URI("udp://127.0.0.1:9999"),
        pub_time=datetime.utcnow(),
        data=b"payload",
    )

    as_dict = r.to_dict()
    r2 = Record.from_dict(as_dict)

    assert r2.gen_name == r.gen_name
    assert r2.gen_domain == r.gen_domain
    assert r2.gen_time == r.gen_time
    assert r2.pub_locator == r.pub_locator
    assert r2.pub_time == r.pub_time
    assert r2.data == r.data
    assert r2.id == r.id


def test_invalid_name_raises():
    with pytest.raises(ValueError):
        Record(
            gen_name="bad\u200Bname",
            gen_domain="example.org",
            gen_time=datetime.utcnow(),
            pub_locator=URI("udp://127.0.0.1:9999"),
            pub_time=datetime.utcnow(),
            data=b"payload",
        )

    with pytest.raises(ValueError):
        Record(
            gen_name="sensorA",
            gen_domain="\u0000bad",
            gen_time=datetime.utcnow(),
            pub_locator=URI("udp://127.0.0.1:9999"),
            pub_time=datetime.utcnow(),
            data=b"payload",
        )


def test_from_dict_schema_mismatch():
    r = Record(
        gen_name="sensorA",
        gen_domain="example.org",
        gen_time=datetime.utcnow(),
        pub_locator=URI("udp://127.0.0.1:9999"),
        pub_time=datetime.utcnow(),
        data=b"payload",
    )
    d = r.to_dict()
    d["schema_uri"] = "https://wrong.schema/uri"
    with pytest.raises(ValueError):
        Record.from_dict(d)

    d = r.to_dict()
    d["schema_id"] = str(UUID(int=0))
    with pytest.raises(ValueError):
        Record.from_dict(d)


def test_from_dict_encodes_str_data():
    r = Record(
        gen_name="sensorA",
        gen_domain="example.org",
        gen_time=datetime.utcnow(),
        pub_locator=URI("udp://127.0.0.1:9999"),
        pub_time=datetime.utcnow(),
        data=b"payload",
    )
    d = r.to_dict()
    d["data"] = "text"
    r2 = Record.from_dict(d)
    assert isinstance(r2.data, bytes)
    assert r2.data == b"text"
