# backend.py — Whisper-tiny + Gemini 2.5 Flash Lite structured meeting summarizer
# with follow-up email, WhatsApp summary, multi-language (on demand),
# speaker diarization, and speaker name detection.

import os
import json
import re
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware

from pydub import AudioSegment
from faster_whisper import WhisperModel

# -----------------------------
# 1. GEMINI CONFIG (FIXED)
# -----------------------------
import google.generativeai as genai

# Hardcoded Gemini API key  🔥 (you can replace this if needed)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL_NAME = "models/gemini-2.5-flash-lite"
GEMINI_MAX_TOKENS = 1200
GEMINI_TEMPERATURE = 0.0
OLLAMA_TIMEOUT = 300  # not used here but left for parity

# Upload limit (2GB)
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024

# Diarization gap threshold (seconds) — not used directly but kept for future
DIARIZATION_GAP_THRESHOLD = 0.9

# ---------- Validate key ----------
if not GEMINI_API_KEY:
    raise RuntimeError(
        "Gemini API key missing. Set environment variable GEMINI_API_KEY "
        "or set GEMINI_API_KEY in this file."
    )

# ---------- Gemini setup ----------
try:
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_MODEL = genai.GenerativeModel(GEMINI_MODEL_NAME)
    print(f"✅ Gemini initialized with model: {GEMINI_MODEL_NAME}")
except Exception as e:
    raise RuntimeError(f"Failed to configure Gemini: {e}")


# -----------------------------
# 2. FASTAPI APP
# -----------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# 3. WHISPER (TINY) LOAD
# -----------------------------
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE = "int8"

print(f"Loading faster-whisper (tiny) | device={WHISPER_DEVICE} compute={WHISPER_COMPUTE} ...")
whisper_model = WhisperModel(
    "tiny",
    device=WHISPER_DEVICE,
    compute_type=WHISPER_COMPUTE,
    cpu_threads=os.cpu_count() or 4,
)
print("✅ Whisper (tiny) loaded.")


