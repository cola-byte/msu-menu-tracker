import os
import smtplib
import sys
from datetime import date, timedelta
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
NOTIFY_TO = os.getenv("NOTIFY_TO")

BASE_URL = "https://eatatstate.msu.edu/menu/The%20Gallery%20at%20Snyder%20Phillips/all/{}"
DAYS_AHEAD = 7
TARGET_STATION = ""
TARGET_ITEM = "Chocolate Cake"
TARGET_MEALS = []  # e.g. ["Breakfast"], ["Lunch", "Dinner"], or [] for all


def find_item_at_station(soup):
    """Return dict of {station/period: [item_names]} where TARGET_ITEM matches."""
    matches = {}  # key: "Station / Period", value: list of matching item names

    for group in soup.find_all("div", class_="eas-view-group"):
        h3 = group.find("h3")
        if not h3:
            continue
        station_name = h3.get_text(strip=True)
        if TARGET_STATION and TARGET_STATION not in station_name.lower():
            continue

        for eas_list in group.find_all("div", class_="eas-list"):
            meal_time_div = eas_list.find("div", class_="meal-time")
            period = meal_time_div.get_text(strip=True) if meal_time_div else "Unknown"

            if TARGET_MEALS and period.lower() not in [m.lower() for m in TARGET_MEALS]:
                continue

            for title_div in eas_list.find_all("div", class_="meal-title"):
                item_name = title_div.get_text(strip=True)
                if TARGET_ITEM.lower() in item_name.lower():
                    key = f"{station_name} / {period}"
                    matches.setdefault(key, []).append(item_name)

    return matches


def check_dates():
    """Check the next DAYS_AHEAD days and return list of (date_str, [meal_periods])."""
    results = []
    today = date.today()

    for i in range(DAYS_AHEAD):
        check_date = today + timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")
        url = BASE_URL.format(date_str)

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to fetch {date_str}: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        matches = find_item_at_station(soup)

        if matches:
            friendly = check_date.strftime("%A, %B %#d")
            results.append((friendly, matches))
            for key, items in matches.items():
                print(f"  Found: {friendly} — {key}: {', '.join(items)}")
        else:
            print(f"  No target items found: {date_str}")

    return results


def send_email(results):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD or not NOTIFY_TO:
        print("Email credentials not configured in .env — skipping email.")
        return

    lines = [f"{TARGET_ITEM} is available on the following days:\n"]
    for friendly_date, matches in results:
        lines.append(f"• {friendly_date}")
        for key, items in matches.items():
            lines.append(f"    {key}: {', '.join(items)}")
    body = "\n".join(lines)

    msg = MIMEText(body)
    msg["Subject"] = f"MSU Menu Alert: {TARGET_ITEM}"
    msg["From"] = GMAIL_USER
    recipients = [r.strip() for r in NOTIFY_TO.split(",")]
    msg["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.sendmail(GMAIL_USER, recipients, msg.as_string())
        print(f"\nEmail sent to {NOTIFY_TO}")
    except Exception as e:
        print(f"\nFailed to send email: {e}")


def main():
    print(f"Checking next {DAYS_AHEAD} days for target items...\n")
    results = check_dates()

    if results:
        print(f"\nFound target items on {len(results)} day(s). Sending email...")
        send_email(results)
    else:
        print("\nNo target items found in the next 7 days.")


if __name__ == "__main__":
    main()
