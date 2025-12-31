from datetime import datetime, timedelta, timezone
from typing import List, Optional
import os
import sys
from pydantic import BaseModel
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ChannelVideo(BaseModel):
    title: str
    url: str
    video_id: str
    published_at: datetime
    description: str


class YouTubeScraper:
    def __init__(self):
        # Initialize YouTube Data API v3 client (required)
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            raise ValueError("YOUTUBE_API_KEY environment variable is required. ")
        
        try:
            self.youtube_service = build('youtube', 'v3', developerKey=api_key)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize YouTube API client: {e}")

    def _extract_video_id(self, video_url: str) -> str:
        if "youtube.com/watch?v=" in video_url:
            return video_url.split("v=")[1].split("&")[0]
        if "youtube.com/shorts/" in video_url:
            return video_url.split("shorts/")[1].split("?")[0]
        if "youtu.be/" in video_url:
            return video_url.split("youtu.be/")[1].split("?")[0]
        return video_url

    def get_latest_videos(self, channel_id: str, hours: int = 24) -> list[ChannelVideo]:
        """Get latest videos using YouTube Data API v3"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        videos = []
        
        # Step 1: Get the channel's uploads playlist ID
        channel_response = self.youtube_service.channels().list(
            part='contentDetails',
            id=channel_id
        ).execute()
        
        if not channel_response.get('items'):
            return []
        
        uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Step 2: Get videos from the uploads playlist
        # We'll paginate through results until we find videos older than cutoff_time
        next_page_token = None
        max_results = 50  # Maximum allowed by API
        
        while True:
            playlist_params = {
                'part': 'snippet',
                'playlistId': uploads_playlist_id,
                'maxResults': min(max_results, 50),
            }
            if next_page_token:
                playlist_params['pageToken'] = next_page_token
            
            playlist_response = self.youtube_service.playlistItems().list(**playlist_params).execute()
            
            for item in playlist_response.get('items', []):
                snippet = item['snippet']
                video_id = snippet['resourceId']['videoId']
                
                # Parse published time
                published_str = snippet['publishedAt']
                # Convert ISO 8601 format to datetime
                published_time = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                
                # Stop if we've gone past the cutoff time
                if published_time < cutoff_time:
                    return videos
                
                videos.append(
                    ChannelVideo(
                        title=snippet.get('title', ''),
                        url=f"https://www.youtube.com/watch?v={video_id}",
                        video_id=video_id,
                        published_at=published_time,
                        description=snippet.get('description', ''),
                    )
                )
            
            # Check if there are more pages
            next_page_token = playlist_response.get('nextPageToken')
            if not next_page_token:
                break
            
            # Safety check: if we've collected a reasonable number, stop
            if len(videos) >= 200:
                break
        
        return videos

    def scrape_channel(self, channel_id: str, hours: int = 150) -> list[ChannelVideo]:
        """Get latest videos from a channel (alias for get_latest_videos)"""
        return self.get_latest_videos(channel_id, hours)