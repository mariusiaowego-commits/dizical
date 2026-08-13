# Contributing

Thanks for your interest! This is a dad-built family app, but it's real software with real users — and it's open for contributions.

## What's welcome

- **Bug fixes** — anything in `src/` or `tests/` with a failing test
- **Test improvements** — the suite is 527 tests and growing
- **Documentation** — README, workflow docs, design-system docs
- **New badge themes** — see `docs/badge-image-workflow.md` for the draft-JSON contract
- **Localization** — the UI is Chinese-first; English strings live in templates

## What's probably not

- Large framework migrations (React/Vue rewrites) — vanilla JS + GSAP is a deliberate choice
- Personal data or family-specific config — keep `data/` and `.env` out of every commit
- New runtime dependencies without discussion — this project stays dependency-light

## Getting started

```bash
git clone https://github.com/mariusiaowego-commits/dizical.git && cd dizical
pip install -e ".[dev]"
python -m pytest --ignore=tests/test_achievements_mysql.py -q   # local (SQLite) suite
```

The full suite (including MySQL-backed tests) requires a `DATABASE_URL`; those tests are skipped without it.

## Branch & PR workflow

- Branch from `main`: `git checkout -b fix/<short-description>`
- One logical change per PR
- Run the local test suite before pushing; keep it green
- PR descriptions: what changed, why, and how it was verified

## Code of conduct

Be kind. This project serves a kid; the tone of the codebase (kid-voice unlock copy, encouragement quotes) is part of the product.
