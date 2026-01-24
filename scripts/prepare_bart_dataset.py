import os
import json

TRANSCRIPTS_DIR = os.path.join('data', 'Transcripts')
SUMMARIES_DIR = os.path.join('data', 'Summaries')
OUTPUT_FILE = 'train_dataset.jsonl'

def get_meeting_id(filename):
    # Extract meeting id from filename (e.g., Meeting_01_Transcript.txt -> Meeting_01)
    return filename.split('_Transcript')[0]

def main():
    pairs = []
    for fname in os.listdir(TRANSCRIPTS_DIR):
        if not fname.endswith('.txt'):
            continue
        meeting_id = get_meeting_id(fname)
        transcript_path = os.path.join(TRANSCRIPTS_DIR, fname)
        summary_fname = meeting_id + '_summary.json'
        summary_path = os.path.join(SUMMARIES_DIR, summary_fname)
        print(f"Checking transcript: {fname} -> summary: {summary_fname}")
        if not os.path.exists(summary_path):
            print(f'Summary not found for {fname}, expected: {summary_fname}, skipping.')
            continue
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript = f.read()
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary_json = json.load(f)
            # Try to get the summary text from the JSON
            summary = summary_json.get('summary') or summary_json.get('Summary') or str(summary_json)
        pairs.append({'transcript': transcript, 'summary': summary})
    # Write to JSONL
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')
    print(f'Dataset created: {OUTPUT_FILE} with {len(pairs)} pairs.')

if __name__ == '__main__':
    main()
