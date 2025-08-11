import re
import json

def extract_json_block(text: str) -> dict | None:
    """
    Safely extracts and parses a fenced JSON block from a string.

    This function searches for a JSON object enclosed in triple backticks (```json ... ```).
    It is designed to be robust and will not crash if the JSON is missing or malformed.

    Args:
        text: The string potentially containing the JSON block, typically from an AI response.

    Returns:
        A dictionary if a valid JSON object is found and parsed successfully.
        None if no JSON block is found or if parsing fails.
    """
    if not isinstance(text, str):
        return None

    # Use a regular expression to find the content between ```json and ```
    # re.DOTALL allows the '.' to match newline characters, which is crucial for multi-line JSON.
    match = re.search(r"```json\s*([\s\S]*?)\s*```", text, re.DOTALL)

    if not match:
        # No JSON block was found in the text.
        return None
    
    # The actual JSON string is in the first capturing group of the regex.
    json_string = match.group(1)

    try:
        # Attempt to parse the extracted string into a Python dictionary.
        parsed_json = json.loads(json_string)
        return parsed_json
    except json.JSONDecodeError:
        # The string between the backticks was not valid JSON.
        print(f"!!! UTILS WARNING: Found a JSON block, but it was malformed. Content: {json_string[:200]}")
        return None