# Carbon Arc plugin

An [Open Meridian](https://github.com/open-meridian) data plugin that
connects a deployment to [Carbon Arc](https://docs.carbonarc.ai) with the
firm's own API key.

- **Reads purchased frameworks:** each framework the firm has already
  bought and names in Settings, with its insight, entities and
  entity-mapping version.
- **Resolves companies:** each company a framework measures, as its ticker,
  to the deployment's instrument; what does not resolve is counted, never
  guessed.
- **Never buys:** it reads only, with GET requests to a short list of
  addresses; it never prices, quotes or buys a framework.
- **Polite to Carbon Arc:** it keeps to the rate you set, never above
  Carbon Arc's 100 requests a minute and 1,000 an hour, and pauses on 429.

This version records nothing in the lake: a panel's values over time wait
on a kind of record the platform does not have yet. Its pages show its
connection, its datasets and the frameworks it reads, never the data.

## Use it

    meridian plugin upload
    meridian plugin launch carbon-arc 0.1.0 --instance carbon-arc

Then, in the dashboard: set **API key** (your firm's own) and **Purchased
frameworks**. [docs/setup.md](docs/setup.md) walks through each step.

## Develop it

    pip install -e '.[dev]'
    python -m pytest
    meridian plugin check --verified --run-tests

The tests run offline against fictitious responses committed under
`src/carbon_arc/responses/`; nothing in the tests or CI calls Carbon Arc.
With the **Sample data** setting on, a development deployment runs on the
same responses. `make ci-local` runs lint, the tests, the plugin check and
the image in containers.

| Module | What it does |
|---|---|
| `carbon.py` | Carbon Arc's reads, GET only, and the committed stand-in |
| `limits.py` | the request pace and the pause after a 429 |
| `frameworks.py` | the purchased frameworks, their companies resolved |
| `raw.py` | Carbon Arc's answers as received, and their window |
| `settings.py`, `declared.py` | the settings and what the version declares |
| `page.py`, `records.py`, `templates/` | the pages, and their tools |

`AGENTS.md` is for coding agents working on the plugin.

## Licence

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Not affiliated with
or endorsed by Carbon Arc.
