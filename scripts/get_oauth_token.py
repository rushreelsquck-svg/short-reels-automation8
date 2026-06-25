"""
get_oauth_token.py
RUN THIS ONCE ON YOUR OWN COMPUTER (not in GitHub Actions — it needs to open
a browser for you to log in and approve access).

It prints a refresh token at the end. Copy that into your GitHub repo's
Settings -> Secrets -> Actions as YT_REFRESH_TOKEN. Never commit it to the repo.

Before running, fill in YT_CLIENT_ID / YT_CLIENT_SECRET below or as env vars
(see README "Step 1: Google Cloud setup").
"""
import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    client_config = {
        "installed": {
            "client_id": os.environ["YT_CLIENT_ID"],
            "client_secret": os.environ["YT_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    # This opens your browser. Log in with the Google account that owns the
    # YouTube channel, and click through the "unverified app" warning if you
    # see one — that's expected for a personal-use app you created yourself.
    credentials = flow.run_local_server(port=0)

    print("\n=== SUCCESS ===")
    print("Add this as the GitHub secret YT_REFRESH_TOKEN:\n")
    print(credentials.refresh_token)
    print("\n(Keep this private — anyone with it can upload videos to your channel.)")


if __name__ == "__main__":
    main()
