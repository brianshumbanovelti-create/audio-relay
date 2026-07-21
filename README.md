# Low-Data Live Audio Relay

A one-page tool that takes any YouTube live stream and re-serves it to your
phone as 32kbps audio — a fraction of the data a normal video stream uses.

You paste a YouTube link into a web page, tap **Go**, then **Play**/**Stop**
to control it. Everything happens on a free server; your phone only ever
downloads the small 32kbps audio.

---

## Part 1 — Put this project on GitHub

1. Go to [github.com](https://github.com) and log in (same as your HTML page project).
2. Tap **New repository** (the **+** icon, top right).
3. Name it something like `audio-relay`. Keep it **Public**. Don't add a README from GitHub's own template — you'll upload these files instead.
4. Tap **Create repository**.
5. On the new empty repo page, tap **uploading an existing file** (or **Add file → Upload files**).
6. Upload these 5 files/folders exactly as they are, keeping the same names:
   - `Dockerfile`
   - `app.py`
   - `requirements.txt`
   - `fly.toml`
   - `static/index.html` (make sure this ends up inside a folder called `static` — GitHub's uploader will do this automatically if you drag the whole `static` folder in, or you may need to create the folder first by naming a file `static/index.html` when uploading)
7. Tap **Commit changes**.

You should now see all 5 items in your repo's file list.

---

## Part 2 — Create your Fly.io account (no card needed)

1. Go to [fly.io](https://fly.io) in your phone browser.
2. Tap **Sign Up**.
3. Choose **Sign up with GitHub** — this is the easiest option since you already have GitHub, and it lets Fly.io see your repos in the next step.
4. Approve the GitHub permission prompt.

---

## Part 3 — Deploy from the Fly.io dashboard (no typing commands)

1. Once logged in, go to your Fly.io **Dashboard**.
2. Look for a **Launch App** or **Create App** button.
3. Choose **Launch from GitHub** (or similarly worded "Deploy from a repository" option).
4. If asked, grant Fly.io access to your GitHub repositories.
5. Select the `audio-relay` repo you just created.
6. Fly.io will detect the `Dockerfile` and `fly.toml` automatically.
7. When asked to pick a region, choose the one closest to Zimbabwe available on the free tier (Johannesburg — `jnb` — is already set in `fly.toml`; if it's not offered, Cape Town or a nearby European region is the next best).
8. Confirm / Launch. Fly.io will build and deploy — this takes a few minutes the first time.
9. Once deployed, Fly.io will show you your app's URL, something like:
   `https://audio-relay-morning-frost-1234.fly.dev`

**Bookmark that URL on your phone** — that's your fixed control page link, the same one every time.

---

## Part 4 — Using it

1. Open your bookmarked link.
2. Paste a YouTube **live** video URL into the box.
3. Tap **Go** — wait a few seconds while it connects.
4. Tap **Play** to start listening.
5. When you're done, tap **Stop** — this shuts the relay down completely so it's not left running.

---

## If something goes wrong

- **"Could not start the relay" error**: the YouTube link might not be a live stream, or might be private/region-locked. Try a different link to confirm the tool itself works.
- **Long delay before audio starts**: normal — yt-dlp has to look up the stream first, this can take 5-15 seconds.
- **It stops working after a while**: check the Fly.io dashboard's **Logs** or **Metrics** tab for your app — if you see memory or crash errors, let me know exactly what they say and we'll adjust.
- **Free tier limits**: Fly.io's free allowance is usage-based. A few 3-4 hour sessions a week should comfortably fit, but if you start using it daily for many hours, check Fly.io's current free tier limits on their pricing page.

---

## What's actually happening technically (optional reading)

- `yt-dlp` finds YouTube's own audio-only stream track for the video you paste in.
- `ffmpeg` re-encodes that down to 32kbps mono MP3.
- Your phone connects to `/stream.mp3` on your Fly.io app and receives only that small 32kbps stream — the full-size download from YouTube happens on Fly.io's server, not on your data plan.
