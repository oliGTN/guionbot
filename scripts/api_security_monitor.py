#!/usr/bin/env python3
import collections, datetime as dt, gzip, glob, json, re, time, urllib.request
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

CONFIG = "/home/pi/GuionBot/SERVER_SECRETS/api_security_monitor.json"
RX = re.compile(r'^(\S+) \S+ \S+ \[([^]]+)\] "([^"]*)" (\d{3}) (\S+)')
PROBE = re.compile(r'(\.\./|%2e%2e|/\.env|wp-admin|wp-login|phpmyadmin|\.git|/cgi-bin)', re.I)
INJECT = re.compile(r'(union(?:%20|\s)+select|sleep\s*\(|<script|information_schema)', re.I)


def malicious_match(target):
    labels = []
    rules = (
        ("path traversal", r'(\.\./|%2e%2e)'),
        ("environment-file probe", r'/\.env'),
        ("WordPress probe", r'wp-admin|wp-login'),
        ("phpMyAdmin probe", r'phpmyadmin'),
        ("Git metadata probe", r'\.git'),
        ("CGI probe", r'/cgi-bin'),
        ("SQL injection pattern", r'union(?:%20|\s)+select|sleep\s*\(|information_schema'),
        ("script injection pattern", r'<script'),
    )
    for label, expression in rules:
        if re.search(expression, target, re.I):
            labels.append(label)
    return labels

def safe_request_target(target):
    parts = urlsplit(target)
    query = urlencode([(key[:80], "[REDACTED]") for key, _ in parse_qsl(parts.query, keep_blank_values=True)[:12]])
    return urlunsplit(("", "", parts.path[:300], query, ""))[:500]

def clean_header(value, limit=180):
    return re.sub(r'[\x00-\x1f\x7f]', ' ', str(value))[:limit].strip()



SENSITIVE_PATH = re.compile(
    r'(^|/)(\.env(?:\.|$)|\.git(?:/|$)|wp-admin(?:/|$)|wp-login\.php$|'
    r'phpmyadmin(?:/|$)|cgi-bin(?:/|$))', re.I
)


def request_fingerprint(request):
    """Stable identity for one Apache request, independent of log rotation."""
    fields = (request.get("ip"), request.get("ts"), request.get("method"),
              request.get("target"), request.get("status"))
    return json.dumps(fields, separators=(",", ":"), ensure_ascii=True)


def is_high_risk_success(request):
    """Only treat a 2xx response as a high-severity disclosure/exploit signal."""
    if not 200 <= int(request.get("status", 0)) < 300:
        return False
    target = request.get("target", "")
    return bool(SENSITIVE_PATH.search(urlsplit(target).path) or INJECT.search(target))


def normalized_thresholds(config):
    """Tolerate accidental whitespace around JSON threshold names."""
    return {str(key).strip(): value for key, value in config.get("thresholds", {}).items()}


def collect_new_malicious(requests, state, now):
    """Return newly observed suspicious requests and retain a bounded dedupe ledger."""
    seen = state.setdefault("malicious_seen", {})
    fresh = []
    for request in requests:
        fingerprint = request_fingerprint(request)
        if fingerprint not in seen:
            fresh.append(request)
        seen[fingerprint] = request["ts"]
    state["malicious_seen"] = {
        key: ts for key, ts in seen.items() if now - ts < 172800
    }
    return fresh


def queue_malicious_activity(fresh, state, now):
    """Queue low-risk probes; return grouped repeated probes and high-risk successes."""
    pending_by_ip = state.setdefault("malicious_pending", {})
    high_risk_by_ip = collections.defaultdict(list)
    for request in fresh:
        if is_high_risk_success(request):
            high_risk_by_ip[request["ip"]].append(request)
        else:
            pending_by_ip.setdefault(request["ip"], []).append({
                "ts": request["ts"], "target": request["target"],
                "method": request["method"], "status": request["status"],
                "user_agent": request.get("user_agent", "-"),
                "rules": request.get("rules", [])
            })
    high_risk = []
    for ip, matches in high_risk_by_ip.items():
        latest = max(matches, key=lambda x: x["ts"])
        high_risk.append(("HIGH", "SENSITIVE_SUCCESS", ip, len(matches), latest))
    repeated = []
    for ip in list(pending_by_ip):
        pending = [x for x in pending_by_ip[ip] if now - x["ts"] <= 300]
        if len(pending) >= 3:
            latest = max(pending, key=lambda x: x["ts"])
            repeated.append(("MEDIUM", "MALICIOUS_URI", ip, len(pending), latest))
            pending = []
        if pending:
            pending_by_ip[ip] = pending
        else:
            del pending_by_ip[ip]
    return high_risk + repeated



