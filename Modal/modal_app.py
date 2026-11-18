# ===================== NAMESPACE IMPORTS =====================
# Imports required for app deployment, API routing, and regex processing

import modal                                  # Modal library for serverless deployment
import os                                     # OS module for environment variables
import re                                     # Regex module for text cleanup
from fastapi import FastAPI                   # FastAPI framework for API routing
from pydantic import BaseModel                # Pydantic for request schema validation

# ===================== APP & VOLUME SETUP =====================
# Initializes the Modal app and a persistent volume for model caching

app = modal.App("image-caption-studio")       # Define the app name

# Create a persistent volume to cache the 15GB model weights
model_cache = modal.Volume.from_name("hf-hub-cache", create_if_missing=True) # Mount volume
CACHE_DIR = "/cache"                          # Define cache path

# ===================== DOCKER IMAGE DEFINITION =====================
# Defines the environment, dependencies, and variables for the GPU container

image = (
    modal.Image.from_registry(
        "qwenllm/qwenvl:2.5-cu121",           # Base image with CUDA 12.1
        add_python="3.11"                     # Ensure Python 3.11 is installed
    )
    .pip_install(
        "fastapi[standard]",                  # Web framework
        "transformers==4.53.3",               # Hugging Face transformers
        "accelerate==0.27.2",                 # Acceleration library
        "bitsandbytes>=0.46.1,<0.47.0",       # Quantization library
        "qwen-vl-utils==0.0.8",               # Qwen specific utilities
        "pillow",                             # Image processing
        "torch==2.4.0",                       # PyTorch
        "torchvision==0.19.0",                # Torchvision
        extra_options="--extra-index-url https://download.pytorch.org/whl/cu121" # CUDA wheel index
    )
    .env({
        "HF_HUB_CACHE": CACHE_DIR,            # Set HF cache directory
        "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True" # Prevent OOM fragmentation
    })
)

# ===================== REQUEST SCHEMA =====================
# Defines the structure of the JSON payload expected from the frontend

class CaptionRequest(BaseModel):
    image: str                                # Base64 encoded image
    styles: list                              # List of requested styles
    word_limits: dict                         # Dictionary of word limits

# ===================== MODAL SERVERLESS CLASS =====================
# Defines the GPU configuration, container lifecycle, and API endpoints

