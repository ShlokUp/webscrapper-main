import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
]

# Global proxy setting
PROXY_SOURCE_URL = "https://www.proxy-list.download/api/v1/get?type=http"

def get_proxies(limit=5):
    """Get list of proxies"""
    if not PROXY_SOURCE_URL:
        return []
    
    try:
        response = requests.get(PROXY_SOURCE_URL, timeout=8)
        proxies = []
        for line in response.text.splitlines()[:limit]:
            line = line.strip()
            if line and ':' in line and not line.startswith(('http://', 'https://')):
                proxies.append(f"http://{line}")
        random.shuffle(proxies)
        return proxies
    except:
        return []

def fetch_page(url, use_proxies=True):
    """Fetch webpage with rotating user agents"""
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    time.sleep(0.5)  # Polite delay
    
    # Try with proxies first
    if use_proxies:
        proxies = get_proxies()
        for proxy in proxies:
            try:
                response = requests.get(
                    url, 
                    headers=headers, 
                    proxies={"http": proxy, "https": proxy}, 
                    timeout=10,
                    verify=False
                )
                if response.status_code == 200:
                    return response.text
            except:
                continue
    
    # Fallback to direct request
    response = requests.get(url, headers=headers, timeout=15, verify=False)
    response.raise_for_status()
    return response.text

def scrape_into_dataframe(url, tag_type="alltext", limit=50, custom_tag=None, parse_text=None, use_proxies=True, api_key=None):
    """
    Main scraping function - extracts data from URL and returns DataFrame
    """
    # Validate URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Fetch page
    html = fetch_page(url, use_proxies=use_proxies)
    soup = BeautifulSoup(html, "html.parser")
    
    # Handle raw HTML mode
    if tag_type == "rawhtml":
        with open("page_content.txt", "w", encoding="utf-8") as f:
            f.write(html)
        return None
    
    # Extract based on tag type
    if tag_type == "images":
        imgs = soup.find_all("img", src=True)[:limit]
        data = [{"src": img["src"], "alt": img.get("alt", "")} for img in imgs]
    
    elif tag_type == "links":
        links = soup.find_all("a", href=True)[:limit]
        data = [{"text": link.get_text(strip=True), "url": link["href"]} for link in links]
    
    elif tag_type == "headings":
        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])[:limit]
        data = [{"tag": h.name, "text": h.get_text(strip=True)} for h in headings]
    
    elif tag_type == "paragraphs":
        paragraphs = soup.find_all("p")[:limit]
        data = [{"text": p.get_text(strip=True)} for p in paragraphs]
    
    elif tag_type == "customtag" and custom_tag:
        elements = soup.find_all(custom_tag)[:limit]
        data = [{"content": elem.get_text(strip=True)} for elem in elements]
    
    else:  # alltext - default
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        data = [{"content": line} for line in lines] # Get ALL lines initially
    
    # AI parsing if requested
    if parse_text and data:
        try:
            from parse import parse_content
            
            # If AI is enabled, we want to process the whole content, not just the limited rows
            # Combine text into larger chunks (approx 6000 chars) to reduce API calls and provide context
            full_text_list = [d.get("content", "") for d in data]
            
            # Create chunks
            chunks = []
            current_chunk = ""
            for line in full_text_list:
                if len(current_chunk) + len(line) < 6000:
                    current_chunk += line + "\n"
                else:
                    chunks.append(current_chunk)
                    current_chunk = line + "\n"
            if current_chunk:
                chunks.append(current_chunk)
            
            # Parse chunks
            parsed_results = parse_content(chunks, parse_text, api_key=api_key)
            
            # Create DataFrame from parsed results
            df = pd.DataFrame(parsed_results, columns=["Extracted Data"])
            
            # Apply limit to the FINAL extracted results
            if limit:
                df = df.head(limit)
                
            return df
            
        except Exception as e:
            print(f"AI Parsing Error: {e}")
            # Fallback to normal behavior if AI fails
            pass

    # If no AI or AI failed, apply limit to raw data and return
    if limit:
        data = data[:limit]
    
    df = pd.DataFrame(data)
    return df


def download_images(urls, base_url=None, output_folder="downloaded_images"):
    """
    Download all images from a list of URLs
    Returns a list of successfully downloaded file paths
    """
    import os
    from urllib.parse import urljoin, urlparse
    
    os.makedirs(output_folder, exist_ok=True)
    downloaded_files = []
    
    for idx, url in enumerate(urls, 1):
        try:
            # Ensure url is a string and strip whitespace
            url = str(url).strip()
            
            if not url or url == 'nan':
                continue
            
            # Handle relative URLs - convert to absolute
            if base_url and not url.startswith(('http://', 'https://', '//')):
                # Remove leading ./ or ../
                while url.startswith('../'):
                    url = url[3:]
                while url.startswith('./'):
                    url = url[2:]
                
                # Ensure base_url ends without slash, url starts without slash
                base_url_clean = base_url.rstrip('/')
                url_clean = url.lstrip('/')
                url = f"{base_url_clean}/{url_clean}"
            
            # Skip if still not a valid URL
            if not url.startswith(('http://', 'https://')):
                print(f"Skipping invalid URL: {url}")
                continue
            
            # Download image
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            response.raise_for_status()
            
            # Extract filename from URL
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            
            # Clean up filename - remove query parameters
            if '?' in filename:
                filename = filename.split('?')[0]
            
            # Fallback filename if URL has no file extension
            if not filename or '.' not in filename:
                filename = f"image_{idx}.jpg"
            
            # Ensure unique filename to avoid overwrites
            filepath = os.path.join(output_folder, filename)
            counter = 1
            name, ext = os.path.splitext(filename)
            while os.path.exists(filepath):
                filepath = os.path.join(output_folder, f"{name}_{counter}{ext}")
                counter += 1
            
            # Save image
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            downloaded_files.append(filepath)
            time.sleep(0.2)  # Polite delay between downloads
            
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            continue
    
    return downloaded_files