# Market Reactive cloud service

Personal ambient display: follows New Zealand → Sydney → Tokyo → Hong Kong → London → New York.
The ESP32 polls this service directly over its saved Wi-Fi. No always-on home computer is needed.

## Behavior

- Stay with the selected exchange until its final regular-session close, even when sessions overlap.
- Then select the next currently open exchange in the route. If none is open, show closed/idle.
- A lunch break pauses the current market; it does not trigger a handover.
- Calendars handle time zones, daylight saving, holidays and early closes. Unscheduled exchange closures may require calendar updates.
- On service restart, choose the first open exchange in route order. Deploy one worker/instance so the shared selection is consistent.

The default symbols are **ETF proxies**, not aggregate exchange readings:

| Exchange | Symbol | Proxy |
|---|---|---|
| NZX | FNZ.NZ | New Zealand shares |
| ASX | STW.AX | Australian shares |
| JPX | 1306.T | Japanese shares |
| HKEX | 2800.HK | Hong Kong shares |
| LSE | ISF.L | UK shares |
| NYSE session | SPY | US shares; ETF trades on NYSE Arca |

The original five proxies returned usable price/volume history on 20 October 2026; FNZ.NZ was verified on 21 October 2026.
New Zealand stays selected until its close, then hands over to Sydney if still open.
Free data uses the unofficial yfinance/Yahoo route: coverage, delay and availability are not guaranteed.
This is for your personal display; provider terms apply. A cloud provider may be rate-limited even when a local check works.
Failures are reported honestly; the service never substitutes simulated data in production.

## Signals

- **Change:** latest completed five-minute close versus the preceding trading session's adjusted daily close.
- **Relative volume:** last completed bar's volume divided by the median for the same local five-minute slot over up to 20 prior sessions (at least five samples).
- **Turbulence:** dispersion of recent intraday log returns divided by three times the median historical one-hour dispersion, clamped to 0–1. No overnight returns are included.
- Sparse/insufficient history returns `warming`; startup needs at least four completed bars in the current session.
- Data more than 30 minutes old returns `stale`. Valid frames are explicitly marked `delayed`, never claimed to be real-time.

The endpoint is `GET /v1/market`; `/health` is the health check. HTTP response fields:
`schema`, `status`, `exchange`, `symbol`, `generated_at`, `observed_at`, `valid_until`, `next_open`,
`change_pct`, `relative_volume`, `turbulence`. Timestamps are UTC Unix seconds.
All clients share a one-minute response cache and a five-minute provider cache. No query parameter can select arbitrary tickers or increase upstream requests.

## Deploy on Render

This folder is a standalone cloud project. Put **only this folder's contents** into a GitHub repository;
never upload the WLED device backups, which contain Wi-Fi credentials.

1. Sign in to Render and choose **New → Blueprint**, then connect the cloud repository.
2. Use the included `render.yaml` (Docker, free plan, one service). Review the plan before deployment.
3. Wait for `/health` to return `{"status":"ok","schema":1}`.
4. Check `/v1/market`. Closed markets legitimately return `closed`; during an open session verify `delayed` and plausible timestamps.
5. Give the service hostname, e.g. `your-service.onrender.com`, to the ESP32's **Market-Reactive → cloud-host** setting. Enter only the hostname, without `https://` or a path.

No API key is required for the free-feed adapter. No cloud resource has been created by this development work.
Render free services may sleep after inactivity and take time to wake. The ESP32 retries once a minute and shows idle if data expires.
Do not claim deployment complete until the endpoint is checked from the actual cloud host.

## Local development

Python 3.13:

```
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest -q
uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1
```

Tests use deterministic fixtures, not live data. `requirements.txt` pins the versions tested locally.
The Dockerfile provides a non-root cloud runtime. Docker itself was not available for an image build during development.

## References

- https://pandas-market-calendars.readthedocs.io/en/stable/
- https://github.com/ranaroussi/yfinance — personal-use/free-feed limitations
- https://render.com/docs/docker
- https://render.com/docs/free
- https://render.com/docs/tls
