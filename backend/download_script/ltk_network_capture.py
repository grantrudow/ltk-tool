import json
import time
import re
import os
import signal
import logging
import tempfile
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set a timeout for the entire function
class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Network capture timed out")

def capture_video_urls(video_page_url, timeout=30, skip=0):
    """
    Capture video URLs from a LikeToKnowIt video page
    
    Args:
        video_page_url (str): URL to the video page
        timeout (int): Maximum time in seconds to wait for the entire process
        skip (int): Number of URLs to skip from the beginning
        
    Returns:
        list: A list of found M3U8 URLs, empty if none found
    """
    # Set up timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    
    driver = None
    temp_dir = None
    
    try:
        # Create a unique temporary directory for Chrome user data
        temp_dir = tempfile.mkdtemp(prefix="chrome_user_data_")
        logger.info(f"Created temporary user data directory: {temp_dir}")
        
        # Make sure the directory has the right permissions
        os.chmod(temp_dir, 0o755)
        
        # Configure Chrome with network logging enabled
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run headless for reliability
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")  # Allow autoplay
        
        # Add these arguments to fix the "DevToolsActivePort file doesn't exist" error
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"--remote-debugging-port={9222 + os.getpid() % 1000}")  # Use a dynamic port
        
        # Add a unique user data directory
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--incognito")
        
        # Set log preferences for network monitoring
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        
        logger.info(f"Starting Chrome with options: {chrome_options.arguments}")
        
        try:
            # Check if chromedriver is in PATH
            chrome_path = os.environ.get('CHROME_PATH', None)
            chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', None)
            
            if chrome_path:
                logger.info(f"Using Chrome binary from: {chrome_path}")
                chrome_options.binary_location = chrome_path
            
            if chromedriver_path:
                logger.info(f"Using ChromeDriver from: {chromedriver_path}")
                service = Service(executable_path=chromedriver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("Chrome driver initialized with explicit service path")
            else:
                driver = webdriver.Chrome(options=chrome_options)
                logger.info("Chrome driver initialized successfully")
        except WebDriverException as e:
            logger.error(f"Failed to initialize Chrome driver: {str(e)}")
            # Try with service object explicitly
            try:
                service = Service()
                driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("Chrome driver initialized with explicit service")
            except Exception as e2:
                logger.error(f"Second attempt to initialize Chrome driver failed: {str(e2)}")
                raise
        
        # Navigate to the video page
        print(f"Network capture: Opening URL: {video_page_url}")
        logger.info(f"Navigating to URL: {video_page_url}")
        driver.get(video_page_url)
        
        # Wait for video element to load with a shorter timeout
        print("Network capture: Waiting for video element...")
        logger.info("Waiting for video element...")
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "video"))
            )
            print("Network capture: Video element found")
            logger.info("Video element found")
        except TimeoutException:
            print("Network capture: Video element not found, continuing anyway")
            logger.warning("Video element not found, continuing anyway")
        
        # Try to play the video
        video_elements = driver.find_elements(By.TAG_NAME, "video")
        if video_elements:
            print(f"Network capture: Found {len(video_elements)} video elements. Trying to play...")
            logger.info(f"Found {len(video_elements)} video elements. Trying to play...")
            for video in video_elements:
                try:
                    driver.execute_script("arguments[0].play();", video)
                    # Skip forward a bit to trigger video loading
                    driver.execute_script("arguments[0].currentTime = 2;", video)
                    logger.info("Successfully played video")
                except Exception as e:
                    print("Network capture: Error playing video, continuing...")
                    logger.warning(f"Error playing video: {str(e)}, continuing...")
        
        # Also try clicking play buttons if videos didn't autoplay
        try:
            play_buttons = driver.find_elements(
                By.CSS_SELECTOR, 
                "[class*='play'], [id*='play'], button[class*='video']"
            )
            if play_buttons:
                print(f"Network capture: Found {len(play_buttons)} play buttons. Trying to click...")
                for button in play_buttons:
                    try:
                        button.click()
                        print("Network capture: Clicked play button")
                        break
                    except:
                        try:
                            driver.execute_script("arguments[0].click();", button)
                            print("Network capture: Clicked play button with JavaScript")
                            break
                        except:
                            continue
        except:
            pass
        
        # Wait for video to load and generate network requests (shorter wait time)
        print("Network capture: Waiting for video to load (5 seconds)...")
        time.sleep(5)
        
        # Get browser logs
        logs = driver.get_log('performance')
        
        # Find M3U8 URLs in network requests
        m3u8_urls = []
        mux_urls = []
        
        # Process network logs to find M3U8 URLs
        for entry in logs:
            try:
                log_data = json.loads(entry["message"])["message"]
                
                # Check if this is a network request
                if "Network.requestWillBeSent" in log_data["method"]:
                    request_data = log_data["params"]
                    url = request_data.get("request", {}).get("url", "")
                    
                    # Look for M3U8 URLs
                    if url and '.m3u8' in url:
                        m3u8_urls.append(url)
                        
                        # Specifically check for Mux URLs
                        if 'stream.mux.com' in url:
                            mux_urls.append(url)
            except:
                pass
        
        # If no Mux URLs found but we have other M3U8 URLs, that's fine
        if not mux_urls and m3u8_urls:
            print("Network capture: Found M3U8 URLs but no Mux URLs")
        
        # If no M3U8 URLs found in network requests, try the page source
        if not m3u8_urls:
            print("Network capture: No M3U8 URLs found in network logs. Checking page source...")
            page_source = driver.page_source
            m3u8_pattern = r'(https?://[^"\']+\.m3u8)'
            matches = re.findall(m3u8_pattern, page_source)
            
            if matches:
                for url in matches:
                    m3u8_urls.append(url)
                    if 'stream.mux.com' in url:
                        mux_urls.append(url)
        
        # If still no results, try to extract from video.js player
        if not m3u8_urls and 'videojs' in driver.page_source.lower():
            print("Network capture: Attempting to extract from Video.js player...")
            js_script = """
            function getVideoJsSources() {
                var sources = [];
                if (typeof videojs !== 'undefined') {
                    var players = document.querySelectorAll('.video-js');
                    for (var i = 0; i < players.length; i++) {
                        var player = videojs.getPlayer(players[i]);
                        if (player && player.src) {
                            sources.push(player.src());
                        }
                    }
                }
                return sources;
            }
            return getVideoJsSources();
            """
            
            try:
                videojsUrls = driver.execute_script(js_script)
                if videojsUrls and len(videojsUrls) > 0:
                    for url in videojsUrls:
                        m3u8_urls.append(url)
                        if 'stream.mux.com' in url:
                            mux_urls.append(url)
            except:
                pass
        
        # Try to find all post items on the page to get more videos
        try:
            print("Network capture: Looking for post items on the page...")
            post_items = driver.find_elements(By.CSS_SELECTOR, "[data-test-id='post-feed-item/card']")
            print(f"Network capture: Found {len(post_items)} post items")
            
            if len(post_items) > 0:
                # Process each post to find more videos
                for i, post in enumerate(post_items):
                    try:
                        # Skip posts based on the skip parameter
                        if i < skip:
                            print(f"Network capture: Skipping post #{i+1} as requested")
                            continue
                            
                        print(f"Network capture: Processing post #{i+1}")
                        
                        # Try to get the post URL
                        post_url = post.get_attribute("href")
                        if post_url and not post_url.startswith("http"):
                            # Handle relative URLs
                            base_url = "/".join(video_page_url.split("/")[:3])  # Get domain part
                            post_url = base_url + post_url
                        
                        if post_url:
                            print(f"Network capture: Found post URL: {post_url}")
                            # Open the post in a new tab
                            driver.execute_script("window.open(arguments[0]);", post_url)
                            # Switch to the new tab
                            driver.switch_to.window(driver.window_handles[-1])
                            # Wait for the page to load
                            time.sleep(3)
                            
                            # Look for video elements
                            video_elements = driver.find_elements(By.TAG_NAME, "video")
                            if video_elements:
                                print(f"Network capture: Found {len(video_elements)} video elements in post")
                                for video in video_elements:
                                    try:
                                        driver.execute_script("arguments[0].play();", video)
                                    except:
                                        pass
                            
                            # Wait for video to load
                            time.sleep(2)
                            
                            # Check for m3u8 URLs in this post
                            post_logs = driver.get_log('performance')
                            for entry in post_logs:
                                try:
                                    log_data = json.loads(entry["message"])["message"]
                                    if "Network.requestWillBeSent" in log_data["method"]:
                                        request_data = log_data["params"]
                                        url = request_data.get("request", {}).get("url", "")
                                        if url and '.m3u8' in url:
                                            if url not in m3u8_urls:
                                                m3u8_urls.append(url)
                                                print(f"Network capture: Found new M3U8 URL in post: {url}")
                                                if 'stream.mux.com' in url:
                                                    mux_urls.append(url)
                                except:
                                    pass
                            
                            # Close the tab and switch back to the main tab
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                    except Exception as e:
                        print(f"Network capture: Error processing post #{i+1}: {e}")
                        # Make sure we're back on the main tab
                        if len(driver.window_handles) > 1:
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
        except Exception as e:
            print(f"Network capture: Error finding post items: {e}")
        
        # Print results
        if mux_urls:
            print(f"Network capture: Found {len(mux_urls)} Mux URLs:")
            for i, url in enumerate(mux_urls):
                print(f"{i+1}. {url}")
            # Return Mux URLs first if we found any
            return mux_urls[skip:] if skip < len(mux_urls) else []
        elif m3u8_urls:
            print(f"Network capture: Found {len(m3u8_urls)} M3U8 URLs:")
            for i, url in enumerate(m3u8_urls):
                print(f"{i+1}. {url}")
            return m3u8_urls[skip:] if skip < len(m3u8_urls) else []
        else:
            print("Network capture: No M3U8 URLs found")
            return []
        
    except TimeoutError:
        print(f"Network capture: Timed out after {timeout} seconds")
        logger.error(f"Timed out after {timeout} seconds")
        # Return any URLs we might have found before timeout
        if driver:
            try:
                return extract_m3u8_urls_from_logs(driver, skip)
            except Exception as e:
                print(f"Network capture: Error extracting URLs after timeout: {e}")
                logger.error(f"Error extracting URLs after timeout: {str(e)}")
                return []
        return []
    except Exception as e:
        print(f"Network capture: Error during network capture: {e}")
        logger.error(f"Error during network capture: {str(e)}")
        return []
    finally:
        # Clean up
        signal.alarm(0)  # Cancel the alarm
        if driver:
            try:
                driver.quit()
                logger.info("Chrome driver closed successfully")
            except Exception as e:
                print(f"Network capture: Error closing driver: {e}")
                logger.error(f"Error closing driver: {str(e)}")
        
        # Clean up the temporary user data directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"Removed temporary user data directory: {temp_dir}")
            except Exception as e:
                logger.error(f"Error removing temporary directory {temp_dir}: {str(e)}")

