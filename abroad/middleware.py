from django.utils.deprecation import MiddlewareMixin


class StellarTomlCORSMiddleware(MiddlewareMixin):
    """
    Ensure Access-Control-Allow-Origin is present on the stellar.toml response.

    Some scanners require a wildcard header even for simple GET requests, so we
    add it unconditionally for the well-known TOML path.
    """

    def process_response(self, request, response):
        if request.path == "/.well-known/stellar.toml":
            response["Access-Control-Allow-Origin"] = "*"
        return response
