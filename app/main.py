from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Daymark</title>
      </head>
      <body style="font-family: system-ui; padding: 24px;">
        <h1>Daymark</h1>
        <p>A calm reference point for today.</p>
        <p><b>Status:</b> GREEN</p>
      </body>
    </html>
    """
