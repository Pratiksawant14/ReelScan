import yt_dlp
import uuid
import os
import time
from google import genai
from sentence_transformers import SentenceTransformer
from supabase import create_client, Client
from config import settings

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
