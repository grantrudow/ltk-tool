const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const apiRequest = async (endpoint, options = {}) => {
  // Make sure endpoint starts with a slash but doesn't have multiple slashes
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  
  // Always include the /api prefix
  const url = `${API_URL}/api${cleanEndpoint}`;
  
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });
  
  // Return the raw response instead of automatically parsing JSON
  return response;
}; 