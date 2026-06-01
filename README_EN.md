# 🎵 dizical

[English](./README_EN.md) · [中文](./README.md)

> A home-grown practice management system for Chinese bamboo flute education — tracking lessons, payments, daily practice, stage progression, and achievements.

<p align="center">
  <img src="https://img.shields.io/badge/python-3.14-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/tests-49%20passed-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/lessons-211%20days%20imported-blue" alt="Lessons">
</p>

---

## What It Does

**Parent side:**
- Lesson scheduling with automatic Saturday generation
- Fee tracking with payment reminders on lesson day
- `dizical reminders sync` — two-way sync with Apple Reminders (type "单吐10分钟" in Reminders, it logs a practice session)
- Web-based lesson calendar and practice history editor at `/config/lessons` and `/config/records`

**Kid side (iPad, 1024×768):**
- `/prepare` — what to practice today, visual item cards
- `/practice` — log sessions with duration and notes
- `/achievements` — badge collection earned through consistent practice
- `/report` — bamboo flute heatmap, click bars for daily breakdown
- `/praise` — random encouragement quotes from a parent-curated pool

**Teacher side:**
- Weekly assignment system with stage-based progression (7-day cycles)
- Item-level practice requirements with fuzzy name matching
- Practice heatmap showing attendance patterns over time

---

## Quick Start

```bash
pip install -e .

# Start the iPad interface
dizical kid start
# → http://<your-ip>:8765

# CLI
dizical lessons list
dizical practice category list
dizical reminders sync
```

---

## Tech Stack

Python 3.12 + SQLite + FastAPI + Vanilla JS + GSAP. No React. No npm. No cloud.

---

## API Use

GPT-4o is used for AI-generated monthly practice report images. See `docs/OPENAI_PRO_PLAN.md` for expansion plans.

---

## Badge Collection

35 enamel-pin style badges across 6 categories:

- **Streak** — `streak_1/3/7/14/30/100` (1 day to 100 days)
- **Cumulative** — `total_60/300/600/1000` (60 minutes and up)
- **Grade** — `grade_1` through `grade_10` (1st to 10th exam achievements)
- **Top** — `top1/top2/top3` (monthly practice top 3)
- **Festival** — `lucky_61_2026/2027/2028/2029/2030` (Children's Day limited: each year on June 1, practice to unlock)
- **Special** — `first_log`, `double`, `week_champ`, `full_month`, `all_items`, and others

---

## License

MIT
