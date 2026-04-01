import os
import smtplib
import sys
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
NOTIFY_TO = os.getenv("NOTIFY_TO")

BASE_URL_TEMPLATE = "https://eatatstate.msu.edu/menu/{}/all/{}"
LOCATIONS = [
    "The Gallery at Snyder Phillips",
    "Brody Square",
    "South Pointe at Case",
    "Heritage Commons at Landon",
    "The Vista at Shaw",
    "Thrive at Owen",
    "The Edge at Akers",
    "The Workshop",
    "The Sandbox",
    "The State Room at Kellogg",
    "Sparty's Market",
    "Sparty's Market at Holden",
    "Sparty's Market at Holmes",
]
DAYS_AHEAD = 7  # e.g. 7 (check one week ahead), 14 (two weeks)
TARGET_STATION = ""  # e.g. "Grill", "Desserts", or "" for all stations
TARGET_ITEMS = ["Cheese Cake"]  # e.g. ["Chocolate Cake"], ["BBQ", "Pizza"] (case-insensitive partial match)
TARGET_MEALS = ["lunch"]  # e.g. ["Lunch"], ["Lunch", "Dinner"], or [] for all meals


def find_items_at_station(soup):
    """Return dict of {station/period: [item_names]} where any TARGET_ITEMS match."""
    # matches: { "Station / Period": [item_names] }
    matches = {}

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
                if any(t.lower() in item_name.lower() for t in TARGET_ITEMS):
                    key = f"{station_name} / {period}"
                    matches.setdefault(key, []).append(item_name)

    return matches


def merge_periods(day_matches):
    """
    Merge Lunch+Dinner entries for the same location+station+items into one line.

    Input:  { "Location > Station / Lunch": [items], "Location > Station / Dinner": [items] }
    Output: { "Location > Station": { "periods": "Lunch & Dinner", "items": [items] } }
    """
    # Group by (location, station, frozenset of items)
    groups = {}
    for full_key, items in day_matches.items():
        # full_key format: "Location > Station / Period"
        loc_station, period = full_key.rsplit(" / ", 1)
        group_key = (loc_station, tuple(sorted(set(items))))
        groups.setdefault(group_key, []).append(period)

    merged = {}
    for (loc_station, items_tuple), periods in groups.items():
        periods_sorted = sorted(periods, key=lambda p: ["Breakfast", "Lunch", "Dinner"].index(p) if p in ["Breakfast", "Lunch", "Dinner"] else 99)
        if len(periods_sorted) > 1:
            periods_str = " & ".join(periods_sorted)
        else:
            periods_str = periods_sorted[0]
        merged[loc_station] = {"periods": periods_str, "items": list(items_tuple)}

    return merged


def check_dates():
    """Check the next DAYS_AHEAD days across all LOCATIONS."""
    results = []
    today = date.today()

    for i in range(DAYS_AHEAD):
        check_date = today + timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")
        friendly = f"{check_date.strftime('%a')} {check_date.month}/{check_date.day}"
        day_matches = {}

        for location in LOCATIONS:
            url = BASE_URL_TEMPLATE.format(quote(location, safe=""), date_str)

            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"Failed to fetch {location} on {date_str}: {e}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            matches = find_items_at_station(soup)

            for key, items in matches.items():
                full_key = f"{location} > {key}"
                day_matches[full_key] = items
                print(f"  Found: {friendly} — {full_key}: {', '.join(items)}")

        if day_matches:
            results.append((friendly, merge_periods(day_matches)))
        else:
            print(f"  No target items found: {date_str}")

    return results


def build_email_body(results):
    items_label = " / ".join(TARGET_ITEMS)

    plain_lines = [f"{items_label} is available on the following days:\n"]
    html_lines = [
        "<html><body>",
        f"<p><b>{items_label}</b> is available on the following days:</p>",
        "<ul style='list-style:none; padding:0;'>",
    ]

    for friendly_date, merged in results:
        plain_lines.append(f"• {friendly_date}")
        html_lines.append(f"  <li style='margin-top:10px;'><b>{friendly_date}</b><ul style='list-style:none; padding-left:16px;'>")

        for loc_station, info in merged.items():
            periods = info["periods"]
            items_str = ", ".join(info["items"])
            plain_lines.append(f"    {loc_station} ({periods}): {items_str}")
            html_lines.append(f"    <li>{loc_station} <span style='color:#666;'>({periods})</span>: {items_str}</li>")

        html_lines.append("  </ul></li>")

    html_lines += ["</ul>", "</body></html>"]

    return "\n".join(plain_lines), "\n".join(html_lines)


def send_email(results):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD or not NOTIFY_TO:
        print("Email credentials not configured in .env — skipping email.")
        return

    plain_body, html_body = build_email_body(results)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"MSU Menu Alert: {' / '.join(TARGET_ITEMS)}"
    msg["From"] = GMAIL_USER
    recipients = [r.strip() for r in NOTIFY_TO.split(",")]
    msg["To"] = ", ".join(recipients)

    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

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
