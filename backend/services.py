import yt_dlp
import uuid
import os
import time
import json
import asyncio
from google import genai
from sentence_transformers import SentenceTransformer
from supabase import create_client, Client
from config import settings
from prompts import build_intent_prompt, build_entity_prompt

# Initialize clients
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)
gemini_client = genai.Client(api_key=settings.gemini_api_key)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def download_reel(url: str) -> str:
    """Downloads an Instagram reel and returns the local filepath."""
    ydl_opts = {
        'outtmpl': f'tmp_{uuid.uuid4()}_%(id)s.%(ext)s',
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info_dict)
    
    if os.path.exists(filename):
        return filename
    raise Exception("Failed to download reel")

def upload_to_supabase(filepath: str, filename: str) -> str:
    """Uploads a file to Supabase Storage and returns the public URL."""
    with open(filepath, 'rb') as f:
        supabase.storage.from_("reels").upload(
            file=f,
            path=filename,
            file_options={"content-type": "video/mp4"}
        )
    return supabase.storage.from_("reels").get_public_url(filename)

def analyze_video_with_gemini(filepath: str) -> str:
    """Uses Gemini 2.5 Flash to analyze the video."""
    video_file = gemini_client.files.upload(file=filepath)
    
    # Wait for processing to complete
    while video_file.state.name == "PROCESSING":
        print("Waiting for video to be processed...")
        time.sleep(2)
        video_file = gemini_client.files.get(name=video_file.name)
        
    if video_file.state.name == "FAILED":
         raise Exception("Gemini video processing failed.")

    prompt = (
        "Analyze this Instagram reel in detail. Describe the visual content, "
        "any text on the screen, the audio/transcript, and the overall vibe "
        "or key takeaways. Provide a comprehensive summary."
    )
    
    response = gemini_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[video_file, prompt]
    )
    
    # Clean up the file from Gemini storage
    gemini_client.files.delete(name=video_file.name)
    
    return response.text

def get_text_embedding(text: str) -> list[float]:
    """Generates an embedding for the given text."""
    embedding = embedding_model.encode(text)
    return embedding.tolist()

def generate_chat_response(reel_id: str, user_message: str):
    """Retrieves context from Supabase and streams a response from Gemini."""
    # 2. Retrieve the full analysis context for this specific reel directly from the database.
    # Since we are keeping the entire summary as one document per reel (efficient for short videos),
    # we can fetch it directly by reel_id instead of doing a global vector search which might return other reels!
    response = supabase.table("analyses").select("analysis_text").eq("reel_id", reel_id).execute()
    
    if response.data:
        context_text = response.data[0]['analysis_text']
    else:
        context_text = "No analysis found for this reel."
    
    # 3. Construct the prompt for Gemini
    prompt = f"""
    You are an AI assistant helping a user understand an Instagram reel.
    Here is the detailed analysis context of the reel:
    {context_text}
    
    User Question: {user_message}
    
    Answer the user's question naturally and conversationally using the context provided.
    Format your response beautifully using Markdown (bolding, bullet points, etc) if appropriate.
    Do not repeat phrases like "Based on the analysis" or "According to the context" - just give the answer directly.
    If the answer is definitely not in the context, politely say that you don't have that information from the video analysis.
    """
    
    # 4. Stream response from Gemini
    response_stream = gemini_client.models.generate_content_stream(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    for chunk in response_stream:
        yield chunk.text

def safe_parse_json(text: str) -> dict:
    try:
        cleaned = text.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(cleaned)
    except Exception:
        return {}

async def detect_reel_intent(analysis_text: str) -> dict:
    def _sync_call():
        prompt = build_intent_prompt(analysis_text)
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        )
        return response
    result = await asyncio.to_thread(_sync_call)
    return safe_parse_json(result.text)

async def extract_intent_entities(analysis_text: str, intent_data: dict) -> dict:
    def _sync_call():
        category = intent_data.get("category", "other")
        primary_intent = intent_data.get("primary_intent", "Unknown intent")
        prompt = build_entity_prompt(analysis_text, category, primary_intent)
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        )
        return response
    result = await asyncio.to_thread(_sync_call)
    return safe_parse_json(result.text)

async def save_entities_to_db(reel_id: str, intent_data: dict, entities_data: dict):
    category = intent_data.get("category")
    description = intent_data.get("primary_intent")
    keywords = intent_data.get("intent_keywords", [])
    
    supabase.table("reels").update({
        "intent_category": category,
        "intent_description": description,
        "intent_keywords": keywords
    }).eq("id", reel_id).execute()
    
    entities = entities_data.get("entities", [])
    valid_entities = [e for e in entities if e.get("confidence", 0) >= 0.5]
    
    if valid_entities:
        insert_data = []
        for e in valid_entities:
            insert_data.append({
                "reel_id": reel_id,
                "entity_id": e.get("id"),
                "name": e.get("name"),
                "brand": e.get("brand"),
                "type": e.get("type"),
                "sub_category": e.get("sub_category"),
                "search_query": e.get("search_query"),
                "confidence": e.get("confidence"),
                "source": e.get("source", "intent_extraction"),
                "notes": e.get("notes")
            })
        supabase.table("reel_entities").insert(insert_data).execute()
