#!/usr/bin/env python3
import collections, datetime as dt, gzip, glob, json, re, time, urllib.request
from pathlib import Path
from urllib.parse import urlsplit

CONFIG = "/home/pi/GuionBot/SERVER_SECRETS/api_security_monitor.json"
RX = re.compile(r'^(\\S+) \\S+ \\S+ \\[([^]]+)\\] "([^"]*)" (\\d{3}) (\\S+)')
PROBE = re.compile(r'(\.\./|%2e%2e|/\.env|wp-admin|wp-login|phpmyadmin|\.git|/cgi-bin)', re.I)
INJECT = re.compile(r'(union(?:%20|\s)+select|sleep\s*\(|<script|information_schema)', re.I)

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
                                     "target": target, "status": int(status)})
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
        limited = sum(x.get("event_type") == "RATE_LIMIT_EXCEEDED" or x.get("status") == 429 for x in five)
        badparams = sum(x.get("status") in (400, 405, 413) for x in five)
        paths = {x.get("path", "") for x in two}
        if badkeys >= cfg["thresholds"].get("invalid_keys_5m", 5): incidents.append(("MEDIUM", "INVALID_KEYS", ip, badkeys))
        if forbidden >= cfg["thresholds"].get("forbidden_2m", 3): incidents.append(("HIGH", "FORBIDDEN_ENDPOINTS", ip, forbidden))
        if len(paths) >= cfg["thresholds"].get("distinct_paths_2m", 10): incidents.append(("HIGH", "PATH_SCAN", ip, len(paths)))
        if limited >= cfg["thresholds"].get("rate_limit_5m", 10): incidents.append(("HIGH", "RATE_LIMIT", ip, limited))
        if badparams >= cfg["thresholds"].get("invalid_params_5m", 20): incidents.append(("MEDIUM", "INVALID_PARAMETERS", ip, badparams))
    for x in requests:
        if PROBE.search(x["target"]) or INJECT.search(x["target"]):
            incidents.append(("HIGH", "MALICIOUS_URI", x["ip"], 1))
    statepath = Path(cfg["state_path"])
    statepath.parent.mkdir(parents=True, exist_ok=True)
    try: state = json.loads(statepath.read_text())
    except Exception: state = {"alerts": {}, "daily": None}
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
        for severity, kind, ip, count in incidents:
            key = severity + ":" + kind + ":" + ip
            if now - state["alerts"].get(key, 0) >= 1800:
                send("**GUIONBOT API SECURITY — " + severity + "**\n" + kind + " from " + ip + ": " + str(count) + " events. No automatic blocking.")
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
            message = ("**GUIONBOT API — DAILY SECURITY REPORT**\nPrevious 24 hours\n"
                       "Requests: " + str(len(requests)) + "\nSuspicious: " + str(len(suspicious)) +
                       "\nPHP events: " + str(len(events)) + "\nThreshold incidents: " + str(len(incidents)) +
                       "\nHTTP statuses: " + str(dict(statuses)) + "\nPHP event types: " + str(dict(types)) +
                       "\nTop suspicious IPs: " + str(ips) +
                       "\nAssessment: " + ("No threshold incident detected." if not incidents else "Review detections."))
            send(message)
            state["daily"] = today
    tmp = statepath.with_suffix(".tmp")
    tmp.write_text(json.dumps(state))
    tmp.replace(statepath)

if __name__ == "__main__":
    main()
