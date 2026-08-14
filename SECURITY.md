# Security Policy

## Supported versions

The project follows trunk-based development: `main` is the only supported branch.

## Reporting a vulnerability

This is a family project — please report issues directly via [GitHub Issues](https://github.com/mariusiaowego-commits/dizical/issues) with the `security` label.

If the issue involves a live credential or personal data, **do not** open a public issue. Send a private note via the issue template's "confidential" path or open a draft issue and mention `@mariusiaowego`.

## Design principles

- **No secrets in source** — credentials are read from environment variables (`TELEGRAM_BOT_TOKEN`, `DATABASE_URL`, `COS_SECRET_ID`, ...). `.env*` files are gitignored.
- **No personal data in the repo** — `data/` (SQLite DBs, uploads, reports, badge drafts) and agent working docs are gitignored; the repo ships code only.
- **Web auth** — password hashes use scrypt; sessions use HMAC-signed tokens; invite links use `secrets.token_urlsafe(32)`.
- **Dual-backend** — SQLite for local dev, MySQL for production; both use parameterized queries (`?` / `%s`).
