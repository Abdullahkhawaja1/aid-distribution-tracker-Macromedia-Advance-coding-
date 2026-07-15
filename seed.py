"""
Populate the database with sample data so the dashboard has something to show.

    python seed.py
"""

from aid_tracker.database import Database, BeneficiaryRepository, ShipmentRepository, DistributionRepository
from aid_tracker.models import (
    IndividualBeneficiary, HouseholdBeneficiary, InstitutionBeneficiary,
    FoodAid, MedicalAid, ShelterAid, EducationAid,
    Shipment, DistributionRecord, ShipmentStatus, UrgencyLevel,
)

db = Database("data/aid_tracker.db")
ben_repo = BeneficiaryRepository(db)
ship_repo = ShipmentRepository(db)
dist_repo = DistributionRepository(db)

# --- Beneficiaries (one of each subtype) -----------------------------------
b1 = IndividualBeneficiary(name="Amina Yusuf", location="Zone 4 Camp", age=34, vulnerability="pregnant")
b2 = HouseholdBeneficiary(name="Kone Family", location="Riverside Settlement", family_size=5, has_children=True)
b3 = InstitutionBeneficiary(name="Hope Valley Clinic", location="District 2", institution_type="clinic", served_population=430)
b4 = IndividualBeneficiary(name="Teodoro Reyes", location="Zone 4 Camp", age=71, vulnerability="elderly")
b5 = InstitutionBeneficiary(name="Sunrise Primary School", location="District 5", institution_type="school", served_population=210)

for b in (b1, b2, b3, b4, b5):
    ben_repo.save(b)

# --- Shipments ---------------------------------------------------------------
s1 = Shipment(origin="Central Warehouse", destination="Zone 4 Camp", ngo_name="Horizon Relief",
              status=ShipmentStatus.IN_TRANSIT, urgency=UrgencyLevel.CRITICAL)
s1.add_item(MedicalAid(name="First aid kits", quantity=120, unit="kits"))
s1.add_item(FoodAid(name="Rice", quantity=800, unit="kg"))

s2 = Shipment(origin="Central Warehouse", destination="District 2", ngo_name="MedBridge",
              status=ShipmentStatus.DELIVERED, urgency=UrgencyLevel.HIGH)
s2.add_item(MedicalAid(name="Vaccines", quantity=500, unit="doses"))

s3 = Shipment(origin="Coastal Depot", destination="Riverside Settlement", ngo_name="Horizon Relief",
              status=ShipmentStatus.PENDING, urgency=UrgencyLevel.MODERATE)
s3.add_item(ShelterAid(name="Tarpaulins", quantity=60, unit="units"))
s3.add_item(FoodAid(name="Cooking oil", quantity=150, unit="l"))

s4 = Shipment(origin="Central Warehouse", destination="District 5", ngo_name="EduAid Network",
              status=ShipmentStatus.DELAYED, urgency=UrgencyLevel.LOW)
s4.add_item(EducationAid(name="School kits", quantity=210, unit="kits"))

for s in (s1, s2, s3, s4):
    ship_repo.save(s)

# --- Distributions -------------------------------------------------------------
dist_repo.save(DistributionRecord(shipment_id=s2.shipment_id, beneficiary_id=b3.beneficiary_id,
                                   quantity_delivered=430, notes="Full clinic allocation delivered"))
dist_repo.save(DistributionRecord(shipment_id=s1.shipment_id, beneficiary_id=b1.beneficiary_id,
                                   quantity_delivered=1, notes="Priority medical kit"))
dist_repo.save(DistributionRecord(shipment_id=s1.shipment_id, beneficiary_id=b4.beneficiary_id,
                                   quantity_delivered=1))

print("Seed data loaded: 5 beneficiaries, 4 shipments, 3 distribution records.")
