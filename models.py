from database import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String)
    phone_number = Column(String)
    email = Column(String, nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user")


class Plant(Base):
    __tablename__ = 'plants'

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String(255), nullable=False)
    predicted_disease = Column(String(255), nullable=False)
    disease_description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))


class PlantImage(Base):
    __tablename__ = "plant_images"

    id = Column(Integer, primary_key=True, index=True)
    plant_id = Column(Integer, ForeignKey("plants.id"))
    image_path = Column(String)
    uploaded_at = Column(DateTime)

class Diagnosis(Base):
    __tablename__ = "diagnosis"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("plant_images.id"))
    disease_name = Column(String)
    confidence = Column(Float)
