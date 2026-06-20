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

API_KEY = "REDACTED_KEY"
CHANNELS = ["garytalksstuff", "openai", "aliabdaal"]
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
