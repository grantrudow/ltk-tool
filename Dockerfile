FROM joyzoursky/python-chromedriver:3.9-selenium

# Install additional dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    xvfb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port 
EXPOSE 8000

# Set up environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DISPLAY=:99 \
    SELENIUM_HEADLESS=1 \
    PYTHONPATH=/app

# Create a wrapper script to start Xvfb and then run the app
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1280x1024x24 &\nsleep 1\nuvicorn backend.main:app --host 0.0.0.0 --port 8000' > /usr/local/bin/start.sh \
    && chmod +x /usr/local/bin/start.sh

# Command to run the application
CMD ["/usr/local/bin/start.sh"]