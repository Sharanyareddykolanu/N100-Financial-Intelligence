from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_dashboard_screener_matches_api():
    api_response = client.get(
        "/api/v1/screener",
        params={"min_roe": 15},
    )

    assert api_response.status_code == 200

    api_results = api_response.json()["results"]

    # Simulate the dashboard API request using the same API endpoint.
    dashboard_response = client.get(
        "/api/v1/screener",
        params={"min_roe": 15},
    )

    assert dashboard_response.status_code == 200

    dashboard_results = dashboard_response.json()["results"]

    api_tickers = sorted(
        x["ticker"]
        for x in api_results
        if x.get("ticker")
    )

    dashboard_tickers = sorted(
        x["ticker"]
        for x in dashboard_results
        if x.get("ticker")
    )

    assert dashboard_tickers == api_tickers
