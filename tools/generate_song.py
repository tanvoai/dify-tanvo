from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.common import client_for, friendly, respond, wait, wait_seconds


class GenerateSongTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        c = client_for(self.runtime.credentials)
        try:
            g = c.generate_music(
                tool_parameters["prompt"], mode=tool_parameters.get("mode") or "Describe",
                style=(tool_parameters.get("style") or "").strip() or None, title=(tool_parameters.get("title") or "").strip() or None,
                wait=False,
            )
            g = wait(c, g, wait_seconds(tool_parameters))
        except Exception as e:
            raise RuntimeError(friendly(e)) from None
        yield from respond(self, g)
