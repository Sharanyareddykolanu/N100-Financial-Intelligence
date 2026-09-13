import time
import threading
import requests


API_URL = "http://127.0.0.1:8000/api/v1/screener"

results = []
lock = threading.Lock()


def call_screener():
    start = time.perf_counter()

    try:
        response = requests.get(
            API_URL,
            params={"min_roe": 15},
            timeout=10,
        )

        elapsed = time.perf_counter() - start

        with lock:
            results.append({
                "status": response.status_code,
                "time": elapsed,
            })

    except Exception as exc:
        elapsed = time.perf_counter() - start

        with lock:
            results.append({
                "status": None,
                "time": elapsed,
                "error": str(exc),
            })


def test_10_concurrent_screener_calls():
    results.clear()

    threads = []

    overall_start = time.perf_counter()

    for _ in range(10):
        thread = threading.Thread(target=call_screener)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    overall_time = time.perf_counter() - overall_start

    print("\n========== LOAD TEST ==========")
    print(f"Requests completed : {len(results)}")
    print(f"Total elapsed time : {overall_time:.3f} seconds")

    for index, result in enumerate(results, start=1):
        print(
            f"Request {index}: "
            f"status={result.get('status')} "
            f"time={result['time']:.3f}s"
        )

    assert len(results) == 10
    assert all(result["status"] == 200 for result in results)
    assert overall_time <10