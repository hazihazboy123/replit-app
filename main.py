from app import app, JSON_REPAIR_AVAILABLE
import logging

if __name__ == '__main__':
    # Log whether json_repair is available
    if JSON_REPAIR_AVAILABLE:
        logging.info("✅ json_repair package is installed and ready!")
    else:
        logging.warning("⚠️  json_repair package not found - using fallback parser")
        logging.warning("⚠️  To install: pip install json_repair")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
