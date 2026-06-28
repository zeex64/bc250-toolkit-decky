#!/usr/bin/env python3
"""Construit le catalogue des ~2000 jeux les plus populaires (SteamSpy par owners)
+ marque les plus joués (Steam most-played chart). Sortie: games_catalog.json."""
import json, time, urllib.request, datetime, sys

import os
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "games_catalog.json")
UA = {"User-Agent": "BC250-Toolkit-Catalog/1.0"}
log = lambda m: print(f"[{datetime.datetime.now():%H:%M:%S}] {m}", flush=True)

def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

def owners_mid(s):
    # "100,000,000 .. 200,000,000" -> 150000000 (pour trier)
    try:
        a, b = s.replace(",", "").split("..")
        return (int(a) + int(b)) // 2
    except Exception:
        return 0

games = {}  # appid(str) -> {appid,name,owners_mid,ccu}

# --- SteamSpy: pages 0 et 1 (1000 chacune), 1 req/min ---
for page in (0, 1):
    if page > 0:
        log("pause 65s (rate-limit SteamSpy all)...")
        time.sleep(65)
    log(f"SteamSpy all page {page}...")
    try:
        data = fetch(f"https://steamspy.com/api.php?request=all&page={page}")
    except Exception as e:
        log(f"  ERREUR page {page}: {e}")
        continue
    n = 0
    for appid, info in data.items():
        name = (info.get("name") or "").strip()
        if not name:
            continue
        games[str(appid)] = {
            "appid": str(appid),
            "name": name,
            "owners_mid": owners_mid(info.get("owners", "")),
            "ccu": int(info.get("ccu") or 0),
        }
        n += 1
    log(f"  +{n} jeux (total {len(games)})")

# --- Steam most-played chart: flag 'most_played' (top ~100 par joueurs) ---
log("Steam most-played chart...")
most_played = set()
try:
    mp = fetch("https://api.steampowered.com/ISteamChartsService/GetMostPlayedGames/v1/")
    for rank in mp.get("response", {}).get("ranks", []):
        most_played.add(str(rank.get("appid")))
    log(f"  {len(most_played)} appids most-played")
except Exception as e:
    log(f"  ERREUR most-played: {e}")

# tri par owners desc puis ccu
ordered = sorted(games.values(), key=lambda g: (g["owners_mid"], g["ccu"]), reverse=True)
catalog = []
for g in ordered:
    catalog.append({
        "appid": g["appid"],
        "name": g["name"],
        **({"top": True} if g["appid"] in most_played else {}),
    })

out = {
    "_meta": {
        "description": "Catalogue des jeux Steam les plus populaires pour le sélecteur de submit (BC250-Toolkit). Trié par nombre de propriétaires (SteamSpy). 'top'=true si dans le chart Steam des plus joués.",
        "updated": datetime.date.today().isoformat(),
        "source": "SteamSpy request=all (pages 0-1) + Steam ISteamChartsService/GetMostPlayedGames",
        "count": len(catalog),
    },
    "games": catalog,
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=0)
log(f"ÉCRIT {OUT} — {len(catalog)} jeux, {len(most_played)} marqués most-played")
