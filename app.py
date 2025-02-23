import time
import requests
from bs4 import BeautifulSoup
import re
import streamlit as st

# Default keywords and stopwords
DEFAULT_KEYWORDS = ["Gen-AI", "Generative AI", "Artificial Intelligence", "Machine Learning", "AI"]
STOPWORDS = {"the", "and", "is", "in", "to", "of", "for", "on", "with", "at", "a", "an"}

def fetch_page(url):
    """Fetches a webpage using requests."""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.text
        else:
            st.error(f"⚠️ Failed to fetch {url}. Status code: {response.status_code}")
            return None
    except requests.RequestException as e:
        st.error(f"❌ Error fetching {url}: {e}")
        return None

def extract_links(html, base_url):
    """Extracts all valid links from a webpage."""
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a_tag in soup.find_all("a", href=True):
        full_url = requests.compat.urljoin(base_url, a_tag["href"])
        links.add(full_url)
    return links

def filter_illinois_links(links):
    """Keeps only links that belong to illinois.edu and its subdomains."""
    return {
        link for link in links 
        if requests.utils.urlparse(link).netloc.endswith(".illinois.edu") 
           or requests.utils.urlparse(link).netloc == "illinois.edu"
    }

def contains_keywords(html, keywords, min_count=3):
    """Checks if the page contains the specified keywords a minimum number of times."""
    soup = BeautifulSoup(html, "html.parser")
    # Extract meaningful text from common containers
    content_blocks = soup.find_all(["article", "section", "div", "p", "h1", "h2"], class_=True)
    text = " ".join(block.get_text() for block in content_blocks)
    
    # Clean and normalize text
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    words = text.lower().split()
    words = [word for word in words if word not in STOPWORDS]
    
    # Count whole-word matches for each keyword
    matched_keywords = {kw: len(re.findall(rf'\b{kw.lower()}\b', text, re.IGNORECASE)) for kw in keywords}
    st.write(f"🔍 Checking page for keywords. Found matches: {matched_keywords}")
    
    return sum(matched_keywords.values()) >= min_count

def crawl_illinois(start_urls, keywords, max_pages=50):
    """Crawls the provided websites looking for AI-related content."""
    visited = set()
    to_visit = set(start_urls)
    relevant_articles = []
    page_count = 0

    # Create a progress bar in the Streamlit app
    progress_bar = st.progress(0)
    
    while to_visit and page_count < max_pages:
        url = to_visit.pop()
        if url in visited:
            continue
        visited.add(url)
        page_count += 1

        st.write(f"🔍 Scanning: {url}")
        html = fetch_page(url)
        if not html:
            continue

        links = extract_links(html, url)
        illinois_links = filter_illinois_links(links)
        to_visit.update(illinois_links - visited)
        
        if contains_keywords(html, keywords):
            relevant_articles.append(url)
            st.success(f"🔹 Found relevant article: {url}")

        time.sleep(1)  # be polite to servers
        progress_bar.progress(page_count / max_pages)
    
    progress_bar.empty()
    return relevant_articles

# --- Streamlit App Layout ---
st.title("Illinois AI News Crawler")
st.write("This app crawls websites (by default, https://illinois.edu) for AI-related content based on keywords.")

# Input: websites to crawl
sites_input = st.text_input(
    "Enter website(s) to crawl (separate multiple URLs by commas):", 
    "https://illinois.edu"
)

# Input: keywords to search for
keywords_input = st.text_input(
    "Enter additional keywords (separate multiple by commas):", 
    "Deep Learning, Neural Networks"
)

# Button to start crawling
if st.button("Start Crawling"):
    # Parse inputs into lists
    start_urls = [site.strip() for site in sites_input.split(",") if site.strip()]
    user_keywords = [kw.strip() for kw in keywords_input.split(",") if kw.strip()]
    
    # Combine default keywords with user-defined ones if any; 
    # here you can decide to use user_keywords exclusively or add them to the defaults.
    search_keywords = user_keywords if user_keywords else DEFAULT_KEYWORDS
    
    st.write("### Starting crawl...")
    articles = crawl_illinois(start_urls, search_keywords, max_pages=50)
    
    st.write("## AI-Related Articles Found:")
    if articles:
        for article in articles:
            st.markdown(f"- [Link]({article})")
    else:
        st.info("No relevant articles were found.")
