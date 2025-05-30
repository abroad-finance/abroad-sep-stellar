from typing import Dict, Optional, List
from decimal import Decimal

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
        return "http://localhost:5173/mobile/anchor"

    def after_interactive_flow(self, request: Request, transaction: Transaction):
        """
        Same as ``DepositIntegration.after_interactive_flow``
        """
        transaction.amount_expected = Decimal(request.query_params.get("amount_expected"))
        transaction.status = Transaction.STATUS.pending_user_transfer_start
        transaction.save()

    def save_sep9_fields(
        self,
        token: SEP10Token,
        request: Request,
        stellar_account: str,
        fields: Dict,
        language_code: str,
        muxed_account: Optional[str] = None,
        account_memo: Optional[str] = None,
        account_memo_type: Optional[str] = None,
        *args: List,
        **kwargs: Dict
    ):
        """
        Same as ``DepositIntegration.save_sep9_fields``
        """
        raise NotImplementedError()

    def process_sep6_request(
        self,
        token: SEP10Token,
        request: Request,
        params: Dict,
        transaction: Transaction,
        *args: List,
        **kwargs: Dict
    ) -> Dict:
        """
        .. _/withdraw: https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0006.md#withdraw
        .. _Withdraw no additional information needed: https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0006.md#1-success-no-additional-information-needed-1

        Same as ``DepositIntegration.process_sep6_request`` except for the case below.
        Specifically, the ``how`` attribute should not be included.

        `Withdraw no additional information needed`_

        A success response. Polaris populates most of the attributes for this response.
        Simply return an 'extra_info' attribute if applicable:
        ::

            {
                "extra_info": {
                    "message": "Send the funds to the following stellar account including 'memo'"
                }
            }

        In addition to this response, you may also return the `Customer information needed`_
        and `Customer Information Status`_ responses as described in
        ``DepositIntegration.process_sep6_request``.
        """
        raise NotImplementedError(
            "`process_sep6_request` must be implemented if SEP-6 is active"
        )

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
