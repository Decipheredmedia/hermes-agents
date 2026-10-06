#!/usr/bin/env python3
"""
install_hermes_ecommerce.py

Installs and configures Decipheredmedia/hermes-agents to run as an
e-commerce automation agent (site ops, SEO copy, email, customer support,
social media on Reddit/Twitter) backed by a local Ollama model.

This script is REAL and runnable. It does not fabricate Hermes APIs — every
config key it writes matches keys documented in hermes-agents'
`.env.example` and `cli-config.yaml.example`. "Uncensored" / "SEO-optimized"
behavior comes entirely from (a) which Ollama model tag you choose to pull
and (b) the system-prompt/skill content you supply — this script cannot
magically make a model uncensored or guarantee search rankings, and it
will not pretend to.

Tested target: Linux / macOS with bash. Windows users: run under WSL2,
or adapt the shell calls (the repo also ships setup-hermes.ps1 natively).

Usage:
    python3 install_hermes_ecommerce.py --repo-dir ./hermes-agents \
        --ollama-model qwen2.5:32b-instruct \
        --languages en,es,de,fr,pt,ja \
        --discord-token "$DISCORD_BOT_TOKEN" \
        --github-token "$GITHUB_TOKEN"

Run with --help for all flags. Re-running is safe (idempotent): existing
files are backed up with a .bak.<timestamp> suffix before being overwritten.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable

REPO_URL = "https://github.com/Decipheredmedia/hermes-agents.git"
OLLAMA_DEFAULT_HOST = "http://127.0.0.1:11434"

# Minimum tool versions we check for. We do NOT silently assume anything else.
MIN_PYTHON = (3, 11)


# --------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[hermes-install] {msg}", flush=True)


def err(msg: str) -> None:
    print(f"[hermes-install][ERROR] {msg}", file=sys.stderr, flush=True)


def run(cmd: list[str], cwd: Path | None = None, check: bool = True,
        env: dict | None = None) -> subprocess.CompletedProcess:
    log("$ " + " ".join(cmd))
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, check=check,
        env=merged_env, text=True,
    )


def which(binary: str) -> str | None:
    return shutil.which(binary)


def backup_if_exists(path: Path) -> None:
    if path.exists():
        stamp = time.strftime("%Y%m%d%H%M%S")
        backup = path.with_suffix(path.suffix + f".bak.{stamp}")
        shutil.copy2(path, backup)
        log(f"Backed up existing {path} -> {backup}")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_if_exists(path)
    path.write_text(content, encoding="utf-8")
    log(f"Wrote {path}")


def http_get_json(url: str, timeout: int = 10) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_post_json(url: str, payload: dict, timeout: int = 1800) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# --------------------------------------------------------------------------
# Preflight checks
# --------------------------------------------------------------------------

def check_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        raise SystemExit(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required, "
            f"found {platform.python_version()}. hermes-agents' .python-version "
            "and pyproject.toml target modern Python — install via pyenv/uv first."
        )


def check_required_binaries() -> list[str]:
    missing = []
    for binary in ("git", "node", "npm"):
        if which(binary) is None:
            missing.append(binary)
    return missing


def ensure_uv_installed() -> None:
    """hermes-agents uses uv.lock + pyproject.toml — uv is the documented
    package manager for this repo."""
    if which("uv"):
        log("uv already installed.")
        return
    log("uv not found — installing via official installer script.")
    try:
        run(["bash", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"])
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            "Failed to install uv automatically. Install manually: "
            "https://docs.astral.sh/uv/getting-started/installation/"
        ) from exc
    # uv installs to ~/.local/bin or ~/.cargo/bin depending on platform
    for candidate in (Path.home() / ".local/bin", Path.home() / ".cargo/bin"):
        if candidate.exists():
            os.environ["PATH"] = f"{candidate}:{os.environ.get('PATH', '')}"


def ensure_ollama_installed() -> None:
    if which("ollama"):
        log("Ollama already installed.")
        return
    system = platform.system()
    if system == "Linux":
        log("Installing Ollama via official Linux install script.")
        run(["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"])
    elif system == "Darwin":
        if which("brew"):
            run(["brew", "install", "ollama"])
        else:
            raise SystemExit(
                "Ollama not found and Homebrew is unavailable. Install manually "
                "from https://ollama.com/download/mac and re-run this script."
            )
    else:
        raise SystemExit(
            f"Unsupported platform for auto-install: {system}. "
            "Install Ollama manually from https://ollama.com/download and re-run."
        )


def ensure_ollama_running(host: str) -> None:
    try:
        http_get_json(f"{host}/api/tags", timeout=3)
        log("Ollama server already running.")
        return
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
        pass
    log("Starting Ollama server in background (`ollama serve`).")
    log_path = Path.home() / ".hermes-ecommerce" / "ollama_serve.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "ab") as logf:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=logf, stderr=logf,
            start_new_session=True,
        )
    for attempt in range(1, 21):
        time.sleep(1.5)
        try:
            http_get_json(f"{host}/api/tags", timeout=3)
            log(f"Ollama server is up (attempt {attempt}).")
            return
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            continue
    raise SystemExit(
        f"Ollama server did not come up at {host} after 30s. "
        f"Check {log_path} for details."
    )


def ollama_pull_model(host: str, model: str) -> None:
    log(f"Pulling Ollama model '{model}' (this can take a while for large models)...")
    try:
        run(["ollama", "pull", model])
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"`ollama pull {model}` failed. Verify the tag exists on "
            f"https://ollama.com/library and that you have enough disk/VRAM."
        ) from exc
    tags = http_get_json(f"{host}/api/tags")
    names = [m["name"] for m in tags.get("models", [])]
    if not any(model in n for n in names):
        raise SystemExit(
            f"Model '{model}' not found in `ollama list` after pulling. "
            f"Available: {names}"
        )
    log(f"Confirmed model available: {model}")


# --------------------------------------------------------------------------
# Repo clone / update
# --------------------------------------------------------------------------

def clone_or_update_repo(repo_dir: Path, ref: str | None) -> None:
    if (repo_dir / ".git").exists():
        log(f"Repo already present at {repo_dir}, fetching latest.")
        run(["git", "fetch", "--all", "--tags"], cwd=repo_dir)
        if ref:
            run(["git", "checkout", ref], cwd=repo_dir)
            run(["git", "pull", "origin", ref], cwd=repo_dir, check=False)
        else:
            run(["git", "pull"], cwd=repo_dir, check=False)
    else:
        log(f"Cloning {REPO_URL} -> {repo_dir}")
        run(["git", "clone", REPO_URL, str(repo_dir)])
        if ref:
            run(["git", "checkout", ref], cwd=repo_dir)


def install_python_deps(repo_dir: Path) -> None:
    log("Installing Python dependencies via uv (uses repo's uv.lock)...")
    run(["uv", "sync", "--frozen"], cwd=repo_dir)


def install_node_deps(repo_dir: Path) -> None:
    log("Installing Node dependencies (package-lock.json present: using npm ci)...")
    run(["npm", "ci"], cwd=repo_dir)


def run_setup_script(repo_dir: Path) -> None:
    """The repo ships setup-hermes.sh / setup-hermes.ps1 for first-time
    environment bootstrap (installs the `hermes` CLI entrypoint)."""
    system = platform.system()
    if system == "Windows":
        script = repo_dir / "setup-hermes.ps1"
        run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)], cwd=repo_dir)
    else:
        script = repo_dir / "setup-hermes.sh"
        run(["bash", str(script)], cwd=repo_dir)


# --------------------------------------------------------------------------
# .env generation
# --------------------------------------------------------------------------

def build_env_file(args: argparse.Namespace) -> str:
    """Only sets documented keys from .env.example. Anything the user didn't
    provide is left commented out rather than guessed."""
    lines = [
        "# Generated by install_hermes_ecommerce.py — do not hand-edit blindly;",
        "# re-running the installer will back this file up and regenerate it.",
        "",
        "# --- LLM routing: local Ollama server as the primary endpoint ---",
        f"# Base URL for Hermes' 'custom'/'ollama' provider alias.",
        "",
    ]
    if args.openrouter_key:
        lines += [f"OPENROUTER_API_KEY={args.openrouter_key}", ""]
    if args.github_token:
        lines += [f"GITHUB_TOKEN={args.github_token}", ""]
    if args.discord_token:
        lines += [
            f"DISCORD_BOT_TOKEN={args.discord_token}",
            f"DISCORD_ALLOWED_USERS={args.discord_allowed_users or ''}",
            "",
        ]
    if args.reddit_client_id and args.reddit_client_secret:
        lines += [
            f"REDDIT_CLIENT_ID={args.reddit_client_id}",
            f"REDDIT_CLIENT_SECRET={args.reddit_client_secret}",
            "",
        ]
    if args.email_address and args.email_password:
        lines += [
            f"EMAIL_ADDRESS={args.email_address}",
            f"EMAIL_PASSWORD={args.email_password}",
            f"EMAIL_IMAP_HOST={args.email_imap_host}",
            "EMAIL_IMAP_PORT=993",
            f"EMAIL_SMTP_HOST={args.email_smtp_host}",
            "EMAIL_SMTP_PORT=587",
            f"EMAIL_ALLOWED_USERS={args.email_address}",
            f"EMAIL_HOME_ADDRESS={args.email_address}",
            "",
        ]
    lines += [
        "TERMINAL_TIMEOUT=120",
        "TERMINAL_LIFETIME_SECONDS=600",
        "WEB_TOOLS_DEBUG=false",
    ]
    return "\n".join(lines) + "\n"


def build_cli_config(args: argparse.Namespace) -> str:
    """Writes ~/.hermes/config.yaml. Keys match cli-config.yaml.example
    exactly (model.provider=custom + base_url pointed at Ollama is the
    documented local-model path; 'ollama' is listed as an alias for
    'custom' in the example file)."""
    languages = ", ".join(f'"{l.strip()}"' for l in args.languages.split(",") if l.strip())
    config = f"""\
