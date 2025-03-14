# main.py
import os
import shutil
import tempfile
import sys
from typing import List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import uuid
import logging
import asyncio
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fix the import path - add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)  # Go up one level if necessary
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Import your existing download script
try:
    # Try both import paths to be safe
    try:
        from backend.download_script.ltk_network_capture import capture_video_urls
        from backend.download_script.ltk_m3u8_downloader import download_m3u8_to_mp4
        from backend.download_script.download_video_from_url import download_video_from_url
        logger.info("Successfully imported download scripts using 'backend.' prefix")
    except ImportError:
        from download_script.ltk_network_capture import capture_video_urls
        from download_script.ltk_m3u8_downloader import download_m3u8_to_mp4
        from download_script.download_video_from_url import download_video_from_url
        logger.info("Successfully imported download scripts without prefix")
except ImportError as e:
    logger.error(f"Error importing download scripts: {e}")
    # Define placeholder functions if imports fail
    def capture_video_urls(url, timeout=30):
        logger.warning("Using placeholder capture_video_urls function")
        return ["http://example.com/test.m3u8"]
        
    def download_m3u8_to_mp4(m3u8_url, output_file):
        logger.warning("Using placeholder download_m3u8_to_mp4 function")
        # Create a dummy file
        with open(output_file, "w") as f:
            f.write(f"Dummy video file for {m3u8_url}")
        return True
        
    def download_video_from_url(video_url, output_dir, max_items=10):
        logger.warning("Using placeholder download_video_from_url function")
        # Create a dummy file
        os.makedirs(output_dir, exist_ok=True)
        dummy_file = os.path.join(output_dir, "dummy_video.mp4")
        with open(dummy_file, "w") as f:
            f.write(f"Dummy video file for {video_url}")
        # Note: The real function doesn't return anything

# Actual download function that will be used
async def download_media(url: str, count: int, target_dir: str, url_type: str = "profile") -> List[str]:
    """
    Download media from the given URL and save to target_dir.
    
    Args:
        url: The URL to download from
        count: Maximum number of items to download
        target_dir: Directory to save downloaded files
        url_type: Type of URL - "profile" or "post"
    
    Returns:
        List of downloaded file paths
    """
    logger.info(f"Starting download from {url} with count {count} to {target_dir}, URL type: {url_type}")
    
    # Create target directory if it doesn't exist
    os.makedirs(target_dir, exist_ok=True)
    
    try:
        if url_type == "post":
            # For direct post URLs, we only download the first media item
            logger.info(f"Processing direct post URL: {url}")
            # Use the download_video_from_url function with is_direct_post=True
            download_video_from_url(url, target_dir, max_items=1, is_direct_post=True)
        else:
            # For profile URLs, use the existing bulk download functionality
            logger.info(f"Using download_video_from_url to download from profile {url} with max_items={count}")
            download_video_from_url(url, target_dir, max_items=count)
        
        # Get a list of all downloaded files
        downloaded_files = []
        for file in os.listdir(target_dir):
            file_path = os.path.join(target_dir, file)
            if os.path.isfile(file_path):
                downloaded_files.append(file_path)
        
        logger.info(f"Found {len(downloaded_files)} downloaded files")
        
        # Limit the number of files based on count (this is now redundant but kept for safety)
        if len(downloaded_files) > count:
            logger.info(f"Limiting to {count} files as requested")
            downloaded_files = downloaded_files[:count]
        
        return downloaded_files
    except Exception as e:
        logger.error(f"Error downloading media: {e}")
        raise

