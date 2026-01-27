import os
import json
import pandas as pd
from typing import List, Dict

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
    parser = argparse.ArgumentParser(description="Evaluate predictions with ROUGE from a CSV file.")
    parser.add_argument('--csv_path', type=str, required=True, help='CSV file with reference and generated summaries')
    parser.add_argument('--ref_col', type=str, default='summary', help='Column name for reference summaries')
    parser.add_argument('--pred_col', type=str, default='generated_summary', help='Column name for generated summaries')
    parser.add_argument('--model_name', type=str, default=None, help='Name of the model for saving scores in JSON (optional)')
    args = parser.parse_args()

    if not os.path.exists(args.csv_path):
        print(f"CSV file {args.csv_path} not found. Please generate it first.")
        exit(1)
    df = pd.read_csv(args.csv_path)
    if args.ref_col not in df.columns or args.pred_col not in df.columns:
        print(f"CSV must contain columns '{args.ref_col}' and '{args.pred_col}'.")
        exit(1)
    refs = df[args.ref_col].astype(str).tolist()
    preds = df[args.pred_col].astype(str).tolist()
    if len(preds) != len(refs):
        print(f"Warning: {len(preds)} predictions but {len(refs)} references.")
    scores = compute_rouge(preds, refs)
    print("ROUGE scores:", scores)
    # Save ROUGE scores in the same directory as the input CSV
    output_csv_dir = os.path.dirname(os.path.abspath(args.csv_path))
    os.makedirs(output_csv_dir, exist_ok=True)
    # Use model name from argument or CSV path as key
    model_name = args.model_name if args.model_name else os.path.basename(os.path.dirname(os.path.abspath(args.csv_path)))
    # Path to the shared JSON file
    output_path = os.path.join(output_csv_dir, "rouge_scores.json")
    # Load existing scores if file exists
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            all_scores = json.load(f)
    else:
        all_scores = {}
    # Add/update this model's scores
    all_scores[model_name] = scores
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_scores, f, indent=2)
    print(f"ROUGE scores for {model_name} saved/updated in {output_path}")
