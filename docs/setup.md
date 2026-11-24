# Setup

## Before launching

1. Your firm needs its own Carbon Arc account and API key, from Carbon Arc's
   user portal. Each deployment uses its own key.
2. Buy the frameworks you want in Carbon Arc's own platform, and note each
   one's framework ID. This plugin never buys anything.

Launch the plugin and approve its one role, `data` (a data plugin).

## The key and the frameworks

In the dashboard's Settings form:

- **API key**, required and secret: your firm's Carbon Arc key. While it is
  missing the plugin asks Carbon Arc nothing, Connection says **No key**,
  and the plugin's status names the setting. It is never shown or logged.
- **Purchased frameworks**: one framework ID per row, up to 200. A row that
  is not a framework ID is named on the Frameworks page and skipped.
## Pace and what is kept

- **Requests a minute**: this plugin's share of Carbon Arc's limit of 100
  requests a minute and 1,000 an hour, 10 by default. Lower it where other
  tools at your firm use the same key: Carbon Arc counts them together.
- **Keep Carbon Arc's answers**: on by default, so you can test with them.
  Off, answers are read and not kept. Whether bought data may be kept, and
  for how long, is your firm's contract with Carbon Arc.
- **Raw responses window** and **past the window**: how long kept answers
  stay in the plugin's storage, a year by default, and whether they are then
  archived, kept or deleted.
- **Sample data**, on a deployment installed for development only: two
  fictitious frameworks, committed with the plugin, in place of Carbon Arc.
  Runs without a key.

## The companies

The **Frameworks** page shows each entity your frameworks measure, its
ticker, and the instrument it resolved to, or why none. Add a missing
instrument to your deployment, and the next hourly read resolves it.
