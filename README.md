<div align="center">
  <h1>ODD JOBS</h1>
  <b>Small agents for small annoying problems.</b>
  <br>
  Each one is a single file. Runs on your laptop. Free API key.
</div>

---

## 💼 Agents

*agents built for things that actually annoy me.*

- [💸 HowLong?](howlong) - Paste in your bank and UPI messages, say
  how many days the money has to last, and it tells you your daily
  budget and where it's actually going

- [📦 ShipBrief](shipbrief) - Paste a GitHub repo link or describe what
  you built, and it writes the Instagram caption, hashtags and a
  one-line learning reflection — in a builder's voice, not an
  influencer's

## Quick start

**1. Clone and enter the folder**
```bash
git clone https://github.com/vaanyaagarwal27/odd-jobs.git
cd odd-jobs/<agent-folder>
```

**2. Install what it needs**
```bash
pip3 install -r requirements.txt
```

**3. Get a free Gemini API key from https://aistudio.google.com/apikey and put it in a `.env` file in this folder**
```
GEMINI_API_KEY=your_key_here
```

**4. Run it**
```bash
python3 -m streamlit run app.py
```

Each agent's own page has its specific setup.
