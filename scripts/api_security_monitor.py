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
    """Format a grouped Discord alert using actual line breaks."""
    return ("**GUIONBOT API SECURITY — ALERT DIGEST**\n" +
            "\n".join(lines) +
            "\nNo automatic blocking.")

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
        badparams = sum(x.get("status") in (400, 405, 413) and "method" in x for x in five)
        paths = {x.get("path", "") for x in two if "method" in x}
        if badkeys >= thresholds.get("invalid_keys_5m", 5): incidents.append(("MEDIUM", "INVALID_KEYS", ip, badkeys))
        if forbidden >= thresholds.get("forbidden_2m", 3): incidents.append(("MEDIUM", "FORBIDDEN_ENDPOINTS", ip, forbidden))
        if len(paths) >= thresholds.get("distinct_paths_2m", 10): incidents.append(("MEDIUM", "PATH_SCAN", ip, len(paths)))
        if limited >= thresholds.get("rate_limit_5m", 10): incidents.append(("MEDIUM", "RATE_LIMIT", ip, limited))
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
        due = []
        due_keys = []
        for incident in incidents:
            severity, kind, ip, count = incident[:4]
            key = severity + ":" + kind + ":" + ip
            if now - state["alerts"].get(key, 0) < 1800:
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
            due.append(severity + " " + kind + " — " + ip + ": " +
                       str(count) + " event(s)" + detail)
            due_keys.append(key)
        if due:
            # Keep the Discord payload bounded. Unsent entries remain eligible
            # on the next minute check instead of being silently discarded.
            selected = []
            selected_keys = []
            used = len("**GUIONBOT API SECURITY — ALERT DIGEST**\n\nNo automatic blocking.")
            for line, key in zip(due, due_keys):
                if used + len(line) + 1 > 1750:
                    break
                selected.append(line)
                selected_keys.append(key)
                used += len(line) + 1
            message = build_alert_digest(selected)
            send(message)
            for key in selected_keys:
                state["alerts"][key] = now
        state["alerts"] = {k:v for k,v in state["alerts"].items() if now-v < 86400}
    if a.daily:
        from zoneinfo import ZoneInfo
        today = dt.datetime.now(ZoneInfo(cfg.get("timezone", "Europe/Paris"))).date().isoformat()
        if state.get("daily") != today:
            statuses = collections.Counter(str(x["status"]) for x in requests)
            suspicious = [x for x in requests if x["status"] in (400,401,403,404,405,413,429) or PROBE.search(x["target"]) or INJECT.search(x["target"])]
            types = collections.Counter(x.get("event_type", "UNKNOWN") for x in events)
            ips = collections.Counter(x["ip"] for x in suspicious).most_common(5)
            uri_rules = collections.Counter(rule for x in requests for rule in malicious_match(x["target"]))
            successful_sensitive = sum(is_high_risk_success(x) for x in requests)
            message = ("**GUIONBOT API — DAILY SECURITY REPORT**\nPrevious 24 hours\n"
                       "Requests: " + str(len(requests)) + "\nSuspicious HTTP/URI requests: " + str(len(suspicious)) +
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
