from requests import Response
from api.errors import (
    USGSAuthenticationError,
    USGSError,
    USGSRateLimitError,
    USGSUnauthorizedError,
)


def check_exceptions(response: Response):
    data = response.json()
    error = {"code": data.get("errorCode"), "msg": data.get("errorMessage")}
    msg = f"{error['code']}: {error['msg']}"

    match error["code"]:
        case "AUTH_INVALID" | "AUTH_KEY_INVALID":
            raise USGSAuthenticationError(msg)
        case "AUTH_UNAUTHORIZED":
            raise USGSUnauthorizedError(msg)
        case "RATE_LIMIT":
            raise USGSRateLimitError(msg)
        case _:
            if error["code"] is not None:
                raise USGSError(msg)