app = FastAPI(title="Media Downloader API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],  # Add your frontend URL and allow all for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DownloadRequest(BaseModel):
    url: HttpUrl
    count: int = 10  # Default to 10 items
    urlType: str = "profile"  # Default to profile URL, can be "profile" or "post"

class DownloadResponse(BaseModel):
    task_id: str
    message: str

# Store download tasks
download_tasks = {}

@app.post("/api/download", response_model=DownloadResponse)
async def start_download(request: DownloadRequest, background_tasks: BackgroundTasks):
    """
    Start a download task in the background
    """
    # Generate a unique task ID
    task_id = str(uuid.uuid4())
    
    # Create a temporary directory for this task
    temp_dir = os.path.join(tempfile.gettempdir(), f"ltk_download_{task_id}")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Store task info
    download_tasks[task_id] = {
        "status": "processing",
        "url": str(request.url),
        "count": request.count,
        "urlType": request.urlType,
        "temp_dir": temp_dir,
        "start_time": time.time(),
        "download_path": None
    }
    
    # Start the download process in the background
    background_tasks.add_task(
        process_download, 
        task_id=task_id, 
        url=str(request.url), 
        count=request.count,
        temp_dir=temp_dir,
        url_type=request.urlType
    )
    
    return {"task_id": task_id, "message": "Download started"}

async def process_download(task_id: str, url: str, count: int, temp_dir: str, url_type: str = "profile"):
    """
    Process a download task in the background
    """
    try:
        logger.info(f"Processing download task {task_id} for URL: {url}")
        
        # Update task status
        download_tasks[task_id]["status"] = "downloading"
        
        # Download the media
        downloaded_files = await download_media(url, count, temp_dir, url_type)
        
        if not downloaded_files or len(downloaded_files) == 0:
            logger.warning(f"No files were downloaded for task {task_id}")
            download_tasks[task_id]["status"] = "failed"
            download_tasks[task_id]["error"] = "No files were downloaded"
            return
        
        # Create a zip file of all downloaded files
        zip_path = os.path.join(tempfile.gettempdir(), f"ltk_download_{task_id}.zip")
        
        # Create the zip file
        shutil.make_archive(
            os.path.splitext(zip_path)[0],  # Remove .zip extension for make_archive
            'zip',
            temp_dir
        )
        
        # Update task status
        download_tasks[task_id]["status"] = "completed"
        download_tasks[task_id]["download_path"] = zip_path
        
        logger.info(f"Download task {task_id} completed successfully")
    except Exception as e:
        logger.error(f"Error processing download task {task_id}: {e}")
        download_tasks[task_id]["status"] = "failed"
        download_tasks[task_id]["error"] = str(e)

@app.get("/api/download/{task_id}/status")
async def check_download_status(task_id: str):
    """Check the status of a download task"""
    logger.info(f"Checking status for task {task_id}")
    if task_id not in download_tasks:
        logger.warning(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"status": download_tasks[task_id]["status"]}

@app.get("/api/download/{task_id}")
async def get_download(task_id: str):
    """Get the downloaded zip file"""
    logger.info(f"Download request for task {task_id}")
    if task_id not in download_tasks:
        logger.warning(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = download_tasks[task_id]
    
    if task["status"] != "completed":
        logger.warning(f"Download not ready for task {task_id}. Status: {task['status']}")
        raise HTTPException(
            status_code=400, 
            detail=f"Download not ready. Current status: {task['status']}"
        )
    
    zip_path = task["download_path"]
    logger.info(f"Serving zip file from {zip_path}")
    
    # Schedule cleanup for after the file is served
    # (not removing right away to allow the file to be downloaded)
    def cleanup():
        try:
            # Check if the task still exists in the dictionary
            if task_id in download_tasks:
                # Check if the zip file exists before trying to delete it
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                    logger.info(f"Deleted zip file: {zip_path}")
                else:
                    logger.info(f"Zip file already deleted: {zip_path}")
                
                # Check if the directory exists before trying to delete it
                if os.path.exists(task["temp_dir"]):
                    shutil.rmtree(task["temp_dir"], ignore_errors=True)
                    logger.info(f"Deleted directory: {task['temp_dir']}")
                else:
                    logger.info(f"Directory already deleted: {task['temp_dir']}")
                
                # Remove the task from the dictionary
                download_tasks.pop(task_id, None)
                logger.info(f"Cleaned up resources for task {task_id}")
            else:
                logger.info(f"Task {task_id} already cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup for task {task_id}: {e}")
    
    background_tasks = BackgroundTasks()
    background_tasks.add_task(cleanup)
    
    return FileResponse(
        zip_path, 
        media_type="application/zip",
        filename="downloaded_media.zip",
        background=background_tasks
    )

# Add a simple root endpoint for health check
@app.get("/")
def read_root():
    return {"message": "Media Downloader API is running"}

@app.get("/api/health")
def health_check():
    """Health check endpoint for Docker healthcheck"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Media Downloader API server")
    uvicorn.run(app, host="0.0.0.0", port=8000)