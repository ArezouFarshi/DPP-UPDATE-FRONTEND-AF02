import os, json

def process_and_anchor(panel_id, event_type, fault_type, fault_severity,
                       action_taken, event_hash, validated_by, timestamp):
    file_path = os.path.join("panels", f"{panel_id}.json")

    # Auto-create file if missing
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({
                "factory_registration": {},
                "installation_metadata": {},
                "digital_twin_status": {},
                "fault_log_installation": [],
                "fault_log_operation": []
            }, f, indent=2)

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    new_event = {
        "event_id": event_hash,
        "event_type": event_type,
        "fault_type": fault_type,
        "fault_severity": fault_severity,
        "action_taken": action_taken,
        "validated_by": validated_by,
        "timestamp": timestamp
    }

    # Choose correct section
    section = "fault_log_installation" if event_type.lower() == "installation" else "fault_log_operation"
    data[section].append(new_event)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"✅ JSON updated for {panel_id} ({event_type})")
