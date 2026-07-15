"""
Tests covering the pieces most relevant to the course rubric:
inheritance, polymorphism, JSON serialization, and SQLite persistence.

Run with:  python -m pytest tests/
"""

import json
import tempfile
from pathlib import Path

import pytest

from aid_tracker.models import (
    IndividualBeneficiary, HouseholdBeneficiary, InstitutionBeneficiary,
    FoodAid, MedicalAid, ShelterAid, EducationAid,
    Shipment, DistributionRecord, Beneficiary, AidItem,
)
from aid_tracker.database import Database, BeneficiaryRepository, ShipmentRepository, DistributionRepository
from aid_tracker import serializers


# --------------------------------------------------------------------------- #
# Inheritance & polymorphism
# --------------------------------------------------------------------------- #

def test_beneficiary_polymorphism():
    """Each subclass computes headcount() and describe() differently."""
    individual = IndividualBeneficiary(name="A", location="X", age=30)
    household = HouseholdBeneficiary(name="B", location="Y", family_size=4)
    institution = InstitutionBeneficiary(name="C", location="Z", served_population=100)

    assert individual.headcount() == 1
    assert household.headcount() == 4
    assert institution.headcount() == 100

    # All are Beneficiary instances (inheritance) but behave differently (polymorphism)
    for b in (individual, household, institution):
        assert isinstance(b, Beneficiary)
    assert individual.describe() != household.describe() != institution.describe()


def test_aid_item_priority_polymorphism():
    """priority_score() differs per AidItem subclass — the core polymorphism example."""
    items = [FoodAid("Rice", 10), MedicalAid("Bandages", 5),
              ShelterAid("Tent", 2), EducationAid("Notebooks", 50)]
    scores = {item.category: item.priority_score() for item in items}
    assert scores["medical"] > scores["food"] > scores["shelter"] > scores["education"]
    for item in items:
        assert isinstance(item, AidItem)


# --------------------------------------------------------------------------- #
# JSON serialization round-trips
# --------------------------------------------------------------------------- #

def test_beneficiary_json_roundtrip():
    original = HouseholdBeneficiary(name="Kone Family", location="Riverside", family_size=5, has_children=True)
    data = original.to_dict()
    restored = Beneficiary.from_dict(data)
    assert restored.name == original.name
    assert restored.headcount() == original.headcount()
    assert isinstance(restored, HouseholdBeneficiary)


def test_shipment_json_roundtrip():
    shipment = Shipment(origin="Depot", destination="Camp", ngo_name="TestNGO")
    shipment.add_item(FoodAid("Rice", 100, "kg"))
    shipment.add_item(MedicalAid("Kits", 10, "kits"))

    restored = Shipment.from_dict(shipment.to_dict())
    assert restored.shipment_id == shipment.shipment_id
    assert restored.item_count() == 2
    assert restored.total_priority() == shipment.total_priority()


# --------------------------------------------------------------------------- #
# SQLite persistence
# --------------------------------------------------------------------------- #

@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmp:
        yield Database(Path(tmp) / "test.db")


def test_beneficiary_persists_to_sqlite(temp_db):
    repo = BeneficiaryRepository(temp_db)
    b = IndividualBeneficiary(name="Amina", location="Zone 4", age=34)
    repo.save(b)

    fetched = repo.get(b.beneficiary_id)
    assert fetched is not None
    assert fetched.name == "Amina"
    assert isinstance(fetched, IndividualBeneficiary)
    assert fetched.age == 34


def test_shipment_persists_with_items(temp_db):
    repo = ShipmentRepository(temp_db)
    s = Shipment(origin="Depot", destination="Camp", ngo_name="TestNGO")
    s.add_item(FoodAid("Beans", 50, "kg"))
    repo.save(s)

    fetched = repo.get(s.shipment_id)
    assert fetched.item_count() == 1
    assert fetched.items[0].name == "Beans"


def test_distribution_links_beneficiary_and_shipment(temp_db):
    ben_repo = BeneficiaryRepository(temp_db)
    ship_repo = ShipmentRepository(temp_db)
    dist_repo = DistributionRepository(temp_db)

    b = IndividualBeneficiary(name="Test", location="X")
    s = Shipment(origin="A", destination="B", ngo_name="NGO")
    ben_repo.save(b)
    ship_repo.save(s)

    record = DistributionRecord(shipment_id=s.shipment_id, beneficiary_id=b.beneficiary_id,
                                 quantity_delivered=10)
    dist_repo.save(record)

    records = dist_repo.for_beneficiary(b.beneficiary_id)
    assert len(records) == 1
    assert records[0].quantity_delivered == 10


# --------------------------------------------------------------------------- #
# Full backup / restore
# --------------------------------------------------------------------------- #

def test_full_backup_and_restore(temp_db, tmp_path):
    ben_repo = BeneficiaryRepository(temp_db)
    ship_repo = ShipmentRepository(temp_db)

    ben_repo.save(IndividualBeneficiary(name="Backup Test", location="X"))
    s = Shipment(origin="A", destination="B", ngo_name="NGO")
    s.add_item(FoodAid("Rice", 10))
    ship_repo.save(s)

    backup_path = serializers.full_backup(temp_db, tmp_path)
    assert backup_path.exists()

    snapshot = json.loads(backup_path.read_text())
    assert len(snapshot["beneficiaries"]) == 1
    assert len(snapshot["shipments"]) == 1
