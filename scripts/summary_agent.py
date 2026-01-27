import os
import json
import re
import glob
import pandas as pd
from typing import List, Dict

# Preprocessing function for transcripts
def preprocess_transcript(text: str) -> str:
    text = re.sub(r'\b[A-Za-z ]+:', '', text)  # Remove speaker labels
    text = re.sub(r'\s+', ' ', text)           # Normalize whitespace
    text = text.strip()
    return text

# Load transcript-summary pairs
def load_dataset(transcript_dir: str, summary_dir: str) -> List[Dict[str, str]]:
    pairs = []
    transcript_files = sorted(glob.glob(os.path.join(transcript_dir, '*.txt')))
    for transcript_path in transcript_files:
        meeting_id = os.path.basename(transcript_path).split('_')[2] if '_' in os.path.basename(transcript_path) else os.path.basename(transcript_path).split('.')[0].split('_')[-2]
        summary_pattern = f'*{meeting_id}*_summary.json'
        summary_files = glob.glob(os.path.join(summary_dir, summary_pattern))
        if not summary_files:
            continue
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript = preprocess_transcript(f.read())
        with open(summary_files[0], 'r', encoding='utf-8') as f:
            summary_json = json.load(f)
            summary = ' '.join(summary_json.get('summary', []))
        pairs.append({'transcript': transcript, 'summary': summary})
    return pairs

# Save dataset in CSV format for Hugging Face
def save_dataset_csv(pairs: List[Dict[str, str]], out_path: str):
    df = pd.DataFrame(pairs)
    df.to_csv(out_path, index=False)

# Example scoring function (ROUGE)
def compute_rouge(preds: List[str], refs: List[str]) -> Dict[str, float]:
    from rouge_score import rouge_scorer
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)
    scores = {'rouge1': 0, 'rougeL': 0}
    for pred, ref in zip(preds, refs):
        score = scorer.score(ref, pred)
        scores['rouge1'] += score['rouge1'].fmeasure
        scores['rougeL'] += score['rougeL'].fmeasure
    n = len(preds)
    return {k: v/n for k, v in scores.items()}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Meeting dataset CSV and ROUGE scorer")
    parser.add_argument('--make_csv', action='store_true', help='Generate meeting_dataset.csv from data/raw/transcripts and data/raw/summaries')
    parser.add_argument('--score_rouge', action='store_true', help='Score predictions.json with ROUGE against reference summaries')
    parser.add_argument('--csv_path', type=str, default='data/processed/meeting_dataset.csv', help='CSV file to use for ROUGE scoring')
    parser.add_argument('--preds_path', type=str, default='data/predictions/predictions.json', help='Predictions JSON file for ROUGE scoring')
    args = parser.parse_args()

    if args.make_csv or (not args.make_csv and not args.score_rouge):
        transcript_dir = "data/raw/transcripts"
        summary_dir = "data/raw/summaries"
        out_path = args.csv_path
        pairs = load_dataset(transcript_dir, summary_dir)
        print(f"Loaded {len(pairs)} transcript-summary pairs.")
        save_dataset_csv(pairs, out_path)
        print(f"Saved dataset to {out_path}")

    if args.score_rouge:
        # Load reference summaries from CSV
        if not os.path.exists(args.csv_path):
            print(f"CSV file {args.csv_path} not found. Please generate it first.")
            exit(1)
        df = pd.read_csv(args.csv_path)
        refs = df['summary'].tolist()
        preds_path = args.preds_path
        if os.path.exists(preds_path):
            with open(preds_path, "r", encoding="utf-8") as f:
                preds = json.load(f)
            if len(preds) != len(refs):
                print(f"Warning: {len(preds)} predictions but {len(refs)} references.")
            scores = compute_rouge(preds, refs)
            print("ROUGE scores:", scores)
            with open("rouge_scores.json", "w", encoding="utf-8") as f:
                json.dump(scores, f, indent=2)
            print("ROUGE scores saved to rouge_scores.json")
        else:
            print(f"No predictions found at {preds_path}. Please save your model-generated summaries as a JSON list in this file.")
