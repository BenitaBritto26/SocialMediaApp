# Appv3.py (Refactored Flask Backend)

import json
import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
import io # For handling file data in memory
import PyPDF2 # For PDF parsing
from docx import Document # For Word document parsing

# --- Flask App Setup ---
app = Flask(__name__)

# Load environment variables from .env file
# Ensure API_KEY.env is in the same directory as this script, or specify the full path
load_dotenv("API_KEY.env")

# --- Configure Google Generative AI ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY environment variable not set. AI features may not work.")
    # In a production environment, you might want to raise an error or exit if the key is critical.

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
# Combine your prompts into a single string for better AI response generation
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

# Route to serve the main HTML page
@app.route('/')
def index():
    # Flask looks for templates in the 'templates' folder by default
    # Make sure Frontend2.html is moved to a 'templates' directory
    return render_template('Frontend2.html')

# API endpoint for vulnerability assessment
@app.route('/assess', methods=['POST'])
def assess():
    input_type = request.form.get('input_type') # Get input_type from frontend's FormData
    data_to_assess = ""

    if input_type == 'text':
        data_to_assess = request.form.get('text_data')
    elif input_type in ['pdf', 'word', 'json']:
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "No file uploaded."}), 400

        # Read file into an in-memory stream for processing
        file_stream = io.BytesIO(file.read())

        if input_type == 'pdf':
            try:
                data_to_assess = extract_text_from_pdf(file_stream)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
        elif input_type == 'word':
            try:
                data_to_assess = extract_text_from_docx(file_stream)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
        elif input_type == 'json':
            try:
                json_data_str = request.form.get('json_data') # Frontend sends JSON as string
                json_content = json.loads(json_data_str)
                # You might want to format this JSON content for the AI model
                data_to_assess = json.dumps(json_content, indent=2)
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON data received."}), 400
    else:
        return jsonify({"error": "Invalid input type provided."}), 400

    if not data_to_assess or data_to_assess.strip() == "":
        return jsonify({"error": "No content provided for assessment."}), 400

    # --- Call Gemini API ---
    if not GEMINI_API_KEY:
        return jsonify({"error": "API Key not configured on the server."}), 500

    try:
        model = genai.GenerativeModel('gemini-pro') # Using gemini-pro for text tasks
        # Concatenate the base prompt with the user's data
        full_gemini_input = f"{gemini_base_prompt}\n\n```\n{data_to_assess}\n```"
        
        gemini_response = model.generate_content(full_gemini_input)
        
        # Extract vulnerability score (assuming Gemini returns it as a percentage in its text)
        # This is a simple regex example. You might need to refine it based on actual Gemini output.
        import re
        score_match = re.search(r'(\d+)%', gemini_response.text)
        score = int(score_match.group(1)) if score_match else 50 # Default to 50 if no score found

        return jsonify({
            "score": score,
            "full_report": gemini_response.text # Send the full AI report back if needed
        })

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return jsonify({"error": "Failed to get assessment from AI model.", "details": str(e)}), 500

# --- Run the Flask App ---
if __name__ == '__main__':
    # For local development
    # Ensure you install PyPDF2 and python-docx:
    # pip install PyPDF2 python-docx
    app.run(debug=True, port=5000)
