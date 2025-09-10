from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from polaris.models import Transaction


def _uuid_to_base64(uuid_str: str) -> str:
    """Mirror /abroad uuidToBase64: strip dashes, hex → bytes → base64 string."""
    compact = uuid_str.replace("-", "")
    raw = bytes.fromhex(compact)
    return base64.b64encode(raw).decode("ascii")

def _map_partner_status(status: str) -> str:
    """Map /abroad TransactionStatus to Polaris Transaction.STATUS values."""
    normalized = (status or "").upper()
    if normalized == "PAYMENT_COMPLETED":
        return Transaction.STATUS.completed
    if normalized in {"PAYMENT_FAILED", "WRONG_AMOUNT"}:
        return Transaction.STATUS.error
    if normalized == "PROCESSING_PAYMENT":
        return Transaction.STATUS.pending_anchor
    # Default to the start of user transfer
    return Transaction.STATUS.pending_user_transfer_start


@csrf_exempt
def abroad_transaction_webhook(request: HttpRequest) -> HttpResponse:
    """
    Receive transaction events from /abroad and update Polaris Transaction.

    Expected JSON body:
    {
      "event": "transaction.updated" | "transaction.created",
      "data": { "id": "<uuid>", "status": "...", ... }
    }

    Correlates via Polaris Transaction.memo == base64(uuid_bytes) of /abroad id.
    Optionally requires a secret provided as a URL query param if
    settings.ABROAD_WEBHOOK_SECRET is set.
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    # Optional simple shared-secret check via header or query param
    required_secret = getattr(settings, "ABROAD_WEBHOOK_SECRET", None)
    if required_secret:
        provided = request.headers.get("X-Abroad-Webhook-Secret") or request.GET.get("secret")
        if provided != required_secret:
            return JsonResponse({"detail": "Forbidden"}, status=403)

    try:
        payload: Dict[str, Any] = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)

    event = payload.get("event")
    data = payload.get("data") or {}
    if not isinstance(data, dict) or not isinstance(event, str):
        return JsonResponse({"detail": "Invalid payload shape"}, status=400)

    tx_id = data.get("id")
    status = data.get("status")
    if not isinstance(tx_id, str):
        return JsonResponse({"detail": "Missing data.id"}, status=400)

    # Only act on updates; creations may be ignored or treated as initial state
    if event not in ("transaction.updated", "transaction.created"):
        return JsonResponse({"detail": "Ignored event"}, status=200)

    try:
        memo_value = _uuid_to_base64(tx_id)
    except Exception:
        return JsonResponse({"detail": "Invalid data.id"}, status=400)

    try:
        polaris_tx = (
            Transaction.objects.filter(memo=memo_value)
            .order_by("-started_at")
            .first()
        )
        if not polaris_tx:
            # Not found – accept to avoid retries, but report
            return JsonResponse({"detail": "Transaction not found"}, status=404)

        if isinstance(status, str):
            new_status = _map_partner_status(status)
            polaris_tx.status = new_status
            # If the transaction errored on the partner, mark it as refunded
            if new_status == Transaction.STATUS.error:
                polaris_tx.refunded = True
                if not polaris_tx.status_message:
                    polaris_tx.status_message = "Refunded due to partner error"
                polaris_tx.save(update_fields=["status", "refunded", "status_message"])  # small write
            else:
                # For non-error updates, avoid touching the refunded flag
                polaris_tx.save(update_fields=["status"])  # small write

        return JsonResponse({"ok": True})
    except Exception as exc:
        return JsonResponse({"detail": f"Server error: {exc}"}, status=500)
