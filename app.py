# ============================
# Image Caption Studio - Streamlit App
# ============================

import streamlit as st
import torch
from PIL import Image
import transformers
from transformers import BitsAndBytesConfig
import time
import warnings
import random
from pathlib import Path
import base64
import io
warnings.filterwarnings('ignore')

# ============================
# PAGE CONFIGURATION
# ============================

st.set_page_config(
    page_title="Image Caption Studio",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================
# CUSTOM CSS FOR BEAUTIFUL UI
# ============================

def load_css():
    st.markdown("""
    <style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Main container */
    .main-container {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 24px;
        padding: 40px;
        margin: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.15);
        backdrop-filter: blur(10px);
    }
    
    /* Title styling */
    .title-container {
        text-align: center;
        margin-bottom: 40px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 20px;
        border-radius: 20px;
    }
    
    .main-title {
        font-size: 3.5rem !important;
        font-weight: 800 !important;
        margin-bottom: 10px !important;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .subtitle {
        font-size: 1.2rem !important;
        color: #666 !important;
        max-width: 800px;
        margin: 0 auto;
        line-height: 1.6;
    }
    
    /* Logo container */
    .logo-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 20px;
        margin-bottom: 20px;
    }
    
    .logo-icon {
        font-size: 4rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Image display */
    .image-container {
        border-radius: 20px;
        overflow: hidden;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        margin: 30px auto;
        max-width: 600px;
        border: 3px solid #667eea;
        position: relative;
    }
    
    .image-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(45deg, transparent, rgba(102, 126, 234, 0.1));
        z-index: 1;
    }
    
    /* Cards */
    .card {
        background: white;
        border-radius: 20px;
        padding: 25px;
        margin: 15px 0;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        border: 2px solid transparent;
        transition: all 0.3s ease;
    }
    
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(0,0,0,0.15);
    }
    
    .short-card {
        border-color: #4CAF50;
        background: linear-gradient(135deg, #f8fff8 0%, #e8f5e9 100%);
    }
    
    .tech-card {
        border-color: #2196F3;
        background: linear-gradient(135deg, #f8fbff 0%, #e3f2fd 100%);
    }
    
    .human-card {
        border-color: #FF9800;
        background: linear-gradient(135deg, #fff8f8 0%, #fff3e0 100%);
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.9rem;
        margin-bottom: 15px;
    }
    
    .short-badge {
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
        color: white;
    }
    
    .tech-badge {
        background: linear-gradient(135deg, #2196F3 0%, #0D47A1 100%);
        color: white;
    }
    
    .human-badge {
        background: linear-gradient(135deg, #FF9800 0%, #EF6C00 100%);
        color: white;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 14px 28px;
        border-radius: 50px;
        font-weight: 600;
        font-size: 1.1rem;
        transition: all 0.3s ease;
        width: 100%;
        margin-top: 20px;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    .upload-btn {
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%) !important;
    }
    
    /* Progress bar */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Success message */
    .success-msg {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: 2px solid #4CAF50;
        border-radius: 15px;
        padding: 20px;
        margin: 20px 0;
        text-align: center;
        font-weight: 600;
        color: #155724;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        margin-top: 50px;
        color: #666;
        font-size: 0.9rem;
        padding: 20px;
        border-top: 2px solid #eee;
    }
    
    /* Radio buttons */
    .stRadio > div {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #f8fbff 0%, #e3f2fd 100%) !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
    
    /* Sliders */
    .stSlider {
        padding: 10px 0;
    }
    
    /* Word counter */
    .word-counter {
        font-size: 0.9rem;
        color: #666;
        font-style: italic;
        margin-top: 5px;
    }
    
    /* Loading animation */
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    .loading {
        animation: pulse 1.5s infinite;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .main-title {
            font-size: 2.5rem !important;
        }
        .main-container {
            padding: 20px;
            margin: 10px;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# ============================
# MODEL LOADING (CACHED)
# ============================

@st.cache_resource(show_spinner=False)
def load_model():
    """Load the Qwen2.5-VL model (cached for performance)"""
    
    with st.spinner("🚀 Loading AI Model..."):
        try:
            # Check GPU availability
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Model ID
            model_id = "Qwen/Qwen2.5-VL-7B-Instruct"
            
            # Try with quantization for faster loading
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
            
            # Load model and processor
            model = transformers.Qwen2_5_VLForConditionalGeneration.from_pretrained(
                model_id,
                quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.float16
            )
            
            processor = transformers.Qwen2_5_VLProcessor.from_pretrained(model_id)
            
            st.success("✅ AI Model Loaded Successfully!")
            return model, processor, device
            
        except Exception as e:
            st.error(f"❌ Error loading model: {str(e)}")
            # Fallback to CPU if GPU fails
            try:
                model = transformers.Qwen2_5_VLForConditionalGeneration.from_pretrained(
                    model_id,
                    device_map="cpu",
                    torch_dtype=torch.float32
                )
                processor = transformers.Qwen2_5_VLProcessor.from_pretrained(model_id)
                return model, processor, "cpu"
            except:
                st.error("Failed to load model. Please check your internet connection.")
                return None, None, None

# ============================
# PROMPT TEMPLATES
# ============================

class CaptionPrompts:
    """Class containing prompt templates for different caption styles"""
    
    @staticmethod
    def get_short_caption_prompt(word_limit=15):
        """Generate short caption"""
        return f"""<|im_start|>system
You are an expert image captioning assistant. Generate a VERY SHORT caption describing the image.
The caption should be concise, under {word_limit} words, and capture the main subject.
Focus only on the most important elements.<|im_end|>
<|im_start|>user
<image>
Describe this image in a single, very short sentence (under {word_limit} words).<|im_end|>
<|im_start|>assistant
"""
    
    @staticmethod
    def get_technical_caption_prompt(word_limit=35):
        """Generate technical caption"""
        return f"""<|im_start|>system
You are a technical image analysis expert. Generate a detailed technical caption.
Focus on objective observations, visual characteristics, composition, and technical aspects.
Use precise terminology. Keep it under {word_limit} words.<|im_end|>
<|im_start|>user
<image>
Provide a technical description of this image with precise observations (under {word_limit} words).<|im_end|>
<|im_start|>assistant
"""
    
    @staticmethod
    def get_human_friendly_caption_prompt(word_limit=25):
        """Generate human-friendly caption"""
        return f"""<|im_start|>system
You are a friendly storyteller. Generate an engaging, human-friendly caption.
Make it descriptive, interesting, and easy to understand for general audiences.
Use vivid language and keep it under {word_limit} words.<|im_end|>
<|im_start|>user
<image>
Create a friendly, engaging caption for this image that tells a story (under {word_limit} words).<|im_end|>
<|im_start|>assistant
"""

# ============================
# CAPTION GENERATION FUNCTION
# ============================

def generate_caption(model, processor, device, image, prompt: str, max_new_tokens: int = 100) -> str:
    """Generate caption for an image using the given prompt"""
    try:
        # Prepare inputs
        messages = [
            {"role": "user", "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt.split("<|im_start|>user\n")[-1].split("<|im_end|>")[0]}
            ]}
        ]
        
        text = processor.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )
        
        # Prepare image inputs
        image_inputs = processor(text=text, images=image, return_tensors="pt")
        image_inputs = {k: v.to(device) for k, v in image_inputs.items()}
        
        # Generate caption
        with torch.no_grad():
            generated_ids = model.generate(
                **image_inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
            )
        
        # Decode the generated text
        generated_ids_trimmed = [
            out_ids[len(in_ids):] 
            for in_ids, out_ids in zip(image_inputs["input_ids"], generated_ids)
        ]
        
        caption = processor.batch_decode(
            generated_ids_trimmed, 
            skip_special_tokens=True, 
            clean_up_tokenization_spaces=True
        )[0]
        
        return caption.strip()
    
    except Exception as e:
        return f"Error generating caption: {str(e)}"

# ============================
# MAIN APP FUNCTION
# ============================

def main():
    # Load custom CSS
    load_css()
    
    # Main container
    with st.container():
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        
        # Header with logo and title
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="logo-container">', unsafe_allow_html=True)
            st.markdown('<span class="logo-icon">🖼️✨</span>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<h1 class="main-title">Image Caption Studio</h1>', unsafe_allow_html=True)
            st.markdown('<p class="subtitle">Transform your images into beautiful captions using advanced AI. Upload any image and get short, technical, and human-friendly captions instantly!</p>', unsafe_allow_html=True)
        
        # Load model (cached)
        model, processor, device = load_model()
        
        if model is None:
            st.error("⚠️ Model failed to load. Please refresh the page or check your connection.")
            return
        
        # ============================
        # SIDEBAR FOR SETTINGS
        # ============================
        
        with st.sidebar:
            st.markdown("## ⚙️ Settings")
            
            # Caption type selection
            caption_type = st.radio(
                "**Select Caption Style:**",
                ["🎯 All Three Styles", "📝 Short Only", "🔬 Technical Only", "😊 Human-Friendly Only"],
                help="Choose which caption styles to generate"
            )
            
            # Advanced options expander
            with st.expander("**⚙️ Advanced Options**", expanded=False):
                st.markdown("### Word Limits")
                
                short_limit = st.slider(
                    "**Short Caption Limit:**",
                    min_value=5,
                    max_value=25,
                    value=15,
                    help="Maximum words for short captions"
                )
                
                tech_limit = st.slider(
                    "**Technical Caption Limit:**",
                    min_value=15,
                    max_value=50,
                    value=35,
                    help="Maximum words for technical captions"
                )
                
                human_limit = st.slider(
                    "**Human-Friendly Limit:**",
                    min_value=15,
                    max_value=50,
                    value=25,
                    help="Maximum words for human-friendly captions"
                )
            
            # Performance info
            st.markdown("---")
            st.markdown("### 📊 System Info")
            st.info(f"**Device:** {device.upper()}\n\n**Model:** Qwen2.5-VL-7B\n\n**Status:** Ready ✅")
        
        # ============================
        # MAIN CONTENT AREA
        # ============================
        
        # Create two columns for layout
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.markdown("### 📤 Upload Your Image")
            
            # File uploader
            uploaded_file = st.file_uploader(
                "Choose an image...",
                type=['jpg', 'jpeg', 'png', 'bmp', 'tiff'],
                help="Supported formats: JPG, JPEG, PNG, BMP, TIFF"
            )
            
            # Display uploaded image
            if uploaded_file is not None:
                try:
                    image = Image.open(uploaded_file)
                    
                    # Resize for display
                    max_size = (500, 500)
                    image.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    st.markdown('<div class="image-container">', unsafe_allow_html=True)
                    st.image(image, use_column_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Image info
                    st.success(f"✅ **{uploaded_file.name}** uploaded successfully!")
                    st.caption(f"**Size:** {image.size[0]}x{image.size[1]} pixels | **Format:** {image.format}")
                    
                except Exception as e:
                    st.error(f"Error loading image: {str(e)}")
                    image = None
            else:
                # Display placeholder
                st.markdown('<div class="image-container">', unsafe_allow_html=True)
                st.image("https://via.placeholder.com/500x300/667eea/ffffff?text=Upload+an+Image", 
                        use_column_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                st.info("👆 Upload an image to get started")
                image = None
        
        with col_right:
            st.markdown("### 🎨 Caption Settings")
            
            # Display current settings
            if caption_type == "🎯 All Three Styles":
                st.markdown("**Selected:** All caption styles")
                cols = st.columns(3)
                with cols[0]:
                    st.markdown('<div class="badge short-badge">Short</div>', unsafe_allow_html=True)
                with cols[1]:
                    st.markdown('<div class="badge tech-badge">Technical</div>', unsafe_allow_html=True)
                with cols[2]:
                    st.markdown('<div class="badge human-badge">Human-Friendly</div>', unsafe_allow_html=True)
            else:
                st.markdown(f"**Selected:** {caption_type.split(' ')[1]}")
            
            # Generate button
            generate_btn = st.button(
                "🚀 Generate Captions",
                type="primary",
                disabled=uploaded_file is None,
                use_container_width=True
            )
        
        # ============================
        # CAPTION GENERATION
        # ============================
        
        if generate_btn and uploaded_file is not None and image is not None:
            try:
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Generate captions based on selection
                captions = {}
                
                if caption_type in ["🎯 All Three Styles", "📝 Short Only"]:
                    status_text.text("🔍 Generating short caption...")
                    short_prompt = CaptionPrompts.get_short_caption_prompt(short_limit)
                    short_caption = generate_caption(model, processor, device, image, short_prompt, 50)
                    
                    # Enforce word limit
                    short_words = short_caption.split()
                    if len(short_words) > short_limit:
                        short_caption = ' '.join(short_words[:short_limit]) + "..."
                    captions['short'] = short_caption
                    progress_bar.progress(33)
                
                if caption_type in ["🎯 All Three Styles", "🔬 Technical Only"]:
                    status_text.text("🔬 Generating technical caption...")
                    tech_prompt = CaptionPrompts.get_technical_caption_prompt(tech_limit)
                    tech_caption = generate_caption(model, processor, device, image, tech_prompt, 100)
                    
                    # Enforce word limit
                    tech_words = tech_caption.split()
                    if len(tech_words) > tech_limit:
                        tech_caption = ' '.join(tech_words[:tech_limit]) + "..."
                    captions['technical'] = tech_caption
                    progress_bar.progress(66 if caption_type == "🔬 Technical Only" else 66)
                
                if caption_type in ["🎯 All Three Styles", "😊 Human-Friendly Only"]:
                    status_text.text("😊 Generating human-friendly caption...")
                    human_prompt = CaptionPrompts.get_human_friendly_caption_prompt(human_limit)
                    human_caption = generate_caption(model, processor, device, image, human_prompt, 100)
                    
                    # Enforce word limit
                    human_words = human_caption.split()
                    if len(human_words) > human_limit:
                        human_caption = ' '.join(human_words[:human_limit]) + "..."
                    captions['human'] = human_caption
                    progress_bar.progress(100)
                
                status_text.text("✅ Captions generated successfully!")
                time.sleep(0.5)
                progress_bar.empty()
                status_text.empty()
                
                # ============================
                # DISPLAY RESULTS
                # ============================
                
                st.markdown("---")
                st.markdown("## 📋 Generated Captions")
                
                # Display appropriate cards
                if 'short' in captions:
                    st.markdown('<div class="card short-card loading">', unsafe_allow_html=True)
                    st.markdown('<div class="badge short-badge">Short Caption</div>', unsafe_allow_html=True)
                    st.markdown(f'**{captions["short"]}**')
                    st.markdown(f'<div class="word-counter">📊 Words: {len(captions["short"].split())} / {short_limit}</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                if 'technical' in captions:
                    st.markdown('<div class="card tech-card loading">', unsafe_allow_html=True)
                    st.markdown('<div class="badge tech-badge">Technical Caption</div>', unsafe_allow_html=True)
                    st.markdown(f'**{captions["technical"]}**')
                    st.markdown(f'<div class="word-counter">📊 Words: {len(captions["technical"].split())} / {tech_limit}</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                if 'human' in captions:
                    st.markdown('<div class="card human-card loading">', unsafe_allow_html=True)
                    st.markdown('<div class="badge human-badge">Human-Friendly Caption</div>', unsafe_allow_html=True)
                    st.markdown(f'**{captions["human"]}**')
                    st.markdown(f'<div class="word-counter">📊 Words: {len(captions["human"].split())} / {human_limit}</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Copy to clipboard button
                if caption_type == "🎯 All Three Styles":
                    all_captions = f"Short: {captions.get('short', '')}\n\nTechnical: {captions.get('technical', '')}\n\nHuman-Friendly: {captions.get('human', '')}"
                else:
                    all_captions = list(captions.values())[0]
                
                st.download_button(
                    label="💾 Download All Captions",
                    data=all_captions,
                    file_name="captions.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                
                # Success message
                st.markdown('<div class="success-msg">✨ Captions generated successfully! You can copy them or download as text.</div>', unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"❌ Error generating captions: {str(e)}")
        
        # ============================
        # FEATURES SECTION
        # ============================
        
        st.markdown("---")
        st.markdown("## ✨ Features")
        
        features_cols = st.columns(3)
        
        with features_cols[0]:
            st.markdown("""
            <div style="text-align: center; padding: 20px;">
                <h3>🎯 Multiple Styles</h3>
                <p>Short, technical, and human-friendly captions tailored to your needs</p>
            </div>
            """, unsafe_allow_html=True)
        
        with features_cols[1]:
            st.markdown("""
            <div style="text-align: center; padding: 20px;">
                <h3>⚡ Fast & Accurate</h3>
                <p>Powered by Qwen2.5-VL AI model for precise and quick results</p>
            </div>
            """, unsafe_allow_html=True)
        
        with features_cols[2]:
            st.markdown("""
            <div style="text-align: center; padding: 20px;">
                <h3>🎨 Customizable</h3>
                <p>Adjust word limits and choose specific caption styles</p>
            </div>
            """, unsafe_allow_html=True)
        
        # ============================
        # FOOTER
        # ============================
        
        st.markdown("---")
        st.markdown('<div class="footer">', unsafe_allow_html=True)
        st.markdown("""
        <p>🎓 <strong>Final Year Project</strong> | MCA Department</p>
        <p>🤖 Powered by Qwen2.5-VL AI Model | 🚀 Built with Streamlit</p>
        <p>📧 Contact: student@college.edu | 🔗 GitHub Repository Available</p>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close main container

# ============================
# RUN THE APP
# ============================

if __name__ == "__main__":
    main()
