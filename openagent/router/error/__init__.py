from fastapi.responses import JSONResponse


class APIExceptionResponse(JSONResponse):
    def __init__(self, status_code: int, error: Exception):
        super().__init__(
            status_code=status_code,
            content={
                "error": str(error),
            },
        )


__all__ = [APIExceptionResponse]
