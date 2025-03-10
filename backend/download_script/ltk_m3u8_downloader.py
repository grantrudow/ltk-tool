import subprocess
import os
import platform
import sys

def check_ffmpeg():
    """Check if FFmpeg is installed"""
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False

def download_m3u8_to_mp4(m3u8_url, output_file):
    """
    Download an m3u8 stream and convert it to an MP4 file
    
    Args:
        m3u8_url (str): URL to the m3u8 playlist
        output_file (str): Output MP4 filename
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Check if FFmpeg is installed
    if not check_ffmpeg():
        print("Error: FFmpeg is not installed.")
        print_ffmpeg_instructions()
        return False
    
    # Make sure the output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Construct the FFmpeg command
    command = [
        'ffmpeg',
        '-i', m3u8_url,
        '-c', 'copy',  # Copy the stream without re-encoding (much faster)
        '-bsf:a', 'aac_adtstoasc',  # Fix for AAC audio streams
        '-loglevel', 'warning',  # Reduce log output
        output_file
    ]
    
    print(f"Downloading video from {m3u8_url} to {output_file}...")
    
    # Run FFmpeg
    try:
        result = subprocess.run(
            command,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            print(f"Successfully downloaded and converted to {output_file}")
            print(f"Output file size: {os.path.getsize(output_file) / (1024*1024):.2f} MB")
            return True
        else:
            print(f"FFmpeg error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error running FFmpeg: {e}")
        return False

def print_ffmpeg_instructions():
    """Print instructions for installing FFmpeg based on the platform"""
    system = platform.system()
    
    print("FFmpeg is not installed. Here's how to install it:")
    
    if system == "Windows":
        print("\nWindows instructions:")
        print("1. Download FFmpeg from https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip")
        print("2. Extract the ZIP file")
        print("3. Copy the ffmpeg.exe, ffplay.exe, and ffprobe.exe files from the bin folder to C:\\Windows\\System32")
        print("   (or add the bin folder to your PATH environment variable)")
    
    elif system == "Darwin":  # macOS
        print("\nmacOS instructions:")
        print("1. Install Homebrew if you don't have it already: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        print("2. Install FFmpeg: brew install ffmpeg")
    
    elif system == "Linux":
        print("\nLinux instructions:")
        print("Ubuntu/Debian: sudo apt update && sudo apt install ffmpeg")
        print("Fedora: sudo dnf install ffmpeg")
        print("Arch Linux: sudo pacman -S ffmpeg")

# This allows the module to be run standalone for testing
if __name__ == "__main__":
    print("LTK M3U8 Downloader Module")
    print("------------------------")
    
    # Check if FFmpeg is installed
    if not check_ffmpeg():
        print_ffmpeg_instructions()
        sys.exit(1)
    
    m3u8_url = input("Enter the M3U8 URL: ")
    output_file = input("Enter the output file path (or press Enter for 'video.mp4'): ")
    
    if not output_file:
        output_file = "video.mp4"
    
    # Make sure output file has .mp4 extension
    if not output_file.lower().endswith('.mp4'):
        output_file += '.mp4'
    
    # Download the video
    download_m3u8_to_mp4(m3u8_url, output_file)