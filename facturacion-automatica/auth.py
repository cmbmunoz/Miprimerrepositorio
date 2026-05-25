import msal
from config import AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET

_app = None


def _get_app():
    global _app
    if _app is None:
        authority = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
        _app = msal.ConfidentialClientApplication(
            AZURE_CLIENT_ID,
            authority=authority,
            client_credential=AZURE_CLIENT_SECRET,
        )
    return _app


def get_token() -> str:
    app = _get_app()
    result = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in result:
        error = result.get("error_description") or result.get("error") or "unknown"
        raise RuntimeError(f"No se pudo obtener token de Microsoft 365: {error}")
    return result["access_token"]
