from flask import Flask, render_template, request, jsonify, send_from_directory
from inference_sdk import InferenceHTTPClient
from werkzeug.utils import secure_filename
from groq import Groq
from dotenv import load_dotenv

import os
import logging


# ============================================================
# Configuration
# ============================================================

load_dotenv()

app = Flask(__name__)

# Required application secret
app.secret_key = os.environ["SECRET_KEY"]

# Upload configuration
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================================
# Environment Variables
# ============================================================

ROBOFLOW_API_KEY = os.environ["ROBOFLOW_API_KEY"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
TOMTOM_API_KEY = os.environ["TOMTOM_API_KEY"]

# Keep the model configurable from the environment.
# Current replacement for deprecated llama-3.1-8b-instant.
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)


# ============================================================
# Logging
# ============================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# API Clients
# ============================================================

# Roboflow
CLIENT = InferenceHTTPClient(
    api_url="https://detect.roboflow.com",
    api_key=ROBOFLOW_API_KEY
)

# Groq
groq_client = Groq(
    api_key=GROQ_API_KEY
)


# ============================================================
# Chatbot
# ============================================================

def validate_question(question):
    """
    Basic validation for chatbot input.
    """
    return bool(question and question.strip())


def query_groq(question):
    """
    Send the user's question to the Groq LLM.

    Returns:
        tuple:
            (response, None) on success
            (None, error_message) on failure
    """

    if not validate_question(question):
        return None, "Please provide a valid medical question."

    messages = [
        {
            "role": "system",
            "content": (
                "You are Doctor Vision, an AI medical information assistant. "
                "Provide helpful and accurate general medical information. "
                "Do not claim to be a licensed physician or provide definitive "
                "diagnoses. For serious, emergency, or worsening symptoms, "
                "advise the user to seek appropriate professional medical care. "
                "Keep responses concise and professional."
            )
        },
        {
            "role": "user",
            "content": question
        }
    ]

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages,
            model=GROQ_MODEL,
            max_tokens=500,
            temperature=0.7
        )

        response = chat_completion.choices[0].message.content

        if not response:
            return None, "The chatbot returned an empty response."

        return response, None

    except Exception:
        logger.exception("Groq API request failed")
        return None, "The chatbot service is temporarily unavailable."


# ============================================================
# Main Routes
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/diagnostics")
def diagnostics():
    return render_template(
        "project.html",
        tomtom_api_key=TOMTOM_API_KEY
    )


@app.route("/research")
def research():
    return render_template("bids.html")


@app.route("/Finances")
def finances():
    return render_template("Finances.html")


@app.route("/audit")
def audit():
    return render_template("Audit.html")

@app.route("/training")
def training():
    return render_template("training.html")


# ============================================================
# Image Upload / Disease Analysis
# ============================================================

@app.route("/upload", methods=["POST"])
def analyze_image():

    upload_path = None

    try:
        # Check file
        if "file" not in request.files:
            return render_template(
                "bids.html",
                error="No file uploaded"
            ), 400

        file = request.files["file"]

        if file.filename == "":
            return render_template(
                "bids.html",
                error="No file selected"
            ), 400

        # Get disease type
        selected_disease = request.form.get("disease", "").strip()

        if not selected_disease:
            return render_template(
                "bids.html",
                error="No disease type selected"
            ), 400

        # Secure filename
        filename = secure_filename(file.filename)

        if not filename:
            return render_template(
                "bids.html",
                error="Invalid filename"
            ), 400

        # Save uploaded file
        upload_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        file.save(upload_path)

        # Supported disease models
        model_ids = {
            "brain_tumor": "brain_tumour_detection-p4qam/1",
            "tb": "tb-chemm/1",
            "pneumonia": "pneumonia-kefdw/1"
        }

        model_id = model_ids.get(selected_disease)

        if not model_id:
            return render_template(
                "bids.html",
                error="Invalid disease type selected"
            ), 400

        # Run Roboflow inference
        result = CLIENT.infer(
            upload_path,
            model_id=model_id
        )

        predictions = result.get(
            "predictions",
            []
        )

        return render_template(
            "bids.html",
            predictions=predictions,
            selected_disease=selected_disease
        )

    except Exception:
        logger.exception("Upload/Analysis Error")

        return render_template(
            "bids.html",
            error="Analysis failed. Please try again."
        ), 500

    finally:
        # Always remove uploaded file
        if upload_path and os.path.exists(upload_path):
            try:
                os.remove(upload_path)
            except OSError:
                logger.warning(
                    "Could not remove uploaded file: %s",
                    upload_path
                )


# ============================================================
# Chatbot API
# ============================================================

@app.route("/ask", methods=["POST"])
def ask():

    try:
        user_question = request.form.get(
            "question",
            ""
        ).strip()

        if not user_question:
            return jsonify({
                "error": "No question provided"
            }), 400

        response, error = query_groq(
            user_question
        )

        if error:
            return jsonify({
                "error": error
            }), 503

        return jsonify({
            "response": response
        }), 200

    except Exception:
        logger.exception("Chatbot Error")

        return jsonify({
            "error": (
                "Sorry, there was an error "
                "processing your request."
            )
        }), 500


# ============================================================
# Uploaded Files
# ============================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# ============================================================
# Error Handlers
# ============================================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template(
        "index.html"
    ), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template(
        "index.html"
    ), 500


@app.errorhandler(413)
def request_entity_too_large(e):
    return render_template(
        "bids.html",
        error="File is too large. Maximum size is 10 MB."
    ), 413


# ============================================================
# Run Application
# ============================================================

if __name__ == "__main__":

    host = os.getenv(
        "HOST",
        "0.0.0.0"
    )

    port = int(
        os.getenv(
            "PORT",
            10000
        )
    )

    debug = (
        os.getenv(
            "FLASK_DEBUG",
            "False"
        ).lower() == "true"
    )

    logger.info(
        "Starting Flask app on %s:%s (debug=%s)",
        host,
        port,
        debug
    )

    app.run(
        debug=debug,
        host=host,
        port=port
    )