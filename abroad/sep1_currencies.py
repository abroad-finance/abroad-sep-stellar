from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Mapping, Tuple

from stellar_sdk.strkey import StrKey

from polaris.models import Asset

_ALLOWED_STATUSES = {"live", "dead", "test", "private"}
_ALLOWED_ANCHOR_ASSET_TYPES = {
    "fiat",
    "crypto",
    "nft",
    "stock",
    "bond",
    "commodity",
    "realestate",
    "other",
}

_KNOWN_CURRENCY_FIELDS = {
    "code",
    "issuer",
    "contract",
    "code_template",
    "status",
    "display_decimals",
    "name",
    "desc",
    "conditions",
    "image",
    "fixed_number",
    "max_number",
    "is_unlimited",
    "is_asset_anchored",
    "anchor_asset_type",
    "anchor_asset",
    "attestation_of_reserve",
    "redemption_instructions",
    "collateral_addresses",
    "collateral_address_messages",
    "collateral_address_signatures",
    "regulated",
    "approval_server",
    "approval_criteria",
}

_ANCHOR_TESTS_REQUIRED_FIELDS = {
    "is_asset_anchored",
    "anchor_asset_type",
    "code",
    "desc",
    "status",
}


def _require_string(
    value: Any, *, field: str, max_length: int | None = None
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"'{field}' must be a non-empty string")
    if max_length is not None and len(value) > max_length:
        raise ValueError(f"'{field}' must be <= {max_length} characters")
    return value


def _optional_string(
    data: Mapping[str, Any], *, field: str, max_length: int | None = None
) -> None:
    if field not in data or data[field] is None:
        return
    _require_string(data[field], field=field, max_length=max_length)


def _optional_bool(data: Mapping[str, Any], *, field: str) -> None:
    if field not in data or data[field] is None:
        return
    if not isinstance(data[field], bool):
        raise ValueError(f"'{field}' must be a boolean")


def _optional_int(
    data: Mapping[str, Any], *, field: str, min_value: int | None = None, max_value: int | None = None
) -> None:
    if field not in data or data[field] is None:
        return
    value = data[field]
    if not isinstance(value, int):
        raise ValueError(f"'{field}' must be an integer")
    if min_value is not None and value < min_value:
        raise ValueError(f"'{field}' must be >= {min_value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"'{field}' must be <= {max_value}")


def _optional_list_of_strings(data: Mapping[str, Any], *, field: str) -> None:
    if field not in data or data[field] is None:
        return
    value = data[field]
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"'{field}' must be a list of non-empty strings")


def validate_currency_entry(
    raw_entry: Mapping[str, Any], *, strict: bool = True
) -> Dict[str, Any]:
    """
    Validates a SEP-1 [[CURRENCIES]] entry.

    Required:
    - code (<= 12 chars)
    - exactly one of issuer (Stellar Asset) or contract (SEP-41 token)
    """
    if not isinstance(raw_entry, Mapping):
        raise ValueError("currency entry must be an object")

    entry: Dict[str, Any] = dict(raw_entry)

    if strict:
        unknown = sorted(set(entry.keys()) - _KNOWN_CURRENCY_FIELDS)
        if unknown:
            raise ValueError(f"unknown field(s): {', '.join(unknown)}")

    entry["code"] = _require_string(entry.get("code"), field="code", max_length=12)

    issuer = entry.get("issuer")
    contract = entry.get("contract")
    if issuer and contract:
        raise ValueError("only one of 'issuer' or 'contract' can be set")
    if not issuer and not contract:
        raise ValueError("one of 'issuer' (Stellar Asset) or 'contract' (SEP-41 token) must be set")

    if issuer is not None:
        issuer = _require_string(issuer, field="issuer")
        if not StrKey.is_valid_ed25519_public_key(issuer):
            raise ValueError("'issuer' must be a valid Stellar public key (G...)")

    if contract is not None:
        contract = _require_string(contract, field="contract")
        if not StrKey.is_valid_contract(contract):
            raise ValueError("'contract' must be a valid Stellar contract ID (C...)")

    _optional_string(entry, field="code_template", max_length=12)

    status = entry.get("status")
    if status is not None:
        status = _require_string(status, field="status")
        if status not in _ALLOWED_STATUSES:
            raise ValueError(f"'status' must be one of {sorted(_ALLOWED_STATUSES)}")

    _optional_int(entry, field="display_decimals", min_value=0, max_value=7)
    _optional_string(entry, field="name", max_length=20)
    _optional_string(entry, field="desc")
    _optional_string(entry, field="conditions")
    _optional_string(entry, field="image")
    _optional_int(entry, field="fixed_number", min_value=0)
    _optional_int(entry, field="max_number", min_value=0)
    _optional_bool(entry, field="is_unlimited")
    _optional_bool(entry, field="is_asset_anchored")

    anchor_asset_type = entry.get("anchor_asset_type")
    if anchor_asset_type is not None:
        anchor_asset_type = _require_string(anchor_asset_type, field="anchor_asset_type")
        if anchor_asset_type not in _ALLOWED_ANCHOR_ASSET_TYPES:
            raise ValueError(
                f"'anchor_asset_type' must be one of {sorted(_ALLOWED_ANCHOR_ASSET_TYPES)}"
            )

    _optional_string(entry, field="anchor_asset")
    _optional_string(entry, field="attestation_of_reserve")
    _optional_string(entry, field="redemption_instructions")

    _optional_list_of_strings(entry, field="collateral_addresses")
    _optional_list_of_strings(entry, field="collateral_address_messages")
    _optional_list_of_strings(entry, field="collateral_address_signatures")

    _optional_bool(entry, field="regulated")
    _optional_string(entry, field="approval_server")
    _optional_string(entry, field="approval_criteria")

    return entry


