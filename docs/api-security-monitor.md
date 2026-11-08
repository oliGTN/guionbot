# API security monitoring

## Scope and behavior
- Apache access log records all HTTP requests, including successful calls and unknown URLs.
- PHP JSONL events record malformed bearer authentication, invalid API keys, forbidden endpoint access, rate-limit failures and successful authentication.
- Immediate Discord alerts cover repeated invalid keys (5/5 min), forbidden endpoint access (3/2 min), 10 distinct paths/2 min, rate-limit events (10/5 min), bursts of invalid parameters (20/5 min), and suspicious URI/injection patterns.
- Alerts are deduplicated for 30 minutes per severity/type/source.
- A daily 24-hour Discord report is sent at 08:00 Europe/Paris, including quiet days.
- PHP event logs are retained for 90 days. No automatic IP blocking is performed.

## PHP event directory
Create a directory writable by Apache:
```bash
sudo install -d -o www-data -g www-data -m 0750 /var/log/guionbot-api-security
```
The shared authentication layer logs authentication and authorization events. It never records bearer values or request bodies.

## Apache access log
Add to the HTTPS virtual host serving guionbot.fr:
```apache
CustomLog ${APACHE_LOG_DIR}/guionbot-api-access.log combined
```
Then run `sudo apachectl configtest` and `sudo systemctl reload apache2`. Do not log Authorization headers or request bodies. Grant the monitor user read access to this log without making it world-readable.

## Configuration
Create `/home/pi/GuionBot/SERVER_SECRETS/api_security_monitor.json` from `docs/api-security-monitor.example.json`, replace the webhook placeholder with a private Discord webhook, and protect it:
```bash
sudo chown pi:www-data /home/pi/GuionBot/SERVER_SECRETS/api_security_monitor.json
sudo chmod 0640 /home/pi/GuionBot/SERVER_SECRETS/api_security_monitor.json
sudo install -d -o pi -g pi -m 0750 /var/lib/guionbot-api-security
```

## Schedule (pi crontab)
```cron
* * * * * /usr/bin/python3 /home/pi/GuionBot/guionbot-dev/scripts/api_security_monitor.py --check
0 8 * * * /usr/bin/python3 /home/pi/GuionBot/guionbot-dev/scripts/api_security_monitor.py --daily
```
Redirect cron output to a protected log. The daily state guard prevents duplicate reports.

## Retention
Install `/etc/logrotate.d/guionbot-api-security`:
```text
/var/log/guionbot-api-security/events-*.jsonl {
    daily
    rotate 90
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
    su www-data www-data
}
```
Apache access-log retention is separate. Ensure Apache's logrotate policy also retains 90 days if full request history is required.

## Validation
After configuring the webhook and Apache log, test a normal API call, missing/incorrect key, forbidden endpoint, invalid parameters, unknown path and repeated failures. Confirm that Apache captures all requests and PHP JSONL captures the expected authentication events. Tune thresholds against normal traffic.
