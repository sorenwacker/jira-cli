"""Markdown to Atlassian Document Format (ADF) conversion."""

import re
from typing import Any

# Block boundary patterns
_CODE_FENCE = re.compile(r"^```")
_HEADING = re.compile(r"^#{1,6}\s+")
_BULLET = re.compile(r"^[-*]\s+")
_NUMBERED = re.compile(r"^\d+\.\s+")
_HRULE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")

# Block patterns with capture
_HEADING_FULL = re.compile(r"^(#{1,6})\s+(.+)$")
_BULLET_ITEM = re.compile(r"^[-*]\s+(.+)$")
_NUMBERED_ITEM = re.compile(r"^\d+\.\s+(.+)$")

# Inline pattern for markdown formatting
_INLINE_PATTERN = re.compile(
    r"(?P<bold_italic>\*\*\*(?P<bold_italic_text>.+?)\*\*\*)"
    r"|(?P<bold_ast>\*\*(?P<bold_ast_text>.+?)\*\*)"
    r"|(?P<bold_under>__(?P<bold_under_text>.+?)__)"
    r"|(?P<italic_ast>\*(?P<italic_ast_text>[^*]+?)\*)"
    r"|(?P<italic_under>_(?P<italic_under_text>[^_]+?)_)"
    r"|(?P<code>`(?P<code_text>[^`]+?)`)"
    r"|(?P<link>\[(?P<link_text>[^\]]+?)\]\((?P<link_url>[^)]+?)\))"
)

# Inline node type mappings: (group_name, text_group_name, marks)
_INLINE_NODE_TYPES: list[tuple[str, str, list[str]]] = [
    ("bold_italic", "bold_italic_text", ["strong", "em"]),
    ("bold_ast", "bold_ast_text", ["strong"]),
    ("bold_under", "bold_under_text", ["strong"]),
    ("italic_ast", "italic_ast_text", ["em"]),
    ("italic_under", "italic_under_text", ["em"]),
    ("code", "code_text", ["code"]),
]


def markdown_to_adf(text: str) -> dict[str, Any]:
    """Convert markdown text to Atlassian Document Format.

    Args:
        text: Markdown-formatted text.

    Returns:
        ADF document structure.
    """
    if not text or not text.strip():
        return {"type": "doc", "version": 1, "content": []}

    content = _parse_blocks(text)
    return {"type": "doc", "version": 1, "content": content}


def _parse_blocks(text: str) -> list[dict[str, Any]]:
    """Parse text into block-level ADF nodes."""
    blocks: list[dict[str, Any]] = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        block, i = _parse_single_block(lines, i, line)
        if block:
            blocks.append(block)

    return blocks


def _parse_single_block(
    lines: list[str],
    i: int,
    line: str,
) -> tuple[dict[str, Any] | None, int]:
    """Parse a single block element using dispatch."""
    # Try each block type in order
    for parser in _BLOCK_PARSERS:
        result = parser(lines, i, line)
        if result is not None:
            return result
    return _parse_paragraph(lines, i)


def _try_code_block(
    lines: list[str],
    i: int,
    line: str,
) -> tuple[dict[str, Any], int] | None:
    """Try to parse a code block."""
    if not line.startswith("```"):
        return None
    return _parse_code_block(lines, i)


def _try_heading(
    lines: list[str],  # noqa: ARG001
    i: int,
    line: str,
) -> tuple[dict[str, Any], int] | None:
    """Try to parse a heading."""
    match = _HEADING_FULL.match(line)
    if not match:
        return None
    level = len(match.group(1))
    content = _parse_inline(match.group(2))
    return {"type": "heading", "attrs": {"level": level}, "content": content}, i + 1


def _try_hrule(
    lines: list[str],  # noqa: ARG001
    i: int,
    line: str,
) -> tuple[dict[str, Any], int] | None:
    """Try to parse a horizontal rule."""
    if not _HRULE.match(line.strip()):
        return None
    return {"type": "rule"}, i + 1


def _try_bullet_list(
    lines: list[str],
    i: int,
    line: str,
) -> tuple[dict[str, Any], int] | None:
    """Try to parse a bullet list."""
    if not _BULLET.match(line):
        return None
    return _parse_bullet_list(lines, i)


def _try_ordered_list(
    lines: list[str],
    i: int,
    line: str,
) -> tuple[dict[str, Any], int] | None:
    """Try to parse an ordered list."""
    if not _NUMBERED.match(line):
        return None
    return _parse_ordered_list(lines, i)


# Block parser dispatch table
_BLOCK_PARSERS = [
    _try_code_block,
    _try_heading,
    _try_hrule,
    _try_bullet_list,
    _try_ordered_list,
]


