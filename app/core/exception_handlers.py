from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError
from app.core.i18n import translate


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    locale = getattr(request.state, "locale", "ja")
    translated = translate(exc.message, locale)
    return JSONResponse(status_code=exc.status_code, content={"detail": translated})
