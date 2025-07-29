
# Import json for reading json files
import json

# Import the genai library for interacting with Gemini API
import google.generativeai as genai

# Import flask to integrate the frontend (html)
from flask import Flask, render_template, request, jsonify

# Import necessary libraries for file handling
import os # For environment variables
import io # For handling file data in memory
import PyPDF2 # For PDF parsing
from docx import Document # For Word document parsing

# Set up the Flask app
app = Flask(__name__)

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv("API_KEY.env")

# Configure Gemini API client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("GEMINI_API_KEY environment variable not set!")

# File handling functions
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
    "Analyze my social media profile (attached as a JSON file) and identify any vulnerabilities. Predict any possible breaches to my account based on posting habits, privacy settings, and information shared. ONLY USE THE INFO PRESENT IN THE JSON FILE FOR ANALYSIS.\n"

   

    "I have been using social media and want to understand if I would be at risk for privacy breaches. Based on the advice you give, they want to be able to avoid these breaches. Share the top 3 vulnerabilities - choose ones that put the user at the most risk. Then you can include a couple more (2-3 more) ONLY IF NEEDED. If there aren’t any major risks DO NOT INCLUDE THEM! If there is not three major vulnerabilities, then just share top two or one. If there is no vulnerabilities at all then just say that. \n"

   

    "Act as a social media security expert. Write your response as if you are talking to the user directly."

   

    "Maintain a formal and informative tone and deliver information in a clear and concise way. Include bullet points for each vulnerability/possible breach and explain why it is an issue. After each one provides a possible solution to avoid that breach. Format the bullet points well - avoid the use of asterisk - make it pleasing to the eyes \n"

   

    "Scoring Method: Give the user a percentage of how likely I am to have their social media profile breached.\n"

   

    "Use this as a reference, but make it more concise, and avoid saying “I have” – make it to the point about what the vulnerabilities are and what needs to change. \n"

 

    "After analysis the risk percentage of your profile being breached is (insert the percentage here after looking at the profile)"

    "Here are your top three vulnerabilities:\n"

    "1.  Insert the top vulnerability here \n"

    "    Insert brief explanation of the vulnerability with specific examples\n"

   

    "    Solution: Insert way to improve – brief 1-2 sentences \n"

    "2.  Insert the top vulnerability here \n"

    "    Insert brief explanation of the vulnerability with specific examples\n"

   

    "    Solution: Insert way to improve – brief 1-2 sentences \n"

    "3.  Insert the top vulnerability here \n"

    "    Insert brief explanation of the vulnerability with specific examples\n"

   

    "    Solution: Insert way to improve – brief 1-2 sentences \n"

    "Create a bullet for access control insights - are their privacy settings good/bad - what needs to change? Follow a similar format to above but make it more concise and get rid of unneeded spaces/extra lines. Make it clear with as few possible words. DO NOT COPY THE EXAMPLE ABOVE ONLY USE IT TO HAVE A FORMAT"
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
