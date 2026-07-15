"""
Run the Aid Distribution Tracker locally:

    python run.py

Then open http://127.0.0.1:5000 in your browser.
"""

from aid_tracker.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
