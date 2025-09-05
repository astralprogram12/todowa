import asyncio
import sys
import os

# --- Add project root to sys.path ---
# This is to ensure that the script can find the other modules like 'wa_version'
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from wa_version import TodowaApp
    import config
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure that wa_version.py and config.py are in the same directory.")
    sys.exit(1)

async def main():
    """
    Main function to run the Todowa CLI application.
    """
    print("Starting Todowa CLI...")

    # 1. Initialize the application
    chat_app = TodowaApp()
    if not chat_app.initialize_system():
        print("Failed to initialize the Todowa system. Exiting.")
        return

    # 2. Get user_id. For this CLI, we'll use the test user ID from config.
    user_id = config.CHAT_TEST_USER_ID
    if not user_id:
        print("CHAT_TEST_USER_ID not found in config.py. Exiting.")
        return

    print(f"Using test user ID: {user_id}")

    # 3. Create a user-specific Supabase client
    user_supabase_client = chat_app.create_user_supabase_client(user_id)
    if not user_supabase_client:
        print(f"Failed to create a Supabase client for user {user_id}. Exiting.")
        return

    print("Initialization complete. You can now start messaging.")
    print("Type 'exit' or 'quit' to end the session.")
    print("-" * 20)

    # 4. Main loop for user interaction
    while True:
        try:
            message = input("You: ")
            if message.lower() in ["exit", "quit"]:
                print("Exiting CLI. Goodbye!")
                break

            if not message.strip():
                continue

            # 5. Process the message using the app's core logic
            response = await chat_app.process_message_async(message, user_id, user_supabase_client)

            # 6. Print the response
            print(f"Bot: {response}")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting CLI. Goodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Setup asyncio event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCLI interrupted by user.")
