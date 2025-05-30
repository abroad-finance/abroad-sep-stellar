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




usdc = Asset.objects.all().delete()
usdc = Asset.objects.filter(code="USDC").first()
if usdc is None:
    usdc = Asset()
    usdc.code = "USDC"
    usdc.issuer = "GBJ73BHEWY2WJPDYO5JTLY24ORCUSWU2LFY44GVZDHAFRBWZAAQSYMAH"
    usdc.sep38_enabled = True
    usdc.sep24_enabled = True
    usdc.sep31_enabled = True
    usdc.sep6_enabled = True
    usdc.withdrawal_enabled = True
    usdc.deposit_enabled = False
    usdc.save()
    
delivery_method = DeliveryMethod.objects.filter(name="TRANSFIYA").first()
if delivery_method is None:
    delivery_method = DeliveryMethod()
    delivery_method.type = "buy"
    delivery_method.description = "Transfiya"
    delivery_method.name = "TRANSFIYA"
    delivery_method.save()
    
    
    
offchain_asset = OffChainAsset.objects.filter(identifier="COP").first()
if offchain_asset is None:
    offchain_asset = OffChainAsset()
    offchain_asset.country_codes = ["CO"]
    offchain_asset.identifier = "COP"
    offchain_asset.symbol = "COP"
    offchain_asset.scheme = "iso4217"
    offchain_asset.save()
    offchain_asset.delivery_methods.set([delivery_method]) 

exchange_pair = ExchangePair.objects.filter(buy_asset=offchain_asset, sell_asset=usdc).first()
if exchange_pair is None:
    exchange_pair = ExchangePair()
    exchange_pair.buy_asset = offchain_asset
    exchange_pair.sell_asset = usdc
    exchange_pair.save()