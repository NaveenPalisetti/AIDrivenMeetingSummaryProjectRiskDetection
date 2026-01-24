# Download and cache Hugging Face models locally for offline use
# Usage: python download_hf_model.py --model_name sshleifer/distilbart-cnn-12-6 --save_dir ./local_distilbart
# Example for Mistral small 32k:
# python download_hf_model.py --model_name mistralai/Mistral-7B-Instruct-v0.2 --save_dir ./local_mistral --causal_lm


import argparse
import os
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, PegasusTokenizer, PegasusForConditionalGeneration, T5Tokenizer, T5ForConditionalGeneration, BartTokenizer, BartForConditionalGeneration, AutoModel, AutoModelForCausalLM


def main():
    parser = argparse.ArgumentParser(description="Download and cache a Hugging Face model/tokenizer for offline use.")
    parser.add_argument('--model_name', type=str, required=True, help='Hugging Face model name (e.g., sshleifer/distilbart-cnn-12-6)')
    parser.add_argument('--save_dir', type=str, required=True, help='Directory to save the model and tokenizer')
    parser.add_argument('--causal_lm', action='store_true', help='Use AutoModelForCausalLM for causal language models (e.g., Mistral, TinyLlama)')
    args = parser.parse_args()

    os.makedirs(args.save_dir, exist_ok=True)
    print(f"Downloading and saving {args.model_name} to {args.save_dir} ...")

    # Use model-specific classes for Pegasus, T5, BART, BERT, or causal LM (Mistral, TinyLlama, etc.)
    if 'pegasus' in args.model_name.lower():
        print("Using Pegasus model.")
        tokenizer = PegasusTokenizer.from_pretrained(args.model_name)
        model = PegasusForConditionalGeneration.from_pretrained(args.model_name)
    elif 't5' in args.model_name.lower():
        print("Using T5 model.")
        tokenizer = T5Tokenizer.from_pretrained(args.model_name)
        model = T5ForConditionalGeneration.from_pretrained(args.model_name)
    elif 'bart' in args.model_name.lower():
        print("Using BART model.")
        tokenizer = BartTokenizer.from_pretrained(args.model_name)
        model = BartForConditionalGeneration.from_pretrained(args.model_name)
    elif 'bert' in args.model_name.lower():
        print("Using BERT model.")
        tokenizer = AutoTokenizer.from_pretrained(args.model_name)
        model = AutoModel.from_pretrained(args.model_name)
    elif args.causal_lm or any(x in args.model_name.lower() for x in ["mistral", "tinyllama", "llama", "gpt", "falcon"]):
        print("Using AutoModelForCausalLM for causal language model (e.g., Mistral, TinyLlama, Llama, GPT, Falcon).")
        tokenizer = AutoTokenizer.from_pretrained(args.model_name)
        model = AutoModelForCausalLM.from_pretrained(args.model_name)
    else:
        print("Using AutoModelForSeq2SeqLM (default).")
        tokenizer = AutoTokenizer.from_pretrained(args.model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(args.model_name)

    tokenizer.save_pretrained(args.save_dir)
    model.save_pretrained(args.save_dir)
    print("Done. You can now use this directory as your model_name in your training/inference scripts.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Download interrupted by user.")
