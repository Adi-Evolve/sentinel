from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "demo_logs"
NORMAL_IPS = [
    "49.36.81.12",
    "52.172.14.90",
    "18.139.22.71",
    "34.93.210.45",
    "91.189.91.157",
    "104.26.12.44",
    "13.127.221.19",
    "172.67.181.44",
]
USERS = ["admin", "ops", "ubuntu", "deploy", "monitor", "service", "backup", "nginx"]
MASSIVE_NORMAL_IPS = [
    "49.36.81.12",
    "52.172.14.90",
    "18.139.22.71",
    "34.93.210.45",
    "91.189.91.157",
    "104.26.12.44",
    "13.127.221.19",
    "172.67.181.44",
    "103.86.99.13",
    "185.199.111.153",
    "151.101.1.69",
    "142.250.183.110",
    "13.233.221.9",
    "35.154.61.17",
    "52.66.114.77",
    "3.108.42.98",
    "157.240.18.35",
    "20.204.243.166",
    "20.205.243.166",
    "93.184.216.34",
]
ATTACKER_IPS = [
    "185.220.101.47",
    "45.95.147.11",
    "198.98.51.189",
    "109.70.100.21",
    "203.0.113.45",
    "198.51.100.73",
]


def build_brute_force_log() -> str:
    rng = random.Random(42)
    lines: list[str] = []
    start = datetime(2026, 4, 13, 0, 0, 0)

    for index in range(7952):
        current = start + timedelta(seconds=index * 7)
        ip = rng.choice(NORMAL_IPS)
        user = rng.choice(USERS)
        port = rng.randint(30000, 65000)
        outcome = rng.random()
        if outcome < 0.18:
            message = f"Failed password for {user} from {ip} port {port} ssh2"
        elif outcome < 0.44:
            message = f"Accepted password for {user} from {ip} port {port} ssh2"
        else:
            message = f"Connection closed by {ip} port {port} [preauth]"
        lines.append(_auth_line(current, message))

    attack_start = datetime(2026, 4, 13, 2, 31, 0)
    for offset in range(47):
        current = attack_start + timedelta(seconds=4 * offset)
        lines.append(
            _auth_line(
                current,
                f"Failed password for root from 185.220.101.47 port {48122 + offset} ssh2",
            )
        )
    lines.append(
        _auth_line(
            datetime(2026, 4, 13, 2, 34, 52),
            "Accepted password for root from 185.220.101.47 port 48200 ssh2",
        )
    )

    return "\n".join(sorted(lines)) + "\n"


def build_brute_force_log_massive(normal_lines: int, attack_bursts: int) -> str:
    rng = random.Random(42042)
    lines: list[str] = []
    start = datetime(2026, 4, 13, 0, 0, 0)

    for index in range(normal_lines):
        current = start + timedelta(seconds=index * 2)
        ip = rng.choice(MASSIVE_NORMAL_IPS)
        user = rng.choice(USERS)
        port = rng.randint(30000, 65000)
        outcome = rng.random()
        if outcome < 0.20:
            message = f"Failed password for {user} from {ip} port {port} ssh2"
        elif outcome < 0.53:
            message = f"Accepted password for {user} from {ip} port {port} ssh2"
        else:
            message = f"Connection closed by {ip} port {port} [preauth]"
        lines.append(_auth_line(current, message))

    attack_start = datetime(2026, 4, 13, 6, 0, 0)
    for burst in range(attack_bursts):
        base = attack_start + timedelta(minutes=burst * 17)
        attacker = ATTACKER_IPS[burst % len(ATTACKER_IPS)]
        target_user = "root" if burst % 2 == 0 else "admin"
        burst_failures = 65 + (burst % 8)
        for offset in range(burst_failures):
            current = base + timedelta(seconds=offset * 3)
            lines.append(
                _auth_line(
                    current,
                    f"Failed password for {target_user} from {attacker} port {48000 + offset} ssh2",
                )
            )
        lines.append(
            _auth_line(
                base + timedelta(minutes=4, seconds=10),
                f"Accepted password for {target_user} from {attacker} port 57999 ssh2",
            )
        )

    return "\n".join(sorted(lines)) + "\n"