def build_alert_digest(lines):
    """Format an immediate HIGH Discord alert using actual line breaks."""
    return ("**GUIONBOT API SECURITY — ALERT DIGEST**\n" +
            "\n".join(lines) +
            "\nNo automatic blocking.")


def queue_medium_incidents(incidents, state, now):
    """Coalesce MEDIUM incidents for an hourly digest without losing detections."""
    pending = state.setdefault("medium_pending", {})
    for incident in incidents:
        severity, kind, ip, count = incident[:4]
        if severity != "MEDIUM":
            continue
        key = kind + ":" + ip
        entry = pending.setdefault(key, {
            "kind": kind, "ip": ip, "count": 0,
            "first_seen": now, "last_seen": now
        })
        # Threshold incidents are evaluated on overlapping rolling windows;
        # keep their peak window count rather than adding the same requests
        # repeatedly. MALICIOUS_URI batches contain newly-seen fingerprints,
        # so their counts can be accumulated safely.
        if kind == "MALICIOUS_URI":
            entry["count"] += int(count)
        else:
            entry["count"] = max(int(entry["count"]), int(count))
        entry["last_seen"] = now
    if pending and "medium_digest_due" not in state:
        state["medium_digest_due"] = now + 3600
    return pending


def medium_digest_lines(pending):
    """Build one line per source IP, grouping all MEDIUM rules for that IP."""
    by_ip = collections.defaultdict(list)
    for entry in pending.values():
        by_ip[entry["ip"]].append(entry)
    lines = []
    for ip in sorted(by_ip):
        entries = sorted(by_ip[ip], key=lambda x: x["kind"])
        details = "; ".join(
            entry["kind"] + " " + str(entry["count"]) + " event(s)"
            for entry in entries
        )
        lines.append("MEDIUM SCAN — " + ip + ": " + details)
    return lines


def medium_digest_due(state, now):
    """Return whether the queued MEDIUM digest is due."""
    return bool(state.get("medium_pending")) and now >= state.get("medium_digest_due", now + 3600)


