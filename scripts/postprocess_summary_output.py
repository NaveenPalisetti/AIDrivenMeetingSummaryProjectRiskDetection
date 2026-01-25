import json
import ast

# Input and output file paths
input_file = "summary_output.json"
output_file = "summary_output_structured.json"

def try_eval(s):
    try:
        return ast.literal_eval(s)
    except Exception:
        return s

def extract_structured_data(data):
    structured = {
        "summary_points": [],
        "action_items": [],
        "debug_chunks": []
    }
    # Process summary_points
    for item in data.get("summary_points", []):
        parsed = try_eval(item)
        if isinstance(parsed, dict):
            # If dict, extract summary_points and action_items if present
            if "summary_points" in parsed:
                structured["summary_points"].extend(parsed["summary_points"])
            if "action_items" in parsed:
                structured["action_items"].extend(parsed["action_items"])
        elif isinstance(parsed, list):
            structured["summary_points"].extend(parsed)
        else:
            structured["summary_points"].append(parsed)
    # Process debug_chunks (optional, just parse for readability)
    for chunk in data.get("debug_chunks", []):
        structured["debug_chunks"].append(try_eval(chunk))
    # If action_items at top level
    for item in data.get("action_items", []):
        structured["action_items"].append(item)
    return structured

def main():
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    structured = extract_structured_data(data)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)
    print(f"Structured output saved to: {output_file}")

if __name__ == "__main__":
    main()
