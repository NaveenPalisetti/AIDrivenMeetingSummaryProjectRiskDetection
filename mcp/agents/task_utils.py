import os, json

def extract_and_create_tasks(meeting_id, summary):
    # Accepts summary as a list of action item dicts or a single dict
    tasks = []
    action_items = []
    if isinstance(summary, list):
        action_items = summary
    elif isinstance(summary, dict):
        # If dict, try to extract from 'action_items' key or treat as single item
        if 'action_items' in summary and isinstance(summary['action_items'], list):
            action_items = summary['action_items']
        else:
            action_items = [summary]
    else:
        # Fallback: treat as string
        action_items = [{"title": str(summary)}]

    for item in action_items:
        title = item.get('title', str(item))
        owner = item.get('owner', None)
        due = item.get('due', None)
        tasks.append({
            "meeting_id": meeting_id,
            "title": title,
            "owner": owner,
            "due": due,
            "task": f"{title} (Owner: {owner or 'Unassigned'}, Due: {due or 'Unspecified'})"
        })
    return tasks
