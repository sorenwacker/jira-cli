# Codebase Review

Date: 2026-06-25
Scope: `src/jira_cli/` (15 modules, 3660 LOC) plus mirrored tests. 23 files were
read by the review agents.

Method: objective baseline gates, then a multi-agent per-file review (one reviewer
per module group) followed by an adversarial verification pass that attempted to
refute every high/medium finding. Only findings that survived verification are
reported as confirmed.

## Baseline gates

All of the project's own quality gates pass. These define "flawless" for this
codebase and the review found nothing that contradicts them.

| Gate | Command | Result |
|------|---------|--------|
| Lint | `ruff check src/ tests/` | pass |
| Format | `ruff format --check src/ tests/` | pass (31 files) |
| Dead code | `vulture src tests --min-confidence 80` | pass (no hits) |
| Types | `mypy src/ tests/` | pass (no issues, 31 files) |
| Lint (supplementary) | `pylint src/ tests/` | 10.00/10 |
| Function length | `flake8` (max 32 lines) | pass |
| Tests | `pytest` | 224 passed |
| File size | max 1000 LOC | pass (largest: `shell.py`, 562) |

No TODO/FIXME/HACK markers in the source tree.

## Summary

| Severity | Confirmed | Unverified (lower-confidence) |
|----------|-----------|-------------------------------|
| High | 1 | 0 |
| Medium | 5 | 0 |
| Low | 0 | 14 |
| **Total** | **6** | **14** |

20 findings were raised; 6 survived adversarial verification, 0 were refuted, and
14 lower-confidence findings were left unverified (reported in the appendix). The
gates pass because every confirmed issue is a runtime edge case that static
analysis and the current single-path test fixtures do not exercise.

### Recurring themes

1. **Text round-trip fidelity.** Three confirmed issues are in the
   storage/ADF → plain-text rendering paths: the code-block language token leaks
   into output (`confluence_storage`), and block-level nodes are concatenated with
   no separator (`models`). The two halves of the codebase render blocks
   differently — Confluence inserts newlines on block close, the Jira ADF
   extractor does not.

2. **Null / empty / malformed input robustness.** The Confluence model crashes on
   explicit JSON `null`, the ADF converter emits an API-invalid node for an empty
   code block, and the shell crashes on a non-integer `--limit`. The Jira models
   already guard against null uniformly; the Confluence half dropped that idiom.

3. **Jira ↔ Confluence mirror drift.** The two subsystems are intentionally
   parallel (client / cli / mcp / models / storage), and several findings are
   places where the Confluence side diverges from the Jira side's defensive
   patterns. Worth treating consistency as a review axis in its own right.

## Resolution

All 6 confirmed findings (H1, M1–M5) and all 14 appendix notes (L1–L14) were
addressed on 2026-06-25. Code fixes carry regression tests; L3 and L5 were
resolved as documentation (see the Disposition column). The suite grew from 224
to 248 tests; all baseline gates still pass.

## Confirmed findings

### High

#### H1 — `readline` can be unbound, crashing the shell on Windows
`src/jira_cli/shell.py:23`

`HAS_READLINE = "readline" in sys.modules or sys.platform != "win32"`. When this is
False (Windows, readline not already imported), the `if HAS_READLINE:` block is
skipped, so module-level `readline` is never bound. The `readline = None` fallback
lives only in the `except ImportError` branch, which is unreachable on that path.
`preloop()` then runs `if readline:` unconditionally and raises
`NameError: name 'readline' is not defined` at shell startup — on exactly the
platform the guard was meant to protect. (`HAS_READLINE` is also never read again.)

Fix: bind `readline = None` at module scope before the conditional import, so the
False path leaves a defined sentinel.

### Medium

#### M1 — Code-macro language token leaks into rendered text
`src/jira_cli/confluence_storage.py:256`

`storage_to_text` does not handle the `<ac:parameter ac:name="language">…</ac:parameter>`
that `markdown_to_storage` emits for language-tagged fenced blocks. `_CDATA.sub`
extracts only the plain-text body; `_TAG.sub` strips the parameter's tags but its
inner text survives, and with no block-close newline it concatenates onto the code.
Round trip: `markdown_to_storage("```python\nprint(1)\n```")` →
`storage_to_text(...) == "pythonprint(1)"`. Reachable from this module's own output
and from any real Confluence page whose code block declares a language.
`test_code_macro_body_preserved` misses it (no language parameter; substring assert).

Fix: consume the whole `<ac:structured-macro>` code envelope (including
`ac:parameter` children) when extracting the CDATA body. Add a round-trip test with
a language-tagged block asserting equality, not substring.

#### M2 — Nested `.get()` chains crash on explicit JSON `null`
`src/jira_cli/confluence_models.py:60` (and `:84`)

