import json
import os
import re
import time
import requests
import streamlit as st
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

st.set_page_config(page_title="ShipBrief", page_icon="📦")
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
    background: #E6DCF2;
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

.stCode code, pre code {
    white-space: pre-wrap !important;
    word-break: break-word !important;
}
</style>
""", unsafe_allow_html=True)
st.title("📦 ShipBrief")

# ── Inputs ────────────────────────────────────────────────────────────────────

tab_describe, tab_github = st.tabs(["Describe it", "GitHub repo"])

with tab_describe:
    description_text = st.text_area(
        "What did you build?",
        height=220,
        placeholder="Tell me what you built, what tools you used, and what problem it solves.",
        key="describe_input",
    )
    run_describe = st.button("Generate", type="primary", use_container_width=True, key="run_describe")

with tab_github:
    repo_url = st.text_input(
        "Public GitHub repo URL",
        placeholder="https://github.com/owner/repo",
        key="github_input",
    )
    run_github = st.button("Generate", type="primary", use_container_width=True, key="run_github")

# ── GitHub fetch helpers ──────────────────────────────────────────────────────

def fetch_github_description(owner, repo):
    """Fetch repo metadata, README, languages, and recent commits into one string."""
    base = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    parts = []
    any_success = False

    # Repo metadata
    try:
        r = requests.get(base, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        desc = data.get("description") or ""
        topics = ", ".join(data.get("topics") or [])
        parts.append(f"Repo: {owner}/{repo}")
        if desc:
            parts.append(f"Description: {desc}")
        if topics:
            parts.append(f"Topics: {topics}")
        any_success = True
    except Exception:
        pass

    # README
    try:
        r = requests.get(
            f"{base}/readme",
            headers={"Accept": "application/vnd.github.v3.raw"},
            timeout=10,
        )
        r.raise_for_status()
        readme = r.text[:4000]
        parts.append(f"\nREADME (truncated to 4000 chars):\n{readme}")
        any_success = True
    except Exception:
        pass

    # Languages
    try:
        r = requests.get(f"{base}/languages", headers=headers, timeout=10)
        r.raise_for_status()
        langs = ", ".join(r.json().keys())
        if langs:
            parts.append(f"\nLanguages: {langs}")
        any_success = True
    except Exception:
        pass

    # Recent commits
    try:
        r = requests.get(f"{base}/commits", headers=headers, params={"per_page": 30}, timeout=10)
        r.raise_for_status()
        messages = [c["commit"]["message"].splitlines()[0] for c in r.json()]
        if messages:
            parts.append("\nRecent commit messages:\n" + "\n".join(f"- {m}" for m in messages))
        any_success = True
    except Exception:
        pass

    return "\n".join(parts), any_success

# ── Shared generation logic ───────────────────────────────────────────────────

SYSTEM_INSTRUCTION = """You write Instagram captions for builders documenting their work. Not influencers. Builders.

Voice rules — follow all of them without exception:
- lowercase everything (except proper nouns and acronyms like API, CSS, JS)
- short sentences. no fluff.
- never use exclamation marks
- never use the words "excited", "love", "journey", "passionate", "thrilled", "proud", "amazing", "awesome", "incredible"
- no filler openers like "so," or "honestly," or "okay so"
- no em-dashes used for dramatic effect
- sound like a developer writing a commit message, not a lifestyle blogger

Caption format to follow: lead with what was built and how. name the specific tools or constraints. end with what it does or why it matters. 2–3 sentences max.

Good example: "built a chrome extension that flags toxic comments before you post them. vanilla js + perspective api — no framework, no build step. runs entirely in the content script."

Bad example: "So excited to finally share this. I've been pouring so much love into this project and I'm so proud of how it turned out!"

Reflection: one plain sentence about what you actually learned. specific, not generic. not "learned a lot about X" — say what specifically surprised you or broke your mental model. If commit messages are provided, base it on what they reveal about what was actually hard, not on what the README claims.

Always respond with valid JSON only — no markdown, no explanation, no code fences.
Use this exact shape:
{
  "caption": "2–3 sentence caption",
  "hashtags": ["tag1", "tag2", ...],
  "reflection": "One-line learning reflection"
}
hashtags should be 10–15 items, without the # symbol. keep hashtags relevant and specific, not generic (#coding is too vague)."""


def run_generation(description):
    prompt = f"{SYSTEM_INSTRUCTION}\n\nProject description:\n{description}"

    with st.spinner("Generating…"):
        try:
            response = call_gemini(prompt)
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
        result = json.loads(raw)
    except json.JSONDecodeError:
        st.error("Couldn't parse the response. Try again.")
        st.code(raw, language="json")
        st.stop()

    st.divider()

    st.subheader("Caption")
    st.code(result.get("caption", ""), language=None, wrap_lines=True)

    st.subheader("Hashtags")
    hashtags = result.get("hashtags") or []
    st.code(" ".join(f"#{tag}" for tag in hashtags), language=None, wrap_lines=True)

    st.subheader("Learning reflection")
    st.code(result.get("reflection", ""), language=None, wrap_lines=True)

# ── Main logic ────────────────────────────────────────────────────────────────

if run_describe:
    if not description_text.strip():
        st.warning("Please describe what you built first.")
        st.stop()
    run_generation(description_text.strip())

if run_github:
    if not repo_url.strip():
        st.warning("Please enter a GitHub repo URL.")
        st.stop()

    match = re.search(r"github\.com/([^/]+)/([^/?\s]+)", repo_url.strip())
    if not match:
        st.warning("Couldn't parse that URL — expected https://github.com/owner/repo")
        st.stop()

    owner, repo = match.group(1), match.group(2).rstrip(".git")

    with st.spinner(f"Fetching {owner}/{repo}…"):
        description, any_success = fetch_github_description(owner, repo)

    if not any_success:
        st.warning(
            f"Couldn't fetch anything from {owner}/{repo}. "
            "Make sure the repo is public and the URL is correct."
        )
        st.stop()

    run_generation(description)
