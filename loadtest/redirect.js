import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = (__ENV.BASE_URL || "http://localhost").replace(/\/$/, "");
const CACHE_ENABLED = __ENV.CACHE_ENABLED || "true";

export const options = {
  scenarios: {
    redirect_traffic: {
      executor: "constant-arrival-rate",
      rate: 20,
      timeUnit: "1s",
      duration: "30s",
      preAllocatedVUs: 10,
      maxVUs: 50,
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<500"],
  },
};

export function setup() {
  if (__ENV.SEED_CODE) {
    return { code: __ENV.SEED_CODE };
  }

  const response = http.post(
    `${BASE_URL}/api/links`,
    JSON.stringify({ long_url: "https://example.com/load-test-destination" }),
    { headers: { "Content-Type": "application/json" } },
  );
  check(response, { "seed link created": (res) => res.status === 201 });
  if (response.status !== 201) {
    throw new Error(`Could not create seed link: ${response.status} ${response.body}`);
  }
  return { code: response.json("code") };
}

export default function (data) {
  // A low create percentage keeps the benchmark representative of a shortener.
  if (Math.random() < 0.01) {
    const response = http.post(
      `${BASE_URL}/api/links`,
      JSON.stringify({ long_url: `https://example.com/load-test/${__VU}/${__ITER}` }),
      { headers: { "Content-Type": "application/json" }, tags: { operation: "create" } },
    );
    check(response, { "create returns 201": (res) => res.status === 201 });
  } else {
    const response = http.get(`${BASE_URL}/${data.code}`, {
      redirects: 0,
      tags: { operation: `redirect-cache-${CACHE_ENABLED}` },
    });
    check(response, { "redirect returns 302": (res) => res.status === 302 });
  }
  sleep(0.05);
}
