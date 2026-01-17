from fastapi import FastAPI, HTTPException, Query
from typing import Optional
import uvicorn

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from youtube_transcript_api.formatters import TextFormatter, SRTFormatter, WebVTTFormatter

app = FastAPI(
    title="YouTube Transcript API",
    description="API for extracting transcripts from YouTube videos",
    version="1.0.0",
)

ytt_api = YouTubeTranscriptApi()

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/test/{video_id}")
def test_transcript(video_id: str):
    try:
        transcript_list = ytt_api.list(video_id)
        available = []
        for transcript in transcript_list:
            available.append(
                {
                    "language": transcript.language,
                    "language_code": transcript.language_code,
                    "is_generated": transcript.is_generated,
                }
            )
        return {
            "status": "success",
            "video_id": video_id,
            "available_transcripts": available,
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "video_id": video_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }

@app.get("/transcript/{video_id}")
def get_transcript(
    video_id: str,
    languages: Optional[str] = Query(None, description="Comma-separated codes, e.g. 'en,de'"),
    format: Optional[str] = Query("json", description="json, text, srt, webvtt"),
    translate_to: Optional[str] = Query(None, description="Translate to this language code"),
):
    lang_list = languages.split(",") if languages else ["en"]
    lang_list = [lang.strip() for lang in lang_list]

    try:
        transcript_list = ytt_api.list(video_id)
        transcript = transcript_list.find_transcript(lang_list)

        if translate_to:
            transcript = transcript.translate(translate_to)

        fetched = transcript.fetch()

        fmt = format.lower()
        if fmt == "text":
            formatter = TextFormatter()
            formatted = formatter.format_transcript(fetched)
            return {"video_id": video_id, "format": "text", "transcript": formatted}
        elif fmt == "srt":
            formatter = SRTFormatter()
            formatted = formatter.format_transcript(fetched)
            return {"video_id": video_id, "format": "srt", "transcript": formatted}
        elif fmt == "webvtt":
            formatter = WebVTTFormatter()
            formatted = formatter.format_transcript(fetched)
            return {"video_id": video_id, "format": "webvtt", "transcript": formatted}
        else:
            return {"video_id": video_id, "transcript": fetched}

    except NoTranscriptFound:
        raise HTTPException(
            status_code=404,
            detail="No transcript found. This video may not have subtitles or is a Shorts video.",
        )
    except TranscriptsDisabled:
        raise HTTPException(
            status_code=403,
            detail="Transcripts are disabled for this video.",
        )
    except Exception as e:
        import traceback
        print(f"Error fetching transcript for {video_id}: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
