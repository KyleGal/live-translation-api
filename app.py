import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from routes.translate import translate_bp

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(translate_bp, url_prefix='/api/translate')

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    from datetime import datetime
    return {
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat()
    }

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=True)
