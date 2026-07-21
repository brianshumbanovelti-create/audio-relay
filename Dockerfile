FROM python:3.11-slim

# ffmpeg for transcoding, curl for fetching the standalone yt-dlp binary
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install yt-dlp as a standalone binary (kept up to date independent of pip)
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY static ./static

ENV PORT=8080
EXPOSE 8080

CMD ["python", "app.py"]
