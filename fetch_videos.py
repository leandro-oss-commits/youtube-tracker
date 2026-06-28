#!/usr/bin/env python3
"""
YouTube Tracker - Fetch latest videos from specified channels
Uses YouTube Data API v3
"""

import urllib.request
import urllib.parse
import json
import time
import os

API_KEY = os.environ.get("YT_API_KEY") or "REDACTED_KEY"
CHANNELS = [
    # 🏆 Industry Leaders - High viewership, recognized authorities
    "garytalksstuff",     # Chinese harness engineering, agent workflows
    "Anthropic",          # Building Effective Agents, harness architecture
    "latentspace",        # AI engineering podcast, agent systems
    "openai",             # Codex, agent control, practical demos
    "karpathy",           # AI-native software, practical engineering
    "aliabdaal",          # AI productivity workflows
    "ycombinator",        # AI startup applications & tools
    "Fireship",           # Quick practical AI/dev content
    "mreflow",            # AI explained, agent frameworks
    
    # 💎 Hidden Treasures - Small subscriber counts, high signal-to-noise
    "TechWhistleHub",     # <1K subs — harness engineering deep dives, agent memory mechanisms
    "indydevdan",         # Claude Code agentic coding, practical builds
    "cognitiverevolution", # AI builder interviews, agent engineering conversations
    "TonbisAIGarage",     # AI garage, practical builds and experiments

    # 🆕 Added 2026-06-28 from 知乎推荐「普通人学AI建议死磕的10个油管博主」
    "jeffsu",             # AI生产力天花板 — ChatGPT实战、AI办公效率、Prompt技巧
    "TinaHuang1",         # 最适合普通人的AI学姐 — AI Agent、数据科学、AI职业规划
    "IBMTechnology",      # AI知识百科全书 — RAG、Agent、Transformer、向量数据库
    "googlecloudtech",    # Google官方AI课堂 — Gemini, Vertex AI, NotebookLM
    "daveebbelaar",       # AI Agent实战派 — AI系统工程、Agent开发、LangChain
    "deeplearningai",     # 吴恩达的AI学校 — Prompt Engineering、AI Agent、LangChain、RAG
    "aiexplained-official", # 前沿AI解读第一梯队 — GPT, Claude, Gemini, AGI
    "TwoMinutePapers",    # AI圈快乐源泉 — AI论文、视频生成、机器人、科研突破
    "AlexFinnOfficial",   # Vibe Coding入门必看 — Cursor, Claude Code, AI编程
]
MAX_VIDEOS_PER_CHANNEL = 10

def api_request(url):
    """Make a GET request to the YouTube API and return parsed JSON."""
    req = urllib.request.Request(url, headers={"User-Agent": "YouTubeTracker/1.0"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def get_channel_info(channel_name):
    """Search for a channel by name and return its ID and title."""
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(channel_name)}&type=channel&maxResults=1&key={API_KEY}"
    data = api_request(url)
    if "items" not in data or len(data["items"]) == 0:
        print(f"  [WARN] No channel found for '{channel_name}'")
        return None, None
    item = data["items"][0]
    return item["id"]["channelId"], item["snippet"]["title"]

def get_uploads_playlist(channel_id):
    """Get the uploads playlist ID for a channel."""
    url = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={channel_id}&key={API_KEY}"
    data = api_request(url)
    if "items" not in data or len(data["items"]) == 0:
        return None
    return data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

def get_playlist_videos(playlist_id, max_results=MAX_VIDEOS_PER_CHANNEL):
    """Get the latest videos from a playlist."""
    videos = []
    url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults={max_results}&playlistId={playlist_id}&key={API_KEY}"
    data = api_request(url)
    if "items" not in data:
        return videos
    for item in data["items"]:
        videos.append({
            "videoId": item["snippet"]["resourceId"]["videoId"],
            "title": item["snippet"]["title"],
            "publishedAt": item["snippet"]["publishedAt"],
            "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
            "channelTitle": item["snippet"]["channelTitle"],
        })
    return videos

def get_video_stats(video_ids):
    """Get view counts and durations for a batch of videos."""
    ids = ",".join(video_ids)
    url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics,contentDetails&id={ids}&key={API_KEY}"
    data = api_request(url)
    stats = {}
    if "items" not in data:
        return stats
    for item in data["items"]:
        vid = item["id"]
        stat = item.get("statistics", {})
        content = item.get("contentDetails", {})
        duration = content.get("duration", "PT0S")
        stats[vid] = {
            "viewCount": int(stat.get("viewCount", 0)),
            "likeCount": int(stat.get("likeCount", 0)),
            "duration": duration,
        }
    return stats

def parse_duration(duration_str):
    """Convert ISO 8601 duration to human-readable format."""
    import re
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return "0:00"
    h, m, s = [int(x) if x else 0 for x in match.groups()]
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    else:
        return f"{m}:{s:02d}"

def main():
    import datetime
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    all_videos = []
    
    for channel_name in CHANNELS:
        print(f"Fetching channel: {channel_name}...")
        channel_id, display_name = get_channel_info(channel_name)
        if not channel_id:
            continue
        
        print(f"  Channel ID: {channel_id} ({display_name})")
        playlist_id = get_uploads_playlist(channel_id)
        if not playlist_id:
            print(f"  [WARN] No uploads playlist for {channel_name}")
            continue
        
        videos = get_playlist_videos(playlist_id)
        if not videos:
            print(f"  [WARN] No videos found for {channel_name}")
            continue
        
        # Get stats for all videos
        video_ids = [v["videoId"] for v in videos]
        stats = get_video_stats(video_ids)
        
        for v in videos:
            vid = v["videoId"]
            stat = stats.get(vid, {"viewCount": 0, "likeCount": 0, "duration": "PT0S"})
            v["viewCount"] = stat["viewCount"]
            v["likeCount"] = stat["likeCount"]
            v["duration"] = parse_duration(stat["duration"])
            # 跳过超过 30 天的视频
            published = datetime.datetime.fromisoformat(v["publishedAt"].replace("Z", "+00:00"))
            if published >= cutoff:
                all_videos.append(v)
        
        print(f"  Fetched {len(videos)} videos")
        time.sleep(0.5)  # Rate limiting
    
    # Sort by view count descending
    all_videos.sort(key=lambda x: x["viewCount"], reverse=True)
    
    # Save to JSON
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos.json")
    with open(output_path, "w") as f:
        json.dump(all_videos, f, indent=2)
    
    print(f"\nDone! Saved {len(all_videos)} videos to videos.json")

if __name__ == "__main__":
    main()
