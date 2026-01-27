# Script to check and clean your meeting summarization dataset
# Usage: python check_clean_dataset.py

import pandas as pd
import os

# Path to your dataset CSV
csv_path = "data/processed/meeting_dataset.csv"

# Load dataset
if not os.path.exists(csv_path):
    print(f"File not found: {csv_path}")
    exit(1)

df = pd.read_csv(csv_path)
print(f"Loaded {len(df)} rows from {csv_path}")

# Check for missing values
missing = df.isnull().sum()
print("Missing values per column:")
print(missing)

# Drop rows with missing transcript or summary
before = len(df)
df = df.dropna(subset=["transcript", "summary"])
after = len(df)
print(f"Dropped {before - after} rows with missing transcript or summary.")

# Remove duplicates
before = len(df)
df = df.drop_duplicates(subset=["transcript", "summary"])
after = len(df)
print(f"Dropped {before - after} duplicate rows.")

# Preview a few samples
print("\nSample rows:")
print(df.sample(min(3, len(df))))

# Split into train and validation sets (80/20)
from sklearn.model_selection import train_test_split
train_df, val_df = train_test_split(df, test_size=0.2, random_state=42)

# Save cleaned dataset
clean_path = "data/processed/meeting_dataset_clean.csv"
df.to_csv(clean_path, index=False)
print(f"Cleaned dataset saved to {clean_path}")

# Save train and validation sets
train_path = "data/processed/meeting_train.csv"
val_path = "data/processed/meeting_val.csv"
train_df.to_csv(train_path, index=False)
val_df.to_csv(val_path, index=False)
print(f"Train set saved to {train_path} ({len(train_df)} rows)")
print(f"Validation set saved to {val_path} ({len(val_df)} rows)")
