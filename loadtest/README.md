# k6 load test

The script models a shortener workload: 99% redirects and 1% link creation.
Redirects do not follow the external destination, so the measured request is
the shortener's `302` response.

The benchmark commands below use `docker-compose.loadtest.yml`, a
benchmark-only Compose override. It raises the API's per-IP link-creation
limit to `1000` for this local scenario and keeps the window at `60` seconds.
The base Compose configuration and production defaults remain unchanged
(`10` requests per `60` seconds). Do not use the override for production.

## Run with caching enabled

Start the stack with the benchmark override:

```bash
docker compose -f docker-compose.yml -f docker-compose.loadtest.yml up --build -d
k6 run -e BASE_URL=http://localhost -e CACHE_ENABLED=true loadtest/redirect.js
```

## Run with caching disabled

`CACHE_ENABLED` is read by the API at startup. Keep the same benchmark
override and recreate the API with the flag disabled, then run the same
scenario:

```bash
CACHE_ENABLED=false docker compose -f docker-compose.yml -f docker-compose.loadtest.yml up -d --build api
k6 run -e BASE_URL=http://localhost -e CACHE_ENABLED=false loadtest/redirect.js
```

PowerShell equivalent:

```powershell
$env:RATE_LIMIT_PER_MINUTE = "1000"
$env:RATE_LIMIT_WINDOW_SECONDS = "60"
$env:CACHE_ENABLED = "true"
docker compose -f docker-compose.yml -f docker-compose.loadtest.yml up --build -d
k6 run -e BASE_URL=http://localhost -e CACHE_ENABLED=true loadtest/redirect.js
$env:CACHE_ENABLED = "false"
docker compose -f docker-compose.yml -f docker-compose.loadtest.yml up -d --build api
k6 run -e BASE_URL=http://localhost -e CACHE_ENABLED=false loadtest/redirect.js
$env:CACHE_ENABLED = "true"
docker compose -f docker-compose.yml -f docker-compose.loadtest.yml up -d --build api
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

## Local benchmark results

The following results were measured on a local Windows machine using Docker
Compose, not on AWS or in a production environment.

- k6 version: `2.2.0`
- Duration: `30 seconds` per run
- Target arrival rate: `20 iterations/second`
- Workload: approximately `99%` redirects and `1%` link creation
- Benchmark-only rate-limit override: `1000` requests per `60` seconds
- Both runs passed all k6 checks and thresholds

| Metric | Cache enabled | Cache disabled |
| --- | ---: | ---: |
| HTTP requests/sec | 19.851601 | 19.983186 |
| p95 latency | 6.21 ms | 8.00 ms |
| Average latency | 4.83 ms | 5.97 ms |
| HTTP error rate | 0.00% | 0.00% |
| Total HTTP requests | 601 | 602 |
| Duration | 30 seconds | 30 seconds |

In these runs, caching enabled showed lower p95 latency than caching disabled
(6.21 ms versus 8.00 ms). This is an observation from these local runs, not a
universal or production performance claim.
