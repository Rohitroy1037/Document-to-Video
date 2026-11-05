# Document to Video AI

Turn PDF and PowerPoint documents into narrated videos, with source-page previews and document-grounded chat.

## Requirements

- Python
- Node.js and npm
- FFmpeg available on `PATH` for video rendering
- A Groq API key

## Run locally

1. Configure the backend key:

   ```powershell
   Copy-Item backend\.env.example backend\.env
   ```

   Set `GROQ_API_KEY` in `backend\.env`.

2. Install and start the backend:

   ```powershell
   py -m venv backend\.venv
   backend\.venv\Scripts\Activate.ps1
   pip install -r backend\requirements.txt
   Set-Location backend
   uvicorn app.main:app --reload
   ```

   The API is available at `http://127.0.0.1:8000`.

3. In a second terminal, install and start the frontend:

   ```powershell
   Set-Location frontend\frontend-temp
   npm ci
   npm run dev
   ```

   Open `http://localhost:3000`.

Uploaded documents, generated media, and local embedding caches are stored under `backend\storage` and are excluded from Git.
