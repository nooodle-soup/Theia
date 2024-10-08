# Theia Errors


class TheiaError(Exception):
    pass


class TheiaCredentialsError(Exception):
    pass


# General Exceptions


class USGSError(Exception):
    pass


"""
class USGSInvalidInputFormatError(Exception):
    pass


class USGSInvalidParametersError(Exception):
    pass


class USGSNotFoundError(Exception):
    pass


class USGSServerError(Exception):
    pass


class USGSVersionUnknownError(Exception):
    pass
"""


class USGSDatasetAuthError(Exception):
    """
    Dataset Authentication Unavailable to User
    """

    pass


# Authentication Exceptions


class USGSAuthenticationError(Exception):
    """
    User credential verification failed
    """

    pass


class USGSUnauthorizedError(Exception):
    """
    User account does not have access to the requested endpoint
    """

    pass


# Rate Limit Exceptions


class USGSRateLimitError(Exception):
    pass
