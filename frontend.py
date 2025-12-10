# frontend.py – Enhanced Dark UI with Professional Color Sync

import streamlit as st
import requests
from audiorecorder import audiorecorder
import io
import wave

BACKEND_URL = "http://localhost:8000/summarize"

st.set_page_config(
    page_title="Smart Meeting Assistant",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS with Professional Color Synchronization
st.markdown("""
<style>
    /* CSS Variables for Consistent Colors */
    :root {
        --primary-purple: #6366f1;
        --secondary-purple: #8b5cf6;
        --dark-bg: #1e1b4b;
        --darker-bg: #1a1744;
        --glass-bg: rgba(99, 102, 241, 0.08);
        --glass-border: rgba(139, 92, 246, 0.2);
        --text-primary: #f1f5f9;
        --text-secondary: #cbd5e1;
        --text-muted: #94a3b8;
        --success: #10b981;
        --warning: #f59e0b;
        --error: #ef4444;
    }

    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Container padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }
    
    /* Title styling with gradient */
    h1 {
        background: linear-gradient(135deg, var(--primary-purple) 0%, var(--secondary-purple) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3.5rem !important;
        font-weight: 800 !important;
        text-align: center;
        margin-bottom: 10px;
        filter: drop-shadow(0 0 30px rgba(99, 102, 241, 0.4));
    }
    
    /* Subtitle styling */
    .subtitle {
        text-align: center;
        color: var(--text-secondary);
        font-size: 1.2rem;
        margin-bottom: 50px;
        font-weight: 400;
    }
    
    /* Subheaders */
    h2, h3 {
        color: var(--text-primary) !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }
    
    /* Tab styling with synchronized colors */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background: rgba(30, 27, 75, 0.5);
        padding: 10px;
        border-radius: 16px;
        backdrop-filter: blur(10px);
        border: 1px solid var(--glass-border);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 12px;
        color: var(--text-muted);
        padding: 16px 32px;
        font-weight: 600;
        font-size: 1.05rem;
        border: 1px solid transparent;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: var(--glass-bg);
        color: var(--text-secondary);
        border-color: rgba(99, 102, 241, 0.3);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary-purple) 0%, var(--secondary-purple) 100%) !important;
        color: white !important;
        border: 1px solid transparent !important;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
    }
    
    /* Button styling with gradient */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-purple) 0%, var(--secondary-purple) 100%);
        color: white;
        border: none;
        padding: 18px 40px;
        font-size: 1.2rem;
        font-weight: 700;
        border-radius: 50px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 6px 25px rgba(99, 102, 241, 0.4);
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 35px rgba(99, 102, 241, 0.6);
    }
    
    .stButton > button:active {
        transform: translateY(0px);
    }
    
    /* File uploader container */
    .stFileUploader {
        background: rgba(30, 27, 75, 0.4);
        border-radius: 20px;
        padding: 30px;
        border: 2px dashed var(--glass-border);
        transition: all 0.3s ease;
    }
    
    .stFileUploader:hover {
        border-color: var(--primary-purple);
        background: var(--glass-bg);
    }
    
    /* File uploader - ALL TEXT VISIBLE */
    .stFileUploader label,
    .stFileUploader label span,
    .stFileUploader div,
    .stFileUploader p,
    .stFileUploader span {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }
    
    /* File uploader dropzone */
    .stFileUploader [data-testid="stFileUploaderDropzone"] {
        background: transparent !important;
        border: none !important;
    }
    
    /* File uploader dropzone instructions - CRITICAL FIX */
    .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] p,
    .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] span,
    .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] div {
        color: var(--text-secondary) !important;
        font-size: 1.05rem !important;
        font-weight: 500 !important;
    }
    
    /* Uploaded file name visibility */
    .stFileUploader [data-testid="stFileUploaderFileName"] {
        color: var(--success) !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        background: rgba(16, 185, 129, 0.1) !important;
        padding: 8px 12px !important;
        border-radius: 8px !important;
    }
    
    /* File uploader delete button */
    .stFileUploader [data-testid="stFileUploaderDeleteBtn"] {
        color: var(--text-primary) !important;
    }
    
    /* File uploader button - Browse files button */
    .stFileUploader button {
        background: linear-gradient(135deg, var(--primary-purple) 0%, var(--secondary-purple) 100%) !important;
        color: white !important;
        border: none !important;
        padding: 12px 28px !important;
        border-radius: 25px !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4) !important;
    }
    
    .stFileUploader button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6) !important;
    }
    
    /* File uploader small text */
    .stFileUploader small {
        color: var(--text-muted) !important;
        font-size: 0.95rem !important;
    }
    
    /* Text area styling */
    .stTextArea textarea {
        background: rgba(30, 27, 75, 0.4) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 12px !important;
        color: var(--text-primary) !important;
        backdrop-filter: blur(10px);
        font-size: 0.95rem;
        line-height: 1.7;
        font-family: 'Segoe UI', system-ui, sans-serif;
    }
    
    .stTextArea textarea:focus {
        border-color: var(--primary-purple) !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.3) !important;
        outline: none !important;
    }
    
    .stTextArea label {
        color: var(--text-primary) !important;
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 8px;
    }
    
    /* Info/Success/Warning boxes with synchronized colors */
    .stAlert {
        background: var(--glass-bg) !important;
        backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 1px solid var(--glass-border);
        color: var(--text-primary) !important;
        padding: 16px 20px;
    }
    
    /* Success alert */
    [data-baseweb="notification"][kind="success"],
    .stSuccess {
        background: rgba(16, 185, 129, 0.15) !important;
        border-left: 4px solid var(--success) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
    }
    
    /* Info alert */
    [data-baseweb="notification"][kind="info"],
    .stInfo {
        background: rgba(99, 102, 241, 0.15) !important;
        border-left: 4px solid var(--primary-purple) !important;
        border: 1px solid var(--glass-border) !important;
    }
    
    /* Warning alert */
    [data-baseweb="notification"][kind="warning"],
    .stWarning {
        background: rgba(245, 158, 11, 0.15) !important;
        border-left: 4px solid var(--warning) !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
    }
    
    /* Error alert */
    [data-baseweb="notification"][kind="error"],
    .stError {
        background: rgba(239, 68, 68, 0.15) !important;
        border-left: 4px solid var(--error) !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
    }
    
    /* Markdown styling - ENSURE TEXT IS VISIBLE */
    .stMarkdown {
        color: var(--text-secondary) !important;
        line-height: 1.8;
    }
    
    .stMarkdown p {
        color: var(--text-secondary) !important;
        font-size: 1.05rem;
        margin-bottom: 16px;
        line-height: 1.8;
    }
    
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        color: var(--text-primary) !important;
        margin-top: 24px;
        margin-bottom: 16px;
    }
    
    .stMarkdown strong {
        color: var(--primary-purple) !important;
        font-weight: 700;
    }
    
    .stMarkdown ul, .stMarkdown ol {
        color: var(--text-secondary) !important;
        margin-left: 20px;
        margin-bottom: 16px;
    }
    
    .stMarkdown li {
        margin-bottom: 8px;
        line-height: 1.7;
    }
    
    /* Task cards styling */
    .stMarkdown hr {
        border: none;
        height: 1px;
        background: var(--glass-border);
        margin: 24px 0;
    }
    
    /* Audio player */
    audio {
        width: 100%;
        border-radius: 12px;
        background: rgba(30, 27, 75, 0.4);
        border: 1px solid var(--glass-border);
        margin-top: 15px;
    }
    
    /* --- FIX SPINNER COLOR & REMOVE BOX --- */
    .stSpinner > div {
        border: 4px solid rgba(255, 255, 255, 0.2) !important;
        border-top-color: white !important;
        border-right-color: white !important;
    }

    .stSpinner > div + div {
        color: white !important;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
    }

    /* Remove any background box around spinner */
    div[data-testid="stSpinner"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    
    /* JSON viewer */
    .stJson {
        background: rgba(0, 0, 0, 0.3) !important;
        border-radius: 12px;
        border: 1px solid var(--glass-border);
        color: var(--text-secondary) !important;
        padding: 20px;
    }
    
    /* Section dividers */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--glass-border), transparent);
        margin: 40px 0;
    }
    
    /* Hover glow effects */
    .stButton > button:hover,
    .stTabs [data-baseweb="tab"]:hover {
        box-shadow: 0 0 25px rgba(99, 102, 241, 0.5);
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(30, 27, 75, 0.3);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, var(--primary-purple) 0%, var(--secondary-purple) 100%);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, var(--secondary-purple) 0%, var(--primary-purple) 100%);
    }
    
    /* Audio recorder button styling */
    [data-testid="stAudioRecorder"] button {
        background: linear-gradient(135deg, var(--primary-purple) 0%, var(--secondary-purple) 100%) !important;
        color: white !important;
        border: none !important;
        padding: 14px 28px !important;
        border-radius: 30px !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4) !important;
    }
    
    [data-testid="stAudioRecorder"] button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6) !important;
    }
    
    /* Better text visibility in all elements */
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stText"],
    .stMarkdown,
    label {
        color: var(--text-secondary) !important;
    }
    
    /* Override for file uploader section - FORCE VISIBILITY */
    section[data-testid="stFileUploadDropzone"] div,
    section[data-testid="stFileUploadDropzone"] p,
    section[data-testid="stFileUploadDropzone"] span,
    section[data-testid="stFileUploadDropzone"] label {
        color: var(--text-primary) !important;
        opacity: 1 !important;
    }
    
    /* Drag and drop text */
    [data-testid="stFileUploaderDropzone"] > div > div {
        color: var(--text-primary) !important;
    }
</style>
""", unsafe_allow_html=True)

# Header with emoji icon
st.markdown("<h1> Smart Meeting Assistant</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Transform your meetings into actionable insights with AI-powered analysis</p>", unsafe_allow_html=True)

# Choose Input Method Section
st.markdown("---")
st.subheader(" Choose Input Method")

tab_upload, tab_record = st.tabs([" Upload Audio", " Real Time Record"])

# OPTION A – UPLOAD AUDIO
with tab_upload:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Upload your meeting audio file")
    st.markdown("Supported formats: **MP3, WAV, M4A, FLAC, OGG**")
    st.markdown("<br>", unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Drag and drop file here or click to browse",
        type=["wav", "mp3", "m4a", "ogg", "flac"],
        label_visibility="collapsed"
    )

    if uploaded_file:
        st.success(f" File loaded: **{uploaded_file.name}**")
        st.audio(uploaded_file, format="audio/wav")

# OPTION B – LIVE RECORD AUDIO
with tab_record:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Record your meeting in real-time")
    st.info(" **Tip:** Find a quiet environment for best recording quality")
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        audio = audiorecorder(" Start Recording", " Stop Recording")

    recorded_audio = None

    if len(audio) > 0:
        st.success(" Recording captured successfully!")

        # Convert raw PCM data into a VALID WAV file
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(audio.channels)
            wav_file.setsampwidth(audio.sample_width)
            wav_file.setframerate(audio.frame_rate)
            wav_file.writeframes(audio.raw_data)

        recorded_audio = wav_buffer.getvalue()

        # Play back the valid WAV
        st.audio(recorded_audio, format="audio/wav")

# Decide which input will be processed
audio_bytes = None
filename = None

if uploaded_file:
    audio_bytes = uploaded_file.getvalue()
    filename = uploaded_file.name

elif recorded_audio:
    audio_bytes = recorded_audio
    filename = "live_recording.wav"

# Submit Button
if audio_bytes:
    st.markdown("---")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(" Process Meeting with AI"):
        with st.spinner(" AI is transcribing and analyzing your meeting..."):
            try:
                files = {
                    "audio": (
                        filename,
                        audio_bytes,
                        "audio/wav",
                    )
                }

                # Send to backend
                response = requests.post(BACKEND_URL, files=files, timeout=600)

                if response.status_code != 200:
                    st.error(f" Backend error ({response.status_code}): {response.text}")
                else:
                    data = response.json()

                    if data.get("note"):
                        st.warning(f" {data['note']}")

                    # MAIN SUMMARY
                    st.markdown("---")
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("<h2 style='color:#ffffff;font-weight:800;'> Meeting Summary</h2>", unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Display summary in a styled box
                    summary_content = data.get("structured_summary", "_No summary returned._")

                    st.markdown(
                        f"""
                        <div style='background: rgba(99, 102, 241, 0.08); 
                                    padding: 24px; 
                                    border-radius: 14px; 
                                    border: 1px solid rgba(139, 92, 246, 0.2);
                                    color: #e2e8f0;
                                    line-height: 1.8;
                                    font-size: 1.1rem;'>
                            <span style='color:#7c3aed; font-weight:700; font-size:1.3rem;'>SUMMARY</span><br><br>
                            <span style='color:#e2e8f0; font-weight:400;'>{summary_content}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


                    # TABS FOR DETAILS
                    st.markdown("---")
                    st.markdown("<br>", unsafe_allow_html=True)
                    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
                        [
                            " Transcript",
                            " Action Points",
                            " Tasks",
                            " Follow-up Email",
                            " WhatsApp Message",
                            " Diarization",
                        ]
                    )

                    # Transcript
                    with tab1:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown("### Full Meeting Transcript")
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.text_area(
                            "Transcript content",
                            data.get("transcript", ""),
                            height=400,
                            label_visibility="collapsed"
                        )

                    # Action points
                    with tab2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        aps = data.get("action_points", [])
                        if aps:
                            st.markdown("### Key Action Points")
                            st.markdown("<br>", unsafe_allow_html=True)
                            for i, ap in enumerate(aps, 1):
                                st.markdown(f"""
                                <div style='background: rgba(99, 102, 241, 0.08); 
                                            padding: 16px 20px; 
                                            border-radius: 12px; 
                                            margin-bottom: 12px; 
                                            border-left: 4px solid #6366f1;'>
                                    <strong style='color: #6366f1; font-size: 1.1rem;'>{i}.</strong> 
                                    <span style='color: #cbd5e1; font-size: 1.05rem;'>{ap}</span>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info(" No action points detected.")

                    # Tasks
                    with tab3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        tasks = data.get("tasks", [])
                        if tasks:
                            st.markdown("### Assigned Tasks")
                            st.markdown("<br>", unsafe_allow_html=True)
                            for i, t in enumerate(tasks, 1):
                                st.markdown(
                                    f"""
                                    <div style='background: rgba(99, 102, 241, 0.08); 
                                                padding: 20px 24px; 
                                                border-radius: 14px; 
                                                margin-bottom: 18px; 
                                                border-left: 4px solid #6366f1;'>
                                        <h4 style='color: #6366f1; margin-bottom: 12px; font-size: 1.2rem;'>Task {i}</h4>
                                        <p style='color: #cbd5e1; margin-bottom: 8px; font-size: 1.05rem;'>
                                            <strong style='color: #f1f5f9;'> Assignee:</strong> {t.get('assignee') or t.get('speaker') or 'Unknown'}
                                        </p>
                                        <p style='color: #cbd5e1; margin-bottom: 8px; font-size: 1.05rem;'>
                                            <strong style='color: #f1f5f9;'> Task:</strong> {t.get('task')}
                                        </p>
                                        <p style='color: #cbd5e1; margin-bottom: 0; font-size: 1.05rem;'>
                                            <strong style='color: #f1f5f9;'> Deadline:</strong> {t.get('deadline') or 'No deadline specified'}
                                        </p>
                                    </div>
                                    """, unsafe_allow_html=True
                                )
                        else:
                            st.info(" No tasks found.")

                    # Follow-up Email
                    with tab4:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown("###  Follow-up Email")
                        st.markdown("Copy the email below and send it to your team")
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.text_area(
                            "Email content",
                            data.get("followup_email", ""),
                            height=350,
                            label_visibility="collapsed"
                        )

                    # WhatsApp Summary
                    with tab5:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown("###  WhatsApp Message")
                        st.markdown("Quick summary ready to share on WhatsApp")
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.text_area(
                            "WhatsApp content",
                            data.get("whatsapp", ""),
                            height=250,
                            label_visibility="collapsed"
                        )

                    # Diarization
                    with tab6:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown("###  Speaker Identification")
                        st.markdown("Timeline and speaker information")
                        st.markdown("<br>", unsafe_allow_html=True)
                        diar = data.get("diarization", [])
                        if diar:
                            st.json(diar)
                        else:
                            st.info(" No diarization data available.")

            except Exception as e:
                st.error(f" Unexpected error: {e}")

else:
    st.markdown("---")
    st.markdown("<br>", unsafe_allow_html=True)
    st.info(" **Upload or record audio** to get started with AI-powered meeting analysis")
    st.markdown("<br><br>", unsafe_allow_html=True)