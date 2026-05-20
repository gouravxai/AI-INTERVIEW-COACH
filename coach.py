import os
from dotenv import load_dotenv
from groq import Groq
from gtts import gTTS
import pygame
import time
import sounddevice as sd
from scipy.io.wavfile import write

load_dotenv()
api_key = os.getenv('GROQ_API_KEY')

if not api_key:
    raise ValueError('GROQ_API_KEY is not found in your .env file')

client = Groq(api_key=api_key)

def speak_text(text):
    clean_text = text.replace('*', '').replace('#', '')
    print(f'\nAI SPEAKING: {clean_text}')
    tts = gTTS(text=clean_text, lang='en', tld='com')
    filename = 'interviewer_voice.mp3'
    tts.save(filename)
    pygame.mixer.init()
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    pygame.mixer.quit()
    if os.path.exists(filename):
        os.remove(filename)

def record_answer(filename='sample_answer.wav', duration=60, samplerate=44100):
    print('Recording started... Speak now!')
    audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
    input()
    sd.stop()
    write(filename, samplerate, audio)
    print('Recording saved!')

def process_audio_ingestion(file_path):
    if not os.path.exists(file_path):
        print(f'\n[Error] File not found: {file_path}')
        return None
    print('[INFO] Transcribing your voice answer via Groq Whisper...')
    try:
        with open(file_path, 'rb') as file:
            transcript = client.audio.transcriptions.create(
                file=file,
                model='whisper-large-v3',
                response_format='text'
            )
        return transcript
    except Exception as e:
        print(f'[Error] Transcription failed: {str(e)}')
        return None

def generate_next_round(conversation_history):
    print('\n[INFO] AI INTERVIEWER IS ANALYSING...')
    system_prompt = (
    "You are an elite Technical Interviewer from Google. Maintain a professional, strict persona. "
    "You will receive a conversation history. The LAST user message contains the latest question and answer.\n\n"
    "You MUST ALWAYS provide evaluation first, then ask next question.\n"
    "NEVER skip the evaluation section.\n\n"
    "Provide your response in this EXACT format:\n"
    "### Evaluation for Previous Answer\n"
    "- **Technical Accuracy:** [Score]/10\n"
    "- **Confidence Level:** [High/Medium/Low]\n"
    "- **Answer Structure:** [Structured/Unstructured]\n"
    "- **Feedback:** [1 brief sentence on what to improve]\n\n"
    "### Next Interview Question\n"
    "[STRICTLY ask from Python, Data Science, Machine Learning or Deep Learning ONLY. NO DSA. ONE question only.]"
    "Ask CONCEPTUAL questions only, not coding assignments. "
    "For example: 'What is overfitting?' not 'Implement a neural network'. "
    "Candidate is answering VERBALLY via voice, so questions must be answerable in 1-2 spoken sentences."
)
    try:
        response = client.chat.completions.create(
            messages=[{'role': 'system', 'content': system_prompt}] + conversation_history,
            model='llama-3.1-8b-instant',
            temperature=0.4
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f'[Error] AI Evaluator Failed: {e}')
        return None

if __name__ == '__main__':
    chat_history = []
    AUDIO_FILE = 'sample_answer.wav'
    current_question = 'What is the main difference between a List and a Tuple in Python?'
    print('THE INTERVIEW HAS STARTED')
    while True:
        speak_text(current_question)
        print(f'\nQuestion: {current_question}')
        print('-' * 50)
        user_input = input("Press ENTER to start recording, or type 'exit' to stop: ")
        if user_input.strip().lower() == 'exit':
            print('Interview ended. Goodbye!')
            break
        start_time = time.time()
        record_answer(AUDIO_FILE)
        end_time = time.time()
        answer_duration = round(end_time - start_time, 2)
        user_text = process_audio_ingestion(AUDIO_FILE)
        if not user_text:
            print('[ERROR] Could not process audio, Please Try Again...')
            continue
        print(f'You Said: {user_text}')
        words = user_text.lower().split()
        filler_words = ['um', 'uh', 'like', 'basically', 'you know', 'actually', 'so']
        filler_count = {w: words.count(w) for w in filler_words if words.count(w) > 0}
        total_fillers = sum(filler_count.values())
        print(f'Answer Duration: {answer_duration} seconds')
        print(f'Filler Words: {filler_count}')
        print(f'Total Fillers: {total_fillers}')
        print('-' * 50)
        chat_history.append({'role': 'user', 'content': f'Question: {current_question}\nAnswer: {user_text}'})
        ai_response = generate_next_round(chat_history)
        if not ai_response:
            print('[ERROR] AI FAILED TO RESPOND, ENDING INTERVIEW.')
            break
        print(ai_response)
        print('-' * 40)
        chat_history.append({'role': 'assistant', 'content': ai_response})
        if '### Next Interview Question' in ai_response:
            current_question = ai_response.split('### Next Interview Question')[1].strip()
        else:
            current_question = 'Can you tell me about your favourite Python libraries for data science?'