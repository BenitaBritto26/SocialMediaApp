import json
import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
# imports the genai library for interacting with Gemini API
from google import genai

import io # For handling file data in memory
import PyPDF2 # For PDF parsing
from docx import Document # For Word document parsing

# --- Flask App Setup ---
app = Flask(__name__)

# Load environment variables from .env file
load_dotenv("API_KEY.env")

# --- Configure Google Generative AI ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY environment variable not set. AI features may not work.")

# --- Helper Functions for File Processing ---
def extract_text_from_pdf(file_stream):
    """Extracts text from a PDF file stream."""
    text = ""
    try:
        reader = PyPDF2.PdfReader(file_stream)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        raise ValueError("Could not process PDF file.")
    return text

def extract_text_from_docx(file_stream):
    """Extracts text from a DOCX file stream."""
    text = ""
    try:
        document = Document(file_stream)
        for paragraph in document.paragraphs:
            text += paragraph.text + "\n"
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        raise ValueError("Could not process Word document.")
    return text

# --- Gemini Prompt Construction ---
gemini_base_prompt = """
Between each section, put a dashed line to keep the sections separate.
Give the user a percent of how unsafe their account is (higher percentage means they are revealing more sensitive data that can be used to exploit the user).
---
Give a bullet point list of vulnerabilities of this social media profile.
---
Give a 3-5 sentence summary of possible solutions that could be implemented to resolve said vulnerabilities.
---
Give suggestions of which users this profile should be accessible to (Eg: family, close friends, mutual friends, public).
---
Give a 3-5 prediction summary of possible breaches to the account or threats that could result from not making any changes to the current account.

Based on the following social media information, provide the assessment:
"""

# --- Flask Routes ---

@app.route('/')
def index():
    return render_template('Frontend2.html')

@app.route('/assess', methods=['POST'])
def assess():
    input_type = request.form.get('input_type')
    data_to_assess = ""

    if input_type == 'text':
        data_to_assess = request.form.get('text_data')
        print(f"DEBUG: Processing text input. Length: {len(data_to_assess or '')}")

    elif input_type == 'json':
        # JSON data comes from request.form as a string, not request.files
        json_data_str = request.form.get('json_data')
        if not json_data_str:
            print("ERROR: No 'json_data' found in form for JSON input type.")
            return jsonify({"error": "No JSON data provided."}), 400
        try:
            json_content = json.loads(json_data_str)
            data_to_assess = json.dumps(json_content, indent=2) # Re-format for AI
            print(f"DEBUG: Processed JSON data. Length: {len(data_to_assess)}")
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON data received from frontend: {e}")
            return jsonify({"error": "Invalid JSON data received."}), 400

    elif input_type in ['pdf', 'word']:
        # PDF and Word files come from request.files
        file = request.files.get('file')
        if not file:
            print(f"ERROR: No file uploaded for {input_type} input type.")
            return jsonify({"error": "No file uploaded for PDF/Word."}), 400
        
        print(f"DEBUG: Received {input_type} file: {file.filename}")
        file_stream = io.BytesIO(file.read())

        if input_type == 'pdf':
            try:
                data_to_assess = extract_text_from_pdf(file_stream)
            except ValueError as e:
                print(f"ERROR: PDF processing failed: {e}")
                return jsonify({"error": str(e)}), 400
        elif input_type == 'word':
            try:
                data_to_assess = extract_text_from_docx(file_stream)
            except ValueError as e:
                print(f"ERROR: Word processing failed: {e}")
                return jsonify({"error": str(e)}), 400
    else:
        print(f"ERROR: Invalid input type '{input_type}' provided.")
        return jsonify({"error": "Invalid input type provided."}), 400

    if not data_to_assess or data_to_assess.strip() == "":
        print("ERROR: No assessable content after file/text processing.")
        return jsonify({"error": "No content provided for assessment."}), 400

    # --- Call Gemini API ---
    if not GEMINI_API_KEY:
        print("ERROR: API Key not configured on the server (GEMINI_API_KEY is missing).")
        return jsonify({"error": "API Key not configured on the server."}), 500

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        full_gemini_input = f"{gemini_base_prompt}\n\n```\n{data_to_assess}\n```"
        print(f"DEBUG: Calling Gemini API with input length: {len(full_gemini_input)}")
        
        gemini_response = model.generate_content(full_gemini_input)
        print("DEBUG: Gemini API call completed.")
        
        if not gemini_response.text:
            print("WARNING: Gemini API returned an empty text response.")
            return jsonify({
                "score": 50, # Default or handle as an error
                "full_report": "AI returned an empty response. Please try again."
            })

        import re
        score_match = re.search(r'(\d+)%', gemini_response.text)
        # Safely extract score, default to 50 if not found
        score = int(score_match.group(1)) if score_match else 50 
        print(f"DEBUG: Extracted score: {score}")

        return jsonify({
            "score": score,
            "full_report": gemini_response.text
        })

    except Exception as e:
        print(f"ERROR: An exception occurred during Gemini API call: {e}")
        import traceback
        traceback.print_exc() # Print full traceback to Render logs
        return jsonify({"error": "Failed to get assessment from AI model.", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
