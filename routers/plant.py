from fastapi import APIRouter, Depends, HTTPException, Path, Request, File, UploadFile
from pydantic import BaseModel, Field
from typing import Annotated, List
from starlette import status
from sqlalchemy.orm import Session
from pathlib import Path
import torch
from PIL import Image
import uuid
import os
from transformers import AutoImageProcessor, AutoModelForImageClassification
import httpx
from database import engine, SessionLocal
from models import Plant
from routers.auth import get_current_user
import dotenv
import os

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
import logging

# Add logging configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}
MODEL_NAME = "google/mobilenet_v2_1.0_224"

router = APIRouter(
    prefix="/plant",
    tags=["Plant"]
)

class PlantResponse(BaseModel):
    id: int
    file_path: str
    predicted_disease: str
    disease_description: str | None
    owner_id: int

    class Config:
        from_attributes = True

class ImageProcessor:
    def __init__(self):
        self.processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
        self.model = AutoModelForImageClassification.from_pretrained(MODEL_NAME)  # Remove fast_init

    def predict(self, image_path: str) -> int:
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt")
        
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.logits.argmax(-1).item()

class FileHandler:
    @staticmethod
    def get_upload_path(user_id: int, filename: str) -> Path:
        file_extension = Path(filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        upload_dir = Path("media") / f"user_{user_id}"
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir / unique_filename

    @staticmethod
    async def save_file(file_path: Path, file: UploadFile) -> dict:
        try:
            content = await file.read()
            file_path.write_bytes(content)
            return {"file_path": str(file_path)}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving image: {str(e)}"
            )

def get_db():
    db = SessionLocal(bind=engine)
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

@router.get("/all", response_model=List[PlantResponse])
async def get_all_plants(
    db: db_dependency,
    user_dict: user_dependency
) -> List[Plant]:
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    return db.query(Plant).filter(Plant.owner_id == user_dict["id"]).all()

@router.get("/{plant_id}", response_model=PlantResponse)
async def get_plant_by_id(
    plant_id: int,
    db: db_dependency,
    user_dict: user_dependency
) -> Plant:
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    plant = db.query(Plant).filter(
        Plant.id == plant_id,
        Plant.owner_id == user_dict["id"]
    ).first()

    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found"
        )
    
    return plant

import httpx
import os

dotenv.load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

async def get_disease_description(disease_name: str) -> str:
    if not GEMINI_API_KEY:
        logger.error("Gemini API key not found")
        return "API key not found - Description unavailable"

    try:
        # Sanitize disease name and create a more specific prompt
        sanitized_name = disease_name.strip().lower().replace('_', ' ')
        
        prompt = (
            f"Bitkide '{sanitized_name}' hastalığı tespit edildi. "
            "Aşağıdaki başlıklara göre Türkçe, kısa ve anlaşılır bir açıklama yap:\n\n"
            "1. Nedir?\n"
            "2. Belirtileri nelerdir?\n"
            "3. Nasıl tedavi edilir?\n"
            "Cevabı madde madde ve toplamda 3–5 cümleyi geçmeyecek şekilde oluştur."
        )

        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "safetySettings": [{
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }]
        }

        logger.debug(f"Sending request to Gemini API for disease: {sanitized_name}")
        resp = httpx.post(GEMINI_API_URL, json=data, headers={"Content-Type": "application/json"}, timeout=30)
        resp.raise_for_status()
        content = resp.json()
        return content["candidates"][0]["content"]["parts"][0]["text"].strip()

    except httpx.TimeoutException:
        logger.error("Gemini API request timed out")
        return f"Could not get description for {disease_name} - Request timed out"
    except Exception as e:
        logger.exception(f"Error in get_disease_description: {str(e)}")
        return f"Could not process description for {disease_name}. Error: {str(e)}"

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=PlantResponse)
async def upload_image(
    db: db_dependency,
    user_dict: user_dependency,
    file: UploadFile = File(...)
) -> Plant:
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )

    try:
        file_handler = FileHandler()
        image_processor = ImageProcessor()

        # Save file
        upload_path = file_handler.get_upload_path(user_dict["id"], file.filename)
        saved_file = await file_handler.save_file(upload_path, file)

        # Get prediction and handle disease name
        prediction = image_processor.predict(saved_file["file_path"])
        try:
            disease_name = image_processor.model.config.id2label[prediction]
            logger.info(f"Predicted disease: {disease_name}")
        except KeyError:
            logger.error(f"Unknown prediction index: {prediction}")
            disease_name = "Unknown Condition"

        # Get description with better error handling
        disease_description = await get_disease_description(disease_name)
        if not disease_description or len(disease_description.strip()) < 10:
            fallback_description = (
                f"A condition affecting plants. The system identified this as '{disease_name}'. "
                "Please consult a plant expert for specific advice."
            )
            logger.warning(f"Using fallback description for {disease_name}")
            disease_description = fallback_description

        # Save to database
        new_plant = Plant(
            file_path=str(upload_path),
            predicted_disease=disease_name,
            disease_description=disease_description,  # This should now always have a value
            owner_id=user_dict["id"]
        )
        
        db.add(new_plant)
        db.commit()
        db.refresh(new_plant)
        
        return new_plant

    except Exception as e:
        # Clean up file if database operation fails
        if 'upload_path' in locals():
            upload_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )



