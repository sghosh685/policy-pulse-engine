# 🔍 NetZeroX Policy Pulse Engine

**Cross-Border Compliance Insurance for North American Energy Leaders.**

The automated intelligence engine that scrapes US and Canadian regulatory
sources, analyzes updates with AI, and generates executive briefings.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Set up AI analysis
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# 3. Initialize the database
python main.py init

# 4. Run the full pipeline
python main.py pipeline
```

## Commands

| Command | What It Does |
|:--------|:-------------|
| `python main.py init` | Create the SQLite database |
| `python main.py scrape` | Scrape all 8 regulatory sources |
| `python main.py analyze` | AI-analyze new items (or keyword fallback) |
| `python main.py report` | Generate the weekly executive briefing |
| `python main.py pipeline` | Run scrape → analyze → report |
| `python main.py stats` | Show database statistics |

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  8 Sources   │───▶│  scraper.py  │───▶│  SQLite DB   │
│  (RSS/HTML)  │    │  (feedparser │    │  (Structured │
│              │    │   + BS4)     │    │   Storage)   │
└─────────────┘    └──────────────┘    └──────┬───────┘
                                              │
                                    ┌─────────▼─────────┐
                                    │   analyzer.py      │
                                    │   (OpenAI GPT-4o)  │
                                    └─────────┬─────────┘
                                              │
                                    ┌─────────▼─────────┐
                                    │ report_generator   │
                                    │ (Jinja2 → MD/PDF)  │
                                    └─────────┬─────────┘
                                              │
                                    ┌─────────▼─────────┐
                                    │   emailer.py       │
                                    │   (SMTP Delivery)  │
                                    └───────────────────┘
```

## Sources Monitored

| # | Source | Country | Type |
|:--|:-------|:--------|:-----|
| 1 | EPA (Federal Register) | 🇺🇸 US | RSS |
| 2 | SEC (Climate Disclosure) | 🇺🇸 US | RSS |
| 3 | DOE (Clean Energy Funding) | 🇺🇸 US | RSS |
| 4 | FERC (Pipeline/LNG) | 🇺🇸 US | RSS |
| 5 | Canada Gazette Part I | 🇨🇦 CA | RSS |
| 6 | Alberta Energy Regulator | 🇨🇦 CA | HTML |
| 7 | Texas Railroad Commission | 🇺🇸 US | HTML |
| 8 | BC Energy Regulator | 🇨🇦 CA | HTML |

## Configuration

Edit `config.yaml` to:
- Add/remove sources
- Modify keyword filters (critical / high / medium)
- Configure AI model and temperature
- Set up email delivery

## License

Proprietary — NetZeroX Labs © 2026
