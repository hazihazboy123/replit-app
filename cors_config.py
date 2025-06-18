"""
CORS configuration for n8n integration
"""
from flask_cors import CORS

def configure_cors(app):
    """Configure CORS for API endpoints to allow n8n integration"""
    CORS(app, resources={
        r"/api/*": {
            "origins": ["*"],  # Allow all origins for n8n integration
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
        },
        r"/process": {
            "origins": ["*"],  # Allow all origins for web form and n8n
            "methods": ["POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
        }
    })