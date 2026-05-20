import streamlit as st
import time
import os
import re
import base64
import io
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Interview Coach", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background: #0d0d0d;
    color: #e0e0e0;
}
.stApp { background: #0d0d0d; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem; max-width: 1200px; }

h1 {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: #555;
    font-weight: 400;
}

.question-box {
    border-left: 3px solid #c8f542;
    padding: 20px 28px;
    margin: 28px 0;
    font-size: 20px;
    font-weight: 300;
    line-height: 1.6;
    color: #e0e0e0;
    background: #111;
}

.metric-row {
    display: flex;
    border: 1px solid #1e1e1e;
    margin-bottom: 28px;
}
.metric-box {
    flex: 1;
    padding: 18px 22px;
    border-right: 1px solid #1e1e1e;
}
.metric-box:last-child { border-right: none; }
.metric-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #444;
    margin-bottom: 6px;
}
.metric-val {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 26px;
    font-weight: 500;
    color: #c8f542;
}
.metric-val.warn { color: #f5a623; }
.metric-val.bad  { color: #ff4d4d; }

.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #444;
    border-bottom: 1px solid #1e1e1e;
    padding-bottom: 10px;
    margin-bottom: 18px;
    margin-top: 24px;
}

.transcript-area {
    background: #111;
    border: 1px solid #1e1e1e;
    padding: 20px;
    font-size: 14px;
    font-weight: 300;
    line-height: 1.8;
    color: #ccc;
    min-height: 90px;
    margin-bottom: 20px;
}

.eval-section { border: 1px solid #1e1e1e; margin-bottom: 2px; }
.eval-head {
    background: #111;
    padding: 10px 18px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #555;
    border-bottom: 1px solid #1e1e1e;
}
.eval-body {
    padding: 14px 18px;
    font-size: 14px;
    font-weight: 300;
    line-height: 1.7;
    color: #bbb;
}

.filler-tag {
    display: inline-block;
    border: 1px solid #f5a623;
    color: #f5a623;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    padding: 3px 10px;
    margin: 3px;
}

.history-row {
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid #111;
    font-size: 13px;
    color: #555;
}
.history-score { color: #c8f542; font-family: 'IBM Plex Mono', monospace; }

.stButton > button {
    background: #c8f542 !important;
    color: #0d0d0d !important;
    border: none !important;
    border-radius: 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    padding: 12px 28px !important;
    font-weight: 500 !important;
    width: 100% !important;
}
.stButton > button:hover { opacity: 0.8 !important; }

div[data-testid="stSelectbox"] > div {
    background: #111 !important;
    border: 1px solid #1e1e1e !important;
    border-radius: 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
}
</style>
""", unsafe_allow_html=True)

def load_api_key():
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return os.getenv('GROQ_API_KEY', '')

defaults = {
    'chat_history': [],
    'current_question': 'What is the main difference between a List and a Tuple in Python?',
    'round_num': 1,
    'transcript': '',
    'ai_response': '',
    'filler_count': {},
    'total_fillers': 0,
    'answer_duration': 0,
    'scores': [],
    'history_log': [],
    'last_processed_audio_id': None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def get_client():
    from groq import Groq
    api_key = load_api_key()
    if not api_key:
        st.error('GROQ_API_KEY not found. Add it to Streamlit Secrets or .env file.')
        return None
    return Groq(api_key=api_key)

def process_audio_live(audio_buffer):
    client = get_client()
    if not client:
        return None
    try:
        transcript = client.audio.transcriptions.create(
            file=audio_buffer, model='whisper-large-v3', response_format='text'
        )
        return transcript
    except Exception as e:
        st.error(f'Transcription failed: {e}')
        return None

def generate_evaluation(history):
    client = get_client()
    if not client:
        return None
    system_prompt = (
        "You are an elite Technical Interviewer from Google. Maintain a professional, strict persona. "
        "The LAST user message contains the latest question and answer. "
        "You MUST ALWAYS provide evaluation first, then ask next question. NEVER skip evaluation.\n\n"
        "Provide your response in this EXACT format:\n"
        "### Evaluation for Previous Answer\n"
        "- **Technical Accuracy:** [Score]/10\n"
        "- **Confidence Level:** [High/Medium/Low]\n"
        "- **Answer Structure:** [Structured/Unstructured]\n"
        "- **Feedback:** [1 brief sentence on what to improve]\n\n"
        "### Next Interview Question\n"
        "[STRICTLY ask from Python, Data Science, Machine Learning or Deep Learning ONLY. "
        "Ask CONCEPTUAL questions only, not coding assignments. "
        "Questions must be answerable verbally in 1-2 sentences. Do NOT ask DSA. ONE question only.]"
    )
    try:
        response = client.chat.completions.create(
            messages=[{'role': 'system', 'content': system_prompt}] + history,
            model='llama-3.1-8b-instant',
            temperature=0.4
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f'AI evaluation failed: {e}')
        return None

def count_fillers(text):
    filler_words = ['um', 'uh', 'like', 'basically', 'you know', 'actually', 'so']
    words = text.lower().split()
    count = {w: words.count(w) for w in filler_words if words.count(w) > 0}
    return count, sum(count.values())

def extract_score(response):
    match = re.search(r'Technical Accuracy.*?(\d+)/10', response)
    return int(match.group(1)) if match else 0

def extract_next_question(response):
    if '### Next Interview Question' in response:
        return response.split('### Next Interview Question')[1].strip()
    return 'Can you explain the difference between supervised and unsupervised learning?'

def speak(text):
    from gtts import gTTS
    clean = text.replace('*', '').replace('#', '')
    tts = gTTS(text=clean, lang='en', tld='com')
    audio_buffer = io.BytesIO()
    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)
    b64 = base64.b64encode(audio_buffer.read()).decode()
    st.markdown(f'<audio autoplay><source src="data:audio/mp3;base64,{b64}"></audio>', unsafe_allow_html=True)

def avg_score():
    if not st.session_state.scores:
        return 0
    return round(sum(st.session_state.scores) / len(st.session_state.scores), 1)

with st.sidebar:
    st.markdown('<div class="section-label">Topic</div>', unsafe_allow_html=True)
    starters = {
        'Python Basics':    'What is the main difference between a List and a Tuple in Python?',
        'Data Science':     'What is the difference between correlation and causation?',
        'Machine Learning': 'What is overfitting and how do you prevent it?',
        'Deep Learning':    'What is the vanishing gradient problem in neural networks?',
    }
    selected = st.selectbox('Topic', list(starters.keys()), label_visibility='collapsed')
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    if st.button('Start New Interview'):
        for k, v in defaults.items():
            st.session_state[k] = v
        st.session_state.current_question = starters[selected]
        st.rerun()

st.markdown(f'<h1>Interview Coach / Round {st.session_state.round_num:02d}</h1>', unsafe_allow_html=True)
st.markdown(f'<div class="question-box">{st.session_state.current_question}</div>', unsafe_allow_html=True)

dur = int(st.session_state.answer_duration)
dur_class = 'warn' if dur < 20 and dur > 0 else ''
fil_class = 'bad' if st.session_state.total_fillers > 5 else 'warn' if st.session_state.total_fillers > 0 else ''

st.markdown(f"""
<div class="metric-row">
    <div class="metric-box">
        <div class="metric-title">Duration</div>
        <div class="metric-val {dur_class}">{dur}s</div>
    </div>
    <div class="metric-box">
        <div class="metric-title">Filler Words</div>
        <div class="metric-val {fil_class}">{st.session_state.total_fillers}</div>
    </div>
    <div class="metric-box">
        <div class="metric-title">Avg Score</div>
        <div class="metric-val">{avg_score()}/10</div>
    </div>
    <div class="metric-box">
        <div class="metric-title">Rounds Done</div>
        <div class="metric-val">{len(st.session_state.history_log)}</div>
    </div>
</div>
""", unsafe_allow_html=True)

col_left, col_right = st.columns([1, 1], gap='large')

with col_left:
    st.markdown('<div class="section-label">Record Your Answer Live</div>', unsafe_allow_html=True)

    from streamlit_mic_recorder import mic_recorder

    audio = mic_recorder(
        start_prompt='Click to Speak',
        stop_prompt='Stop & Submit',
        just_once=True,
        use_container_width=True,
        key='mic'
    )

    if audio and audio['id'] != st.session_state.last_processed_audio_id:
        st.session_state.last_processed_audio_id = audio['id']
        live_audio_file = io.BytesIO(audio['bytes'])
        live_audio_file.name = 'live_response.wav'
        start_time = time.time()
        with st.spinner('Transcribing...'):
            transcript = process_audio_live(live_audio_file)
            duration = round(time.time() - start_time, 2)
        if transcript:
            st.session_state.transcript = transcript
            st.session_state.answer_duration = max(duration, len(transcript.split()) * 0.4)
            fc, total = count_fillers(transcript)
            st.session_state.filler_count = fc
            st.session_state.total_fillers = total
            st.session_state.chat_history.append({
                'role': 'user',
                'content': f'Question: {st.session_state.current_question}\nAnswer: {transcript}'
            })
            with st.spinner('AI is evaluating...'):
                ai_response = generate_evaluation(st.session_state.chat_history)
            if ai_response:
                st.session_state.ai_response = ai_response
                st.session_state.chat_history.append({'role': 'assistant', 'content': ai_response})
                score = extract_score(ai_response)
                if score:
                    st.session_state.scores.append(score)
                st.session_state.history_log.append({
                    'round': st.session_state.round_num,
                    'question': st.session_state.current_question,
                    'score': score
                })
                st.session_state.current_question = extract_next_question(ai_response)
                st.session_state.round_num += 1
                st.rerun()

    if st.session_state.filler_count:
        st.markdown('<div class="section-label">Filler Words Detected</div>', unsafe_allow_html=True)
        tags = ''.join([f'<span class="filler-tag">{w} x{c}</span>' for w, c in st.session_state.filler_count.items()])
        st.markdown(f'<div>{tags}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Session History</div>', unsafe_allow_html=True)
    if st.session_state.history_log:
        for item in reversed(st.session_state.history_log):
            q_short = item['question'][:55] + '...' if len(item['question']) > 55 else item['question']
            st.markdown(f"""
            <div class="history-row">
                <span>R{item['round']:02d} &nbsp; {q_short}</span>
                <span class="history-score">{item['score']}/10</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<p style="font-family:IBM Plex Mono,monospace;font-size:12px;color:#333;">No rounds logged yet.</p>', unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="section-label">Transcript</div>', unsafe_allow_html=True)
    text = st.session_state.transcript or 'Your spoken words will appear here after processing.'
    st.markdown(f'<div class="transcript-area">{text}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Evaluation</div>', unsafe_allow_html=True)
    if st.session_state.ai_response:
        for section in st.session_state.ai_response.split('###'):
            section = section.strip()
            if not section:
                continue
            lines = section.split('\n', 1)
            head = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ''
            if 'Next Interview Question' in head:
                continue
            st.markdown(f"""
            <div class="eval-section">
                <div class="eval-head">{head}</div>
                <div class="eval-body">{body}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="eval-section">
            <div class="eval-head">Awaiting Answer</div>
            <div class="eval-body" style="color:#333;">Click the mic, speak your answer, results appear automatically.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    if st.button('Read Question Aloud'):
        try:
            speak(st.session_state.current_question)
        except Exception as e:
            st.info(f'TTS error: {e}')
