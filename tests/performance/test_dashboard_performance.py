import time

from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)

TICKERS = ["TCS", "RELIANCE", "INFY", "HDFCBANK", "ICICIBANK"]


def test_company_profile_performance():
    print("\n========== COMPANY PROFILE PERFORMANCE ==========")

    timings = []

    for ticker in TICKERS:
        start = time.perf_counter()

        response = client.get(
            f"/api/v1/companies/{ticker}"
        )

        elapsed = time.perf_counter() - start
        timings.append(elapsed)

        print(
            f"{ticker}: "
            f"status={response.status_code}, "
            f"time={elapsed:.3f}s"
        )

        assert response.status_code == 200
        assert elapsed < 3

    print("-----------------------------------------------")
    print(f"Average time: {sum(timings) / len(timings):.3f}s")
    print(f"Maximum time: {max(timings):.3f}s")

    assert max(timings) < 3