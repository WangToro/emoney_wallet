from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from routers.auth import router as auth_router
from routers.wallet import router as wallet_router
from routers.merchant import router as merchant_router
from routers.admin import router as admin_router

app = FastAPI()

app.include_router(auth_router, prefix="/auth")
app.include_router(wallet_router, prefix="/wallet")
app.include_router(merchant_router, prefix="/merchant")
app.include_router(admin_router, prefix="/admin")

# 自定義 Swagger UI 的 OpenAPI schema → 顯示 Bearer token 欄位
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="電子錢包 API",
        version="1.0.0",
        description="本地測試用電子錢包服務",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
