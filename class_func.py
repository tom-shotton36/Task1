#!/usr/bin/python
"""Connector helpers for YouTube Data and Analytics API requests."""

import os
import json
from typing import Any

import pandas as pd
from dotenv import load_dotenv
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

load_dotenv()

DATA_API_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
ANALYTICS_SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly"]
ALL_SCOPES = DATA_API_SCOPES + ANALYTICS_SCOPES


class YouTubeApiError(Exception):
    """Base exception for connector failures."""


class QuotaExceededError(YouTubeApiError):
    """Raised when the YouTube API rejects a request with HTTP 403 quota errors."""


class TokenRefreshError(YouTubeApiError):
    """Raised when an OAuth token cannot be refreshed."""


class YouTubeConnector:
    def __init__(self, client_secrets_path: str | None = None, token_path: str | None = None):
        # this is pretty sketch ill have to talk to Thomas about this. 
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
        load_dotenv()

        self.client_secrets_path = client_secrets_path or os.getenv("CLIENT_SECRET_PATH")
        if not self.client_secrets_path:
            raise ValueError("CLIENT_SECRET_PATH must point to a Google client secrets JSON file")

        self.token_path = token_path or os.getenv("TOKEN_PATH")
        self.credentials = self._authenticate()
        self.youtube = googleapiclient.discovery.build("youtube", "v3", credentials=self.credentials)
        self.youtube_analytics = googleapiclient.discovery.build("youtubeAnalytics", "v2", credentials=self.credentials)

        self._save_credentials(self.credentials)

    def _authenticate(self):
        """
        Authenticate both APIs and return the credentials. If a token file exists, we load to avoid re-auth, 
        and if it is expired we refresh it.
        """
        api_service_name = "youtube"
        api_version = "v3"
        credentials = None

        if self.token_path and os.path.exists(self.token_path):
            with open(self.token_path, "r", encoding="utf-8") as handle:
                token_data = json.load(handle)
                credentials = Credentials.from_authorized_user_info(token_data, ALL_SCOPES)
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                self._save_credentials(credentials)
            except Exception as exc:
                raise TokenRefreshError(f"Token refresh failed: {exc}") from exc
        if not credentials or not credentials.valid:
            # Get credentials and create an API client
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                self.client_secrets_path, ALL_SCOPES)
            credentials = flow.run_local_server(port=0)
            self._save_credentials(credentials)
        
        return credentials 

    def _save_credentials(self, credentials: Credentials) -> None:
        """
        Save the credentials to the token path.
        """
        with open(self.token_path, "w", encoding="utf-8") as handle:
            json.dump(json.loads(credentials.to_json()), handle, indent=2)

    def _execute_with_retry(self, request: Any) -> dict[str, Any]:
        """
        Execute a YouTube API request with retry logic for token refresh and quota errors.
        """
        try:
            return request.execute()
        except googleapiclient.errors.HttpError as exc:
            status_code = getattr(exc.resp, "status", None)
            if status_code == 401:
                try:
                    self.credentials.refresh(Request())
                    self._save_credentials(self.credentials)
                except Exception as exc2:
                    raise TokenRefreshError(f"Token refresh failed after 401 response: {exc2}") from exc2
                return request.execute()
            if status_code == 403:
                raise QuotaExceededError(
                    f"YouTube API quota exceeded or request blocked: {exc}") from exc
            raise YouTubeApiError(f"YouTube API request failed: {exc}") from exc

    def _get_channel_item(self) -> dict[str, Any]:
        request = self.youtube.channels().list(part="snippet,contentDetails,statistics", mine=True)
        response = self._execute_with_retry(request)
        items = response.get("items", [])
        if not items:
            raise YouTubeApiError("No channel data was returned by the YouTube API")
        return items[0]

    def get_channel_statistics(self) -> dict[str, Any]:
        """
        Returns a dictionary with the basic statistics for the authenticated user's channel.
        """
        channel_item = self._get_channel_item()
        stats = channel_item.get("statistics", {})
        # make dataframe, obviously just a single row
        channel = {
            "view_count": int(stats.get("viewCount", 0)),
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
        }

        return pd.DataFrame(channel, index=[0])
    
    def get_recent_video_stats(self, max_results: int = 5):
        """
        Simple function to return the basic stats for the most recent videos on a channel.
        """
        channel_item = self._get_channel_item()
        uploads_playlist_id = (
            channel_item["contentDetails"]["relatedPlaylists"]["uploads"]
        )

        # Get recent video IDs
        request = self.youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=max_results,
        )
        response = self._execute_with_retry(request)
        video_ids = [
            item["snippet"]["resourceId"]["videoId"]
            for item in response.get("items", [])
        ]
        request = self.youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids),
        )
        response = self._execute_with_retry(request)
        rows = []

        # before I was going to build out a Dataframe-iser to make this more generic, but its not a big enough class. 
        for item in response.get("items", []):
            stats = item.get("statistics", {})
            rows.append({
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "dislike_count": int(stats.get("dislikeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
            })

        return pd.DataFrame(rows)
    
    def get_timeseries_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Returns info about a channels performance over a given time range. Could be used to plot a graph of performance over time.
        """
        request = self.youtube_analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics= 'estimatedMinutesWatched,views,likes,subscribersGained',
            dimensions='day',
            sort='day'
        )

        response = self._execute_with_retry(request)
        rows = response.get("rows", [])
        return pd.DataFrame(rows)


def main() -> None:
    connector = YouTubeConnector()
    print(connector.get_channel_statistics())
    print(connector.get_timeseries_data("2026-06-20", "2026-06-28"))
    print(connector.get_recent_video_stats(max_results=5))

if __name__ == "__main__":
    main()

