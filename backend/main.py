from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import uuid
from typing import Optional, List, Dict, Any
from services import (
    download_reel,
    upload_to_supabase,
    analyze_video_with_gemini,
    get_text_embedding,
    generate_chat_response,
    supabase,
    detect_reel_intent,
    extract_intent_entities,
    save_entities_to_db
)

class AnalyzeRequest(BaseModel):
    url: str

class AnalyzeResponse(BaseModel):
    status: str
    reel_id: str
    analysis: str
    storage_url: str
    intent: Optional[Dict[str, Any]] = {}
    entities: Optional[List[Dict[str, Any]]] = []

class ChatRequest(BaseModel):
    reel_id: str
    message: str

app = FastAPI(
    title="ReelInsights API",
    description="AI-powered Instagram Reel analyzer and chat assistant",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Update with frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to ReelInsights API"}

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_reel(req: AnalyzeRequest):
    local_filepath = None
    try:
        # 1. Download Reel
        local_filepath = download_reel(req.url)
        filename = f"{uuid.uuid4()}_{os.path.basename(local_filepath)}"
        
        # 2. Upload to Supabase Storage
        storage_url = upload_to_supabase(local_filepath, filename)
        
        # 3. Analyze with Gemini
        analysis_text = analyze_video_with_gemini(local_filepath)
        
        # 4. Generate Embeddings
        embedding = get_text_embedding(analysis_text)
        
        # 5. Save to Supabase DB
        # Insert reel
        reel_res = supabase.table("reels").insert({
            "original_url": req.url,
            "storage_url": storage_url
        }).execute()
        
        reel_id = str(reel_res.data[0]['id'])
        
        # Insert analysis
        supabase.table("analyses").insert({
            "reel_id": reel_id,
            "analysis_text": analysis_text,
            "embedding": embedding
        }).execute()
        
        # Step 5 (new): Intent detection + Entity extraction
        try:
            intent_data = await detect_reel_intent(analysis_text)
            entities_data = await extract_intent_entities(analysis_text, intent_data)
            await save_entities_to_db(reel_id, intent_data, entities_data)
        except Exception as e:
            print(f"[Entity Extraction Failed — non-critical]: {e}")
            intent_data = {}
            entities_data = {"entities": []}
            
        return AnalyzeResponse(
            status="success",
            reel_id=reel_id,
            analysis=analysis_text,
            storage_url=storage_url,
            intent=intent_data,
            entities=entities_data.get("entities", [])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup local file unconditionally
        if local_filepath and os.path.exists(local_filepath):
            os.remove(local_filepath)

@app.post("/api/chat")
async def chat_with_reel(req: ChatRequest):
    try:
        return StreamingResponse(
            generate_chat_response(req.reel_id, req.message),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
