import requests, re, json, os, collections
from bs4 import BeautifulSoup
import os
import time

# ---------------------------------
# CONFIGURATION
# ---------------------------------
SCHOLAR_URL = "https://scholar.google.com/citations?user=NNLK86QAAAAJ&hl=en"
PATENT_URLS = [
    "https://patents.google.com/patent/US11971805B2/en",
    "https://patents.google.com/patent/US20230269268A1/en",
    "https://patents.google.com/patent/US20200409681A1/en",
    "https://patents.google.com/patent/US20190333075A1/en",
    "https://patents.google.com/patent/US11443026B2/en",
    "https://patents.google.com/patent/US8626888B2/en",
    "https://patents.google.com/patent/US10887414B2/en",
    "https://patents.google.com/patent/US10834219B1/en",
    "https://patents.google.com/patent/US10460031B2/en",
    "https://patents.google.com/patent/US10079719B2/en",
    "https://patents.google.com/patent/US8626888B2/en"
]
IEEE_URLS = [
    "https://ieeexplore.ieee.org/document/11187640",
    "https://link.springer.com/chapter/10.1007/978-981-97-4540-1_3",
    "https://ieeexplore.ieee.org/document/10624986",
    "https://ieeexplore.ieee.org/document/10426170",
    "https://ieeexplore.ieee.org/document/9955300"
]

OUTPUT_FILE = "wordcloud_data.json"
DIFF_FILE = "wordcloud_diff.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------------------------------
# HELPERS
# ---------------------------------
def clean_text(text):
    text = re.sub(r'[^A-Za-z0-9\s-]', '', text)
    return text.strip()

def extract_keywords(titles):
    freq = collections.Counter()
    for title in titles:
        words = re.findall(r'\b[A-Za-z]{4,}\b', title)
        for w in words:
            w = w.title()
            if w.lower() not in ['with', 'from', 'into', 'using', 'based', 'over', 'through', 'under', 'within', 'this', 'that', 'have']:
                freq[w] += 1
    return freq

# ---------------------------------
# Load old data & compare 
# ---------------------------------

def load_previous_data():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            try:
                return dict((w, v) for w, v in json.load(f))
            except Exception:
                return {}
    return {}

def compare_wordclouds(current_data, prev_data):
    new_words = {}
    for word, weight in current_data.items():
        if word not in prev_data:
            new_words[word] = weight
        elif weight != prev_data[word]:
            new_words[word] = weight - prev_data[word]
    return new_words

# ---------------------------------
# FETCH FUNCTIONS
# ---------------------------------
def fetch_dzone_titles():
    path = "dzone_titles.txt"
    if os.path.exists(path):
        with open(path) as f:
            titles = [clean_text(line.strip()) for line in f if line.strip()]
        print(f"✅ DZone: {len(titles)} titles loaded from local file")
        return titles
    print("⚠️ Could not fetch DZone articles (Cloudflare challenge).")
    return []

def fetch_patent_titles():
    titles = []
    for url in PATENT_URLS:
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        title_tag = soup.find('meta', attrs={'name': 'DC.title'})
        if title_tag and title_tag.get('content'):
            titles.append(clean_text(title_tag['content']))
    print(f"✅ Patents: {len(titles)} titles fetched")
    return titles

def fetch_ieee_titles():
    titles = []
    for url in IEEE_URLS:
        try:
            resp = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://ieeexplore.ieee.org/"
            }, timeout=10)

            soup = BeautifulSoup(resp.text, 'html.parser')
            meta_tag = soup.find('meta', attrs={'name': 'citation_title'})

            if meta_tag and meta_tag.get('content'):
                title = clean_text(meta_tag['content'])
            else:
                # fallback: use regex search
                match = re.search(r'"title":"([^"]+)"', resp.text)
                title = clean_text(match.group(1)) if match else None

            if title and title not in titles:
                titles.append(title)

        except Exception as e:
            print(f"⚠️ Error fetching IEEE title for {url}: {e}")

    print(f"✅ IEEE: {len(titles)} titles fetched")
    print("titles:", titles)
    return titles


# -------------------------
# MAIN
# -------------------------
def main():
    all_titles = fetch_ieee_titles() + fetch_patent_titles() + fetch_dzone_titles()
    freq = extract_keywords(all_titles)

    # ✅ Take exactly top 50 keywords
    top_keywords = freq.most_common(50)

    # Normalize weights to stay visually balanced (10–50)
    current_data = {
        word: int((count / top_keywords[0][1]) * 50)
        for word, count in top_keywords
    }

    prev_data = load_previous_data()
    new_words = compare_wordclouds(current_data, prev_data)

    # ✅ Keep only top 50 even in combined data
    combined_data = dict(list(current_data.items())[:50])

    with open(OUTPUT_FILE, "w") as f:
        json.dump([[w, v] for w, v in combined_data.items()], f, indent=2)

    if new_words:
        with open(DIFF_FILE, "w") as f:
            json.dump([[w, v] for w, v in new_words.items()], f, indent=2)
        print(f"✨ {len(new_words)} new/changed words saved to {DIFF_FILE}")
    else:
        print("✅ No new words detected")

    print(f"✅ Wordcloud data updated → {OUTPUT_FILE}")
    print("Top 10 keywords:", top_keywords[:10])

if __name__ == "__main__":
    main()