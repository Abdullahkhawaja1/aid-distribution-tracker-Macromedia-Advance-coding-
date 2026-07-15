"""
aid_tracker.app
=================
Flask web application — the presentation layer. Talks only to the
repositories / serializers, never touches SQL directly.
"""

from __future__ import annotations
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_file

from .database import Database, BeneficiaryRepository, ShipmentRepository, DistributionRepository
from .models import (
    IndividualBeneficiary, HouseholdBeneficiary, InstitutionBeneficiary,
    FoodAid, MedicalAid, ShelterAid, EducationAid,
    Shipment, DistributionRecord, ShipmentStatus, UrgencyLevel,
)
from . import serializers

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "aid_tracker.db"
EXPORT_DIR = BASE_DIR / "exports"

ITEM_CLASSES = {
    "food": FoodAid, "medical": MedicalAid, "shelter": ShelterAid, "education": EducationAid,
}
BENEFICIARY_CLASSES = {
    "individual": IndividualBeneficiary, "household": HouseholdBeneficiary,
    "institution": InstitutionBeneficiary,
}


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "aid-distribution-tracker-dev-key"

    db = Database(DB_PATH)
    ben_repo = BeneficiaryRepository(db)
    ship_repo = ShipmentRepository(db)
    dist_repo = DistributionRepository(db)

    # ------------------------------------------------------------------ #
    # Dashboard
    # ------------------------------------------------------------------ #
    @app.route("/")
    def dashboard():
        beneficiaries = ben_repo.all()
        shipments = ship_repo.all()
        distributions = dist_repo.all()

        total_people_reached = sum(b.headcount() for b in beneficiaries)
        active_shipments = [s for s in shipments if s.status in
                             (ShipmentStatus.PENDING, ShipmentStatus.IN_TRANSIT)]
        delivered = [s for s in shipments if s.status == ShipmentStatus.DELIVERED]
        critical = sorted(shipments, key=lambda s: s.total_priority(), reverse=True)[:5]

        status_counts = {status.value: 0 for status in ShipmentStatus}
        for s in shipments:
            status_counts[s.status.value] += 1

        category_counts = {"food": 0, "medical": 0, "shelter": 0, "education": 0}
        for s in shipments:
            for item in s.items:
                category_counts[item.category] = category_counts.get(item.category, 0) + item.quantity

        return render_template(
            "dashboard.html",
            beneficiary_count=len(beneficiaries),
            total_people_reached=total_people_reached,
            shipment_count=len(shipments),
            active_count=len(active_shipments),
            delivered_count=len(delivered),
            distribution_count=len(distributions),
            critical_shipments=critical,
            status_counts=status_counts,
            category_counts=category_counts,
            recent_distributions=distributions[:6],
        )

    # ------------------------------------------------------------------ #
    # Beneficiaries
    # ------------------------------------------------------------------ #
    @app.route("/beneficiaries")
    def beneficiaries_list():
        return render_template("beneficiaries.html", beneficiaries=ben_repo.all())

    @app.route("/beneficiaries/add", methods=["POST"])
    def beneficiaries_add():
        form = request.form
        kind = form.get("type", "individual")
        common = dict(name=form["name"], location=form["location"],
                      contact=form.get("contact", ""), notes=form.get("notes", ""))
        if kind == "individual":
            b = IndividualBeneficiary(age=int(form.get("age") or 0),
                                       vulnerability=form.get("vulnerability", "general"), **common)
        elif kind == "household":
            b = HouseholdBeneficiary(family_size=int(form.get("family_size") or 1),
                                      has_children=form.get("has_children") == "on", **common)
        else:
            b = InstitutionBeneficiary(institution_type=form.get("institution_type", "shelter"),
                                        served_population=int(form.get("served_population") or 0), **common)
        ben_repo.save(b)
        flash(f"Registered {b.name} ({b.beneficiary_id})", "success")
        return redirect(url_for("beneficiaries_list"))

    @app.route("/beneficiaries/<beneficiary_id>/delete", methods=["POST"])
    def beneficiaries_delete(beneficiary_id):
        ben_repo.delete(beneficiary_id)
        flash("Beneficiary record removed", "info")
        return redirect(url_for("beneficiaries_list"))

    # ------------------------------------------------------------------ #
    # Shipments
    # ------------------------------------------------------------------ #
    @app.route("/shipments")
    def shipments_list():
        return render_template("shipments.html", shipments=ship_repo.all(),
                                item_categories=list(ITEM_CLASSES.keys()),
                                statuses=[s.value for s in ShipmentStatus])

    @app.route("/shipments/add", methods=["POST"])
    def shipments_add():
        form = request.form
        s = Shipment(origin=form["origin"], destination=form["destination"],
                      ngo_name=form["ngo_name"], urgency=form.get("urgency", "MODERATE"))

        categories = request.form.getlist("item_category")
        names = request.form.getlist("item_name")
        quantities = request.form.getlist("item_quantity")
        units = request.form.getlist("item_unit")
        for cat, name, qty, unit in zip(categories, names, quantities, units):
            if not name or not qty:
                continue
            item_cls = ITEM_CLASSES.get(cat, FoodAid)
            s.add_item(item_cls(name=name, quantity=float(qty), unit=unit or "unit"))

        ship_repo.save(s)
        flash(f"Shipment {s.shipment_id} created with {s.item_count()} item line(s)", "success")
        return redirect(url_for("shipments_list"))

    @app.route("/shipments/<shipment_id>/status", methods=["POST"])
    def shipments_update_status(shipment_id):
        new_status = request.form["status"]
        ship_repo.update_status(shipment_id, new_status)
        flash(f"Shipment {shipment_id} marked {new_status.replace('_', ' ').title()}", "info")
        return redirect(url_for("shipments_list"))

    @app.route("/shipments/<shipment_id>/delete", methods=["POST"])
    def shipments_delete(shipment_id):
        ship_repo.delete(shipment_id)
        flash("Shipment removed", "info")
        return redirect(url_for("shipments_list"))

    # ------------------------------------------------------------------ #
    # Distributions
    # ------------------------------------------------------------------ #
    @app.route("/distributions")
    def distributions_list():
        return render_template(
            "distributions.html",
            distributions=dist_repo.all(),
            beneficiaries=ben_repo.all(),
            shipments=ship_repo.all(),
        )

    @app.route("/distributions/add", methods=["POST"])
    def distributions_add():
        form = request.form
        record = DistributionRecord(
            shipment_id=form["shipment_id"],
            beneficiary_id=form["beneficiary_id"],
            quantity_delivered=float(form["quantity_delivered"]),
            notes=form.get("notes", ""),
        )
        dist_repo.save(record)
        flash(f"Distribution recorded ({record.record_id})", "success")
        return redirect(url_for("distributions_list"))

    # ------------------------------------------------------------------ #
    # JSON import / export / backup  (serialization & persistence)
    # ------------------------------------------------------------------ #
    @app.route("/data")
    def data_tools():
        backups = sorted(EXPORT_DIR.glob("backup_*.json"), reverse=True)
        return render_template("data.html", backups=[b.name for b in backups])

    @app.route("/data/export/<kind>")
    def data_export(kind):
        EXPORT_DIR.mkdir(exist_ok=True)
        if kind == "beneficiaries":
            path = serializers.export_beneficiaries(ben_repo, EXPORT_DIR / "beneficiaries.json")
        elif kind == "shipments":
            path = serializers.export_shipments(ship_repo, EXPORT_DIR / "shipments.json")
        else:
            path = serializers.full_backup(db, EXPORT_DIR)
        return send_file(path, as_attachment=True)

    @app.route("/data/backup", methods=["POST"])
    def data_backup():
        path = serializers.full_backup(db, EXPORT_DIR)
        flash(f"Backup saved: {path.name}", "success")
        return redirect(url_for("data_tools"))

    @app.route("/data/restore", methods=["POST"])
    def data_restore():
        filename = request.form["filename"]
        counts = serializers.restore_backup(db, EXPORT_DIR / filename)
        flash(f"Restored {counts['beneficiaries']} beneficiaries, "
              f"{counts['shipments']} shipments, {counts['distributions']} distributions", "success")
        return redirect(url_for("data_tools"))

    @app.route("/api/stats")
    def api_stats():
        """Small JSON API endpoint powering the live dashboard chart."""
        shipments = ship_repo.all()
        status_counts = {status.value: 0 for status in ShipmentStatus}
        for s in shipments:
            status_counts[s.status.value] += 1
        return jsonify(status_counts)

    return app


def main():
    """Console-script entry point (see pyproject.toml [project.scripts])."""
    application = create_app()
    application.run(debug=True, port=5000)


if __name__ == "__main__":
    main()
