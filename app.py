import streamlit as st
import pandas as pd
from datetime import datetime
import zipfile
import os
import time

# import scrape function AND the module so we can toggle the proxy flag
from scraper_main import scrape_into_dataframe, download_images
import scraper_main

# 🧭 Page Setup
st.set_page_config(page_title="Web Harvester", page_icon="🕸️", layout="wide")

# Initialize session state
if "scraped_data" not in st.session_state:
    st.session_state.scraped_data = None
if "downloaded_images_files" not in st.session_state:
    st.session_state.downloaded_images_files = None

# 🌐 Custom CSS for Modern UI
st.markdown("""
    <style>
        body { background-color: #f7f9fc; }
        .main-title {
            text-align: center;
            color: #2c3e50;
            font-size: 4em;
            font-weight: bold;
            margin-bottom: -10px;
        }
        .sub-title {
            text-align: center;
            color: #7f8c8d;
            font-size: 1.2em;
            margin-bottom: 30px;
        }
        .stButton>button {
            background-color: #3498db;
            color: white;
            font-weight: bold;
            border-radius: 10px;
            padding: 10px 25px;
        }
        .stButton>button:hover {
            background-color: #2980b9;
        }
        .info-box {
            background: #ecf0f1;
            padding: 15px;
            border-radius: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# 🕸️ Header
st.markdown('<div class="main-title">🕸️ Web Harvester</div>', unsafe_allow_html=True)
st.markdown(''' <div style="display: flex; justify-content: center; align-items: center; margin-top: 10px;"> 
            <img src="https://assets-v2.lottiefiles.com/a/b942abb8-d62e-11ee-a179-af4105107ebe/tPZDd31PcO.gif" width="200" height="200"> </div> ''', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Your friendly web data extractor — built with Python + Streamlit</div>', unsafe_allow_html=True)


# ⚙️ Sidebar
with st.sidebar:
    st.header("⚙️ Settings Panel")
    st.markdown("Fine-tune how you want to scrape data:")

    tag_type = st.selectbox(
        "📄 Content Type",
        ("All Text", "Headings", "Paragraphs", "Links", "Custom Tag", "Only Images", "Raw HTML")
    )

    custom_tag = st.text_input("🔖 Custom Tag (optional)", placeholder="e.g., div, span, title")
    limit = st.slider("📊 Limit Results", 10, 500, 50)

    st.markdown("---")
    use_ai = st.checkbox("🤖 Use LLM Parsing")
    parse_text = ""
    api_key = "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"
    
    if use_ai:
        st.success("Using Groq (Cloud)")
        parse_text = st.text_area("🧠 Describe what you want to extract:", placeholder="e.g., Extract all product prices and names")

    # NEW: proxy toggle (default OFF)
    use_proxies = st.checkbox("🛡️ Use proxies (auto)", value=False)

    st.markdown("💡 **Tip:** Try scraping small limits first to avoid timeouts.")

# 🌐 URL Input
url = st.text_input("🌍 Enter Website URL", placeholder="https://example.com")

# 💡 Global info message about relative links
st.info("🔗 **Note:** Some links may be partial (like `/product/...`). Add the main domain (e.g., `https://flipkart.com`) before them to open correctly.")

# Map UI text to scraper tag keys
mapping = {
    "All Text": "alltext",
    "Headings": "headings",
    "Paragraphs": "paragraphs",
    "Links": "links",
    "Custom Tag": "customtag",
    "Only Images": "images",
    "Raw HTML": "rawhtml"
}
tag_key = mapping.get(tag_type, "alltext")

# 🚀 Scrape Button
if st.button("🚀 Scrape Site"):
    if not url.strip():
        st.warning("⚠️ Please enter a valid URL!")
    else:
        # Configure proxy usage in scraper_main based on sidebar toggle
        # If use_proxies True -> keep scraper_main.PROXY_SOURCE_URL as-is (or set default)
        # If False -> disable it by setting to empty string
        if use_proxies:
            if not getattr(scraper_main, "PROXY_SOURCE_URL", ""):
                scraper_main.PROXY_SOURCE_URL = "https://www.proxy-list.download/api/v1/get?type=http"
        else:
            scraper_main.PROXY_SOURCE_URL = ""

        with st.spinner("🔎 Scraping in progress... please wait ⏳"):
            try:
                start_time = datetime.now()
                df = scrape_into_dataframe(
                    url, 
                    tag_type=tag_key, 
                    limit=limit, 
                    custom_tag=custom_tag, 
                    parse_text=parse_text,
                    api_key=api_key
                )
                duration = round((datetime.now() - start_time).total_seconds(), 2)
                
                # Store in session state
                st.session_state.scraped_data = df
                st.session_state.last_url = url
                st.session_state.last_tag_type = tag_type

                if df is None:
                    # 🧾 Raw HTML mode
                    st.success(f"✅ HTML scraped successfully in {duration} seconds!")
                    with open("page_content.txt", "r", encoding="utf-8") as f:
                        html_content = f.read()
                    st.download_button(
                        "⬇️ Download Raw HTML (.txt)",
                        html_content,
                        "page_content.txt",
                        "text/plain",
                        use_container_width=True
                    )

                elif isinstance(df, pd.DataFrame) and not df.empty:
                    st.success(f"✅ Scraped {len(df)} records in {duration} seconds!")

            except Exception as e:
                st.error(f"❌ Error: {e}")

# Display scraped data from session state
if st.session_state.scraped_data is not None:
    df = st.session_state.scraped_data
    url = st.session_state.get("last_url", url)
    tag_type = st.session_state.get("last_tag_type", tag_type)
    
    if isinstance(df, pd.DataFrame) and not df.empty:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
           st.markdown(f"<p style='font-size:15px;'>🔗 <b>URL:</b> {url[:50]}...</p>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<p style='font-size:15px;'>📑 <b>Type:</b> {tag_type}</p>", unsafe_allow_html=True)
        with col3:
             st.markdown(f"<p style='font-size:15px;'>🕒 <b>Time:</b> Done</p>", unsafe_allow_html=True)

        # 👀 Show preview (first 5 rows)
        st.markdown("### 👀 Quick Preview (first 5 rows)")
        st.dataframe(df.head(), use_container_width=True)

        # Full Data (inside expander)
        with st.expander("📄 View Full Scraped Data"):
            st.dataframe(df, use_container_width=True)

        # Prepare data for download (outside expander)
        csv_data = df.to_csv(index=False).encode("utf-8")
        txt_data = df.to_string(index=False)

        st.markdown("### 📦 Download Extracted Data")
        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button(
                "⬇️ Download as CSV",
                csv_data,
                "scraped_data.csv",
                "text/csv",
                use_container_width=True
            )
        with col_b:
            st.download_button(
                "⬇️ Download as TXT",
                txt_data,
                "scraped_data.txt",
                "text/plain",
                use_container_width=True
            )
        
        # 🖼️ Image Download Option
        if tag_type == "Only Images" and not df.empty and "src" in df.columns:
            st.markdown("### 🖼️ Bulk Download Images")
            
            # Show image URLs
            st.markdown("**📋 Image URLs found:**")
            for idx, img_url in enumerate(df["src"].tolist()[:10], 1):
                st.code(img_url, language="text")
            if len(df) > 10:
                st.info(f"... and {len(df) - 10} more images")
            
            if st.button("⬇️ Download All Images at Once", use_container_width=True, key="download_images_btn"):
                with st.spinner("📥 Downloading images... this may take a moment"):
                    try:
                        image_urls = df["src"].tolist()
                        # Extract base domain from URL for relative links
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        base_url = f"{parsed.scheme}://{parsed.netloc}"
                        
                        st.info(f"🔗 Base URL: {base_url}")
                        
                        downloaded_files = download_images(image_urls, base_url=base_url, output_folder="downloaded_images")
                        
                        # Store in session state
                        st.session_state.downloaded_images_files = downloaded_files
                        
                        if downloaded_files:
                            st.success(f"✅ Downloaded {len(downloaded_files)} images!")
                            
                            # Create ZIP file for download
                            zip_filename = "downloaded_images.zip"
                            try:
                                if os.path.exists(zip_filename):
                                    os.remove(zip_filename)
                            except:
                                pass
                            
                            # Create ZIP and close it properly
                            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                for file in downloaded_files:
                                    if os.path.exists(file):
                                        arcname = os.path.basename(file)
                                        zipf.write(file, arcname=arcname)
                            
                            # Now read and display download button
                            time.sleep(0.5)  # Small delay to ensure file is released
                            if os.path.exists(zip_filename):
                                with open(zip_filename, "rb") as f:
                                    zip_data = f.read()
                                st.download_button(
                                    "📦 Download All Images (ZIP)",
                                    zip_data,
                                    zip_filename,
                                    "application/zip",
                                    use_container_width=True
                                )
                            
                            # Show thumbnails
                            st.markdown("**📸 Preview of downloaded images:**")
                            cols = st.columns(4)
                            for idx, file in enumerate(downloaded_files[:12]):
                                if os.path.exists(file):
                                    try:
                                        with cols[idx % 4]:
                                            st.image(file, use_container_width=True)
                                    except:
                                        pass
                        else:
                            st.warning("⚠️ No images could be downloaded. Check the URLs or network connection.")
                    except Exception as e:
                        st.error(f"❌ Error downloading images: {e}")
            
            # Show previously downloaded images if they exist
            if st.session_state.downloaded_images_files:
                st.markdown("### 📥 Downloaded Images")
                st.info(f"✅ {len(st.session_state.downloaded_images_files)} images ready for download")
                
                # Recreate ZIP for download
                zip_filename = "downloaded_images.zip"
                if os.path.exists(zip_filename) and st.session_state.downloaded_images_files:
                    with open(zip_filename, "rb") as f:
                        zip_data = f.read()
                    st.download_button(
                        "📦 Download All Images (ZIP)",
                        zip_data,
                        zip_filename,
                        "application/zip",
                        use_container_width=True,
                        key="redownload_zip"
                    )

st.markdown("---")

# 📘 How to Use
with st.expander("ℹ️ How to use this tool"):
    st.markdown("""
    ### 🧭 Steps to Scrape:
    1. Paste a **valid website URL** below  
    2. Select **what type of content** to extract  
    3. Adjust the **limit or custom tag** (optional)  
    4. Toggle **Use proxies (auto)** if you want to try free proxies first  
    5. Click **Scrape Site** and relax ⏳  
    6. Preview your extracted data and download it as CSV or TXT  
    """)

# 🧾 Footer
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#95a5a6;'>Made with ❤️ using Streamlit • Designed by <b>Shlok Upadhyay</b></p>",
    unsafe_allow_html=True
)