def build_impossible_travel_log() -> str:
    rng = random.Random(84)
    lines: list[str] = []
    start = datetime(2026, 4, 13, 0, 0, 0)
    baseline_ips = ["49.36.81.12", "52.172.14.90", "34.93.210.45", "13.127.221.19"]

    for index in range(7998):
        current = start + timedelta(seconds=index * 9)
        ip = rng.choice(baseline_ips)
        user = rng.choice(USERS)
        port = rng.randint(30000, 65000)
        outcome = rng.random()
        if outcome < 0.22:
            message = f"Accepted password for {user} from {ip} port {port} ssh2"
        elif outcome < 0.42:
            message = f"Failed password for {user} from {ip} port {port} ssh2"
        else:
            message = f"Connection closed by {ip} port {port} [preauth]"
        lines.append(_auth_line(current, message))

    lines.append(
        _auth_line(
            datetime(2026, 4, 13, 10, 0, 12),
            "Accepted password for ajay.kumar from 103.21.58.1 port 51220 ssh2",
        )
    )
    lines.append(
        _auth_line(
            datetime(2026, 4, 13, 10, 18, 44),
            "Accepted password for ajay.kumar from 85.214.132.1 port 53311 ssh2",
        )
    )

    return "\n".join(sorted(lines)) + "\n"


def build_impossible_travel_log_massive(normal_lines: int, travel_events: int) -> str:
    rng = random.Random(84084)
    lines: list[str] = []
    start = datetime(2026, 4, 13, 0, 0, 0)

    for index in range(normal_lines):
        current = start + timedelta(seconds=index * 3)
        ip = rng.choice(MASSIVE_NORMAL_IPS)
        user = rng.choice(USERS)
        port = rng.randint(30000, 65000)
        outcome = rng.random()
        if outcome < 0.24:
            message = f"Accepted password for {user} from {ip} port {port} ssh2"
        elif outcome < 0.45:
            message = f"Failed password for {user} from {ip} port {port} ssh2"
        else:
            message = f"Connection closed by {ip} port {port} [preauth]"
        lines.append(_auth_line(current, message))

    travel_users = ["ajay.kumar", "neha.shah", "prod.admin", "infra.ops"]
    for idx in range(travel_events):
        base = datetime(2026, 4, 13, 10, 0, 0) + timedelta(minutes=idx * 23)
        user = travel_users[idx % len(travel_users)]
        lines.append(
            _auth_line(
                base + timedelta(seconds=12),
                f"Accepted password for {user} from 103.21.58.1 port {51220 + idx} ssh2",
            )
        )
        lines.append(
            _auth_line(
                base + timedelta(minutes=18, seconds=44),
                f"Accepted password for {user} from 85.214.132.1 port {53311 + idx} ssh2",
            )
        )

    return "\n".join(sorted(lines)) + "\n"


def build_attack_storm_log(total_lines: int) -> str:
    rng = random.Random(220022)
    lines: list[str] = []
    start = datetime(2026, 4, 12, 22, 0, 0)

    hot_endpoints = ["/login", "/wp-admin", "/admin", "/api/auth", "/xmlrpc.php", "/phpmyadmin"]
    users = USERS + ["root", "postgres", "oracle", "jenkins"]

    for index in range(total_lines):
        current = start + timedelta(seconds=index)
        attacker = rng.choice(ATTACKER_IPS)
        user = rng.choice(users)
        endpoint = rng.choice(hot_endpoints)
        port = rng.randint(20000, 65000)
        pattern = index % 9
        if pattern in {0, 1, 2, 3, 4}:
            message = f"Failed password for {user} from {attacker} port {port} ssh2"
        elif pattern == 5:
            message = f"Accepted password for {user} from {attacker} port {port} ssh2"
        elif pattern == 6:
            message = f"Invalid user {user} from {attacker} port {port}"
        elif pattern == 7:
            message = f"Connection closed by {attacker} port {port} [preauth]"
        else:
            message = f"Disconnected from invalid user {user} {attacker} port {port} [preauth]"
        lines.append(_auth_line(current, message))

        if index % 40 == 0:
            lines.append(
                f"{current:%b %d %H:%M:%S} web nginx[2001]: {attacker} - - [{current:%d/%b/%Y:%H:%M:%S} +0000] \"GET {endpoint} HTTP/1.1\" 401 312"
            )

    return "\n".join(lines) + "\n"


