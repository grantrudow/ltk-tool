"use client";

import DownloadManager from './components/DownloadManager';

export default function Page() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">LTK Downloader</h1>
      <DownloadManager />
    </div>
  );
}