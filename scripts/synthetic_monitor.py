"""Synthetic monitoring bot — exercises all user flows against a live deployment.

Usage:
    MONITOR_BASE_URL=https://your-backend.example.com python scripts/synthetic_monitor.py

Exits 0 if all checks pass, 1 if any fail.
Sends a Telegram alert on failure if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set.

Environment variables:
    MONITOR_BASE_URL        Backend base URL (default: http://localhost:8000)
    TELEGRAM_BOT_TOKEN      Telegram bot token from BotFather
    TELEGRAM_CHAT_ID        Your Telegram chat ID
"""

import contextlib
import json
import os
import random
import sys
import time
import uuid
from datetime import UTC, datetime

import httpx

BASE_URL = os.environ.get("MONITOR_BASE_URL", "http://localhost:8000")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def _unique_place_id() -> str:
    """Return a place ID from the offline dataset so fetch-reviews returns real data."""
    return random.choice([
        "offline_lager_ale",
        "offline_lager_ale_raanana",
        "offline_lager_ale_herzliya",
        "offline_beer_garden",
        "offline_rami_levy",
        "offline_lala_market",
    ])


class SyntheticMonitor:
    def __init__(self):
        self.client = httpx.Client(base_url=f"{BASE_URL}/api", timeout=60)
        self.results: list[dict] = []
        self.token: str | None = None
        # Track created businesses so cleanup always runs
        self._biz_ids: list[str] = []

    def _record(self, name: str, success: bool, duration_ms: float, detail: str = "") -> None:
        self.results.append(
            {
                "name": name,
                "success": success,
                "duration_ms": round(duration_ms),
                "detail": detail,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        status = "PASS" if success else "FAIL"
        detail_str = f" — {detail}" if detail else ""
        print(f"  [{status}] {name} ({round(duration_ms)}ms){detail_str}", flush=True)

    def _timed(self, name: str, fn):
        t0 = time.perf_counter()
        try:
            result = fn()
            self._record(name, True, (time.perf_counter() - t0) * 1000)
            return result
        except AssertionError as exc:
            self._record(name, False, (time.perf_counter() - t0) * 1000, str(exc))
            return None
        except Exception as exc:
            self._record(name, False, (time.perf_counter() - t0) * 1000, str(exc))
            return None

    def _check(self, response: httpx.Response, expected_status: int) -> httpx.Response:
        if response.status_code != expected_status:
            raise AssertionError(
                f"Expected HTTP {expected_status}, got {response.status_code}: "
                f"{response.text[:300]}"
            )
        return response

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    # ── Check methods ───────────────────────────────────────────────────────────

    def check_health(self) -> bool:
        r = self._timed(
            "health_check",
            lambda: self._check(self.client.get("/health"), 200),
        )
        return r is not None

    def check_register(self) -> bool:
        email = f"bot-{uuid.uuid4().hex[:8]}@synthetic-monitor.com"
        password = "SyntheticBot123!"

        r = self._timed(
            "register",
            lambda: self._check(
                self.client.post("/auth/register", json={"email": email, "password": password}),
                201,
            ),
        )
        if r is None:
            return False
        self.token = r.json()["access_token"]
        return True

    def check_create_business(self, place_id: str) -> str | None:
        """Create a business and return its ID."""
        r = self._timed(
            "create_business",
            lambda: self._check(
                self.client.post(
                    "/businesses",
                    json={"place_id": place_id, "business_type": "bar"},
                    headers=self._headers(),
                ),
                201,
            ),
        )
        if r is None:
            return None
        biz_id = r.json()["id"]
        self._biz_ids.append(biz_id)
        return biz_id

    def check_fetch_reviews(self, biz_id: str, label: str = "fetch_reviews") -> bool:
        r = self._timed(
            label,
            lambda: self._check(
                self.client.post(
                    f"/businesses/{biz_id}/fetch-reviews",
                    headers=self._headers(),
                ),
                200,
            ),
        )
        return r is not None

    def check_analyze(self, biz_id: str, label: str = "analyze") -> bool:
        r = self._timed(
            label,
            lambda: self._check(
                self.client.post(
                    f"/businesses/{biz_id}/analyze",
                    headers=self._headers(),
                ),
                200,
            ),
        )
        return r is not None

    def check_dashboard(self, biz_id: str) -> bool:
        r = self._timed(
            "dashboard",
            lambda: self._check(
                self.client.get(
                    f"/businesses/{biz_id}/dashboard",
                    headers=self._headers(),
                ),
                200,
            ),
        )
        if r is None:
            return False
        data = r.json()
        # Verify analysis data made it through
        t0 = time.perf_counter()
        has_summary = bool(data.get("ai_summary"))
        self._record(
            "dashboard_has_summary",
            has_summary,
            (time.perf_counter() - t0) * 1000,
            "" if has_summary else "ai_summary is null after analysis",
        )
        return True

    def check_add_competitor(self, biz_id: str, comp_place_id: str) -> str | None:
        """Add a competitor and return the competitor business ID."""
        r = self._timed(
            "add_competitor",
            lambda: self._check(
                self.client.post(
                    f"/businesses/{biz_id}/competitors",
                    json={"place_id": comp_place_id, "business_type": "bar"},
                    headers=self._headers(),
                ),
                201,
            ),
        )
        if r is None:
            return None
        comp_biz_id = r.json()["business"]["id"]
        self._biz_ids.append(comp_biz_id)
        return comp_biz_id

    def check_comparison(self, biz_id: str, label: str = "comparison") -> bool:
        r = self._timed(
            label,
            lambda: self._check(
                self.client.post(
                    f"/businesses/{biz_id}/competitors/comparison",
                    headers=self._headers(),
                ),
                200,
            ),
        )
        return r is not None

    def cleanup(self) -> None:
        """Delete all businesses created during this run."""
        for biz_id in self._biz_ids:
            with contextlib.suppress(Exception):
                self.client.delete(f"/businesses/{biz_id}", headers=self._headers())

    # ── Main run ────────────────────────────────────────────────────────────────

    def run(self) -> list[dict]:
        print(f"\nSynthetic monitor → {BASE_URL}", flush=True)
        print(f"Run ID: {uuid.uuid4()}", flush=True)
        print(f"Time:   {datetime.now(UTC).isoformat()}\n", flush=True)

        try:
            if not self.check_health():
                self._send_alert("CRITICAL: Health check failed — backend may be down")
                return self.results

            if not self.check_register():
                self._send_alert("CRITICAL: Registration failed — auth or DB may be broken")
                return self.results

            # ── Target business ──────────────────────────────────────────────
            target_place_id = _unique_place_id()
            biz_id = self.check_create_business(target_place_id)
            if not biz_id:
                self._send_alert("CRITICAL: Business creation failed")
                return self.results

            self.check_fetch_reviews(biz_id)
            self.check_analyze(biz_id)
            self.check_dashboard(biz_id)

            # ── Competitor + comparison ──────────────────────────────────────
            comp_place_id = _unique_place_id()
            comp_biz_id = self.check_add_competitor(biz_id, comp_place_id)

            if comp_biz_id:
                self.check_fetch_reviews(comp_biz_id, label="fetch_competitor_reviews")
                self.check_analyze(comp_biz_id, label="analyze_competitor")

                # Cold comparison (LLM call)
                self.check_comparison(biz_id, label="comparison_cold")

                # Warm comparison (should hit MongoDB cache)
                self.check_comparison(biz_id, label="comparison_cached")

        finally:
            self.cleanup()

        # ── Report ────────────────────────────────────────────────────────────
        failures = [r for r in self.results if not r["success"]]
        passed = len(self.results) - len(failures)
        total = len(self.results)

        print(f"\nResult: {passed}/{total} checks passed", flush=True)

        if failures:
            lines = "\n".join(f"  - {f['name']}: {f['detail']}" for f in failures)
            self._send_alert(
                f"SYNTHETIC MONITOR: {len(failures)}/{total} checks failed\n{lines}"
            )

        return self.results

    def _send_alert(self, message: str) -> None:
        if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
            print(f"\nALERT (Telegram not configured): {message}", file=sys.stderr)
            return
        try:
            httpx.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": f"🔴 {message}"},
                timeout=10,
            )
        except Exception as exc:
            print(f"Failed to send Telegram alert: {exc}", file=sys.stderr)


if __name__ == "__main__":
    monitor = SyntheticMonitor()
    results = monitor.run()

    passed = sum(1 for r in results if r["success"])
    total = len(results)
    output = {"passed": passed, "total": total, "results": results}

    # Write results for CI artifact upload
    results_path = os.environ.get("SYNTHETIC_RESULTS_PATH", "/tmp/synthetic-results.json")
    try:
        with open(results_path, "w") as f:
            json.dump(output, f, indent=2)
    except Exception:
        pass

    print(json.dumps(output, indent=2))
    sys.exit(0 if passed == total else 1)
