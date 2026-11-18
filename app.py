# ===================== NAMESPACE IMPORTS =====================
# Imports required for UI rendering, image processing, and API communication

import streamlit as st                        # Core Streamlit library for UI
from PIL import Image                         # Image processing library
import base64                                 # For encoding images to base64
from io import BytesIO                        # For handling in-memory bytes
import requests                               # For making HTTP requests to the backend

# ===================== PAGE CONFIGURATION =====================
# Sets the browser tab title, icon, and layout width

st.set_page_config(
    page_title="Image Caption Studio",        # Browser tab title
    page_icon="🖼️",                           # Browser tab icon
    layout="wide"                            # Uses full screen width
)

# ===================== SECURE CONFIGURATION =====================
# Loads the Modal API URL from Streamlit secrets for security
# Falls back to a placeholder if running locally without secrets

try:
    MODAL_API_URL = st.secrets["MODAL_API_URL"]      # Retrieve secret from Streamlit
except (FileNotFoundError, KeyError):                # Catch missing secrets file or key
    MODAL_API_URL = "https://your-modal-url-here.modal.run"   # Placeholder fallback URL
    st.warning("⚠️ Developer Note: `MODAL_API_URL` secret is not configured. The backend will not respond.")

# ===================== CUSTOM CSS STYLING =====================
# Injects custom CSS to override default Streamlit styles and create a dark theme

