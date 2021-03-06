import hiro
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from slowapi.extension import Limiter
from slowapi.util import get_ipaddr
from tests import TestSlowapi


class TestDecorators(TestSlowapi):
    def test_single_decorator(self):
        app, limiter = self.build_fastapi_app(key_func=get_ipaddr)

        @app.get("/t1")
        @limiter.limit("5/minute")
        async def t1(request: Request):
            return PlainTextResponse("test")

        client = TestClient(app)
        for i in range(0, 10):
            response = client.get("/t1")
            assert response.status_code == 200 if i < 5 else 429

    def test_multiple_decorators(self):
        app, limiter = self.build_fastapi_app(key_func=get_ipaddr)

        @app.get("/t1")
        @limiter.limit(
            "100 per minute", lambda: "test"
        )  # effectively becomes a limit for all users
        @limiter.limit("50/minute")  # per ip as per default key_func
        async def t1(request: Request):
            return PlainTextResponse("test")

        with hiro.Timeline().freeze() as timeline:
            cli = TestClient(app)
            for i in range(0, 100):
                response = cli.get("/t1", headers={"X_FORWARDED_FOR": "127.0.0.2"})
                assert response.status_code == 200 if i < 50 else 429
            for i in range(50):
                assert cli.get("/t1").status_code == 200

            assert cli.get("/t1").status_code == 429
            assert (
                cli.get("/t1", headers={"X_FORWARDED_FOR": "127.0.0.3"}).status_code
                == 429
            )
