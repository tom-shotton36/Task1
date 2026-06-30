# Task1
YoutubeConnector API using OAuth

Step 1
a) Setting up project in Google Cloud
Go to https://developers.google.com/youtube/v3/quickstart/python#step_3_run_an_authorized_request
follow through Step 1.1
Create a project
Enable the Project's Youtube API in Google Cloud Console
Then create a client secret and download the credential in JSON
*add your computer to the test user list so it will be given access to this project

b) Getting the skeleton code to use Youtube Data API
follow through 1.2b OAuth 2.0 

go to https://developers.google.com/youtube/v3/docs/channels/list
pick "list(my channel)" and then click on Python in the API explorer
Then copy the skeleton code and replace the STANDIN data with your own environment variable. 
Adjust your program as to how you want your program's output to be

c) Create a .env file and add
CLIENT_SECRET_PATH = "./client_secret...xyz.json" -- the one you downloaded in step 1
TOKEN_PATH = "./xyz.json" -- where and what name you want to store your token as. 

Step 2 
run "python3 class_func.py"
you will be prompted to give consent for access to the project. 
Then you should see a output of your channel's statistics 

e.g. 
            0  1  2  3  4
0  2026-06-20  0  0  0  0
1  2026-06-21  0  0  0  0
2  2026-06-22  0  0  0  0
3  2026-06-23  0  0  0  0
4  2026-06-24  0  0  0  0
5  2026-06-25  0  6  1  0
6  2026-06-26  0  0  0  0
7  2026-06-27  0  0  0  0
   view_count  like_count  dislike_count  comment_count
0           6           1              0              0

and then your token stored in the format like the following
e.g.
{
  "token": "ya29.a0A.....................................................PQ0206",
  "refresh_token": "1//.......................................U6NzeOV7QnxQOAQA0g",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "8183xxxxxx..............it.apps.googleusercontent.com",
  "client_secret": "GOxxxxxx........hV3",
  "scopes": [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly"
  ],
  "universe_domain": "googleapis.com",
  "account": "",
  "expiry": "YYYY-MM-DDThh:mm:ssZ"
}