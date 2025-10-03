from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import JSONFormatter, TextFormatter, SRTFormatter, WebVTTFormatter
from typing import Optional, List
import uvicorn

app = FastAPI(
    title="YouTube Transcript API",
    description="API for extracting transcripts from YouTube videos",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {
        "message": "YouTube Transcript API is running",
        "endpoints": {
            "/transcript/{video_id}": "Get transcript for a video",
            "/list/{video_id}": "List available transcripts",
            "/docs": "API documentation"
        }
    }

@app.get("/transcript/{video_id}")
def get_transcript(
    video_id: str,
    languages: Optional[str] = Query(None, description="Comma-separated language codes (e.g., 'en,de')"),
    format: Optional[str] = Query("json", description="Output format: json, text, srt, webvtt"),
    preserve_formatting: bool = Query(False, description="Preserve HTML formatting"),
    translate_to: Optional[str] = Query(None, description="Translate transcript to this language code")
):
    """
    Fetch transcript for a YouTube video
    
    - **video_id**: YouTube video ID (not the full URL)
    - **languages**: Preferred languages in priority order (default: en)
    - **format**: Output format (json, text, srt, webvtt)
    - **preserve_formatting**: Keep HTML tags like <i> and <b>
    - **translate_to**: Translate the transcript to specified language
    """
    try:
        # Parse languages
        lang_list = languages.split(',') if languages else ['en']
        lang_list = [lang.strip() for lang in lang_list]
        
        # Fetch transcript
        if translate_to:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_transcript(lang_list)
            translated = transcript.translate(translate_to)
            fetched_transcript = translated.fetch()
        else:
            fetched_transcript = YouTubeTranscriptApi.get_transcript(
                video_id, 
                languages=lang_list,
                preserve_formatting=preserve_formatting
            )
        
        # Format output
        if format.lower() == "text":
            formatter = TextFormatter()
            formatted = formatter.format_transcript(fetched_transcript)
            return {"transcript": formatted, "format": "text"}
        elif format.lower() == "srt":
            formatter = SRTFormatter()
            formatted = formatter.format_transcript(fetched_transcript)
            return {"transcript": formatted, "format": "srt"}
        elif format.lower() == "webvtt":
            formatter = WebVTTFormatter()
            formatted = formatter.format_transcript(fetched_transcript)
            return {"transcript": formatted, "format": "webvtt"}
        else:  # json
            return {
                "video_id": video_id,
                "transcript": fetched_transcript
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/list/{video_id}")
def list_transcripts(video_id: str):
    """
    List all available transcripts for a video
    
    - **video_id**: YouTube video ID
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        transcripts = []
        for transcript in transcript_list:
            transcripts.append({
                "language": transcript.language,
                "language_code": transcript.language_code,
                "is_generated": transcript.is_generated,
                "is_translatable": transcript.is_translatable,
                "translation_languages": [
                    {"language": lang.language, "language_code": lang.language_code}
                    for lang in transcript.translation_languages
                ] if transcript.is_translatable else []
            })
        
        return {
            "video_id": video_id,
            "available_transcripts": transcripts
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
