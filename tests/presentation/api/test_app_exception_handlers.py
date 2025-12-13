"""Tests for the API exception handlers."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


def test_http_exception_handler_formats_string_detail() -> None:
    import src.presentation.api.app as api_app

    app = FastAPI()
    app.add_exception_handler(HTTPException, api_app.http_exception_handler)  # type: ignore[arg-type]

    @app.get("/boom")
    def boom() -> None:
        raise HTTPException(status_code=400, detail="Bad request")

    client = TestClient(app)
    response = client.get("/boom")

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "message": "Bad request",
            "status_code": 400,
            "path": "/boom",
        }
    }


def test_http_exception_handler_formats_dict_detail_with_extras() -> None:
    import src.presentation.api.app as api_app

    app = FastAPI()
    app.add_exception_handler(HTTPException, api_app.http_exception_handler)  # type: ignore[arg-type]

    @app.get("/teapot")
    def teapot() -> None:
        raise HTTPException(
            status_code=418,
            detail={
                "message": "Short and stout",
                "code": "teapot",
                "extra": {"spout": True},
            },
        )

    client = TestClient(app)
    response = client.get("/teapot")

    assert response.status_code == 418
    assert response.json() == {
        "error": {
            "message": "Short and stout",
            "status_code": 418,
            "path": "/teapot",
            "code": "teapot",
            "details": {"extra": {"spout": True}},
        }
    }


def test_general_exception_handler_returns_internal_error_payload() -> None:
    import src.presentation.api.app as api_app

    app = FastAPI()
    app.add_exception_handler(HTTPException, api_app.http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, api_app.general_exception_handler)

    @app.get("/crash")
    def crash() -> None:
        raise ValueError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/crash")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "message": "Internal server error",
            "status_code": 500,
            "path": "/crash",
        }
    }
