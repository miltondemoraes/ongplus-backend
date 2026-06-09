class CnpjNotFound(Exception):
    """Exception raised when CNPJ is not found in the external registry."""
    pass

class ExternalApiError(Exception):
    """Exception raised when an external API call fails (timeout, bad gateway, etc.)."""
    pass

class InvalidAddressError(Exception):
    """Exception raised when the address provided or retrieved is malformed or invalid."""
    pass
