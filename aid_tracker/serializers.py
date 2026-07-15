"""
aid_tracker.serializers
=========================
JSON serialization, data persistence helpers, and full-database backup/restore.

Demonstrates: JSON with Python, serialization & data persistence, working
with modules/packages (this module only knows about `models` + `database`,
never about the web layer).
"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

from .models import Beneficiary, Shipment, DistributionRecord
from .database import Database, BeneficiaryRepository, ShipmentRepository, DistributionRepository


def export_beneficiaries(repo: BeneficiaryRepository, path: str | Path) -> Path:
    """Write all beneficiaries to a JSON file (e.g. for field-team handoff)."""
    path = Path(path)
    data = [b.to_dict() for b in repo.all()]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def import_beneficiaries(repo: BeneficiaryRepository, path: str | Path) -> int:
    """Load beneficiaries from a JSON file into the database. Returns count imported."""
    path = Path(path)
    records = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for record in records:
        beneficiary = Beneficiary.from_dict(record)
        repo.save(beneficiary)
        count += 1
    return count


def export_shipments(repo: ShipmentRepository, path: str | Path) -> Path:
    path = Path(path)
    data = [s.to_dict() for s in repo.all()]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def import_shipments(repo: ShipmentRepository, path: str | Path) -> int:
    path = Path(path)
    records = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for record in records:
        shipment = Shipment.from_dict(record)
        repo.save(shipment)
        count += 1
    return count


def full_backup(db: Database, out_dir: str | Path) -> Path:
    """
    Serialize the entire database (beneficiaries, shipments, distributions)
    into a single timestamped JSON snapshot for data persistence / disaster recovery.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ben_repo = BeneficiaryRepository(db)
    ship_repo = ShipmentRepository(db)
    dist_repo = DistributionRepository(db)

    snapshot = {
        "backup_created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "beneficiaries": [b.to_dict() for b in ben_repo.all()],
        "shipments": [s.to_dict() for s in ship_repo.all()],
        "distributions": [d.to_dict() for d in dist_repo.all()],
    }

    filename = f"backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    out_path = out_dir / filename
    out_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return out_path


def restore_backup(db: Database, backup_path: str | Path) -> dict:
    """Restore a full JSON snapshot back into the database. Returns counts restored."""
    backup_path = Path(backup_path)
    snapshot = json.loads(backup_path.read_text(encoding="utf-8"))

    ben_repo = BeneficiaryRepository(db)
    ship_repo = ShipmentRepository(db)
    dist_repo = DistributionRepository(db)

    for b in snapshot.get("beneficiaries", []):
        ben_repo.save(Beneficiary.from_dict(b))
    for s in snapshot.get("shipments", []):
        ship_repo.save(Shipment.from_dict(s))
    for d in snapshot.get("distributions", []):
        try:
            dist_repo.save(DistributionRecord.from_dict(d))
        except Exception:
            pass  # duplicate primary key on re-import; safe to skip

    return {
        "beneficiaries": len(snapshot.get("beneficiaries", [])),
        "shipments": len(snapshot.get("shipments", [])),
        "distributions": len(snapshot.get("distributions", [])),
    }
