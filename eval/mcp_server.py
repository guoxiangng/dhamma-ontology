"""Serve system B's or system C's tools over MCP (stdio), so headless Claude Code can call them.

    python eval/mcp_server.py B    # search_suttas, read_sutta, list_suttas
    python eval/mcp_server.py C    # list_concepts, lookup, word_senses, read_passages, coverage

The tools are the same functions as in systems.py; nothing else in the repo (the answer key
included) is reachable through them.
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcp.server.mcpserver import MCPServer  # noqa: E402

import systems as S  # noqa: E402

WHICH = sys.argv[1] if len(sys.argv) > 1 else ""
if WHICH not in ("B", "C"):
    sys.exit("usage: mcp_server.py B|C")

with contextlib.redirect_stdout(sys.stderr):  # stdout is the MCP channel; keep it clean while building
    impl = S.TextTools() if WHICH == "B" else S.OntologyTools()
desc = {t["name"]: t["description"] for t in impl.TOOLS}
server = MCPServer("suttas" if WHICH == "B" else "ontology")

if WHICH == "B":
    @server.tool(description=desc["search_suttas"])
    def search_suttas(query: str, limit: int = 10) -> str:
        return impl.call("search_suttas", {"query": query, "limit": limit})

    @server.tool(description=desc["read_sutta"])
    def read_sutta(uid: str) -> str:
        return impl.call("read_sutta", {"uid": uid})

    @server.tool(description=desc["list_suttas"])
    def list_suttas() -> str:
        return impl.call("list_suttas", {})
else:
    @server.tool(description=desc["list_concepts"])
    def list_concepts() -> str:
        return impl.call("list_concepts", {})

    @server.tool(description=desc["lookup"])
    def lookup(term: str) -> str:
        return impl.call("lookup", {"term": term})

    @server.tool(description=desc["word_senses"])
    def word_senses(word: str) -> str:
        return impl.call("word_senses", {"word": word})

    @server.tool(description=desc["read_passages"])
    def read_passages(segments: list[str]) -> str:
        return impl.call("read_passages", {"segments": segments})

    @server.tool(description=desc["coverage"])
    def coverage(uid: str = "") -> str:
        return impl.call("coverage", {"uid": uid})

if __name__ == "__main__":
    server.run("stdio")
