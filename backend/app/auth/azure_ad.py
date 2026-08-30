"""Azure AD (Entra ID) OAuth 2.0 helpers via MSAL."""

from __future__ import annotations

import msal

from app.config import settings

AUTHORITY = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}"
# User.Read is enough to resolve the signed-in user's identity claims.
SCOPES = ["User.Read"]


def _app() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        settings.AZURE_AD_CLIENT_ID,
        authority=AUTHORITY,
        client_credential=settings.AZURE_AD_CLIENT_SECRET,
    )


def get_authorization_url(state: str) -> str:
    return _app().get_authorization_request_url(
        SCOPES,
        redirect_uri=settings.AZURE_AD_REDIRECT_URI,
        state=state,
    )


def acquire_token_by_code(code: str) -> dict:
    result = _app().acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=settings.AZURE_AD_REDIRECT_URI,
    )
    if "error" in result:
        raise RuntimeError(
            result.get("error_description") or result.get("error") or "Azure AD login failed"
        )
    return result
