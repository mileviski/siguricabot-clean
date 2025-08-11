import requests
import time
import json
import telebot

# Lista ID-ova liga iz API-Football
LIGE = [
    39,   # Premier League
    140,  # La Liga
    135,  # Serie A
    78,   # Bundesliga
    61,   # Ligue 1
    2,    # Champions League
    3,    # Europa League
    848,  # Conference League
    94,   # Primeira Liga (Portugal)
    88,   # Eredivisie (Nizozemska)
    203,  # Süper Lig (Turska)
    143,  # Segunda Division (Španjolska)
    141,  # Copa del Rey
    42,   # FA Cup
    45,   # Championship
    144,  # EFL Cup
    795,  # Hrvatska HNL
    307,  # Belgijska Jupiler Pro League
    332,  # Švicarska Super League
    233   # Grčka Super League 1
]

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
                # Filtriramo samo željene lige
                if match["league"]["id"] not in LIGE:
                    continue

                fixture_id = match["fixture"]["id"]
                home = match["teams"]["home"]
                away = match["teams"]["away"]

                if fixture_id in sent_ids:
                    continue

                # Provjera ako favorit gubi (po trenutnom rezultatu)
                if home["winner"] is False or away["winner"] is False:
                    message = (
                        f"📉 Favorit gubi!\n"
                        f"{home['name']} {match['goals']['home']} - {match['goals']['away']} {away['name']}\n"
                        f"Liga: {match['league']['name']}"
                    )

                    send_message(bot, user_id, message)
                    sent_ids.add(fixture_id)

        except Exception as e:
            print("❌ Greška:", e)

        time.sleep(60)

if __name__ == "__main__":
    main()



             