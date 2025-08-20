import os
import sys
import google.generativeai as genai
from supabase import create_client, Client
from waitress import serve

# --- 1. Add Project Directories to Python Path ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.append(src_dir)

# --- 2. Import Your Application Code ---
from app import app
from src.multi_agent_system.orchestrator import Orchestrator # Import the class directly
import config

# --- 3. Initialize All Services and Inject Them (The Correct Way) ---
print("--- [RUN.PY] SCRIPT EXECUTION STARTED ---")
try:
    print("[RUN.PY] Initializing Google Generative AI...")
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    print("[RUN.PY] Initializing Supabase client...")
    supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    
    # --- The New, Fast Initialization Sequence ---
    # 1. Create the Orchestrator instance. This is VERY FAST.
    print("[RUN.PY] Creating Orchestrator instance...")
    multi_agent_system = Orchestrator(supabase, model)

    # 2. Inject the instance into the Flask app IMMEDIATELY.
    print("[RUN.PY] Injecting services into Flask app context...")
    app.supabase = supabase
    app.model = model
    app.multi_agent_system = multi_agent_system
    print("--- [RUN.PY] INJECTION COMPLETE. Webhook is now ready. ---")

    # 3. Now, do the SLOW work of loading prompts. This happens after injection.
    prompts_dir = os.path.join(current_dir, 'prompts')
    multi_agent_system.load_all_agent_prompts(prompts_dir)
    print("--- [RUN.PY] APPLICATION IS FULLY WARMED UP. ---")

except Exception as e:
    print(f"FATAL: Failed to initialize application during startup.")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# --- 4. Entrypoint for Local Development ---
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"--- Starting LOCAL server with Waitress on port {port} ---")
    serve(app, host='0.0.0.0', port=port)