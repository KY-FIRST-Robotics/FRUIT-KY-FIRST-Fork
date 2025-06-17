from google_auth_oauthlib.flow import InstalledAppFlow

# Define the required scopes for YouTube API
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

# Load the client secrets file
flow = InstalledAppFlow.from_client_secrets_file(
    "client_secrets.json", SCOPES
)

# Run the local server to authenticate
credentials = flow.run_local_server(port=8080, prompt="consent")

# Print the refresh token
print("Access Token:", credentials.token)
print("Refresh Token:", credentials.refresh_token)