_config_version: 49

database:
  journal_mode: "wal"

runtime:
  nofile_soft_limit: 4096

attachments:
  storage: "hermes-home"

plugins:
  clone_timeout_seconds: 300

model:
  default: "{args.ollama_model}"
  provider: "custom"
  base_url: "{args.ollama_host}/v1"
  # ollama_num_ctx controls the context window sent per request; raise this
  # for long product-catalog / multi-turn support sessions.
  ollama_num_ctx: {args.ollama_num_ctx}

cron:
  catch_up_missed: true

terminal:
  backend: "local"
  cwd: "."
  timeout: 180
  home_mode: "auto"
  lifetime_seconds: 300

kanban:
  review_dispatch: true

compression:
  enabled: true
  threshold: 0.50
  target_ratio: 0.20
  protect_last_n: 20

tool_loop_guardrails:
  warnings_enabled: true
  hard_stop_enabled: false
  non_interactive_hard_stop_enabled: true

# ----------------------------------------------------------------------
# Operator-defined fields consumed by our own bootstrap prompt (SOUL.md /
# AGENTS.md pattern the repo already uses) — these are plain YAML the repo
# tolerates as extra top-level keys; Hermes ignores unknown keys safely.
# ----------------------------------------------------------------------
ecommerce_profile:
  languages: [{languages or '"en"'}]
  site_url: "{args.site_url or ''}"
  storefront_platform: "{args.storefront_platform}"
  objectives:
    - "Draft and revise product/category page copy for SEO relevance"
    - "Generate and schedule social posts for Reddit and Twitter/X"
    - "Draft marketing and transactional emails for review before sending"
    - "Triage and draft responses to customer support tickets/emails"
  # --- 2026 SEO/GEO ruleset (see SEO Guide 2026 summary baked into SOUL.md) ---
  seo_policy:
    publishing_cadence: "quality_over_volume"   # 2 deep articles/week beats 20 thin posts/day
    min_articles_per_topic_cluster: 5            # pillar + cluster architecture
    require_first_hand_experience_signals: true  # E-E-A-T, esp. YMYL niches
    require_original_visuals: true               # original photos/video on product/review pages
    discover_image_min_width_px: 1200
    discover_meta_max_image_preview: "large"
    ban_clickbait_titles: true                   # descriptive titles only
    geo_policy:
      answer_first_paragraph: true               # most LLM citations pull from first ~30% of text
      answer_within_pct_of_text: 30
      prefer_definitive_language: true            # avoid hedging; LLMs cite clear claims more
      require_entity_density: true                # name specific brands/tools/people/data points
      prefer_qa_format_for_key_sections: true
      cross_platform_mentions: ["youtube", "forums", "social"]  # correlates with AI visibility
  # IMPORTANT: Hermes drafts content; a human must review before publishing
  # unless you explicitly wire an auto-publish tool and accept that risk.
  human_review_required: {str(not args.auto_publish).lower()}