# -----------------------------
# 4. AUDIO HELPERS
# -----------------------------
def convert_to_wav(path: Path) -> Path:
    """
    Convert any supported audio file to mono 16k WAV.
    """
    audio = AudioSegment.from_file(path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    out = path.with_suffix(".wav")
    audio.export(out, format="wav")
    return out


def transcribe_audio(wav_path: Path):
    """
    Transcribe audio using faster-whisper tiny and also return diarization segments.
    Each segment: {start, end, text}
    """
    segments, info = whisper_model.transcribe(
        str(wav_path),
        beam_size=1,
        vad_filter=True,
        vad_parameters={"threshold": 0.4},
    )

    transcript_parts = []
    diarization: List[Dict[str, Any]] = []

    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        transcript_parts.append(text)
        diarization.append(
            {
                "start": float(seg.start),
                "end": float(seg.end),
                "text": text,
            }
        )

    transcript = " ".join(transcript_parts)
    return transcript.strip(), diarization


# -----------------------------
# 5. LOCAL FALLBACK EXTRACTOR
# -----------------------------
TASK_PATTERNS = [
    r"([A-Z][a-z]+)\s+(?:will|should|needs to|is going to|must|has to)\s+(.+?)(?:\.|$)",
    r"([A-Z][a-z]+)\s*:\s*(?:will|should|needs to|must)\s+(.+?)(?:\.|$)",
    r"([A-Z][a-z]+)\s+(?:assigned|tasked)\s+to\s+(.+?)(?:\.|$)",
]

DEADLINE_PATTERNS = [
    r"by\s+[A-Za-z]+\s*\d*",
    r"by\s+end of week",
    r"by\s+tomorrow",
    r"by\s+next week",
    r"by\s+Friday",
    r"by\s+Monday",
    r"by\s+Thursday",
    r"by\s+Sunday",
    r"before\s+next\s+meeting",
]


def local_extract(text: str) -> Dict[str, Any]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary = " ".join(sentences[:3])

    action_points: List[str] = []
    tasks: List[Dict[str, Optional[str]]] = []
    deadlines: List[str] = []

    for s in sentences:
        sl = s.lower()

        # Rough action point detector
        if any(k in sl for k in ["should", "need to", "must", "will", "targeting", "aim to"]):
            action_points.append(s)

        # Task patterns
        for pat in TASK_PATTERNS:
            m = re.search(pat, s)
            if m:
                assignee = m.group(1)
                task = m.group(2)
                deadline = None
                for dp in DEADLINE_PATTERNS:
                    md = re.search(dp, s, re.IGNORECASE)
                    if md:
                        deadline = md.group(0)
                        deadlines.append(deadline)
                        break
                tasks.append(
                    {
                        "speaker": assignee,
                        "assignee": assignee,
                        "task": task.strip(),
                        "deadline": deadline,
                        "source": s,
                    }
                )

        # Deadlines even if no tasks
        for dp in DEADLINE_PATTERNS:
            md = re.search(dp, s, re.IGNORECASE)
            if md:
                deadlines.append(md.group(0))

    return {
        "summary": summary.strip() or "No summary available.",
        "action_points": list(dict.fromkeys(action_points)),
        "tasks": tasks,
        "deadlines": list(dict.fromkeys(deadlines)),
        # local extractor doesn't know speakers list; leave empty
        "speakers": [],
    }


# -----------------------------
# 6. GEMINI STRUCTURED EXTRACT
# -----------------------------
def gemini_extract_structured(text: str) -> Dict[str, Any]:
    """
    Use Gemini 2.5 Flash Lite to extract structured summary.
    Raises RuntimeError if anything fails.
    """
    if GEMINI_MODEL is None:
        raise RuntimeError("Gemini model not initialized (API key missing or invalid).")

    prompt = f"""
You are an expert AI meeting assistant.

Read the following meeting transcript and return ONLY valid JSON with EXACTLY these keys:

{{
  "summary": "string, 3–6 sentences summarizing the meeting",
  "action_points": [
    "bullet point action item 1",
    "bullet point action item 2"
  ],
  "tasks": [
    {{
      "speaker": "who spoke this task (e.g., John, Priya, Lead)",
      "assignee": "who is responsible (can be same as speaker)",
      "task": "what must be done",
      "deadline": "short deadline phrase like 'Thursday', 'end of this week', or null if no deadline",
      "source": "short quote from the transcript that supports this task"
    }}
  ],
  "deadlines": [
    "Thursday",
    "Monday",
    "end of this week"
  ],
  "speakers": [
    "unique speaker name 1",
    "unique speaker name 2"
  ]
}}

Rules:
- Use names exactly as they appear in the transcript (John, Priya, Amit, Sarah, Lead, etc.).
- If someone introduces themselves (e.g., "Hi, I'm Rahul"), detect that and add "Rahul" as a speaker.
- Do NOT hallucinate tasks or deadlines that are not implied by the transcript.
- If a task has no clear deadline, set "deadline": null.
- "speakers" must be a de-duplicated list of canonical speaker names detected from the transcript.
- Return ONLY JSON. No markdown, no extra commentary.

Transcript:
{text}
"""

    try:
        response = GEMINI_MODEL.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": GEMINI_MAX_TOKENS,
            },
        )
        content = response.text or ""

        # Try to isolate JSON object
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("Gemini did not return a JSON object.")

        json_str = content[start: end + 1]
        parsed = json.loads(json_str)

        # Sanity defaults
        parsed.setdefault("summary", "No summary available.")
        parsed.setdefault("action_points", [])
        parsed.setdefault("tasks", [])
        parsed.setdefault("deadlines", [])
        parsed.setdefault("speakers", [])

        return parsed

    except Exception as e:
        raise RuntimeError(f"Gemini call failed: {e}")


