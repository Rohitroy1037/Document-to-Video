# Document to Video AI

Document to Video AI turns a PDF or PowerPoint presentation into a narrated video. It extracts document text and page visuals, creates and translates a narration script, plans scenes against the source pages, generates voiceover and subtitles, and renders an MP4. You can also ask questions about the selected document and follow citations back to their source pages.

## Contents

- [How it works](#how-it-works)
- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Run locally on Windows](#run-locally-on-windows)
- [Deploy to Vercel and Render](#deploy-to-vercel-and-render)
- [Use the application](#use-the-application)
- [Document chat and RAG](#document-chat-and-rag)
- [HTTP API](#http-api)
- [Generated files](#generated-files)
- [Tests](#tests)
- [Troubleshooting](#troubleshooting)
- [Current limitations](#current-limitations)
- [Privacy and external services](#privacy-and-external-services)

## How it works

The browser frontend calls a local FastAPI backend. Video generation is a sequential pipeline: each step saves its result locally, and a later step depends on the earlier step's output.

```text
PDF/PPTX
   │
   ├─ 1. Upload, extract text, and render each page/slide
   ├─ 2. Analyze the document
   ├─ 3. Create a narration script
   ├─ 4. Translate/adapt the script to the selected language
   ├─ 5. Plan scenes and map them to source pages/slides
   ├─ 6. Synthesize scene-by-scene voiceover and time the scenes
   └─ 7. Render the MP4 and create an SRT subtitle file
```

The frontend displays progress for these stages, a video preview, subtitles, a scene timeline, and the corresponding source page. Generation stops and displays an error if a required stage fails.

## Features

- Upload `.pdf` and `.pptx` files up to **50 MB** through the frontend.
- Extract text from PDF pages and PowerPoint slides; render source visuals for preview and video scenes.
- Generate document analysis and a structured narration script with Groq.
- Choose narration language: **English**, **Hindi**, or **Hinglish**.
- Plan scenes that refer back to the original page or slide.
- Generate a separate voiceover for each scene, synchronize scene durations to the audio, and render an MP4.
- Generate an SRT subtitle file and synchronize the source-page preview with video playback.
- Ask document-specific questions with semantic retrieval and source-page citations.
- Keep uploaded documents, rendered pages, indexes, audio, subtitles, and videos in local storage.

## Architecture

| Area | Location | Responsibility |
|---|---|---|
| Web application | `frontend/frontend-temp/` | Next.js interface, upload, generation progress, source/video preview, and chat |
| API application | `backend/app/main.py` | FastAPI app, CORS for local development, health endpoint, static video/subtitle serving, and router registration |
| API routes | `backend/app/api/` | Upload, analyze, script, translation, scenes, audio, video, and chat endpoints |
| Processing services | `backend/app/services/` | PDF/PPTX parsing, AI prompts, embeddings/retrieval, speech synthesis, subtitles, and FFmpeg rendering |
| Request/response schemas | `backend/app/schemas/` | Pydantic request and document models |
| Automated backend tests | `backend/test_*.py` | Unit tests for parsing and selected AI/retrieval helpers |
| Runtime data | `backend/storage/` | Uploaded files, extracted text, model/index caches, rendered media, and intermediate pipeline results; ignored by Git |

## Requirements

- Windows (the current PowerPoint-to-image renderer expects LibreOffice at `C:\Program Files\LibreOffice\program\soffice.exe`).
- Python and `pip`.
- Node.js and npm.
- [FFmpeg](https://ffmpeg.org/) available on `PATH` for MP4 rendering.
- [LibreOffice](https://www.libreoffice.org/) installed at the path above to convert PPTX files to PDF for slide rendering.
- A [Groq API key](https://console.groq.com/keys).
- An internet connection for Groq requests, Edge TTS voice synthesis, package installation, and the first download of the local embedding model.

Check that FFmpeg is on `PATH` from PowerShell:

```powershell
ffmpeg -version
```

## Run locally on Windows

Open PowerShell in the repository root.

### 1. Configure the Groq API key

Create your local environment file from the example:

```powershell
Copy-Item backend\.env.example backend\.env
notepad backend\.env
```

Replace the placeholder with your own key:

```dotenv
GROQ_API_KEY=your_groq_api_key
```

Do not commit `backend\.env` or paste the key into source code. The root `.gitignore` excludes local environment files.

### 2. Install and start the backend

In the first PowerShell terminal:

```powershell
py -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
Set-Location backend
python -m uvicorn app.main:app --reload
```

If PowerShell prevents virtual-environment activation, either allow it for the current terminal with `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, or call `backend\.venv\Scripts\python.exe` directly for the install and server commands.

The backend runs at `http://127.0.0.1:8000`. Check `http://127.0.0.1:8000/health` for a JSON health response. Interactive API documentation is at `http://127.0.0.1:8000/docs`.

Run Uvicorn from the `backend` directory: the application uses relative `storage/...` paths, so the working directory determines where generated files are saved.

### 3. Install and start the frontend

Open a second PowerShell terminal in the repository root:

```powershell
Set-Location frontend\frontend-temp
npm ci
npm run dev
```

Open `http://localhost:3000`. Keep both development servers running while using the app.

To make a production frontend build, run `npm run build` in `frontend\frontend-temp`. To serve that build locally, use `npm run start` from the same directory.

## Deploy to Vercel and Render

The frontend is a Next.js app and deploys to Vercel. The FastAPI backend uses FFmpeg, LibreOffice, and local generated files, so it deploys as a Docker web service on Render. The repository includes `render.yaml` and `backend/Dockerfile` for the backend deployment.

### 1. Deploy the frontend to Vercel

1. Sign in to [Vercel](https://vercel.com/) and import this GitHub repository.
2. Set **Root Directory** to `frontend/frontend-temp`. Vercel should detect Next.js automatically.
3. Keep the default install and build commands (`npm install`/`npm ci` and `npm run build`).
4. Deploy the frontend. Its first deployment can use the local API fallback; API requests will work after you set the Render URL in step 3.
5. Copy the production domain Vercel assigns, for example `https://your-project.vercel.app`.

### 2. Deploy the backend to Render

1. Sign in to [Render](https://render.com/) and create a **Blueprint** from this GitHub repository. Render reads `render.yaml` from the repository root.
2. Confirm the service named `document-to-video-api` uses the Docker runtime, `backend` as its root directory, and the Free plan.
3. When prompted, set these environment variables:
   - `GROQ_API_KEY`: your Groq API key. Enter it in the Render dashboard only; never commit it to GitHub.
   - `FRONTEND_ORIGINS`: your exact Vercel origin, such as `https://your-project.vercel.app` (no path or trailing slash). Add any additional frontend origins as a comma-separated list.
4. Create the Blueprint and wait for the Docker build and service deploy to complete.
5. Confirm the backend health endpoint responds with JSON at `https://your-render-service.onrender.com/health`.

The Docker image installs FFmpeg and LibreOffice and runs the API on Render's assigned port. The backend uses `FRONTEND_ORIGINS` for browser CORS; if it is unset during local development, the two local Next.js origins are allowed.

### 3. Connect Vercel to the deployed backend

After Render gives you the backend URL:

1. Open the Vercel project's **Settings → Environment Variables**.
2. Add `NEXT_PUBLIC_API_URL` with the full Render service origin, such as `https://your-render-service.onrender.com` (no trailing slash). This is a public URL, not a secret.
3. Apply it to the **Production** environment and redeploy the frontend so the URL is included in the Next.js build.
4. Open the Vercel site, upload a small text-based PDF, and verify chat/video requests reach the Render service.

The frontend reads `NEXT_PUBLIC_API_URL` at build time. Updating the variable without creating a new Vercel deployment does not change the already-built JavaScript.

### Free-tier behavior and public demo limits

- Render Free web services sleep after 15 minutes without traffic. The first request after sleep can take about a minute while the service starts.
- Render Free has an ephemeral filesystem and no persistent disks. Uploaded documents, intermediate pipeline files, the downloaded chat model, chat indexes, subtitles, and videos can be erased whenever the service sleeps, restarts, or redeploys. This deployment is for demos; files are not durable.
- The embedding model downloads on the first chat request after the service starts. Video rendering and embedding can be resource-intensive; if the service runs out of memory or requests time out, move the backend to a paid Render instance or use external object storage and a suitable compute plan.
- There is no user login. The backend applies shared, in-memory limits of 20 uploads per hour, 30 generation-stage requests per hour, and 60 chat requests per hour across all visitors on that running instance. These limits reset when the service restarts and are not an authentication system or a guaranteed billing cap.
- Configure usage alerts or spending limits for your Groq account. Do not upload sensitive or confidential documents to a public demo.
- Vercel preview deployments use different origins. If you want them to call Render, add their exact origin to `FRONTEND_ORIGINS` and redeploy the backend.

## Use the application

1. Open the frontend and select a PDF or PPTX (maximum 50 MB).
2. Select English, Hindi, or Hinglish narration.
3. Optionally select a narration style or visual style. These controls are currently visual placeholders and do not change backend generation.
4. Select **Generate Video**. The app uploads the document if it has not already been uploaded, then runs the seven pipeline stages in order.
5. When complete, play or seek the video. The displayed source page follows the current scene; use the SRT subtitle track when available.
6. Ask questions in **Chat with your document**. If the selected file has not been uploaded yet, the first question uploads it before requesting an answer. Click a citation to navigate to its source page.

The initial upload returns a document ID. The frontend keeps it for subsequent pipeline requests and chat. If you reset the project or reload the browser, you may need to select and upload the file again.

## Document chat and RAG

Chat uses a retrieval-augmented generation (RAG) flow:

1. The backend reads the uploaded document's extracted page/slide text.
2. A local FastEmbed multilingual embedding model splits the text into overlapping chunks and embeds them. The model is downloaded and cached under `backend\storage\chat_models` on first use; a document's chunk index is cached under `backend\storage\chat_indexes`.
3. The question embedding is compared with the document chunks, and the four most relevant passages are retrieved.
4. The backend sends the question, recent chat history, and retrieved passages to Groq for a concise answer.
5. Citations are attached from the retrieved passages, with page/slide numbers and excerpts. Selecting a citation navigates the source preview.

The embedding search runs locally. The question and retrieved excerpts are sent to Groq to generate the response; chat is grounded in the uploaded document, and the assistant is instructed to say when the retrieved text does not answer the question.

The chat request accepts a question up to 1,500 characters and up to eight history messages. A document can produce at most 2,000 indexed text chunks. The first chat request can take longer while the local model downloads and creates the document index.

## HTTP API

All API routes are served by the FastAPI backend at `http://127.0.0.1:8000`. Except for chat, generation endpoints use the document ID returned by `/upload`. Run the earlier stages first; later endpoints return an error if required intermediate data is missing.

| Method and route | Input | Purpose and prerequisite |
|---|---|---|
| `GET /health` | None | Backend health check |
| `POST /upload` | Multipart form field `file` | Accepts a PDF or PPTX; saves the upload, extracts text, and renders page/slide images. Returns `document_id`, `document_type`, and `visual_type`. |
| `POST /analyze/{document_id}` | None | Analyze the uploaded document. Run upload first. |
| `POST /script/{document_id}` | None | Create a narration script from the saved analysis. Run analyze first. |
| `POST /translate/{document_id}/{language}` | None | Adapt the script to `english`, `hindi`, or `hinglish`. Run script first. |
| `POST /scenes/{document_id}/{language}` | None | Build a scene plan using the translated script and source pages/slides. Run translate first. |
| `POST /audio/{document_id}/{language}` | None | Generate scene voiceover, measure audio durations, and update the scene plan. Run scenes first. |
| `POST /video/{document_id}/{language}` | None | Render the MP4 and create the SRT file. Requires the scene plan, audio plan, document visuals, and FFmpeg. |
| `POST /chat/{document_id}` | JSON: `{"question":"...","history":[]}` | Retrieve relevant document passages and return an answer with page citations. Upload the document first. |
| `GET /videos/{filename}` | None | Serve a generated MP4. |
| `GET /subtitles/{filename}` | None | Serve a generated SRT subtitle file. |

For exact request schemas and interactive requests, use the local Swagger UI at `http://127.0.0.1:8000/docs`.

### Run the generation pipeline directly

The browser runs these same requests automatically. To call the API yourself, first upload a document with `curl.exe` from PowerShell:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/upload" `
  -F "file=@C:\path\to\document.pdf"
```

Copy the `document_id` from the JSON response into `$documentId`, then call each generation stage in order. Change `english` to `hindi` or `hinglish` if desired:

```powershell
$documentId = "paste-document-id-here"
$language = "english"
$api = "http://127.0.0.1:8000"

Invoke-RestMethod "$api/analyze/$documentId" -Method Post
Invoke-RestMethod "$api/script/$documentId" -Method Post
Invoke-RestMethod "$api/translate/$documentId/$language" -Method Post
Invoke-RestMethod "$api/scenes/$documentId/$language" -Method Post
Invoke-RestMethod "$api/audio/$documentId/$language" -Method Post
Invoke-RestMethod "$api/video/$documentId/$language" -Method Post
```

The video response contains the video and subtitle file paths. They are also available from the backend at `/videos/{filename}` and `/subtitles/{filename}`. To ask a document question directly, provide JSON:

```powershell
$body = @{
  question = "What are the main conclusions?"
  history = @()
} | ConvertTo-Json

Invoke-RestMethod "$api/chat/$documentId" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

## Generated files

All paths below are relative to the backend working directory. Files are created as each pipeline stage completes.

| Directory | Contents |
|---|---|
| `storage/uploads/` | Original uploaded PDF/PPTX files |
| `storage/documents/` | Normalized document text and metadata |
| `storage/pages/{document_id}/` | Rendered PDF pages or PPTX slides |
| `storage/analyses/` | Document analysis JSON |
| `storage/scripts/` | Generated narration-script JSON |
| `storage/translations/` | Language-specific script JSON |
| `storage/scenes/` | Scene plans and synchronized scene timings |
| `storage/audio/` | Scene MP3 files and audio plans |
| `storage/videos/` | Final MP4 files and temporary render files |
| `storage/subtitles/` | SRT subtitle files |
| `storage/chat_models/` | Downloaded embedding model cache |
| `storage/chat_indexes/` | Cached per-document text chunks and embeddings |

These are local working files, not a database or hosted storage service. The root `.gitignore` excludes backend storage, virtual environments, dependency folders, and secrets from Git.

## Tests

The backend unit tests use Python's built-in `unittest` runner. From `backend`:

```powershell
python -m unittest test_ai_analyzer test_document_chat test_pdf_parser test_scene_planner test_script_generator
```

`test_pptx_renderer.py` is an interactive manual utility: it asks for the path to a PPTX file and renders its slides into `storage/test_pptx_slides/`. It is not part of the non-interactive unit-test command.

Frontend commands, from `frontend\frontend-temp`:

```powershell
npm run lint
npm run build
```

## Troubleshooting

### Backend is not responding

- Start the backend from the `backend` directory and confirm `http://127.0.0.1:8000/health` returns successfully.
- Keep the backend terminal open; errors are reported there.
- The frontend defaults to `http://127.0.0.1:8000`. Set `NEXT_PUBLIC_API_URL` in the frontend environment to use a different backend URL. The backend CORS configuration allows local origins `localhost:3000` and `127.0.0.1:3000`.

### Missing `GROQ_API_KEY` or Groq errors

- Confirm `backend\.env` exists and contains a valid `GROQ_API_KEY`.
- Restart the backend after changing the environment file.
- Groq model availability, rate limits, and usage quotas are controlled by your Groq account. If an error reports a token limit, try a shorter or smaller document, or retry after the limit resets.

### PPTX upload or rendering fails

- Install LibreOffice and confirm `C:\Program Files\LibreOffice\program\soffice.exe` exists. The current renderer uses this fixed Windows path.
- Confirm the presentation opens and can be converted by LibreOffice.

### MP4 rendering fails

- Confirm `ffmpeg -version` works in the same environment used to launch the backend.
- Restart the backend terminal after adding FFmpeg to `PATH`.
- Check the backend output for the FFmpeg command and error details.

### Chat is slow the first time or cannot find the document

- The first question may download the embedding model and build a local index. Later questions reuse that cache.
- Keep the backend running from its `backend` directory so it can find `storage/documents` and the embedding caches.
- Confirm the document has searchable text. Scanned PDFs without an extractable text layer may not provide text for analysis or chat.
- The Groq key is required for answer generation even though semantic embedding and retrieval run locally.

### Video subtitles are missing

- The video stage creates an SRT file in `storage/subtitles/` and the backend serves it at `/subtitles/{filename}`.
- Confirm the backend is still running and check its terminal for a missing-file or rendering error.

## Current limitations

- The frontend API URL and backend CORS origins are configurable for deployment, but each hosted platform still needs its environment variables set as described above.
- Narration-style and visual-style dropdowns are not yet connected to backend behavior.
- PDF support extracts selectable text; OCR for image-only/scanned PDFs is not implemented.
- Chat indexes only extracted text and returns a maximum of four retrieved passages as citations per answer.
- PPTX slide rendering requires LibreOffice. The Windows app uses its default Windows install path; the Render Docker image includes LibreOffice on Linux.
- Generated assets are stored on the local filesystem and are not currently exposed through user accounts or cloud persistence.

## Privacy and external services

Uploaded files and generated assets are stored under `backend\storage` and are excluded from this repository. On Render Free, this directory is ephemeral and files are lost when the service sleeps, restarts, or redeploys. For AI generation, the backend sends document-derived content to Groq for analysis, script generation, translation, scene planning, and chat answers. Voice synthesis uses Edge TTS and requires network access. Chat embeddings and retrieval run locally, but the question and retrieved passages are sent to Groq to produce the answer.

Review the privacy, retention, and usage terms of external services before using sensitive documents. The public demo does not have user accounts; do not upload sensitive files. Never commit API keys, `.env` files, uploaded documents, or generated media.
