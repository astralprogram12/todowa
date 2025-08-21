import os
from waitress import serve

# --- [THE FIX] ---
# We import the 'app' object from our now self-contained app.py file.
# When this import runs, all the initialization code inside app.py will execute.
try:
    from app import app
    print("[RUN.PY] Successfully imported the configured Flask app from app.py")
except Exception as e:
    print(f"FATAL: Could not import the Flask app from app.py. Check app.py for errors.")
    import traceback
    traceback.print_exc()
    # Exit if the core app can't even be imported
    import sys
    sys.exit(1)
# --- [END OF FIX] ---


# This block only runs when you execute `python run.py` on your local machine.
# Vercel ignores this and just uses the 'app' object we imported above.
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"--- Starting LOCAL server with Waitress on port {port} ---")
    serve(app, host='0.0.0.0', port=port)