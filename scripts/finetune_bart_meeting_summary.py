
import os
import json
from transformers import BartTokenizer, BartForConditionalGeneration, Trainer, TrainingArguments, DataCollatorForSeq2Seq
from datasets import load_dataset, Dataset
import evaluate
import torch

# Paths
MODEL_PATH = "models/local_bart_large_cnn"  # Update if your BART model is elsewhere
DATASET_PATH = "train_dataset.jsonl"
OUTPUT_DIR = "models/local_bart_large_cnn_finetuned"

# Hyperparameters
BATCH_SIZE = 2
EPOCHS = 3
MAX_INPUT_LENGTH = 1024
MAX_TARGET_LENGTH = 256

# Load tokenizer and model
print("Loading tokenizer and model...")
tokenizer = BartTokenizer.from_pretrained(MODEL_PATH)
model = BartForConditionalGeneration.from_pretrained(MODEL_PATH)

# Load dataset
def load_jsonl_dataset(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = [json.loads(line) for line in f]
    return Dataset.from_list(data)

dataset = load_jsonl_dataset(DATASET_PATH)

def preprocess_function(examples):
    inputs = examples["transcript"]
    targets = examples["summary"]
    model_inputs = tokenizer(inputs, max_length=MAX_INPUT_LENGTH, truncation=True, padding="max_length")
    with tokenizer.as_target_tokenizer():
        labels = tokenizer(targets, max_length=MAX_TARGET_LENGTH, truncation=True, padding="max_length")
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs


# Metrics (use evaluate library)
rouge_metric = evaluate.load("rouge")
bleu_metric = evaluate.load("bleu")

def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    decoded_preds = tokenizer.batch_decode(predictions, skip_special_tokens=True)
    # Replace -100 in the labels as we can't decode them
    labels = [[(l if l != -100 else tokenizer.pad_token_id) for l in label] for label in labels]
    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
    # ROUGE
    rouge_result = rouge_metric.compute(predictions=decoded_preds, references=decoded_labels)
    # BLEU
    bleu_result = bleu_metric.compute(predictions=[pred.split() for pred in decoded_preds], references=[[label.split()] for label in decoded_labels])
    # Loss is logged automatically by Trainer
    return {
        "rouge1": rouge_result["rouge1"].mid.fmeasure,
        "rouge2": rouge_result["rouge2"].mid.fmeasure,
        "rougeL": rouge_result["rougeL"].mid.fmeasure,
        "bleu": bleu_result["bleu"],
    }

print("Tokenizing dataset...")
tokenized_dataset = dataset.map(preprocess_function, batched=True, remove_columns=dataset.column_names)

data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=BATCH_SIZE,
    num_train_epochs=EPOCHS,
    save_total_limit=2,
    save_steps=50,
    logging_steps=10,
    fp16=torch.cuda.is_available(),
    report_to=[],
)


trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    data_collator=data_collator,
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
)


print("Starting training...")
train_result = trainer.train()
metrics = train_result.metrics
print(f"Training completed. Final loss: {metrics.get('train_loss', 'N/A')}")

print(f"Model fine-tuned and saved to {OUTPUT_DIR}")