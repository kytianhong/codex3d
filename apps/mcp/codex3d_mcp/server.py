from __future__ import annotations

import json
import sys
from typing import Any, BinaryIO

from .tools import McpToolService


SERVER_NAME = "codex3d-mcp"
SERVER_VERSION = "0.1.0"
LATEST_PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = {LATEST_PROTOCOL_VERSION, "2025-03-26", "2024-11-05"}
MAX_MESSAGE_BYTES = 2 * 1024 * 1024


class Codex3DMcpServer:
    def __init__(self, tool_service: McpToolService | None = None) -> None:
        self.tool_service = tool_service or McpToolService()

    def handle_message(self, message: Any) -> dict[str, Any] | None:
        if not isinstance(message, dict):
            return self._jsonrpc_error(None, -32600, "Invalid Request")
        request_id = message.get("id")
        method = message.get("method")
        if message.get("jsonrpc") != "2.0" or not isinstance(method, str):
            return self._jsonrpc_error(request_id, -32600, "Invalid Request")
        if request_id is None:
            return None
        params = message.get("params", {})
        try:
            if method == "initialize":
                return self._result(request_id, self._initialize(params))
            if method == "ping":
                return self._result(request_id, {})
            if method == "tools/list":
                return self._result(request_id, {"tools": self.tool_service.list_tools()})
            if method == "tools/call":
                return self._result(request_id, self._call_tool(params))
            return self._jsonrpc_error(request_id, -32601, "Method not found")
        except Exception:
            return self._jsonrpc_error(request_id, -32603, "Internal error")

    def handle_line(self, line: bytes) -> dict[str, Any] | None:
        if len(line) > MAX_MESSAGE_BYTES:
            return self._jsonrpc_error(None, -32600, "Request exceeds 2 MiB limit")
        try:
            message = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._jsonrpc_error(None, -32700, "Parse error")
        return self.handle_message(message)

    def run(self, stdin: BinaryIO | None = None, stdout: BinaryIO | None = None) -> int:
        input_stream = stdin or sys.stdin.buffer
        output_stream = stdout or sys.stdout.buffer
        for line in input_stream:
            response = self.handle_line(line)
            if response is None:
                continue
            output_stream.write(json.dumps(response, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
            output_stream.flush()
        return 0

    def _initialize(self, params: Any) -> dict[str, Any]:
        requested = params.get("protocolVersion") if isinstance(params, dict) else None
        protocol_version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
        return {
            "protocolVersion": protocol_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": "Use the structured Blender tools. Distances are meters, rotations are Euler radians, and colors are linear values in [0,1]. Inspect before editing unfamiliar scenes.",
        }

    def _call_tool(self, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict) or not isinstance(params.get("name"), str):
            payload = {"ok": False, "error": {"code": "invalid_arguments", "message": "tools/call requires name and arguments.", "details": {}}}
        else:
            payload = self.tool_service.call_tool(params["name"], params.get("arguments", {}))
        image_content = payload.pop("_mcp_image", None)
        text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        content = [{"type": "text", "text": text}]
        if isinstance(image_content, dict):
            content.append(image_content)
        return {
            "content": content,
            "structuredContent": payload,
            "isError": not bool(payload.get("ok")),
        }

    def _result(self, request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _jsonrpc_error(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def main() -> int:
    return Codex3DMcpServer().run()