st.markdown("""
<style>
/* ===================== GLOBAL STYLES ===================== */
/* Base background color for the entire page */
body { 
    background:#0e1117;                       /* Dark theme background color */
}

/* ===================== HEADER STYLING ===================== */
/* Centers the main title and subtitle with specific spacing */
.header { 
    text-align:center;                        /* Centers text horizontally */
    margin:30px 0 40px;                       /* Top and bottom margin spacing */
}

.header h1 { 
    font-size:42px;                           /* Large title font size */
    font-weight:800;                          /* Extra bold font weight */
    margin:0;                                 /* Removes default margins */
}

.header p { 
    color:#aaa;                               /* Light gray subtitle text */
    margin-top:8px;                           /* Small gap below title */
}

/* ===================== IMAGE UPLOAD CONTAINER ===================== */
/* Fixed dimensions for the image preview box */
.image-box-container {
  width: 100%;                                /* Takes full width of column */
  height: 450px;                              /* Fixed height for consistent layout */
  border: 2px dashed #30363d;                 /* Dashed border for drop-zone look */
  border-radius: 16px;                        /* Rounded corners */
  margin-bottom: 12px;                        /* Space below the box */
  overflow: hidden;                           /* Hides any overflow from images */
  display: flex;                              /* Flexbox for centering content */
  align-items: center;                        /* Centers vertically */
  justify-content: center;                    /* Centers horizontally */
  background-color: #161b22;                  /* Slightly lighter dark background */
}

/* Placeholder text styling when no image is selected */
.image-placeholder { 
    color: #888;                              /* Gray text */
    font-size: 18px;                          /* Readable font size */
}

/* THE SOLUTION: STRETCH TO FILL */
/* Ensures uploaded images completely fill the container without distortion */
.image-box-container img { 
    width: 100% !important;                   /* Forces image to full container width */
    height: 100% !important;                  /* Forces image to full container height */
    object-fit: fill !important;              /* Stretches image to fill dimensions */
}

/* ===================== GENERATE BUTTON STYLING ===================== */
/* Container for the button to add top margin */
.generate-button-container { 
    margin-top: 30px;                         /* Pushes button down from options */
    width: 100%;                              /* Full width container */
}

/* Gradient styling for the primary Generate button */
.generate-button-container button {
  background: linear-gradient(90deg,#6366f1,#06b6d4) !important; /* Purple to cyan gradient */
  color:#fff !important;                      /* White text */
  font-size:18px !important;                  /* Larger text */
  font-weight:700 !important;                 /* Bold text */
  padding:12px 36px !important;               /* Comfortable padding */
  border-radius:16px !important;              /* Rounded button edges */
  border:none !important;                     /* Removes default border */
  cursor:pointer !important;                  /* Pointer cursor on hover */
  width: 100% !important;                     /* Full width button */
}

/* ===================== OUTPUT SECTION LAYOUT ===================== */
/* Container for the generated captions */
.output-section { 
    margin-top: 40px;                         /* Space above output section */
    width: 100%;                              /* Full width */
}

/* Title styling above the generated captions */
.output-title {
  text-align: center;                         /* Center align the title */
  color: #fff;                                /* White text */
  font-size: 28px;                            /* Large title */
  font-weight: 700;                           /* Bold text */
  margin-bottom: 30px;                        /* Space below title */
  padding-bottom: 15px;                       /* Space inside bottom border */
  border-bottom: 2px solid #30363d;           /* Separator line */
}

/* ===================== CAPTION CARDS STYLING ===================== */
/* Base styling for each caption card */
.output-card {
  background: linear-gradient(145deg, #161b22, #1c2129); /* Subtle gradient background */
  padding: 28px;                              /* Internal spacing */
  border-radius: 18px;                        /* Rounded corners */
  margin-bottom: 25px;                        /* Space between cards */
  border-left: 5px solid #6366f1;             /* Colored left accent border */
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);  /* Drop shadow for depth */
  transition: transform 0.3s ease, box-shadow 0.3s ease;  /* Smooth animation */
}

/* Hover effect for interactivity */
.output-card:hover { 
    transform: translateY(-5px);                  /* Lifts card up slightly */
    box-shadow: 0 12px 25px rgba(0, 0, 0, 0.4);   /* Deeper shadow */
}

/* Header inside each card (Icon + Title) */
.card-header { 
    display: flex;                            /* Flex layout */
    align-items: center;                      /* Vertical center */
    margin-bottom: 20px;                      /* Space below header */
    padding-bottom: 15px;                     /* Space inside bottom border */
    border-bottom: 1px solid #30363d;         /* Separator line */
}

.card-icon { 
    font-size: 24px;                          /* Larger icon */
    margin-right: 15px;                       /* Space between icon and text */
}

.card-title { 
    font-size: 22px;                          /* Title size */
    font-weight: 700;                         /* Bold */
    color: #fff;                              /* White text */
    margin: 0;                                /* Removes default margin */
}

/* Actual generated text inside the card */
.card-content { 
    font-size: 16px;                          /* Readable body text */
    line-height: 1.6;                         /* Line spacing for readability */
    color: #c9d1d9;                           /* Light gray text */
    padding: 10px 0;                          /* Vertical padding */
}

/* Specific border colors for different caption types */
.card-short { border-left-color: #06b6d4; } 
.card-short .card-icon { color: #06b6d4; }       /* Cyan accent for short */
.card-technical { border-left-color: #10b981; } 
.card-technical .card-icon { color: #10b981; }   /* Green accent for technical */
.card-friendly { border-left-color: #f59e0b; } 
.card-friendly .card-icon { color: #f59e0b; }    /* Yellow accent for friendly */

/* ===================== EMPTY STATE STYLING ===================== */
/* Placeholder text when no captions are generated */
.empty-output {
  text-align: center;                         /* Centered text */
  color: #666;                                /* Dark gray text */
  font-size: 16px;                            /* Readable font */
  padding: 40px;                              /* Large internal spacing */
  background: #161b22;                        /* Dark background */
  border-radius: 16px;                        /* Rounded corners */
  border: 2px dashed #30363d;                 /* Dashed border */
}

/* ===================== FOOTER STYLING ===================== */
/* Styling for the copyright text at the bottom */
.footer {
  text-align:center;                          /* Centered text */
  color:#777;                                 /* Gray text */
  font-size:14px;                             /* Small font */
  margin-top:80px;                            /* Large gap above footer */
  padding: 30px 30px 30px 30px;               /* Uniform internal padding */
  border-top:1px solid #30363d;               /* Top separator line */
}

/* Adjusts Streamlit's default padding to maximize screen space */
.block-container { 
    padding-top: 0rem !important;             /* Removes top padding */
    padding-bottom: 1rem !important;          /* Reduces bottom padding */
}
</style>
""", unsafe_allow_html=True)

