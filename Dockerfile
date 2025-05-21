# Gmail Digest Assistant Dockerfile (v0.7 Beta)
#
# Build:   docker build -t gmaildigest:0.7 .
# Run:     docker run -it --rm -v ~/gmaildigest-config/.env:/app/.env -v ~/gmaildigest-config/credentials.json:/app/credentials.json gmaildigest:0.7
#
# Note: The setup GUI (setup_config.py) is not supported in Docker. Run it on your host to generate .env and credentials.json first.

FROM python:3.10-slim

# Install system dependencies for cryptography, sumy, and Tkinter
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libssl-dev \
        tk \
        libxml2-dev \
        libxslt1-dev \
        && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . .

# Download NLTK punkt data (after nltk is installed)
RUN python -c "import nltk; nltk.download('punkt')"

# Default command: run the main app
CMD ["python", "gmaildigest.py"] 