def truncate_messages(messages: list[dict], max_messages: int = 50) -> list[dict]:
    """Keep the most recent messages within the limit.

    Truncation never splits a tool-call/tool-result pair: if the oldest kept message
    is a tool result, we drop it too (its matching assistant message is already gone).
    """
    if len(messages) <= max_messages:
        return messages

    truncated = messages[-max_messages:]
    # Drop any leading tool-result messages that lost their assistant pair
    while truncated and truncated[0].get("role") == "tool":
        truncated = truncated[1:]
    return truncated
