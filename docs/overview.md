# Overview

This plugin connects your deployment to Carbon Arc with your firm's own API
key, reads the frameworks your firm has already bought there, and finds the
listed companies they measure among your deployment's instruments.

## What it does in this version

- **Reads your purchased frameworks.** You name each framework your firm
  has bought; the plugin reads what it measures (its insight and
  aggregation), the entities it covers, and the version of Carbon Arc's
  entity mapping it was read under.
- **Resolves companies.** Each company a framework measures is read as its
  ticker and matched to your deployment's instrument. A ticker that matches
  none, or more than one, is counted and shown, never guessed.
- **Keeps Carbon Arc's answers**, as received, in the plugin's storage, with
  Carbon Arc's own entity ID and the mapping version beside each, unless you
  turn keeping off.

## What it does not do yet

- **It records no panel's values in the lake.** A panel is a value over
  time for a company, and the platform has no kind of record for such a
  value yet. The panels' dataset comes with it, in a later version.
- **Brands, locations, people and digital properties** are counted but not
  resolved: the platform has no such kind of subject yet.
- **Carbon Arc's own derived insights and scores** are not carried.

## What it never does

- It never prices, quotes or buys a framework. Buying spends your firm's
  credits, and is your firm's decision, made in Carbon Arc's own platform.
- It never shows a panel's values on its own pages.
- It generates no trading signal, rating or score.