@app.cls(
    image=image,                              # Use defined Docker image
    gpu="A10G",                               # Allocate A10G GPU
    timeout=600,                              # Timeout after 10 minutes
    scaledown_window=600,                     # Stay warm for 10 minutes
    volumes={CACHE_DIR: model_cache}          # Mount cached volume
)
class CaptionModel:
    
    # -------------------- MODEL INITIALIZATION --------------------
    # Runs once when the container starts, loading the model into GPU memory
    
    @modal.enter()
    def load_model(self):
        import torch                          # Import inside function to save local startup time
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
        
        print("🚀 Loading Qwen2.5-VL-7B-Instruct...") # Log status
        model_id = "Qwen/Qwen2.5-VL-7B-Instruct" # Model identifier
        
        # 4-bit quantization configuration to fit the 7B model on the A10G GPU
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,                # Enable 4-bit quantization
            bnb_4bit_compute_dtype=torch.float16, # Compute in FP16
            bnb_4bit_quant_type="nf4",        # NF4 quantization type
            bnb_4bit_use_double_quant=True,   # Double quantization
        )
        
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_id,                         # Load model
            quantization_config=quantization_config, # Apply 4-bit config
            device_map="auto",                # Auto-device placement
            trust_remote_code=True            # Allow custom code
        )
        
        # Load processor with a max pixel constraint to prevent OOM errors
        self.processor = AutoProcessor.from_pretrained(
            model_id,                         # Model identifier
            use_fast=False,                   # Use slow processor
            trust_remote_code=True,           # Allow custom code
            max_pixels=2048 * 28 * 28         # Limit image resolution
        )
        print("✅ Model loaded successfully!") # Log success

    # -------------------- API ENDPOINT DEFINITION --------------------
    # Defines the FastAPI app and routes
    
    @modal.asgi_app()
    def web(self):
        import torch                          # Import torch
        import base64                         # Import base64
        from io import BytesIO                # Import BytesIO
        from PIL import Image                 # Import PIL
        from collections import OrderedDict   # Import OrderedDict

        api = FastAPI()                       # Initialize API

        # Health check endpoint
        @api.get("/health")
        def health():
            return {"status": "healthy"}      # Return health status

        # Main generation endpoint
        @api.post("/generate-captions")
        async def generate(req: CaptionRequest):
            try:
                # Decode the base64 image string into a PIL Image
                image_data = base64.b64decode(req.image) # Decode base64
                pil_image = Image.open(BytesIO(image_data)).convert("RGB") # Open as RGB

                # Determine which caption types to generate
                caption_types = ['short', 'technical', 'human-friendly'] if 'all' in req.styles else req.styles
                results = OrderedDict()       # Store results in order

                # -------------------- GENERATION HELPER --------------------
                # Handles the model inference for a given set of prompts
                def run_generation(system_msg, user_msg, max_tokens, temperature):
                    messages = [              # Build chat messages
                        {"role": "system", "content": system_msg}, # System prompt
                        {"role": "user", "content": [              # User prompt
                            {"type": "image", "image": pil_image}, # Attach image
                            {"type": "text", "text": user_msg}     # Attach text prompt
                        ]}
                    ]
                    
                    # Prepare inputs for the model
                    text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True) # Format prompt
                    image_inputs = self.processor(text=text, images=pil_image, return_tensors="pt") # Process image and text
                    image_inputs = {k: v.to(self.model.device) for k, v in image_inputs.items()} # Move to GPU

                    # Generate text
                    with torch.no_grad():     # Disable gradient calculation
                        generated_ids = self.model.generate(
                            **image_inputs,   # Inputs
                            max_new_tokens=max_tokens, # Max tokens to generate
                            do_sample=True,   # Enable sampling
                            temperature=temperature, # Creativity level
                            top_p=0.9,        # Nucleus sampling
                            repetition_penalty=1.1 # Prevent repetition
                        )

                    # Decode output and strip quotes
                    generated_ids_trimmed = [
                        out_ids[len(in_ids):] for in_ids, out_ids in zip(image_inputs["input_ids"], generated_ids) # Remove prompt tokens
                    ]
                    caption = self.processor.batch_decode(
                        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=True
                    )[0].strip()              # Decode to string
                    
                    return caption.strip('"').strip("'").strip() # Strip quotes

                # -------------------- MAIN GENERATION LOOP --------------------
                # Iterates through requested styles and applies 3-pass logic
                for caption_type in ['short', 'technical', 'human-friendly']:
                    if caption_type not in caption_types:
                        continue              # Skip unrequested styles
                    
                    target = req.word_limits.get(caption_type, 25) # Target word count
                    min_words = max(5, target - 3) # Minimum allowed
                    max_words = target + 3    # Maximum allowed

                    # === PASS 1: Initial Generation ===
                    if caption_type == 'short':
                        system_msg = "You are an expert image captioning assistant. Your task is to write a concise caption."
                        user_msg = f"Describe this image in exactly {target} words. Start your sentence and count down from {target} words. Output only the caption."
                        temp = 0.3            # Low temp for precision
                    
                    elif caption_type == 'technical':
                        system_msg = "You are a technical image analysis expert. Generate a detailed, objective caption."
                        user_msg = f"Provide a technical description of this image in approximately {target} words. Use precise terminology. Output only the caption."
                        temp = 0.4            # Medium temp
                    
                    else: # human-friendly
                        system_msg = "You are a friendly storyteller. Generate an engaging, human-friendly caption. Do NOT use emojis or hashtags."
                        user_msg = f"Create a friendly, engaging caption for this image in approximately {target} words. Do NOT use emojis or hashtags. Output only the caption."
                        temp = 0.7            # High temp for creativity

                    caption = run_generation(system_msg, user_msg, max_tokens=250, temperature=temp) # Generate
                    word_count = len(caption.split()) # Count generated words

                    # === PASS 2: Strict Self-Correction ===
                    # If the word count is outside the buffer, prompt the model to fix it
                    if word_count > max_words or word_count < min_words:
                        print(f"⚠️ Pass 1: {caption_type} generated {word_count} words (Target: {target}). Correcting...")
                        
                        if word_count > max_words:
                            instruction = f"Your caption was too long ({word_count} words). You must rewrite it to be strictly {max_words} words or fewer."
                        else:
                            instruction = f"Your caption was too short ({word_count} words). You must rewrite it to be approximately {target} words, adding more descriptive detail."

                        correction_system = "You are an expert editor with absolute control over word count. Follow the length constraint perfectly. Do NOT use emojis or hashtags."
                        correction_user = f"""Here is a caption: "{caption}"
{instruction}
Output only the revised caption. Do not explain your reasoning."""

                        revised_caption = run_generation(correction_system, correction_user, max_tokens=250, temperature=0.3) # Generate correction
                        revised_word_count = len(revised_caption.split()) # Count corrected words
                        
                        # Only accept the revision if it's closer to the target
                        if abs(revised_word_count - target) < abs(word_count - target):
                            caption = revised_caption # Accept revision
                            word_count = revised_word_count # Update count
                            print(f"✅ Pass 2 improved to {word_count} words.")

                    # === PASS 3: Final Polish ===
                    if word_count > max_words or word_count < min_words:
                        print(f"⚠️ Pass 3: Final adjustment needed for {caption_type} ({word_count} words)...")
                        if word_count > max_words:
                            final_system = "You are a ruthless editor. Cut the text down to the absolute minimum."
                            final_user = f"Rewrite this caption to be exactly {target} words or less. Be very brief: \"{caption}\""
                        else:
                            final_system = "You are a descriptive writer. Add more vivid details."
                            final_user = f"Rewrite this caption to be closer to {target} words. Add adjectives and adverbs: \"{caption}\""
                            
                        polished_caption = run_generation(final_system, final_user, max_tokens=250, temperature=0.4) # Generate polish
                        polished_word_count = len(polished_caption.split()) # Count polished words
                        
                        if abs(polished_word_count - target) < abs(word_count - target):
                            caption = polished_caption # Accept polish
                            word_count = polished_word_count # Update count
                            print(f"✅ Pass 3 improved to {word_count} words.")

                    # -------------------- TEXT CLEANUP & REGEX --------------------
                    # Removes hashtags and non-ASCII characters (emojis)
                    caption = re.sub(r'#\w+', '', caption) # Remove hashtags
                    caption = ''.join(c for c in caption if c.isascii()) # Remove emojis
                    caption = ' '.join(caption.split())    # Normalize spaces
                    word_count = len(caption.split())      # Recalculate word count

                    # Hard truncation if the model completely ignores the limit
                    if word_count > max_words:
                        words = caption.split()            # Split into words
                        trimmed_words = words[:max_words]  # Take only max allowed words
                        trimmed_text = ' '.join(trimmed_words) # Rejoin
                        
                        # Cut at the last punctuation mark for a clean ending
                        last_punct = max(trimmed_text.rfind('.'), trimmed_text.rfind('!'), trimmed_text.rfind('?'))
                        
                        if last_punct > 0:
                            caption = trimmed_text[:last_punct+1] # Keep up to punctuation
                        else:
                            caption = trimmed_text + '.'      # Add period if none found
                            
                        word_count = len(caption.split())  # Final count
                        print(f"🔨 Hard truncated {caption_type} to {word_count} words.")

                    # Remove dangling conjunctions (e.g., "and." or "or.")
                    caption = re.sub(r'\s+(and|or|but|with|in|on|at|to|by|of)\.?$', '.', caption, flags=re.IGNORECASE) # Regex cleanup
                    caption = re.sub(r'\s+\.', '.', caption) # Clean up spaces before period
                    word_count = len(caption.split())        # Final count
                    
                    # Store finalized result
                    results[caption_type] = {
                        'caption': caption,                  # Final text
                        'word_count': word_count,            # Final word count
                        'word_limit': target                 # Target word limit
                    }
                    
                    # Clear VRAM after each generation
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()             # Empty cache

                return {"success": True, "captions": results} # Return success JSON

            except Exception as e:                    # Catch errors
                import traceback                      # Import traceback
                traceback.print_exc()                 # Log error
                return {"success": False, "error": str(e)} # Return error JSON

        return api                                # Return FastAPI app
