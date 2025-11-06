"""
Simple script to download IBM Granite 3.1-3B model
Run this to pre-download the model before using it in your app
"""

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import os

print("=" * 60)
print("Downloading IBM Granite 3.1-3B-a800m-instruct")
print("This will take a few minutes (~3GB download)")
print("=" * 60)
print()

model_id = "ibm-granite/granite-3.1-3b-a800m-instruct"

print("Step 1/2: Downloading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_id)
print("✓ Tokenizer downloaded!")
print()

print("Step 2/2: Downloading model (this is the big one ~3GB)...")
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto"
)
print("✓ Model downloaded!")
print()

print("=" * 60)
print("✅ Download Complete!")
print(f"Model cached at: C:\\Users\\{os.getlogin()}\\.cache\\huggingface\\hub\\")
print("=" * 60)

# Quick test
print("\n🧪 Testing model with a quick generation...")
messages = [{"role": "user", "content": "Say hello in one sentence."}]
inputs = tokenizer.apply_chat_template(
    messages,
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
).to(model.device)

with torch.no_grad():
    outputs = model.generate(**inputs, max_new_tokens=50)

response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
print(f"Model response: {response}")
print("\n✅ Model is working perfectly!")
