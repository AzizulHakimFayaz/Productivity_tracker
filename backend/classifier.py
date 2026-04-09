"""
activity_classifier.py — Enhanced ActivityClassifier
=====================================================
Improvements over v1:
  • 9 categories instead of 5 (+ designing, browsing, meetings, planning, reading)
  • User personalization: feedback loop + per-user override store (JSON)
  • Performance: LRU cache, batch embeddings, lazy model load, early-exit rules
  • Accuracy: URL-path-aware matching, confidence ensemble (BGE + TF-IDF),
              richer domain/keyword tables, YouTube intent detection
"""

from __future__ import annotations

import json
import os
import re
from collections import OrderedDict
from pathlib import Path
from typing import Optional
from backend.ai_debug import ai_debug_log, set_model_status


# ══════════════════════════════════════════════════════════════════════════════
#  LRU Cache (no external deps)
# ══════════════════════════════════════════════════════════════════════════════

class _LRUCache:
    """Simple thread-unsafe LRU cache (adequate for single-threaded tracking)."""

    def __init__(self, maxsize: int = 2048):
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: str) -> Optional[str]:
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, key: str, value: str) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)

    def invalidate(self, key: str) -> None:
        self._cache.pop(key, None)


# ══════════════════════════════════════════════════════════════════════════════
#  ActivityClassifier
# ══════════════════════════════════════════════════════════════════════════════

