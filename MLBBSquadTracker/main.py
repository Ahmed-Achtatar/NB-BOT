# Main entry point for the application
# Handles both the Discord bot and the Flask web server

import os
import threading
import logging
from flask import Flask, render_template
from bot import run_bot

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Start the Discord bot in a separate thread
bot_thread = threading.Thread(target=run_bot)
bot_thread.daemon = True
bot_thread.start()
logger.info("Started Discord bot thread")

@app.route('/')
def index():
    """Homepage route for the web application."""
    return render_template('index.html')

def run_flask():
    """Run the Flask web server."""
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    # Start the Flask web server
    logger.info("Starting Flask web server...")
    run_flask()
