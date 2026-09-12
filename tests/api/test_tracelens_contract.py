def test_tracelens_openapi_exposes_investigation_workflow() -> None:
    from tracelens.main import app

    paths = app.openapi()["paths"]
    expected = {
        "/api/overview",
        "/api/services/{service_name}",
        "/api/incidents",
        "/api/incidents/{incident_id}",
        "/api/simulator/scenarios/{scenario_id}/start",
        "/api/events",
    }
    assert expected.issubset(paths)
