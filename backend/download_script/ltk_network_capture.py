import json
import time
import re
import os
import signal
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

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
    
    try:
        # Configure Chrome with network logging enabled
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run headless for reliability
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")  # Allow autoplay
        
        # Set log preferences for network monitoring
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to the video page
        print(f"Network capture: Opening URL: {video_page_url}")
        driver.get(video_page_url)
        
        # Wait for video element to load with a shorter timeout
        print("Network capture: Waiting for video element...")
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "video"))
            )
            print("Network capture: Video element found")
        except TimeoutException:
            print("Network capture: Video element not found, continuing anyway")
        
        # Try to play the video
        video_elements = driver.find_elements(By.TAG_NAME, "video")
        if video_elements:
            print(f"Network capture: Found {len(video_elements)} video elements. Trying to play...")
            for video in video_elements:
                try:
                    driver.execute_script("arguments[0].play();", video)
                    # Skip forward a bit to trigger video loading
                    driver.execute_script("arguments[0].currentTime = 2;", video)
                except:
                    print("Network capture: Error playing video, continuing...")
        
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
        print("Network capture: Process timed out, returning any URLs found so far")
        if 'mux_urls' in locals() and mux_urls:
            return mux_urls[skip:] if skip < len(mux_urls) else []
        elif 'm3u8_urls' in locals() and m3u8_urls:
            return m3u8_urls[skip:] if skip < len(m3u8_urls) else []
        return []
    except Exception as e:
        print(f"Network capture error: {e}")
        return []
    finally:
        # Cancel the alarm
        signal.alarm(0)
        
        # Close the browser
        if driver:
            try:
                driver.quit()
                print("Network capture: Browser closed")
            except:
                print("Network capture: Error closing browser")
                # Force close if needed
                try:
                    if hasattr(driver, 'service') and hasattr(driver.service, 'process'):
                        if driver.service.process:
                            driver.service.process.kill()
                except:
                    pass

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