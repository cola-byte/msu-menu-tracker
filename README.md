# MSU Menu Scraper

Scrapes [The Gallery at Snyder Phillips](https://eatatstate.msu.edu/menu/The%20Gallery%20at%20Snyder%20Phillips/all) and sends a Gmail notification when a target menu item is found.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Copy `.env` and fill in your credentials:
   ```
   GMAIL_USER=you@gmail.com
   GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
   NOTIFY_TO=you@gmail.com
   ```
   > `GMAIL_APP_PASSWORD` is a Gmail App Password, not your regular password.  
   > Generate one at: Google Account → Security → 2-Step Verification → App Passwords

3. Run:
   ```
   python scraper.py
   ```

## Configuration

All options are at the top of `scraper.py`:

| Variable | Default | Description |
|---|---|---|
| `TARGET_ITEM` | `"Cherry Pie"` | Item name to search for. Partial match, case-insensitive. |
| `TARGET_STATION` | `""` | Station to search in (e.g. `"Latitudes"`, `"Bliss"`). Empty string searches all stations. |
| `TARGET_MEALS` | `[]` | Meal periods to include. Empty list includes all. |
| `DAYS_AHEAD` | `7` | How many days ahead to check, starting from today. |

### Examples

Search for Ham Slice at Latitudes, dinner only:
```python
TARGET_ITEM    = "Ham Slice"
TARGET_STATION = "Latitudes"
TARGET_MEALS   = ["Dinner"]
DAYS_AHEAD     = 14
```

Search for any pizza across all stations, all meal periods:
```python
TARGET_ITEM    = "Pizza"
TARGET_STATION = ""
TARGET_MEALS   = []
```

Search only breakfast and lunch:
```python
TARGET_MEALS = ["Breakfast", "Lunch"]
```

### Notify multiple recipients

In `.env`, separate addresses with commas:
```
NOTIFY_TO=you@gmail.com,friend@gmail.com
```

## Automation

To run this daily automatically, add a Windows Task Scheduler task that runs:
```
python C:\path\to\msu_menu\scraper.py
```
