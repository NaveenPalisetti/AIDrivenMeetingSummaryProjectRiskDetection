# Script to check tokenization and data loading for your summarization dataset
# Usage: python check_tokenization.py --model_type bart --model_name facebook/bart-base --csv meeting_dataset_clean.csv

import pandas as pd
import argparse
from transformers import (
    BartTokenizer,
    T5Tokenizer,
    PegasusTokenizer,
    AutoTokenizer
)

parser = argparse.ArgumentParser(description="Check tokenization and data loading.")
parser.add_argument('--model_type', type=str, default='bart', choices=['bart', 'distilbart', 'tinybart', 't5', 'pegasus'],
                    help='Model type: bart, distilbart, tinybart, t5, pegasus')
parser.add_argument('--model_name', type=str, default='facebook/bart-base', help='Model name or local path')
parser.add_argument('--csv', type=str, default='meeting_dataset_clean.csv', help='CSV file to check')
args = parser.parse_args()

# Load data
print(f"Loading {args.csv} ...")
df = pd.read_csv(args.csv)
print(f"Loaded {len(df)} rows.")
print("Sample rows:")
print(df.head(3))

# Load tokenizer
if args.model_type == 'bart' or args.model_type == 'distilbart' or args.model_type == 'tinybart':
    tokenizer = BartTokenizer.from_pretrained(args.model_name)
elif args.model_type == 't5':
    tokenizer = T5Tokenizer.from_pretrained(args.model_name)
elif args.model_type == 'pegasus':
    tokenizer = PegasusTokenizer.from_pretrained(args.model_name)
else:
    # fallback to AutoTokenizer for any other model
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)

# Check tokenization for a few samples
for i in range(min(3, len(df))):
    text = df.iloc[i]['transcript']
    print(f"\nSample {i+1} transcript:")
    print(text[:200])
    tokens = tokenizer(text, max_length=256, truncation=True, padding="max_length")
    print("Tokenized input_ids:", tokens['input_ids'][:20], '...')
    print("Decoded text:", tokenizer.decode(tokens['input_ids']))

    summary = df.iloc[i]['summary']
    print(f"Sample {i+1} summary:")
    print(summary[:200])
    tokens = tokenizer(summary, max_length=64, truncation=True, padding="max_length")
    print("Tokenized summary input_ids:", tokens['input_ids'][:20], '...')
    print("Decoded summary:", tokenizer.decode(tokens['input_ids']))
