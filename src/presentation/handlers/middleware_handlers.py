from src.presentation.handlers.base_handler import BaseHandler


class PlaceholderMiddlewareHandler(BaseHandler):
    async def handle(self, update, context):
        raise NotImplementedError
