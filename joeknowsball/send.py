import json
import os
import re
import time
import calendar
import datetime
import feedparser
import requests
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-3.8-flash"

token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]


def call_gemini(prompt):
    """Cycles through fallback models; up to 6 retryable attempts with 10/30/60/120/240 s back-off.
    400/404 removes the model and retries the next immediately. Other non-retryable errors raise."""
    models = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.7-flash"]
    delays = [10, 30, 60, 120, 240]
    retryable = {429, 500, 502, 503, 504}
    defunct = {400, 404}
    model_idx = 0
    delay_idx = 0
    while True:
        if not models:
            raise RuntimeError("call_gemini: all models exhausted")
        model = models[model_idx % len(models)]
        print(f"call_gemini trying {model}...")
        try:
            result = client.models.generate_content(model=model, contents=prompt)
            print(f"call_gemini answered: {model}")
            return result
        except Exception as exc:
            code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
            if code in defunct:
                print(f"call_gemini {model} returned {code}, removing for this run")
                models.remove(model)
                if not models:
                    raise
            elif code is not None and code not in retryable:
                print(f"call_gemini error (not retrying): {exc}")
                raise
            else:
                print(f"call_gemini attempt {delay_idx + 1} failed on {model} ({code}): {exc}")
                if delay_idx < 5:
                    time.sleep(delays[delay_idx])
                    delay_idx += 1
                    model_idx += 1
                else:
                    raise


