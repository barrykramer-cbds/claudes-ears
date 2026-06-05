#!/usr/bin/env python3
"""
Claude's Ears - Semantic Lyric Channel

Three-tier lyric perception:
  1. Acquisition: web fetch for known songs, Whisper fallback for originals
  2. Lexical sentiment: VADER surface analysis
  3. Semantic interpretation: Claude API for deep meaning
"""

import os, json, re, requests

def fetch_lyrics_web(artist, title):
    try:
        url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            lyrics = data.get("lyrics", "")
            if lyrics and len(lyrics) > 50:
                lyrics = lyrics.strip()
                lines = [l.strip() for l in lyrics.split('\n') if l.strip()]
                return {"source": "lyrics.ovh", "text": "\n".join(lines), "lines": [{"text": l} for l in lines], "method": "web_fetch"}
    except Exception as e:
        print(f"    lyrics.ovh failed: {e}")
    return None

def lyrics_from_whisper_cache(cache_path):
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            data = json.load(f)
        lines = data.get("lines", [])
        if lines:
            text = "\n".join(l["text"] for l in lines)
            return {"source": "whisper", "text": text, "lines": lines, "method": "transcription"}
    return None

def vader_sentiment(lyrics_data):
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()
        lines = lyrics_data.get("lines", [])
        sentiments = []
        for line in lines:
            text = line.get("text", line) if isinstance(line, dict) else str(line)
            score = analyzer.polarity_scores(text)
            sentiments.append({"text": text, "compound": round(score["compound"], 4), "pos": round(score["pos"], 3), "neg": round(score["neg"], 3)})
        overall = round(float(sum(s["compound"] for s in sentiments) / max(len(sentiments), 1)), 4)
        return {"overall_sentiment": overall, "line_sentiments": sentiments[:50],
                "most_positive": max(sentiments, key=lambda s: s["compound"])["text"] if sentiments else "",
                "most_negative": min(sentiments, key=lambda s: s["compound"])["text"] if sentiments else ""}
    except ImportError:
        return {"overall_sentiment": None, "note": "VADER not installed"}

def build_semantic_prompt(lyrics_text, acoustic_context=None):
    system = """You are a lyric analyst. Given song lyrics and optional acoustic data, provide structured semantic analysis. Return ONLY valid JSON:
{"themes":[],"imagery":[],"cultural_references":[{"reference":"","tradition":"","significance":""}],"emotional_arc":"","subtext":"","surface_vs_depth":"","semantic_valence":0.0,"key_lines":[{"line":"","significance":""}]}
semantic_valence: -1 to +1 based on MEANING not vocabulary. Captivity in gentle language = negative. Freedom in dark metaphors = positive."""
    user_msg = f"Analyze these lyrics:\n\n{lyrics_text}"
    if acoustic_context:
        user_msg += "\n\nAcoustic context:\n" + "\n".join(f"  {k}: {v}" for k, v in acoustic_context.items())
    return system, user_msg

def semantic_analysis_via_api(lyrics_text, acoustic_context=None, api_key=None):
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {"error": "No API key", "prompt_template": build_semantic_prompt(lyrics_text, acoustic_context)}
    system, user_msg = build_semantic_prompt(lyrics_text, acoustic_context)
    try:
        resp = requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 1500, "system": system,
                  "messages": [{"role": "user", "content": user_msg}]}, timeout=30)
        if resp.status_code == 200:
            text = resp.json()["content"][0]["text"].strip()
            if text.startswith("```"): text = re.sub(r'^```(?:json)?\n?', '', text); text = re.sub(r'\n?```$', '', text)
            result = json.loads(text); result["method"] = "claude_api"; return result
        return {"error": f"API {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def full_lyric_perception(artist, title, whisper_cache=None, acoustic_context=None, api_key=None):
    print(f"  Lyric perception: {artist} - {title}")
    lyrics_data = fetch_lyrics_web(artist, title)
    if not lyrics_data and whisper_cache: lyrics_data = lyrics_from_whisper_cache(whisper_cache)
    if not lyrics_data: return {"available": False}
    print(f"    Source: {lyrics_data['source']} ({len(lyrics_data['lines'])} lines)")
    vader = vader_sentiment(lyrics_data)
    semantic = semantic_analysis_via_api(lyrics_data["text"], acoustic_context, api_key)
    result = {"available": True, "source": lyrics_data["source"], "line_count": len(lyrics_data["lines"]),
              "text": lyrics_data["text"][:3000], "vader": vader, "semantic": semantic}
    if vader.get("overall_sentiment") is not None and semantic.get("semantic_valence") is not None:
        gap = semantic["semantic_valence"] - vader["overall_sentiment"]
        result["interpretation_gap"] = {"vader_surface": vader["overall_sentiment"],
            "semantic_depth": semantic["semantic_valence"], "gap": round(gap, 4),
            "description": "darker than they sound" if gap < -0.2 else "brighter than they sound" if gap > 0.2 else "surface and depth align"}
    return result

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3: print("Usage: python semantic_lyrics.py <artist> <title>"); sys.exit(1)
    result = full_lyric_perception(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))
