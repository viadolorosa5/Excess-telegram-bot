from aiogram import Router

from handlers import common, handler_babel, handler_glupy, handler_quotes, handler_stats


router = Router()
router.include_router(handler_babel.router)
router.include_router(handler_glupy.router)
router.include_router(handler_stats.router)
router.include_router(handler_quotes.router)
router.include_router(common.router)

__all__ = ["router"]
