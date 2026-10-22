# Install (instructions for Claude)

You are installing the `sohk-thumbnails` skill for someone who is probably not technical. Do every step yourself. Only ask them for what you can't do (their Gemini key, a click in a browser). Explain each step in one plain sentence, and never show them a wall of terminal output.

Works on Mac and Windows with Claude Code. Commands below are Mac/Linux; Windows equivalents are noted.

## 1. Check Python 3 and git

```bash
python3 --version && git --version
```

- Python 3.10 or newer and git both print a version: carry on.
- **Mac, either missing:** run `xcode-select --install`. A macOS window pops up: tell them to click **Install** and wait for it to finish (about 5 minutes), then re-check.
- **Windows:** use `py --version`. If Python is missing, have them install it from https://www.python.org/downloads/ and tick **"Add python.exe to PATH"** on the first screen. Git: https://git-scm.com/download/win with all defaults.

## 2. Download the skill

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/bradford-marais/sohk-thumbnails.git ~/.claude/skills/sohk-thumbnails
```

If the folder already exists, update it instead: `git -C ~/.claude/skills/sohk-thumbnails pull`.

Then install its Python packages into its own private environment (this touches nothing else on their machine):

```bash
cd ~/.claude/skills/sohk-thumbnails
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
```

Windows: `py -m venv .venv` then `.venv\Scripts\pip install -q -r requirements.txt`.

## 3. Their Gemini API key

The skill uses Google's Gemini image model. They need their own key, **with billing on** (Google's image model has no free tier). A cover costs roughly $0.15–0.60.

Walk them through it, one step at a time:

1. Open https://aistudio.google.com/apikey and sign in with a Google account.
2. Click **Create API key**, pick or create a project, then copy the key.
3. If the page shows **Set up billing** next to the key, click it and add a card. Without billing, image generation fails.
4. Paste the key here in the chat.

When they paste it, write it to the skill's `.env` file. **Never repeat the key back to them or print it in a command output.**

```bash
printf 'GEMINI_API_KEY=%s\n' '<the key>' > ~/.claude/skills/sohk-thumbnails/.env
```

## 4. Check everything works

```bash
~/.claude/skills/sohk-thumbnails/.venv/bin/python ~/.claude/skills/sohk-thumbnails/scripts/check.py
```

Windows: `.venv\Scripts\python.exe scripts\check.py` from the skill folder.

Every line should say `OK`. A `FAIL` line says what to fix (bad key, billing off, missing packages). Fix it and run the check again.

The check saves a sample layout to `~/Desktop/SoHK Thumbnails/_setup-check-sample.png`. Open it with your Read tool, show them, then delete it.

## 5. Hand over

Tell them, in about these words:

> All set. Close Claude Code and open it again so it picks up the new skill. Then just ask for what you need, like:
> - "Make a coach cover for Sarah Jones, title Daily Content Support" (and drop her photo in)
> - "Make a classroom cover called Long-Form Playbook"
>
> Covers land in the **SoHK Thumbnails** folder on your Desktop.

Then offer to make their first cover right now if they have a photo handy. (In this session you can follow `SKILL.md` directly, no restart needed.)
