import asyncio
import json
import os

import requests
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

FEEDLY_API_BASE = "https://cloud.feedly.com/v3"

server = Server("feedly-mcp")

_profile_cache: dict | None = None


def _token() -> str:
    token = os.environ.get("FEEDLY_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("FEEDLY_ACCESS_TOKEN environment variable is not set")
    return token


def _request(method: str, path: str, **kwargs) -> dict:
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"OAuth {_token()}"
    resp = requests.request(method, f"{FEEDLY_API_BASE}{path}", headers=headers, timeout=30, **kwargs)
    resp.raise_for_status()
    return resp.json() if resp.content else {}


def _user_id() -> str:
    global _profile_cache
    if _profile_cache is None:
        _profile_cache = _request("GET", "/profile")
    return _profile_cache["id"]


def _resolve_stream_id(stream_id: str) -> str:
    """Allow shorthand category/tag names by expanding them to the user's stream id."""
    if "/" in stream_id:
        return stream_id
    return f"user/{_user_id()}/category/{stream_id}"


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_profile",
            description="Get the authenticated Feedly user's profile information.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_categories",
            description="List the user's Feedly categories (folders).",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_subscriptions",
            description="List the feeds the user is subscribed to.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_unread_counts",
            description="Get unread article counts per feed/category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "autorefresh": {
                        "type": "boolean",
                        "description": "Force a refresh of the counts before returning them.",
                    }
                },
            },
        ),
        Tool(
            name="get_stream_contents",
            description=(
                "Fetch articles from a feed, category or tag. 'stream_id' can be a full "
                "Feedly stream id (e.g. 'feed/http://example.com/rss' or "
                "'user/<id>/category/<name>'), or a shorthand category/tag name which "
                "will be resolved against the current user."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "stream_id": {"type": "string", "description": "Feed, category or tag id."},
                    "count": {"type": "integer", "description": "Number of entries to return (default 20)."},
                    "unread_only": {"type": "boolean", "description": "Only return unread entries."},
                    "continuation": {"type": "string", "description": "Pagination token from a previous call."},
                },
                "required": ["stream_id"],
            },
        ),
        Tool(
            name="search_feeds",
            description="Search for feeds in the Feedly index by name, URL or topic.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query, e.g. a topic or site name."},
                    "count": {"type": "integer", "description": "Maximum number of results (default 10)."},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="mark_entries_read",
            description="Mark one or more article entry ids as read.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of entry ids to mark as read.",
                    }
                },
                "required": ["entry_ids"],
            },
        ),
        Tool(
            name="mark_stream_read",
            description="Mark all entries in a feed or category as read.",
            inputSchema={
                "type": "object",
                "properties": {
                    "stream_id": {"type": "string", "description": "Feed or category id (or shorthand category name)."},
                },
                "required": ["stream_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    arguments = arguments or {}

    if name == "get_profile":
        result = _request("GET", "/profile")

    elif name == "list_categories":
        result = _request("GET", "/categories")

    elif name == "list_subscriptions":
        result = _request("GET", "/subscriptions")

    elif name == "get_unread_counts":
        params = {}
        if arguments.get("autorefresh"):
            params["autorefresh"] = "true"
        result = _request("GET", "/markers/counts", params=params)

    elif name == "get_stream_contents":
        params = {
            "streamId": _resolve_stream_id(arguments["stream_id"]),
            "count": arguments.get("count", 20),
        }
        if arguments.get("unread_only"):
            params["unreadOnly"] = "true"
        if arguments.get("continuation"):
            params["continuation"] = arguments["continuation"]
        result = _request("GET", "/streams/contents", params=params)

    elif name == "search_feeds":
        params = {"query": arguments["query"], "count": arguments.get("count", 10)}
        result = _request("GET", "/search/feeds", params=params)

    elif name == "mark_entries_read":
        _request(
            "POST",
            "/markers",
            json={"action": "markAsRead", "type": "entries", "entryIds": arguments["entry_ids"]},
        )
        result = {"status": "ok"}

    elif name == "mark_stream_read":
        _request(
            "POST",
            "/markers",
            json={
                "action": "markAsRead",
                "type": "feeds",
                "feedIds": [_resolve_stream_id(arguments["stream_id"])],
            },
        )
        result = {"status": "ok"}

    else:
        raise ValueError(f"Unknown tool: {name}")

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
