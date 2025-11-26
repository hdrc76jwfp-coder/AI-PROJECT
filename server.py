from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from pydantic import BaseModel
from dotenv import load_dotenv
from agent import Copilot
from PIL import Image
import io
import base64

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize FastAPI app
app = FastAPI()

# Configure CORS so your frontend can call your backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (you can restrict this later)
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Create an instance of your custom Copilot class
bot = Copilot()

# Pydantic model for chat requests
class ChatRequest(BaseModel):
    text: str

# Chat endpoint
@app.post("/chat")
async def chat(request: ChatRequest):
    response = bot.run(request.text)
    return {"reply": response}

@app.post("/vision")
async def vision(file: UploadFile = File(...)):
    # Read the uploaded image file
    image_data = await file.read()

    # Create a Gemini model instance
    model = genai.GenerativeModel("models/gemini-2.5-pro")

    # Pass the image directly in a single coherent request
    response = model.generate_content(
        contents=[
            {
                "role": "user",
                "parts": [
                    "Explain this image in detail:",
                    {"mime_type": file.content_type, "data": image_data}
                ],
            }
        ]
    )

    return {"reply": response.text}
