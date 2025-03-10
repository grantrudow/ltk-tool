// app/api/proxy/download/[...path]/route.js
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(request, { params }) {
    const path = params.path || [];
    const pathString = path.join('/');
    
    console.log(`Proxying GET request to: ${API_URL}/download/${pathString}`);
    console.log(`Path parts:`, path);
    console.log(`Joined path: ${pathString}`);
    console.log(`Environment API_URL: ${process.env.API_URL}`);
    console.log(`Environment NEXT_PUBLIC_API_URL: ${process.env.NEXT_PUBLIC_API_URL}`);
    
    // Check if this is a status request
    const isStatusRequest = pathString.includes('status');
    
    // Get the task ID (first part of the path)
    const taskId = path[0]; // The first part should be the task ID
    
    try {
        // Add timeout to prevent hanging requests
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minute timeout for large files
        
        const response = await fetch(`${API_URL}/download/${pathString}`, {
            headers: {
                'Accept': 'application/json, application/octet-stream, */*',
            },
            signal: controller.signal
        }).catch(error => {
            if (error.name === 'AbortError') {
                throw new Error('Request timed out after 5 minutes');
            }
            throw error;
        });
        
        // Clear the timeout
        clearTimeout(timeoutId);
        
        const contentType = response.headers.get('content-type') || '';
        
        console.log(`Response status: ${response.status}, Content-Type: ${contentType}`);
        
        if (!response.ok) {
            console.error(`Error response from API: ${response.status} ${response.statusText}`);
            // Try to get error details
            let errorDetails = '';
            try {
                if (contentType.includes('application/json')) {
                    const errorData = await response.json();
                    errorDetails = JSON.stringify(errorData);
                } else {
                    errorDetails = await response.text();
                }
            } catch (e) {
                errorDetails = 'Could not parse error response';
            }
            
            return Response.json({ 
                error: `API returned error: ${response.status} ${response.statusText}`,
                details: errorDetails
            }, { status: response.status });
        }
        
        // For binary files (like zip files), we need to handle differently
        if (!isStatusRequest && response.ok && 
            (contentType.includes('application/zip') || 
             contentType.includes('application/octet-stream'))) {
            
            console.log('Handling as binary file download');
            const contentDisposition = response.headers.get('content-disposition');
            const contentLength = response.headers.get('content-length');
            
            // Use streaming instead of loading the entire blob into memory
            const { readable, writable } = new TransformStream();
            response.body.pipeTo(writable).catch(err => {
                console.error('Error streaming response:', err);
            });
            
            const newResponse = new Response(readable);
            
            // Copy all relevant headers
            if (contentType) newResponse.headers.set('content-type', contentType);
            if (contentDisposition) newResponse.headers.set('content-disposition', contentDisposition);
            if (contentLength) newResponse.headers.set('content-length', contentLength);
            
            return newResponse;
        }
        
        // For JSON responses (status requests or errors)
        try {
            if (contentType.includes('application/json')) {
                const data = await response.json();
                return Response.json(data, { status: response.status });
            } else {
                // If not JSON but text, try to parse it
                const text = await response.text();
                console.log(`Response text (first 200 chars): ${text.substring(0, 200)}`);
                
                // Try to parse as JSON if it looks like JSON
                if (text.trim().startsWith('{') || text.trim().startsWith('[')) {
                    try {
                        const jsonData = JSON.parse(text);
                        return Response.json(jsonData, { status: response.status });
                    } catch (parseError) {
                        console.error('Failed to parse text as JSON:', parseError);
                    }
                }
                
                // Return as error with the text
                return Response.json({ 
                    error: 'Server returned non-JSON response', 
                    status: response.status,
                    statusText: response.statusText,
                    responseText: text.substring(0, 500) // Include part of the response for debugging
                }, { status: response.ok ? 200 : 500 });
            }
        } catch (jsonError) {
            // If response is not valid JSON, return a proper error
            console.error(`Invalid JSON response from ${API_URL}/download/${pathString}:`, jsonError);
            const text = await response.text();
            console.error(`Response text:`, text.substring(0, 200) + '...');
            return Response.json({ 
                error: 'Invalid response from server', 
                status: response.status,
                statusText: response.statusText
            }, { status: 500 });
        }
    } catch (error) {
        console.error(`Error proxying request to ${API_URL}/download/${pathString}:`, error);
        return Response.json({ 
            error: 'Failed to proxy request: ' + error.message,
            details: error.toString()
        }, { status: 500 });
    }
}
  
