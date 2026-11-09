import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "api_security_monitor.py"
SPEC = importlib.util.spec_from_file_location("api_security_monitor", SCRIPT)
monitor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(monitor)


def request(ip="203.0.113.10", ts=1000, target="/.env", status=404):
    return {
        "ip": ip, "ts": ts, "target": target, "status": status,
        "method": "GET", "path": target, "user_agent": "test-agent"
    }


class SecurityMonitorTests(unittest.TestCase):
    def test_single_probe_is_not_an_alert(self):
        state = {}
        fresh = monitor.collect_new_malicious([request()], state, 1000)
        incidents = monitor.queue_malicious_activity(fresh, state, 1000)
        self.assertEqual(incidents, [])
        self.assertEqual(len(state["malicious_pending"]["203.0.113.10"]), 1)

    def test_three_probes_within_five_minutes_are_grouped_medium(self):
        state = {}
        rows = [request(ts=1000), request(ts=1060, target="/.git/config"),
                request(ts=1120, target="/wp-login.php")]
        fresh = monitor.collect_new_malicious(rows, state, 1120)
        incidents = monitor.queue_malicious_activity(fresh, state, 1120)
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0][:4], ("MEDIUM", "MALICIOUS_URI", "203.0.113.10", 3))

    def test_old_pending_probes_expire(self):
        state = {"malicious_pending": {"203.0.113.10": [
            {"ts": 100, "target": "/.env", "method": "GET", "status": 404,
             "user_agent": "-", "rules": ["environment-file probe"]}
        ]}}
        incidents = monitor.queue_malicious_activity([], state, 500)
        self.assertEqual(incidents, [])
        self.assertNotIn("203.0.113.10", state["malicious_pending"])

    def test_seen_request_is_not_reprocessed(self):
        row = request()
        state = {}
        first = monitor.collect_new_malicious([row], state, 1000)
        second = monitor.collect_new_malicious([row], state, 1001)
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])

    def test_successful_sensitive_path_is_high(self):
        row = request(status=200)
        self.assertTrue(monitor.is_high_risk_success(row))
        state = {}
        incidents = monitor.queue_malicious_activity([row], state, 1000)
        self.assertEqual(incidents[0][:3], ("HIGH", "SENSITIVE_SUCCESS", "203.0.113.10"))

    def test_not_found_sensitive_path_is_not_high(self):
        self.assertFalse(monitor.is_high_risk_success(request(status=404)))

    def test_successful_exploit_pattern_is_high(self):
        row = request(target="/api/v1/items?id=1%20UNION%20SELECT%201", status=200)
        self.assertTrue(monitor.is_high_risk_success(row))

    def test_threshold_keys_ignore_accidental_whitespace(self):
        result = monitor.normalized_thresholds({"thresholds": {" rate_limit_5m ": 7}})
        self.assertEqual(result["rate_limit_5m"], 7)

    def test_alert_digest_uses_real_newlines(self):
        message = monitor.build_alert_digest(["MEDIUM PATH_SCAN — 203.0.113.10: 10 event(s)",
                                              "MEDIUM MALICIOUS_URI — 203.0.113.10: 3 event(s)"])
        self.assertIn("\n", message)
        self.assertNotIn("\\n", message)
        self.assertEqual(len(message.splitlines()), 4)

    def test_fingerprint_is_stable(self):
        row = request()
        self.assertEqual(monitor.request_fingerprint(row), monitor.request_fingerprint(dict(row)))

    def test_medium_threshold_incidents_are_coalesced_without_rolling_window_double_count(self):
        state = {}
        incidents = [
            ("MEDIUM", "PATH_SCAN", "203.0.113.10", 12),
            ("MEDIUM", "PATH_SCAN", "203.0.113.10", 15),
            ("MEDIUM", "INVALID_PARAMETERS", "203.0.113.10", 22),
            ("MEDIUM", "MALICIOUS_URI", "203.0.113.10", 3),
            ("MEDIUM", "MALICIOUS_URI", "203.0.113.10", 2),
        ]
        monitor.queue_medium_incidents(incidents, state, 1000)
        self.assertEqual(state["medium_pending"]["PATH_SCAN:203.0.113.10"]["count"], 15)
        self.assertEqual(state["medium_pending"]["INVALID_PARAMETERS:203.0.113.10"]["count"], 22)
        self.assertEqual(state["medium_pending"]["MALICIOUS_URI:203.0.113.10"]["count"], 5)
        self.assertEqual(state["medium_digest_due"], 4600)

    def test_medium_digest_groups_rules_by_ip(self):
        pending = {
            "PATH_SCAN:203.0.113.10": {"ip": "203.0.113.10", "kind": "PATH_SCAN", "count": 15},
            "MALICIOUS_URI:203.0.113.10": {"ip": "203.0.113.10", "kind": "MALICIOUS_URI", "count": 5},
            "INVALID_PARAMETERS:203.0.113.11": {"ip": "203.0.113.11", "kind": "INVALID_PARAMETERS", "count": 22},
        }
        lines = monitor.medium_digest_lines(pending)
        self.assertEqual(len(lines), 2)
        self.assertIn("PATH_SCAN 15 event(s)", lines[0])
        self.assertIn("MALICIOUS_URI 5 event(s)", lines[0])

    def test_medium_digest_is_hourly(self):
        state = {}
        monitor.queue_medium_incidents([("MEDIUM", "PATH_SCAN", "203.0.113.10", 12)], state, 1000)
        self.assertFalse(monitor.medium_digest_due(state, 4599))
        self.assertTrue(monitor.medium_digest_due(state, 4600))

    def test_high_incident_is_not_queued_as_medium(self):
        state = {}
        monitor.queue_medium_incidents([("HIGH", "SENSITIVE_SUCCESS", "203.0.113.10", 1)], state, 1000)
        self.assertEqual(state["medium_pending"], {})

    def test_high_alert_key_separates_different_sensitive_paths(self):
        a = ("HIGH", "SENSITIVE_SUCCESS", "203.0.113.10", 1, request(target="/.env", status=200))
        b = ("HIGH", "SENSITIVE_SUCCESS", "203.0.113.10", 1, request(target="/.git/config", status=200))
        self.assertNotEqual(monitor.high_alert_key(a), monitor.high_alert_key(b))


if __name__ == "__main__":
    unittest.main()
