"""
aid_tracker.database
=====================
SQLite persistence layer.

Demonstrates: SQLite with Python (sqlite3), schema design, parameterized
queries, and a small Repository pattern that keeps SQL out of the rest
of the codebase.
"""

from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Iterator

from .models import (
    Beneficiary, Shipment, DistributionRecord, AidItem,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS beneficiaries (
    beneficiary_id TEXT PRIMARY KEY,
    type           TEXT NOT NULL,
    name           TEXT NOT NULL,
    location       TEXT NOT NULL,
    contact        TEXT,
    notes          TEXT,
    registered_on  TEXT,
    extra_json     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id     TEXT PRIMARY KEY,
    origin          TEXT NOT NULL,
    destination     TEXT NOT NULL,
    ngo_name        TEXT NOT NULL,
    status          TEXT NOT NULL,
    urgency         TEXT NOT NULL,
    departure_date  TEXT,
    items_json      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS distributions (
    record_id           TEXT PRIMARY KEY,
    shipment_id          TEXT NOT NULL,
    beneficiary_id        TEXT NOT NULL,
    quantity_delivered  REAL NOT NULL,
    delivered_on        TEXT NOT NULL,
    notes                TEXT,
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
    FOREIGN KEY (beneficiary_id) REFERENCES beneficiaries(beneficiary_id)
);
"""


class Database:
    """Thin wrapper around a SQLite connection for this project."""

    def __init__(self, db_path: str | Path = "data/aid_tracker.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# Repositories — one per aggregate, each translating rows <-> domain objects
# ---------------------------------------------------------------------------

class BeneficiaryRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, b: Beneficiary) -> None:
        data = b.to_dict()
        core_keys = {"beneficiary_id", "type", "name", "location", "contact",
                     "notes", "registered_on", "headcount", "description"}
        extra = {k: v for k, v in data.items() if k not in core_keys}
        with self.db._connect() as conn:
            conn.execute(
                """INSERT INTO beneficiaries
                   (beneficiary_id, type, name, location, contact, notes, registered_on, extra_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(beneficiary_id) DO UPDATE SET
                       type=excluded.type, name=excluded.name, location=excluded.location,
                       contact=excluded.contact, notes=excluded.notes, extra_json=excluded.extra_json""",
                (b.beneficiary_id, b.category, b.name, b.location, b.contact,
                 b.notes, b.registered_on, json.dumps(extra)),
            )

    def all(self) -> list[Beneficiary]:
        with self.db._connect() as conn:
            rows = conn.execute("SELECT * FROM beneficiaries ORDER BY registered_on DESC").fetchall()
        return [self._row_to_obj(r) for r in rows]

    def get(self, beneficiary_id: str) -> Beneficiary | None:
        with self.db._connect() as conn:
            row = conn.execute(
                "SELECT * FROM beneficiaries WHERE beneficiary_id = ?", (beneficiary_id,)
            ).fetchone()
        return self._row_to_obj(row) if row else None

    def delete(self, beneficiary_id: str) -> None:
        with self.db._connect() as conn:
            conn.execute("DELETE FROM beneficiaries WHERE beneficiary_id = ?", (beneficiary_id,))

    @staticmethod
    def _row_to_obj(row: sqlite3.Row) -> Beneficiary:
        extra = json.loads(row["extra_json"])
        data = {
            "beneficiary_id": row["beneficiary_id"], "type": row["type"], "name": row["name"],
            "location": row["location"], "contact": row["contact"], "notes": row["notes"],
            **extra,
        }
        return Beneficiary.from_dict(data)


class ShipmentRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, s: Shipment) -> None:
        items_json = json.dumps([i.to_dict() for i in s.items])
        with self.db._connect() as conn:
            conn.execute(
                """INSERT INTO shipments
                   (shipment_id, origin, destination, ngo_name, status, urgency, departure_date, items_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(shipment_id) DO UPDATE SET
                       origin=excluded.origin, destination=excluded.destination,
                       ngo_name=excluded.ngo_name, status=excluded.status,
                       urgency=excluded.urgency, departure_date=excluded.departure_date,
                       items_json=excluded.items_json""",
                (s.shipment_id, s.origin, s.destination, s.ngo_name, s.status.value,
                 s.urgency.value, s.departure_date, items_json),
            )

    def all(self) -> list[Shipment]:
        with self.db._connect() as conn:
            rows = conn.execute("SELECT * FROM shipments ORDER BY departure_date DESC").fetchall()
        return [self._row_to_obj(r) for r in rows]

    def get(self, shipment_id: str) -> Shipment | None:
        with self.db._connect() as conn:
            row = conn.execute(
                "SELECT * FROM shipments WHERE shipment_id = ?", (shipment_id,)
            ).fetchone()
        return self._row_to_obj(row) if row else None

    def update_status(self, shipment_id: str, status: str) -> None:
        with self.db._connect() as conn:
            conn.execute(
                "UPDATE shipments SET status = ? WHERE shipment_id = ?", (status, shipment_id)
            )

    def delete(self, shipment_id: str) -> None:
        with self.db._connect() as conn:
            conn.execute("DELETE FROM shipments WHERE shipment_id = ?", (shipment_id,))

    @staticmethod
    def _row_to_obj(row: sqlite3.Row) -> Shipment:
        data = {
            "shipment_id": row["shipment_id"], "origin": row["origin"],
            "destination": row["destination"], "ngo_name": row["ngo_name"],
            "status": row["status"], "urgency": row["urgency"],
            "departure_date": row["departure_date"], "items": json.loads(row["items_json"]),
        }
        return Shipment.from_dict(data)


class DistributionRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, d: DistributionRecord) -> None:
        with self.db._connect() as conn:
            conn.execute(
                """INSERT INTO distributions
                   (record_id, shipment_id, beneficiary_id, quantity_delivered, delivered_on, notes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (d.record_id, d.shipment_id, d.beneficiary_id,
                 d.quantity_delivered, d.delivered_on, d.notes),
            )

    def all(self) -> list[DistributionRecord]:
        with self.db._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM distributions ORDER BY delivered_on DESC"
            ).fetchall()
        return [DistributionRecord(**dict(r)) for r in rows]

    def for_beneficiary(self, beneficiary_id: str) -> list[DistributionRecord]:
        with self.db._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM distributions WHERE beneficiary_id = ? ORDER BY delivered_on DESC",
                (beneficiary_id,),
            ).fetchall()
        return [DistributionRecord(**dict(r)) for r in rows]

    def delete(self, record_id: str) -> None:
        with self.db._connect() as conn:
            conn.execute("DELETE FROM distributions WHERE record_id = ?", (record_id,))
