# zoterios

A CLI tool to interact with your local Zotero library.

## Prerequisites

- Python 3.13+
- [Zotero 7+](https://www.zotero.org/) running locally (default port 23119)

## Installation

```bash
# with uv (recommended)
uv tool install zoterios

# or with pip
pip install zoterios
```

To let AI agents (e.g. Kimi Code CLI) discover and use zoterios, install the skill definition:

```bash
zoterios install-skill ~/.config/agents/skills
```

## Quick Start

```bash
# Check connection
zoterios ping

# List recent papers
zoterios papers list

# Search papers
zoterios papers list --query "transformer" --tag "ML" --limit 10

# Get paper details
zoterios papers get ABCD1234

# Open a paper's PDF
zoterios papers pdf ABCD1234 --open

# Read a paper as markdown
zoterios papers markdown ABCD1234
```

## Commands

### `ping`

Test connection to the local Zotero instance.

### `papers`

| Command | Description |
|---|---|
| `papers list [--query Q] [--tag T] [--limit N]` | List papers (default limit: 20) |
| `papers get KEY` | Show paper details |
| `papers pdf KEY [--open]` | Print PDF path, or open it with `--open` |
| `papers markdown KEY` | Convert paper's PDF to markdown |
| `papers import-pdf PATH --title T [opts]` | Import a local PDF into Zotero |

**`import-pdf` options:**

```
--title TEXT        Paper title (required)
-a, --author TEXT   Author name (repeatable)
--year TEXT         Publication year
--type TEXT         Item type: document (default), journalArticle,
                    conferencePaper, preprint, book, thesis, report
--journal TEXT      Journal / publication name
--abstract TEXT     Abstract
--doi TEXT          DOI
--url TEXT          URL
-t, --tag TEXT      Tag (repeatable)
```

Example:

```bash
zoterios papers import-pdf paper.pdf \
  --title "Attention Is All You Need" \
  -a "Ashish Vaswani" -a "Noam Shazeer" \
  --year 2017 --type conferencePaper \
  --journal "NeurIPS" -t "transformer"
```

### `arxiv`

| Command | Description |
|---|---|
| `arxiv fetch ID` | Fetch paper metadata from arXiv |
| `arxiv pdf ID [--open]` | Download PDF (cached locally) |
| `arxiv markdown ID` | Convert arXiv PDF to markdown |
| `arxiv source ID` | Download and extract TeX source |
| `arxiv save ID [--no-pdf]` | Save paper to Zotero (with PDF by default) |
| `arxiv check ID` | Check if paper already exists in Zotero |
| `arxiv clear-cache ID` | Clear cached data for a paper |

Example:

```bash
zoterios arxiv fetch 1706.03762
zoterios arxiv save 1706.03762
```

### `markdownit`

Convert any supported file to markdown (PDF, DOCX, PPTX, HTML, etc.):

```bash
zoterios markdownit report.pdf
zoterios markdownit slides.pptx
```

## Global Options

```
--base-url TEXT   Zotero API URL (default: http://localhost:23119)
--cache-dir TEXT  Cache directory (default: ~/.cache/zoterios)
--json            Output JSON for all commands
```

## Configuration

Settings can be configured via environment variables (prefix `ZOTERIOS_`) or a `.env` file:

| Variable | Default | Description |
|---|---|---|
| `ZOTERIOS_BASE_URL` | `http://localhost:23119` | Zotero local API URL |
| `ZOTERIOS_CACHE_DIR` | `~/.cache/zoterios` | Cache directory |
| `ZOTERIOS_HTTP_PROXY` | | HTTP proxy |
| `ZOTERIOS_HTTPS_PROXY` | | HTTPS proxy |

CLI flags (`--base-url`, `--cache-dir`) take priority over env vars.

## License

MIT
