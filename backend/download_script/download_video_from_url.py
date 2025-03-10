import requests
import os
import time
import re
import base64
import subprocess
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import the other modules
try:
    from . import ltk_network_capture
    from . import ltk_m3u8_downloader
    MODULES_IMPORTED = True
except ImportError:
    MODULES_IMPORTED = False
    print("Warning: ltk_network_capture.py or ltk_m3u8_downloader.py not found in the current directory.")
    print("Video downloading will be limited to direct downloads only.")

def download_video_from_url(video_url, output_dir="downloaded_videos", max_items=10):
    """
    Script to download a video from a page containing a video tag,
    including support for blob URLs
    
    Args:
        video_url (str): URL to a page containing a video
        output_dir (str): Directory to save videos
        max_items (int): Maximum number of items to download (default: 10)
    """
    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Setup Chrome
    chrome_options = Options()
    # Uncomment to run in background
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Navigate to the video page
        print(f"Opening URL: {video_url}")
        driver.get(video_url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Process each post/item on the page
        post_items = driver.find_elements(By.CSS_SELECTOR, "[data-test-id='post-feed-item/card']")
        print(f"Found {len(post_items)} post items on the page")
        
        # Skip the first 2 items as requested
        if len(post_items) > 2:
            print("Skipping the first 2 media items as requested")
            post_items = post_items[2:]
            print(f"Processing {len(post_items)} remaining items")
        else:
            print("Warning: Less than 3 items found, processing all available items")
        
        # Limit the number of items to process based on max_items
        if len(post_items) > max_items:
            print(f"Limiting to {max_items} items as requested")
            post_items = post_items[:max_items]
            print(f"Processing {len(post_items)} items")
        
        image_count = 0
        video_count = 0
        
        for i, post in enumerate(post_items):
            try:
                print(f"\n{'='*50}")
                print(f"DEBUGGING POST #{i+3}")  # +3 because we skipped 2
                print(f"{'='*50}")
                
                # Debug: Print the HTML structure of the post
                post_html = post.get_attribute('outerHTML')
                print(f"Post HTML snippet (first 200 chars): {post_html[:200]}...")
                
                # Debug: Check for all buttons in the post
                all_buttons = post.find_elements(By.TAG_NAME, "button")
                print(f"Found {len(all_buttons)} buttons in post")
                for j, btn in enumerate(all_buttons):
                    btn_class = btn.get_attribute("class")
                    print(f"  Button #{j+1} class: {btn_class}")
                
                # Debug: Check for elements with 'play' in their class or id
                play_elements = post.find_elements(By.CSS_SELECTOR, "[class*='play'], [id*='play']")
                print(f"Found {len(play_elements)} elements with 'play' in class/id")
                for j, elem in enumerate(play_elements):
                    elem_tag = elem.tag_name
                    elem_class = elem.get_attribute("class")
                    print(f"  Play element #{j+1}: Tag={elem_tag}, Class={elem_class}")
                
                # More specific check for play buttons
                play_button = post.find_elements(By.CSS_SELECTOR, "button.play-icon, button.v-btn--fab i.capsule-consumer-play-outline-16")
                
                if play_button:
                    print(f"Post #{i+3}: Found specific play button. Processing as video.")
                    video_count += 1
                    process_video_post(driver, post, output_dir, video_url, i)
                else:
                    print(f"Post #{i+3}: No play button found. Processing as image.")
                    image_count += 1
                    process_image_post(driver, post, output_dir, video_url, i)
            except Exception as e:
                print(f"Error processing post #{i+3}: {e}")
        
        print(f"Processing complete. Found {image_count} images and {video_count} videos.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

def process_video_post(driver, post_element, output_dir, referer_url, index):
    """Process and download video content from a post"""
    try:
        # First try to get the post URL to navigate to the individual post page
        post_url = post_element.get_attribute("href")
        if post_url and not post_url.startswith("http"):
            # Handle relative URLs
            base_url = "/".join(referer_url.split("/")[:3])  # Get domain part
            post_url = base_url + post_url
        
        if post_url:
            print(f"Navigating to individual post: {post_url}")
            
            # If we have the ltk_network_capture module, use it to get the M3U8 URL
            if MODULES_IMPORTED:
                try:
                    print("Using ltk_network_capture to get M3U8 URL...")
                    m3u8_urls = ltk_network_capture.capture_video_urls(post_url)
                    
                    if m3u8_urls:
                        print(f"Found {len(m3u8_urls)} M3U8 URLs")
                        for i, m3u8_url in enumerate(m3u8_urls):
                            print(f"Processing M3U8 URL #{i+1}: {m3u8_url}")
                            output_file = os.path.join(output_dir, f"video_{index}_{i}.mp4")
                            
                            # Use ltk_m3u8_downloader to download the video
                            print(f"Downloading video using ltk_m3u8_downloader...")
                            ltk_m3u8_downloader.download_m3u8_to_mp4(m3u8_url, output_file)
                            print(f"Video saved to {output_file}")
                        
                        # Return early since we've handled the video download
                        return
                    else:
                        print("No M3U8 URLs found. Falling back to direct download methods.")
                except Exception as e:
                    print(f"Error using ltk_network_capture: {e}")
                    print("Falling back to direct download methods.")
            
            # If ltk_network_capture failed or isn't available, use the direct download method
            # Open the post in a new tab
            driver.execute_script("window.open(arguments[0]);", post_url)
            # Switch to the new tab
            driver.switch_to.window(driver.window_handles[-1])
            # Wait for the page to load
            time.sleep(5)
            
            # Now look for video elements on the individual post page
            video_elements = driver.find_elements(By.TAG_NAME, "video")
            if video_elements:
                print(f"Found {len(video_elements)} video elements on post page")
                for j, video in enumerate(video_elements):
                    try:
                        # Try to get video src directly
                        video_src = video.get_attribute("src")
                        
                        if video_src:
                            print(f"Found video src: {video_src}")
                            
                            # Check if it's a blob URL
                            if video_src.startswith("blob:"):
                                print("Detected blob URL. Using JavaScript to download...")
                                filename = os.path.join(output_dir, f"video_{index}_{j}.mp4")
                                download_blob_url(driver, video_src, filename)
                            else:
                                filename = os.path.join(output_dir, f"video_{index}_{j}.mp4")
                                download_file(video_src, filename, post_url)
                            continue
                        
                        # If no src on video tag, look for source elements
                        source_elements = video.find_elements(By.TAG_NAME, "source")
                        for k, source in enumerate(source_elements):
                            source_src = source.get_attribute("src")
                            if source_src:
                                print(f"Found source src: {source_src}")
                                
                                # Check if it's a blob URL
                                if source_src.startswith("blob:"):
                                    print("Detected blob URL. Using JavaScript to download...")
                                    filename = os.path.join(output_dir, f"video_{index}_{j}_source_{k}.mp4")
                                    download_blob_url(driver, source_src, filename)
                                else:
                                    filename = os.path.join(output_dir, f"video_{index}_{j}_source_{k}.mp4")
                                    download_file(source_src, filename, post_url)
                    except Exception as e:
                        print(f"Error processing video element {j}: {e}")
            else:
                print("No video elements found on post page. Trying to find video URLs in page source...")
                # Try to find video URL in page source
                page_source = driver.page_source
                
                # Look for video URLs in the source
                video_patterns = [
                    r'(https?://[^"\']+\.mp4)',
                    r'(https?://[^"\']+/video[^"\']*)',
                    r'videoSrc\s*[:=]\s*["\']([^"\']+)["\']',
                    r'videoUrl\s*[:=]\s*["\']([^"\']+)["\']',
                    r'data-video-url=["\']([^"\']+)["\']',
                    r'(https?://[^"\']+/stream[^"\']*)'
                ]
                
                for pattern in video_patterns:
                    matches = re.findall(pattern, page_source)
                    if matches:
                        print(f"Found {len(matches)} potential video URLs in page source")
                        
                        for i, match in enumerate(matches):
                            if isinstance(match, tuple):  # Some regex patterns return tuples
                                match = match[0]
                            
                            url = match
                            if url and is_likely_video_url(url):
                                print(f"Found video URL in source: {url}")
                                filename = os.path.join(output_dir, f"video_{index}_src_{i}.mp4")
                                download_file(url, filename, post_url)
            
            # Close the tab and switch back to the main window
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        else:
            # If we can't navigate to the individual post, try to process the video directly
            print("Could not find post URL. Trying to process video directly from the feed.")
            video_elements = post_element.find_elements(By.TAG_NAME, "video")
            if video_elements:
                print(f"Found {len(video_elements)} video elements in post")
                # Process video elements (similar to above)
                # ... (code similar to above)
            else:
                print("No video elements found in post. Trying alternative methods...")
                # Try to extract video URL from the post element
                # ... (code similar to above)
    except Exception as e:
        print(f"Error processing video post: {e}")
        # Make sure we switch back to the main window if an error occurs
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

def process_image_post(driver, post_element, output_dir, referer_url, index):
    """Process and download image content from a post"""
    try:
        # First try to find images within the specific structure from the example
        image_elements = post_element.find_elements(By.CSS_SELECTOR, ".ltk-img img, img.c-image")
        
        if not image_elements:
            # Fallback to any images in the post
            image_elements = post_element.find_elements(By.TAG_NAME, "img")
        
        if image_elements:
            print(f"Found {len(image_elements)} image elements in post")
            
            for i, img in enumerate(image_elements):
                try:
                    # Try to get the highest resolution image from srcset if available
                    srcset = img.get_attribute("srcset")
                    if srcset:
                        # Parse srcset to get the highest resolution image
                        srcset_parts = srcset.split(',')
                        highest_res_url = None
                        highest_dpr = 0
                        
                        for part in srcset_parts:
                            part = part.strip()
                            if part:
                                url_dpr = part.split(' ')
                                if len(url_dpr) >= 2:
                                    url = url_dpr[0]
                                    dpr_str = url_dpr[-1]
                                    try:
                                        # Extract the DPR value (e.g., "2x" -> 2)
                                        dpr = float(dpr_str.replace('x', ''))
                                        if dpr > highest_dpr:
                                            highest_dpr = dpr
                                            highest_res_url = url
                                    except ValueError:
                                        continue
                        
                        if highest_res_url:
                            print(f"Found highest resolution image in srcset: {highest_res_url}")
                            filename = os.path.join(output_dir, f"image_{index}_{i}.jpg")
                            download_file(highest_res_url, filename, referer_url)
                            continue
                    
                    # If no srcset or couldn't parse it, use src attribute
                    img_src = img.get_attribute("src")
                    if img_src:
                        print(f"Found image src: {img_src}")
                        filename = os.path.join(output_dir, f"image_{index}_{i}.jpg")
                        download_file(img_src, filename, referer_url)
                    
                except Exception as e:
                    print(f"Error processing image element {i}: {e}")
        else:
            print("No image elements found in post.")
    except Exception as e:
        print(f"Error processing image post: {e}")

def download_blob_url(driver, blob_url, filename):
    """Download a blob URL using JavaScript in the browser"""
    try:
        # JavaScript to fetch the blob and convert it to base64
        script = """
        async function fetchBlob(blobUrl) {
            try {
                const response = await fetch(blobUrl);
                const blob = await response.blob();
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result);
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                });
            } catch (e) {
                return 'Error: ' + e.message;
            }
        }
        return await fetchBlob(arguments[0]);
        """
        
        print(f"Fetching blob data from: {blob_url}")
        # Execute the script and get the base64 data
        base64_data = driver.execute_async_script(script, blob_url)
        
        if base64_data.startswith('Error:'):
            print(f"JavaScript error: {base64_data}")
            return False
        
        if not base64_data or not base64_data.startswith('data:'):
            print("Failed to get valid data from blob URL")
            return False
        
        # Strip the data URL prefix (e.g., "data:video/mp4;base64,")
        base64_prefix = base64_data.find('base64,')
        if base64_prefix == -1:
            print("Invalid base64 data format")
            return False
        
        base64_str = base64_data[base64_prefix + 7:]  # +7 to skip "base64,"
        
        # Decode and save the file
        print(f"Decoding blob data and saving to: {filename}")
        with open(filename, 'wb') as f:
            f.write(base64.b64decode(base64_str))
        
        file_size = os.path.getsize(filename)
        print(f"Saved {file_size} bytes to {filename}")
        
        # Basic validation
        if file_size < 10000:
            print(f"Warning: File size is very small ({file_size} bytes). This might not be a valid video.")
        
        return True
    except Exception as e:
        print(f"Error downloading blob URL: {e}")
        return False

def is_likely_video_url(url):
    """Check if a URL is likely a video"""
    video_indicators = ['.mp4', '.webm', '.mov', '/video', 'media', '/stream', 'mux.com']
    for indicator in video_indicators:
        if indicator in url.lower():
            return True
    return False

def download_file(url, filename, referer):
    """Download a file from URL"""
    try:
        print(f"Downloading: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
            'Referer': referer
        }
        
        response = requests.get(url, headers=headers, stream=True)
        
        if response.status_code == 200:
            print(f"Download successful. Content-Type: {response.headers.get('Content-Type')}")
            print(f"Content-Length: {response.headers.get('Content-Length')} bytes")
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            
            file_size = os.path.getsize(filename)
            print(f"Saved {file_size} bytes to {filename}")
            
            # Verify it's not too small to be a real file
            if file_size < 10000:
                print(f"Warning: File size is very small ({file_size} bytes). This might not be a valid file.")
            
            return True
        else:
            print(f"Failed to download. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error downloading file: {e}")
        return False

if __name__ == "__main__":
    print("LTK Content Downloader - Images and Videos")
    print("--------------------------------------")
    
    video_url = input("Enter the URL of the page containing the content: ")
    output_dir = input("Enter a directory to save the content (or press Enter for default 'downloaded_videos'): ")
    
    if not output_dir:
        output_dir = "downloaded_videos"
    
    download_video_from_url(video_url, output_dir) 