# ===================== HEADER RENDER =====================
# Injects the HTML for the main application header

st.markdown("""
<div class="header">
  <h1>🖼️ Image Caption Studio</h1>    <!-- Main app title -->
  <p>Upload an image and generate Short, Technical, or Human-friendly captions using Generative AI.</p>   <!-- Subtitle -->
</div>
""", unsafe_allow_html=True)

# ===================== SESSION STATE INITIALIZATION =====================
# Tracks variables across reruns to maintain UI state

if 'initialized' not in st.session_state:            # Check if first run
    st.session_state.uploaded_image = None           # Stores the original UI image
    st.session_state.api_image = None                # Stores the processed image for the backend
    st.session_state.image_html = None               # Stores HTML string for the image preview
    st.session_state.captions_generated = False      # Flag indicating if generation is complete
    st.session_state.generated_captions = {}         # Dictionary holding the API response
    st.session_state.initialized = True              # Flag ensuring initialization only happens once

# ===================== API COMMUNICATION MODULE =====================
# Handles image encoding and sending requests to the Modal backend

def generate_captions_from_api(image: Image.Image, styles: list, word_limits: dict) -> dict:
    try:
        buffered = BytesIO()                         # In-memory byte buffer
        
        # Check original PNG size. If > 2MB, compress to JPEG for faster backend processing.
        image.save(buffered, format="PNG")           # Save as PNG first to check size
        if buffered.tell() > 2 * 1024 * 1024:        # If size > 2MB
            buffered = BytesIO()                     # Reset buffer
            image.save(buffered, format="JPEG", quality=85)   # Compress to JPEG
            
        img_str = base64.b64encode(buffered.getvalue()).decode()   # Encode to base64 string
        
        # Construct payload with dynamic constraints
        payload = {
            "image": img_str,                        # Base64 image string
            "styles": styles,                        # Requested caption styles
            "word_limits": word_limits               # User-defined word limits
        }
        
        # Send POST request to the Modal API
        response = requests.post(f"{MODAL_API_URL}/generate-captions", json=payload, timeout=300)
        
        if response.status_code == 200:              # Success
            return response.json()                   # Return parsed JSON response
        else:                                        # Failure
            return {'success': False, 'error': f"API error {response.status_code}: {response.text[:100]}"}
            
    except requests.exceptions.Timeout:              # Handle timeouts
        return {'success': False, 'error': "Timeout - The model might be starting up. Please try again in 60 seconds."}
    except Exception as e:                           # Handle other exceptions
        return {'success': False, 'error': str(e)}

# ===================== SIDEBAR CONFIGURATION =====================
# Displays backend status and application information

with st.sidebar:
    st.markdown("### 📡 Backend Status")              # Sidebar title
    st.success("🟢 Connected to Modal Serverless GPU (Free Tier)")   # Status message
    st.markdown("---")                               # Horizontal divider
    st.markdown("**Model:** Qwen2.5-VL-7B-Instruct") # Model info
    st.markdown("**Platform:** Modal")               # Platform info
    st.markdown("**Hardware:** A10G GPU")            # Hardware info
    st.info("The first request may take up to 30-90 seconds to cold-start. Subsequent requests will take 5-15 seconds to respond.")   # Cold start info
    st.markdown("---")                               # Horizontal divider
    st.markdown("**Note:**")                         # Note header
    st.error("The server automatically goes to sleep after 10 minutes of inactivity to save GPU credits.")   # Sleep info

