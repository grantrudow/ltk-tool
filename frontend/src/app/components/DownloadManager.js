"use client";

import { useState, useEffect } from 'react';

export default function DownloadManager() {
  const [downloadStatus, setDownloadStatus] = useState('idle');
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [downloadId, setDownloadId] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const handleStartDownload = async (e) => {
    if (e) e.preventDefault();
    
    // Prevent duplicate requests
    if (isSubmitting || downloadStatus === 'starting' || downloadStatus === 'processing') {
      console.log('Request already in progress, ignoring');
      return;
    }
    
    setIsSubmitting(true);
    setDownloadStatus('starting');
    setDownloadProgress(0);
    setDownloadUrl(null);
    
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL 
        ? process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '')
        : 'http://localhost:8000';
      
      console.log('Starting download task...');
      
      const response = await fetch(`${API_URL}/api/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          // Your request data
          // For example:
          // url: formData.url,
          // options: {
          //   // Any options your API needs
          // }
        }),
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Download task started:', data);
      
      // Store the download ID for status polling
      if (data.id) {
        setDownloadId(data.id);
        setDownloadStatus('processing');
        // Start polling for status
        pollDownloadStatus(data.id);
      } else {
        throw new Error('No download ID returned from API');
      }
      
    } catch (error) {
      console.error('Error starting download:', error);
      setDownloadStatus('error');
      // Show error message to user
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const pollDownloadStatus = async (id) => {
    if (!id) return;
    
    const API_URL = process.env.NEXT_PUBLIC_API_URL 
      ? process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '')
      : 'http://localhost:8000';
    
    try {
      const response = await fetch(`${API_URL}/api/download/status/${id}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Download status:', data);
      
      // Update progress
      if (data.progress !== undefined) {
        setDownloadProgress(data.progress);
      }
      
      // Update status
      if (data.status) {
        setDownloadStatus(data.status);
        
        // If complete, get the download URL
        if (data.status === 'complete' && data.download_url) {
          setDownloadUrl(data.download_url);
        }
        
        // If still processing, continue polling
        if (data.status === 'processing') {
          // Poll again after a delay
          setTimeout(() => pollDownloadStatus(id), 2000); // Poll every 2 seconds
        }
      }
      
    } catch (error) {
      console.error('Error checking download status:', error);
      setDownloadStatus('error');
      // Show error message to user
    }
  };
  
  const handleDownloadFile = async () => {
    if (!downloadUrl) return;
    
    try {
      // Option 1: Direct download via window.open
      window.open(downloadUrl, '_blank');
      
      console.log('Download initiated');
    } catch (error) {
      console.error('Error downloading file:', error);
      // Show error message to user
    }
  };
  
  // Cleanup effect
  useEffect(() => {
    let pollingTimeout;
    
    // Cleanup function
    return () => {
      if (pollingTimeout) {
        clearTimeout(pollingTimeout);
      }
    };
  }, []);
  
  return (
    <div className="container mx-auto">
      {/* Start Download Button */}
      <button
        onClick={handleStartDownload}
        disabled={isSubmitting || downloadStatus === 'processing' || downloadStatus === 'starting'}
        className={`bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg transition-colors ${
          (isSubmitting || downloadStatus === 'processing' || downloadStatus === 'starting') 
            ? 'opacity-50 cursor-not-allowed' 
            : ''
        }`}
      >
        {downloadStatus === 'starting' 
          ? 'Starting...' 
          : downloadStatus === 'processing' 
            ? 'Processing...' 
            : 'Start Download'}
      </button>
      
      {/* Status and Progress */}
      {downloadStatus !== 'idle' && downloadStatus !== 'complete' && (
        <div className="mt-6">
          <p className="mb-2">
            {downloadStatus === 'starting' && 'Starting download task...'}
            {downloadStatus === 'processing' && 'Processing download...'}
            {downloadStatus === 'error' && 'Error processing download.'}
          </p>
          
          {/* Progress Bar */}
          {(downloadStatus === 'processing' || downloadStatus === 'starting') && (
            <div className="w-full bg-gray-200 rounded-full h-2.5 mb-4">
              <div 
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300" 
                style={{ width: `${downloadProgress}%` }}
              ></div>
            </div>
          )}
        </div>
      )}
      
      {/* Download Button - Only show when download is complete */}
      {downloadStatus === 'complete' && downloadUrl && (
        <div className="mt-6">
          <p className="text-green-600 mb-2">Download ready!</p>
          <button
            onClick={handleDownloadFile}
            className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-lg transition-colors"
          >
            Download File
          </button>
        </div>
      )}
      
      {/* Error Message */}
      {downloadStatus === 'error' && (
        <div className="mt-6">
          <p className="text-red-600">
            There was an error processing your download. Please try again.
          </p>
          <button
            onClick={() => setDownloadStatus('idle')}
            className="mt-2 bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      )}
    </div>
  );
} 