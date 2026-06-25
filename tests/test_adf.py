"""Tests for markdown to ADF conversion."""

from jira_cli.adf import markdown_to_adf


class TestPlainText:
    """Tests for plain text conversion."""

    def test_simple_text(self) -> None:
        """Simple text becomes a paragraph."""
        result = markdown_to_adf("Hello world")
        assert result == {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Hello world"}],
                }
            ],
        }

    def test_multiple_paragraphs(self) -> None:
        """Blank lines create separate paragraphs."""
        result = markdown_to_adf("First paragraph\n\nSecond paragraph")
        assert len(result["content"]) == 2
        assert result["content"][0]["content"][0]["text"] == "First paragraph"
        assert result["content"][1]["content"][0]["text"] == "Second paragraph"

    def test_single_newlines_preserved(self) -> None:
        """Single newlines within paragraph create hard breaks."""
        result = markdown_to_adf("Line one\nLine two")
        content = result["content"][0]["content"]
        assert len(content) == 3  # text, hardBreak, text
        assert content[0]["text"] == "Line one"
        assert content[1]["type"] == "hardBreak"
        assert content[2]["text"] == "Line two"

    def test_empty_string(self) -> None:
        """Empty string returns empty doc."""
        result = markdown_to_adf("")
        assert result == {"type": "doc", "version": 1, "content": []}

    def test_whitespace_only(self) -> None:
        """Whitespace-only string returns empty doc."""
        result = markdown_to_adf("   \n\n   ")
        assert result == {"type": "doc", "version": 1, "content": []}


class TestUnderscoreEmphasis:
    """Tests for underscore emphasis word-boundary handling."""

    def test_intra_word_underscores_not_italic(self) -> None:
        """Underscores inside a word do not create emphasis."""
        nodes = markdown_to_adf("some_variable_name")["content"][0]["content"]
        assert len(nodes) == 1
        assert nodes[0]["text"] == "some_variable_name"
        assert "marks" not in nodes[0]

    def test_underscore_emphasis_at_word_boundary(self) -> None:
        """Underscore emphasis at word boundaries still applies."""
        first = markdown_to_adf("_italic_ word")["content"][0]["content"][0]
        assert first["text"] == "italic"
        assert first["marks"] == [{"type": "em"}]


class TestInlineFormatting:
    """Tests for inline formatting."""

    def test_bold_double_asterisk(self) -> None:
        """**text** becomes bold."""
        result = markdown_to_adf("This is **bold** text")
        content = result["content"][0]["content"]
        assert content[1]["text"] == "bold"
        assert content[1]["marks"] == [{"type": "strong"}]

    def test_bold_double_underscore(self) -> None:
        """__text__ becomes bold."""
        result = markdown_to_adf("This is __bold__ text")
        content = result["content"][0]["content"]
        assert content[1]["text"] == "bold"
        assert content[1]["marks"] == [{"type": "strong"}]

    def test_italic_single_asterisk(self) -> None:
        """*text* becomes italic."""
        result = markdown_to_adf("This is *italic* text")
        content = result["content"][0]["content"]
        assert content[1]["text"] == "italic"
        assert content[1]["marks"] == [{"type": "em"}]

    def test_italic_single_underscore(self) -> None:
        """_text_ becomes italic."""
        result = markdown_to_adf("This is _italic_ text")
        content = result["content"][0]["content"]
        assert content[1]["text"] == "italic"
        assert content[1]["marks"] == [{"type": "em"}]

    def test_inline_code(self) -> None:
        """`code` becomes code mark."""
        result = markdown_to_adf("Run `npm install` to install")
        content = result["content"][0]["content"]
        assert content[1]["text"] == "npm install"
        assert content[1]["marks"] == [{"type": "code"}]

    def test_bold_italic_combined(self) -> None:
        """***text*** becomes bold and italic."""
        result = markdown_to_adf("This is ***bold italic*** text")
        content = result["content"][0]["content"]
        marks = content[1]["marks"]
        mark_types = {m["type"] for m in marks}
        assert mark_types == {"strong", "em"}


class TestLinks:
    """Tests for link conversion."""

    def test_markdown_link(self) -> None:
        """[text](url) becomes a link."""
        result = markdown_to_adf("Click [here](https://example.com) for info")
        content = result["content"][0]["content"]
        assert content[1]["text"] == "here"
        assert content[1]["marks"] == [
            {"type": "link", "attrs": {"href": "https://example.com"}}
        ]

    def test_link_with_special_chars(self) -> None:
        """Links with query params work."""
        result = markdown_to_adf("[link](https://example.com/path?a=1&b=2)")
        content = result["content"][0]["content"]
        assert (
            content[0]["marks"][0]["attrs"]["href"]
            == "https://example.com/path?a=1&b=2"
        )


