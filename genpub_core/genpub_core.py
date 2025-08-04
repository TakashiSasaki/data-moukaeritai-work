# File: genpub_core.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import NewType
from uuid import UUID, uuid4

# Schema: genpub_core
# Module file: genpub_core.py

URI = NewType("URI", str)

@dataclass(slots=True)
class Record:
    """
    Minimal record for the GenPub Core schema.
    """
    gen_name: str
    gen_domain: str
    gen_time: datetime
    pub_locator: URI
    pub_time: datetime
    data: bytes
    id: UUID = field(default_factory=uuid4)
