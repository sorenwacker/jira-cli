"""Markdown to Confluence storage format conversion and rendering.

Confluence pages are stored as "storage format", an XHTML-based representation.
This module converts a subset of markdown to storage format for writing, and
renders storage format back to plain text for terminal display.
"""

import re
from html import escape, unescape

__all__ = ["markdown_to_storage", "storage_to_text"]

_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
_BULLET = re.compile(r"^[-*]\s+(.+)$")
_NUMBERED = re.compile(r"^\d+\.\s+(.+)$")
_HRULE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")

_INLINE_PATTERN = re.compile(
    r"(?P<bold_italic>\*\*\*(?P<bold_italic_text>.+?)\*\*\*)"
    r"|(?P<bold_ast>\*\*(?P<bold_ast_text>.+?)\*\*)"
    r"|(?P<bold_under>__(?P<bold_under_text>.+?)__)"
    r"|(?P<italic_ast>\*(?P<italic_ast_text>[^*]+?)\*)"
    r"|(?P<italic_under>_(?P<italic_under_text>[^_]+?)_)"
    r"|(?P<code>`(?P<code_text>[^`]+?)`)"
    r"|(?P<link>\[(?P<link_text>[^\]]+?)\]\((?P<link_url>[^)]+?)\))"
)


def markdown_to_storage(text: str) -> str:
    """Convert markdown text to Confluence storage format.

    Args:
        text: Markdown-formatted text.

    Returns:
        Storage-format XHTML string (empty for blank input).
    """
    if not text or not text.strip():
        return ""

    lines = text.split("\n")
    blocks: list[str] = []
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        block, i = _parse_block(lines, i)
        blocks.append(block)
    return "".join(blocks)


def _parse_block(lines: list[str], i: int) -> tuple[str, int]:
    """Parse a single block, returning its storage XHTML and the next index."""
    for parser in _BLOCK_PARSERS:
        result = parser(lines, i)
        if result is not None:
            return result
    return _paragraph(lines, i)


def _try_code(lines: list[str], i: int) -> tuple[str, int] | None:
    """Parse a fenced code block into a Confluence code macro."""
    if not lines[i].startswith("```"):
        return None
    language = lines[i][3:].strip()
    code_lines: list[str] = []
    j = i + 1
    while j < len(lines) and not lines[j].startswith("```"):
        code_lines.append(lines[j])
        j += 1
    j = min(j + 1, len(lines))
    return _code_macro(language, "\n".join(code_lines)), j


def _try_heading(lines: list[str], i: int) -> tuple[str, int] | None:
    """Parse a heading line."""
    match = _HEADING.match(lines[i])
    if not match:
        return None
    level = len(match.group(1))
    return f"<h{level}>{_inline(match.group(2))}</h{level}>", i + 1


def _try_hrule(lines: list[str], i: int) -> tuple[str, int] | None:
    """Parse a horizontal rule."""
    if not _HRULE.match(lines[i].strip()):
        return None
    return "<hr/>", i + 1


def _try_bullet(lines: list[str], i: int) -> tuple[str, int] | None:
    """Parse a bullet list."""
    if not _BULLET.match(lines[i]):
        return None
    return _list_block(lines, i, _BULLET, "ul")


def _try_ordered(lines: list[str], i: int) -> tuple[str, int] | None:
    """Parse an ordered list."""
    if not _NUMBERED.match(lines[i]):
        return None
    return _list_block(lines, i, _NUMBERED, "ol")


_BLOCK_PARSERS = [_try_code, _try_heading, _try_hrule, _try_bullet, _try_ordered]


def _code_macro(language: str, code: str) -> str:
    """Build a Confluence code macro for a code block."""
    lang = (
        f'<ac:parameter ac:name="language">{escape(language, quote=False)}'
        "</ac:parameter>"
        if language
        else ""
    )
    return (
        '<ac:structured-macro ac:name="code">'
        f"{lang}"
        f"<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>"
        "</ac:structured-macro>"
    )


def _list_block(
    lines: list[str],
    start: int,
    pattern: re.Pattern[str],
    tag: str,
) -> tuple[str, int]:
    """Parse a contiguous list into ul/ol storage markup."""
    items: list[str] = []
    i = start
    while i < len(lines):
        match = pattern.match(lines[i])
        if not match:
            break
        items.append(f"<li>{_inline(match.group(1))}</li>")
        i += 1
    return f"<{tag}>{''.join(items)}</{tag}>", i


def _is_boundary(line: str) -> bool:
    """Check whether a line starts a new block."""
    if line.startswith("```") or _HEADING.match(line):
        return True
    if _BULLET.match(line) or _NUMBERED.match(line):
        return True
    return bool(_HRULE.match(line.strip()))


def _paragraph(lines: list[str], start: int) -> tuple[str, int]:
    """Collect consecutive lines into a paragraph."""
    para: list[str] = []
    i = start
    while i < len(lines):
        if not lines[i].strip() or _is_boundary(lines[i]):
            break
        para.append(lines[i])
        i += 1
    return f"<p>{_inline('\n'.join(para))}</p>", i


def _inline(text: str) -> str:
    """Convert inline markdown formatting to storage XHTML, escaping text."""
    result: list[str] = []
    pos = 0
    for match in _INLINE_PATTERN.finditer(text):
        if match.start() > pos:
            result.append(escape(text[pos : match.start()], quote=False))
        result.append(_inline_node(match))
        pos = match.end()
    if pos < len(text):
        result.append(escape(text[pos:], quote=False))
    return "".join(result)


def _inline_node(match: re.Match[str]) -> str:
    """Render a single inline match to storage XHTML."""
    if match.group("code"):
        return f"<code>{escape(match.group('code_text'), quote=False)}</code>"
    if match.group("link"):
        href = escape(match.group("link_url"), quote=True)
        text = escape(match.group("link_text"), quote=False)
        return f'<a href="{href}">{text}</a>'
    return _emphasis_node(match)


def _emphasis_node(match: re.Match[str]) -> str:
    """Render a bold, italic, or bold-italic inline match to storage XHTML."""
    if match.group("bold_italic"):
        inner = escape(match.group("bold_italic_text"), quote=False)
        return f"<strong><em>{inner}</em></strong>"
    if match.group("bold_ast") or match.group("bold_under"):
        inner = escape(
            match.group("bold_ast_text") or match.group("bold_under_text"),
            quote=False,
        )
        return f"<strong>{inner}</strong>"
    inner = escape(
        match.group("italic_ast_text") or match.group("italic_under_text"),
        quote=False,
    )
    return f"<em>{inner}</em>"


_CDATA = re.compile(
    r"<ac:plain-text-body><!\[CDATA\[(.*?)\]\]></ac:plain-text-body>",
    re.DOTALL,
)
_BLOCK_CLOSE = re.compile(r"</(p|h[1-6]|li|ul|ol|tr|table)>", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")


def storage_to_text(storage: str | None) -> str:
    """Render storage-format XHTML to plain text for terminal display.

    Args:
        storage: Storage-format XHTML, or None.

    Returns:
        Plain text with block elements separated by newlines.
    """
    if not storage:
        return ""

    text = _CDATA.sub(lambda m: f"{m.group(1)}\n", storage)
    text = _BLOCK_CLOSE.sub("\n", text)
    text = text.replace("<hr/>", "\n").replace("<br/>", "\n")
    text = _TAG.sub("", text)
    text = unescape(text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()
