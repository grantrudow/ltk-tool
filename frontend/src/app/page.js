"use client";

import { useState, useEffect } from 'react';

const [downloadStatus, setDownloadStatus] = useState('idle'); // 'idle', 'starting', 'processing', 'complete', 'error'
const [downloadProgress, setDownloadProgress] = useState(0);
const [downloadId, setDownloadId] = useState(null);
const [downloadUrl, setDownloadUrl] = useState(null);
const [isSubmitting, setIsSubmitting] = useState(false);

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

const handleDownloadFile = async () => {
  if (!downloadUrl) return;
  
  try {
    // Option 1: Direct download via window.open
    window.open(downloadUrl, '_blank');
    
    // Option 2: Fetch and download as blob
    // const response = await fetch(downloadUrl);
    // const blob = await response.blob();
    // const url = window.URL.createObjectURL(blob);
    // const a = document.createElement('a');
    // a.href = url;
    // a.download = 'download.zip'; // Or get filename from headers
    // document.body.appendChild(a);
    // a.click();
    // window.URL.revokeObjectURL(url);
    // a.remove();
    
    console.log('Download initiated');
  } catch (error) {
    console.error('Error downloading file:', error);
    // Show error message to user
  }
};

// This remains a Server Component
import DownloadManager from './components/DownloadManager';

export default function Page() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">LTK Downloader</h1>
      <DownloadManager />
    </div>
  );
}