class TestHeadings:
    """Tests for heading conversion."""

    def test_heading_level_1(self) -> None:
        """# creates h1."""
        result = markdown_to_adf("# Heading 1")
        assert result["content"][0]["type"] == "heading"
        assert result["content"][0]["attrs"]["level"] == 1
        assert result["content"][0]["content"][0]["text"] == "Heading 1"

    def test_heading_level_2(self) -> None:
        """## creates h2."""
        result = markdown_to_adf("## Heading 2")
        assert result["content"][0]["attrs"]["level"] == 2

    def test_heading_level_3(self) -> None:
        """### creates h3."""
        result = markdown_to_adf("### Heading 3")
        assert result["content"][0]["attrs"]["level"] == 3

    def test_heading_with_inline_formatting(self) -> None:
        """Headings can contain inline formatting."""
        result = markdown_to_adf("# Heading with **bold**")
        content = result["content"][0]["content"]
        assert len(content) == 2
        assert content[1]["marks"] == [{"type": "strong"}]


class TestCodeBlocks:
    """Tests for code block conversion."""

    def test_fenced_code_block(self) -> None:
        """```code``` becomes codeBlock."""
        result = markdown_to_adf("```\ncode here\n```")
        assert result["content"][0]["type"] == "codeBlock"
        assert result["content"][0]["content"][0]["text"] == "code here"

    def test_code_block_with_language(self) -> None:
        """```python becomes codeBlock with language."""
        result = markdown_to_adf("```python\ndef foo():\n    pass\n```")
        block = result["content"][0]
        assert block["type"] == "codeBlock"
        assert block["attrs"]["language"] == "python"
        assert "def foo():" in block["content"][0]["text"]

    def test_code_block_preserves_indentation(self) -> None:
        """Code blocks preserve indentation."""
        code = "```\n    indented\n        more\n```"
        result = markdown_to_adf(code)
        text = result["content"][0]["content"][0]["text"]
        assert "    indented" in text
        assert "        more" in text

    def test_empty_code_block_omits_text_node(self) -> None:
        """An empty fenced block has empty content (ADF rejects empty text)."""
        block = markdown_to_adf("```\n```")["content"][0]
        assert block["type"] == "codeBlock"
        assert block["content"] == []


class TestLists:
    """Tests for list conversion."""

    def test_bullet_list_dash(self) -> None:
        """- items become bulletList."""
        result = markdown_to_adf("- Item 1\n- Item 2\n- Item 3")
        assert result["content"][0]["type"] == "bulletList"
        items = result["content"][0]["content"]
        assert len(items) == 3
        assert items[0]["type"] == "listItem"

    def test_bullet_list_asterisk(self) -> None:
        """* items become bulletList."""
        result = markdown_to_adf("* Item 1\n* Item 2")
        assert result["content"][0]["type"] == "bulletList"

    def test_numbered_list(self) -> None:
        """1. items become orderedList."""
        result = markdown_to_adf("1. First\n2. Second\n3. Third")
        assert result["content"][0]["type"] == "orderedList"
        items = result["content"][0]["content"]
        assert len(items) == 3

    def test_list_with_inline_formatting(self) -> None:
        """List items can contain inline formatting."""
        result = markdown_to_adf("- Item with **bold**")
        item_content = result["content"][0]["content"][0]["content"][0]["content"]
        assert any(
            node.get("marks") == [{"type": "strong"}]
            for node in item_content
            if "marks" in node
        )


class TestHorizontalRule:
    """Tests for horizontal rule conversion."""

    def test_horizontal_rule_dashes(self) -> None:
        """--- becomes rule."""
        result = markdown_to_adf("Above\n\n---\n\nBelow")
        types = [node["type"] for node in result["content"]]
        assert "rule" in types

    def test_spaced_thematic_break_is_rule_not_bullet(self) -> None:
        """A space-separated thematic break is a rule, not a bullet list."""
        result = markdown_to_adf("* * *")
        assert result["content"][0]["type"] == "rule"

    def test_horizontal_rule_asterisks(self) -> None:
        """*** becomes rule."""
        result = markdown_to_adf("Above\n\n***\n\nBelow")
        types = [node["type"] for node in result["content"]]
        assert "rule" in types


class TestComplexDocuments:
    """Tests for complex document structures."""

    def test_mixed_content(self) -> None:
        """Document with multiple element types."""
        md = """# Title

This is a paragraph with **bold** and *italic*.

## Section

- Item 1
- Item 2

```python
code
```
"""
        result = markdown_to_adf(md)
        types = [node["type"] for node in result["content"]]
        assert "heading" in types
        assert "paragraph" in types
        assert "bulletList" in types
        assert "codeBlock" in types

    def test_preserves_special_characters(self) -> None:
        """Special characters are preserved."""
        result = markdown_to_adf("Test <>&\"' chars")
        text = result["content"][0]["content"][0]["text"]
        assert "<>&\"'" in text
