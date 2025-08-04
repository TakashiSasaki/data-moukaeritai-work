"""
Module: genpub_core.py

This module implements the GenPub Core schema as a Python dataclass.
The GenPub Core schema captures minimal metadata for distributed data lineage:

Fields:
  - gen_name    : Identifier of the data generator (e.g., sensor42).
  - gen_domain  : Domain or organization of the generator (e.g., example.org).
  - gen_time    : UTC timestamp when data was created (ISO 8601 string).
  - pub_locator : Generic URI of the publication endpoint or medium
                  (e.g., udp://host:port, s3://bucket/object, file:///path).
  - pub_time    : UTC timestamp when data was published.
  - data        : Raw payload or reference (bytes, text, JSON, or hash).
  - id          : UUID4 primary key for internal indexing.

Usage example:
    from datetime import datetime
    from genpub_core import Record, URI

    record = Record(
        gen_name="sensor42",
        gen_domain="example.org",
        gen_time=datetime.utcnow(),
        pub_locator=URI("udp://192.0.2.15:54321"),
        pub_time=datetime.utcnow(),
        data=b"sensor reading binary blob"
    )

"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import NewType
from uuid import UUID, uuid4

# Alias for a generic URI type (e.g., udp://, s3://, file://)
URI = NewType("URI", str)

@dataclass(slots=True)
class Record:
    """
    GenPub Core Record:
    Represents a single unit of data generation and publication metadata.
    """
    gen_name: str        # Name of the generator (unique per domain)
    gen_domain: str      # Domain or organization of the generator
    gen_time: datetime   # Timestamp when data was generated (UTC)
    pub_locator: URI     # Publication endpoint as a URI-like locator
    pub_time: datetime   # Timestamp when data was published (UTC)
    data: bytes          # Payload or reference (raw bytes, JSON text, or hash)
    id: UUID = field(default_factory=uuid4)
                           # Internal UUID4 identifier for record tracking

    def to_dict(self) -> dict:
        """
        Serialize Record to dict with ISO-formatted timestamps.
        Useful for JSON conversion or storing in document stores.
        """
        return {
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
        """
        return cls(
            gen_name=obj["gen_name"],
            gen_domain=obj["gen_domain"],
            gen_time=datetime.fromisoformat(obj["gen_time"]),
            pub_locator=URI(obj["pub_locator"]),
            pub_time=datetime.fromisoformat(obj["pub_time"]),
            data=obj["data"] if isinstance(obj["data"], (bytes, bytearray)) else obj["data"].encode(),
            id=UUID(obj.get("id", uuid4())),
        )
