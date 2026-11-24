# Troubleshooting

## Waiting for carbon_arc_api_key

The key is not set. Enter your firm's Carbon Arc key in Settings. Nothing is
asked of Carbon Arc until it is.

## Carbon Arc refused the key

Carbon Arc answered 401 or 403. Check that the key is current (Carbon Arc's
keys expire after a year) and belongs to the account that bought the
frameworks.

## Not held

Carbon Arc has no framework with that ID for your key. Check the ID, and
that your firm bought it with this account. The plugin never buys it.

## A framework row is not an ID

A row of Purchased frameworks is not a framework ID. Correct or remove it in
Settings.

## Companies not resolved

A company's ticker matches none of your deployment's instruments, or more
than one (Carbon Arc's ticker names no exchange). Add or correct the
instrument; the next hourly read resolves it.

## Too many requests; paused

Carbon Arc answered 429. The plugin waits as long as Carbon Arc asks, then
carries on. Lower **Requests a minute** if other tools share the key.
