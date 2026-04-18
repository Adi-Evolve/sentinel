from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "demo_logs" / "noisy_mixed.log"

NORMAL_IPS = [
    "49.36.81.12",
    "52.172.14.90",
    "18.139.22.71",
    "34.93.210.45",
    "91.189.91.157",
    "104.26.12.44",
    "13.127.221.19",
    "172.67.181.44",
    "203.0.113.10",
    "198.51.100.22",
    "192.0.2.8",
]
USERS = ["admin", "ops", "ubuntu", "deploy", "monitor", "service", "backup", "nginx", "api"]
HTTP_PATHS = ["/", "/health", "/api/status", "/login", "/dashboard", "/metrics", "/admin", "/assets/app.js"]


def main() -> int:
    rng = random.Random(20260414)
    lines: list[str] = []
    start = datetime(2026, 4, 13, 0, 0, 0)

    for index in range(12000):
        current = start + timedelta(seconds=index * 3)
        ip = rng.choice(NORMAL_IPS)
        if rng.random() < 0.52:
            user = rng.choice(USERS)
            port = rng.randint(30000, 65000)
            outcome = rng.random()
            if outcome < 0.12:
                message = f"Failed password for {user} from {ip} port {port} ssh2"
            elif outcome < 0.30:
                message = f"Accepted password for {user} from {ip} port {port} ssh2"
            else:
                message = f"Connection closed by {ip} port {port} [preauth]"
            lines.append(f"{current:%b %d %H:%M:%S} server sshd[1234]: {message}")
        else:
            method = "GET" if rng.random() < 0.85 else "POST"
            path = rng.choice(HTTP_PATHS)
            status = rng.choices([200, 204, 301, 401, 403, 404, 500], weights=[55, 8, 7, 8, 8, 10, 4])[0]
            bytes_sent = rng.randint(120, 5400)
            lines.append(
                f"{ip} - - [{current:%d/%b/%Y:%H:%M:%S} +0000] \"{method} {path} HTTP/1.1\" {status} {bytes_sent}"
            )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
