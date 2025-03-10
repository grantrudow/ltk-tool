// app/api/proxy/download/route.js
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
        
        // Test direct curl to the backend
        try {
            const testCmd = `curl -X POST -H "Content-Type: application/json" -d '${JSON.stringify(body)}' ${url}`;
            console.log(`Test curl command: ${testCmd}`);
        } catch (e) {
            console.error('Error creating test curl command:', e);
        }
        
        // Add timeout to prevent hanging requests
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
        
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
                throw new Error('Request timed out after 10 seconds');
            }
            throw error;
        });
        
        // Clear the timeout
        clearTimeout(timeoutId);
        
        const contentType = response.headers.get('content-type') || '';
        console.log(`Response status: ${response.status}, Content-Type: ${contentType}`);
        
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