def high_alert_key(incident):
    """Deduplicate HIGH incidents by source and affected path where available."""
    severity, kind, ip, count = incident[:4]
    suffix = ""
    if len(incident) > 4:
        suffix = ":" + urlsplit(incident[4].get("target", "")).path[:200]
    return severity + ":" + kind + ":" + ip + suffix

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    p.add_argument("--daily", action="store_true")
    a = p.parse_args()
    if not (a.check or a.daily):
        p.error("choose --check or --daily")
    cfg = json.load(open(CONFIG))
    now = time.time()
    requests = []
    log_paths = [cfg["access_log"]] + glob.glob(cfg["access_log"] + ".[0-9]*")
    for log_path in log_paths:
        try:
            opener = gzip.open if log_path.endswith(".gz") else open
            with opener(log_path, "rt", encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = RX.match(line)
                    if not m:
                        continue
                    ip, stamp, request, status, size = m.groups()
                    try:
                        ts = dt.datetime.strptime(stamp, "%d/%b/%Y:%H:%M:%S %z").timestamp()
                    except ValueError:
                        continue
                    if ts < now - 86400:
                        continue
                    parts = request.split()
                    target = parts[1] if len(parts) > 1 else "/"
                    requests.append({"ip": ip, "ts": ts, "path": urlsplit(target).path,
                                     "target": target, "status": int(status),
                                     "method": parts[0] if len(parts) > 0 else "?",
                                     "user_agent": line.rstrip().split('"')[-2] if line.count('"') >= 6 else "-"})
        except OSError as e:
            if log_path == cfg["access_log"]:
                print("Apache log unavailable:", e)
    events = []
    first_event_day = dt.datetime.fromtimestamp(now - 86400, dt.timezone.utc).date()
    for path in Path(cfg["event_dir"]).glob("events-*.jsonl"):
        try:
            event_day = dt.date.fromisoformat(path.stem.replace("events-", "", 1))
            if event_day < first_event_day:
                continue
            for line in path.read_text(errors="replace").splitlines():
                try:
                    x = json.loads(line)
                    x["ts"] = dt.datetime.fromisoformat(x["timestamp"].replace("Z", "+00:00")).timestamp()
                    if x["ts"] >= now - 86400:
                        events.append(x)
                except Exception:
                    pass
        except OSError:
            pass
    thresholds = normalized_thresholds(cfg)
    grouped = collections.defaultdict(list)
    for x in requests:
        grouped[x["ip"]].append(x)
    for x in events:
        grouped[x.get("ip", "unknown")].append(x)
    incidents = []
    for ip, rows in grouped.items():
        five = [x for x in rows if now - x["ts"] <= 300]
        two = [x for x in rows if now - x["ts"] <= 120]
        badkeys = sum(x.get("event_type") in ("INVALID_API_KEY", "MALFORMED_AUTH") for x in five)
        forbidden = sum(x.get("event_type") == "ENDPOINT_FORBIDDEN" for x in two)
        # Count rate limits from the PHP event only; Apache's matching 429 is
        # the same request and must not be counted a second time.
        limited = sum(x.get("event_type") == "RATE_LIMIT_EXCEEDED" for x in five)
        # Only count malformed requests aimed at GuionBot API endpoints.
        # Website 400/405/413 responses are not API parameter incidents.
        badparams = sum(
            x.get("status") in (400, 405, 413)
            and str(x.get("path", "")).startswith("/api/v1/")
            and "method" in x
            for x in five
        )
        paths = {x.get("path", "") for x in two if "method" in x}
        forbidden_severity = (
            "HIGH" if any(x.get("event_type") == "ENDPOINT_FORBIDDEN"
                          and x.get("severity") == "HIGH" for x in two)
            else "MEDIUM"
        )
        rate_severity = (
            "HIGH" if any(x.get("event_type") == "RATE_LIMIT_EXCEEDED"
                          and x.get("severity") == "HIGH" for x in five)
            else "MEDIUM"
        )
        if badkeys >= thresholds.get("invalid_keys_5m", 5): incidents.append(("MEDIUM", "INVALID_KEYS", ip, badkeys))
        if forbidden >= thresholds.get("forbidden_2m", 3): incidents.append((forbidden_severity, "FORBIDDEN_ENDPOINTS", ip, forbidden))
        # A minimum of 20 distinct paths avoids alerting on low-volume
        # background noise even if the deployed config still says 10.
        path_scan_threshold = max(20, int(thresholds.get("distinct_paths_2m", 20)))
        if len(paths) >= path_scan_threshold: incidents.append(("MEDIUM", "PATH_SCAN", ip, len(paths)))
        if limited >= thresholds.get("rate_limit_5m", 10): incidents.append((rate_severity, "RATE_LIMIT", ip, limited))
        if badparams >= thresholds.get("invalid_params_5m", 20): incidents.append(("MEDIUM", "INVALID_PARAMETERS", ip, badparams))
    malicious_requests = []
    for x in requests:
        if PROBE.search(x["target"]) or INJECT.search(x["target"]):
            x["rules"] = malicious_match(x["target"])
            malicious_requests.append(x)
    statepath = Path(cfg["state_path"])
    statepath.parent.mkdir(parents=True, exist_ok=True)
    try: state = json.loads(statepath.read_text())
    except Exception: state = {"alerts": {}, "daily": None}
    state.setdefault("alerts", {})
    state.setdefault("daily", None)
    state.setdefault("malicious_pending", {})

    # On the first run after upgrading, baseline the existing 24h log window.
    # This prevents a one-time flood from replaying historical scan traffic.
    if "malicious_seen" not in state:
        state["malicious_seen"] = {
            request_fingerprint(x): x["ts"] for x in malicious_requests
        }
        fresh_malicious = []
    else:
        fresh_malicious = collect_new_malicious(malicious_requests, state, now)

    # Only newly observed requests can generate URI alerts. Routine probes
    # are silent unless repeated at least three times within five minutes.
    incidents.extend(queue_malicious_activity(fresh_malicious, state, now))
    def send(message):
        body = json.dumps({"content": message[:1900], "allowed_mentions": {"parse": []}}).encode()
        req = urllib.request.Request(
            cfg["discord_webhook"],
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status not in (200, 204): raise RuntimeError("Discord webhook failed")
    if a.check:
        from zoneinfo import ZoneInfo
        high_due = []
        high_keys = []
        for incident in incidents:
            severity, kind, ip, count = incident[:4]
            if severity != "HIGH":
                continue
            key = high_alert_key(incident)
            # A short per-incident cooldown suppresses repeat notifications
            # while allowing new HIGH incidents to surface promptly.
            if now - state["alerts"].get(key, 0) < 300:
                continue
            detail = ""
            if len(incident) > 4:
                x = incident[4]
                local_time = dt.datetime.fromtimestamp(
                    x["ts"], ZoneInfo(cfg.get("timezone", "Europe/Paris"))
                ).strftime("%H:%M:%S")
                detail = (" — " + local_time + ", " +
                          (", ".join(x.get("rules", [])) or "sensitive path") +
                          ", " + clean_header(x.get("method", "?")) + " " +
                          safe_request_target(x.get("target", "/")) +
                          ", HTTP " + str(x.get("status", "?")) +
                          ", UA " + clean_header(x.get("user_agent", "-"), 100))
            high_due.append("HIGH " + kind + " — " + ip + ": " +
                            str(count) + " event(s)" + detail)
            high_keys.append(key)

        # HIGH alerts are always sent immediately, before any MEDIUM digest.
        if high_due:
            # Send bounded messages separately. Record only keys whose message
            # was accepted by Discord, so a failure cannot silently drop HIGHs.
            batch_lines = []
            batch_keys = []
            batch_size = len("**GUIONBOT API SECURITY — ALERT DIGEST**\n\nNo automatic blocking.")
            for line, key in zip(high_due, high_keys):
                if batch_lines and batch_size + len(line) + 1 > 1750:
                    send(build_alert_digest(batch_lines))
                    for sent_key in batch_keys:
                        state["alerts"][sent_key] = now
                    batch_lines, batch_keys = [], []
                    batch_size = len("**GUIONBOT API SECURITY — ALERT DIGEST**\n\nNo automatic blocking.")
                batch_lines.append(line)
                batch_keys.append(key)
                batch_size += len(line) + 1
            if batch_lines:
                send(build_alert_digest(batch_lines))
                for sent_key in batch_keys:
                    state["alerts"][sent_key] = now

        queue_medium_incidents(incidents, state, now)
        if medium_digest_due(state, now):
            pending = state["medium_pending"]
            all_lines = medium_digest_lines(pending)
            selected_keys = []
            selected_lines = []
            used = len("**GUIONBOT API SECURITY — ALERT DIGEST**\n\nNo automatic blocking.")
            for line in all_lines:
                if used + len(line) + 1 > 1750:
                    break
                selected_lines.append(line)
                used += len(line) + 1
            if selected_lines:
                # Lines are emitted in sorted-IP order. Derive the selected
                # IPs from the same sorted groups (works for IPv4 and IPv6).
                ordered_ips = sorted({entry["ip"] for entry in pending.values()})
                selected_ips = set(ordered_ips[:len(selected_lines)])
                selected_keys = [
                    key for key, entry in pending.items()
                    if entry["ip"] in selected_ips
                ]
                send(build_alert_digest(selected_lines))
                for key in selected_keys:
                    pending.pop(key, None)
                if pending:
                    # Keep overflow queued; retry on the next monitor run.
                    state["medium_digest_due"] = now
                else:
                    state.pop("medium_digest_due", None)
        state["alerts"] = {k:v for k,v in state["alerts"].items() if now-v < 86400}
    if a.daily:
        from zoneinfo import ZoneInfo
        today = dt.datetime.now(ZoneInfo(cfg.get("timezone", "Europe/Paris"))).date().isoformat()
        if state.get("daily") != today:
            statuses = collections.Counter(str(x["status"]) for x in requests)
            uri_suspicious = [x for x in requests if PROBE.search(x["target"]) or INJECT.search(x["target"])]
            http_errors = [x for x in requests if x["status"] in (400,401,403,404,405,413,429)]
            types = collections.Counter(x.get("event_type", "UNKNOWN") for x in events)
            ips = collections.Counter(x["ip"] for x in uri_suspicious).most_common(5)
            uri_rules = collections.Counter(rule for x in requests for rule in malicious_match(x["target"]))
            successful_sensitive = sum(is_high_risk_success(x) for x in requests)
            message = ("**GUIONBOT API — DAILY SECURITY REPORT**\nPrevious 24 hours\n"
                       "Requests: " + str(len(requests)) + "\nURI-pattern requests: " + str(len(uri_suspicious)) +
                       "\nHTTP error responses (400/401/403/404/405/413/429): " + str(len(http_errors)) +
                       "\nURI detections by rule: " + str(dict(uri_rules)) +
                       "\nSuccessful sensitive/exploit-pattern responses (2xx): " + str(successful_sensitive) +
                       "\nPHP events: " + str(len(events)) + "\nActive threshold incidents: " + str(len(incidents)) +
                       "\nHTTP statuses: " + str(dict(statuses)) + "\nPHP event types: " + str(dict(types)) +
                       "\nTop suspicious IPs: " + str(ips) +
                       "\nAssessment: " + ("No active threshold incident detected." if not incidents else "Review grouped detections."))
            send(message)
            state["daily"] = today
    tmp = statepath.with_suffix(".tmp")
    tmp.write_text(json.dumps(state))
    tmp.replace(statepath)

if __name__ == "__main__":
    main()
