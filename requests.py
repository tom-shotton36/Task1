#!/usr/bin/python
"""
Connector class for Youtube API requests

"""
from __future__ import print_function

from googleapiclient.errors import HttpError
from googleapiclient import sample_tools
from oauth2client.client import AccessTokenRefreshError


class YoutubeConnector():
