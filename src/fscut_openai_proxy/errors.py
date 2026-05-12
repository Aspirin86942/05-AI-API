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

