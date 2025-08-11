from typing import Dict, Optional, List
from decimal import Decimal
import os

from django import forms
from django.http import QueryDict
from rest_framework.request import Request

from polaris.models import Transaction, Asset
from polaris.integrations.forms import TransactionForm
from polaris.templates import Template
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
        return f"{base_url}/?transaction_id={transaction.id}&asset_code={asset.code}&callback={callback}&lang={lang}&token={token}&source_amount={amount}&address={address}&qr_scanner=true"

    def after_interactive_flow(self, request: Request, transaction: Transaction):
        """
        Same as ``DepositIntegration.after_interactive_flow``
        """
        transaction.amount_expected = Decimal(request.query_params.get("amount_expected"))
        transaction.memo = request.query_params.get("memo", "")
        transaction.memo_type = "text"
        transaction.status = Transaction.STATUS.pending_user_transfer_start
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
