
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
train_df = pd.read_csv(args.train_csv)
val_df = pd.read_csv(args.val_csv)
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
max_input_length = 256
max_target_length = 64
def preprocess_function(examples):
    inputs = examples["transcript"]
    targets = examples["summary"]
    if args.model_type == 't5':
        # T5 expects a prefix for summarization
        inputs = ["summarize: " + inp for inp in inputs]
    elif args.model_type == 'pegasus':
        # Pegasus expects no prefix, but you may want to truncate/pad differently if needed
        pass
    model_inputs = tokenizer(inputs, max_length=max_input_length, truncation=True, padding="max_length")
    with tokenizer.as_target_tokenizer():
        labels = tokenizer(targets, max_length=max_target_length, truncation=True, padding="max_length")
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
