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
scopes = ["https://www.googleapis.com/auth/youtube.readonly"]


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

        self.client_secrets_path = client_secrets_path
        if not self.client_secrets_path:
            raise ValueError("CLIENT_SECRET_PATH must point to a Google client secrets JSON file")

        self.token_path = token_path
        self.credentials = self._authenticate()
        self.youtube = googleapiclient.discovery.build("youtube", "v3", credentials=self.credentials)
        self.youtube_analytics = googleapiclient.discovery.build("youtubeAnalytics", "v2", credentials=self.credentials)

    def _authenticate(self):
        api_service_name = "youtube"
        api_version = "v3"

        # Get credentials and create an API client
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            self.client_secrets_path, scopes)
        credentials = flow.run_local_server(port=0)
        
        return cred

    def _save_credentials(self, credentials: Credentials) -> None:
        with open(self.token_path, "w", encoding="utf-8") as handle:
            json.dump(json.loads(credentials.to_json()), handle, indent=2)

    def _execute_with_retry(self, request: Any) -> dict[str, Any]:
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
        channel_item = self._get_channel_item()
        return self._normalize_channel_payload({"items": [channel_item]})

    @staticmethod
    def _rows_to_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows)


def main() -> None:
    connector = YouTubeConnector()
    print(connector.get_channel_statistics())

if __name__ == "__main__":
    main()

