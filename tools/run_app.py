from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.common import client_for, friendly, respond, upload_files, wait, wait_seconds


class RunAppTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        c = client_for(self.runtime.credentials)
        try:
            g = c.generate_from_app(
                tool_parameters["app"].strip(), look=(tool_parameters.get("look") or "").strip() or None,
                photos=upload_files(c, tool_parameters.get("photos")),
                details=(tool_parameters.get("details") or "").strip() or None, wait=False,
            )
            g = wait(c, g, wait_seconds(tool_parameters))
        except KeyError as e:
            raise RuntimeError(f"Tanvo: {e.args[0]} Use List Apps to see the app ids and their looks.") from None
        except Exception as e:
            raise RuntimeError(friendly(e)) from None
        yield from respond(self, g)
