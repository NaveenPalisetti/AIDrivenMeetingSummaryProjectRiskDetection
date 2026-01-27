
import os
import json
from datetime import datetime, timedelta
import random




# Place this at the end of the file

projects = [
    {
        "name": "UX Enhancements",
        "description": "Improving the user experience for the dashboard module.",
        "participants": [
            {"name": "Priya Sharma", "role": "Project Manager"},
            {"name": "Arjun Mehta", "role": "UX Developer"},
            {"name": "Ravi Kumar", "role": "Backend Developer"},
            {"name": "Sneha Patel", "role": "QA1"},
            {"name": "Amit Singh", "role": "QA2"}
        ],
        "agendas": [
            "Sprint Planning", "Dashboard Layout", "API Endpoints", "Test Cases", "Bug Ticket"
        ],
        "risk_factors": [
            "Tight deadline for dashboard API", "Unclear API requirements"
        ]
    },
    {
        "name": "Mobile App Launch",
        "description": "Launching the new mobile application for Android and iOS.",
        "participants": [
            {"name": "Sonia Verma", "role": "Project Manager"},
            {"name": "Rahul Joshi", "role": "Mobile Developer"},
            {"name": "Deepak Rao", "role": "Backend Developer"},
            {"name": "Meera Nair", "role": "QA"},
            {"name": "Vikas Gupta", "role": "DevOps"}
        ],
        "agendas": [
            "Sprint Planning", "App UI Review", "API Integration", "Release Checklist", "Bug Review"
        ],
        "risk_factors": [
            "App store approval delays", "API instability"
        ]
    }
]


topics = [
    "Sprint Planning", "Dashboard Layout", "API Endpoints", "Test Cases",
    "Bug Ticket", "Risk Assessment", "Story Points", "Regression Testing",
    "App UI Review", "API Integration", "Release Checklist", "Bug Review"
]


# Example discussions for each project (can be expanded)
project_discussions = {
    "UX Enhancements": [
        ("Priya Sharma", "Let's begin our Sprint {sprint} kickoff for the {project_name} project."),
        ("Arjun Mehta", "I’ll start designing the new dashboard layout today."),
        ("Priya Sharma", "Please ensure the design aligns with the latest branding guidelines."),
        ("Ravi Kumar", "I’ll set up the API endpoints for the dashboard. Should be done by Friday."),
        ("Sneha Patel", "I’ll prepare the test cases for the new dashboard features."),
        ("Amit Singh", "I’ll focus on regression testing for the existing modules."),
        ("Priya Sharma", "Please update Jira with your tasks. Backend, your story is {backend_points} points, UX is {ux_points} points."),
        ("Arjun Mehta", "I found a bug in the login flow. I’ll create a bug ticket for it."),
        ("Priya Sharma", "Thanks, Arjun. Please assign it to yourself and set the due date for this week."),
        ("Ravi Kumar", "I might need some clarification on the API requirements. Can we schedule a quick call tomorrow?"),
        ("Priya Sharma", "Sure, let’s block 15 minutes after the daily standup."),
        ("Sneha Patel", "Are there any known risks for this sprint?"),
        ("Priya Sharma", "The main risk is the tight deadline for the dashboard API. Ravi, let us know if you need any support."),
        ("Amit Singh", "Do we have the updated test data for the new features?"),
        ("Priya Sharma", "I’ll share the updated test data by end of day."),
        ("Arjun Mehta", "I’ll also update the sprint planning board after this call."),
        ("Priya Sharma", "Any other issues or blockers?"),
        ("Ravi Kumar", "None from my side."),
        ("Sneha Patel", "All good here."),
        ("Amit Singh", "No blockers."),
        ("Priya Sharma", "Great, let’s have a productive sprint!")
    ],
    "Mobile App Launch": [
        ("Sonia Verma", "Welcome to the Sprint {sprint} planning for the {project_name} project."),
        ("Rahul Joshi", "I’ll begin the app UI review and start integrating the new APIs."),
        ("Deepak Rao", "I’ll ensure the backend is ready for mobile integration."),
        ("Meera Nair", "I’ll prepare the test cases for the mobile app features."),
        ("Vikas Gupta", "I’ll set up the CI/CD pipeline for the release."),
        ("Sonia Verma", "Please update Jira with your tasks. Backend, your story is {backend_points} points, Mobile is {mobile_points} points."),
        ("Rahul Joshi", "I found a bug in the push notification module. I’ll create a bug ticket for it."),
        ("Sonia Verma", "Thanks, Rahul. Please assign it to yourself and set the due date for this week."),
        ("Deepak Rao", "Can we clarify the API response format?"),
        ("Sonia Verma", "Let’s schedule a call after the standup."),
        ("Meera Nair", "Are there any known risks for this sprint?"),
        ("Sonia Verma", "App store approval delays and API instability are the main risks."),
        ("Vikas Gupta", "Do we have the release checklist ready?"),
        ("Sonia Verma", "I’ll share the checklist by end of day."),
        ("Rahul Joshi", "I’ll update the sprint planning board after this call."),
        ("Sonia Verma", "Any other issues or blockers?"),
        ("Deepak Rao", "None from my side."),
        ("Meera Nair", "All good here."),
        ("Vikas Gupta", "No blockers."),
        ("Sonia Verma", "Great, let’s have a productive sprint!")
    ]
}


