# 🗞️ Joe

You open X to catch up on AI and lose an hour to threads, hot takes and ads, and still couldn't explain to anyone what actually happened.

Every morning at 7am Joe reads Hacker News and a list of blogs, picks what matters, reads the actual articles, and sends you one Telegram message per story: what happened, the new terms with a trick to remember them, and why it matters to you. He remembers what he's sent so you never get the same story twice. Gemini picks and writes; Jina Reader (r.jina.ai, free, no key) turns each article into clean text so Joe reads the real thing instead of guessing from headlines; Python handles the links and memory.

## Running it

**1. Clone and enter the folder**
```bash
git clone https://github.com/vaanyaagarwal27/odd-jobs.git
cd odd-jobs/joeknowsball
```

**2. Install what it needs**
```bash
pip3 install -r requirements.txt
```

**3. Make a Telegram bot:** message @BotFather, send `/newbot`, and copy the token it gives you. Send your new bot any message, then open `https://api.telegram.org/bot<your-token>/getUpdates` and copy the number after `"chat":{"id":`.

**4. Get a free Gemini API key from https://aistudio.google.com/apikey and put all three in a `.env` file in this folder**
```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
GEMINI_API_KEY=...
```

**5. Run it**
```bash
python3 send.py
```

## Every morning, automatically

Add the same three values as repository secrets (Settings → Secrets and variables → Actions). The workflow in `.github/workflows/joe.yml` starts at 6:28am IST and sends at 7:00. Run it anytime from the Actions tab. Your GitHub token needs the workflow scope to push workflow files.

## Make him yours

Edit `SOUL.md` to change who Joe is writing to, what he covers and what he skips. Edit `sources.txt` to change the RSS feeds he reads — one feed per line.

## Notes

Never commit `.env`. If Joe fails he messages you why. If one Gemini model is busy he falls back to another. Jina Reader is free for basic use, so check Jina's terms before commercial use.
