from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Union

import requests
from django.conf import settings
from requests import Response

from polaris.models import Asset, DeliveryMethod, OffChainAsset, Quote
from polaris.sep10.token import SEP10Token
from rest_framework.request import Request
from polaris.integrations.quote import QuoteIntegration as BaseQuoteIntegration

logger = logging.getLogger(__name__)


class QuoteIntegration(BaseQuoteIntegration):
    """Concrete implementation of the SEP-38 `QuoteIntegration` interface.

    This implementation consumes the partner API described in the provided
    ``swagger.json``.  Only the endpoints that relate to pricing are used:

    * ``POST /quote`` – fiat → crypto quotes
    * ``POST /quote/reverse`` – crypto → fiat quotes

    All other I/O (authentication, pagination, etc.) is handled by Polaris
    outside of this class.  The integration *only* concerns itself with
    transforming the SEP‑38 payload into the request/response pairs expected
    by the upstream partner and mapping the results back into the values
    required by Polaris.
    """

    #: Attribute names placed on a *Polaris* ``Asset`` that identify whether that
    #: asset represents a blockchain currency in the partner API.  Assets that
    #: *don’t* match any of these are assumed to be off‑chain (fiat).
    _CRYPTO_CODES: set[str] = {"USDC", "USDT", "BTC", "ETH"}

    def __init__(self) -> None:  # noqa: D401, D401 (imperative mood is fine)
        # NOTE: read the partner base‑URL and credentials from ``settings`` so
        # deployments can override them without code changes.
        self.base_url: str = settings.PARTNER_API_BASE_URL.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({
            "X-API-Key": settings.PARTNER_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    # ---------------------------------------------------------------------
    # Public API – the three hooks Polaris calls
    # ---------------------------------------------------------------------

    def get_prices(
        self,
        token: SEP10Token,
        request: Request,
        sell_asset: Union[Asset, OffChainAsset],
        sell_amount: Decimal,
        buy_assets: List[Union[Asset, OffChainAsset]],
        sell_delivery_method: Optional[DeliveryMethod] = None,
        buy_delivery_method: Optional[DeliveryMethod] = None,
        country_code: Optional[str] = None,
        *args,
        **kwargs,
    ) -> List[Decimal]:
        """Return partner *non‑binding* prices for each asset in ``buy_assets``.

        The partner API does **not** support batch pricing, therefore we loop
        over ``buy_assets`` and call :py:meth:`get_price` for each entry.  All
        exceptions propagating out of that call are intentionally *not*
        swallowed so Polaris can map them to the correct HTTP status codes.
        """

        prices: list[Decimal] = []
        for ba in buy_assets:
            price = self.get_price(
                token=token,
                request=request,
                sell_asset=sell_asset,
                buy_asset=ba,
                sell_amount=sell_amount,
                sell_delivery_method=sell_delivery_method,
                buy_delivery_method=buy_delivery_method,
                country_code=country_code,
            )
            prices.append(price)
        return prices

    def get_price(
        self,
        token: SEP10Token,
        request: Request,
        sell_asset: Union[Asset, OffChainAsset],
        buy_asset: Union[Asset, OffChainAsset],
        buy_amount: Optional[Decimal] = None,
        sell_amount: Optional[Decimal] = None,
        sell_delivery_method: Optional[DeliveryMethod] = None,
        buy_delivery_method: Optional[DeliveryMethod] = None,
        country_code: Optional[str] = None,
        *args,
        **kwargs,
    ) -> Decimal:
        """Return a *non‑binding* price of *one* ``buy_asset`` in ``sell_asset``.

        The upstream service offers **two** quote endpoints:

        * ``POST /quote`` – expects fiat *amount* and responds with crypto
          *value* (fiat → crypto)
        * ``POST /quote/reverse`` – expects crypto *source_amount* and responds
          with fiat *value* (crypto → fiat)

        Which one we call depends on the nature of ``sell_asset`` &
        ``buy_asset``:

        +----------------+----------------+-------------------------------+
        | ``sell_asset`` | ``buy_asset``  |  endpoint                    |
        +================+================+===============================+
        | crypto         | fiat           |  ``/quote`` (fiat→crypto)    |
        +----------------+----------------+-------------------------------+
        | fiat           | crypto         |  ``/quote/reverse``          |
        +----------------+----------------+-------------------------------+
        | crypto         | crypto         |  *unsupported*               |
        +----------------+----------------+-------------------------------+
        | fiat           | fiat           |  *unsupported*               |
        +----------------+----------------+-------------------------------+

        Because SEP‑38 always wants *price‑per‑unit*, we **always** request a
        quantity of *one* for whichever asset the partner expects as *amount*.
        We then convert the partner’s numeric ``value`` to a ``Decimal`` and
        return it.
        """

        try:
            if self._is_crypto(sell_asset) and not self._is_crypto(buy_asset):
                # User is *selling* crypto → needs /quote (fiat → crypto)
                body = self._build_quote_request(
                    fiat_asset=buy_asset,  # because /quote takes fiat amount
                    crypto_asset=sell_asset,
                    fiat_amount=Decimal("1"),
                    sell_delivery_method=sell_delivery_method,
                    buy_delivery_method=buy_delivery_method,
                )
                endpoint = "/quote"
            elif not self._is_crypto(sell_asset) and self._is_crypto(buy_asset):
                # User is selling fiat to *buy* crypto → reverse quote
                body = self._build_reverse_quote_request(
                    fiat_asset=sell_asset,
                    crypto_asset=buy_asset,
                    crypto_amount=Decimal("1"),
                    sell_delivery_method=sell_delivery_method,
                    buy_delivery_method=buy_delivery_method,
                )
                endpoint = "/quote/reverse"
            else:
                raise ValueError("Only fiat⇄crypto pairs are supported by the partner API")

            response: Response = self._session.post(f"{self.base_url}{endpoint}", json=body, timeout=10)
            self._raise_for_status(response)
            data: dict = response.json()
            # Partner returns the amount of *crypto* or *fiat* you get for the
            # one‑unit you asked for.  Regardless of direction, that number is
            # the *price* of a single ``buy_asset`` in units of ``sell_asset``.
            return Decimal(str(data["value"]))
        except ValueError:
            raise  # Polaris will map this to 400.
        except requests.RequestException as exc:
            logger.error("Error calling partner pricing service: %s", exc, exc_info=True)
            raise RuntimeError("Failed to fetch price from upstream service") from exc

    def post_quote(
        self,
        token: SEP10Token,
        request: Request,
        quote: Quote,
        *args,
        **kwargs,
    ) -> Quote:  # noqa: D401
        """Populate ``price`` and ``expires_at`` on *binding* ``quote`` objects.

        The *binding* variant differs from :pymeth:`get_price` in that the
        returned price must be *honoured* later.  We therefore call the same
        partner endpoint but now propagate the client‑specified *amount* and
        *expiry* (if any) so that both parties have a record of the rate.
        """

        sell_asset = quote.sell_asset  # type: ignore[attr-defined]
        buy_asset = quote.buy_asset  # type: ignore[attr-defined]

        if self._is_crypto(sell_asset) and not self._is_crypto(buy_asset):
            body = self._build_quote_request(
                fiat_asset=buy_asset,
                crypto_asset=sell_asset,
                fiat_amount=quote.buy_amount or Decimal("0"),  # fiat amount is required by /quote
                sell_delivery_method=quote.sell_delivery_method,  # type: ignore[attr-defined]
                buy_delivery_method=quote.buy_delivery_method,  # type: ignore[attr-defined]
            )
            endpoint = "/quote"
        elif not self._is_crypto(sell_asset) and self._is_crypto(buy_asset):
            body = self._build_reverse_quote_request(
                fiat_asset=sell_asset,
                crypto_asset=buy_asset,
                crypto_amount=quote.sell_amount or Decimal("0"),  # source_amount is required
                sell_delivery_method=quote.sell_delivery_method,  # type: ignore[attr-defined]
                buy_delivery_method=quote.buy_delivery_method,  # type: ignore[attr-defined]
            )
            endpoint = "/quote/reverse"
        else:
            raise ValueError("Only fiat⇄crypto pairs are supported by the partner API")

        try:
            response: Response = self._session.post(f"{self.base_url}{endpoint}", json=body, timeout=10)
            self._raise_for_status(response)
            data: dict = response.json()
        except ValueError:
            raise
        except requests.RequestException as exc:
            logger.error("Error calling partner pricing service: %s", exc, exc_info=True)
            raise RuntimeError("Failed to create quote with upstream service") from exc

        quote.price = Decimal(str(data["value"]))  # type: ignore[attr-defined]
        quote.expire_at = datetime.fromtimestamp(data["expiration_time"], tz=timezone.utc)  # type: ignore[attr-defined]
        quote.external_id = data["quote_id"]  # Optional: store partner‑side ID for later reconciliation.
        return quote

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _is_crypto(asset: Union[Asset, OffChainAsset]) -> bool:
        """Return ``True`` if *asset* is a blockchain/crypto asset."""
        return isinstance(asset, Asset) and asset.code.upper() in QuoteIntegration._CRYPTO_CODES

    @staticmethod
    def _delivery_to_payment_method(dm: Optional[DeliveryMethod]) -> Optional[str]:
        if dm is None:
            return None
        return dm.name.upper()

    def _build_quote_request(
        self,
        *,
        fiat_asset: Union[Asset, OffChainAsset],
        crypto_asset: Union[Asset, OffChainAsset],
        fiat_amount: Decimal,
        sell_delivery_method: Optional[DeliveryMethod],
        buy_delivery_method: Optional[DeliveryMethod],
    ) -> dict:
        """Return payload for ``POST /quote`` (fiat → crypto)."""
        return {
            "target_currency": fiat_asset.code.upper(),
            "payment_method": self._delivery_to_payment_method(buy_delivery_method) or "MOVII",
            "network": "STELLAR",  # Polaris currently only supports Stellar
            "crypto_currency": crypto_asset.code.upper(),
            "amount": float(fiat_amount),
        }

    def _build_reverse_quote_request(
        self,
        *,
        fiat_asset: Union[Asset, OffChainAsset],
        crypto_asset: Union[Asset, OffChainAsset],
        crypto_amount: Decimal,
        sell_delivery_method: Optional[DeliveryMethod],
        buy_delivery_method: Optional[DeliveryMethod],
    ) -> dict:
        """Return payload for ``POST /quote/reverse`` (crypto → fiat)."""
        return {
            "target_currency": fiat_asset.code.upper(),
            "payment_method": self._delivery_to_payment_method(sell_delivery_method) or "MOVII",
            "network": "STELLAR",
            "crypto_currency": crypto_asset.code.upper(),
            "source_amount": float(crypto_amount),
        }

    # The partner occasionally returns 400 with a structured JSON body.
    # Transform that into Python exceptions so Polaris can map them onto
    # the correct HTTP status codes.
    @staticmethod
    def _raise_for_status(resp: Response) -> None:
        if 200 <= resp.status_code < 300:
            return
        if resp.status_code == 400:
            # Any issues with parameters – propagate as ``ValueError`` so Polaris
            # replies with *400 Bad Request*.
            reason = resp.json().get("reason", resp.text)
            raise ValueError(f"Bad request to partner API: {reason}")
        # Everything else surfaces as *503 Service Unavailable*.
        raise RuntimeError(f"Partner API error – status {resp.status_code}: {resp.text}")
