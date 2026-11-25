import os
import pytest
from httpx import ASGITransport, AsyncClient

os.environ["LLM_PROVIDER"] = "demo"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_enterpriseiq.db"

from app.analytics.engine import detect_metric_anomalies, forecast_metric  # noqa: E402
from app.core.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.processing.pipeline import process_uploaded_file  # noqa: E402
from app.services.seed_demo import seed_demo_data  # noqa: E402


def test_processing_pipeline_flags_missing_and_duplicates():
    csv_bytes = (
        "period,metric_name,actual_value,target_value\n"
        "2026-10,revenue,1338000,1610000\n"
        "2026-10,revenue,1338000,1610000\n"
        "2026-11,revenue,,1620000\n"
    ).encode("utf-8")
    res = process_uploaded_file("test_metrics.csv", csv_bytes)
    assert res["stats"]["total_records"] == 3
    assert res["stats"]["duplicate_records"] == 1
    assert res["stats"]["invalid_records"] == 1
    assert len(res["validation_issues"]) >= 2


def test_anomaly_and_forecast_engines():
    series = [
        {"period": f"2026-{m:02d}", "metric_name": "operating_expenses", "actual_value": v}
        for m, v in enumerate([900, 905, 910, 915, 920, 925, 1380], start=1)
    ]
    anomalies = detect_metric_anomalies(series)
    assert any(a["period"] == "2026-07" for a in anomalies)

    forecasts = forecast_metric(series, horizon=3)
    assert len(forecasts) == 3
    assert all(f["lower_bound"] <= f["predicted_value"] <= f["upper_bound"] for f in forecasts)


@pytest.fixture(autouse=True)
async def reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        await seed_demo_data(db)
    yield


@pytest.mark.asyncio
async def test_full_demo_workflow_and_rbac():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login as demo CEO
        login = await client.post("/api/auth/login", json={"email": "ceo@meridian-demo.com", "password": "DemoPass123!"})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # Dashboard overview & consistent demo numbers
        ov = await client.get("/api/dashboard/overview", headers=headers)
        assert ov.status_code == 200
        assert ov.json()["kpis"]["revenue"] == 1310000.0

        # AI Copilot grounded answer with citations
        ask = await client.post("/api/ai/ask", headers=headers, json={"question": "Why is our operational cost increasing?"})
        assert ask.status_code == 200
        assert len(ask.json()["citations"]) >= 1

        # Create & update corrective action
        act = await client.post("/api/actions", headers=headers, json={"title": "Audit West freight lanes", "priority": "high"})
        assert act.status_code == 201
        upd = await client.patch(f"/api/actions/{act.json()['id']}", headers=headers, json={"status": "Completed", "outcome_note": "Saved $18K/mo"})
        assert upd.status_code == 200
        assert upd.json()["progress_pct"] == 100

        # RBAC check: analyst cannot view audit logs
        analyst_login = await client.post("/api/auth/login", json={"email": "analyst@meridian-demo.com", "password": "DemoPass123!"})
        analyst_headers = {"Authorization": f"Bearer {analyst_login.json()['access_token']}"}
        audit_denied = await client.get("/api/settings/audit-logs", headers=analyst_headers)
        assert audit_denied.status_code == 403
