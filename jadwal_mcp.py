from mcp.server.mcpserver import MCPServer

mcp = MCPServer("jadwal")

@mcp.tool()
def list_events(start: str, end: str) -> list:
    """List calendar events between two ISO 8601 datetimes (with timezone offset). Use this to check what's already scheduled before proposing a new event, or when the user asks what's on their calendar."""
    from jadwal_calendar import list_events as _list_events
    return _list_events(start, end)


@mcp.tool()
def create_event(title: str, start: str, end: str) -> dict:
    """Create a calendar event. Only call this AFTER the user has explicitly confirmed the exact title, start, and end time in this conversation. Use this when the user has said yes/confirmed to a proposed event — this is what actually books it."""
    from jadwal_calendar import create_event as _create_event
    return _create_event(title, start, end)


@mcp.tool()
def delete_event(title: str, start: str) -> dict:
    """Delete a calendar event. Only call this AFTER the user has confirmed the exact title and start time."""
    from jadwal_calendar import delete_event as _delete_event
    return _delete_event(title, start)


@mcp.tool()
def find_free_slot(duration_minutes: int, after: str, before: str) -> list:
    """Find open time windows of at least the given duration between two datetimes. Use this when the user asks when they're free, or asks you to find a time for something."""
    from jadwal_calendar import find_free_slot as _find_free_slot
    return _find_free_slot(duration_minutes, after, before)


if __name__ == "__main__":
    mcp.run(transport="stdio")