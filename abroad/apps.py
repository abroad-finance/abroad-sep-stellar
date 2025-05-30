from django.apps import AppConfig

class AbroadConfig(AppConfig):
    name = 'abroad'

    def ready(self):
        from polaris.integrations import register_integrations
        from .sep1 import return_toml_contents
        from .integrations.quote import QuoteIntegration
        from .integrations.withdrawal import WithdrawalAbroad

        register_integrations(
            toml=return_toml_contents,
            quote=QuoteIntegration(),
            withdrawal=WithdrawalAbroad()
        )
