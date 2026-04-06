## How to increase its speed

- It skips the startup balance refresh and let /health refresh in the background instead.
  That gives you a fast boot; balance updates after the bot is already running.
- Should use a system chromedriver (set CHROMEDRIVER_PATH) so webdriver_manager doesn’t run at startup.
- Possibly disable balance refresh on /health if you want the bot to stay responsive even on slow networks.
