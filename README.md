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

## Quick start

```bash
git clone https://github.com/vaanyaagarwal27/odd-jobs.git
cd odd-jobs/howlong
pip3 install -r requirements.txt
python3 -m streamlit run app.py
```

Note you need a `.env` file in the agent folder with
`GEMINI_API_KEY=your_key_here`, free from
https://aistudio.google.com/apikey