def extract_m3u8_urls_from_logs(driver, skip=0):
    """
    Extract M3U8 URLs from browser logs
    
    Args:
        driver: Selenium WebDriver instance
        skip: Number of URLs to skip
        
    Returns:
        list: A list of found M3U8 URLs
    """
    try:
        # Get browser logs
        logs = driver.get_log('performance')
        
        # Find M3U8 URLs in network requests
        m3u8_urls = []
        mux_urls = []
        
        # Process network logs to find M3U8 URLs
        for entry in logs:
            try:
                log_data = json.loads(entry["message"])["message"]
                
                # Check if this is a network request
                if "Network.requestWillBeSent" in log_data["method"]:
                    request_data = log_data["params"]
                    url = request_data.get("request", {}).get("url", "")
                    
                    # Look for M3U8 URLs
                    if url and '.m3u8' in url:
                        m3u8_urls.append(url)
                        
                        # Specifically check for Mux URLs
                        if 'stream.mux.com' in url:
                            mux_urls.append(url)
            except Exception as e:
                logger.warning(f"Error processing log entry: {str(e)}")
                continue
        
        # If we found Mux URLs, prioritize those
        if mux_urls:
            return mux_urls[skip:] if skip < len(mux_urls) else []
        elif m3u8_urls:
            return m3u8_urls[skip:] if skip < len(m3u8_urls) else []
        else:
            return []
    except Exception as e:
        logger.error(f"Error extracting M3U8 URLs from logs: {str(e)}")
        return []

# This allows the module to be run standalone for testing
if __name__ == "__main__":
    print("LTK Network Capture Module")
    print("-----------------------")
    
    video_url = input("Enter the URL of the video page: ")
    m3u8_urls = capture_video_urls(video_url)
    
    if m3u8_urls:
        print("\nFound M3U8 URLs:")
        for i, url in enumerate(m3u8_urls):
            print(f"{i+1}. {url}")
    else:
        print("\nNo M3U8 URLs found")