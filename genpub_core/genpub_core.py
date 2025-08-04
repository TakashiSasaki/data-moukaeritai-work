"""
Module: genpub_core.py

This module implements the GenPub Core schema as a Python dataclass.
The GenPub Core schema captures minimal metadata for distributed data lineage.
Each schema version is uniquely identified by a persistent URI (`SCHEMA_URI`) and its derived UUIDv5 (`SCHEMA_ID`).

Fields:
  - gen_name    : Identifier of the data generator (Unicode string; excludes control and format characters).
  - gen_domain  : Domain or organization of the generator (Unicode string; excludes control and format characters).
  - gen_time    : UTC timestamp when data was created (ISO 8601 string).
  - pub_locator : Generic URI of the publication endpoint or medium
                  (e.g., udp://host:port, s3://bucket/object, file:///path).
  - pub_time    : UTC timestamp when data was published.
  - data        : Raw payload or reference (bytes, text, JSON, or hash).
  - id          : UUID4 primary key for internal indexing and tracking.
                   Ensures each record has a globally unique identifier independent of its content or timestamps.

Validation:
  - `gen_name` and `gen_domain` are validated to ensure they are non-empty Unicode strings
    without control characters (C0 and C1 blocks) or format characters (Unicode category Cf).

Usage example:
    from datetime import datetime
    from genpub_core import Record, URI

    record = Record(
        gen_name="センサーA",
        gen_domain="例示.org",
        gen_time=datetime.utcnow(),
        pub_locator=URI("udp://192.0.2.15:54321"),
        pub_time=datetime.utcnow(),
        data=b"sensor reading binary blob"
    )

"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import NewType
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

# Persistent schema URI for GenPub Core v1
SCHEMA_URI: str = "https://example.org/schema/genpub_core/v1"
# Derive a UUIDv5 from the URL namespace and the schema URI
SCHEMA_ID: UUID = uuid5(NAMESPACE_URL, SCHEMA_URI)

# Alias for a generic URI type (e.g., udp://, s3://, file://)
URI = NewType("URI", str)

# Regex to detect invalid characters: control (C0: U+0000-U+001F, C1: U+007F-U+009F)
# and format characters (Unicode category Cf)
_INVALID_NAME_CH_PATTERN = re.compile(
    r"[\x00-\x1F\x7F-\x9F"  # C0 and C1 control
    r"\u200B-\u200F"          # ZERO WIDTH and directional marks
    r"\u202A-\u202E"          # bidirectional overrides
    r"\u2060-\u2064"          # format control
    r"\uFEFF]"                 # ZERO WIDTH NO-BREAK SPACE (BOM)
)

@dataclass(slots=True)
class Record:
    """
    GenPub Core Record:
    Represents a single unit of data generation and publication metadata.

    Attributes:
        gen_name      : Name of the data generator (Unicode; validated).
        gen_domain    : Domain or organization of the generator (Unicode; validated).
        gen_time      : Timestamp when data was generated (UTC).
        pub_locator   : Publication endpoint as a URI-like locator.
        pub_time      : Timestamp when data was published (UTC).
        data          : Payload or reference (raw bytes, JSON text, or hash).
        id            : UUID4 primary key for internal indexing and tracking.
    """
    gen_name: str        # Name of the generator (Unicode; validated)
    gen_domain: str      # Domain or organization of the generator (Unicode; validated)
    gen_time: datetime   # Timestamp when data was generated (UTC)
    pub_locator: URI     # Publication endpoint as a URI-like locator
    pub_time: datetime   # Timestamp when data was published (UTC)
    data: bytes          # Payload or reference (raw bytes, JSON text, or hash)
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        """
        Validate that gen_name and gen_domain do not contain disallowed characters.
        """
        for attr in ("gen_name", "gen_domain"):
            val = getattr(self, attr)
            if not isinstance(val, str) or not val:
                raise ValueError(f"{attr} must be a non-empty string")
            if _INVALID_NAME_CH_PATTERN.search(val):
                raise ValueError(f"{attr} contains invalid characters: {val!r}")

    def to_dict(self) -> dict:
        """
        Serialize Record to dict with ISO-formatted timestamps and schema info.
        """
        return {
            "schema_uri": SCHEMA_URI,
            "schema_id": str(SCHEMA_ID),
            "id": str(self.id),
            "gen_name": self.gen_name,
            "gen_domain": self.gen_domain,
            "gen_time": self.gen_time.isoformat(),
            "pub_locator": self.pub_locator,
            "pub_time": self.pub_time.isoformat(),
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, obj: dict) -> Record:
        """
        Deserialize Record from dict (timestamps must be ISO strings).
        Verifies schema_uri matches this schema version.
        """
        if obj.get("schema_uri") != SCHEMA_URI:
            raise ValueError(
                f"Schema URI mismatch: expected {SCHEMA_URI}, got {obj.get('schema_uri')}"
            )
        schema_id = UUID(obj.get("schema_id", ""))
        if schema_id != SCHEMA_ID:
            raise ValueError(
                f"Schema ID mismatch: expected {SCHEMA_ID}, got {schema_id}"
            )
        return cls(
            gen_name=obj["gen_name"],
            gen_domain=obj["gen_domain"],
            gen_time=datetime.fromisoformat(obj["gen_time"]),
            pub_locator=URI(obj["pub_locator"]),
            pub_time=datetime.fromisoformat(obj["pub_time"]),
            data=obj["data"] if isinstance(obj["data"], (bytes, bytearray)) else obj["data"].encode(),
            id=UUID(obj.get("id", str(uuid4()))),
        )