def _currency_key(entry: Mapping[str, Any]) -> Tuple[str | None, str | None, str | None]:
    return (entry.get("code"), entry.get("issuer"), entry.get("contract"))


def _dedupe_currencies(currencies: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    unique: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str | None, str | None]] = set()

    for currency in currencies:
        key = _currency_key(currency)
        if key in seen:
            continue
        seen.add(key)
        unique.append(dict(currency))

    unique.sort(key=lambda c: (c.get("code") or "", c.get("issuer") or "", c.get("contract") or ""))
    return unique


def load_additional_currencies_from_env(env_var: str = "SEP1_CURRENCIES") -> List[Dict[str, Any]]:
    """
    Read additional currencies from an env var containing a JSON list of
    SEP-1 [[CURRENCIES]] objects.
    """
    raw = os.environ.get(env_var)
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{env_var} must be valid JSON") from exc

    if not isinstance(data, list):
        raise RuntimeError(f"{env_var} must be a JSON list of objects")

    currencies: List[Dict[str, Any]] = []
    for idx, entry in enumerate(data):
        try:
            currencies.append(validate_currency_entry(entry))
        except Exception as exc:
            raise RuntimeError(f"Invalid currency entry at {env_var}[{idx}]: {exc}") from exc

    return currencies


def _apply_required_field_defaults(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Anchor reference tests currently require a subset of currency attributes to
    be present. If they're missing, set safe defaults so the emitted TOML
    complies with the schema.
    """
    code = entry.get("code") or "TOKEN"

    entry.setdefault("status", "live")
    entry.setdefault("desc", f"{code} token")
    entry.setdefault("is_asset_anchored", True)
    entry.setdefault("anchor_asset_type", "fiat")
    entry.setdefault("anchor_asset", code)
    entry.setdefault("anchor_asset_type", "other")

    for field in _ANCHOR_TESTS_REQUIRED_FIELDS:
        if field not in entry:
            raise ValueError(f"currency entry missing required field '{field}' after applying defaults")

    return entry


def build_sep1_currencies() -> List[Dict[str, Any]]:
    """
    Builds the SEP-1 [[CURRENCIES]] list from Polaris Assets plus any extra
    currencies configured in `SEP1_CURRENCIES`.
    """
    currencies_by_key: Dict[Tuple[str | None, str | None, str | None], Dict[str, Any]] = {}
    for asset in Asset.objects.all():
        currency = {
            "code": asset.code,
            "issuer": asset.issuer,
            "display_decimals": asset.significant_decimals,
        }
        currency = _apply_required_field_defaults(currency)
        currencies_by_key[_currency_key(currency)] = validate_currency_entry(
            currency, strict=False
        )

    for env_currency in load_additional_currencies_from_env():
        key = _currency_key(env_currency)
        merged = dict(currencies_by_key.get(key, {}))
        merged.update(env_currency)
        merged = _apply_required_field_defaults(merged)
        currencies_by_key[key] = validate_currency_entry(merged)

    return _dedupe_currencies(currencies_by_key.values())
