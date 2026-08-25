# Markdown Formatting

Issue descriptions, comments, and Confluence page bodies are written in markdown and converted on the way to Atlassian.

## Jira: Atlassian Document Format

Jira descriptions and comments are converted to Atlassian Document Format (ADF).

| Syntax | Result |
|--------|--------|
| `**bold**` | Bold |
| `*italic*` | Italic |
| `` `code` `` | Inline code |
| ```` ```lang ```` | Code block with language |
| `# Heading` | Headings 1-6 |
| `- item` | Bullet list |
| `1. item` | Numbered list |
| `[text](url)` | Link |
| `---` | Horizontal rule |
| Blank line | Paragraph break |

Markdown tables are not converted; Jira does not render them.

```bash
jira issue create PROJ "New feature" -d "## Overview

This is a **new feature** with:
- Item one
- Item two
"
```

## Confluence: storage format

Confluence pages are stored as storage format, an XHTML-based representation. The supported syntax mirrors the ADF converter, with one addition for task lists.

| Syntax | Storage output |
|--------|----------------|
| `# Heading` | `<h1>` to `<h6>` |
| `**bold**` | `<strong>` |
| `*italic*` | `<em>` |
| `` `code` `` | `<code>` |
| ```` ```lang ```` | `code` macro with language parameter |
| `- item` | `<ul><li>` |
| `- [ ] item` / `- [x] item` | `task-list` macro (unchecked / checked) |
| `1. item` | `<ol><li>` |
| `[text](url)` | `<a href>` |
| `---` | `<hr/>` |
| Blank line | `<p>` |

Reading a page renders the storage-format body to plain text; `confluence page ID --raw` shows the unmodified XHTML.
