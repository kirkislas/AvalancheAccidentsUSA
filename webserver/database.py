from sqlalchemy.ext.declarative import declarative_base
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker



ASYNC_DATABASE_URL = os.environ.get('ASYNC_DATABASE_URL')

Base = declarative_base()

# Create an asynchronous engine instance
engine = create_async_engine(ASYNC_DATABASE_URL, echo=True)

# Create a sessionmaker, binding the async engine
# The class_ parameter is set to AsyncSession to enable async session operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

# Example usage of the async session in FastAPI endpoint
async def get_db():
    async with SessionLocal() as session:
        yield session