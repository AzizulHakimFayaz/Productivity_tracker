import os
import platform
import numpy as np

print("Loading AI model... please wait...")

# Windows DLL workaround for ONNX Runtime
if platform.system() == "Windows":
    import site
    paths = site.getsitepackages()
    if hasattr(site, "getusersitepackages"):
        paths.append(site.getusersitepackages())
    for package_path in paths:
        onnx_path = os.path.join(package_path, "onnxruntime", "capi")
        if os.path.exists(onnx_path):
            os.add_dll_directory(onnx_path)
            
from fastembed import TextEmbedding

# Load the exact same model we use in classifier.py
model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")

CATEGORY_DESCRIPTIONS = {
    "coding": "programming coding development software engineering debugging IDE terminal",
    "learning": "learning tutorial course research studying documentation education",
    "writing": "writing typing notes chatgpt blogging documentation composing",
    "communication": "meeting email slack teams zoom chat messaging video call",
    "entertainment": "youtube netflix video gaming social media fun browsing reddit memes",
}

categories = list(CATEGORY_DESCRIPTIONS.keys())
cat_texts = [CATEGORY_DESCRIPTIONS[c] for c in categories]

# Embed category descriptions
cat_embeddings = np.array(list(model.embed(cat_texts)))

print("\n✅ FastEmbed initialized successfully!")
print("Type an app title, website, or generic text to see how it is classified.")
print("The 'unknown' threshold is REMOVED so you will see exactly what it guesses.")
print("Type 'exit' to quit.\n")

while True:
    text = input("Enter text to classify > ")
    if text.lower() in ('exit', 'quit'):
        break
        
    if not text.strip():
        continue
        
    # Embed single text
    q_emb = list(model.embed([text]))[0]
    
    # Get cosine similarity scores
    scores = np.dot(cat_embeddings, q_emb)
    
    best_idx = int(scores.argmax())
    best_score = float(scores[best_idx])
    result = categories[best_idx]
    
    print(f"\n🧠 AI GUESS: {result.upper()} (Top Score: {best_score:.3f})")
    
    # Print out detailed scores for everything
    print("   Detailed Breakdown:")
    # Sort them by score decending for easy reading
    sorted_indices = scores.argsort()[::-1]
    for idx in sorted_indices:
        cat = categories[idx]
        score = scores[idx]
        print(f"     - {cat.capitalize():15s}: {score:.3f}")
    print("\n" + "-"*40 + "\n")