project_summaries = {
    "UX Enhancements": [
        "Sprint {sprint} for {project_name} kicked off with clear assignments and deadlines.",
        "Arjun to design the new dashboard layout and create a bug ticket for login flow.",
        "Ravi to set up API endpoints for the dashboard and requested a follow-up call for clarifications.",
        "QA team to prepare test cases and perform regression testing; updated test data to be shared.",
        "Main risk identified: {risk_factors}. Team to update Jira and sprint planning board."
    ],
    "Mobile App Launch": [
        "Sprint {sprint} for {project_name} started with focus on UI review and API integration.",
        "Rahul to review app UI and create a bug ticket for push notification module.",
        "Deepak to ensure backend readiness for mobile integration.",
        "QA to prepare test cases and DevOps to set up CI/CD; release checklist to be shared.",
        "Main risks: {risk_factors}. Team to update Jira and sprint planning board."
    ]
}


project_action_items = {
    "UX Enhancements": [
        {"summary": "Design new dashboard layout", "description": "As a UX Developer, design the new dashboard layout as per branding guidelines.", "assignee": "Arjun Mehta", "issue_type": "Story", "due_days": 4},
        {"summary": "Set up API endpoints for dashboard", "description": "As a Backend Developer, set up API endpoints for the dashboard.", "assignee": "Ravi Kumar", "issue_type": "Story", "due_days": 4},
        {"summary": "Prepare test cases for new features", "description": "As QA, prepare test cases for the new dashboard features.", "assignee": "Sneha Patel", "issue_type": "Task", "due_days": 3},
        {"summary": "Regression testing for existing modules", "description": "As QA, perform regression testing for existing modules.", "assignee": "Amit Singh", "issue_type": "Task", "due_days": 3},
        {"summary": "Create bug ticket for login issue", "description": "As a UX Developer, create a bug ticket for the login flow issue.", "assignee": "Arjun Mehta", "issue_type": "Bug", "due_days": 1},
        {"summary": "Share updated test data", "description": "As Project Manager, share updated test data for new features.", "assignee": "Priya Sharma", "issue_type": "Task", "due_days": 0},
        {"summary": "Update sprint planning board", "description": "As a UX Developer, update the sprint planning board after the meeting.", "assignee": "Arjun Mehta", "issue_type": "Task", "due_days": 0},
        {"summary": "Schedule API clarification call", "description": "As Project Manager, schedule a call for API clarification.", "assignee": "Priya Sharma", "issue_type": "Task", "due_days": 1}
    ],
    "Mobile App Launch": [
        {"summary": "Review app UI and integrate APIs", "description": "As a Mobile Developer, review the app UI and start integrating new APIs.", "assignee": "Rahul Joshi", "issue_type": "Story", "due_days": 4},
        {"summary": "Backend readiness for mobile integration", "description": "As a Backend Developer, ensure backend is ready for mobile integration.", "assignee": "Deepak Rao", "issue_type": "Story", "due_days": 4},
        {"summary": "Prepare test cases for mobile app", "description": "As QA, prepare test cases for mobile app features.", "assignee": "Meera Nair", "issue_type": "Task", "due_days": 3},
        {"summary": "Set up CI/CD pipeline", "description": "As DevOps, set up CI/CD pipeline for the mobile app release.", "assignee": "Vikas Gupta", "issue_type": "Task", "due_days": 3},
        {"summary": "Create bug ticket for push notification", "description": "As a Mobile Developer, create a bug ticket for the push notification module.", "assignee": "Rahul Joshi", "issue_type": "Bug", "due_days": 1},
        {"summary": "Share release checklist", "description": "As Project Manager, share the release checklist with the team.", "assignee": "Sonia Verma", "issue_type": "Task", "due_days": 0},
        {"summary": "Update sprint planning board", "description": "As a Mobile Developer, update the sprint planning board after the meeting.", "assignee": "Rahul Joshi", "issue_type": "Task", "due_days": 0},
        {"summary": "Schedule API response clarification call", "description": "As Project Manager, schedule a call to clarify API response format.", "assignee": "Sonia Verma", "issue_type": "Task", "due_days": 1}
    ]
}