`Page.from_api_response` uses `data.get("version", {}).get("number")`,
`data.get("body", {}).get("storage", {}).get("value")`,
`data.get("_links", {}).get("webui")`. The `{}` default only applies when the key
is **absent**; if the API returns the key present with `null`, `.get` returns
`None` and the next `.get` raises `AttributeError`. Same for
`from_search_result`'s `data.get("content", {})`. The sibling Jira models guard
this uniformly via `_get_display_name`/`_get_nested_name` (`field_data.get(...) if
field_data else None`); the Confluence half dropped the idiom.

Fix: guard each level with `or {}`, e.g.
`version = (data.get("version") or {}).get("number")`.

#### M3 — Empty code block emits an API-invalid ADF text node
`src/jira_cli/adf.py:188`

`_parse_code_block` always builds `content = [{"type": "text", "text": code_text}]`
even when `code_text == ""`. An empty fence (```` ```\n``` ````) yields a
`codeBlock` containing a `text` node with an empty string, which the ADF schema
disallows and the Atlassian REST API rejects (used by `add_comment` /
`create_issue` descriptions). `_parse_inline` already guards empty text nodes; the
code-block path does not.

Fix: only include the text node when `code_text` is non-empty, so an empty block
emits `{"type": "codeBlock", "content": []}`.

#### M4 — Non-integer `--limit` terminates the shell
`src/jira_cli/shell.py:73`

`_parse_shell_args` wraps only `shlex.split` in try/except. The conversion
`int(args[i + 1])` is unguarded, so `list --limit abc` raises `ValueError`, which
propagates through `do_list`/`do_new`/`do_edit` and — since `cmdloop()` is called
without a surrounding handler (`cli.py:352`) and `cmd.Cmd.onecmd` does not swallow
exceptions — unwinds the whole loop with a traceback. This contradicts the module's
explicit "shell should not crash" design (every client call carries
`# noqa: BLE001`).

Fix: guard the `int()` conversion and surface an error message instead of crashing,
matching every other user-error path.

#### M5 — ADF text extraction collapses block elements with no separator
`src/jira_cli/models.py:185`

`_extract_adf_node_text` joins child text with `""`. Block-level nodes (multiple
paragraphs, list items, headings) concatenate without whitespace: two paragraphs
`First.` and `Second.` render as `First.Second.`. Used for both `Issue.description`
and `Comment.body`. Inconsistent with the Confluence half, where `storage_to_text`
separates every block close with a newline. All conftest fixtures are
single-paragraph, so it is untested.

Fix: separate distinct block-level nodes with a newline, mirroring
`storage_to_text`'s block separation.

## Appendix — lower-confidence findings (all addressed)

These were raised by reviewers but not run through the adversarial verifier
(`verifyLow: false`). All were triaged and addressed: code fixes carry tests;
L3 and L5 were resolved as documentation.

| # | File:line | Note | Disposition |
|---|-----------|------|-------------|
| L1 | `confluence_storage.py` | `_code_macro` did not escape a `]]>` CDATA terminator; could emit malformed storage. | Fixed — split terminator, round-trip test. |
| L2 | `confluence_storage.py` | Table row cells rendered with no separator. | Fixed — cells separated by tab. |
| L3 | `confluence_models.py:47` | `Page.url` is a relative `webui` path surfaced as `url`. | Documented — field comment + CONFLUENCE.md. |
| L4 | `confluence_cli.py` | `--body ""` could not clear a page body. | Fixed — guard on `body is not None`. |
| L5 | `confluence_mcp.py` | Page/space tools lack a `confluence_` prefix. | Documented — intentional, no collision; noted in CONFLUENCE.md. |
| L6 | `adf.py` | Intra-word underscores parsed as italic. | Fixed — word-boundary guard (both converters). |
| L7 | `adf.py` | Spaced thematic break `* * *` parsed as a bullet. | Fixed — spaced-aware hrule (both converters). |
| L8 | `client.py` | Redundant `field(default=None)`. | Fixed — plain `= None`, `field` import dropped. |
| L9 | `client.py` | Search read only the first page. | Fixed — pages over `nextPageToken`, test. |
| L10 | `cli.py` | "Updated" printed even on a no-op edit. | Fixed — `update_issue` returns changed flag. |
| L11 | `cli.py` | Duplicate of L8. | Fixed with L8. |
| L12 | `mcp.py` | `__all__` mid-import-block. | Fixed — moved after imports. |
| L13 | `mcp.py` | Full issue dict omitted labels/attachments. | Fixed — both included, test. |
| L14 | `config.py` | `save_config` interpolated TOML without escaping. | Fixed — `_toml_string` escaping, round-trip test. |
