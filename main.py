import requests
import time
import json
import telebot

def load_config():
    with open("config.json") as f:
        return json.load(f)

def send_message(bot, user_id, text):
    try:
        bot.send_message(user_id, text)
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

def main():
    config = load_config()
    bot = telebot.TeleBot(config["telegram_bot_token"])
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

                if home["winner"] is False or away["winner"] is False:
                    message = (
                        f"📉 Favorit gubi!\n"
                        f"{home['name']} {match['goals']['home']} - {match['goals']['away']} {away['name']}"
                    )
                    send_message(bot, user_id, message)
                    sent_ids.add(fixture_id)

        except Exception as e:
            print("❌ Greška:", e)

        time.sleep(60)

if __name__ == "__main__":
    main()


             