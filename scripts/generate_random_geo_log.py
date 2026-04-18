import random
from datetime import datetime, timedelta

# Generate a log file with random IPs (public, private, edge cases)
RANDOM_IPS = [
    "8.8.8.8", "1.1.1.1", "203.0.113.45", "198.51.100.73", # public
    "10.0.0.1", "172.16.5.4", "192.168.1.100", "127.0.0.1", # private
    "185.220.101.47", "45.95.147.11", "198.98.51.189", # known bad
    "0.0.0.0", "255.255.255.255", "100.64.0.1", # edge cases
]
USERS = ["testuser", "admin", "guest"]

start = datetime(2026, 4, 16, 12, 0, 0)
lines = []
for i in range(50):
    ts = start + timedelta(seconds=i * 60)
    ip = random.choice(RANDOM_IPS)
    user = random.choice(USERS)
    port = random.randint(30000, 65000)
    if i % 7 == 0:
        msg = f"Failed password for {user} from {ip} port {port} ssh2"
    elif i % 11 == 0:
        msg = f"Accepted password for {user} from {ip} port {port} ssh2"
    else:
        msg = f"Connection closed by {ip} port {port} [preauth]"
    lines.append(f"{ts:%b %d %H:%M:%S} server sshd[1234]: {msg}")

with open("data/demo_logs/random_geo_test.log", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("Generated random_geo_test.log for GeoIP demo.")
