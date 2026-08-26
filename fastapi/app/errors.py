"""에러 응답 규약.

계약 문서(`docs/api-contract.md` 1장)가 정한 형태로 모든 실패 응답을 통일한다.

    {"error": {"code": "...", "message": "..."}}

FastAPI 기본값은 `{"detail": ...}`라 그대로 두면 검증 실패(422)만 형태가 달라진다.
그러면 정어진 쪽에서 분기를 두 벌 짜야 하므로 핸들러로 덮어쓴다.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """계약에 정의된 에러를 낼 때 쓴다."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


def _body(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


# 계약에 없는 경로로 새어 나온 HTTP 에러에 붙일 기본 code.
_FALLBACK_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    500: "INTERNAL_ERROR",
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content=_body(exc.code, exc.message)
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # 어느 필드가 문제인지까지 알려준다. 메시지로 분기하지 말라고 계약에
        # 적어 두었으므로 code 는 항상 VALIDATION_ERROR 로 고정한다.
        fields = ", ".join(
            ".".join(str(p) for p in err["loc"][1:]) or "(본문)" for err in exc.errors()
        )
        return JSONResponse(
            status_code=422,
            content=_body("VALIDATION_ERROR", f"요청 값이 올바르지 않습니다: {fields}"),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _FALLBACK_CODES.get(exc.status_code, "ERROR")
        return JSONResponse(
            status_code=exc.status_code, content=_body(code, str(exc.detail))
        )