# -----------------------------
# 7. GEMINI EXTRA FEATURES
# -----------------------------
def gemini_generate_followup_email(summary: str, tasks: List[Dict[str, Any]]) -> str:
    """
    Generate a professional follow-up email for the meeting.
    """
    if GEMINI_MODEL is None:
        return "Gemini not available for email generation."

    prompt = f"""
You are an expert meeting assistant.

Write a professional follow-up email based on the meeting summary and tasks below.

Rules:
- Tone: clear, concise, corporate, but friendly.
- Structure:
  - Subject line suggestion.
  - Greeting.
  - 2–3 lines summarizing meeting purpose and outcomes.
  - Bullet list of action items with owners & deadlines.
  - Closing line thanking participants and inviting questions.
- Do NOT hallucinate information that is not in the summary or tasks.
- Use only the details provided.

MEETING SUMMARY:
{summary}

TASKS (JSON):
{json.dumps(tasks, indent=2)}

Return only the email body text (no markdown, no JSON).
"""

    try:
        resp = GEMINI_MODEL.generate_content(
            prompt,
            generation_config={
                "temperature": GEMINI_TEMPERATURE,
                "max_output_tokens": GEMINI_MAX_TOKENS,
            },
        )
        return (resp.text or "").strip()
    except Exception as e:
        return f"Email generation failed: {e}"


def gemini_generate_whatsapp(summary: str) -> str:
    """
    Generate a short WhatsApp-style recap message.
    """
    if GEMINI_MODEL is None:
        return "Gemini not available for WhatsApp summary."

    prompt = f"""
Convert the following meeting summary into a short WhatsApp-style recap message.

Rules:
- 3–6 short bullet-like lines.
- Simple language.
- Add relevant emojis (2–6 total) where natural.
- Focus on decisions and key next steps.
- No greeting or signature.
- No markdown bullets, just plain text lines.

MEETING SUMMARY:
{summary}

Return only the message text.
"""
    try:
        resp = GEMINI_MODEL.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 300,
            },
        )
        return (resp.text or "").strip()
    except Exception as e:
        return f"WhatsApp summary failed: {e}"


def gemini_translate_summary(summary: str, target_lang: str) -> str:
    """
    Translate summary into target_lang when requested.
    """
    if GEMINI_MODEL is None:
        return summary

    if not target_lang:
        return summary

    prompt = f"""
Translate the meeting summary below into {target_lang}.

Rules:
- Preserve meaning exactly.
- Keep it concise and natural for native speakers.
- No extra explanations or comments.

SUMMARY:
{summary}
"""

    try:
        resp = GEMINI_MODEL.generate_content(
            prompt,
            generation_config={
                "temperature": 0.0,
                "max_output_tokens": 400,
            },
        )
        text = (resp.text or "").strip()
        return text or summary
    except Exception:
        # If translation fails, just return original
        return summary


# -----------------------------
# 8. MARKDOWN FORMATTER (⿡ ⿢ ⿣ ⿤ FORMAT)
# -----------------------------
def format_markdown_block(
    data: Dict[str, Any],
    followup_email: str,
    whatsapp_msg: str,
) -> str:
    """
    Create a single markdown block that explains the whole flow in the exact format:

    
        - Summary
        - Action points
        - Tasks assigned to specific people
        - Deadlines
        - Follow-up emails
    ⿤ Sends it to:
        - WhatsApp
        - Email
    """

    summary = data.get("summary", "No summary available.")
    action_points = data.get("action_points") or []
    tasks = data.get("tasks") or []
    deadlines = data.get("deadlines") or []

    out = ""


    # Summary
    out += "- **Summary**\n"
    out += f"  - {summary}\n\n"

    # Action points
    out += "- **Action points**\n"
    if action_points:
        for a in action_points:
            out += f"  - {a}\n"
    else:
        out += "  - None detected.\n"
    out += "\n"

    # Tasks
    out += "- **Tasks assigned to specific people**\n"
    if tasks:
        for t in tasks:
            assignee = t.get("assignee") or t.get("speaker") or "Unknown"
            task_text = t.get("task") or ""
            deadline = t.get("deadline") or "No deadline"
            out += f"  - **{assignee}** → {task_text} _(Deadline: {deadline})_\n"
    else:
        out += "  - No explicit tasks found.\n"
    out += "\n"

    # Deadlines
    out += "- **Deadlines**\n"
    if deadlines:
        for d in deadlines:
            out += f"  - {d}\n"
    else:
        out += "  - None mentioned.\n"
    out += "\n"

    # Follow-up email
    out += "- **Follow-up emails**\n"
    if followup_email and not followup_email.lower().startswith("email generation failed"):
        out += "  - Draft ready below:\n\n"
        out += "```text\n"
        out += followup_email.strip() + "\n"
        out += "```\n"
    else:
        out += "  - Could not generate email.\n"
    out += "\n"

    # ⿤ Sends it to
    out += "⿤ **Sends it to**\n"
    # WhatsApp
    out += "- **WhatsApp** — copy & paste this recap:\n\n"
    if whatsapp_msg and not whatsapp_msg.lower().startswith("whatsapp summary failed"):
        out += "```text\n"
        out += whatsapp_msg.strip() + "\n"
        out += "```\n"
    else:
        out += "_No WhatsApp summary generated._\n"
    out += "\n"

    # Email
    out += "- **Email** — use the follow-up email draft above to send to participants.\n"

    return out


