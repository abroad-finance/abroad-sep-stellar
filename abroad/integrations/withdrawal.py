from typing import Dict, Optional, List
from decimal import Decimal
import os

from rest_framework.request import Request

from polaris.models import Transaction, Asset
from polaris.sep10.token import SEP10Token
from polaris.integrations.transactions import WithdrawalIntegration

class WithdrawalAbroad(WithdrawalIntegration):
    """
    The container class for withdrawal integration functions

    Subclasses must be registered with Polaris by passing it to
    ``polaris.integrations.register_integrations``.
    """

    def interactive_url(
        self,
        request: Request,
        transaction: Transaction,
        asset: Asset,
        amount: Optional[Decimal],
        callback: Optional[str],
        lang: Optional[str],
        *args: List,
        **kwargs: Dict
    ) -> Optional[str]:
        """
        Same as ``DepositIntegration.interactive_url``

        :return: a URL to be used as the entry point for the interactive
            withdrawal flow
        """
        print("request", request)
        base_url = os.environ.get("INTERACTIVE_URL_BASE", "http://localhost:5173")
        token = request.query_params.get("token")
        address = transaction.stellar_account
        qr_scanner = request.query_params.get("qr_scanner")
        url = (
            f"{base_url}/?transaction_id={transaction.id}"
            f"&asset_code={asset.code}"
            f"&callback={callback}"
            f"&lang={lang}"
            f"&token={token}"
            f"&source_amount={amount}"
            f"&address={address}"
        )
        if qr_scanner is not None:
            url += f"&qr_scanner={qr_scanner}"
        return url

    def after_interactive_flow(self, request: Request, transaction: Transaction):
        """
        Same as ``DepositIntegration.after_interactive_flow``
        """
        transaction.amount_expected = Decimal(request.query_params.get("amount_expected"))
        transaction.amount_in = Decimal(request.query_params.get("amount_expected"))
        transaction.status = Transaction.STATUS.pending_user_transfer_start
        transaction.memo = request.query_params.get("memo", "")
        transaction.memo_type = "text"
        transaction.receiving_anchor_account = "GCLMP4CYNFN62DDKPRMFWU4FQZFJBUL4CPTJ3JAGIHM72UNB6IX5HUGK"
        transaction.save()

    def patch_transaction(
        self,
        token: SEP10Token,
        request: Request,
        params: Dict,
        transaction: Transaction,
        *args: List,
        **kwargs: Dict
    ):
        """
        Same as ``DepositIntegration.patch_transaction``
        """
        raise NotImplementedError("PATCH /transactions/:id is not supported")
