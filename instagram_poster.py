import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import mimetypes

load_dotenv()

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
APP_ID = os.getenv("META_APP_ID")
APP_SECRET = os.getenv("META_APP_SECRET")
BASE_URL = "https://graph.facebook.com/v19.0"

supabase_client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def upload_image_to_supabase(local_path: str) -> str:
    """Upload a local image to Supabase Storage and return public URL."""
    path = Path(local_path)
    file_name = f"posts/{int(time.time())}_{path.name}"
    mime_type = mimetypes.guess_type(local_path)[0] or "image/jpeg"

    with open(local_path, "rb") as f:
        supabase_client.storage.from_("media").upload(
            file_name,
            f.read(),
            {"content-type": mime_type}
        )

    # Build public URL
    public_url = (
        f"{os.getenv('SUPABASE_URL')}/storage/v1/object/public/media/{file_name}"
    )
    print(f"✅ Image uploaded: {public_url}")
    return public_url

def get_instagram_account_id() -> str:
    """Get your Instagram Business Account ID."""
    # First get your Facebook Page ID
    url = f"{BASE_URL}/me/accounts"
    params = {"access_token": ACCESS_TOKEN}
    res = requests.get(url, params=params)
    res.raise_for_status()
    pages = res.json().get("data", [])

    if not pages:
        raise ValueError(
            "No Facebook Pages found. Make sure your account has a Page."
        )

    page = pages[0]  # use first page
    page_id = page["id"]
    page_token = page["access_token"]

    # Get Instagram account connected to this Page
    url = f"{BASE_URL}/{page_id}"
    params = {
        "fields": "instagram_business_account",
        "access_token": page_token
    }
    res = requests.get(url, params=params)
    res.raise_for_status()
    data = res.json()

    ig_account = data.get("instagram_business_account")
    if not ig_account:
        raise ValueError(
            "No Instagram Business account connected to this Page. "
            "Go to Instagram Settings → Switch to Professional Account → "
            "Connect to your Facebook Page."
        )

    print(f"✅ Instagram Account ID: {ig_account['id']}")
    return ig_account["id"]

def post_image_to_instagram(
    image_url: str,
    caption: str,
    ig_account_id: str = None
) -> dict:
    """
    Post an image to Instagram.

    IMPORTANT: image_url must be a publicly accessible URL.
    Instagram's API downloads the image from this URL — local file paths don't work.

    Args:
        image_url: Public URL of the image to post
        caption: Post caption (hashtags go here too)
        ig_account_id: Instagram Business Account ID

    Returns:
        dict with post_id and permalink
    """
    if not ig_account_id:
        ig_account_id = get_instagram_account_id()

    print(f"📸 Creating media container...")
    print(f"   Image: {image_url[:60]}...")
    print(f"   Caption: {caption[:50]}...")

    # Step 1: Create media container
    container_url = f"{BASE_URL}/{ig_account_id}/media"
    container_params = {
        "image_url": image_url,
        "caption": caption,
        "access_token": ACCESS_TOKEN
    }
    res = requests.post(container_url, data=container_params)
    res.raise_for_status()
    container_id = res.json()["id"]
    print(f"   Container ID: {container_id}")

    # Step 2: Wait for container to process (Instagram needs a moment)
    print(f"⏳ Waiting 5 seconds for container to process...")
    time.sleep(5)

    # Step 3: Check container status
    status_url = f"{BASE_URL}/{container_id}"
    status_params = {
        "fields": "status_code,status",
        "access_token": ACCESS_TOKEN
    }
    status_res = requests.get(status_url, params=status_params)
    status_data = status_res.json()
    print(f"   Status: {status_data.get('status_code', 'unknown')}")

    # Step 4: Publish the container
    print(f"🚀 Publishing to Instagram...")
    publish_url = f"{BASE_URL}/{ig_account_id}/media_publish"
    publish_params = {
        "creation_id": container_id,
        "access_token": ACCESS_TOKEN
    }
    pub_res = requests.post(publish_url, data=publish_params)
    pub_res.raise_for_status()
    post_id = pub_res.json()["id"]

    # Step 5: Get the permalink
    permalink_url = f"{BASE_URL}/{post_id}"
    permalink_params = {
        "fields": "permalink,timestamp",
        "access_token": ACCESS_TOKEN
    }
    permalink_res = requests.get(permalink_url, params=permalink_params)
    permalink_data = permalink_res.json()

    result = {
        "post_id": post_id,
        "permalink": permalink_data.get("permalink", ""),
        "timestamp": permalink_data.get("timestamp", ""),
        "caption": caption[:50] + "..."
    }

    print(f"✅ Posted successfully!")
    print(f"   Post ID: {post_id}")
    print(f"   URL: {result['permalink']}")
    return result

def refresh_long_lived_token() -> str:
    """Refresh a long-lived token before it expires (do this every 45 days)."""
    url = f"{BASE_URL}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": ACCESS_TOKEN
    }
    res = requests.get(url, params=params)
    res.raise_for_status()
    new_token = res.json()["access_token"]
    print(f"✅ Token refreshed. New token: {new_token[:20]}...")
    return new_token

if __name__ == "__main__":
    # First run: get your Instagram Account ID
    ig_id = get_instagram_account_id()
    print(f"\nSave this ID: {ig_id}")
    print("Add to .env as: INSTAGRAM_ACCOUNT_ID=" + ig_id)