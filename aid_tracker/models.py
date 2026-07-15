"""
aid_tracker.models
===================
Core domain classes for the Aid Distribution Tracker.

Demonstrates:
    - Object-Oriented Programming (encapsulation of state + behavior)
    - Inheritance (Beneficiary / AidItem class hierarchies)
    - Polymorphism (each subclass overrides shared methods differently)
    - Serializable objects (to_dict / from_dict feed the JSON + SQLite layers)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timezone
from enum import Enum
from typing import Optional
import uuid


# ---------------------------------------------------------------------------
# Enums — small, explicit vocabularies used across the domain
# ---------------------------------------------------------------------------

class ShipmentStatus(str, Enum):
    PENDING = "PENDING"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"


class UrgencyLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def _new_id(prefix: str) -> str:
    """Generate a short, human-legible manifest-style ID, e.g. BEN-8F3A21."""
    return f"{prefix}-{uuid.uuid4().hex[:6].upper()}"


# ---------------------------------------------------------------------------
# Beneficiary hierarchy  (Inheritance + Polymorphism)
# ---------------------------------------------------------------------------

class Beneficiary(ABC):
    """
    Abstract base for anyone/anything receiving aid.

    Subclasses must implement `headcount()` and `describe()`, which behave
    differently per concrete type — this is the polymorphism the course
    material asks us to demonstrate.
    """

    category: str = "beneficiary"

    def __init__(self, name: str, location: str, contact: str = "",
                 beneficiary_id: Optional[str] = None, notes: str = ""):
        self.beneficiary_id = beneficiary_id or _new_id("BEN")
        self.name = name
        self.location = location
        self.contact = contact
        self.notes = notes
        self.registered_on = datetime.now(timezone.utc).isoformat(timespec="seconds")

    @abstractmethod
    def headcount(self) -> int:
        """How many individual people this record represents."""
        raise NotImplementedError

    @abstractmethod
    def describe(self) -> str:
        """Human-readable one-liner used in reports/UI."""
        raise NotImplementedError

    def to_dict(self) -> dict:
        return {
            "beneficiary_id": self.beneficiary_id,
            "type": self.category,
            "name": self.name,
            "location": self.location,
            "contact": self.contact,
            "notes": self.notes,
            "registered_on": self.registered_on,
            "headcount": self.headcount(),
            "description": self.describe(),
            **self._extra_fields(),
        }

    def _extra_fields(self) -> dict:
        """Hook for subclasses to inject extra serialized fields."""
        return {}

    @staticmethod
    def from_dict(data: dict) -> "Beneficiary":
        kind = data.get("type", "individual")
        cls_map = {
            "individual": IndividualBeneficiary,
            "household": HouseholdBeneficiary,
            "institution": InstitutionBeneficiary,
        }
        cls = cls_map.get(kind, IndividualBeneficiary)
        return cls._build_from_dict(data)

    @classmethod
    def _build_from_dict(cls, data: dict) -> "Beneficiary":
        raise NotImplementedError

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.beneficiary_id} {self.name!r}>"


class IndividualBeneficiary(Beneficiary):
    category = "individual"

    def __init__(self, name: str, location: str, age: int = 0,
                 vulnerability: str = "general", **kwargs):
        super().__init__(name, location, **kwargs)
        self.age = age
        self.vulnerability = vulnerability  # e.g. "elderly", "disabled", "general"

    def headcount(self) -> int:
        return 1

    def describe(self) -> str:
        return f"Individual, age {self.age}, vulnerability: {self.vulnerability}"

    def _extra_fields(self) -> dict:
        return {"age": self.age, "vulnerability": self.vulnerability}

    @classmethod
    def _build_from_dict(cls, data: dict) -> "IndividualBeneficiary":
        return cls(
            name=data["name"], location=data["location"],
            age=data.get("age", 0), vulnerability=data.get("vulnerability", "general"),
            beneficiary_id=data.get("beneficiary_id"), contact=data.get("contact", ""),
            notes=data.get("notes", ""),
        )


class HouseholdBeneficiary(Beneficiary):
    category = "household"

    def __init__(self, name: str, location: str, family_size: int = 1,
                 has_children: bool = False, **kwargs):
        super().__init__(name, location, **kwargs)
        self.family_size = max(1, family_size)
        self.has_children = has_children

    def headcount(self) -> int:
        return self.family_size

    def describe(self) -> str:
        child_note = " (with children)" if self.has_children else ""
        return f"Household of {self.family_size}{child_note}"

    def _extra_fields(self) -> dict:
        return {"family_size": self.family_size, "has_children": self.has_children}

    @classmethod
    def _build_from_dict(cls, data: dict) -> "HouseholdBeneficiary":
        return cls(
            name=data["name"], location=data["location"],
            family_size=data.get("family_size", 1), has_children=data.get("has_children", False),
            beneficiary_id=data.get("beneficiary_id"), contact=data.get("contact", ""),
            notes=data.get("notes", ""),
        )


class InstitutionBeneficiary(Beneficiary):
    category = "institution"

    def __init__(self, name: str, location: str, institution_type: str = "shelter",
                 served_population: int = 0, **kwargs):
        super().__init__(name, location, **kwargs)
        self.institution_type = institution_type  # school, clinic, shelter, camp...
        self.served_population = served_population

    def headcount(self) -> int:
        return self.served_population

    def describe(self) -> str:
        return f"{self.institution_type.title()} serving {self.served_population} people"

    def _extra_fields(self) -> dict:
        return {"institution_type": self.institution_type, "served_population": self.served_population}

    @classmethod
    def _build_from_dict(cls, data: dict) -> "InstitutionBeneficiary":
        return cls(
            name=data["name"], location=data["location"],
            institution_type=data.get("institution_type", "shelter"),
            served_population=data.get("served_population", 0),
            beneficiary_id=data.get("beneficiary_id"), contact=data.get("contact", ""),
            notes=data.get("notes", ""),
        )


# ---------------------------------------------------------------------------
# AidItem hierarchy  (Inheritance + Polymorphism)
# ---------------------------------------------------------------------------

class AidItem(ABC):
    """Abstract base for any kind of aid carried in a shipment."""

    category: str = "generic"

    def __init__(self, name: str, quantity: float, unit: str = "unit"):
        self.name = name
        self.quantity = quantity
        self.unit = unit

    @abstractmethod
    def priority_score(self) -> int:
        """
        Relative urgency score (higher = more time-critical).
        Overridden per-category — this IS the polymorphism: the same method
        name yields category-specific logic.
        """
        raise NotImplementedError

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "priority_score": self.priority_score(),
        }

    @staticmethod
    def from_dict(data: dict) -> "AidItem":
        cls_map = {
            "food": FoodAid,
            "medical": MedicalAid,
            "shelter": ShelterAid,
            "education": EducationAid,
        }
        cls = cls_map.get(data.get("category", "food"), FoodAid)
        return cls(name=data["name"], quantity=data["quantity"], unit=data.get("unit", "unit"))

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name} {self.quantity}{self.unit}>"


class FoodAid(AidItem):
    category = "food"

    def priority_score(self) -> int:
        return 9  # food spoils / is needed daily — consistently high urgency


class MedicalAid(AidItem):
    category = "medical"

    def priority_score(self) -> int:
        return 10  # highest baseline urgency — life-critical


class ShelterAid(AidItem):
    category = "shelter"

    def priority_score(self) -> int:
        return 6


class EducationAid(AidItem):
    category = "education"

    def priority_score(self) -> int:
        return 3  # important, but rarely time-critical


# ---------------------------------------------------------------------------
# Shipment & DistributionRecord — compose the above into operational records
# ---------------------------------------------------------------------------

class Shipment:
    def __init__(self, origin: str, destination: str, ngo_name: str,
                 status: ShipmentStatus = ShipmentStatus.PENDING,
                 items: Optional[list[AidItem]] = None,
                 shipment_id: Optional[str] = None,
                 departure_date: Optional[str] = None,
                 urgency: UrgencyLevel = UrgencyLevel.MODERATE):
        self.shipment_id = shipment_id or _new_id("SHP")
        self.origin = origin
        self.destination = destination
        self.ngo_name = ngo_name
        self.status = ShipmentStatus(status) if isinstance(status, str) else status
        self.items: list[AidItem] = items or []
        self.departure_date = departure_date or date.today().isoformat()
        self.urgency = UrgencyLevel(urgency) if isinstance(urgency, str) else urgency

    def add_item(self, item: AidItem) -> None:
        self.items.append(item)

    def total_priority(self) -> int:
        """Aggregate urgency across all items — used for dashboard sorting."""
        return sum(item.priority_score() for item in self.items)

    def item_count(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict:
        return {
            "shipment_id": self.shipment_id,
            "origin": self.origin,
            "destination": self.destination,
            "ngo_name": self.ngo_name,
            "status": self.status.value,
            "urgency": self.urgency.value,
            "departure_date": self.departure_date,
            "items": [i.to_dict() for i in self.items],
            "total_priority": self.total_priority(),
        }

    @staticmethod
    def from_dict(data: dict) -> "Shipment":
        items = [AidItem.from_dict(i) for i in data.get("items", [])]
        return Shipment(
            origin=data["origin"], destination=data["destination"], ngo_name=data["ngo_name"],
            status=data.get("status", "PENDING"), items=items,
            shipment_id=data.get("shipment_id"), departure_date=data.get("departure_date"),
            urgency=data.get("urgency", "MODERATE"),
        )

    def __repr__(self):
        return f"<Shipment {self.shipment_id} {self.origin}->{self.destination} [{self.status.value}]>"


@dataclass
class DistributionRecord:
    """A concrete hand-off: this shipment's aid reached this beneficiary."""
    shipment_id: str
    beneficiary_id: str
    quantity_delivered: float
    delivered_on: str = field(default_factory=lambda: date.today().isoformat())
    record_id: str = field(default_factory=lambda: _new_id("DST"))
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "DistributionRecord":
        return DistributionRecord(**data)
