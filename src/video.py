# src/video.py

import os
import random
import requests
import re
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

# ----------------- CONFIG -----------------
PEXELS_API_KEY = "HnNqgJkNliEvK72zXHXjC8DxpsAmaQc7TkKXDA3HjyLnRZrrs0VLLkgg"
MEDIA_DIR = "input/media_temp/"
FINAL_DIR = "output/final/"

os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(FINAL_DIR, exist_ok=True)

STOPWORDS = {"the","and","with","your","that","this","then","have","will","just","like","very","from","into"}
FALLBACK_KEYWORDS = ["health","fitness","meditation","yoga","food","nature","relax","lifestyle"]

# ----------------- HELPERS -----------------
def extract_keywords(text, max_keywords=3):
    text = re.sub(r"[^a-zA-Z ]", "", text).lower()
    words = text.split()
    keywords = [w for w in words if len(w) > 3 and w not in STOPWORDS]
    if not keywords:
        return random.choice(FALLBACK_KEYWORDS)
    return " ".join(keywords[:max_keywords])

def fetch_pexels_video(query):
    """Fetch a single best video for a given query"""
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=1"
    print(f"🔍 Searching Pexels for: '{query}'")
    response = requests.get(url, headers=headers)
    data = response.json()

    if not data.get("videos"):
        print(f"⚠️ No results for '{query}', using fallback")
        query = random.choice(FALLBACK_KEYWORDS)
        url = f"https://api.pexels.com/videos/search?query={query}&per_page=1"
        response = requests.get(url, headers=headers)
        data = response.json()

    if not data.get("videos"):
        return None

    video = data["videos"][0]
    files_sorted = sorted(video["video_files"], key=lambda x: x["width"], reverse=True)
    video_url = files_sorted[0]["link"]

    file_path = os.path.join(MEDIA_DIR, f"{query}.mp4")
    r = requests.get(video_url, stream=True)
    with open(file_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)
    return file_path

def split_script(script_text):
    """Split script into meaningful chunks (sentences)."""
    sentences = re.split(r'[.!?]', script_text)
    return [s.strip() for s in sentences if s.strip()]

# ----------------- MAIN FUNCTION -----------------
def make_video(audio_path, script_text):
    """
    Create a 9:16 reel where each sentence of script 
    is matched with its own relevant Pexels video.
    """
    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration

    # Step 1: split script
    chunks = split_script(script_text)
    n_chunks = len(chunks)
    per_chunk_duration = audio_duration / n_chunks

    # Step 2: fetch relevant video per chunk
    clips = []
    for chunk in chunks:
        query = extract_keywords(chunk)
        media_file = fetch_pexels_video(query)
        if not media_file:
            continue

        # Load clip and crop to 9:16
        clip = VideoFileClip(media_file)
        clip = clip.resize(height=1920)
        clip = clip.crop(width=1080, height=1920,
                         x_center=clip.w//2, y_center=clip.h//2)

        # Trim to sentence duration
        clip = clip.subclip(0, min(per_chunk_duration, clip.duration))
        clips.append(clip)

    if not clips:
        raise Exception("No video clips found for any script chunk")

    # Step 3: concatenate & add audio
    final_clip = concatenate_videoclips(clips).set_audio(audio_clip)

    # Step 4: export
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    output_path = os.path.join(FINAL_DIR, f"{base_name}.mp4")
    final_clip.write_videofile(
        output_path,
        fps=24,
        codec='libx264',
        audio_codec='aac'
    )

    # Cleanup
    final_clip.close()
    audio_clip.close()
    for c in clips:
        c.close()
    for file in os.listdir(MEDIA_DIR):
        os.remove(os.path.join(MEDIA_DIR, file))

    return output_path
