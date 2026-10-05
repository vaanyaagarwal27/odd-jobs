import json
import os
import time
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.5-flash"


def call_gemini(prompt):
    """Up to 3 retries with 2 / 4 / 8 s back-off; re-raises on final failure."""
    delays = [2, 4, 8]
    for attempt in range(4):
        try:
            return client.models.generate_content(model=MODEL, contents=prompt)
        except Exception as exc:
            if attempt < 3:
                time.sleep(delays[attempt])
            else:
                raise exc

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="How Long Will It Last?", page_icon="💸")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,700&display=swap');

.stApp { background: #FAF4EA; }
html, body, [class*="st-"], button, input, textarea, select {
    font-family: 'DM Sans', sans-serif;
}
.block-container { max-width: 680px; padding-top: 3rem; }

h1, h2, h3 {
    font-weight: 700;
    letter-spacing: -0.03em;
    color: #16150F;
}

.stButton > button {
    background: #16150F;
    color: #FAF4EA;
    border: none;
    border-radius: 999px;
    font-weight: 500;
    padding: 0.65rem 1.8rem;
}
.stButton > button:hover { background: #33301F; color: #FAF4EA; }

[data-testid="stMetric"] {
    background: #F7EBB5;
    border-radius: 22px;
    padding: 1.3rem 1.5rem;
}
[data-testid="stMetricValue"] {
    font-size: 3.4rem;
    font-weight: 700;
    letter-spacing: -0.04em;
}
[data-testid="stMetricLabel"] {
    font-weight: 500;
    opacity: 0.55;
}

textarea, input, [data-baseweb="input"], [data-baseweb="textarea"],
[data-baseweb="base-input"] {
    border-radius: 16px !important;
}
[data-testid="stDataFrame"] { border-radius: 16px; overflow: hidden; }

[data-testid="stAlert"] { border-radius: 16px; }
hr { border-color: #E4D8C4; }
</style>
""", unsafe_allow_html=True)
st.title("💸 How Long Will It Last?")

# ── Inputs ────────────────────────────────────────────────────────────────────

sms_text = st.text_area(
    "Paste your bank / UPI SMS messages here",
    height=220,
    placeholder="Just dump them all in — messy is fine.",
)

col1, col2 = st.columns(2)
with col1:
    money_left = st.number_input("Money you have left (₹)", min_value=0.0, value=None, step=100.0, placeholder="e.g. 2000")
with col2:
    days_left = st.number_input("Days it has to last", min_value=1, value=30, step=1)

analyse = st.button("Analyse", type="primary", use_container_width=True)

# ── Main logic ────────────────────────────────────────────────────────────────

if analyse:
    if not sms_text.strip():
        st.warning("Please paste some SMS messages first.")
        st.stop()
    if money_left is None or money_left <= 0:
        st.warning("Please enter how much money you have left.")
        st.stop()

    # ── Step 1: Extract transactions via Gemini ───────────────────────────────

    with st.spinner("Reading your messages…"):
        extract_prompt = f"""
You are a financial data extractor. Parse the SMS messages below and return ONLY a JSON array.

Rules:
- Include only DEBIT / payment / sent transactions. Skip credits, refunds, OTPs, and balance alerts.
- Each item must have exactly these keys:
    "amount"   : number (positive, in INR, no commas or symbols)
    "merchant" : string (who was paid — UPI ID, merchant name, or "Unknown")
    "category" : one of ["food", "travel", "stationery", "shopping", "other"]
- If you cannot determine the amount reliably, skip that message.
- Return raw JSON only — no markdown, no explanation.

Messages:
\"\"\"
{sms_text}
\"\"\"
"""
        try:
            response = call_gemini(extract_prompt)
        except Exception:
            st.warning(
                "Couldn't reach Gemini right now — the free tier is occasionally busy. "
                "Try again in a minute."
            )
            st.stop()

    raw = response.text.strip()
    # Strip markdown code fences if the model wraps the JSON anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        transactions = json.loads(raw)
    except json.JSONDecodeError:
        st.error("Couldn't parse the transaction data. Try again or simplify the messages.")
        st.code(raw, language="json")
        st.stop()

    if not transactions:
        st.info("No debit transactions found in those messages.")
        st.stop()

    # ── Step 2 & 3: Pure-Python arithmetic ───────────────────────────────────

    df = pd.DataFrame(transactions)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    total_spent = df["amount"].sum()
    category_totals = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    daily_budget = money_left / days_left

    # ── Step 4: Display ───────────────────────────────────────────────────────

    st.divider()

    # Daily budget — big and prominent
    st.metric(
        label=f"Daily budget for the next {int(days_left)} days",
        value=f"₹{daily_budget:,.0f}",
        delta=f"₹{money_left:,.0f} left total",
        delta_color="off",
    )

    col_a, col_b = st.columns(2)
    col_a.metric("Total spent (from SMS)", f"₹{total_spent:,.0f}")
    col_b.metric("Transactions found", len(df))

    st.subheader("Transactions")
    display_df = df[["merchant", "category", "amount"]].copy()
    display_df.columns = ["Merchant", "Category", "Amount (₹)"]
    display_df["Amount (₹)"] = display_df["Amount (₹)"].map(lambda x: f"₹{x:,.0f}")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.subheader("Spending by category")
    st.bar_chart(category_totals, color="#EFCF5C")

    # ── Step 5: Suggestions via Gemini ───────────────────────────────────────

    with st.spinner("Getting suggestions…"):
        category_summary = "\n".join(
            f"- {cat}: ₹{amt:,.0f}" for cat, amt in category_totals.items()
        )
        suggest_prompt = f"""
You're a practical, casual friend giving quick money advice to an Indian college student.

Their spending breakdown:
{category_summary}

They have ₹{money_left:,.0f} left for {int(days_left)} days — that's ₹{daily_budget:,.0f}/day.

Give exactly 3 short, specific suggestions on where they can cut back.
Be direct and friendly, not preachy. Use ₹ amounts. No bullet symbols, just 1. 2. 3.
"""
        try:
            suggestion_response = call_gemini(suggest_prompt)
            st.subheader("💡 3 ways to make it last")
            st.write(suggestion_response.text.strip())
        except Exception:
            st.warning(
                "Couldn't load suggestions right now — Gemini is busy. "
                "Try again in a minute."
            )
