import os
import sys # Import the sys module
import django

# Add the project root directory to the Python path
# This ensures that the 'abroad' module (containing settings.py) can be found.
# __file__ refers to the current script: /workspaces/abroad-polaris/scripts/assets.py
# os.path.dirname(__file__) is its directory: /workspaces/abroad-polaris/scripts
# os.path.dirname(os.path.dirname(__file__)) is the project root: /workspaces/abroad-polaris
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT) # Insert at the beginning of the path

# Set the environment variable for Django settings
# Ensure 'abroad.settings' is the correct Python path to your settings file.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abroad.settings')

# Initialize Django settings and applications
django.setup()

from polaris.models import Asset, OffChainAsset, DeliveryMethod, ExchangePair

Asset.objects.all().delete() # This line is kept from original

print("Starting asset setup/update...")

# USDC Asset
usdc, created = Asset.objects.update_or_create(
    code="USDC",
    issuer="GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN",
    defaults={
        "sep38_enabled": True,
        "sep24_enabled": True,
        "sep31_enabled": True,
        "sep6_enabled": True,
        "withdrawal_max_amount": 800,
        "withdrawal_min_amount": 1,
        "withdrawal_enabled": True,
        "deposit_enabled": False,  # As per original script
    }
)
if created:
    print(f"Asset {usdc.code} (Issuer: {usdc.issuer}) created.")
else:
    print(f"Asset {usdc.code} (Issuer: {usdc.issuer}) updated/verified.")

# DeliveryMethod
delivery_method, created = DeliveryMethod.objects.update_or_create(
    name="TRANSFIYA",
    defaults={
        "type": "buy",
        "description": "Transfiya",
    }
)
if created:
    print(f"DeliveryMethod {delivery_method.name} created.")
else:
    print(f"DeliveryMethod {delivery_method.name} updated/verified.")

# OffChainAsset (COP)
offchain_asset, created = OffChainAsset.objects.update_or_create(
    identifier="COP",
    defaults={
        "country_codes": ["CO"],
        "symbol": "COP",
        "scheme": "iso4217",
    }
)
if created:
    print(f"OffChainAsset {offchain_asset.identifier} created.")
else:
    print(f"OffChainAsset {offchain_asset.identifier} updated/verified.")

# Associate DeliveryMethod with OffChainAsset
if offchain_asset and delivery_method:
    if not offchain_asset.delivery_methods.filter(pk=delivery_method.pk).exists():
        offchain_asset.delivery_methods.add(delivery_method)
        print(f"Associated {delivery_method.name} with {offchain_asset.identifier}.")
    else:
        print(f"{delivery_method.name} already associated with {offchain_asset.identifier}.")
elif not offchain_asset:
    print("Error: OffChainAsset 'COP' could not be created/fetched, cannot associate delivery method.")
elif not delivery_method:
    print("Error: DeliveryMethod 'TRANSFIYA' could not be created/fetched, cannot associate with OffChainAsset.")


# ExchangePair
if usdc and offchain_asset:
    exchange_pair, created = ExchangePair.objects.update_or_create(
        buy_asset=offchain_asset,
        sell_asset=usdc,
        defaults={}  # No other defaults specified in original script for the pair itself
    )
    if created:
        print(f"ExchangePair {offchain_asset.identifier}/{usdc.code} created.")
    else:
        print(f"ExchangePair {offchain_asset.identifier}/{usdc.code} updated/verified.")
else:
    print("Error: Cannot create/update ExchangePair due to missing dependent assets (USDC or COP).")

print("Asset setup/update finished.")