export async function POST(request) {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || 'http://localhost:8000';
    const url = `${API_URL}/api/download`;
    
    console.log(`Proxying POST request to: ${url}`);
    console.log(`Environment API_URL: ${process.env.API_URL}`);
    console.log(`Environment NEXT_PUBLIC_API_URL: ${process.env.NEXT_PUBLIC_API_URL}`);
    console.log(`Full URL being used: ${url}`);
    
    try {
        const body = await request.json();
        console.log('Request body:', body);
        
        // Check if this is an LTK URL
        const isLtkUrl = body.url && (
            body.url.includes('shopltk.com') || 
            body.url.includes('liketoknow.it') ||
            body.url.includes('ltk.app')
        );
        
        if (isLtkUrl) {
            console.log('Detected LTK URL:', body.url);
        }
        
        // Add timeout to prevent hanging requests
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minute timeout
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            body: JSON.stringify(body),
            signal: controller.signal
        }).catch(error => {
            if (error.name === 'AbortError') {
                throw new Error('Request timed out after 5 minutes');
            }
            throw error;
        });
        
        // Clear the timeout
        clearTimeout(timeoutId);
        
        const contentType = response.headers.get('content-type') || '';
        console.log(`Response status: ${response.status}, Content-Type: ${contentType}`);
        
        if (!response.ok) {
            console.error(`Error response from API: ${response.status} ${response.statusText}`);
            // Try to get error details
            let errorDetails = '';
            try {
                if (contentType.includes('application/json')) {
                    const errorData = await response.json();
                    errorDetails = JSON.stringify(errorData);
                } else {
                    errorDetails = await response.text();
                }
            } catch (e) {
                errorDetails = 'Could not parse error response';
            }
            
            return Response.json({ 
                error: `API returned error: ${response.status} ${response.statusText}`,
                details: errorDetails
            }, { status: response.status });
        }
        
        try {
            if (contentType.includes('application/json')) {
                const data = await response.json();
                return Response.json(data, { status: response.status });
            } else {
                // If not JSON but text, try to parse it
                const text = await response.text();
                console.log(`Response text (first 200 chars): ${text.substring(0, 200)}`);
                
                // Try to parse as JSON if it looks like JSON
                if (text.trim().startsWith('{') || text.trim().startsWith('[')) {
                    try {
                        const jsonData = JSON.parse(text);
                        return Response.json(jsonData, { status: response.status });
                    } catch (parseError) {
                        console.error('Failed to parse text as JSON:', parseError);
                    }
                }
                
                // Return as error with the text
                return Response.json({ 
                    error: 'Server returned non-JSON response', 
                    status: response.status,
                    statusText: response.statusText,
                    responseText: text.substring(0, 500) // Include part of the response for debugging
                }, { status: response.ok ? 200 : 500 });
            }
        } catch (jsonError) {
            // If response is not valid JSON, return a proper error
            console.error(`Invalid JSON response from ${url}:`, jsonError);
            const text = await response.text();
            console.error(`Response text:`, text.substring(0, 200) + '...');
            return Response.json({ 
                error: 'Invalid response from server', 
                status: response.status,
                statusText: response.statusText
            }, { status: 500 });
        }
    } catch (error) {
        console.error(`Error proxying POST request to ${url}:`, error);
        return Response.json({ 
            error: 'Failed to proxy request: ' + error.message,
            details: error.toString()
        }, { status: 500 });
    }
}