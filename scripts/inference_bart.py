

import os
import torch
import argparse
from transformers import BartTokenizer, BartForConditionalGeneration, T5Tokenizer, T5ForConditionalGeneration

# Argument parser for model selection
parser = argparse.ArgumentParser(description="Inference for summarization models (BART, T5, DistilBART, TinyBART, Pegasus)")

parser.add_argument('--model_type', type=str, default='bart', 
    choices=['bart', 't5', 'distilbart', 'tinybart', 'pegasus'], 
    help='Model type: bart, t5, distilbart, tinybart, or pegasus')
parser.add_argument('--model_name', type=str, default=None, help='Model directory or Hugging Face model name')
parser.add_argument('--input_csv', type=str, required=True, help='CSV file with transcripts')
parser.add_argument('--output_csv', type=str, default='predictions.csv', help='Output CSV for summaries')
args = parser.parse_args()

# Set model_dir based on model_name or default
if args.model_name:
    model_dir = args.model_name
else:
    # Default directories for each model type
    default_dirs = {
        'bart': './bart_finetuned_meeting_summary',
        'distilbart': './distilbart_finetuned_meeting_summary',
        'tinybart': './tinybart_finetuned_meeting_summary',
        't5': './t5_finetuned_meeting_summary',
        'pegasus': './pegasus_finetuned_meeting_summary',
    }
    model_dir = default_dirs.get(args.model_type, './bart_finetuned_meeting_summary')

print(f"Loading model and tokenizer from: {model_dir}")

# Model selection
if args.model_type in ['bart', 'distilbart', 'tinybart']:
    tokenizer = BartTokenizer.from_pretrained(model_dir)
    model = BartForConditionalGeneration.from_pretrained(model_dir)
elif args.model_type == 't5':
    tokenizer = T5Tokenizer.from_pretrained(model_dir)
    model = T5ForConditionalGeneration.from_pretrained(model_dir)
elif args.model_type == 'pegasus':
    from transformers import PegasusTokenizer, PegasusForConditionalGeneration
    tokenizer = PegasusTokenizer.from_pretrained(model_dir)
    model = PegasusForConditionalGeneration.from_pretrained(model_dir)
else:
    raise ValueError("Unsupported model_type. Use 'bart', 'distilbart', 'tinybart', 't5', or 'pegasus'.")

# Function to summarize a transcript
def summarize(transcript, max_input_length=512, max_output_length=128):
    if args.model_type == 't5':
        transcript = "summarize: " + transcript
    inputs = tokenizer([transcript], max_length=max_input_length, truncation=True, return_tensors="pt")
    summary_ids = model.generate(
        inputs["input_ids"],
        num_beams=4,
        max_length=max_output_length,
        early_stopping=True,
        length_penalty=1.0,
        forced_bos_token_id=tokenizer.bos_token_id if hasattr(tokenizer, 'bos_token_id') and tokenizer.bos_token_id is not None else None
    )
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary

if __name__ == "__main__":
    import pandas as pd
    # Load transcripts from CSV
    df = pd.read_csv(args.input_csv)
    if 'transcript' not in df.columns:
        raise ValueError("Input CSV must have a 'transcript' column.")

    summaries = []
    for text in df['transcript']:
        summary = summarize(str(text))
        summaries.append(summary)

    df['generated_summary'] = summaries
    df.to_csv(args.output_csv, index=False)
    print(f"Saved {len(summaries)} summaries to {args.output_csv}")
