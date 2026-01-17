from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
import uvicorn

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)

from youtube_transcript_api.formatters import JSONFormatter, TextFormatter, SRTFormatter, WebVTTFormatter

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
    - **preserve_formatting**: Keep HTML tags like <i> and <b> (not used directly here)
    - **translate_to**: Translate the transcript to specified language
    """
    # parse languages
    lang_list = languages.split(',') if languages else ['en']
    lang_list = [lang.strip() for lang in lang_list]

    try:
        # 1) brug samme pattern som i /test
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(lang_list)

        if translate_to:
            transcript = transcript.translate(translate_to)

        # preserve_formatting understøttes af formatters, ikke direkte her,
        # så vi lader formatterne håndtere det hvis nødvendigt.
        fetched_transcript = transcript.fetch()

        # 2) format output
        fmt = format.lower()

        if fmt == "text":
            formatter = TextFormatter()
            formatted = formatter.format_transcript(fetched_transcript)
            return {"transcript": formatted, "format": "text", "video_id": video_id}

        elif fmt == "srt":
            formatter = SRTFormatter()
            formatted = formatter.format_transcript(fetched_transcript)
            return {"transcript": formatted, "format": "srt", "video_id": video_id}

        elif fmt == "webvtt":
            formatter = WebVTTFormatter()
            formatted = formatter.format_transcript(fetched_transcript)
            return {"transcript": formatted, "format": "webvtt", "video_id": video_id}

        else:  # json
            # fetched_transcript er en liste af dicts kompatibelt med JSON
            return {
                "video_id": video_id,
                "transcript": fetched_transcript
            }

    except NoTranscriptFound:
        raise HTTPException(
            status_code=404,
            detail="No transcript found. This video may not have captions/subtitles available, or it might be a YouTube Shorts video."
        )
    except TranscriptsDisabled:
        raise HTTPException(
            status_code=403,
            detail="Transcripts are disabled for this video."
        )
    except (RequestBlocked, IpBlocked) as e:
        # gør IP‑blokkering tydelig hvis det sker
        raise HTTPException(
            status_code=503,
            detail=f"Requests are being blocked by YouTube for this server IP: {str(e)}. Configure a proxy to continue."
        )
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error fetching transcript for {video_id}: {error_traceback}")
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

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

@app.get("/test/{video_id}")
def test_transcript(video_id: str):
    """
    Test endpoint to debug transcript fetching issues
    Shows detailed error information
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        available = []
        for transcript in transcript_list:
            available.append({
                "language": transcript.language,
                "language_code": transcript.language_code,
                "is_generated": transcript.is_generated
            })

        return {
            "status": "success",
            "video_id": video_id,
            "available_transcripts": available,
            "message": "Video has transcripts available"
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "video_id": video_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
