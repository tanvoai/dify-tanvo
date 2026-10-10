from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.common import client_for, friendly, respond, upload_files, wait, wait_seconds


def picked(params: dict[str, Any], *names: str) -> dict[str, Any]:
    """The settings the user chose; "auto" or empty means the model's default."""
    return {n: params[n] for n in names if params.get(n) not in (None, "", "auto")}


class GenerateImageTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        c = client_for(self.runtime.credentials)
        try:
            g = c.generate_image(
                tool_parameters["prompt"], model=tool_parameters.get("model") or "nano-banana-2",
                images=upload_files(c, tool_parameters.get("images")), wait=False,
                **picked(tool_parameters, "aspect", "resolution", "format"),
            )
            g = wait(c, g, wait_seconds(tool_parameters))
        except Exception as e:
            raise RuntimeError(friendly(e)) from None
        yield from respond(self, g)
