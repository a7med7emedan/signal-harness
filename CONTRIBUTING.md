# Contributing

Bug reports and pull requests are welcome. A few things keep review quick.

## Before you open a merge request

```bash
make setup
make check
```

`make check` runs lint, the format check, the test suite with its coverage
floor and the reproducibility check. A merge request that fails any of them
will not be reviewed until it passes.

## Changes that alter the rendered page

The bundled example has a published checksum. If your change is meant to
alter the output, regenerate it and say why in the merge request:

```bash
signal-harness demo -o build/issue.sample.html
cd build && sha256sum issue.sample.html > ../src/signal_harness/examples/issue.sample.sha256
```

An unexplained checksum change is treated as a regression.

## Adding a source

Sources live in `src/signal_harness/sources/`. An adapter takes a `Fetcher`
and returns `Candidate` objects with a real publication date. Add recorded
responses under `tests/data/` and test against those; tests must not use the
network.

## Adding a gate

A gate is a function from the page text to a list of `Finding`. Register it
in `ALL_CHECKS` and add two tests: one showing the real example page passes,
one planting the exact fault the gate exists to catch.

## Style

Ruff handles formatting and linting, line length 100. Commit messages are in
the imperative mood and explain why, not only what.