def _parse_paragraph(
    lines: list[str],
    start: int,
) -> tuple[dict[str, Any] | None, int]:
    """Parse a paragraph block."""
    para_lines, i = _collect_paragraph_lines(lines, start)
    if not para_lines:
        return None, i
    para_text = "\n".join(para_lines)
    content = _parse_inline_with_breaks(para_text)
    if not content:
        return None, i
    return {"type": "paragraph", "content": content}, i


def _parse_code_block(lines: list[str], start: int) -> tuple[dict[str, Any], int]:
    """Parse a fenced code block."""
    first_line = lines[start]
    language = first_line[3:].strip() or None

    code_lines = []
    i = start + 1
    while i < len(lines):
        if lines[i].startswith("```"):
            i += 1
            break
        code_lines.append(lines[i])
        i += 1

    code_text = "\n".join(code_lines)
    block: dict[str, Any] = {
        "type": "codeBlock",
        "content": [{"type": "text", "text": code_text}],
    }
    if language:
        block["attrs"] = {"language": language}

    return block, i


def _parse_bullet_list(lines: list[str], start: int) -> tuple[dict[str, Any], int]:
    """Parse a bullet list."""
    items = []
    i = start

    while i < len(lines):
        line = lines[i]
        if match := _BULLET_ITEM.match(line):
            items.append(_create_list_item(match.group(1)))
            i += 1
        elif not line.strip():
            if i + 1 < len(lines) and _BULLET.match(lines[i + 1]):
                i += 1
            else:
                break
        else:
            break

    return {"type": "bulletList", "content": items}, i


def _parse_ordered_list(lines: list[str], start: int) -> tuple[dict[str, Any], int]:
    """Parse an ordered list."""
    items = []
    i = start

    while i < len(lines):
        line = lines[i]
        if match := _NUMBERED_ITEM.match(line):
            items.append(_create_list_item(match.group(1)))
            i += 1
        elif not line.strip():
            if i + 1 < len(lines) and _NUMBERED.match(lines[i + 1]):
                i += 1
            else:
                break
        else:
            break

    return {"type": "orderedList", "content": items}, i


def _create_list_item(text: str) -> dict[str, Any]:
    """Create a list item node."""
    content = _parse_inline(text)
    return {
        "type": "listItem",
        "content": [{"type": "paragraph", "content": content}],
    }


def _collect_paragraph_lines(lines: list[str], start: int) -> tuple[list[str], int]:
    """Collect lines that form a paragraph."""
    para_lines = []
    i = start

    while i < len(lines):
        line = lines[i]
        if _is_block_boundary(line):
            if not line.strip():
                i += 1
            break
        para_lines.append(line)
        i += 1

    return para_lines, i


def _is_block_boundary(line: str) -> bool:
    """Check if line is a block boundary."""
    stripped = line.strip()
    if not stripped:
        return True
    patterns = [_CODE_FENCE, _HEADING, _BULLET, _NUMBERED]
    if any(p.match(line) for p in patterns):
        return True
    return bool(_HRULE.match(stripped))


def _parse_inline_with_breaks(text: str) -> list[dict[str, Any]]:
    """Parse inline content, converting newlines to hard breaks."""
    result: list[dict[str, Any]] = []
    parts = text.split("\n")

    for idx, part in enumerate(parts):
        if part:
            result.extend(_parse_inline(part))
        if idx < len(parts) - 1:
            result.append({"type": "hardBreak"})

    if result and result[-1].get("type") == "hardBreak":
        result.pop()

    return result


def _parse_inline(text: str) -> list[dict[str, Any]]:
    """Parse inline markdown formatting."""
    if not text:
        return []

    result: list[dict[str, Any]] = []
    pos = 0

    for match in _INLINE_PATTERN.finditer(text):
        if match.start() > pos:
            result.append({"type": "text", "text": text[pos : match.start()]})
        node = _create_inline_node(match)
        if node:
            result.append(node)
        pos = match.end()

    if pos < len(text):
        result.append({"type": "text", "text": text[pos:]})

    if not result and text:
        result.append({"type": "text", "text": text})

    return result


def _create_inline_node(match: re.Match[str]) -> dict[str, Any] | None:
    """Create an inline node from a regex match using dispatch table."""
    # Check standard text marks
    for group_name, text_group, marks in _INLINE_NODE_TYPES:
        if match.group(group_name):
            return _text_with_marks(match.group(text_group), marks)

    # Handle link separately (has attrs)
    if match.group("link"):
        return _create_link_node(match)

    return None


def _text_with_marks(text: str, marks: list[str]) -> dict[str, Any]:
    """Create a text node with marks."""
    return {"type": "text", "text": text, "marks": [{"type": m} for m in marks]}


def _create_link_node(match: re.Match[str]) -> dict[str, Any]:
    """Create a link node from a regex match."""
    return {
        "type": "text",
        "text": match.group("link_text"),
        "marks": [{"type": "link", "attrs": {"href": match.group("link_url")}}],
    }
