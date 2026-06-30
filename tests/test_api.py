from __future__ import annotations

import io


def asset_payload(**overrides):
    payload = {
        "asset_code": "TST-SCADA-001",
        "system_name": "Test supervisory server",
        "site": "Test Site",
        "asset_type": "SCADA Server",
        "support_status": "end_of_support",
        "business_criticality": 5,
        "safety_impact": 4,
        "production_impact": 5,
        "cyber_exposure": 5,
        "failure_likelihood": 4,
        "spares_risk": 4,
        "recoverability_risk": 5,
        "dependency_complexity": 5,
        "evidence_confidence": "A",
        "delivery_readiness": 2,
        "treatment": "contain",
    }
    payload.update(overrides)
    return payload


def test_health_and_empty_dashboard(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["database"] == "reachable"

    dashboard = client.get("/api/dashboard/summary").json()
    assert dashboard["generated_from"] == "live_database"
    assert dashboard["metrics"]["total_assets"] == 0


def test_asset_crud_recalculates_assessment(client):
    created = client.post("/api/assets", json=asset_payload())
    assert created.status_code == 201, created.text
    asset = created.json()
    assert asset["risk_band"] in {"High", "Critical"}
    assert asset["recommended_wave"] == "Wave 0"
    first_score = asset["risk_score"]

    updated = client.patch(
        f"/api/assets/{asset['id']}",
        json={
            "support_status": "supported",
            "cyber_exposure": 1,
            "failure_likelihood": 1,
            "spares_risk": 1,
            "recoverability_risk": 1,
            "dependency_complexity": 1,
            "evidence_confidence": "A",
        },
    )
    assert updated.status_code == 200, updated.text
    changed = updated.json()
    assert changed["risk_score"] < first_score

    listed = client.get("/api/assets", params={"risk_band": changed["risk_band"]}).json()
    assert listed["total"] == 1

    deleted = client.delete(f"/api/assets/{asset['id']}")
    assert deleted.status_code == 200
    assert client.get("/api/assets").json()["total"] == 0


def test_asset_validation_rejects_blank_identity_and_invalid_programme(client):
    created = client.post("/api/assets", json=asset_payload())
    assert created.status_code == 201, created.text
    asset = created.json()

    blank_update = client.patch(f"/api/assets/{asset['id']}", json={"asset_code": "   "})
    assert blank_update.status_code == 422

    null_update = client.patch(f"/api/assets/{asset['id']}", json={"site": None})
    assert null_update.status_code == 422

    unchanged = client.get(f"/api/assets/{asset['id']}")
    assert unchanged.status_code == 200
    assert unchanged.json()["asset_code"] == "TST-SCADA-001"

    zero_programme = client.post(
        "/api/assets",
        json=asset_payload(asset_code="TST-SCADA-002", programme_id=0),
    )
    assert zero_programme.status_code == 422

    missing_programme = client.post(
        "/api/assets",
        json=asset_payload(asset_code="TST-SCADA-003", programme_id=999),
    )
    assert missing_programme.status_code == 400
    assert missing_programme.json()["detail"] == "programme_id does not exist"


def test_programme_linkage_and_dashboard_rollup(client):
    programme_response = client.post(
        "/api/programmes",
        json={
            "package_code": "OBP-T01",
            "title": "Test renewal package",
            "status": "design",
            "target_wave": "Wave 1",
            "budget_estimate": 100000,
            "contingency_percent": 25,
        },
    )
    assert programme_response.status_code == 201, programme_response.text
    programme = programme_response.json()

    asset = client.post(
        "/api/assets",
        json=asset_payload(programme_id=programme["id"]),
    ).json()
    package = client.get(f"/api/programmes/{programme['id']}").json()
    assert package["asset_count"] == 1
    assert package["total_budget"] == 125000
    assert package["average_risk"] == asset["risk_score"]

    dashboard = client.get("/api/dashboard/summary").json()
    assert dashboard["metrics"]["active_programmes"] == 1
    assert dashboard["metrics"]["funding_estimate"] == 125000


def test_programme_validation_rejects_blank_identity(client):
    blank = client.post("/api/programmes", json={"package_code": "   ", "title": "   "})
    assert blank.status_code == 422

    created = client.post(
        "/api/programmes",
        json={"package_code": "OBP-T03", "title": "Validation package"},
    )
    assert created.status_code == 201, created.text

    blank_patch = client.patch(f"/api/programmes/{created.json()['id']}", json={"title": "   "})
    assert blank_patch.status_code == 422


def test_csv_import_uses_row_savepoints_and_export(client):
    programme = client.post(
        "/api/programmes",
        json={"package_code": "OBP-T02", "title": "Imported package"},
    ).json()
    assert programme["package_code"] == "OBP-T02"

    csv_text = """asset_code,system_name,site,business_criticality,support_status,programme_code
IMP-001,Imported PLC,North,4,limited,OBP-T02
IMP-BAD,Bad rating,North,9,unknown,OBP-T02
IMP-002,Imported RTU,South,3,supported,OBP-T02
"""
    response = client.post(
        "/api/assets/import",
        files={"file": ("register.csv", io.BytesIO(csv_text.encode()), "text/csv")},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["created"] == 2
    assert result["failed"] == 1
    assert client.get("/api/assets").json()["total"] == 2

    exported = client.get("/api/assets/export.csv")
    assert exported.status_code == 200
    assert "IMP-001" in exported.text
    assert "IMP-002" in exported.text
    assert "IMP-BAD" not in exported.text
    assert "OBP-T02" in exported.text


def test_csv_import_rejects_unknown_direct_programme_id(client):
    csv_text = """asset_code,system_name,site,programme_id
IMP-NO-PROG,Imported orphan,North,999
"""
    response = client.post(
        "/api/assets/import",
        files={"file": ("register.csv", io.BytesIO(csv_text.encode()), "text/csv")},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["created"] == 0
    assert result["failed"] == 1
    assert "programme_id does not exist" in result["errors"][0]
    assert client.get("/api/assets").json()["total"] == 0
