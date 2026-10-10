from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from tools.common import client_for, friendly


class TanvoProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """Checks the key with a free call (the account endpoint); never runs a generation."""
        key = (credentials.get("tanvo_api_key") or "").strip()
        if not key:
            raise ToolProviderCredentialValidationError("Enter your Tanvo API key.")
        try:
            client_for(credentials).me()
        except Exception as e:
            raise ToolProviderCredentialValidationError(friendly(e)) from None
