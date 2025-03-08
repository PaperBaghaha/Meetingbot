import re
from datetime import datetime
import pytz

def extract_meeting_details(transcription_text):
    details = {
        "meeting_time": None,
        "meeting_date": None,
        "deadline": None,
        "project_info": [],
    }

    # Extract date & time (you can improve this regex if needed)
    date_time_pattern = re.compile(r'\b(?:on\s+)?(\w+\s+\d{1,2}(?:st|nd|rd|th)?)\s*(?:at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?))?', re.IGNORECASE)

    for match in date_time_pattern.finditer(transcription_text):
        date_part, time_part = match.groups()

        if date_part and time_part:
            # Full meeting date & time
            details['meeting_date'] = date_part
            details['meeting_time'] = time_part
        elif date_part:
            # Just a date (could be deadline)
            details['deadline'] = date_part

    # Project info - flexible phrasing
    project_info_pattern = re.compile(r'\b(?:this week|we will|our focus|plan to|work on)\b.*', re.IGNORECASE)
    for match in project_info_pattern.finditer(transcription_text):
        details['project_info'].append(match.group().strip())

    return details

def format_for_firestore(details, transcription_text, filename):
    # Convert to Firestore-friendly format
    firestore_data = {
        "filename": filename,
        "text": transcription_text,
        "timestamp": datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%B %d, %Y at %I:%M:%S %p UTC%z'),
        "extracted_details": {
            "meeting_date": details["meeting_date"],
            "meeting_time": details["meeting_time"],
            "deadline": details["deadline"],
            "project_info": details["project_info"]
        }
    }
    return firestore_data

# Example usage
transcription_text = """
Hello everyone, thank you for coming on such short notice.
I just wanted to give a few details. The project deadline is on March 7th.
The next meeting is on March 10th at 3pm and this week we will focus on finalizing the UI.
Thank you everyone.
"""
filename = "WhatsApp Video 2025-03-07 at 6.43.14 PM.mp4"

details = extract_meeting_details(transcription_text)
firestore_data = format_for_firestore(details, transcription_text, filename)

import pprint
pprint.pprint(firestore_data)
