# SportyClaw Autoplacer
SportyClaw Autoplacer is a Telegram-driven SportyBet automation suite that pulls booking codes from your chats, runs Selenium to place bets, and keeps your bankroll sacred by only touching one quarter of the starting balance every day.

# Pipeline
![SportyBet Bot Pipeline](sportybet_bot_pipeline.svg)

## Core features

- **Telegram listener** (`main.py`, `bot/listener.py`): polls Telegram for text updates, ignores unauthorized senders, extracts SportyBet booking codes via `bot/parser.py`, and invokes `sportybet.client.place_bet_with_code` while checking the bankroll quota. Successful bets include a quick bankroll countdown in the reply; if the day’s ready quarters are gone, it replies with an exhaustion warning.
- **Bankroll splitting** (`bankroll.py`, `tests/test_bankroll.py`): every morning the bot scrapes the current SportyBet balance, parses it into a float, and splits that figure into four equal quarters. Only those quarters can be spent during that calendar day; any profits remain untouched until the next reset.
- **Health + reporting** (`health.py`, `bot/commands.py`, `reporter.py`): a HTTP `/health` endpoint plus a `/health` Telegram command that both output the latest stats, including remaining quarters and profit/loss. Daily reports scrape SportyBet, marry the scraped ledger with the in-memory stats, and DM the owner chat as Markdown.
- **Mocking & pytest coverage** (`bot/mock_handler.py`, `tests/*`): the parser, listener, bankroll, and health handlers are all exercised via pytest, and the mock update/message helpers let you run listener tests without Telegram or Selenium.

## Running the bot

1. Populate `.env` with at least `BOT_TOKEN`, `OWNER_CHAT_ID`, `ALLOWED_USER_ID`, and the SportyBet credentials (`SPORTYBET_PHONE`, `SPORTYBET_PASSWORD`).
2. Install dependencies (ideally inside a virtualenv) with `python -m pip install -r requirements.txt`.
3. Run `python main.py`; the health server and Telegram polling start automatically.
4. Send booking codes through Telegram (or via the Telegram Bot API/ Postman) and keep an eye on `/health` to monitor the bankroll/quota breakdown.

## Bankroll mechanics recap

- The bot initializes the bankroll by scraping SportyBet, parsing the balance string into a float (`bankroll.parse_balance`), and running `bankroll.initialize_from_amount`. That balance gets split into four quarters with equal value.
- Before each bet, `listener.handle_message` verifies `bankroll.has_available_chunks()` is true, reserves one chunk (`bankroll.reserve_chunk()`), and on success reports how many quarters remain. Failed bets release the chunk back into availability so it can be retried.
- At midnight the scheduled job `run_daily_reset` resets both the stats and the bankroll (`bankroll.reset()`), then refreshes the balance again for the new day. Profits earned during the day never increase the spending pool until the next reset.

## Testing & health checks

- Run `python -m pytest tests` for parser, listener, health, and bankroll coverage.
- The `/health` HTTP endpoint and Telegram command share the same payload, showing both the ongoing stats and the remaining bankroll quarters.

## Notes

- Selenium/Telegram packages may not be installed on every machine; use a virtualenv if the system rejects `pip install` in this repo.
- The parser ignores common words (`BOOKING`, `CODE`, etc.) and runs case-insensitive matching to avoid false positives. Adjust the regexes in `bot/parser.py` if your booking-code format differs.

Want CLI helpers or a dashboard? Just ask—this README is as flexible as the bot’s bankroll.


 