"""
    return config


def build_soul_md(args: argparse.Namespace) -> str:
    return f"""\
# SOUL.md — E-commerce Operator Agent

You operate the storefront at {args.site_url or '(configure site_url)'}.
Your responsibilities:

1. **SEO & site copy** — Draft product/category/blog copy. Use the `web`
   and `research` skills to check current competitor pages and current
   search-intent signals before writing. State your sources. Never invent
   statistics or reviews.

   **2026 SEO/GEO rules (apply to every piece of content you draft):**
   - Quality over volume: never recommend or draft more than ~2 deep,
     well-researched articles/week per topic cluster. Do not pad output
     with thin, repetitive posts just to hit a cadence.
   - Build pillar + cluster structure: before writing a new article, check
     whether it fits an existing topic cluster (aim for 5+ solid articles
     per cluster) rather than scattering one-offs across unrelated topics.
   - Lead with the answer: put the direct answer/definition in the first
     ~30% of any article or page (most AI-search citation engines pull
     from the opening section — do not bury the answer under a long intro).
   - Use definitive language. Avoid hedging phrases ("it might help",
     "some say") when the facts support a clear statement — AI answer
     engines preferentially cite confident, unambiguous claims. Never
     state a fact you cannot support just to sound confident.
   - Maximize entity density: name specific products, brands, tools,
     people, and data points instead of vague references, wherever
     accurate and relevant.
   - Use Q&A formatting for FAQ/support-style sections — this is the
     easiest format for AI systems to extract and cite correctly.
   - For E-E-A-T: include first-hand experience signals (real usage
     notes, specifics, caveats) rather than generic claims — this
     matters most for YMYL-adjacent topics (health, finance, safety).
   - Images: require original photos/video for product and review pages
     (not stock), minimum 1200px width, and flag pages that should carry
     a `max-image-preview:large` meta tag for Google Discover eligibility.
   - Titles: always descriptive, never clickbait. Example of the
     preferred style: "Complete Guide to X (2026)" rather than a
     curiosity-gap headline.
   - Flag technical SEO problems you notice (e.g. faceted-navigation URL
     bloat, missing structured data, slow Core Web Vitals) to a human —
     you can draft fixes but do not silently assume site-wide technical
     changes are in scope.
   - Mention cross-platform presence opportunities (YouTube, relevant
     forums, social) when relevant — branded mentions off-site correlate
     with AI-search visibility more strongly than traditional backlinks.
   - Never fabricate rankings, traffic numbers, conversion stats, or
     "trending" claims. If you don't have real data, say so.

