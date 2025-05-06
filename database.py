from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = "sqlite:///./database.db"  # Veritabanı bağlantı URL'si (örnek SQLite)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base() 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)