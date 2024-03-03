from fastapi import FastAPI, Request, Depends
from routers import secure_router, public_router
from utils import limiter 
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn
from logging_config import setup_logging
from fastapi.responses import JSONResponse
from custom_exceptions import DatabaseConnectionError, DataNotFoundError, ValidationError, AWSCredentialsError, InvalidAPIKeyError, CacheInvalidationError
from security import SecurityHeadersMiddleware, api_key_auth


app = FastAPI()

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.avalancheaccidentsusa.com",
        "https://avalancheaccidentsusa.com",
        "https://avalanchefrontend.onrender.com"
    ], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter

# Security headers middleware setup
app.add_middleware(SecurityHeadersMiddleware)

setup_logging()
logging.info('Application started')

# Exception Handlers
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request, exc):
    logging.warning(f"Rate limit exceeded: {request.url} - {exc.detail}")
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unexpected error for request {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

@app.exception_handler(DatabaseConnectionError)
async def database_connection_error_handler(request: Request, exc: DatabaseConnectionError):
    logging.error(f"Database connection error for request {request.url}: {exc.detail}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(DataNotFoundError)
async def data_not_found_error_handler(request: Request, exc: DataNotFoundError):
    logging.info(f"Data not found for request {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    logging.warning(f"Validation error for request {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(AWSCredentialsError)
async def aws_credentials_error_handler(request: Request, exc: AWSCredentialsError):
    logging.info(f"AWS Credentials Error {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
    
@app.exception_handler(InvalidAPIKeyError)
async def invalid_api_key_error_handler(request: Request, exc: InvalidAPIKeyError):
    logging.error(f"Invalid API Key for request {request.url}: {exc.detail}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(CacheInvalidationError)
async def cache_invalidation_error_handler(request: Request, exc: CacheInvalidationError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

app.include_router(secure_router, prefix='/api', tags=['secure endpoints'], dependencies=[Depends(api_key_auth)])
app.include_router(public_router, prefix='/api', tags=['public endpoints'])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)