# -----------------------------
# 9. API ENDPOINT
# -----------------------------
@app.post("/summarize")
async def summarize_meeting(
    audio: UploadFile = File(...),
    target_lang: Optional[str] = Form(None),
):
    """
    Main endpoint:
    - Transcribe audio
    - Extract structured summary (Gemini + fallback)
    - Generate follow-up email + WhatsApp message
    - Optionally translate summary if target_lang is provided
    - Return diarization + speaker list
    """
    # Save uploaded file to temp
    tmp_path = Path(tempfile.gettempdir()) / f"up_{audio.filename}"

    with open(tmp_path, "wb") as f:
        while True:
            chunk = await audio.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)

    if not tmp_path.exists():
        raise HTTPException(status_code=400, detail="Failed to save uploaded file.")

    try:
        wav_path = convert_to_wav(tmp_path)
        transcript, diarization = transcribe_audio(wav_path)

        if not transcript.strip():
            raise HTTPException(status_code=400, detail="Transcription is empty.")

        note = ""
        try:
            extracted = gemini_extract_structured(transcript)
        except Exception as e:
            # Fallback to local extractor if Gemini fails
            note = f"Note: Gemini failed, using local extraction instead. ({e})"
            extracted = local_extract(transcript)

        # Extra Gemini features
        summary_text = extracted.get("summary", "")
        tasks = extracted.get("tasks", [])

        followup_email = gemini_generate_followup_email(summary_text, tasks)
        whatsapp_msg = gemini_generate_whatsapp(summary_text)

        # Multi-language support: only if user explicitly selects a language
        translated_summary: Optional[str] = None
        if target_lang and target_lang.lower() not in ["none", "original", "auto"]:
            translated_summary = gemini_translate_summary(summary_text, target_lang)

        # ⿡ ⿢ ⿣ ⿤ formatted summary
        structured_markdown = format_markdown_block(
            extracted,
            followup_email=followup_email,
            whatsapp_msg=whatsapp_msg,
        )

        return {
            "transcript": transcript,
            "diarization": diarization,
            "summary": summary_text,
            "action_points": extracted.get("action_points", []),
            "tasks": tasks,
            "deadlines": extracted.get("deadlines", []),
            "speakers": extracted.get("speakers", []),
            "structured_summary": structured_markdown,
            "followup_email": followup_email,
            "whatsapp": whatsapp_msg,
            "translated_summary": translated_summary,
            "target_lang": target_lang,
            "note": note,
        }

    finally:
        # Cleanup
        try:
            if tmp_path.exists():
                tmp_path.unlink()
            if "wav_path" in locals() and wav_path.exists():
                wav_path.unlink()
        except Exception:
            pass


# -----------------------------
# 10. RUN SERVER
# -----------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend:app", host="0.0.0.0", port=8000, log_level="info")
