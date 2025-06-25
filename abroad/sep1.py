from rest_framework.request import Request
from polaris.integrations.toml import get_stellar_toml

def return_toml_contents(request, *args, **kwargs):
    toml = get_stellar_toml(request, *args, **kwargs)
    return {
        "ORG_NAME": "Abroad.Finance",
        "ORG_DBA": "Abroad Financial Technologies Ltd.",
        "ORG_URL": "https://abroad.finance",
        "ORG_LOGO": "https://storage.googleapis.com/cdn-abroad/Icons/Favicon/Abroad_Badge_transparent.png",
        "ORG_DESCRIPTION": "Abroad.Finance is a financial technology company that provides a platform for users to buy and sell cryptocurrencies and fiat currencies. We aim to make cross-border transactions easier and more accessible for everyone.",
        "ORG_PHYSICAL_ADDRESS": "14 East Bay Lane, London, UK. E15 2GW.",
        "ORG_PHYSICAL_ADDRESS_ATTESTATION": "N/A",
        "ORG_PHONE_NUMBER": "+44 75646 00109",
        "ORG_PHONE_NUMBER_ATTESTATION": "N/A",
        "ORG_TWITTER": "https://x.com/payabroad",
        "ORG_GITHUB": "https://github.com/abroad-finance/abroad",
        "ORG_OFFICIAL_EMAIL": "support@abroad.finance",
        "ORG_SUPPORT_EMAIL": "support@abroad.finance",
        "ORG_LICENSING_AUTHORITY": "N/A",
        "ORG_LICENSE_TYPE": "N/A",
        "ORG_LICENSE_NUMBER": "N/A",
        **toml,
    }
