# Confluence CLI

The `confluence` command manages Confluence Cloud pages with the same credentials as `jira` (see [Configuration](../getting-started/configuration.md#confluence-resolution-order)).

## Search

Searches content using CQL (Confluence Query Language):

```bash
confluence search "text ~ 'roadmap'"
confluence search "space = DEV and type = page" --limit 10
```

Search results include the numeric page ID needed by the page commands.

## Spaces

```bash
confluence space list
confluence space list --limit 50
```

## Pages

```bash
confluence page 12345            # rendered to plain text
confluence page 12345 --raw      # raw storage-format XHTML

confluence create --space DEV --title "Release notes" --body "# Heading"
confluence create --space DEV --title "Child" --file notes.md --parent 12345

confluence update 12345 --title "New title"
confluence update 12345 --file notes.md
```

Page bodies are written in [markdown](../reference/markdown.md#confluence-storage-format) and converted to Confluence storage format.
