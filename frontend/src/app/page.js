// app/page.js - Next.js App Router Home Page
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiRequest } from '@/utils/api';

// Get the API URL from environment variables
const API_URL = process.env.NEXT_PUBLIC_API_URL 
  ? process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '') // Remove trailing slash if present
  : 'http://localhost:8000';

export default function Home() {
  const [url, setUrl] = useState('');
  const [count, setCount] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null);
  const [pollingInterval, setPollingInterval] = useState(null);
  const [useDirectApi, setUseDirectApi] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [downloadReady, setDownloadReady] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState('');
  const [downloadStarted, setDownloadStarted] = useState(false);
  const router = useRouter();

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  const isValidUrl = (string) => {
    try {
      new URL(string);
      return true;
    } catch (_) {
      return false;
    }
  };

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    setError('');
    setDownloadReady(false);
    setDownloadUrl('');
    setDownloadStarted(false);
    
    if (!isValidUrl(url)) {
      setError('Please enter a valid URL');
      return;
    }

    // Prevent endless retries
    if (retryCount >= 2) {
      setError('Failed after multiple attempts. Please check if the backend server is running.');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      console.log('Starting download task...');
      console.log(`Using API URL: ${API_URL}`);
      
      // Start the download task - use the correct API endpoint with /api prefix
      const response = await apiRequest('/download', {
        method: 'POST',
        body: JSON.stringify({ url, count }),
      });

      // Check if we got a response
      if (!response) {
        throw new Error('No response from server');
      }

      console.log(`Response status: ${response.status}`);
      console.log(`Response headers:`, Object.fromEntries([...response.headers.entries()]));

      // Try to parse the response as JSON
      let data;
      try {
        data = await response.json();
        console.log('Response data:', data);
      } catch (jsonError) {
        console.error('Error parsing JSON response:', jsonError);
        const text = await response.text();
        console.error('Response text:', text);
        throw new Error('Invalid response format from server');
      }
      
      if (!response.ok) {
        throw new Error(data.error || data.detail || `Server responded with ${response.status}`);
      }

      // Reset retry count on success
      setRetryCount(0);
      console.log('Download task started:', data);
      
      if (!data.task_id) {
        throw new Error('No task ID returned from server');
      }
      
      setTaskId(data.task_id);
      setStatus('processing');
      
      // Poll for status
      startPolling(data.task_id);
    } catch (err) {
      console.error('Error starting download:', err);
      
      // If using direct API failed, try with proxy (only once)
      if (useDirectApi && retryCount === 0) {
        setError(`Failed with direct API. Trying proxy... (${err.message})`);
        setUseDirectApi(false);
        setRetryCount(prev => prev + 1);
        
        // Try again with proxy after a short delay
        setTimeout(() => {
          handleSubmit();
        }, 1000);
        return;
      }
      
      setError(`Download failed: ${err.message || 'Unknown error'}. Please check if the backend server is running.`);
      setRetryCount(prev => prev + 1);
    } finally {
      setLoading(false);
    }
  };

  const startPolling = (id) => {
    console.log(`Starting polling for task ${id}`);
    
    // Clear any existing polling interval
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }
    
    let failedAttempts = 0;
    const MAX_FAILED_ATTEMPTS = 3;
    
    const interval = setInterval(async () => {
      try {
        // Use the correct API endpoint for status checks
        const statusUrl = `${API_URL}/api/download/${id}/status`;
        console.log(`Checking status at: ${statusUrl}`);
        
        const response = await fetch(statusUrl);
        
        if (!response) {
          throw new Error('No response from server');
        }
        
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          console.error('Non-JSON response received:', contentType);
          throw new Error('Invalid response from server');
        }
        
        const data = await response.json();
        
        if (!response.ok) {
          throw new Error(data.error || data.detail || `Status check failed with ${response.status}`);
        }
        
        // Reset failed attempts on success
        failedAttempts = 0;
        
        console.log(`Task status: ${data.status}`);
        setStatus(data.status);
        
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval);
          setPollingInterval(null);
          
          if (data.status === 'completed') {
            // Set download URL correctly using the API_URL
            const downloadUrl = `${API_URL}/api/download/${id}`;
            console.log(`Download ready at: ${downloadUrl}`);
            setDownloadReady(true);
            setDownloadUrl(downloadUrl);
          }
        }
      } catch (err) {
        console.error('Error checking download status:', err);
        failedAttempts++;
        
        if (failedAttempts >= MAX_FAILED_ATTEMPTS) {
          clearInterval(interval);
          setPollingInterval(null);
          setError('Error checking download status: ' + (err.message || 'Unknown error') + 
                  '. Polling stopped after multiple failed attempts.');
        }
      }
    }, 2000); // Check every 2 seconds
    
    setPollingInterval(interval);
  };

  const toggleApiMode = () => {
    setUseDirectApi(!useDirectApi);
  };

  const handleDownload = async () => {
    if (!downloadUrl || downloadStarted) return;
    
    try {
      setDownloadStarted(true);
      console.log(`Initiating direct download from: ${downloadUrl}`);
      
      // Make a fetch request to get the file
      const response = await fetch(downloadUrl);
      
      // Check if the response is OK
      if (!response.ok) {
        console.error(`Download failed with status: ${response.status}`);
        
        // Try to get more details about the error
        let errorMessage = `Server responded with ${response.status}`;
        try {
          const contentType = response.headers.get('content-type') || '';
          if (contentType.includes('application/json')) {
            const errorData = await response.json();
            errorMessage = errorData.error || errorData.detail || errorMessage;
            console.error('Error details:', errorData);
          }
        } catch (e) {
          console.error('Could not parse error response:', e);
        }
        
        throw new Error(errorMessage);
      }
      
      // Check content type
      const contentType = response.headers.get('content-type');
      console.log(`Download response content-type: ${contentType}`);
      
      // Verify we got a binary file
      if (!contentType || (!contentType.includes('application/zip') && 
          !contentType.includes('application/octet-stream'))) {
        console.warn(`Unexpected content type: ${contentType}. Expected zip or binary.`);
      }
      
      // Get filename from Content-Disposition header or use a default
      let filename = 'downloaded_media.zip';
      const contentDisposition = response.headers.get('content-disposition');
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1];
        }
      }
      
      // Get the blob from the response
      const blob = await response.blob();
      
      // Verify the blob has content
      if (blob.size === 0) {
        throw new Error('Downloaded file is empty');
      }
      
      console.log(`Downloaded blob size: ${blob.size} bytes, type: ${blob.type}`);
      
      // Create a URL for the blob
      const blobUrl = window.URL.createObjectURL(blob);
      
      // Create a link and trigger the download
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      
      // Clean up
      setTimeout(() => {
        window.URL.revokeObjectURL(blobUrl);
        document.body.removeChild(link);
      }, 100);
      
      console.log('Download initiated successfully');
    } catch (err) {
      console.error('Error downloading file:', err);
      
      // If the error is a 404 or 410, it might mean the file was cleaned up
      // Let's try to restart the download process
      if (err.message.includes('404') || err.message.includes('410')) {
        setError(`The download file may have been cleaned up. Please start a new download.`);
      } else {
        setError(`Download failed: ${err.message}. Please try again.`);
      }
    } finally {
      setDownloadStarted(false);
    }
  };

  const startNewDownload = () => {
    // Reset states to start a new download
    setTaskId(null);
    setStatus(null);
    setDownloadReady(false);
    setDownloadUrl('');
    setDownloadStarted(false);
    setError('');
  };

  const handleStartDownload = async () => {
    try {
      console.log('Making request to:', `${API_URL}/api/download`);
      
      const response = await fetch(`${API_URL}/api/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          // Your request data
        }),
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }
      
      // Check the content type of the response
      const contentType = response.headers.get('content-type');
      
      // Handle different response types appropriately
      if (contentType && contentType.includes('application/json')) {
        // If it's JSON, parse it
        const data = await response.json();
        console.log('Response data:', data);
        
        // Process the JSON data
        // ...
      } else if (contentType && contentType.includes('application/octet-stream')) {
        // If it's a file download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'download.zip'; // Or get filename from headers if available
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
      } else {
        // For text or other content types
        const text = await response.text();
        console.log('Response text:', text);
      }
      
    } catch (error) {
      console.error('Error starting download:', error);
      // Handle error
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-8 bg-gray-50">
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm">
        <h1 className="text-4xl font-bold text-center mb-8">LTK Content Downloader</h1>
        
        {downloadReady ? (
          <div className="bg-white p-6 rounded-lg shadow-md mb-8 text-center">
            <h2 className="text-2xl font-bold text-green-600 mb-4">Download Ready!</h2>
            <p className="mb-4">Your content has been successfully processed and is ready to download.</p>
            
            <div className="flex flex-col sm:flex-row justify-center gap-4 mt-6">
              <button
                onClick={handleDownload}
                disabled={downloadStarted}
                className={`bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition-colors ${
                  downloadStarted ? 'opacity-50 cursor-not-allowed' : ''
                }`}
              >
                {downloadStarted ? 'Downloading...' : 'Download Now'}
              </button>
              
              <button
                onClick={startNewDownload}
                className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-3 px-6 rounded-lg transition-colors"
              >
                Start New Download
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md mb-8">
            <div className="mb-4">
              <label htmlFor="url" className="block text-gray-700 font-bold mb-2">
                Enter URL to download content from:
              </label>
              <input
                type="text"
                id="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://www.shopltk.com/explore/username"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading || status === 'processing'}
              />
            </div>
            
            <div className="mb-6">
              <label htmlFor="count" className="block text-gray-700 font-bold mb-2">
                Number of items to download (max):
              </label>
              <input
                type="number"
                id="count"
                value={count}
                onChange={(e) => setCount(Math.max(1, parseInt(e.target.value) || 1))}
                min="1"
                max="100"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading || status === 'processing'}
              />
            </div>
            
            <div className="flex items-center mb-6">
              <input
                type="checkbox"
                id="useDirectApi"
                checked={useDirectApi}
                onChange={toggleApiMode}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                disabled={loading || status === 'processing'}
              />
              <label htmlFor="useDirectApi" className="ml-2 block text-gray-700">
                Use direct API (faster, more reliable)
              </label>
            </div>
            
            <div className="flex justify-center">
              <button
                onClick={handleStartDownload}
                disabled={loading || status === 'processing'}
                className={`bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg transition-colors ${
                  (loading || status === 'processing') ? 'opacity-50 cursor-not-allowed' : ''
                }`}
              >
                {loading ? 'Processing...' : 'Start Download'}
              </button>
            </div>
          </form>
        )}
      </div>
    </main>
  );
}