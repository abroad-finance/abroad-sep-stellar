from rest_framework.request import Request

def return_toml_contents(request, *args, **kwargs):
    return {
        "DOCUMENTATION": {
            "ORG_NAME": "Abroad",
            "ORG_URL": "https://abroad.finance",
            "ORG_LOGO": "...",
            "ORG_DESCRIPTION": "...",
            "ORG_OFFICIAL_EMAIL": "...",
            "ORG_SUPPORT_EMAIL": "..."
        },
    }