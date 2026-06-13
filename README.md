# feedly-mcp

MCP (Model Context Protocol) server that exposes the [Feedly Cloud API](https://developer.feedly.com/)
as tools for AI assistants.

## Setup

1. Get a Feedly developer access token from your Feedly account
   (Settings -> Developer access token).
2. Install the package:

   ```bash
   pip install .
   ```

3. Set the `FEEDLY_ACCESS_TOKEN` environment variable (see `.env.example`).

## Usage with Claude

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "feedly": {
      "command": "feedly-mcp",
      "env": {
        "FEEDLY_ACCESS_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Tools

- `get_profile` - get the authenticated user's profile
- `list_categories` - list categories/folders
- `list_subscriptions` - list subscribed feeds
- `get_unread_counts` - get unread counts per feed/category
- `get_stream_contents` - fetch articles from a feed, category or tag
- `search_feeds` - search the Feedly feed index
- `mark_entries_read` - mark article entries as read
- `mark_stream_read` - mark a whole feed/category as read
