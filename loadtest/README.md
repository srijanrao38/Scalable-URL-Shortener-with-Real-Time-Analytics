# k6 load test

The script models a shortener workload: 99% redirects and 1% link creation.
Redirects do not follow the external destination, so the measured request is
the shortener's `302` response.

## Run with caching enabled

Start the stack with the default configuration:

```bash
docker compose up --build -d
k6 run -e BASE_URL=http://localhost -e CACHE_ENABLED=true loadtest/redirect.js
```

## Run with caching disabled

`CACHE_ENABLED` is read by the API at startup. Recreate the API with the flag
disabled, then run the same scenario:

```bash
CACHE_ENABLED=false docker compose up -d --build api
k6 run -e BASE_URL=http://localhost -e CACHE_ENABLED=false loadtest/redirect.js
```

PowerShell equivalent:

```powershell
$env:CACHE_ENABLED = "false"
docker compose up -d --build api
k6 run -e BASE_URL=http://localhost -e CACHE_ENABLED=false loadtest/redirect.js
$env:CACHE_ENABLED = "true"
docker compose up -d --build api
```

To reuse an existing seed link instead of creating one during setup:

```bash
k6 run -e BASE_URL=http://localhost -e SEED_CODE=abc1234 loadtest/redirect.js
```

Record these values for each run:

- requests per second (`http_reqs / duration`)
- p95 latency (`http_req_duration p(95)`)
- error rate (`http_req_failed rate`)
- the cache mode and exact test duration

The script runs for 30 seconds at a 20-request/second arrival rate. The
thresholds are intentionally modest starting points for a local EC2-sized
demo deployment.
