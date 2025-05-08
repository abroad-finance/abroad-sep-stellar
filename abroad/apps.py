from django.apps import AppConfig

class AbroadConfig(AppConfig):
    name = 'abroad'

    def ready(self):
        from polaris.integrations import register_integrations
        from .sep1 import return_toml_contents

        register_integrations(
            toml=return_toml_contents
        )