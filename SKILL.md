---
name: zoterios
description: CLI tool that talks to a running Zotero 7+ instance via its local API. Use it to list/search papers, read PDFs as markdown, import new PDFs with metadata, fetch arXiv papers (metadata, PDF, TeX source) and save them into Zotero, or convert arbitrary files to markdown with markdownit.
---

# zoterios

CLI tool to interact with a local Zotero library. Requires Zotero 7+ running locally on port 23119.

## Global Options

```
zoterios [--base-url URL] [--cache-dir DIR] [--json] COMMAND
```

- `--base-url` — Zotero API URL (default: `http://localhost:23119`, env: `ZOTERIOS_BASE_URL`)
- `--cache-dir` — Cache directory (default: `~/.cache/zoterios`, env: `ZOTERIOS_CACHE_DIR`)
- `--json` — Output JSON for all commands (useful for piping/parsing)

Configuration via env vars (prefix `ZOTERIOS_`) or `.env` file. Proxy: `ZOTERIOS_HTTP_PROXY`, `ZOTERIOS_HTTPS_PROXY`.

## Commands

### Connection

```bash
zoterios ping                    # Test Zotero connection
```

### Papers (Zotero library)

```bash
zoterios papers list [--query Q] [--tag T] [--limit N]   # List papers
zoterios papers get KEY                                    # Paper details
zoterios papers pdf KEY [--open]                           # Get PDF path or open it
zoterios papers markdown KEY                               # Convert paper PDF to markdown
zoterios papers import-pdf PATH --title T [options]        # Import local PDF into Zotero
```

`import-pdf` options: `--title` (required), `-a/--author` (repeatable), `--year`, `--type` (default: document; also: journalArticle, conferencePaper, preprint, book, thesis, report), `--journal`, `--abstract`, `--doi`, `--url`, `-t/--tag` (repeatable).

### arXiv

```bash
zoterios arxiv fetch ID          # Fetch metadata (title, authors, abstract, etc.)
zoterios arxiv pdf ID [--open]   # Download PDF, return cached path
zoterios arxiv markdown ID       # Convert arXiv PDF to markdown
zoterios arxiv source ID         # Download & extract TeX source
zoterios arxiv save ID [--no-pdf]  # Save to Zotero (with PDF by default)
zoterios arxiv check ID          # Check if already in Zotero
zoterios arxiv clear-cache ID    # Clear local cache
```

### File Conversion

```bash
zoterios markdownit FILE         # Convert any file (PDF, DOCX, PPTX, HTML, ...) to markdown
```

## Examples

```bash
# Search and read a paper
zoterios papers list --query "attention" --limit 5
zoterios papers markdown ABCD1234

# Import a local PDF with metadata
zoterios papers import-pdf paper.pdf --title "My Paper" -a "Alice Smith" -a "Bob Jones" --year 2024 --type journalArticle --journal "Nature" -t "ML"

# Fetch arXiv paper and save to Zotero
zoterios arxiv fetch 2301.00001
zoterios arxiv save 2301.00001

# Convert any file to markdown
zoterios markdownit report.pdf
zoterios markdownit slides.pptx
```
