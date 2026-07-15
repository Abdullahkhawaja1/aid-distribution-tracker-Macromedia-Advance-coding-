"""
Aid Distribution Tracker
=========================
A small system for tracking aid shipments, beneficiaries, and distribution
records for NGOs — built to demonstrate OOP, inheritance, polymorphism,
modules/packages, JSON, serialization, and SQLite in Python.
"""

from .models import (
    Beneficiary, IndividualBeneficiary, HouseholdBeneficiary, InstitutionBeneficiary,
    AidItem, FoodAid, MedicalAid, ShelterAid, EducationAid,
    Shipment, DistributionRecord, ShipmentStatus, UrgencyLevel,
)
from .database import Database, BeneficiaryRepository, ShipmentRepository, DistributionRepository

__version__ = "0.1.0"

__all__ = [
    "Beneficiary", "IndividualBeneficiary", "HouseholdBeneficiary", "InstitutionBeneficiary",
    "AidItem", "FoodAid", "MedicalAid", "ShelterAid", "EducationAid",
    "Shipment", "DistributionRecord", "ShipmentStatus", "UrgencyLevel",
    "Database", "BeneficiaryRepository", "ShipmentRepository", "DistributionRepository",
]
