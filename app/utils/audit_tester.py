import json
import httpx
import asyncio
import time
from datetime import datetime
from typing import Any


async def run_test_scenario(
    client: httpx.AsyncClient,
    name: str,
    endpoint: str
) -> dict[str, Any]:
    """Launches single test and returns metrics."""
    start_time = time.perf_counter()
    try:
        response = await client.get(endpoint)
        latency = (time.perf_counter() - start_time) * 1000  # ms

        response_data = None
        results_count = 0

        if response.status_code == 200:
            try:
                response_data = response.json()
                results_count = len(response_data) if isinstance(response_data, list) else 1
            except (json.JSONDecodeError, ValueError) as e:
                response_data = {
                    "error": f"Failed to parse JSON response: {str(e)}",
                    "raw": response.text
                }

        status = "PASSED" if response.status_code == 200 and len(response.json()) > 0 else "FAILED"

        return {
            "scenario": name,
            "endpoint": endpoint,
            "status": status,
            "http_status": response.status_code,
            "results_count": results_count,
            "latency_ms": round(latency, 2),
            "response_data": response_data,
            "error": None if response.status_code == 200 else response.text
        }
    except Exception as e:
        return {
            "scenario": name,
            "endpoint": endpoint,
            "status": "ERROR",
            "latency_ms": round((time.perf_counter() - start_time) * 1000, 2),
            "error": str(e)
        }


async def generate_report() -> None:
    # Read IDs from test_ids.json
    try:
        with open("test_ids.json", "r") as f:
            ids = json.load(f)
    except FileNotFoundError:
        print("test_ids.json not found. Run seeder.py!")
        return

    report = {
        "timestamp": datetime.now().isoformat(),
        "environment": "Docker-Cassandra-Cluster-5.0",
        "summary": {"passed": 0, "failed": 0, "errors": 0},
        "details": []
    }

    scenarios = [
        ("Audit by Person", f"/api_v1/audit/person/{ids['person_id']}"),
        ("Audit by Institution", f"/api_v1/audit/institution/{ids['institution_id']}"),
        ("Audit by Change Code", f"/api_v1/audit/code/{ids['code']}")
    ]

    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=10.0) as client:
        print("Starting tests execution and report generation...")

        for name, endpoint in scenarios:
            result = await run_test_scenario(client, name, endpoint)
            report["details"].append(result)

            # Updating summary
            if result["status"] == "PASSED":
                report["summary"]["passed"] += 1
            elif result["status"] == "FAILED":
                report["summary"]["failed"] += 1
            else:
                report["summary"]["errors"] += 1

    # Saving report to file
    report_file = "audit_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Tests executed. Report saved to: {report_file}")
    print(f"Summary: {report['summary']['passed']} PASSED, {report['summary']['failed']} FAILED")


if __name__ == "__main__":
    asyncio.run(generate_report())