def _auth_line(timestamp: datetime, message: str) -> str:
    return f"{timestamp:%b %d %H:%M:%S} server sshd[1234]: {message}"


def _line_count(content: str) -> int:
    return content.count("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate hackathon demo logs")
    parser.add_argument(
        "--profile",
        choices=["standard", "massive", "all"],
        default="all",
        help="Which log sets to generate",
    )
    parser.add_argument(
        "--massive-lines",
        type=int,
        default=250000,
        help="Approx baseline normal lines for each massive log",
    )
    parser.add_argument(
        "--attack-bursts",
        type=int,
        default=180,
        help="Number of credential-stuffing bursts for brute-force massive log",
    )
    parser.add_argument(
        "--travel-events",
        type=int,
        default=280,
        help="Number of impossible-travel user pairs in massive travel log",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict[str, int | str]] = {}

    if args.profile in {"standard", "all"}:
        brute_force = build_brute_force_log()
        impossible_travel = build_impossible_travel_log()

        brute_force_path = OUTPUT_DIR / "brute_force.log"
        impossible_travel_path = OUTPUT_DIR / "impossible_travel.log"
        brute_force_path.write_text(brute_force, encoding="utf-8")
        impossible_travel_path.write_text(impossible_travel, encoding="utf-8")

        manifest[brute_force_path.name] = {
            "lines": _line_count(brute_force),
            "size_bytes": brute_force_path.stat().st_size,
            "profile": "standard",
        }
        manifest[impossible_travel_path.name] = {
            "lines": _line_count(impossible_travel),
            "size_bytes": impossible_travel_path.stat().st_size,
            "profile": "standard",
        }
        print(f"Wrote {brute_force_path}")
        print(f"Wrote {impossible_travel_path}")

    if args.profile in {"massive", "all"}:
        massive_brute_force = build_brute_force_log_massive(args.massive_lines, args.attack_bursts)
        massive_travel = build_impossible_travel_log_massive(args.massive_lines, args.travel_events)
        attack_storm = build_attack_storm_log(max(100000, args.massive_lines // 2))

        brute_force_massive_path = OUTPUT_DIR / "brute_force_massive.log"
        impossible_travel_massive_path = OUTPUT_DIR / "impossible_travel_massive.log"
        attack_storm_path = OUTPUT_DIR / "attack_storm_massive.log"

        brute_force_massive_path.write_text(massive_brute_force, encoding="utf-8")
        impossible_travel_massive_path.write_text(massive_travel, encoding="utf-8")
        attack_storm_path.write_text(attack_storm, encoding="utf-8")

        manifest[brute_force_massive_path.name] = {
            "lines": _line_count(massive_brute_force),
            "size_bytes": brute_force_massive_path.stat().st_size,
            "profile": "massive",
        }
        manifest[impossible_travel_massive_path.name] = {
            "lines": _line_count(massive_travel),
            "size_bytes": impossible_travel_massive_path.stat().st_size,
            "profile": "massive",
        }
        manifest[attack_storm_path.name] = {
            "lines": _line_count(attack_storm),
            "size_bytes": attack_storm_path.stat().st_size,
            "profile": "massive",
        }

        print(f"Wrote {brute_force_massive_path}")
        print(f"Wrote {impossible_travel_massive_path}")
        print(f"Wrote {attack_storm_path}")

    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
