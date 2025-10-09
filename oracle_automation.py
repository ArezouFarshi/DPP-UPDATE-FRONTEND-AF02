import json
import os

# Directory for JSON
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PANELS_DIR = os.path.join(BASE_DIR, "panels")

def process_and_anchor(panel_id, event_type, fault_type, fault_severity, action_taken, event_hash, validated_by, timestamp):
    """Update JSON file when a blockchain event is detected."""
    path = os.path.join(PANELS_DIR, f"{panel_id}.json")
    if not os.path.exists(path):
        print(f"⚠️ Panel record not found: {panel_id}")
        return

    with open(path, "r", encoding="utf-8") as f:
        panel_json = json.load(f)

    # Build event record
    event_data = {
        "event_id": event_hash,
        "event_type": event_type,
        "fault_type": fault_type,
        "fault_severity": fault_severity,
        "action_taken": action_taken,
        "validated_by": validated_by,
        "timestamp": timestamp
    }

    # Decide which log to append to
    if event_type.lower() == "installation":
        section = "fault_log_installation"
    else:
        section = "fault_log_operation"

    # Ensure section exists as a list
    if section not in panel_json or not isinstance(panel_json[section], list):
        panel_json[section] = []

    # Debug: show exactly where it’s writing
    print("Writing to:", path)

    # Append new event
    panel_json[section].append(event_data)

    # Save back to file
    with open(path, "w", encoding="utf-8") as f:
        json.dump(panel_json, f, indent=2)

    print(f"✅ JSON updated for {panel_id} ({event_type})")
