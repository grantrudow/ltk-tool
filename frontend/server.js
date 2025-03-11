const http = require("http");
const PORT = 3000;

const server = http.createServer((req, res) => {
  if (req.url === "/" || req.url === "/index.html") {
    res.writeHead(200, { "Content-Type": "text/html" });
    res.end(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>LTK Downloader</title>
          <style>
            body {
              font-family: Arial, sans-serif;
              max-width: 800px;
              margin: 0 auto;
              padding: 20px;
              line-height: 1.6;
            }
            h1 {
              color: #333;
              border-bottom: 1px solid #eee;
              padding-bottom: 10px;
            }
            .message {
              background-color: #f8f9fa;
              border-left: 4px solid #007bff;
              padding: 15px;
              margin: 20px 0;
            }
            a {
              color: #007bff;
              text-decoration: none;
            }
            a:hover {
              text-decoration: underline;
            }
          </style>
        </head>
        <body>
          <h1>LTK Content Downloader</h1>
          <div class="message">
            <p>The frontend server is running successfully!</p>
            <p>Please use the backend API directly at <a href="http://localhost:8000">http://localhost:8000</a> for testing.</p>
            <p>The frontend Next.js application is having compatibility issues in Docker, but the backend API is fully functional.</p>
          </div>
        </body>
      </html>
    `);
  } else {
    res.writeHead(404);
    res.end("Not found");
  }
});

server.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}/`);
}); 