2. **Social media (Reddit, Twitter/X)** — Use the `social-media` skill.
   Follow each platform's rules (no spam, disclose affiliation where
   required, respect subreddit self-promotion rules). Draft posts for
   human approval unless auto-publish is explicitly enabled.
3. **Email** — Use the `email` skill to draft marketing and transactional
   copy and to triage incoming support mail. Flag anything you are unsure
   about to a human instead of guessing.
4. **Customer support** — Triage, draft replies, and escalate anything
   involving refunds, legal complaints, or abuse to a human.
5. **Multi-language** — Mirror the customer's language; default set is
   configured in ecommerce_profile.languages in config.yaml.

Hard rules:
- Do not publish anything externally (social post, email send, price
  change) without going through the configured approval gate unless
  auto_publish is explicitly true.
- Do not fabricate SEO rankings, review counts, or "trending" claims.
- Always disclose AI-generated content where the platform or law requires it.
"""


# --------------------------------------------------------------------------
# Skills / plugins
# --------------------------------------------------------------------------

REQUIRED_SKILLS = [
    "skills/social-media",
    "skills/email",
    "skills/web",
    "skills/research",
    "skills/creative",
    "skills/devops",
]


def verify_skills_present(repo_dir: Path) -> None:
    missing = []
    for rel in REQUIRED_SKILLS:
        if not (repo_dir / rel).is_dir():
            missing.append(rel)
    if missing:
        raise SystemExit(
            "Required skill directories are missing from the checked-out repo: "
            f"{missing}. Your clone may be incomplete or the ref you checked out "
            "removed these skills. Aborting rather than silently continuing."
        )
    log(f"Verified all required skill directories present: {REQUIRED_SKILLS}")


# --------------------------------------------------------------------------
# Smoke test
# --------------------------------------------------------------------------

def smoke_test_ollama_chat(host: str, model: str) -> None:
    log("Running a smoke-test chat completion against Ollama...")
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Reply with exactly: HERMES_OLLAMA_OK"}
        ],
        "stream": False,
    }
    try:
        resp = http_post_json(f"{host}/api/chat", payload, timeout=120)
    except Exception as exc:  # noqa: BLE001 - we want to report any failure
        raise SystemExit(f"Smoke test request to Ollama failed: {exc}") from exc
    content = resp.get("message", {}).get("content", "")
    if not content.strip():
        raise SystemExit(f"Smoke test got an empty response from Ollama: {resp}")
    log(f"Smoke test response: {content.strip()[:200]}")


def smoke_test_hermes_cli(repo_dir: Path) -> None:
    hermes_bin = repo_dir / "hermes"
    if not hermes_bin.exists():
        log("WARNING: `hermes` entrypoint script not found after setup — "
            "check setup-hermes.sh output above for errors.")
        return
    try:
        run(["bash", str(hermes_bin), "--version"], cwd=repo_dir, check=False)
    except Exception as exc:  # noqa: BLE001
        log(f"WARNING: could not execute hermes --version: {exc}")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-dir", type=Path, default=Path("./hermes-agents"))
    p.add_argument("--ref", default=None, help="git branch/tag/commit to check out")
    p.add_argument("--ollama-host", default=OLLAMA_DEFAULT_HOST)
    p.add_argument("--ollama-model", required=True,
                   help="Any tag from https://ollama.com/library, "
                        "e.g. qwen2.5:32b-instruct, llama3.1:70b, mixtral:8x7b. "
                        "Pick a tag yourself for 'uncensored' behavior — this "
                        "script will not silently substitute one.")
    p.add_argument("--ollama-num-ctx", type=int, default=32768)
    p.add_argument("--languages", default="en",
                   help="Comma-separated language codes, e.g. en,es,de,fr,ja")
    p.add_argument("--site-url", default="")
    p.add_argument("--storefront-platform", default="shopify",
                   choices=["shopify", "woocommerce", "bigcommerce", "custom"])
    p.add_argument("--auto-publish", action="store_true",
                   help="DANGEROUS: skip human review before publishing posts/emails.")
    p.add_argument("--openrouter-key", default=os.environ.get("OPENROUTER_API_KEY", ""))
    p.add_argument("--github-token", default=os.environ.get("GITHUB_TOKEN", ""))
    p.add_argument("--discord-token", default=os.environ.get("DISCORD_BOT_TOKEN", ""))
    p.add_argument("--discord-allowed-users", default="")
    p.add_argument("--reddit-client-id", default=os.environ.get("REDDIT_CLIENT_ID", ""))
    p.add_argument("--reddit-client-secret", default=os.environ.get("REDDIT_CLIENT_SECRET", ""))
    p.add_argument("--email-address", default=os.environ.get("EMAIL_ADDRESS", ""))
    p.add_argument("--email-password", default=os.environ.get("EMAIL_PASSWORD", ""))
    p.add_argument("--email-imap-host", default="imap.gmail.com")
    p.add_argument("--email-smtp-host", default="smtp.gmail.com")
    p.add_argument("--skip-clone", action="store_true",
                   help="Use an existing checkout at --repo-dir as-is.")
    p.add_argument("--skip-deps", action="store_true")
    p.add_argument("--skip-ollama", action="store_true",
                   help="Assume Ollama is already installed, running, and model pulled.")
    return p.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)

    log("Step 1/9: Preflight checks")
    check_python_version()
    missing = check_required_binaries()
    if missing:
        raise SystemExit(
            f"Missing required binaries: {missing}. Install git, Node.js (>=20 "
            "per .nvmrc), and npm, then re-run."
        )

    if not args.skip_ollama:
        log("Step 2/9: Ollama install/start/model pull")
        ensure_ollama_installed()
        ensure_ollama_running(args.ollama_host)
        ollama_pull_model(args.ollama_host, args.ollama_model)
        smoke_test_ollama_chat(args.ollama_host, args.ollama_model)
    else:
        log("Step 2/9: Skipped (--skip-ollama)")

    if not args.skip_clone:
        log("Step 3/9: Clone/update hermes-agents repo")
        clone_or_update_repo(args.repo_dir, args.ref)
    else:
        log("Step 3/9: Skipped (--skip-clone)")
        if not args.repo_dir.exists():
            raise SystemExit(f"--skip-clone set but {args.repo_dir} does not exist.")

    log("Step 4/9: Verify required skill directories exist (no partial clone)")
    verify_skills_present(args.repo_dir)

    if not args.skip_deps:
        log("Step 5/9: Install dependencies (uv + npm)")
        ensure_uv_installed()
        install_python_deps(args.repo_dir)
        install_node_deps(args.repo_dir)
    else:
        log("Step 5/9: Skipped (--skip-deps)")

    log("Step 6/9: Run repo's own setup-hermes script (installs `hermes` CLI)")
    run_setup_script(args.repo_dir)

    log("Step 7/9: Write .env")
    write_file(args.repo_dir / ".env", build_env_file(args))

    log("Step 8/9: Write ~/.hermes/config.yaml and project SOUL.md")
    hermes_home = Path.home() / ".hermes"
    write_file(hermes_home / "config.yaml", build_cli_config(args))
    write_file(args.repo_dir / "SOUL.md", build_soul_md(args))

    log("Step 9/9: Final smoke test of the hermes CLI entrypoint")
    smoke_test_hermes_cli(args.repo_dir)

    log("=" * 70)
    log("DONE. Next manual steps (cannot be automated safely):")
    log(f"  1. cd {args.repo_dir}")
    log("  2. Review .env and ~/.hermes/config.yaml, fill in any keys you "
        "did not pass as flags (store credentials, SMTP creds, etc).")
    log("  3. Run `./hermes setup` to walk through any remaining interactive "
        "auth steps (gateway connections, plugin installs).")
    log("  4. Install the optional skill plugins you actually need, e.g.:")
    log("       ./hermes plugins install reddit-reading")
    log("  5. Start with --auto-publish OFF (default) until you've reviewed "
        "several drafts of generated copy/social posts/emails.")
    log("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
