# 📦 ShipBrief

You shipped something. Now you have to write about it, and everything you draft sounds like a LinkedIn post.

Paste a description of what you built, or drop in a public GitHub repo URL. ShipBrief reads the repo's README, languages, and the last 30 commit messages — the commit history tends to reveal what was actually hard, not what the README claims — and returns a caption, hashtags, and a one-line learning reflection written in a builder's voice: lowercase, short sentences, no hype words, no exclamation marks.

## Running it

**1. Clone and enter the folder**
```bash
git clone https://github.com/vaanyaagarwal27/odd-jobs.git
cd odd-jobs/shipbrief
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

---

Built with Streamlit and Gemini 2.5 Flash.
