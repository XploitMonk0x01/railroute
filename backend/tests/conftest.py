import os

# Disable Playwright scraper during backend tests to prevent 
# database pool errors and unnecessary browser launches.
os.environ["TESTING"] = "1"
