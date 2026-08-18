# MediaCrawler Agent Skill

## Purpose

Operate the local MediaCrawler checkout through its supported CLI. This skill is
for controlled, small-scale collection of public information for learning and
research. It does not call external MCP servers, web search, download services,
or remote automation tools.

The helper script is:

```text
.opencode/skills/mediacrawler/mediacrawler_runner.py
```

It uses only Python's standard library and invokes the repository's documented
`uv run main.py` entrypoint.

## Preconditions

1. Work from the MediaCrawler repository, or pass `--project-root` before the
   subcommand. The root must contain `main.py`, `pyproject.toml`, and `config/`.
2. Install project dependencies with `uv sync`.
3. The crawler runs in CDP self-launch mode (`CDP_CONNECT_EXISTING=False`, the
   committed default): it starts its own Chrome, assigns a free port, and keeps
   the login state in a persistent profile directory under `browser_data/`. Do
   NOT rely on attaching to an already-running Chrome on port 9222 — that mode
   is unsupported in this environment.
4. Choose a login method. On first run use QR-code login (a human scans once);
   the saved login state is then reused by later runs, so repeat crawls usually
   need no login at all. Cookie login reads a local cookie file or the
   `MEDIACRAWLER_COOKIES` environment variable.

Run a local preflight check before crawling:

```bash
python .opencode/skills/mediacrawler/mediacrawler_runner.py check
```

## Standard Workflow

### 1. Search by keyword

The runner defaults to conservative limits: 15 notes, one concurrent crawler,
first-level comments disabled, second-level comments disabled, and JSONL output.

```bash
python .opencode/skills/mediacrawler/mediacrawler_runner.py \
  search \
  --platform xhs \
  --login-type qrcode \
  --keywords "人工智能,AI工具" \
  --save-data-option jsonl
```

Enable comments explicitly when needed:

```bash
python .opencode/skills/mediacrawler/mediacrawler_runner.py \
  search \
  --platform xhs \
  --login-type qrcode \
  --keywords "人工智能" \
  --get-comment yes \
  --get-sub-comment yes \
  --max-comments 10
```

### 2. Crawl specified posts or videos

IDs may be comma-separated. Full URLs are accepted where the platform supports
them.

```bash
python .opencode/skills/mediacrawler/mediacrawler_runner.py \
  detail \
  --platform xhs \
  --login-type qrcode \
  --specified-id "https://www.xiaohongshu.com/explore/NOTE_ID" \
  --get-comment yes
```

### 3. Crawl a creator homepage

```bash
python .opencode/skills/mediacrawler/mediacrawler_runner.py \
  creator \
  --platform xhs \
  --login-type qrcode \
  --creator-id "CREATOR_ID"
```

### 4. Use a saved cookie without exposing it in shell history

```bash
python .opencode/skills/mediacrawler/mediacrawler_runner.py \
  search \
  --platform xhs \
  --login-type cookie \
  --cookies-file /secure/path/xhs_cookie.txt \
  --keywords "人工智能"
```

The runner reads the file and passes the value to MediaCrawler without printing
it. Do not put cookies in `SKILL.md`, source control, issue comments, or normal
chat messages.

### 5. Initialize a database

```bash
python .opencode/skills/mediacrawler/mediacrawler_runner.py \
  init-db --database sqlite
```

Supported values are `sqlite`, `mysql`, and `postgres`.

### 6. Summarize crawl output

After any crawl, `report` prints a JSON summary (file paths, record counts, and
sample items) parsed from the output files — no manual jsonl reading needed:

```bash
python .opencode/skills/mediacrawler/mediacrawler_runner.py \
  report --platform dy
```

## Runner Options

Global options must appear before the subcommand:

| Option | Meaning |
| --- | --- |
| `--project-root PATH` | Explicit MediaCrawler checkout; otherwise auto-detected from the current directory and parents |
| `--dry-run` | Print the generated command with cookies redacted, without running it |

Runtime options are available on `search`, `detail`, and `creator`:

| Option | Values / meaning |
| --- | --- |
| `--platform` | `xhs`, `dy`, `ks`, `bili`, `wb`, `tieba`, `zhihu` |
| `--login-type` | `qrcode`, `phone`, `cookie` |
| `--keywords` | Comma-separated search keywords |
| `--specified-id` | Comma-separated post/video IDs or URLs; used by `detail` |
| `--creator-id` | Comma-separated creator IDs or URLs; used by `creator` |
| `--cookies-file` | Local file containing the complete cookie string |
| `--get-comment` | `yes` or `no`; defaults to `no` in the runner |
| `--get-sub-comment` | `yes` or `no`; defaults to `no` |
| `--headless` | `yes` or `no`; defaults to `no` |
| `--save-data-option` | `csv`, `db`, `json`, `jsonl`, `sqlite`, `excel`, `mongodb`, `postgres` |
| `--save-data-path` | Custom output path; default is the repository `data/` folder |
| `--max-notes` | Maximum posts/videos, default `15` |
| `--max-comments` | First-level comments per item, default `10` |
| `--max-concurrency` | Concurrent crawlers, default `1` |
| `--start-page` | Starting page, default `1` |
| `--enable-ip-proxy` | `yes` or `no`; defaults to `no` |
| `--ip-proxy-provider` | `kuaidaili`, `wandouhttp`, or `static` |
| `--ip-proxy-pool-count` | Proxy pool size |
| `--static-proxy-url` | Static proxy URL when provider is `static` |

The runner translates these names to the exact MediaCrawler CLI names, such as
`--crawler_max_notes_count` and `--save_data_option`.

`report` options:

| Option | Meaning |
| --- | --- |
| `--platform` | Filter by platform (`xhs`, `dy`, ...); empty = all |
| `--save-data-path` | Output directory to scan; default is the repository `data/` folder |
| `--limit` | Sample records per file, default `5` |

## Result Handling

After a successful run:

1. Read the path printed by MediaCrawler, or inspect the configured
   `--save-data-path`.
2. For `json` and `jsonl`, parse records and report item counts, platforms,
   titles, authors, comment counts, and any errors. Do not invent missing data.
3. For `csv`, use the header row to identify fields before summarizing.
4. For `sqlite`, query read-only and inspect table names before selecting data.
5. For `excel`, inspect sheet names and row counts; do not overwrite the source.
6. Preserve the raw files and write derived summaries to a separate path.

Prefer the runner's `report` command over manual parsing when the crawl output
is `json` or `jsonl`. For comment records, each entry carries the commenter's
`homepage_url` when the user identifier is available — use it to link to the
commenter's profile.

The skill should report the exact command, effective platform/mode, output
location, item count, and any non-zero exit status. Never claim a crawl worked
only because the process started.

## Direct CLI Fallback

If the helper does not expose a needed option, use the project's documented CLI
directly after checking `uv run main.py --help`:

```bash
uv run main.py --platform dy --lt qrcode --type search \
  --keywords "关键词" --save_data_option jsonl
```

Use `config/base_config.py` only for settings that are not exposed by the CLI.
Keep changes minimal and restore temporary configuration changes after the run.

## Safety Boundaries

- Always collect only public information and respect platform terms, robots
  rules, rate limits, and the repository's non-commercial learning license.
- Always start with a small `--max-notes` value and `--max-concurrency 1`.
- Always ask the user before enabling proxies, increasing concurrency, or
  collecting second-level comments at scale.
- Never commit or print cookies, phone numbers, proxy credentials, or database
  passwords.
- Never run a broad crawl, evade access controls, bypass a CAPTCHA, or collect
  private data.
- Never call an external MCP server or remote downloader as part of this skill.
- QR-code and phone login remain human-in-the-loop operations.

## Failure Handling

- If project root detection fails, ask for or use `--project-root`.
- If `uv` is missing, report the precondition; do not silently substitute a
  different package manager.
- If login fails, stop and ask the user to complete login or provide a valid
  cookie file. Do not retry aggressively.
- If MediaCrawler exits non-zero, preserve its output and report the exit code
  and last visible error rather than claiming success.
