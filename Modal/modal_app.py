import modal
import os
import re
from fastapi import FastAPI
from pydantic import BaseModel

app = modal.App("image-caption-studio")

model_cache = modal.Volume.from_name("hf-hub-cache", create_if_missing=True)
CACHE_DIR = "/cache"

image = (
    modal.Image.from_registry(
        "qwenllm/qwenvl:2.5-cu121", 
        add_python="3.11"
    )
    .pip_install(
        "fastapi[standard]",
        "transformers==4.53.3",
        "accelerate==0.27.2",
        "bitsandbytes>=0.46.1,<0.47.0",
        "qwen-vl-utils==0.0.8",
        "pillow",
        "torch==2.4.0",
        "torchvision==0.19.0",
        extra_options="--extra-index-url https://download.pytorch.org/whl/cu121"
    )
    .env({
        "HF_HUB_CACHE": CACHE_DIR,
        "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"
    })
)

class CaptionRequest(BaseModel):
    image: str
    styles: list
    word_limits: dict

@app.cls(
    image=image, 
    gpu="A10G", 
    timeout=600, 
    scaledown_window=600,
    volumes={CACHE_DIR: model_cache}
)
class CaptionModel:
    
    @modal.enter()
    def load_model(self):
        import torch
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
        
        print("🚀 Loading Qwen2.5-VL-7B-Instruct...")
        model_id = "Qwen/Qwen2.5-VL-7B-Instruct"
        
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
        
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_id,
            quantization_config=quantization_config,
            device_map="auto",
            trust_remote_code=True
        )
        self.processor = AutoProcessor.from_pretrained(
            model_id, 
            use_fast=False, 
            trust_remote_code=True,
            max_pixels=2048 * 28 * 28  # Backend Safety Net for OOM
        )
        print("✅ Model loaded successfully!")

    @modal.asgi_app()
    def web(self):
        import torch
        import base64
        from io import BytesIO
        from PIL import Image
        from collections import OrderedDict

        api = FastAPI()

        @api.get("/health")
        def health():
            return {"status": "healthy"}

        @api.post("/generate-captions")
        async def generate(req: CaptionRequest):
            try:
                image_data = base64.b64decode(req.image)
                pil_image = Image.open(BytesIO(image_data)).convert("RGB")

                caption_types = ['short', 'technical', 'human-friendly'] if 'all' in req.styles else req.styles
                results = OrderedDict()

                def run_generation(system_msg, user_msg, max_tokens, temperature):
                    messages = [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": [
                            {"type": "image", "image": pil_image},
                            {"type": "text", "text": user_msg}
                        ]}
                    ]
                    text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                    image_inputs = self.processor(text=text, images=pil_image, return_tensors="pt")
                    image_inputs = {k: v.to(self.model.device) for k, v in image_inputs.items()}

                    with torch.no_grad():
                        generated_ids = self.model.generate(
                            **image_inputs,
                            max_new_tokens=max_tokens,
                            do_sample=True,
                            temperature=temperature,
                            top_p=0.9,
                            repetition_penalty=1.1
                        )

                    generated_ids_trimmed = [
                        out_ids[len(in_ids):] for in_ids, out_ids in zip(image_inputs["input_ids"], generated_ids)
                    ]
                    caption = self.processor.batch_decode(
                        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=True
                    )[0].strip()
                    return caption.strip('"').strip("'").strip()

                for caption_type in ['short', 'technical', 'human-friendly']:
                    if caption_type not in caption_types:
                        continue
                    
                    target = req.word_limits.get(caption_type, 25)
                    min_words = max(5, target - 3)
                    max_words = target + 3

                    # === PASS 1: Initial Generation with Countdown Prompt ===
                    if caption_type == 'short':
                        system_msg = "You are an expert image captioning assistant. Your task is to write a concise caption."
                        user_msg = f"Describe this image in exactly {target} words. Start your sentence and count down from {target} words. Output only the caption."
                        temp = 0.3
                    
                    elif caption_type == 'technical':
                        system_msg = "You are a technical image analysis expert. Generate a detailed, objective caption."
                        user_msg = f"Provide a technical description of this image in approximately {target} words. Use precise terminology. Output only the caption."
                        temp = 0.4
                    
                    else: # human-friendly
                        system_msg = "You are a friendly storyteller. Generate an engaging, human-friendly caption. Do NOT use emojis or hashtags."
                        user_msg = f"Create a friendly, engaging caption for this image in approximately {target} words. Do NOT use emojis or hashtags. Output only the caption."
                        temp = 0.7

                    caption = run_generation(system_msg, user_msg, max_tokens=250, temperature=temp)
                    word_count = len(caption.split())

                    # === PASS 2: Strict Self-Correction Loop ===
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

                        revised_caption = run_generation(correction_system, correction_user, max_tokens=250, temperature=0.3)
                        revised_word_count = len(revised_caption.split())
                        
                        if abs(revised_word_count - target) < abs(word_count - target):
                            caption = revised_caption
                            word_count = revised_word_count
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
                            
                        polished_caption = run_generation(final_system, final_user, max_tokens=250, temperature=0.4)
                        polished_word_count = len(polished_caption.split())
                        
                        if abs(polished_word_count - target) < abs(word_count - target):
                            caption = polished_caption
                            word_count = polished_word_count
                            print(f"✅ Pass 3 improved to {word_count} words.")

                    # === UPDATE 3: Programmatic Cleanup for Emojis and Hashtags ===
                    caption = re.sub(r'#\w+', '', caption)
                    caption = ''.join(c for c in caption if c.isascii())
                    caption = ' '.join(caption.split())
                    word_count = len(caption.split())

                    # === FINAL GRACEFUL TRUNCATION (Hard Limit Safety Net) ===
                    if word_count > max_words:
                        words = caption.split()
                        trimmed_words = words[:max_words]
                        trimmed_text = ' '.join(trimmed_words)
                        
                        last_punct = max(trimmed_text.rfind('.'), trimmed_text.rfind('!'), trimmed_text.rfind('?'))
                        
                        if last_punct > 0:
                            caption = trimmed_text[:last_punct+1]
                        else:
                            caption = trimmed_text + '.'
                            
                        word_count = len(caption.split())
                        print(f"🔨 Hard truncated {caption_type} to {word_count} words.")
                    
                    results[caption_type] = {
                        'caption': caption,
                        'word_count': word_count,
                        'word_limit': target
                    }
                    
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()

                return {"success": True, "captions": results}

            except Exception as e:
                import traceback
                traceback.print_exc()
                return {"success": False, "error": str(e)}

        return api
