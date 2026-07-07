import os
import json
import logging
import asyncio
from typing import List
from fastapi import FastAPI, Query, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from agent.core import AgentOrchestrator
from agent.config import Config
from agent.tools import ALL_TOOLS

# Configure logging
logger = logging.getLogger("agent.server")

app = FastAPI(
    title="Autonomous ReAct AI Agent Server",
    description="Futuristic streaming API server for modular ReAct agents.",
    version="1.0.0"
)

# Enable CORS for easy local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/status")
async def get_status():
    """
    Returns the current configuration details of the backend LLM brain.
    Useful for populating the HUD status dials upon load.
    """
    provider = Config.LLM_PROVIDER
    
    if provider == "openai":
        model = Config.OPENAI_MODEL
        has_key = bool(Config.OPENAI_API_KEY)
        mode = "OpenAI API" if has_key else "Mock Sandbox"
    elif provider == "ollama":
        model = Config.OLLAMA_MODEL
        mode = "Local API"
    else:
        model = Config.AGENT_MODEL
        has_key = bool(Config.GEMINI_API_KEY)
        mode = "Google API" if has_key else "Mock Sandbox"
    
    return {
        "provider": provider,
        "model": model,
        "mode": mode,
        "tools": list(ALL_TOOLS.keys()),
        "log_level": Config.LOG_LEVEL
    }

@app.post("/api/upload")
async def upload_files(category: str = Form(...), files: List[UploadFile] = File(...)):
    """
    Receives multi-part file uploads and saves them locally into:
    - 'patient_records/' if category is 'patient'
    - 'insurance_rules/' if category is 'policy'
    """
    if category not in ("patient", "policy"):
        raise HTTPException(status_code=400, detail="Invalid target category. Must be 'patient' or 'policy'.")
        
    if category == "patient":
        # Clear claims_audit directory on new patient upload to prevent model hallucination with leftover reports
        audit_dir = "claims_audit"
        if os.path.exists(audit_dir) and os.path.isdir(audit_dir):
            try:
                for f in os.listdir(audit_dir):
                    f_path = os.path.join(audit_dir, f)
                    if os.path.isfile(f_path):
                        os.remove(f_path)
                logger.info("Cleared claims_audit directory on new patient file upload.")
            except Exception as clean_err:
                logger.error(f"Failed to clear claims_audit: {str(clean_err)}")
                
    target_dir = "patient_records" if category == "patient" else "insurance_rules"
    abs_target_dir = os.path.abspath(target_dir)
    
    os.makedirs(abs_target_dir, exist_ok=True)
    
    uploaded_files = []
    for file in files:
        filename = os.path.basename(file.filename)
        if not filename:
            continue
            
        file_path = os.path.join(abs_target_dir, filename)
        
        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            uploaded_files.append({
                "filename": filename,
                "size": len(content)
            })
        except Exception as e:
            logger.error(f"Failed to save uploaded file '{filename}': {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save file '{filename}': {str(e)}")
            
    return {
        "status": "success",
        "category": category,
        "directory": target_dir,
        "files": uploaded_files
    }

@app.get("/api/latest-audit")
async def get_latest_audit_file():
    """
    Scans the 'claims_audit/' folder and returns the filename of the most recently modified `.xlsx` report.
    This ensures the UI can always display a download link regardless of LLM streaming text structure.
    """
    audit_dir = "claims_audit"
    if not os.path.exists(audit_dir) or not os.path.isdir(audit_dir):
        return {"filename": None}
        
    try:
        files = [f for f in os.listdir(audit_dir) if f.endswith(".xlsx")]
        if not files:
            return {"filename": None}
            
        # Sort by modification time (newest first)
        files_sort = []
        for f in files:
            f_path = os.path.join(audit_dir, f)
            files_sort.append((f, os.path.getmtime(f_path)))
            
        files_sort.sort(key=lambda x: x[1], reverse=True)
        newest_file = files_sort[0][0]
        return {"filename": newest_file}
    except Exception as e:
        logger.error(f"Error listing latest audit files: {str(e)}")
        return {"filename": None}

@app.get("/api/chat")
async def chat_stream(q: str = Query(..., description="The user query to the AI Agent.")):
    """
    Exposes a Server-Sent Events (SSE) streaming API endpoint.
    Runs the AgentOrchestrator and flushes step-by-step reasoning live.
    """
    async def event_generator():
        orchestrator = AgentOrchestrator()
        
        # 1. Yield initial handshake metadata containing LLM state
        provider = Config.LLM_PROVIDER
        
        if provider == "openai":
            model = Config.OPENAI_MODEL
            mode = "Live" if bool(Config.OPENAI_API_KEY) else "Mock"
        elif provider == "ollama":
            model = Config.OLLAMA_MODEL
            mode = "Live"
        else:
            model = Config.AGENT_MODEL
            mode = "Live" if bool(Config.GEMINI_API_KEY) else "Mock"
            
        handshake = {
            "type": "handshake",
            "provider": provider,
            "model": model,
            "mode": mode,
            "tools": list(ALL_TOOLS.keys())
        }
        yield f"data: {json.dumps(handshake)}\n\n"
        await asyncio.sleep(0.1) # tiny sleep to ensure flush

        def advance_generator(gen):
            try:
                return next(gen)
            except StopIteration:
                return None

        # 2. Iterate and consume the agent reasoning steps
        runner = orchestrator.run(q)
        while True:
            try:
                # Run the synchronous generator step inside an executor to prevent blocking the event loop
                event = await asyncio.to_thread(advance_generator, runner)
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
                
                # Check current short term memory size to update telemetry HUD
                telemetry = {
                    "type": "telemetry",
                    "memory_size": len(orchestrator.memory.get_messages()),
                    "current_step": event.get("step", None)
                }
                yield f"data: {json.dumps(telemetry)}\n\n"
                
                # Tiny sleep to smooth streaming delivery to frontend client
                await asyncio.sleep(0.05)
                
            except Exception as e:
                logger.error(f"Error during streaming execution: {str(e)}")
                err_payload = {"type": "error", "message": f"Server processing error: {str(e)}"}
                yield f"data: {json.dumps(err_payload)}\n\n"
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/claims_audit/{filename}")
async def download_audit_file(filename: str):
    """
    Serves files from the 'claims_audit/' directory for download.
    """
    safe_filename = os.path.basename(filename)
    file_path = os.path.join("claims_audit", safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audit file not found.")
    
    if safe_filename.endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif safe_filename.endswith(".json"):
        media_type = "application/json"
    else:
        media_type = "application/octet-stream"
        
    return FileResponse(file_path, media_type=media_type, filename=safe_filename)

# Ensure static folder exists
static_path = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_path):
    os.makedirs(static_path, exist_ok=True)

# Mount the static directory for index.html mapping directly to /
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0 to enable local network access
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
