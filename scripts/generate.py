#!/usr/bin/env python3
"""
Fetches fresh match data from tusligascanarias.mygol.es API
and generates lightweight JSON files consumed by the static frontend.
"""

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://tusligascanarias.mygol.es/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
HURACAN_MINI_ID = 1159
HURACAN_PRE_ID = 1112


def fetch(url, retries=3, backoff=2.0):
    """GET JSON with retries on transient failures."""
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    raise last_err


def fmt_date(value):
    if not value or value.startswith("0001") or value.startswith("1901"):
        return ""
    return value[:16]


def tournament_group_map(tournament_data):
    groups = {}
    for g in tournament_data.get("groups", []):
        name = (g.get("name") or "").strip().upper()
        letter = name[-1] if name else "A"
        if letter not in ("A", "B", "C", "D"):
            letter = "A"
        groups[g["id"]] = letter
    return groups


def build_mini_team_map(tournament_data):
    return {team["id"]: team["name"] for team in tournament_data.get("teams", [])}


def build_pre_team_map(tournament_data):
    group_letter = tournament_group_map(tournament_data)
    team_group = {}
    for tg in tournament_data.get("teamGroups", []):
        team_group[tg["idTeam"]] = group_letter.get(tg["idGroup"], "A")
    return {team["id"]: {"name": team["name"], "group": team_group.get(team["id"], "A")} for team in tournament_data.get("teams", [])}


def transform_matches(jornadas_data):
    result = []
    for jornada in jornadas_data:
        matches = []
        for m in jornada.get("matches", []):
            field = m.get("field") or {}
            matches.append({
                "home": m.get("idHomeTeam") or -1,
                "away": m.get("idVisitorTeam") or -1,
                "date": fmt_date(m.get("startTime", "")),
                "status": m.get("status", 5),
                "field": field.get("name") or "",
                "home_score": m.get("homeScore"),
                "away_score": m.get("visitorScore"),
            })
        result.append({"name": jornada.get("name", ""), "group_id": jornada.get("idGroup", 0), "matches": matches})
    return result


BYE_NAME = "Descansa"


def _resolve_team(team_id, team_map, is_pre):
    if team_id == -1:
        return {"name": BYE_NAME, "group": "-"}
    if is_pre:
        return team_map.get(team_id, {"name": f"#{team_id}", "group": "-"})
    return {"name": team_map.get(team_id, f"#{team_id}"), "group": "-"}


def extract_team_matches(jornadas_data, team_id, team_map, is_pre=False):
    out = []
    for jornada in jornadas_data:
        for m in jornada.get("matches", []):
            home = m.get("idHomeTeam") or -1
            away = m.get("idVisitorTeam") or -1
            if team_id not in (home, away):
                continue
            home_team = _resolve_team(home, team_map, is_pre)
            away_team = _resolve_team(away, team_map, is_pre)
            field = m.get("field") or {}
            out.append({
                "jornada": jornada.get("name", ""),
                "home": home,
                "away": away,
                "home_name": home_team["name"],
                "away_name": away_team["name"],
                "date": fmt_date(m.get("startTime", "")),
                "status": m.get("status", 5),
                "field": field.get("name") or "",
                "home_score": m.get("homeScore"),
                "away_score": m.get("visitorScore"),
                "group": home_team.get("group") if team_id == home else away_team.get("group"),
            })
    return out


def save_json(name, payload):
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def infer_season(jornadas):
    """Find earliest startTime year in jornadas; return 'YYYY / YYYY+1'."""
    for j in jornadas:
        for m in j.get("matches", []):
            d = m.get("startTime") or ""
            if d[:4].isdigit():
                y = int(d[:4])
                if 2000 <= y <= 2100:
                    return f"{y} / {y + 1}"
    return "2025 / 2026"


def count_pre_groups(pre_team_map):
    counts = {"A": 0, "B": 0}
    for t in pre_team_map.values():
        g = t.get("group", "A")
        counts[g] = counts.get(g, 0) + 1
    return counts


def main():
    print("Fetching match and team data from mygol.es API...")
    mini_raw = fetch(f"{BASE}/matches/fortournament/85")
    pre_raw = fetch(f"{BASE}/matches/fortournament/87")
    mini_t = fetch(f"{BASE}/tournaments/85")
    pre_t = fetch(f"{BASE}/tournaments/87")

    mini_team_map = build_mini_team_map(mini_t)
    pre_team_map = build_pre_team_map(pre_t)
    updated_at = datetime.now(timezone.utc).isoformat()

    mini_payload = {"updated_at": updated_at, "tournament": {"id": 85, "name": "Miniprebenjamín Escuela"}, "teams": mini_team_map, "jornadas": transform_matches(mini_raw)}
    pre_payload = {"updated_at": updated_at, "tournament": {"id": 87, "name": "Prebenjamín Escuela"}, "teams": pre_team_map, "jornadas": transform_matches(pre_raw)}
    huracan_payload = {"updated_at": updated_at, "mini": extract_team_matches(mini_raw, HURACAN_MINI_ID, mini_team_map, False), "pre": extract_team_matches(pre_raw, HURACAN_PRE_ID, pre_team_map, True)}
    season = infer_season(mini_raw)
    pre_groups = count_pre_groups(pre_team_map)
    meta_payload = {
        "updated_at": updated_at,
        "season": season,
        "leagues": {
            "mini": {
                "label": "Miniprebenjamín",
                "teams": len(mini_team_map),
                "jornadas": len(mini_payload['jornadas']),
            },
            "pre": {
                "label": "Prebenjamín",
                "teams": len(pre_team_map),
                "jornadas": len(pre_payload['jornadas']),
                "groups": pre_groups,
            },
        },
    }

    save_json("mini.json", mini_payload)
    save_json("pre.json", pre_payload)
    save_json("huracan.json", huracan_payload)
    save_json("meta.json", meta_payload)
    print(f"Done! MINI jornadas: {len(mini_payload['jornadas'])} | PRE jornadas: {len(pre_payload['jornadas'])} | Huracán mini partidos: {len(huracan_payload['mini'])}")


if __name__ == "__main__":
    main()
