from __future__ import annotations

from backend.config import NIGHT_HOUR_END, NIGHT_HOUR_START, WINDOW_SIZE_MINUTES
from backend.models.schemas import Anomaly


def render_rule_based_briefing(anomaly: Anomaly) -> str | None:
    template_id = anomaly.rule_triggered
    if template_id == "brute_force":
        return _brute_force_template(anomaly)
    if template_id == "credential_stuffing":
        return _credential_stuffing_template(anomaly)
    if template_id == "off_hours_login":
        return _off_hours_login_template(anomaly)
    if template_id == "impossible_travel":
        return _impossible_travel_template(anomaly)
    if template_id == "port_scan":
        return _port_scan_template(anomaly)
    if anomaly.iso_score > 0:
        return _iso_forest_generic_template(anomaly)
    return None


def feature_summary(anomaly: Anomaly) -> str:
    candidates: list[str] = []
    if anomaly.login_failure_count > 5:
        candidates.append(f"{anomaly.login_failure_count} failed logins")
    if anomaly.requests_per_minute > 30:
        candidates.append(f"{anomaly.requests_per_minute:.0f} requests per minute")
    if anomaly.unique_endpoints > 20:
        candidates.append(f"{anomaly.unique_endpoints} unique endpoints")
    if "off_hours_login" in anomaly.all_rules_fired:
        candidates.append("off-hours activity")
    if anomaly.is_known_bad_ip:
        candidates.append("known bad IP range")
    return ", ".join(candidates[:3]) if candidates else "high aggregate deviation score"


def _brute_force_template(anomaly: Anomaly) -> str:
    success_sentence = (
        f"A successful authentication was recorded in the same {WINDOW_SIZE_MINUTES}-minute window, "
        "which raises the risk of account compromise."
        if anomaly.login_success_count > 0
        else "No successful login was recorded in this window."
    )
    return (
        f"IP {anomaly.source_ip} made {anomaly.login_failure_count} failed login attempts over "
        f"{WINDOW_SIZE_MINUTES} minutes ({anomaly.requests_per_minute:.1f}/min), consistent with automated "
        f"password spraying or an SSH dictionary attack. {success_sentence} Recommended action: block IP "
        f"{anomaly.source_ip} at the firewall immediately and audit all recent successful logins for the affected account."
    )


def _credential_stuffing_template(anomaly: Anomaly) -> str:
    bad_ip_sentence = (
        " This IP is flagged as a known Tor exit node or cloud VPS range commonly used for automated attacks."
        if anomaly.is_known_bad_ip
        else ""
    )
    affected_user = anomaly.user or "the affected account"
    return (
        f"IP {anomaly.source_ip} recorded {anomaly.login_failure_count} failed authentication attempts followed by "
        f"{anomaly.login_success_count} successful login(s) in the same {WINDOW_SIZE_MINUTES}-minute window, a pattern "
        f"strongly consistent with automated credential stuffing using stolen credentials.{bad_ip_sentence} "
        f"Recommended action: immediately reset credentials for {affected_user}, force-terminate active sessions, "
        f"and block IP {anomaly.source_ip}."
    )


def _off_hours_login_template(anomaly: Anomaly) -> str:
    affected_user = anomaly.user or "an account"
    return (
        f"Account {affected_user} authenticated successfully from IP {anomaly.source_ip} ({anomaly.country_code}) at "
        f"{anomaly.window_start:%H:%M}, outside the normal business-hours baseline because {NIGHT_HOUR_START}:00-"
        f"{NIGHT_HOUR_END}:00 is treated as off-hours. This may indicate unauthorized access, a compromised account, "
        f"or a legitimate but undisclosed remote session. Recommended action: verify this login directly with the "
        f"account owner and review the session activity log."
    )


def _impossible_travel_template(anomaly: Anomaly) -> str:
    details = anomaly.metadata.get("impossible_travel", {})
    affected_user = anomaly.user or "the affected account"
    country_1 = details.get("country_1", "one country")
    country_2 = details.get("country_2", "another country")
    time_1 = details.get("time_1")
    time_2 = details.get("time_2")
    gap_minutes = details.get("gap_minutes")
    distance_km = details.get("distance_km")

    first_time = time_1.strftime("%H:%M") if hasattr(time_1, "strftime") else "an earlier time"
    second_time = time_2.strftime("%H:%M") if hasattr(time_2, "strftime") else "a later time"
    gap_text = f"{gap_minutes:.0f} minutes" if gap_minutes is not None else "a very short time"
    distance_text = f" The estimated travel distance is approximately {distance_km:.0f} km." if distance_km is not None else ""

    return (
        f"Account {affected_user} authenticated from {country_1} at {first_time} and then from {country_2} at {second_time}, "
        f"just {gap_text} apart, which is consistent with impossible travel.{distance_text} This is a strong indicator "
        f"of credential compromise, session hijacking, or VPN/proxy-assisted access. Recommended action: force-terminate "
        f"all active sessions for {affected_user}, reset the password immediately, and notify the account owner."
    )


def _port_scan_template(anomaly: Anomaly) -> str:
    return (
        f"IP {anomaly.source_ip} ({anomaly.country_code}) probed {anomaly.unique_endpoints} distinct URL endpoints at "
        f"{anomaly.requests_per_minute:.0f} requests per minute during a {WINDOW_SIZE_MINUTES}-minute window, which is "
        f"consistent with automated vulnerability scanning or directory enumeration. No confirmed exploitation was detected "
        f"in this window, but this activity often precedes a targeted attack. Recommended action: add IP {anomaly.source_ip} "
        f"to the firewall blocklist and monitor subsequent requests from the same IP range."
    )


def _iso_forest_generic_template(anomaly: Anomaly) -> str:
    return (
        f"IP {anomaly.source_ip} ({anomaly.country_code}) produced a statistical anomaly score of "
        f"{anomaly.composite_score:.0f}/100 based on unusual feature combinations such as {feature_summary(anomaly)}. "
        f"While no specific attack-pattern rule was triggered, the behavior deviates significantly from the baseline in "
        f"this log. Recommended action: manually review this IP's full activity for the window starting at "
        f"{anomaly.window_start:%Y-%m-%d %H:%M UTC}."
    )
