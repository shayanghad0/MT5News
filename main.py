from biquote import Biquote

# Initialize the client
bq = Biquote()

# Fetch this week's high-impact macro events for specific countries
events = bq.calendar(importance="high", countries="US,EU,GB")

# Print the events
for event in events:
    print(event)