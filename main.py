from jb_news.news import JBNews, NEWS_SOURCE_MQL5

# 1. Initialize the JBNews client
jb = JBNews()

# 2. Set your API key (replace with your actual key)
API_KEY = "YOUR_API_KEY_HERE"

# 3. Choose the news source (MQL5 Calendar in this case)
NEWS_SOURCE = NEWS_SOURCE_MQL5

# Optional: Set your GMT offset (e.g., 3 for GMT, 7 for EST)
jb.offset = 3

# 4. Connect to the API
if jb.get(API_KEY, news_source=NEWS_SOURCE):
    print("✅ Connected to JB-News API.\n")

    # 5. Load the calendar for today (today=True)
    if jb.calendar(API_KEY, today=True, news_source=NEWS_SOURCE):
        print(f"📅 News Calendar for Today ({len(jb.calendar_info)} events):\n")
        print("-" * 80)

        # 6. Iterate through all events and print details
        for event in jb.calendar_info:
            print(f"Event      : {event.name}")
            print(f"Currency   : {event.currency}")
            print(f"Event ID   : {event.event_id}")
            print(f"Impact     : {event.impact}")
            print(f"Date       : {event.date}")
            print(f"Actual     : {event.actual}")
            print(f"Forecast   : {event.forecast}")
            print(f"Previous   : {event.previous}")
            print(f"Category   : {event.category}")
            print("-" * 80)
    else:
        print("❌ Failed to load calendar. Check your API key or rate limit.")
else:
    print("❌ Failed to connect to JB-News API.")