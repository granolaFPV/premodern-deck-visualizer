# Magic: The Gathering — Premodern Deck Visualizer '98

A utilitarian, retro-styled web visualizer for MTG Premodern format decks.

## Features
- **Authentic Premodern Layout**: 6x10 mainboard grid touching edges + zippered alternating sideboard layout.
- **Premodern Era Prioritization**: Respects exact set/collector numbers (including modern retro frames like DMR 303/324) and defaults un-set cards to authentic 4th Edition through Scourge printings.
- **Card Art & Language Picker**: Switch any individual card to foreign language versions (e.g. Japanese) or curated physical scans.
- **Custom Scans & Photos**: Drag-and-drop local physical card scans or paste URLs.
- **High-Definition Canvas Exporter**: Clean photographic PNG export with natural table framing, realistic lighting, and zero watermarks.
- **Moxfield Integration**: Instant 1-click import from Moxfield deck URLs.

## Running Locally
Requires Python 3.7+ (pure standard library, zero external pip dependencies):
```bash
python3 server.py 8080
```
Open `http://localhost:8080` in your browser.

## Cloud Deployment (Render, Railway, Heroku, etc.)
The server dynamically binds to the `$PORT` environment variable:
- **Build Command**: (none)
- **Start Command**: `python3 server.py`
