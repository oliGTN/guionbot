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
This is an Apache configuration directive, not a shell command. Put it inside the relevant `<VirtualHost *:443>` block. Then run `sudo apachectl configtest` and `sudo systemctl reload apache2`. Do not log Authorization headers or request bodies. Grant the monitor user read access to this log without making it world-readable.

## Create the Discord webhook

Create a dedicated private channel in the Discord server where you want to receive alerts (for example, `#api-security-alerts`). Restrict access to trusted administrators.

1. Open Discord and select the server.
2. Open **Server Settings**.
3. Go to **Integrations** → **Webhooks**. Depending on the Discord client layout, Webhooks may appear directly under Integrations.
4. Click **New Webhook** (or **Create Webhook**).
5. Give it a clear name, such as `GuionBot API Security`.
6. Set **Channel** to the private `#api-security-alerts` channel.
7. Click **Copy Webhook URL** and keep the URL private.

A webhook URL contains a secret token: anyone who obtains it can post messages to that channel. Do not paste it into GitHub, commit it to the repository, include it in logs, or share it in screenshots. If it is exposed, return to **Server Settings** → **Integrations** → **Webhooks**, select the webhook and regenerate its URL (or delete it and create a replacement).

## Configuration

On the Raspberry Pi, create the monitor configuration from the example:
```bash
cd /home/pi/GuionBot/guionbot-dev
cp docs/api-security-monitor.example.json /home/pi/GuionBot/SERVER_SECRETS/api_security_monitor.json
nano /home/pi/GuionBot/SERVER_SECRETS/api_security_monitor.json
```

Replace only the `discord_webhook` placeholder with the URL copied from Discord. Keep the other settings unless you deliberately want to tune them. The file should look like this (use your actual webhook URL; this is only a format example):
```json
{
  "discord_webhook": "https://discord.com/api/webhooks/WEBHOOK_ID/WEBHOOK_TOKEN",
  "access_log": "/var/log/apache2/guionbot-api-access.log",
  "event_dir": "/var/log/guionbot-api-security",
  "state_path": "/var/lib/guionbot-api-security/state.json",
  "timezone": "Europe/Paris",
  "thresholds": {
    "invalid_keys_5m": 5,
    "forbidden_2m": 3,
    "distinct_paths_2m": 10,
    "rate_limit_5m": 10,
    "invalid_params_5m": 20
  }
}
```

Protect the configuration file so the webhook is not readable by other local users:
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
