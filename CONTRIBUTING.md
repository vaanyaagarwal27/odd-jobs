# Contributing to Odd Jobs

Odd Jobs is an open collection of AI projects, one folder each, each one built to fix a real, annoying problem. Use any language, any model, any framework. Your folder is yours.

## What we're aiming for

**Not a chatbot.** If pasting the same thing into a chat app gets the same result, it doesn't belong here.

A project earns its folder by doing something a chat window can't. It should do at least one of these, and the best ones do all three:

- **Reach**: pull in live data a chat can't see, like an API, a feed, an inbox, a repo or your own files.
- **Remember**: keep state between runs, so it knows what it did last time or what normal looks like for you.
- **Act on its own**: run on a schedule or when something happens, and come to you with the result.

**Keep levelling up.** Each new project should use something the collection hasn't done yet, ideally whatever you've just learned. Some directions, as examples only: agents, RAG, multi-agent teams, MCP agents, agent skills, generative UI, voice, local and fine-tuned models.

**Start from your own problem.** If it annoys you, you'll know straight away whether it actually fixes it.

## Folder structure

Every project lives in its own lowercase folder at the top of the repo and carries everything it needs:

````
odd-jobs/
└── your-project/
    ├── app.py              your code (any name, any number of files)
    ├── requirements.txt    every package your code imports
    ├── README.md           see below
    └── .env                your API keys, never committed
````

`requirements.txt` is required so anyone can install your project in one command. If your project isn't Python, use that language's equivalent, like `package.json`.

## The README

Someone who has never seen your project should get it running by copying the code blocks into their terminal, top to bottom, without guessing. Use this shape:

````markdown
# Project Name

One line describing the annoying moment it fixes.

A short paragraph: what you give it, what you get back, and which tools or models it uses.

## Running it

**1. Clone the repo and enter the folder**
```bash
git clone https://github.com/vaanyaagarwal27/odd-jobs.git
cd odd-jobs/your-project
```

**2. Install what it needs**
```bash
pip3 install -r requirements.txt
```

**3. Add your keys to a `.env` file in this folder** (say where to get each key)
```
YOUR_API_KEY=your_key_here
```

**4. Run it**
```bash
python3 app.py
```

---

Built with <tools you used>.
````

Every terminal command goes in its own code block, never inside a sentence. If your project needs extra setup, like a bot token or a scheduled run, add it as another numbered step or its own section after "Running it".

## A few rules

- **Keys never committed.** Keys live in `.env` locally, or in GitHub Actions secrets for scheduled runs. The repo's `.gitignore` already skips `.env`, but check before every commit.
- **Free to try.** Where you can, use free tiers or local models so anyone can run it without paying.
- **AI reads, code computes.** Use the model to turn messy input into structured data. Do totals and maths in code. A model will eventually get a sum wrong in a way that looks right.
- **Fail out loud.** If a model or API call fails, retry, then tell the user what happened. Never crash silently.
- **Ask first before changing `.github/` or someone else's folder.** Workflows run with the repo's secrets, so pull requests that touch them get extra review.
- **Scheduled projects run from your own fork.** Keep your workflow file inside your project folder (for example `your-project/schedule.yml`), and explain in your README how to copy it into `.github/workflows/` and add the keys as GitHub Actions secrets in their own fork. Don't add workflows to this repo.
- **List it.** Add one line for your project to the list in the root README.

## Pushing your project

1. Fork the repo on GitHub (the **Fork** button, top right). This gives you your own copy.

2. Clone your fork and make a branch named after your project:
````bash
git clone https://github.com/<your-username>/odd-jobs.git
cd odd-jobs
git checkout -b your-project
````

3. Build inside `odd-jobs/your-project/`. Before committing, check that no `.env` appears in this list:
````bash
git status --untracked-files=all
````

4. Commit only your folder, plus the root README if you added your line, and push:
````bash
git add your-project/ README.md
git commit -m "add your-project: one line on what it does"
git push origin your-project
````

5. On GitHub, open your fork and click **Compare & pull request**. Say in a line or two what it does. Fixes and improvements to anyone's project go in the same way.

## License

Odd Jobs is released under the MIT License (see LICENSE). By submitting a pull request, you agree your contribution is released under the same license.
