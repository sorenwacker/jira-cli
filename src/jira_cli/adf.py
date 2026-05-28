"""Markdown to Atlassian Document Format (ADF) conversion."""

import re
from typing import Any


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

        # Skip empty lines
        if not line.strip():
            i += 1
            continue

        # Code block
        if line.startswith("```"):
            block, i = _parse_code_block(lines, i)
            blocks.append(block)
            continue

        # Heading
        if match := re.match(r"^(#{1,6})\s+(.+)$", line):
            level = len(match.group(1))
            content = _parse_inline(match.group(2))
            blocks.append(
                {
                    "type": "heading",
                    "attrs": {"level": level},
                    "content": content,
                }
            )
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", line.strip()):
            blocks.append({"type": "rule"})
            i += 1
            continue

        # Bullet list
        if re.match(r"^[-*]\s+", line):
            block, i = _parse_bullet_list(lines, i)
            blocks.append(block)
            continue

        # Numbered list
        if re.match(r"^\d+\.\s+", line):
            block, i = _parse_ordered_list(lines, i)
            blocks.append(block)
            continue

        # Paragraph - collect lines until blank line or block element
        para_lines, i = _collect_paragraph_lines(lines, i)
        if para_lines:
            para_text = "\n".join(para_lines)
            content = _parse_inline_with_breaks(para_text)
            if content:
                blocks.append({"type": "paragraph", "content": content})

    return blocks


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
        if match := re.match(r"^[-*]\s+(.+)$", line):
            item_text = match.group(1)
            item_content = _parse_inline(item_text)
            items.append(
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": item_content}],
                }
            )
            i += 1
        elif not line.strip():
            # Empty line might end the list
            if i + 1 < len(lines) and re.match(r"^[-*]\s+", lines[i + 1]):
                i += 1  # Skip empty line, continue list
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
        if match := re.match(r"^\d+\.\s+(.+)$", line):
            item_text = match.group(1)
            item_content = _parse_inline(item_text)
            items.append(
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": item_content}],
                }
            )
            i += 1
        elif not line.strip():
            # Empty line might end the list
            if i + 1 < len(lines) and re.match(r"^\d+\.\s+", lines[i + 1]):
                i += 1
            else:
                break
        else:
            break

    return {"type": "orderedList", "content": items}, i


def _collect_paragraph_lines(lines: list[str], start: int) -> tuple[list[str], int]:
    """Collect lines that form a paragraph."""
    para_lines = []
    i = start

    while i < len(lines):
        line = lines[i]

        # Stop at block-level elements
        if not line.strip():
            i += 1
            break
        if line.startswith("```"):
            break
        if re.match(r"^#{1,6}\s+", line):
            break
        if re.match(r"^[-*]\s+", line):
            break
        if re.match(r"^\d+\.\s+", line):
            break
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", line.strip()):
            break

        para_lines.append(line)
        i += 1

    return para_lines, i


def _parse_inline_with_breaks(text: str) -> list[dict[str, Any]]:
    """Parse inline content, converting newlines to hard breaks."""
    result: list[dict[str, Any]] = []
    parts = text.split("\n")

    for idx, part in enumerate(parts):
        if part:
            inline_content = _parse_inline(part)
            result.extend(inline_content)
        if idx < len(parts) - 1:
            result.append({"type": "hardBreak"})

    # Remove trailing hardBreak
    if result and result[-1].get("type") == "hardBreak":
        result.pop()

    return result


def _parse_inline(text: str) -> list[dict[str, Any]]:
    """Parse inline markdown formatting."""
    if not text:
        return []

    result: list[dict[str, Any]] = []
    pos = 0

    # Combined pattern for all inline elements
    pattern = re.compile(
        r"(\*\*\*(.+?)\*\*\*)"  # Bold italic ***text***
        r"|(\*\*(.+?)\*\*)"  # Bold **text**
        r"|(__(.+?)__)"  # Bold __text__
        r"|(\*([^*]+?)\*)"  # Italic *text*
        r"|(_([^_]+?)_)"  # Italic _text_
        r"|(`([^`]+?)`)"  # Code `text`
        r"|(\[([^\]]+?)\]\(([^)]+?)\))"  # Link [text](url)
    )

    for match in pattern.finditer(text):
        # Add text before this match
        if match.start() > pos:
            before = text[pos : match.start()]
            if before:
                result.append({"type": "text", "text": before})

        # Process the match
        if match.group(1):  # Bold italic ***
            result.append(
                {
                    "type": "text",
                    "text": match.group(2),
                    "marks": [{"type": "strong"}, {"type": "em"}],
                }
            )
        elif match.group(3):  # Bold **
            result.append(
                {
                    "type": "text",
                    "text": match.group(4),
                    "marks": [{"type": "strong"}],
                }
            )
        elif match.group(5):  # Bold __
            result.append(
                {
                    "type": "text",
                    "text": match.group(6),
                    "marks": [{"type": "strong"}],
                }
            )
        elif match.group(7):  # Italic *
            result.append(
                {
                    "type": "text",
                    "text": match.group(8),
                    "marks": [{"type": "em"}],
                }
            )
        elif match.group(9):  # Italic _
            result.append(
                {
                    "type": "text",
                    "text": match.group(10),
                    "marks": [{"type": "em"}],
                }
            )
        elif match.group(11):  # Code `
            result.append(
                {
                    "type": "text",
                    "text": match.group(12),
                    "marks": [{"type": "code"}],
                }
            )
        elif match.group(13):  # Link
            result.append(
                {
                    "type": "text",
                    "text": match.group(14),
                    "marks": [{"type": "link", "attrs": {"href": match.group(15)}}],
                }
            )

        pos = match.end()

    # Add remaining text
    if pos < len(text):
        remaining = text[pos:]
        if remaining:
            result.append({"type": "text", "text": remaining})

    # If no matches, return the whole text
    if not result and text:
        result.append({"type": "text", "text": text})

    return result
