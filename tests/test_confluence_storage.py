"""Tests for markdown to Confluence storage format conversion."""

from jira_cli.confluence_storage import markdown_to_storage, storage_to_text


class TestMarkdownToStorage:
    """Tests for converting markdown to storage format."""

    def test_empty_text(self) -> None:
        """Empty text produces empty storage."""
        assert markdown_to_storage("") == ""
        assert markdown_to_storage("   ") == ""

    def test_paragraph(self) -> None:
        """Plain text becomes a paragraph."""
        assert markdown_to_storage("Hello world") == "<p>Hello world</p>"

    def test_heading(self) -> None:
        """Headings map to h1-h6."""
        assert markdown_to_storage("# Title") == "<h1>Title</h1>"
        assert markdown_to_storage("### Sub") == "<h3>Sub</h3>"

    def test_bold_and_italic(self) -> None:
        """Bold and italic inline marks are converted."""
        result = markdown_to_storage("This is **bold** and *italic*")
        assert "<strong>bold</strong>" in result
        assert "<em>italic</em>" in result

    def test_inline_code(self) -> None:
        """Inline code is wrapped in a code element."""
        assert "<code>x = 1</code>" in markdown_to_storage("Run `x = 1` now")

    def test_link(self) -> None:
        """Links become anchor elements."""
        result = markdown_to_storage("See [docs](https://example.com)")
        assert '<a href="https://example.com">docs</a>' in result

    def test_bullet_list(self) -> None:
        """Bullet lists become ul/li."""
        result = markdown_to_storage("- one\n- two")
        assert result == "<ul><li>one</li><li>two</li></ul>"

    def test_ordered_list(self) -> None:
        """Ordered lists become ol/li."""
        result = markdown_to_storage("1. one\n2. two")
        assert result == "<ol><li>one</li><li>two</li></ol>"

    def test_task_list(self) -> None:
        """Checkbox items become a Confluence task-list macro."""
        result = markdown_to_storage("- [ ] todo\n- [x] done")
        assert "<ac:task-list>" in result
        assert "<ac:task-status>incomplete</ac:task-status>" in result
        assert "<ac:task-status>complete</ac:task-status>" in result
        assert "<ac:task-body>todo</ac:task-body>" in result
        assert "<ac:task-body>done</ac:task-body>" in result

    def test_task_list_not_treated_as_bullet(self) -> None:
        """A checkbox item is not converted to a plain bullet list."""
        result = markdown_to_storage("- [ ] todo")
        assert "<ul>" not in result

    def test_task_body_supports_inline(self) -> None:
        """Inline formatting inside a task body is converted."""
        result = markdown_to_storage("- [x] read **docs**")
        assert "<ac:task-body>read <strong>docs</strong></ac:task-body>" in result

    def test_code_block_uses_code_macro(self) -> None:
        """Fenced code blocks use the Confluence code macro."""
        result = markdown_to_storage("```python\nprint('hi')\n```")
        assert 'ac:name="code"' in result
        assert 'ac:name="language">python' in result
        assert "print('hi')" in result

    def test_horizontal_rule(self) -> None:
        """A horizontal rule becomes hr."""
        assert "<hr/>" in markdown_to_storage("---")

    def test_special_characters_escaped(self) -> None:
        """Reserved XML characters in text are escaped."""
        result = markdown_to_storage("a < b & c > d")
        assert "&lt;" in result
        assert "&amp;" in result
        assert "&gt;" in result


class TestStorageToText:
    """Tests for rendering storage format to plain text."""

    def test_strips_tags(self) -> None:
        """Tags are removed, leaving text."""
        text = storage_to_text("<p>Page <strong>body</strong> text</p>")
        assert text == "Page body text"

    def test_unescapes_entities(self) -> None:
        """XML entities are decoded."""
        assert storage_to_text("<p>a &lt; b &amp; c</p>") == "a < b & c"

    def test_paragraphs_separated_by_newlines(self) -> None:
        """Block elements produce line breaks."""
        text = storage_to_text("<p>one</p><p>two</p>")
        assert "one" in text
        assert "two" in text
        assert "\n" in text

    def test_code_macro_body_preserved(self) -> None:
        """Code macro plain-text body is preserved."""
        storage = (
            '<ac:structured-macro ac:name="code">'
            "<ac:plain-text-body><![CDATA[print('hi')]]></ac:plain-text-body>"
            "</ac:structured-macro>"
        )
        assert "print('hi')" in storage_to_text(storage)

    def test_task_list_rendered_with_checkboxes(self) -> None:
        """Task list items render as bracketed checkboxes."""
        storage = (
            "<ac:task-list>"
            "<ac:task><ac:task-id>1</ac:task-id>"
            "<ac:task-status>incomplete</ac:task-status>"
            "<ac:task-body>todo</ac:task-body></ac:task>"
            "<ac:task><ac:task-id>2</ac:task-id>"
            "<ac:task-status>complete</ac:task-status>"
            "<ac:task-body>done</ac:task-body></ac:task>"
            "</ac:task-list>"
        )
        text = storage_to_text(storage)
        assert "[ ] todo" in text
        assert "[x] done" in text

    def test_empty_input(self) -> None:
        """Empty or None input renders as empty string."""
        assert storage_to_text("") == ""
        assert storage_to_text(None) == ""
