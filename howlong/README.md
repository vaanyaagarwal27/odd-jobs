# 💸 HowLong?

It's the middle of the month, you have no idea where the money went, and payday is two weeks away.

Paste your bank and UPI messages in — messy is fine. OTPs and credits are ignored. Gemini pulls out each amount and categorises it; the arithmetic is done in Python, not by the model, so the numbers are right. Tell it how many days the money has to last and it gives you a daily budget and a breakdown of where it's actually going.

## Running it

```bash
git clone https://github.com/vaanyaagarwal27/odd-jobs.git
cd odd-jobs/howlong
pip3 install -r requirements.txt
python3 -m streamlit run app.py
```

Note you need a `.env` file in this folder with
`GEMINI_API_KEY=your_key_here`, free from
https://aistudio.google.com/apikey

---

Built with Streamlit and Gemini 2.5 Flash.