def generate_dataset(num_samples=10, base_dir="data/raw"):
    # Ensure parent data directory exists
    os.makedirs(base_dir, exist_ok=True)
    transcripts_dir = os.path.join(base_dir, "transcripts")
    summaries_dir = os.path.join(base_dir, "summaries")
    os.makedirs(transcripts_dir, exist_ok=True)
    os.makedirs(summaries_dir, exist_ok=True)
    start_date = datetime(2025, 11, 1)
    num_projects = len(projects)
    for i in range(num_samples):
        project = projects[i % num_projects]
        project_name = project["name"]
        participants = project["participants"]
        agendas = project["agendas"]
        risk_factors = project["risk_factors"]
        meeting_id = f"{i+1:03d}"
        date = start_date + timedelta(days=i)
        sprint = (i // 10) + 1
        backend_points = random.choice([5, 8, 13])
        ux_points = random.choice([3, 5, 8])
        mobile_points = random.choice([3, 5, 8])


        # Transcript file
        sampled_agenda = random.sample(agendas, min(3, len(agendas)))
        transcript_lines = [
            f"Meeting ID: {meeting_id}",
            f"Project: {project_name}",
            f"Date: {date.strftime('%Y-%m-%d')}",
            "Participants:"
        ]
        for p in participants:
            transcript_lines.append(f"  - Name: {p['name']}, Role: {p['role']}")
        transcript_lines.append(f"Agenda: {', '.join(sampled_agenda)}")
        transcript_lines.append(f"Risk Factors: {', '.join(risk_factors)}")
        transcript_lines.append(f"Description: Kickoff meeting for Sprint {sprint} of the {project_name} project. {project['description']} The team discussed assignments, deadlines, sprint planning, potential risks, and initial blockers.")
        transcript_lines.append("Discussion:")
        discussion = project_discussions[project_name]

        # Expand discussion until transcript reaches ~1000 tokens
        def count_tokens(text):
            # Simple token count: split by whitespace
            return len(text.split())

        # Start with one round of discussion
        expanded_discussion = []
        while True:
            for speaker, text in discussion:
                line = text.format(sprint=sprint, backend_points=backend_points, ux_points=ux_points, mobile_points=mobile_points, project_name=project_name)
                expanded_discussion.append(f"{speaker}: {line}")
                # Check if we've reached 1000 tokens
                if count_tokens("\n".join(transcript_lines + expanded_discussion)) >= 1000:
                    break
            if count_tokens("\n".join(transcript_lines + expanded_discussion)) >= 1000:
                break

        transcript_lines.extend(expanded_discussion)

        transcripts_dir = os.path.join(base_dir, "transcripts")
        summaries_dir = os.path.join(base_dir, "summaries")
        os.makedirs(transcripts_dir, exist_ok=True)
        os.makedirs(summaries_dir, exist_ok=True)
        start_date = datetime(2025, 11, 1)

        for project in projects:
            project_name = project["name"].replace(" ","") # For file naming
            participants = project["participants"]
            agendas = project["agendas"]
            risk_factors = project["risk_factors"]
            # Generate 5 stories per project

            for story_num in range(1, 41):
                meeting_id = f"{story_num:03d}"
                date = start_date + timedelta(days=story_num)
                sprint = (story_num // 2) + 1
                story_points = random.choice([1, 3, 5])

                # Alternate meeting types: odd = story discussion, even = issues/risk
                if story_num % 2 == 1:
                    # Story discussion only
                    sampled_agenda = ["Story Discussion"]
                    issues = []
                    transcript_lines = [
                        f"Meeting ID: {meeting_id}",
                        f"Project: {project_name}",
                        f"Date: {date.strftime('%Y-%m-%d')}",
                        "Participants:"
                    ]
                    for p in participants:
                        transcript_lines.append(f"  - Name: {p['name']}, Role: {p['role']}")
                    transcript_lines.append(f"Agenda: {', '.join(sampled_agenda)}")
                    transcript_lines.append(f"Description: Story {story_num} discussed in Sprint {sprint} of the {project_name} project. Story points: {story_points}. {project['description']} The team focused on story planning and assignments.")
                    transcript_lines.append("Discussion:")
                    discussion = project_discussions[project["name"]]
                else:
                    # Issues and risk discussion only
                    sampled_agenda = ["Issues", "Risks"]
                    num_issues = random.randint(5, 10)
                    issues = []
                    for issue_num in range(1, num_issues+1):
                        issue_type = random.choice(["Bug", "Task", "Story", "Issue"])
                        assignee = random.choice(participants)["name"]
                        issues.append({
                            "summary": f"Issue {issue_num} for Story {story_num}",
                            "description": f"Description for issue {issue_num} in story {story_num} of project {project_name}",
                            "assignee": assignee,
                            "issue_type": issue_type,
                            "story_points": story_points,
                            "due_date": (date + timedelta(days=issue_num)).strftime('%Y-%m-%d')
                        })
                    transcript_lines = [
                        f"Meeting ID: {meeting_id}",
                        f"Project: {project_name}",
                        f"Date: {date.strftime('%Y-%m-%d')}",
                        "Participants:"
                    ]
                    for p in participants:
                        transcript_lines.append(f"  - Name: {p['name']}, Role: {p['role']}")
                    transcript_lines.append(f"Agenda: {', '.join(sampled_agenda)}")
                    transcript_lines.append(f"Risk Factors: {', '.join(risk_factors)}")
                    transcript_lines.append(f"Description: Issues and risks for Story {story_num} discussed in Sprint {sprint} of the {project_name} project. {project['description']} The team focused on blockers, bugs, and risk assessment.")
                    transcript_lines.append("Discussion:")
                    discussion = project_discussions[project["name"]]

                # Expand discussion until transcript reaches ~1000 tokens
                def count_tokens(text):
                    return len(text.split())

                expanded_discussion = []
                while True:
                    for speaker, text in discussion:
                        line = text.format(sprint=sprint, backend_points=story_points, ux_points=story_points, mobile_points=story_points, project_name=project_name)
                        expanded_discussion.append(f"{speaker}: {line}")
                        if count_tokens("\n".join(transcript_lines + expanded_discussion)) >= 1000:
                            break
                    if count_tokens("\n".join(transcript_lines + expanded_discussion)) >= 1000:
                        break

                transcript_lines.extend(expanded_discussion)
                transcript_text = "\n".join(transcript_lines)
                tokens = transcript_text.split()
                if len(tokens) > 1000:
                    transcript_text = " ".join(tokens[:1000])

                transcript_filename = f"{project_name}_meeting_{meeting_id}_transcript.txt"
                with open(os.path.join(transcripts_dir, transcript_filename), "w", encoding="utf-8") as f:
                    f.write(transcript_text)

                # Summary & action items file
                summary_json = {
                    "meeting_id": meeting_id,
                    "project": project_name,
                    "participants": participants,
                    "agenda": sampled_agenda,
                    "risk_factors": risk_factors if story_num % 2 == 0 else [],
                    "story_points": story_points,
                    "summary": [
                        s.format(sprint=sprint, project_name=project_name, risk_factors=", ".join(risk_factors))
                        for s in project_summaries[project["name"]]
                    ],
                    "action_items": issues
                }
                summary_filename = f"{project_name}_meeting_{meeting_id}_summary.json"
                with open(os.path.join(summaries_dir, summary_filename), "w", encoding="utf-8") as f:
                    json.dump(summary_json, f, indent=2)

    # Ensure this is at the very end of the file
if __name__ == "__main__":
    generate_dataset()  # Now generates 40 meetings per project with correct naming