try:
    here = os.path.dirname(__file__)

    sent_path = os.path.join(here, "sent.json")
    if os.path.exists(sent_path):
        sent_links = json.load(open(sent_path))
    else:
        sent_links = {}
    today = datetime.date.today()
    cutoff_date = today - datetime.timedelta(days=14)
    sent_links = {url: date for url, date in sent_links.items()
                  if datetime.date.fromisoformat(date) >= cutoff_date}

    top_ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15).json()[:30]
    hn_stories = [requests.get(f"https://hacker-news.firebaseio.com/v0/item/{id}.json", timeout=15).json() for id in top_ids]
    for s in hn_stories:
        s["_url"] = s.get("url", f"https://news.ycombinator.com/item?id={s['id']}")

    cutoff = time.time() - 259200
    feed_stories = []
    feed_urls = [l.strip() for l in open(os.path.join(here, "sources.txt")) if l.strip() and not l.startswith("#")]
    for feed_url in feed_urls:
        feed = feedparser.parse(feed_url)
        fresh = []
        for e in feed.entries:
            t = e.get("published_parsed") or e.get("updated_parsed")
            if t and calendar.timegm(t) >= cutoff:
                snippet = re.sub(r"<[^>]+>", "", e.get("summary", ""))[:300]
                fresh.append({"title": e.title, "_url": e.link, "_source": feed.feed.title, "_snippet": snippet})
        print(feed.feed.get("title", feed_url), len(fresh), "fresh entries")
        feed_stories.extend(fresh)

    soul = open(os.path.join(here, "SOUL.md")).read()

    all_stories = hn_stories + feed_stories
    before_filter = len(all_stories)
    all_stories = [s for s in all_stories if s["_url"] not in sent_links]
    print(f"Skipped {before_filter - len(all_stories)} already-sent stories")

    def story_label(s):
        if "_source" in s:
            return f"(from {s['_source']})"
        return f"({s.get('score', 0)} points, {s.get('descendants', 0)} comments)"

    def story_line(i, s):
        line = f"{i+1}. {s['title']} {story_label(s)}"
        if "_snippet" in s and s["_snippet"]:
            line += f"\n   {s['_snippet']}"
        return line

    numbered = "\n".join(story_line(i, s) for i, s in enumerate(all_stories))
    n = len(all_stories)
    pick_prompt = (
        f"{soul}\n\nHere are today's {n} stories:\n{numbered}\n\n"
        f"Return ONLY a JSON array of the numbers (1-{n}) of up to 7 stories worth covering today, "
        "most important first. Return [] if none qualify."
    )

    def _try_parse_pick(response_text):
        raw = response_text.strip()
        if not raw:
            raise ValueError("empty response from Gemini")
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            print(f"Pass 1 JSON parse failed. Raw response:\n{raw}")
            m = re.search(r'\[.*?\]', raw, re.DOTALL)
            if m:
                return json.loads(m.group())
            raise ValueError("no [...] found in pass 1 response")

    picked = None
    for attempt in range(2):
        response_text = call_gemini(pick_prompt).text
        try:
            picked = _try_parse_pick(response_text)
            break
        except Exception as e:
            if attempt == 0:
                print(f"Pass 1 attempt 1 failed ({e}), retrying...")
            else:
                raise RuntimeError(f"Pass 1 failed on both attempts: {e}")
    seen = set()
    chosen_indexes = []
    for num in picked:
        if not isinstance(num, (int, float)) or num != int(num) or not (1 <= int(num) <= n):
            print(f"WARNING: pass 1 returned invalid pick {num!r}, dropping")
            continue
        num = int(num)
        if num in seen:
            print(f"WARNING: pass 1 returned duplicate {num}, dropping")
            continue
        seen.add(num)
        chosen_indexes.append(num - 1)

    if not chosen_indexes:
        tg_url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(tg_url, json={"chat_id": chat_id, "text": "Good morning Vaanya. Nothing worth your time today."})
        print("Nothing to send today.")
        exit()

    chosen = [all_stories[i] for i in chosen_indexes]
    for s in chosen:
        print(s["title"])

    article_texts = []
    valid_chosen = []
    for s in chosen:
        try:
            resp = requests.get("https://r.jina.ai/" + s["_url"], timeout=30)
            if resp.status_code != 200:
                print(f"Jina fetch failed for {s['_url']}: status {resp.status_code}, skipping")
                continue
            text = resp.text[:15000]
            if len(text) < 500:
                print(f"Jina fetch too short for {s['_url']}: {len(text)} chars, skipping")
                continue
            print(s["_url"], len(text), "chars")
            article_texts.append(text)
            valid_chosen.append(s)
        except Exception as exc:
            print(f"Jina fetch error for {s['_url']}: {exc}, skipping")
    chosen = valid_chosen

    if not chosen:
        tg_url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(tg_url, json={"chat_id": chat_id, "text": "Good morning Vaanya. Nothing worth your time today."})
        print("Nothing to send today — all articles failed to fetch.")
        exit()

    reading_parts = []
    for i, (s, text) in enumerate(zip(chosen, article_texts), 1):
        reading_parts.append(f"Story {i}: {s['title']}\n{text}")
    reading = "\n\n".join(reading_parts)
    link_instructions = (
        "\n\nFor each story in your digest, end it with exactly "
        "\"Full story: [LINK n]\" where n is that story's number. "
        "Never write any URL yourself."
    )
    prompt = f"{soul}\nAlready taught: (none yet)\nToday's reading:\n{reading}{link_instructions}"

    digest = call_gemini(prompt).text

    pieces = [p.strip() for p in digest.split("---") if p.strip()]
    piece_to_story_num = {}
    for idx, piece in enumerate(pieces):
        m = re.search(r'\[LINK (\d+)\]', piece)
        if m:
            piece_to_story_num[idx] = int(m.group(1))

    link_map = {f"[LINK {i}]": s["_url"] for i, s in enumerate(chosen, 1)}
    for idx in range(len(pieces)):
        for placeholder, url in link_map.items():
            pieces[idx] = pieces[idx].replace(placeholder, url)
    unreplaced = [tok for piece in pieces for tok in re.findall(r'\[LINK \d+\]', piece)]
    for p in unreplaced:
        print(f"WARNING: {p} was not replaced — no matching story URL found")

    if os.environ.get("GITHUB_EVENT_NAME") == "schedule":
        ist_offset = datetime.timedelta(hours=5, minutes=30)
        now_ist = datetime.datetime.utcnow() + ist_offset
        target_ist = now_ist.replace(hour=7, minute=0, second=0, microsecond=0)
        if now_ist < target_ist:
            wait_seconds = (target_ist - now_ist).total_seconds()
            print(f"Joe waiting {wait_seconds:.0f}s until 7:00am IST...")
            time.sleep(wait_seconds)

    tg_url = f"https://api.telegram.org/bot{token}/sendMessage"
    hype_words = ["busy", "huge", "significant", "major", "crazy", "massive", "exciting", "game-changer", "revolutionary"]
    if pieces:
        triggered = next((w for w in hype_words if re.search(r'\b' + re.escape(w) + r'\b', pieces[0], re.IGNORECASE)), None)
        if triggered:
            story_count = len(pieces) - 1
            pieces[0] = f"Morning Vaanya. {story_count} stories today."
            print(f"Greeting replaced — triggered by: '{triggered}'")
    send_errors = []
    today_str = today.isoformat()
    for i, piece in enumerate(pieces):
        resp = requests.post(tg_url, json={"chat_id": chat_id, "text": piece})
        print(resp.status_code, resp.text)
        try:
            ok = resp.status_code == 200 and resp.json().get("ok") is True
        except Exception:
            ok = False
        if ok:
            story_num = piece_to_story_num.get(i)
            if story_num is not None and 1 <= story_num <= len(chosen):
                sent_links[chosen[story_num - 1]["_url"]] = today_str
        else:
            print(f"Telegram delivery failed for piece {i}: status {resp.status_code}")
            send_errors.append(i)
    written_nums = set(piece_to_story_num.values())
    for i, s in enumerate(chosen, 1):
        if i not in written_nums:
            sent_links[s["_url"]] = today_str
    with open(sent_path, "w") as f:
        json.dump(sent_links, f, indent=2)
    if send_errors:
        raise RuntimeError(f"Telegram delivery failed for {len(send_errors)} piece(s): indices {send_errors}")
except Exception as exc:
    tg_url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(tg_url, json={"chat_id": chat_id, "text": "Joe couldn't finish this morning's digest: " + str(exc)[:300]})
    raise
