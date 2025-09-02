from flask import Flask, render_template, request, jsonify, send_from_directory
from inference_sdk import InferenceHTTPClient
import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Get API keys from environment variables
ROBOFLOW_API_KEY = os.getenv('ROBOFLOW_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
TOMTOM_API_KEY = os.getenv('TOMTOM_API_KEY')

# Validate API keys
if not ROBOFLOW_API_KEY:
    raise ValueError("ROBOFLOW_API_KEY environment variable is required")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is required")
if not TOMTOM_API_KEY:
    raise ValueError("TOMTOM_API_KEY environment variable is required")

# Initialize the Roboflow client
CLIENT = InferenceHTTPClient(
    api_url="https://detect.roboflow.com",
    api_key=ROBOFLOW_API_KEY
)

# Initialize the Groq client
client = Groq(api_key=GROQ_API_KEY)

def validate_question(question):
    """Validate if the question is appropriate for a medical AI assistant."""
    if not question or len(question.strip()) == 0:
        return False
    return True

def query_groq(question):
    """Query Groq Llama3-8b for a medical response."""
    try:
        # Validate if the question is appropriate
        if not validate_question(question):
            return "Please provide a valid medical question."
            
        # Add specific instructions in the system prompt
        messages = [
            {
                "role": "system",
                "content": "You are Doctor Vision, an AI medical assistant. Provide helpful, accurate medical information while emphasizing that users should consult healthcare professionals for serious concerns. Keep responses concise and professional."
            },
            {
                "role": "user",
                "content": question
            }
        ]

        # Create a chat completion with Groq API
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant",
            max_tokens=500,
            temperature=0.7
        )

        # Return the generated response
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        print(f"Groq API Error: {e}")
        return "I'm experiencing technical difficulties. Please try again later."

# Main routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/diagnostics')
def diagnostics():
    return render_template('project.html', tomtom_api_key=TOMTOM_API_KEY)

@app.route('/research')
def research():
    return render_template('bids.html')

@app.route('/Finances')
def finances():
    return render_template('Finances.html')

@app.route('/audit')
def audit():
    return render_template('Audit.html')

# Image upload and analysis endpoint
@app.route('/upload', methods=['POST'])
def analyze_image():
    try:
        if 'file' not in request.files:
            return render_template('bids.html', error="No file uploaded"), 400

        file = request.files['file']
        if file.filename == '':
            return render_template('bids.html', error="No file selected"), 400

        # Get the disease type from form data
        selected_disease = request.form.get('disease', '')
        if not selected_disease:
            return render_template('bids.html', error="No disease type selected"), 400

        # Save the uploaded file
        filename = file.filename
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)

        # Define model IDs for different diseases
        model_ids = {
            "brain_tumor": "brain_tumour_detection-p4qam/1",
            "tb": "tb-chemm/1",
            "pneumonia": "pneumonia-kefdw/1"
        }

        # Get the corresponding model ID
        model_id = model_ids.get(selected_disease)
        if not model_id:
            return render_template('bids.html', error="Invalid disease type selected"), 400

        # Perform inference on the uploaded file
        result = CLIENT.infer(upload_path, model_id=model_id)

        # Extract relevant data from the result
        predictions = result.get("predictions", [])
        
        # Clean up the uploaded file
        try:
            os.remove(upload_path)
        except:
            pass
            
        return render_template('bids.html', predictions=predictions, selected_disease=selected_disease)

    except Exception as e:
        print(f"Upload/Analysis Error: {e}")
        return render_template('bids.html', error=f"Analysis failed: {str(e)}"), 500

# Chatbot API Endpoint
@app.route('/ask', methods=['POST'])
def ask():
    try:
        # Get question from form data
        user_question = request.form.get('question', '').strip()
        
        if not user_question:
            return jsonify({"error": "No question provided"}), 400
            
        # Get response from Groq
        response = query_groq(user_question)
        
        return jsonify({"response": response}), 200
        
    except Exception as e:
        print(f"Chatbot Error: {e}")
        return jsonify({"error": "Sorry, there was an error processing your request. Please try again."}), 500

# Static file serving for uploads
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('index.html'), 500

# Run the Flask Application
if __name__ == "__main__":
    # Get configuration from environment variables
    # Render requires binding to 0.0.0.0 and uses PORT environment variable (default 10000)
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 10000))  # Render's default port
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"Starting Flask app on {host}:{port} (debug={debug})")
    app.run(debug=debug, host=host, port=port)