# ===================== MAIN UI LAYOUT =====================
# Splits the screen into two columns: Image Upload & Configuration

left, right = st.columns(2, gap="large")             # Create two columns

# -------------------- LEFT COLUMN: IMAGE UPLOAD --------------------
with left:
    st.markdown("<h3>Upload Image</h3>", unsafe_allow_html=True)   # Column title
    
    # Display image or placeholder based on state
    if st.session_state.image_html:
        st.markdown(st.session_state.image_html, unsafe_allow_html=True)   # Render image HTML
    else:
        st.markdown('<div class="image-box-container"><div class="image-placeholder">📷 No image selected</div></div>', unsafe_allow_html=True)  # Render placeholder
    
    # File uploader widget
    uploaded_file = st.file_uploader("Choose an image file", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    
    if uploaded_file is not None:
        # 20MB Hard Limit Check to prevent server overload
        if uploaded_file.size > 20 * 1024 * 1024:
            st.error("❌ File is too large. Maximum size is 20MB.")   # Show error
            st.session_state.api_image = None        # Clear backend image
            st.session_state.image_html = None       # Clear UI image
        else:
            # Check if this is a new file to prevent infinite reruns
            if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != uploaded_file.name:
                try:
                    image = Image.open(uploaded_file)    # Open image using PIL
                    st.session_state.uploaded_image = image   # Store original
                    
                    # 1. UI DISPLAY (EXACT SAME AS BEFORE - UNTOUCHED)
                    resized_image = image.resize((600, 450), Image.Resampling.LANCZOS)   # Resize for UI box
                    buffered = BytesIO()                 # Buffer for UI image
                    resized_image.save(buffered, format="PNG", optimize=True, quality=95)  # Save UI image
                    img_str = base64.b64encode(buffered.getvalue()).decode() # Encode UI image
                    image_html = f'<div class="image-box-container"><img src="data:image/png;base64,{img_str}" alt="Uploaded Image" /></div>'   # Create HTML
                    st.session_state.image_html = image_html   # Store HTML
                    
                    # 2. BACKEND PREPARATION (CONDITIONAL RESIZING)
                    api_image = image.copy()             # Copy for backend
                    width, height = api_image.size       # Get dimensions
                    # Scale down proportionally if dimension > 2048
                    if width > 2048 or height > 2048:
                        ratio = 2048 / max(width, height) # Calculate aspect ratio
                        new_size = (int(width * ratio), int(height * ratio))   # New dimensions
                        api_image = api_image.resize(new_size, Image.Resampling.LANCZOS)   # Resize
                    
                    st.session_state.api_image = api_image   # Store backend image
                    st.session_state.last_uploaded_file = uploaded_file.name   # Track file
                    st.session_state.captions_generated = False   # Reset generation flag
                    st.session_state.generated_captions = {}   # Clear old captions
                    st.rerun()                              # Force UI update
                except Exception as e:                     # Handle image loading errors
                    st.error(f"Error loading image: {e}")   # Show error

# -------------------- RIGHT COLUMN: OPTIONS --------------------
with right:
    st.markdown("<h3>Caption Style</h3>", unsafe_allow_html=True)   # Column title
    
    # Radio buttons for selecting caption type
    style = st.radio(" ", ["All", "Short", "Technical", "Human-friendly"], label_visibility="collapsed")
    
    # Collapsible section for word limit adjustments
    with st.expander("Advanced Options", expanded=True):
        short_words = st.slider("Short caption words", 5, 30, 15)            # Slider for short limit
        tech_words = st.slider("Technical caption words", 15, 60, 35)        # Slider for technical limit
        human_words = st.slider("Human-friendly caption words", 10, 50, 25)  # Slider for friendly limit
    
    # Generate Button
    st.markdown('<div class="generate-button-container">', unsafe_allow_html=True)
    generate_clicked = st.button("Generate Captions", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ===================== GENERATION LOGIC =====================
# Triggers API call when the button is clicked

if generate_clicked:
    if not st.session_state.get("api_image"):           # Check if image exists
        st.warning("⚠️ Please upload an image first!")  # Show warning
    else:
        # Map UI selections to API payload values
        styles = ["all"] if style == "All" else [{"Short": "short", "Technical": "technical", "Human-friendly": "human-friendly"}[style]]
        word_limits = {"short": short_words, "technical": tech_words, "human-friendly": human_words}
        
        with st.spinner("🔄 Generating captions on Modal GPU... Please wait."):
            result = generate_captions_from_api(st.session_state.api_image, styles, word_limits)   # API Call
            
            if result.get('success'):                # If successful
                st.session_state.captions_generated = True   # Set flag
                st.session_state.generated_captions = result.get('captions', {})   # Store results
                st.rerun()                           # Refresh UI
            else:                                    # If failed
                st.error(f"❌ Error: {result.get('error', 'Unknown error')}")   # Show error

# ===================== OUTPUT SECTION =====================
# Renders the generated captions onto the screen

st.markdown("<br><br>", unsafe_allow_html=True)      # Spacer
st.markdown('<div class="output-section">', unsafe_allow_html=True)

if st.session_state.get("captions_generated", False) and st.session_state.generated_captions:
    
    # Configuration mapping for UI display
    caption_display = {
        "short": {"icon": "⚡", "title": "Short Caption", "class": "card-short"},
        "technical": {"icon": "🔬", "title": "Technical Caption", "class": "card-technical"},
        "human-friendly": {"icon": "😊", "title": "Human-friendly Caption", "class": "card-friendly"}
    }
    
    st.markdown('<div class="output-title">✨ Generated Captions</div>', unsafe_allow_html=True)
    
    # Loop through generated types and display them
    for caption_type in ["short", "technical", "human-friendly"]:   # Iterate over all possible caption types
        if caption_type in st.session_state.generated_captions:     # Check if this type was generated
            data = st.session_state.generated_captions[caption_type]   # Get specific data
            info = caption_display[caption_type]                       # Get UI info
            
            # Render HTML for the card
            st.markdown(f"""
            <div class="output-card {info['class']}">        <!-- Main card container -->
                <div class="card-header">                    <!-- Card header section -->
                    <span class="card-icon">{info['icon']}</span>   <!-- Caption type icon -->
                    <h3 class="card-title">{info['title']}</h3>     <!-- Caption type title -->
                </div>
                <div class="card-content">{data.get('caption', '')}</div>   <!-- Generated caption text -->
            </div>
            """, unsafe_allow_html=True)           # Allow HTML rendering
            
    # Clear Button logic
    col1, col2, col3 = st.columns([2, 1.5, 2])     # Columns to center the button
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)    # Spacer
        if st.button("🗑️ Clear", type="secondary", use_container_width=True):
            # Reset all session states to default
            st.session_state.captions_generated = False       # Reset generation flag
            st.session_state.generated_captions = {}          # Clear old captions
            st.session_state.uploaded_image = None            # Clear UI image
            st.session_state.api_image = None                 # Clear backend image
            st.session_state.image_html = None                # Clear HTML preview
            if 'last_uploaded_file' in st.session_state:      # Check if file tracker exists
                del st.session_state['last_uploaded_file']    # Remove file tracker
            st.rerun()                                        # Force UI refresh

elif st.session_state.get("api_image"):
    st.markdown('<div class="empty-output">📷 Upload an image and click "Generate Captions" to see results here.</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="empty-output">📷 Upload an image and click "Generate Captions" to see results here.</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)   # Close output section

# ===================== FOOTER =====================
# Renders the footer text
st.markdown("""
<div class="footer">
    © 2025 Image Caption Studio • Powered by Qwen2.5-VL-7B-Instruct on Modal
</div>
""", unsafe_allow_html=True)
