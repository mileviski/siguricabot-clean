import requests
import time
import json
import telebot
from datetime import datetime, timedelta, timezone

API_BASE = "https://v3.football.api-sports.io"

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def send_message(bot, user_id, text):
    try:
        bot.send_message(user_id, text)
    except Exception as e:
        print("❌ Greška pri slanju poruke:", e)

def api_get(path, params, api_key, timeout=20):
    headers = {"x-apisports-key": api_key}
    url = f"{API_BASE}{path}"
    r = requests.get(url, headers=headers, params=params, timeout=timeout)
    if r.status_code != 200:
        print(f"❌ API {r.status_code}: {url} {params}")
        return []
    try:
        return r.json().get("response", [])
    except Exception:
        return []

def get_today_fixtures_for_leagues(league_ids, api_key):
    today = datetime.now(timezone.utc).date().isoformat()
    fixtures = api_get("/fixtures", {"date": today}, api_key)
    return [m for m in fixtures if m.get("league", {}).get("id") in league_ids]

def best_match_winner(bookmakers, home_name, away_name):
    home_odd, home_bm = None, None
    away_odd, away_bm = None, None
    for bm in bookmakers or []:
        bm_name = bm.get("name")
        for bet in bm.get("bets", []):
            if bet.get("name") == "Match Winner":
                for v in bet.get("values", []):
                    label = (v.get("value") or "").strip().lower()
                    try:
                        odd = float(v.get("odd"))
                    except:
                        continue
                    if label in ("home", "1") or v.get("value") == home_name:
                        if home_odd is None or odd < home_odd:
                            home_odd, home_bm = odd, bm_name
                    elif label in ("away", "2") or v.get("value") == away_name:
                        if away_odd is None or odd < away_odd:
                            away_odd, away_bm = odd, bm_name
    return home_odd, home_bm, away_odd, away_bm

def get_prematch_bookmakers(fixture_id, api_key):
    resp = api_get("/odds", {"fixture": fixture_id}, api_key)
    out = []
    for item in resp:
        out.extend(item.get("bookmakers", []))
    return out

def get_live_bookmakers(fixture_id, api_key):
    resp = api_get("/odds/live", {"fixture": fixture_id}, api_key)
    out = []
    for item in resp:
        out.extend(item.get("bookmakers", []))
    return out

def build_favorites_map(fixtures, api_key, max_odds):
    favorites = {}
    for fx in fixtures:
        fixture_id = fx["fixture"]["id"]
        home = fx["teams"]["home"]
        away = fx["teams"]["away"]
        league_name = fx["league"]["name"]

        bms = get_live_bookmakers(fixture_id, api_key)
        source = "LIVE"
        if not bms:
            bms = get_prematch_bookmakers(fixture_id, api_key)
            source = "PRE"

        if not bms:
            continue

        h_odd, h_bm, a_odd, a_bm = best_match_winner(bms, home["name"], away["name"])
        if h_odd is None and a_odd is None:
            continue

        fav = None
        fav_odd, fav_bm = None, None
        if h_odd is not None and (a_odd is None or h_odd <= a_odd):
            fav = {"id": home["id"], "name": home["name"]}
            fav_odd, fav_bm = h_odd, (h_bm or source)
        elif a_odd is not None:
            fav = {"id": away["id"], "name": away["name"]}
            fav_odd, fav_bm = a_odd, (a_bm or source)

        if fav and fav_odd is not None and fav_odd <= max_odds:
            favorites[fixture_id] = {
                "fav_team_id": fav["id"],
                "fav_team_name": fav["name"],
                "odd": fav_odd,
                "bookmaker": fav_bm,
                "league": league_name,
            }
    return favorites

def get_live_matches(api_key):
    return api_get("/fixtures", {"live": "all"}, api_key)

def main():
    config = load_config()
    bot = telebot.TeleBot(config["telegram_bot_token"])
    user_id = config["user_id"]
    allowed_leagues = set(config["allowed_leagues"])
    max_odds = float(config.get("max_odds", 1.50))

    # ✅ Startup poruka i log
    print("🚀 Bot se pokrenuo. Filtriram lige:", len(allowed_leagues), "| limit kvote ≤", max_odds)
    send_message(bot, user_id, "✅ Bot je pokrenut i prati utakmice u odabranim ligama.")

    sent_for_fixture = set()
    favorites = {}
    last_build = None

    while True:
        try:
            now = datetime.now(timezone.utc)
            if last_build is None or (now - last_build) >= timedelta(minutes=20):
                fixtures = get_today_fixtures_for_leagues(allowed_leagues, config["api_football_key"])
                favorites = build_favorites_map(fixtures, config["api_football_key"], max_odds)
                last_build = now
                print(f"🗂️ Favoriti spremni: {len(favorites)} utakmica (≤ {max_odds})")

            print("⏳ Provjeravam live utakmice…")
            lives = get_live_matches(config["api_football_key"]) or []

            for m in lives:
                league = m.get("league", {})
                league_id = league.get("id")
                if league_id not in allowed_leagues:
                    continue

                fx = m.get("fixture", {})
                fixture_id = fx.get("id")
                if fixture_id not in favorites:
                    continue

                goals = m.get("goals", {})
                gh = goals.get("home") or 0
                ga = goals.get("away") or 0

                home = m["teams"]["home"]
                away = m["teams"]["away"]

                fav = favorites[fixture_id]
                fav_id = fav["fav_team_id"]
                favorite_is_home = (home["id"] == fav_id)
                is_losing = (gh < ga) if favorite_is_home else (ga < gh)

                # debug log svake provjere
                print(f"▶ {league.get('name')} | {home['name']} {gh}-{ga} {away['name']} | fav={fav['fav_team_name']}@{fav['odd']} | gubi={is_losing}")

                if is_losing and fixture_id not in sent_for_fixture:
                    minute = fx.get("status", {}).get("elapsed")
                    msg = (
                        "🚨 FAVORIT GUBI!\n\n"
                        f"🏆 {league.get('name')}\n"
                        f"🧮 Kvota favorita: {fav['odd']} ({fav['bookmaker']})\n"
                        f"⚽ {home['name']} {gh} - {ga} {away['name']}\n"
                    )
                    if isinstance(minute, int):
                        msg += f"⏱️ {minute}. minuta\n"
                    send_message(bot, user_id, msg)
                    sent_for_fixture.add(fixture_id)

        except Exception as e:
            print("❌ Greška u petlji:", e)

        time.sleep(60)

if __name__ == "__main__":
    main()






             