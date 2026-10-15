import json
import sys
from pathlib import Path

LECTURES = json.loads((Path(__file__).parent / "lectures.json").read_text(encoding="utf-8"))

TOOLS = [
    {
        "name": "find_lecture",
        "description": "Look up a single course lecture by its number (integer 1–10) and return its exact title and list of topics. Call this whenever the user asks what a specific lecture covers, is about, or teaches.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "number": {"type": "integer", "description": "Lecture number, 1 to 10"},
            },
            "required": ["number"],
        },
    },
    {
        "name": "search_lectures",
        "description": "Search the course lectures for a keyword and return the number and title of every lecture whose title or topics contain it. Use it when asked which lecture covers a subject.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Word or phrase to look for, e.g. MCP or testing"},
            },
            "required": ["query"],
        },
    },
]


def send(reply):
    print(json.dumps(reply, separators=(",", ":")), flush=True)


def text_result(id, text, is_error):
    return {
        "jsonrpc": "2.0",
        "id": id,
        "result": {"content": [{"type": "text", "text": text}], "isError": is_error}
    }


def error_reply(id, code, message):
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def handle(msg):
    method = msg.get("method")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg["id"],
            "result": {
                "protocolVersion": msg.get("params", {}).get("protocolVersion"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "lectures", "version": "0.1.0"},
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg["id"], "result": {"tools": TOOLS}}

    if method == "tools/call":
        name = msg["params"]["name"]
        args = msg["params"].get("arguments", {})

        if name == "find_lecture":
            lecture = next((l for l in LECTURES if l["number"] == args.get("number")), None)
            if lecture is None:
                return text_result(msg["id"], f"There is no lecture {args.get('number')}. The course has lectures 1 to 10.", True)
            return text_result(msg["id"], f"Lecture {lecture['number']}: {lecture['title']}. Topics: {lecture['topics']}", False)

        if name == "search_lectures":
            query = args.get("query", "").lower()
            found = [l for l in LECTURES if query in l["title"].lower() or query in l["topics"].lower()]
            if not found:
                return text_result(msg["id"], f"No lecture mentions \"{args.get('query', '')}\".", False)
            return text_result(msg["id"], "\n".join(f"{l['number']}. {l['title']}" for l in found), False)

        return error_reply(msg["id"], -32602, f"Unknown tool: {name}")

    if "id" in msg:
        return error_reply(msg["id"], -32601, f"Unknown method: {method}")

    return None


def main():
    for line in sys.stdin:
        line = line.rstrip("\n")
        print(f"got: {line}", file=sys.stderr)

        reply = handle(json.loads(line))
        if reply is not None:
            send(reply)


if __name__ == '__main__':
    main()
