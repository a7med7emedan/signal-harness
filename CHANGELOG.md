# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[semantic versioning](https://semver.org/).

## [1.0.0] - 2026-10-07

### Added

- Issue schema with strict validation: one lead, ascending ids, desk windows,
  a five part mechanism for every full story, unknown fields refused.
- Per desk freshness windows with inclusive boundaries.
- Append only ledger in JSON Lines that refuses to print a URL twice.
- bioRxiv and medRxiv adapters over the public details API, with pagination
  and first version filtering.
- Deterministic, locale independent HTML renderer producing one offline file.
- Ten publication gates run against the rendered page.
- Command line tool: `demo`, `render`, `gate`, `ledger`, `hunt`.
- Multi stage container image that runs the full test suite during the build.
- Bundled example issue with a published SHA-256 for cross machine checks.
