from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.common import client_for, friendly


class ListAppsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        kind = tool_parameters.get("kind") or "all"
        try:
            apps = client_for(self.runtime.credentials).apps(None if kind == "all" else kind)
        except Exception as e:
            raise RuntimeError(friendly(e)) from None
        rows = [
            {
                "app": a.slug, "kind": a.kind, "name": a.name, "description": a.description, "page": a.url,
                "photos": [{"label": i.label, "required": i.min > 0, "max": i.max} for i in a.inputs],
                "looks": [{"look": l.id, "name": l.name} for l in a.looks],
            }
            for a in apps
        ]
        yield self.create_json_message({"apps": rows})
        yield self.create_variable_message("apps", rows)
