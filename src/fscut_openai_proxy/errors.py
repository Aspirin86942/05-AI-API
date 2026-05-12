class UpstreamAuthExpiredError(Exception):
    def __init__(self) -> None:
        self.status_code = 502
        self.detail = {
            "error": {
                "message": "Upstream authentication expired",
                "type": "upstream_auth_error",
                "code": "upstream_auth_expired",
                "retryable": False,
            }
        }


class UpstreamRateLimitError(Exception):
    def __init__(self) -> None:
        self.status_code = 429
        self.detail = {
            "error": {
                "message": "Upstream rate limit exceeded",
                "type": "rate_limit_error",
                "code": "upstream_rate_limited",
                "retryable": True,
            }
        }


class UpstreamRefreshInvalidResponseError(Exception):
    def __init__(self) -> None:
        self.status_code = 502
        self.detail = {
            "error": {
                "message": "Upstream refresh response missing access token",
                "type": "upstream_auth_error",
                "code": "upstream_refresh_invalid_response",
                "retryable": True,
            }
        }


class UpstreamForbiddenError(Exception):
    def __init__(self) -> None:
        self.status_code = 502
        self.detail = {
            "error": {
                "message": "Upstream rejected this account or request",
                "type": "upstream_permission_error",
                "code": "upstream_forbidden",
                "retryable": False,
            }
        }