class ActivityClassifier:
    """
    Classifies a foreground window into one of 9 activity categories.

    Categories
    ----------
    coding        — writing/running code, using an IDE, terminal, git
    learning      — tutorials, courses, documentation, AI Q&A, studying
    writing       — long-form documents, essays, notes, blogs
    communication — email, chat, video calls, social DMs
    entertainment — YouTube (fun), games, music, social feeds
    designing     — Figma, Photoshop, UI mockups, vector art
    browsing      — unfocused web browsing, search engines, news
    meetings      — scheduled video/audio calls, calendar, standups
    planning      — task managers, kanban boards, project trackers, notes
    reading       — e-readers, PDFs, long articles, Pocket, Instapaper
    unknown       — low-confidence or unrecognised
    """

    # ── Category list ─────────────────────────────────────────────────────────
    CATEGORIES = [
        "coding", "learning", "writing", "communication",
        "entertainment", "designing", "browsing", "meetings", "planning", "reading",
    ]

    # ── App sets ──────────────────────────────────────────────────────────────
    CODING_APPS = {
        "code.exe", "code - insiders.exe", "cursor.exe", "windsurf.exe", "zed.exe",
        "pycharm64.exe", "idea64.exe", "webstorm64.exe", "clion64.exe",
        "rider64.exe", "datagrip64.exe", "goland64.exe", "rubymine64.exe",
        "devenv.exe",  # Visual Studio
        "neovim.exe", "nvim.exe", "vim.exe", "gvim.exe",
        "sublime_text.exe", "atom.exe", "notepad++.exe", "brackets.exe",
        "eclipse.exe", "netbeans64.exe", "androidstudio64.exe",
        "python.exe", "pythonw.exe", "node.exe", "ruby.exe",
        "java.exe", "javaw.exe", "cargo.exe", "rustc.exe", "go.exe",
        "git.exe", "git-bash.exe", "powershell.exe", "pwsh.exe",
        "cmd.exe", "wt.exe", "windowsterminal.exe",
        "bash.exe", "sh.exe", "mintty.exe",
        "docker.exe", "docker desktop.exe",
        "postman.exe", "insomnia.exe", "httpie.exe",
        "dbeaver.exe", "tableplus.exe", "sequel pro.exe",
    }

    DESIGNING_APPS = {
        "figma.exe", "figmadraft.exe",
        "photoshop.exe", "illustrator.exe", "indesign.exe", "xd.exe",
        "sketch.exe", "framer.exe",
        "affinity designer.exe", "affinity photo.exe", "affinitydesigner.exe",
        "inkscape.exe", "gimp-2.10.exe", "gimp.exe",
        "blender.exe", "cinema 4d.exe", "c4d.exe",
        "zeplin.exe", "avocode.exe", "principle.exe",
        "canva.exe", "coreldraw.exe",
        "mspaint.exe", "paint.net.exe",
    }

    MEETINGS_APPS = {
        "zoom.exe", "zoomapp.exe",
        "teams.exe", "msteams.exe",
        "webex.exe", "webexmta.exe", "ciscowebexmeetings.exe",
        "skype.exe",
        "slack.exe",        # also communication but call detection below
        "discord.exe",      # same
        "lync.exe", "ringcentral.exe",
        "googledrivesyncdaemon.exe",   # sometimes runs during Meet
    }

    PLANNING_APPS = {
        "notion.exe", "notionenhancer.exe",
        "obsidian.exe", "logseq.exe", "remnote.exe",
        "todoist.exe", "ticktick.exe", "things3.exe",
        "trello.exe",
        "clickup.exe", "asana.exe",
        "excel.exe",  # often used for planning/tracking
        "onenote.exe",
        "miro.exe",
    }

    READING_APPS = {
        "kindle.exe",
        "acrobat.exe", "acrord32.exe", "foxitreader.exe",
        "sumatrapdf.exe", "calibre.exe",
        "anki.exe", "ankiwin.exe",
        "icecreamreader.exe",
    }

    LEARNING_APPS = {
        "anki.exe", "ankiwin.exe",    # flashcards -> always learning
    }

    WRITING_APPS = {
        "winword.exe", "word.exe",
        "soffice.exe", "libreoffice.exe",
        "notepad.exe", "wordpad.exe",
        "typora.exe", "markdownmonster.exe",
        "scrivener.exe",
        "grammarly.exe",
        "latex.exe", "texmaker.exe", "texstudio.exe",
    }

    COMMUNICATION_APPS = {
        "slack.exe", "discord.exe",
        "teams.exe", "msteams.exe",
        "skype.exe", "webex.exe",
        "telegram.exe", "signal.exe", "whatsapp.exe",
        "outlook.exe", "thunderbird.exe", "mailbird.exe",
        "microsoft office outlook.exe",
        "lync.exe", "ringcentral.exe",
    }

    ENTERTAINMENT_APPS = {
        "spotify.exe", "steam.exe", "epicgameslauncher.exe",
        "vlc.exe", "wmplayer.exe", "mpc-hc64.exe", "mpc-hc.exe",
        "itunes.exe", "musicbee.exe", "foobar2000.exe",
        "netflix.exe", "disneyplus.exe", "hbomax.exe",
        "xboxapp.exe", "playnite.exe",
        "obs64.exe", "obs.exe",
        "minecraft.exe", "valorant.exe", "leagueclient.exe",
    }

    # ── Domain sets ───────────────────────────────────────────────────────────
    CODING_DOMAINS = {
        "github.com", "gitlab.com", "bitbucket.org",
        "stackoverflow.com", "stackexchange.com",
        "docs.python.org", "developer.mozilla.org", "devdocs.io",
        "npmjs.com", "pypi.org", "crates.io", "pkg.go.dev",
        "kubernetes.io", "docker.com", "hub.docker.com",
        "replit.com", "codepen.io", "jsfiddle.net", "codesandbox.io",
        "leetcode.com", "hackerrank.com", "codewars.com",
        "vercel.com", "netlify.com", "railway.app",
        "huggingface.co", "kaggle.com",
    }

    DESIGNING_DOMAINS = {
        "figma.com", "framer.com", "sketch.com",
        "dribbble.com", "behance.net",
        "canva.com", "adobe.com",
        "colorhunt.co", "coolors.co", "color.adobe.com",
        "unsplash.com", "pexels.com", "freepik.com",
        "fontawesome.com", "fonts.google.com", "myfonts.com",
        "spline.design", "rive.app",
        "zeplin.io", "avocode.com",
        "ui8.net", "mobbin.com", "screenlane.com",
    }

    MEETINGS_DOMAINS = {
        "meet.google.com", "zoom.us", "teams.microsoft.com",
        "whereby.com", "around.co", "loom.com",
        "cal.com", "calendly.com", "doodle.com",
        "calendar.google.com", "outlook.office.com/calendar",
        "webex.com",
    }

    PLANNING_DOMAINS = {
        "notion.so", "trello.com", "asana.com",
        "clickup.com", "linear.app", "jira.atlassian.com",
        "basecamp.com", "monday.com",
        "todoist.com", "ticktick.com",
        "miro.com", "mural.co",
        "airtable.com",
        "obsidian.md",
        "drive.google.com",
    }

    READING_DOMAINS = {
        "getpocket.com", "instapaper.com", "readwise.io",
        "kindle.amazon.com", "scribd.com",
        "longform.org", "longreads.com",
        "archive.org",     # often reading old books/articles
    }

    LEARNING_DOMAINS = {
        "udemy.com", "coursera.org", "edx.org", "khanacademy.org",
        "pluralsight.com", "skillshare.com", "linkedin.com/learning",
        "classcentral.com", "freecodecamp.org", "theodinproject.com",
        "medium.com", "dev.to", "hashnode.com",
        "arxiv.org", "semanticscholar.org", "researchgate.net",
        "wikipedia.org", "britannica.com",
        "w3schools.com", "tutorialspoint.com", "geeksforgeeks.org",
        "merriam-webster.com", "dictionary.cambridge.org", "dictionary.com",
        "oxfordlearnersdictionaries.com", "thesaurus.com",
        "claude.ai", "chat.openai.com", "chatgpt.com",
        "gemini.google.com", "bard.google.com",
        "perplexity.ai", "phind.com", "you.com",
        "docs.anthropic.com",
        "learn.microsoft.com", "docs.microsoft.com",
        "developer.apple.com",
    }

    WRITING_DOMAINS = {
        "notion.so", "docs.google.com", "docs.zoho.com",
        "overleaf.com", "hackmd.io",
        "grammarly.com", "hemingwayapp.com",
        "substack.com", "ghost.org", "wordpress.com",
    }

    COMMUNICATION_DOMAINS = {
        "slack.com", "discord.com",
        "mail.google.com", "outlook.live.com", "outlook.office.com",
        "web.whatsapp.com", "web.telegram.org",
        "twitter.com", "x.com",
        "messenger.com",
    }

    BROWSING_DOMAINS = {
        "google.com", "bing.com", "duckduckgo.com",
        "search.yahoo.com", "ecosia.org", "brave.com/search",
        "news.google.com", "news.ycombinator.com",
        "bbc.com", "cnn.com", "theguardian.com", "nytimes.com",
        "techcrunch.com", "theverge.com", "wired.com",
        "arstechnica.com", "engadget.com",
    }

    ENTERTAINMENT_DOMAINS = {
        "youtube.com", "twitch.tv", "netflix.com",
        "disneyplus.com", "hbomax.com", "hulu.com",
        "primevideo.com", "crunchyroll.com", "funimation.com",
        "spotify.com", "soundcloud.com", "tiktok.com",
        "9gag.com", "imgur.com",
        "chess.com", "lichess.org",
        "facebook.com", "instagram.com", "pinterest.com", "snapchat.com",
        "reddit.com", "tumblr.com",
        "store.steampowered.com", "epicgames.com",
        "itch.io", "gog.com", "origin.com",
    }

    # ── Title keyword lists ───────────────────────────────────────────────────
    CODING_TITLE_KEYWORDS = {
        "terminal", "console", "powershell", "bash", "cmd", "shell",
        "debug", "debugger", "breakpoint", "localhost", "127.0.0.1",
        "git commit", "git push", "git pull", "merge request", "pull request",
        "minilm", "bert", "llm", "gpt", "transformer", "embedding",
        "fine-tun", "finetun", "training model", "model performance",
        "fastembed", "sentence-transformer", "huggingface", "pytorch", "tensorflow",
        "langchain", "onnx", "inference", "tokenizer",
        "import ", "def ", "class ", "npm install", "pip install",
    }

    DESIGNING_TITLE_KEYWORDS = {
        "figma", "sketch", "framer", "adobe xd", "photoshop", "illustrator",
        "wireframe", "prototype", "mockup", "ui design", "ux design",
        "color palette", "typography", "icon set", "design system",
        "logo design", "brand identity", "vector",
    }

    MEETINGS_TITLE_KEYWORDS = {
        "zoom meeting", "google meet", "teams meeting", "webex meeting",
        "join meeting", "meeting room", "video call", "conference call",
        "standup", "daily sync", "weekly sync", "1:1", "one-on-one",
        "calendar", "schedule", "invite", "rsvp",
    }

    PLANNING_TITLE_KEYWORDS = {
        "kanban", "sprint", "backlog", "roadmap", "milestone",
        "task list", "to-do", "todo", "project plan", "gantt",
        "notion", "obsidian", "logseq", "trello board",
        "quarterly plan", "okr", "goal",
    }

    READING_TITLE_KEYWORDS = {
        "reading", "e-book", "ebook", "epub", "pdf viewer",
        "pocket", "instapaper", "readwise",
        "chapter", "kindle",
    }

    LEARNING_TITLE_KEYWORDS = {
        "tutorial", "course", "learn", "how to", "how-to", "lecture", "explained",
        "guide", "introduction to", "beginner", "advanced", "masterclass",
        "career advice", "study", "education", "training",
        "tips", "tricks", "best practices", "interview", "resume",
        "wikipedia", "research", "thesis", "paper", "article",
        "definition", "meaning", "dictionary", "thesaurus", "synonym",
        "improving", "optimize", "performance", "comparison",
        "what is", "why is", "when to", "difference between", "vs ",
    }

    COMMUNICATION_TITLE_KEYWORDS = {
        "email", "inbox", "message", "chat",
        "slack", "discord", "whatsapp", "telegram",
        "twitter", "tweet", "linkedin", "notification",
    }

    WRITING_TITLE_KEYWORDS = {
        "untitled", "document", "draft", "essay", "report",
        "notes", "journal", "blog", "article writing",
    }

    BROWSING_TITLE_KEYWORDS = {
        "search results", "google search", "bing search",
        "hacker news", "news feed", "breaking news",
    }

    ENTERTAINMENT_TITLE_KEYWORDS = {
        "watch", "stream", "movie", "episode", "season", "anime",
        "music video", "playlist", "gaming", "gameplay", "live stream",
        "funny", "meme", "shorts",
        "games", "game", "play online", "novel", "manga", "comic",
        "download game", "pc game", "free download", "crack", "skidrow", "codex",
        "torrent", "pirate", "repack",
    }

    OWN_APP_NAMES = {"focus.io", "antigravity", "python", "python3"}

    # ── YouTube intent keywords ───────────────────────────────────────────────
    # If domain == youtube.com, use title to infer learning vs entertainment.
    _YT_LEARNING_KEYWORDS = {
        "tutorial", "course", "how to", "explained", "introduction",
        "lecture", "lesson", "learn", "guide", "deep dive", "breakdown",
        "theory", "concept", "documentation", "full course",
    }
    _YT_ENTERTAINMENT_KEYWORDS = {
        "funny", "meme", "reaction", "vlog", "prank", "challenge",
        "shorts", "music video", "mv", "official video", "live",
        "gaming", "gameplay", "let's play", "highlight",
    }

    # ── Browser suffix cleaner ────────────────────────────────────────────────
    _BROWSER_SUFFIX_RE = re.compile(
        r"\s*[-–|]\s*(?:"
        r"Google Chrome|Mozilla Firefox|Microsoft Edge|Brave|Opera|Safari|"
        r"Chrome|Firefox|Edge|"
        r"Claude|ChatGPT|Gemini|Perplexity|Copilot|"
        r"Stack Overflow|GitHub|YouTube|Reddit|Google|Bing|DuckDuckGo"
        r").*$",
        re.IGNORECASE,
    )
    _GENERIC_TITLES = {
        "new tab", "new page", "start page", "about:blank",
        "speed dial", "most visited",
    }

    # ── AI category descriptions (rich sentences for BGE) ─────────────────────
    CATEGORY_DESCRIPTIONS = {
        "coding": (
            "Writing source code in Python, JavaScript, TypeScript, Rust, Go, Java or C++. "
            "Using VS Code, PyCharm, a terminal, git, Docker. Debugging, compiling, deploying. "
            "Visiting GitHub, Stack Overflow, npm docs. "
            "Working with ML models, embeddings, transformers, LLMs, neural networks."
        ),
        "learning": (
            "Watching educational videos or online courses on Udemy, Coursera, Khan Academy. "
            "Reading Wikipedia, tutorials, documentation, how-to guides, research papers. "
            "Asking Claude, ChatGPT, or Perplexity to explain a concept. "
            "Studying for an exam, using Anki flashcards, taking notes for a course."
        ),
        "writing": (
            "Writing an essay, blog post, report or long-form document in Word, Notion, Google Docs. "
            "Composing or editing a draft. Using Grammarly. Writing a newsletter or LaTeX paper."
        ),
        "communication": (
            "Sending or reading emails in Gmail or Outlook. "
            "Chatting on Slack, Discord, WhatsApp, or Telegram. "
            "Posting on Twitter or LinkedIn. Messaging someone."
        ),
        "entertainment": (
            "Watching YouTube videos, Netflix, Twitch streams for fun. "
            "Playing video games on Steam, Epic. "
            "Browsing Reddit, Instagram, TikTok. Listening to Spotify. Reading manga."
        ),
        "designing": (
            "Creating UI mockups or wireframes in Figma, Sketch, or Adobe XD. "
            "Editing photos in Photoshop or Affinity Photo. Creating vector art in Illustrator. "
            "Browsing Dribbble or Behance for design inspiration. "
            "Working on a design system, logo, brand identity, or color palette."
        ),
        "browsing": (
            "Searching Google or Bing without a specific goal. "
            "Casually reading news articles, tech blogs, Hacker News. "
            "Clicking between tabs without a clear task. General web surfing."
        ),
        "meetings": (
            "Attending a Zoom or Google Meet video call. "
            "In a Microsoft Teams meeting or Webex conference. "
            "Looking at a calendar, scheduling a meeting, checking a calendar invite."
        ),
        "planning": (
            "Organising tasks on a Trello board or in Notion. "
            "Managing a project in Jira, Linear, Asana, or ClickUp. "
            "Writing a roadmap, sprint plan, or OKRs. "
            "Using Obsidian or Logseq to structure ideas and notes."
        ),
        "reading": (
            "Reading a book on Kindle or in a PDF viewer. "
            "Going through a long article in Pocket or Instapaper. "
            "Reading an e-book, EPUB, or Readwise highlight. Focused long-form reading."
        ),
    }

    # ── TF-IDF corpus (one doc per category, same order as CATEGORIES) ────────
    _TFIDF_CORPUS = [
        # coding
        (
            "coding programming development software code terminal git python javascript typescript "
            "debugging vscode ide compiler github gitlab stackoverflow developer api function class "
            "variable build deploy commit push pull request branch merge docker kubernetes npm pip "
            "localhost server framework react angular flask django rust java ruby csharp sql "
            "database query regex lint test unittest integration devops cicd aws azure cloud replit "
            "embedding model llm bert transformer minilm fastembed huggingface onnx pytorch inference "
            "fine-tuning tokenizer neural network machine learning pipeline"
        ),
        # learning
        (
            "learning education course tutorial reading study university lecture academic research book "
            "pdf documentation knowledge wikipedia howto guide lesson quiz exam training bootcamp workshop "
            "certificate skill improvement dictionary definition meaning thesaurus vocabulary encyclopedia "
            "reference manual textbook syllabus mooc seminar webinar udemy coursera edx khanacademy "
            "claude chatgpt perplexity ai assistant question answer how to guide tips comparison"
        ),
        # writing
        (
            "writing document essay blog article word processing notes markdown text editor draft compose "
            "report presentation letter newsletter journal diary notion overleaf latex grammarly prose "
            "paragraph sentence chapter outline revision proofreading editing manuscript google docs"
        ),
        # communication
        (
            "communication email chat message slack discord teams meeting zoom conference call video audio "
            "inbox notification reply thread conversation group skype whatsapp telegram microsoft outlook "
            "calendar invite rsvp standup sync linkedin direct message dm twitter tweet"
        ),
        # entertainment
        (
            "entertainment video music game games gaming youtube netflix streaming movie show spotify "
            "playlist twitch reddit manga anime novel comic relax break fun meme shorts watch play "
            "download torrent crack repack pirate facebook instagram tiktok social media steam epic "
            "origin itch playstation xbox nintendo chess soundcloud"
        ),
        # designing
        (
            "design figma sketch photoshop illustrator xd wireframe prototype mockup ui ux "
            "graphic logo brand identity icon typography color palette font visual design "
            "dribbble behance canva affinity blender framer zeplin color scheme style guide "
            "vector animation motion graphic illustration layout grid component"
        ),
        # browsing
        (
            "browsing search google bing duckduckgo news feed hacker news techcrunch wired theverge "
            "casual surfing reading news articles clicking links general browsing open tabs "
            "new tab homepage start page search results breaking news tech news media"
        ),
        # meetings
        (
            "meeting zoom google meet teams webex video call conference standup daily weekly sync "
            "one on one calendar schedule invite rsvp attendee agenda minutes notes loom whereby "
            "screenshare presentation call audio mute unmute join room webinar"
        ),
        # planning
        (
            "planning task project kanban sprint backlog roadmap milestone trello notion asana jira "
            "linear clickup basecamp monday airtable miro mural okr goal quarterly plan gantt "
            "obsidian logseq to-do todo checklist priority deadline workflow management"
        ),
        # reading
        (
            "reading ebook epub pdf kindle book chapter page scroll article instapaper pocket "
            "readwise scribd long-form reading highlights annotations bookmark literature fiction "
            "nonfiction biography memoir novel textbook academic paper journal"
        ),
    ]

    # ── Confidence thresholds ─────────────────────────────────────────────────
    _BGE_THRESHOLD   = 0.15
    _TFIDF_THRESHOLD = 0.12
    _ENSEMBLE_BOOST  = 0.03   # bonus when both models agree on same category

    def __init__(self, user_id: str = "default", data_dir: str = "classifier_data"):
        self._user_id  = user_id
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._model_cache_dir = self._data_dir / "model_cache"
        self._model_cache_dir.mkdir(parents=True, exist_ok=True)

        self._lru   = _LRUCache(maxsize=4096)
        self._overrides: dict[str, str] = {}   # cache_key -> category

        # AI models (lazy-loaded)
        self._st_model          = None
        self._cat_embeddings    = None
        self._tfidf_vectorizer  = None
        self._tfidf_cat_vectors = None
        self._model_loaded      = False

        self._load_overrides()
        self._load_model()

    # ── Personalisation: overrides ────────────────────────────────────────────

    @property
    def _override_path(self) -> Path:
        return self._data_dir / f"overrides_{self._user_id}.json"

    def _load_overrides(self) -> None:
        if self._override_path.exists():
            try:
                self._overrides = json.loads(self._override_path.read_text())
                print(f"[Personalise] Loaded {len(self._overrides)} overrides for user '{self._user_id}'")
            except Exception as e:
                print(f"[Personalise] Could not load overrides: {e}")

    def _save_overrides(self) -> None:
        try:
            self._override_path.write_text(json.dumps(self._overrides, indent=2))
        except Exception as e:
            print(f"[Personalise] Could not save overrides: {e}")

    def teach(self, app: str, title: str, domain: str, correct_category: str) -> None:
        """
        Let the user correct a misclassification.
        """
        if correct_category not in self.CATEGORIES and correct_category != "unknown":
            raise ValueError(f"Unknown category '{correct_category}'. Choose from: {self.CATEGORIES}")
        key = self._cache_key(app, title, domain)
        self._overrides[key] = correct_category
        self._lru.invalidate(key)         # bust LRU so next call uses override
        self._save_overrides()
        print(f"[Personalise] Taught: '{title[:60]}' -> {correct_category}")

    def forget(self, app: str, title: str, domain: str) -> None:
        """Remove a stored user override."""
        key = self._cache_key(app, title, domain)
        self._overrides.pop(key, None)
        self._lru.invalidate(key)
        self._save_overrides()

    # ── Model loading ─────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        set_model_status("loading")
        try:
            import platform
            if platform.system() == "Windows":
                import sys

                # When running as a PyInstaller EXE, DLLs are unpacked to
                # sys._MEIPASS — add that location first so onnxruntime finds
                # its native DLLs before falling back to site-packages.
                candidate_roots = []
                if hasattr(sys, "_MEIPASS"):
                    candidate_roots.append(sys._MEIPASS)

                import site
                try:
                    candidate_roots.extend(site.getsitepackages())
                except AttributeError:
                    pass
                if hasattr(site, "getusersitepackages"):
                    try:
                        candidate_roots.append(site.getusersitepackages())
                    except Exception:
                        pass

                for root in candidate_roots:
                    onnx_path = os.path.join(root, "onnxruntime", "capi")
                    if os.path.exists(onnx_path):
                        os.add_dll_directory(onnx_path)

            from fastembed import TextEmbedding
            import numpy as np

            self._st_model = TextEmbedding(
                model_name="BAAI/bge-small-en-v1.5",
                cache_dir=str(self._model_cache_dir),
            )
            # Pre-compute category embeddings (batch once at startup)
            cat_texts = [self.CATEGORY_DESCRIPTIONS[c] for c in self.CATEGORIES]
            self._cat_embeddings = np.array(list(self._st_model.embed(cat_texts)))
            print(f"✅ [Classifier] FastEmbed loaded. {len(self.CATEGORIES)} categories embedded.")
            ai_debug_log("MODEL", "FastEmbed loaded (BAAI/bge-small-en-v1.5).")
            set_model_status("fastembed_ready")
            self._model_loaded = True
            return
        except Exception as e:
            print(f"⚠️ [Classifier] FastEmbed unavailable ({e}). Trying TF-IDF…")
            ai_debug_log("MODEL", f"FastEmbed unavailable: {e}")


        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._tfidf_vectorizer  = TfidfVectorizer(sublinear_tf=True, stop_words="english")
            self._tfidf_cat_vectors = self._tfidf_vectorizer.fit_transform(self._TFIDF_CORPUS)
            print("[Classifier] TF-IDF fallback loaded.")
            ai_debug_log("MODEL", "TF-IDF fallback loaded.")
            set_model_status("tfidf_fallback")
            self._model_loaded = True
        except ImportError:
            print("[Classifier] No ML model available — rule-based only.")
            ai_debug_log("MODEL", "No ML model available. Rule-only mode.")
            set_model_status("rule_only")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(app: str, title: str, domain: str) -> str:
        return f"{app.lower()}|{domain.lower()}|{title.lower()}"

    def _clean_title(self, title: str) -> str:
        cleaned = self._BROWSER_SUFFIX_RE.sub("", title).strip()
        return cleaned if cleaned else title

    @staticmethod
    def _domain_to_words(domain: str) -> str:
        if not domain:
            return ""
        base = re.sub(r"^www\.", "", domain)
        base = re.sub(r"\.[a-z]{2,}$", "", base)
        base = re.sub(r"([a-z])([A-Z])", r"\1 \2", base)
        base = re.sub(r"[-_.]", " ", base)
        return base.lower().strip()

    # ── URL-path-aware classification ─────────────────────────────────────────

    @staticmethod
    def _classify_by_url_path(domain: str, url_path: str) -> Optional[str]:
        if not url_path:
            return None

        d = domain.lower()
        p = url_path.lower()

        # GitHub
        if d == "github.com":
            if any(seg in p for seg in ["/pull/", "/issues/", "/commits/", "/actions/", "/compare/"]):
                return "coding"
            if "/trending" in p or "/explore" in p:
                return "browsing"

        # Google
        if d in {"google.com", "www.google.com"}:
            if p.startswith("/search"):
                return "browsing"
            if p.startswith("/docs") or p.startswith("/spreadsheets"):
                return "writing"
            if p.startswith("/calendar"):
                return "meetings"
            if p.startswith("/meet"):
                return "meetings"

        # YouTube
        if d in {"youtube.com", "www.youtube.com"}:
            if p.startswith("/watch"):
                return None   # needs title to decide learning vs entertainment
            if p in {"/", "/feed/subscriptions", "/feed/trending"}:
                return "browsing"

        # Notion
        if d == "notion.so":
            return "planning"     # most notion usage = planning; override if needed

        # Slack
        if d == "slack.com" or d == "app.slack.com":
            if "/calls/" in p or "/huddle" in p:
                return "meetings"
            return "communication"

        return None

    # ── YouTube intent ────────────────────────────────────────────────────────

    def _youtube_category(self, title_l: str) -> str:
        learn_score = sum(1 for kw in self._YT_LEARNING_KEYWORDS if kw in title_l)
        ent_score   = sum(1 for kw in self._YT_ENTERTAINMENT_KEYWORDS if kw in title_l)
        if learn_score > ent_score:
            return "learning"
        return "entertainment"

    # ── Rule-based classification ─────────────────────────────────────────────

    def _rule_classify(
        self, app: str, title: str, domain: str, url_path: str = ""
    ) -> Optional[str]:
        app_l    = app.lower().strip()
        title_l  = title.lower()
        domain_l = domain.lower()

        browser_exes = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"}

        # Generic browser tab
        if app_l in browser_exes and not domain_l:
            if any(p in title_l for p in self._GENERIC_TITLES):
                return "unknown"

        # Own app -> coding
        if any(name in app_l for name in self.OWN_APP_NAMES):
            return "coding"

        # URL-path rules (highest precision)
        url_cat = self._classify_by_url_path(domain_l, url_path)
        if url_cat:
            return url_cat

        # ── App-level rules ──────────────────────────────────────────────────
        if app_l in self.DESIGNING_APPS:    return "designing"
        if app_l in self.CODING_APPS:       return "coding"
        if app_l in self.READING_APPS:      return "reading"
        if app_l in self.LEARNING_APPS:     return "learning"
        if app_l in self.PLANNING_APPS:     return "planning"
        if app_l in self.WRITING_APPS:      return "writing"

        # Meetings app: only if title suggests active call
        if app_l in self.MEETINGS_APPS:
            if any(kw in title_l for kw in self.MEETINGS_TITLE_KEYWORDS):
                return "meetings"
            return "communication"

        if app_l in self.COMMUNICATION_APPS:  return "communication"
        if app_l in self.ENTERTAINMENT_APPS:  return "entertainment"

        # ── Domain-level rules ────────────────────────────────────────────────
        if any(d in domain_l for d in self.CODING_DOMAINS):      return "coding"
        if any(d in domain_l for d in self.DESIGNING_DOMAINS):   return "designing"
        if any(d in domain_l for d in self.MEETINGS_DOMAINS):    return "meetings"
        if any(d in domain_l for d in self.PLANNING_DOMAINS):    return "planning"
        if any(d in domain_l for d in self.READING_DOMAINS):     return "reading"
        if any(d in domain_l for d in self.COMMUNICATION_DOMAINS): return "communication"
        if any(d in domain_l for d in self.WRITING_DOMAINS):     return "writing"
        if any(d in domain_l for d in self.LEARNING_DOMAINS):    return "learning"

        if "youtube.com" in domain_l:
            return self._youtube_category(title_l)

        if any(d in domain_l for d in self.BROWSING_DOMAINS):    return "browsing"
        if any(d in domain_l for d in self.ENTERTAINMENT_DOMAINS): return "entertainment"

        # ── Title keyword rules ───────────────────────────────────────────────
        if any(kw in title_l for kw in self.CODING_TITLE_KEYWORDS):      return "coding"
        if any(kw in title_l for kw in self.DESIGNING_TITLE_KEYWORDS):   return "designing"
        if any(kw in title_l for kw in self.MEETINGS_TITLE_KEYWORDS):    return "meetings"
        if any(kw in title_l for kw in self.PLANNING_TITLE_KEYWORDS):    return "planning"
        if any(kw in title_l for kw in self.READING_TITLE_KEYWORDS):     return "reading"
        if any(kw in title_l for kw in self.COMMUNICATION_TITLE_KEYWORDS): return "communication"
        if any(kw in title_l for kw in self.WRITING_TITLE_KEYWORDS):     return "writing"
        if any(kw in title_l for kw in self.LEARNING_TITLE_KEYWORDS):    return "learning"
        if any(kw in title_l for kw in self.BROWSING_TITLE_KEYWORDS):    return "browsing"
        if any(kw in title_l for kw in self.ENTERTAINMENT_TITLE_KEYWORDS): return "entertainment"

        # Final safety fallback: browser usage with no strong signal should still be browsing, not unknown.
        if app_l in browser_exes:
            return "browsing"

        return None

    # ── BGE score vector ──────────────────────────────────────────────────────

    def _bge_scores(self, text: str):
        if self._st_model is None:
            return None
        try:
            import numpy as np
            q_emb  = list(self._st_model.embed([text]))[0]
            scores = np.dot(self._cat_embeddings, q_emb)
            return scores
        except Exception as e:
            print(f"[BGE] Error: {e}")
            return None

    def _tfidf_scores(self, text: str):
        if self._tfidf_vectorizer is None:
            return None
        try:
            qv     = self._tfidf_vectorizer.transform([text])
            scores = (qv * self._tfidf_cat_vectors.T).toarray()[0]
            return scores
        except Exception as e:
            print(f"[TF-IDF] Error: {e}")
            return None

    # ── AI classification with ensemble ──────────────────────────────────────

    def _ai_classify(self, text: str) -> str:
        bge_scores   = self._bge_scores(text)
        tfidf_scores = self._tfidf_scores(text)

        combined = None

        if bge_scores is not None:
            combined = bge_scores.copy()

        if tfidf_scores is not None:
            mx = tfidf_scores.max()
            tfidf_norm = tfidf_scores / mx if mx > 0 else tfidf_scores

            if combined is None:
                combined = tfidf_norm
            else:
                combined = 0.7 * combined + 0.3 * tfidf_norm
                if int(bge_scores.argmax()) == int(tfidf_scores.argmax()):
                    combined[int(bge_scores.argmax())] += self._ENSEMBLE_BOOST

        if combined is None:
            return "unknown"

        best_idx   = int(combined.argmax())
        best_score = float(combined[best_idx])
        score_str  = ", ".join(f"{c}={s:.3f}" for c, s in zip(self.CATEGORIES, combined))

        threshold = self._BGE_THRESHOLD if bge_scores is not None else self._TFIDF_THRESHOLD

        if best_score < threshold:
            print(f"🤖 [AI] LOW CONFIDENCE ({best_score:.3f}) -> 'unknown'")
            print(f"   Scores: [{score_str}]")
            ai_debug_log("AI", f"LOW_CONF -> unknown ({best_score:.3f})")
            return "unknown"

        result = self.CATEGORIES[best_idx]
        print(f"🧠 [AI] '{result.upper()}' (score={best_score:.3f})")
        print(f"   Scores: [{score_str}]")
        print(f"   Input:  '{text[:120]}'")
        ai_debug_log("AI", f"{result} (score={best_score:.3f})")
        return result

    # ── Public API ────────────────────────────────────────────────────────────

    def classify(self, app: str, title: str, domain: str, url_path: str = "") -> str:
        """Entry point aligned with the tracking loop."""
        key = self._cache_key(app, title, domain)

        cached = self._lru.get(key)
        if cached is not None:
            return cached

        if key in self._overrides:
            cat = self._overrides[key]
            print(f"👤 [OVERRIDE] '{title[:60]}' -> {cat.upper()}")
            ai_debug_log("OVERRIDE", f"{app} | {domain} -> {cat}")
            self._lru.set(key, cat)
            return cat

        cat = self._rule_classify(app, title, domain, url_path)

        if cat:
            print(f"📜 [RULE] '{app} | {domain}' -> {cat.upper()}")
            ai_debug_log("RULE", f"{app} | {domain} -> {cat}")
        else:
            clean_title  = self._clean_title(title)
            domain_words = self._domain_to_words(domain)
            parts        = [p for p in [clean_title, domain_words, app] if p]
            ai_input     = " | ".join(parts)

            print(f"🔍 [NO RULE] Cleaned: '{clean_title[:80]}' | AI input: '{ai_input[:120]}'")
            ai_debug_log("AI", f"NO_RULE -> {app} | {domain} | {clean_title[:60]}")
            cat = self._ai_classify(ai_input)

        self._lru.set(key, cat)
        return cat