import requests

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

def get_screener_results(min_roe=15):
    response = requests.get(
        f"{API_BASE_URL}/screener",
        params={"min_roe": min_roe},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["results"]
