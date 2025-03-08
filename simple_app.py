import os
import subprocess
import whisper
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, render_template
from datetime import datetime
from transformers import pipeline
import dateparser

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

app = Flask(__name__)

summarizer = pipeline("summarization", model="t5-small")

def summarize_text(text):
    summary = summarizer(text, max_length=100, min_length=80, do_sample=False)
    return summary[0]['summary_text']

def extract_dates(text):
    dates = []
    for word in text.split():
        parsed_date = dateparser.parse(word, settings={'PREFER_DATES_FROM': 'future'})
        if parsed_date:
            dates.append(parsed_date.strftime('%Y-%m-%d'))
    return list(set(dates))

def clean_extracted_details(details):
    """Remove empty or None fields before saving to Firestore."""
    return {k: v for k, v in details.items() if v is not None and v != ""}

def save_to_firestore(transcription, summary, filename, extracted_details, dates):
    now = datetime.now()

    doc_ref = db.collection("transcriptions").document()
    doc_ref.set({
        "filename": filename,
        "text": transcription,
        "summary": summary,
        "meeting_time": now.strftime("%I:%M %p"),
        "meeting_date": now.strftime("%Y-%m-%d"),
        "extracted_details": extracted_details,
        "important_dates": dates,
        "timestamp": firestore.SERVER_TIMESTAMP
    })
    print(f"✅ Transcription + Summary + Dates saved to Firestore with document ID: {doc_ref.id}")

@app.route('/')
def upload_form():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    
    if file:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        mp3_filename = os.path.splitext(file.filename)[0] + '.mp3'
        mp3_filepath = os.path.join(PROCESSED_FOLDER, mp3_filename)

        subprocess.run(['ffmpeg', '-i', filepath, mp3_filepath])

        model = whisper.load_model("base")
        result = model.transcribe(mp3_filepath)
        transcription_text = result['text']

        summary = summarize_text(transcription_text)

        important_dates = extract_dates(summary)

        extracted_details = {
            "plans_for_week": ["Review project plan", "Prepare for client presentation"],
            "deadline_date": "2025-03-15",
        }
        cleaned_details = clean_extracted_details(extracted_details)

        save_to_firestore(transcription_text, summary, file.filename, cleaned_details, important_dates)

        txt_filepath = os.path.join(PROCESSED_FOLDER, mp3_filename + '.txt')
        with open(txt_filepath, 'w', encoding='utf-8') as f:
            f.write(transcription_text)

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Meeting Summary</title>
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                background-color: #f7f7f7;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }}
            .notebook {{
                background-color: #fffacd;
                width: 80%;
                max-width: 800px;
                padding: 30px;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
                border-left: 6px solid #ff6666;
                position: relative;
                line-height: 1.5;
                white-space: pre-wrap;
                word-wrap: break-word;
            }}
            h1 {{
                font-size: 24px;
                margin-bottom: 20px;
                color: #444;
            }}
            p {{
                font-size: 16px;
                color: #333;
            }}
            .summary {{
                background-color: #fff;
                padding: 15px;
                border: 1px solid #ddd;
                overflow: auto;
                max-height: 400px;
                white-space: pre-wrap;
            }}
            .sticky-note {{
                position: absolute;
                width: 60px;
                height: 60px;
                transform: rotate(-8deg);
                z-index: 1;
            }}
            .sticky-1 {{ top: -10px; left: -10px; background-color: #ffb6c1; }}
            .sticky-2 {{ top: 10px; right: -15px; background-color: #ffcc80; }}
            .sticky-3 {{ bottom: 10px; left: -15px; background-color: #a5d6a7; }}
            .sticky-4 {{ bottom: -10px; right: -10px; background-color: #90caf9; }}
        </style>
    </head>
    <body>
        <div class="notebook">
            <div class="sticky-note sticky-1"></div>
            <div class="sticky-note sticky-2"></div>
            <div class="sticky-note sticky-3"></div>
            <div class="sticky-note sticky-4"></div>

            <h1>Meeting Summary</h1>
            <p><strong>Here's a quick summary of your meeting:</strong></p>
            <div class="summary">{summary}</div>
        </div>
    </body>
    </html>
    """
if __name__ == '__main__':
    app.run(debug=True)
