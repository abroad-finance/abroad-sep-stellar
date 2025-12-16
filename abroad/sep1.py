from rest_framework.request import Request

from polaris import settings as polaris_settings
from polaris.integrations.toml import get_stellar_toml
from polaris.models import Asset


def _build_accounts():
    accounts = []
    for asset in Asset.objects.all():
        account = asset.distribution_account or asset.issuer
        if account:
            accounts.append(account)
    if polaris_settings.SIGNING_KEY:
        accounts.append(polaris_settings.SIGNING_KEY)

    unique_accounts = []
    seen = set()
    for account in accounts:
        if account not in seen:
            unique_accounts.append(account)
            seen.add(account)
    return unique_accounts


def return_toml_contents(request: Request, *args, **kwargs):
    toml = get_stellar_toml(request, *args, **kwargs)
    toml["ACCOUNTS"] = _build_accounts()
    toml["DOCUMENTATION"] = {
        "ORG_NAME": "Abroad.Finance",
        "ORG_DBA": "Abroad Financial Technologies Ltd.",
        "ORG_URL": "https://abroad.finance",
        "ORG_LOGO": "https://storage.googleapis.com/cdn-abroad/Icons/Favicon/Abroad_Badge_transparent.png",
        "ORG_DESCRIPTION": "Abroad.Finance is a financial technology company that provides a platform for users to buy and sell cryptocurrencies and fiat currencies. We aim to make cross-border transactions easier and more accessible for everyone.",
        "ORG_PHYSICAL_ADDRESS": "14 East Bay Lane, London, UK. E15 2GW.",
        "ORG_PHYSICAL_ADDRESS_ATTESTATION": "https://abroad.finance",
        "ORG_PHONE_NUMBER": "+44 75646 00109",
        "ORG_PHONE_NUMBER_ATTESTATION": "https://abroad.finance",
        "ORG_TWITTER": "https://x.com/payabroad",
        "ORG_GITHUB": "https://github.com/abroad-finance/abroad",
        "ORG_OFFICIAL_EMAIL": "support@abroad.finance",
        "ORG_SUPPORT_EMAIL": "support@abroad.finance",
        "ORG_LICENSING_AUTHORITY": "N/A",
        "ORG_LICENSE_TYPE": "N/A",
        "ORG_LICENSE_NUMBER": "N/A",
    }
    return toml
