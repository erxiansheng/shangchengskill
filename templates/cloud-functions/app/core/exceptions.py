import time
from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, code: int, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


# Error code constants
class ErrorCode:
    PARAMS_ERROR = 1001
    NOT_AUTHENTICATED = 1002
    PERMISSION_DENIED = 1003
    USER_NOT_FOUND = 2001
    PASSWORD_ERROR = 2002
    PHONE_REGISTERED = 2003
    SKILL_NOT_FOUND = 3001
    SKILL_REVIEWING = 3002
    FILE_TYPE_ERROR = 3003
    FILE_TOO_LARGE = 3004
    POINTS_NOT_ENOUGH = 4001
    RECHARGE_FAILED = 4002
    ALREADY_PURCHASED = 4003
    SKILL_TITLE_DUPLICATE = 3005
    SKILL_MD_MISSING = 3006
    STORAGE_ERROR = 3007
    PUBLISH_LIMIT_EXCEEDED = 3008
    NOT_FOUND = 5001


async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
            "timestamp": int(time.time()),
        },
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unhandled exceptions — returns JSON instead of bare 500."""
    import traceback
    traceback.print_exc()
    print(f"[ERROR] Unhandled exception on {request.method} {request.url.path}: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "code": 9999,
            "message": f"服务器内部错误：{type(exc).__name__}: {exc}",
            "data": None,
            "timestamp": int(time.time()),
        },
    )


def success_response(data=None, message="success"):
    return {
        "code": 0,
        "message": message,
        "data": data,
        "timestamp": int(time.time()),
    }


def paginated_response(items, total, page, page_size):
    total_pages = (total + page_size - 1) // page_size
    return success_response({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    })
