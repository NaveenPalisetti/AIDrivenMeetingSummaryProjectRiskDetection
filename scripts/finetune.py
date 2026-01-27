
import os
import pandas as pd
from datasets import Dataset
from transformers import BartTokenizer, BartForConditionalGeneration, T5Tokenizer, T5ForConditionalGeneration, Trainer, TrainingArguments
import torch
import argparse


# Argument parser for model selection
os.environ["WANDB_MODE"] = "disabled"
parser = argparse.ArgumentParser(description="Finetune a summarization model (BART, T5, DistilBART, TinyBART, Pegasus)")
parser.add_argument('--model_type', type=str, default='bart', 
    choices=['bart', 't5', 'distilbart', 'tinybart', 'pegasus'], 
    help='Model type: bart, t5, distilbart, tinybart, or pegasus')
parser.add_argument('--model_name', type=str, default=None, help='Model name or LOCAL PATH for loading (not for saving)')
parser.add_argument('--train_csv', type=str, default='meeting_train.csv', help='CSV file for training data')
parser.add_argument('--val_csv', type=str, default='meeting_val.csv', help='CSV file for validation data')
parser.add_argument('--output', type=str, default='models', help='Output folder to save finetuned model')
args = parser.parse_args()

# Load the datasets

import json

def check_json_column(df, column_name):
    for idx, val in enumerate(df[column_name]):
        try:
            parsed = json.loads(val)
            if not isinstance(parsed, list):
                raise ValueError(f"Row {idx} in '{column_name}' is not a JSON list: {val}")
        except Exception as e:
            raise ValueError(f"Row {idx} in '{column_name}' is not valid JSON: {val}\nError: {e}")

train_df = pd.read_csv(args.train_csv)
val_df = pd.read_csv(args.val_csv)

# Check participants and action_items columns for valid JSON arrays
check_json_column(train_df, "participants")
check_json_column(train_df, "action_items")
check_json_column(val_df, "participants")
check_json_column(val_df, "action_items")

train_dataset = Dataset.from_pandas(train_df)
val_dataset = Dataset.from_pandas(val_df)


# Model selection
if args.model_type == 'bart':
    model_name = args.model_name or "facebook/bart-base"
    tokenizer = BartTokenizer.from_pretrained(model_name)
    model = BartForConditionalGeneration.from_pretrained(model_name)
elif args.model_type == 'distilbart':
    model_name = args.model_name or "sshleifer/distilbart-cnn-12-6"
    tokenizer = BartTokenizer.from_pretrained(model_name)
    model = BartForConditionalGeneration.from_pretrained(model_name)
elif args.model_type == 'tinybart':
    model_name = args.model_name or "sshleifer/tinybart-cnn-6-6"
    tokenizer = BartTokenizer.from_pretrained(model_name)
    model = BartForConditionalGeneration.from_pretrained(model_name)
elif args.model_type == 't5':
    model_name = args.model_name or "t5-small"
    tokenizer = T5Tokenizer.from_pretrained(model_name)
    model = T5ForConditionalGeneration.from_pretrained(model_name)
elif args.model_type == 'pegasus':
    model_name = args.model_name or "google/pegasus-xsum"
    from transformers import PegasusTokenizer, PegasusForConditionalGeneration
    tokenizer = PegasusTokenizer.from_pretrained(model_name)
    model = PegasusForConditionalGeneration.from_pretrained(model_name)
else:
    raise ValueError("Unsupported model_type. Use 'bart', 'distilbart', 'tinybart', 't5', or 'pegasus'.")


# Preprocessing function for BART and T5
import json
max_input_length = 256
# Dynamically determine max_target_length based on training data
def compute_max_json_length(df, fields=["summary", "participants", "agenda", "action_items"]):
    max_len = 0
    for i, row in df.iterrows():
        try:
            target = json.dumps({
                "summary": row.get("summary", ""),
                "participants": json.loads(row.get("participants", "[]")),
                "agenda": row.get("agenda", ""),
                "action_items": json.loads(row.get("action_items", "[]")),
            }, ensure_ascii=False)
            max_len = max(max_len, len(target))
        except Exception as e:
            print(f"[WARN] Could not parse row {i} for max_target_length calculation: {e}")
    return max_len

max_json_length = compute_max_json_length(train_df)
# Add a safety margin (e.g., 20%) and convert to tokens (roughly 4 chars/token for English)
max_target_length = int((max_json_length * 1.2) // 4) + 10
print(f"[INFO] Computed max_target_length for JSON output: {max_target_length} tokens (max JSON chars: {max_json_length})")
debug_printed = False
def preprocess_function(examples):
    global debug_printed
    inputs = examples["transcript"]
    participants = examples.get("participants", "")
    action_items = examples.get("action_items", "")
    agenda = examples.get("agenda", "")
    summary = examples.get("summary", "")
    # Convert fields to lists if not already
    def parse_field(val):
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                return parsed if isinstance(parsed, (list, dict)) else val
            except Exception:
                # fallback: split by semicolon or comma
                if ";" in val:
                    return [v.strip() for v in val.split(";") if v.strip()]
                if "," in val:
                    return [v.strip() for v in val.split(",") if v.strip()]
                return val
        return val
    participants = [parse_field(p) for p in participants]
    action_items = [parse_field(a) for a in action_items]
    agenda = [parse_field(a) for a in agenda]
    summary = [s for s in summary]
    # Build a structured JSON target for each example in the batch
    targets = [
        json.dumps({
            "summary": s,
            "participants": p,
            "agenda": a,
            "action_items": ai
        }, ensure_ascii=False)
        for s, p, a, ai in zip(summary, participants, agenda, action_items)
    ]
    # Print a few targets for debugging (only once)
    if not debug_printed:
        for t in targets[:3]:
            print("[DEBUG] Training target:", t)
        debug_printed = True
    model_inputs = tokenizer(
        inputs, max_length=max_input_length, truncation=True, padding="max_length"
    )
    labels = tokenizer(
        targets, max_length=max_target_length, truncation=True, padding="max_length"
    )
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs


# Tokenize the datasets
tokenized_train = train_dataset.map(preprocess_function, batched=True)
tokenized_val = val_dataset.map(preprocess_function, batched=True)

# Training arguments
output_dir = os.path.join(args.output, f"{args.model_type}_finetuned_meeting_summary")
training_args = TrainingArguments(
    output_dir=output_dir,
    num_train_epochs=3,
    per_device_train_batch_size=2,
    save_steps=500,
    save_total_limit=2,
    logging_steps=100,
    learning_rate=5e-5,
    fp16=torch.cuda.is_available(),
)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_val,
)

# Train
trainer.train()

# Save the model and tokenizer
trainer.save_model(output_dir)
tokenizer.save_pretrained(output_dir)
print(f"Finetuned {args.model_type.upper()} model and tokenizer saved to {output_dir}")
