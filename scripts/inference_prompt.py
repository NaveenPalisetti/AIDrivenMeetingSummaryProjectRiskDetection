import pandas as pd
import argparse
from transformers import (
    BartTokenizer, BartForConditionalGeneration,
    T5Tokenizer, T5ForConditionalGeneration,
    PegasusTokenizer, PegasusForConditionalGeneration
)
import torch
import os

parser = argparse.ArgumentParser(description="Prompt-based meeting summarization inference")
parser.add_argument('--model_type', type=str, default='bart', choices=['bart', 't5', 'distilbart', 'tinybart', 'pegasus'], help='Model type')
parser.add_argument('--model_name', type=str, required=True, help='Model name or LOCAL PATH')
parser.add_argument('--input_csv', type=str, required=True, help='CSV file with transcripts')
parser.add_argument('--output_csv', type=str, default='data/predictions/meeting_summaries.csv', help='Output CSV for summaries')
args = parser.parse_args()

# Load transcripts
df = pd.read_csv(args.input_csv)
if 'transcript' not in df.columns:
    raise ValueError("Input CSV must have a 'transcript' column.")

# Load model and tokenizer
if args.model_type in ['bart', 'distilbart', 'tinybart']:
    tokenizer = BartTokenizer.from_pretrained(args.model_name)
    model = BartForConditionalGeneration.from_pretrained(args.model_name)
elif args.model_type == 't5':
    tokenizer = T5Tokenizer.from_pretrained(args.model_name)
    model = T5ForConditionalGeneration.from_pretrained(args.model_name)
elif args.model_type == 'pegasus':
    tokenizer = PegasusTokenizer.from_pretrained(args.model_name)
    model = PegasusForConditionalGeneration.from_pretrained(args.model_name)
else:
    raise ValueError("Unsupported model_type.")

model.eval()
if torch.cuda.is_available():
    model.to('cuda')

summaries = []
for text in df['transcript']:
    if args.model_type == 't5':
        input_text = "summarize: " + str(text)
    else:
        input_text = str(text)
    inputs = tokenizer([input_text], max_length=256, truncation=True, return_tensors="pt")
    if torch.cuda.is_available():
        inputs = {k: v.to('cuda') for k, v in inputs.items()}
    with torch.no_grad():
        summary_ids = model.generate(
            inputs['input_ids'],
            attention_mask=inputs['attention_mask'],
            max_length=64,
            num_beams=4,
            length_penalty=2.0,
            early_stopping=True
        )
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    summaries.append(summary)

df['generated_summary'] = summaries
os.makedirs(os.path.dirname(args.output_csv), exist_ok=True)
df.to_csv(args.output_csv, index=False)
print(f"Summaries saved to {args.output_csv}")
