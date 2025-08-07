import requests
import time
import json
from telegram import Bot

def load_config():
    with open("config.json") as f:
        return json.load(f)

def send_message(bot, user_id, text):
    try:
        bot.send_message(chat_id=user_id, text=text)
    except Exception as e:
        print("Greška pri slanju poruke:", e)

def get_live_matches(api_key):
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {
        "x-apisports-key": api_key
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("response", [])
    return []

def is_favorite(live_match, min_odds, max_odds):
    try:
        bookmakers = live_match['bookmakers']
        for bookmaker in bookmakers:
            for bet in bookmaker['bets']:
                if bet['name'] == "Match Winner":
                    for outcome in bet['values']:
                        if float(outcome['odd']) <= max_odds:
                            if live_match['teams'][outcome['value']]['winner'] == False:
                                return True
    except:
        pass
    return False

def main():
    config = load_config()
    bot = Bot(token=config["telegram_bot_token"])
    user_id = config["user_id"]

    sent_ids = set()

    while True:
        print("⏳ Provjeravam utakmice...")
        try:
            matches = get_live_matches(config["api_football_key"])
            for match in matches:
                fixture_id = match["fixture"]["id"]
                home = match["teams"]["home"]
                away = match["teams"]["away"]

                if fixture_id in sent_ids:
                    continue

                # Ovo bi u pravilu koristilo kvote, ali ih često nema live besplatno
                # Pa ovdje simuliramo ako favorit gubi
                if home["winner"] is False or away["winner"] is False:
                    losing_team = home if home["winner"] is False else away
                    message = f"📉 Favorit gubi!\n\n⚽ {home_team} {home_score} - {away_score} {away_team}\n📅 {match_time}"


{home['name']} {match['goals']['home']} - {match['goals']['away']} {away['name']}"
                    send_message(bot, user_id, message)
                    sent_ids.add(fixture_id)

        except Exception as e:
            print("❌ Greška:", e)

        time.sleep(60)

if __name__ == "__main__":
    main()
