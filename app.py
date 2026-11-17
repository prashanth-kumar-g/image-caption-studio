import streamlit as st
from PIL import Image
import base64
from io import BytesIO
import requests

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Image Caption Studio",
    page_icon="🖼️",
    layout="wide"
)

# ---------------- CONFIGURATION ----------------
MODAL_API_URL = "https://prashanth-kumar-g--image-caption-studio-captionmodel-web.us-east.modal.run" 

# ---------------- CSS (EXACT ORIGINAL - UNCHANGED) ----------------
st.markdown("""
<style>
body { background:#0e1117; }
.header { text-align:center; margin:30px 0 40px; }
.header h1 { font-size:42px; font-weight:800; margin:0; }
.header p { color:#aaa; margin-top:8px; }
.image-box-container {
  width: 100%; height: 450px; border: 2px dashed #30363d; border-radius: 16px;
  margin-bottom: 12px; overflow: hidden; display: flex; align-items: center;
  justify-content: center; background-color: #161b22;
}
.image-placeholder { color: #888; font-size: 18px; }
.image-box-container img { width: 100% !important; height: 100% !important; object-fit: fill !important; }
.generate-button-container { margin-top: 30px; width: 100%; }
.generate-button-container button {
  background: linear-gradient(90deg,#6366f1,#06b6d4) !important; color:#fff !important;
  font-size:18px !important; font-weight:700 !important; padding:12px 36px !important;
  border-radius:16px !important; border:none !important; cursor:pointer !important; width: 100% !important;
}
.output-section { margin-top: 40px; width: 100%; }
.output-title {
  text-align: center; color: #fff; font-size: 28px; font-weight: 700;
  margin-bottom: 30px; padding-bottom: 15px; border-bottom: 2px solid #30363d;
}
.output-card {
  background: linear-gradient(145deg, #161b22, #1c2129); padding: 28px;
  border-radius: 18px; margin-bottom: 25px; border-left: 5px solid #6366f1;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3); transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.output-card:hover { transform: translateY(-5px); box-shadow: 0 12px 25px rgba(0, 0, 0, 0.4); }
.card-header { display: flex; align-items: center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #30363d; }
.card-icon { font-size: 24px; margin-right: 15px; }
.card-title { font-size: 22px; font-weight: 700; color: #fff; margin: 0; }
.card-content { font-size: 16px; line-height: 1.6; color: #c9d1d9; padding: 10px 0; }
.card-short { border-left-color: #06b6d4; } .card-short .card-icon { color: #06b6d4; }
.card-technical { border-left-color: #10b981; } .card-technical .card-icon { color: #10b981; }
.card-friendly { border-left-color: #f59e0b; } .card-friendly .card-icon { color: #f59e0b; }
.empty-output {
  text-align: center; color: #666; font-size: 16px; padding: 40px;
  background: #161b22; border-radius: 16px; border: 2px dashed #30363d;
}
.footer {
  text-align:center; color:#777; font-size:14px; margin-top:80px;
  padding: 30px 30px 30px 30px; border-top:1px solid #30363d;
}
.block-container { padding-top: 0rem !important; padding-bottom: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("""
<div class="header">
  <h1>🖼️ Image Caption Studio</h1>
  <p>Upload an image and generate Short, Technical, or Human-friendly captions using Generative AI.</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.uploaded_image = None
    st.session_state.api_image = None # Added to store the backend-specific image
    st.session_state.image_html = None
    st.session_state.captions_generated = False
    st.session_state.generated_captions = {}
    st.session_state.initialized = True

# ---------------- API CALL ----------------
def generate_captions_from_api(image: Image.Image, styles: list, word_limits: dict) -> dict:
    try:
        buffered = BytesIO()
        
        # Check original PNG size. If > 2MB, compress to JPEG for faster backend processing.
        image.save(buffered, format="PNG")
        if buffered.tell() > 2 * 1024 * 1024:
            buffered = BytesIO()
            image.save(buffered, format="JPEG", quality=85) # Compress to reduce file size
            
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        payload = {
            "image": img_str,
            "styles": styles,
            "word_limits": word_limits
        }
        
        response = requests.post(f"{MODAL_API_URL}/generate-captions", json=payload, timeout=300)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {'success': False, 'error': f"API error {response.status_code}: {response.text[:100]}"}
            
    except requests.exceptions.Timeout:
        return {'success': False, 'error': "Timeout - The model might be starting up. Please try again in 60 seconds."}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown("### 📡 Backend Status")
    st.success("🟢 Connected to Modal Serverless GPU (Free Tier)")
    st.markdown("---")
    st.markdown("**Model:** Qwen2.5-VL-7B-Instruct")
    st.markdown("**Platform:** Modal")
    st.markdown("**Hardware:** A10G GPU")
    st.info("The first request may take up to 30-90 seconds to cold-start. Subsequent requests will take 5-15 seconds to respond.")
    st.markdown("---")
    st.markdown("**Note:**")
    st.error("The server automatically goes to sleep after 10 minutes of inactivity to save GPU credits.")

# ---------------- LAYOUT ----------------
left, right = st.columns(2, gap="large")

# ---------------- LEFT: IMAGE ----------------
with left:
    st.markdown("<h3>Upload Image</h3>", unsafe_allow_html=True)
    if st.session_state.image_html:
        st.markdown(st.session_state.image_html, unsafe_allow_html=True)
    else:
        st.markdown('<div class="image-box-container"><div class="image-placeholder">📷 No image selected</div></div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Choose an image file", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    
    if uploaded_file is not None:
        # 20MB Hard Limit Check
        if uploaded_file.size > 20 * 1024 * 1024:
            st.error("❌ File is too large. Maximum size is 20MB.")
            st.session_state.api_image = None
            st.session_state.image_html = None
        else:
            if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != uploaded_file.name:
                try:
                    image = Image.open(uploaded_file)
                    st.session_state.uploaded_image = image
                    
                    # 1. UI DISPLAY (EXACT SAME AS BEFORE - UNTOUCHED)
                    resized_image = image.resize((600, 450), Image.Resampling.LANCZOS)
                    buffered = BytesIO()
                    resized_image.save(buffered, format="PNG", optimize=True, quality=95)
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    image_html = f'<div class="image-box-container"><img src="data:image/png;base64,{img_str}" alt="Uploaded Image" /></div>'
                    st.session_state.image_html = image_html
                    
                    # 2. BACKEND PREPARATION (CONDITIONAL RESIZING)
                    api_image = image.copy()
                    width, height = api_image.size
                    # Scale down proportionally if dimension > 2048
                    if width > 2048 or height > 2048:
                        ratio = 2048 / max(width, height)
                        new_size = (int(width * ratio), int(height * ratio))
                        api_image = api_image.resize(new_size, Image.Resampling.LANCZOS)
                    
                    st.session_state.api_image = api_image
                    st.session_state.last_uploaded_file = uploaded_file.name
                    st.session_state.captions_generated = False
                    st.session_state.generated_captions = {}
                    st.rerun()
                except Exception as e:
                    st.error(f"Error loading image: {e}")

# ---------------- RIGHT: OPTIONS ----------------
with right:
    st.markdown("<h3>Caption Style</h3>", unsafe_allow_html=True)
    style = st.radio(" ", ["All", "Short", "Technical", "Human-friendly"], label_visibility="collapsed")
    
    with st.expander("Advanced Options", expanded=True):
        short_words = st.slider("Short caption words", 5, 30, 15)
        tech_words = st.slider("Technical caption words", 15, 60, 35)
        human_words = st.slider("Human-friendly caption words", 10, 50, 25)
    
    st.markdown('<div class="generate-button-container">', unsafe_allow_html=True)
    generate_clicked = st.button("Generate Captions", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- GENERATE LOGIC ----------------
if generate_clicked:
    if not st.session_state.get("api_image"):
        st.warning("⚠️ Please upload an image first!")
    else:
        styles = ["all"] if style == "All" else [{"Short": "short", "Technical": "technical", "Human-friendly": "human-friendly"}[style]]
        word_limits = {"short": short_words, "technical": tech_words, "human-friendly": human_words}
        
        with st.spinner("🔄 Generating captions on Modal GPU... Please wait."):
            result = generate_captions_from_api(st.session_state.api_image, styles, word_limits)
            if result.get('success'):
                st.session_state.captions_generated = True
                st.session_state.generated_captions = result.get('captions', {})
                st.rerun()
            else:
                st.error(f"❌ Error: {result.get('error', 'Unknown error')}")

# ---------------- OUTPUT SECTION ----------------
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<div class="output-section">', unsafe_allow_html=True)

if st.session_state.get("captions_generated", False) and st.session_state.generated_captions:
    caption_display = {
        "short": {"icon": "⚡", "title": "Short Caption", "class": "card-short"},
        "technical": {"icon": "🔬", "title": "Technical Caption", "class": "card-technical"},
        "human-friendly": {"icon": "😊", "title": "Human-friendly Caption", "class": "card-friendly"}
    }
    st.markdown('<div class="output-title">✨ Generated Captions</div>', unsafe_allow_html=True)
    
    for caption_type in ["short", "technical", "human-friendly"]:
        if caption_type in st.session_state.generated_captions:
            data = st.session_state.generated_captions[caption_type]
            info = caption_display[caption_type]
            st.markdown(f"""
            <div class="output-card {info['class']}">
                <div class="card-header">
                    <span class="card-icon">{info['icon']}</span>
                    <h3 class="card-title">{info['title']}</h3>
                </div>
                <div class="card-content">{data.get('caption', '')}</div>
            </div>
            """, unsafe_allow_html=True)
            
    col1, col2, col3 = st.columns([2, 1.5, 2])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Clear", type="secondary", use_container_width=True):
            st.session_state.captions_generated = False
            st.session_state.generated_captions = {}
            st.session_state.uploaded_image = None
            st.session_state.api_image = None
            st.session_state.image_html = None
            if 'last_uploaded_file' in st.session_state: del st.session_state['last_uploaded_file']
            st.rerun()

elif st.session_state.get("api_image"):
    st.markdown('<div class="empty-output">📷 Upload an image and click "Generate Captions" to see results here.</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="empty-output">📷 Upload an image and click "Generate Captions" to see results here.</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ---------------- FOOTER ----------------
st.markdown("""
<div class="footer">
    © 2025 Image Caption Studio • Powered by Qwen2.5-VL-7B-Instruct on Modal
</div>
""", unsafe_allow_html=True)
