from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.common import client_for, friendly, respond, upload_files, wait, wait_seconds
from tools.generate_image import picked


class GenerateVideoTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        c = client_for(self.runtime.credentials)
        settings = picked(tool_parameters, "aspect", "resolution", "tier")
        if tool_parameters.get("duration"):
            settings["duration"] = int(tool_parameters["duration"])
        if tool_parameters.get("audio") in ("on", "off"):
            settings["audio"] = tool_parameters["audio"] == "on"
        try:
            start = upload_files(c, [tool_parameters.get("start_image")])
            end = upload_files(c, [tool_parameters.get("end_image")])
            g = c.generate_video(
                tool_parameters["prompt"], model=tool_parameters.get("model") or "kling-3-0", wait=False,
                image=start[0] if start else None, end_image=end[0] if end else None, **settings,
            )
            g = wait(c, g, wait_seconds(tool_parameters))
        except Exception as e:
            raise RuntimeError(friendly(e)) from None
        yield from respond(self, g)
