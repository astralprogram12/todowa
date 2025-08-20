import os
import sys
import google.generativeai as genai
from supabase import create_client, Client
from waitress import serve

# --- 1. Add Project Directories to Python Path ---
# This ensures that imports from 'app' and 'src' work correctly.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.append(src_dir)

# --- 2. Import Your Application Code ---
# We import the Flask app object from your app.py file
from app import app
# We import your multi-agent system orchestrator
from src.multi_agent_system.orchestrator import create_multi_agent_system
# We import your configuration
import config

# --- 3. Initialize All Services and Inject Them ---
# This code runs as soon as the file is imported, which is what Vercel needs.

print("--- INITIALIZING APPLICATION ---")

try:
    # Configure Gemini AI Model
    print("Initializing Google Generative AI...")
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    print("...Google Generative AI initialized.")

    # Create Supabase Client
    print("Initializing Supabase client...")
    supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    print("...Supabase client initialized.")
    
    # Define prompts directory
    prompts_dir = os.path.join(current_dir, 'prompts')

    # Create the Multi-Agent System
    print("Initializing Multi-Agent System...")
    multi_agent_system = create_multi_agent_system(supabase, model, prompts_dir=prompts_dir)
    print("...Multi-Agent System initialized.")

    # CRITICAL STEP: Inject the initialized objects into the Flask app
    print("Injecting services into Flask app context...")
    app.supabase = supabase
    app.model = model
    app.multi_agent_system = multi_agent_system
    print("...Injection complete. Application is ready.")

except Exception as e:
    print(f"FATAL: Failed to initialize application during startup.")
    print(f"Error: {e}")
    # Exit if services can't be loaded
    sys.exit(1)

# --- 4. Entrypoint for Local Development ---
# This block will ONLY run when you execute `python run.py` in your terminal.
# A production server like Vercel will IGNORE this and just use the 'app' object.
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"--- Starting LOCAL production server with Waitress on port {port} ---")
    serve(app, host='0.0.0.0', port=port)