"use client";



import {

  useCallback,

  useEffect,

  useMemo,

  useRef,

  useState,

} from "react";



import dynamic from "next/dynamic";
import type { PDFDocumentProxy } from "pdfjs-dist";
import DocumentChat from "./DocumentChat";
import { API_URL } from "./api-url";



const PdfViewer = dynamic(() => import("./PdfViewer"), {

  ssr: false,

  loading: () => (

    <div className="p-8 text-center text-gray-400">

      Loading PDF viewer...

    </div>

  ),

});



type StageStatus =

  | "pending"

  | "running"

  | "completed"

  | "failed";



type Stage = {

  name: string;

  status: StageStatus;

};



type Scene = {

  scene_number?: number;

  source_page?: number;

  page_number?: number;

  duration?: number;

  audio_duration?: number;

  narration?: string;

  text?: string;

};



const INITIAL_STAGES: Stage[] = [

  { name: "Upload document", status: "pending" },

  { name: "Analyze document", status: "pending" },

  { name: "Create narration script", status: "pending" },

  { name: "Translate narration", status: "pending" },

  { name: "Plan scenes", status: "pending" },

  { name: "Generate voiceover", status: "pending" },

  { name: "Render video", status: "pending" },

];



async function apiRequest(

  endpoint: string,

  options: RequestInit = {}

): Promise<any> {

  let response: Response;



  try {

    response = await fetch(`${API_URL}${endpoint}`, options);

  } catch {

    throw new Error(

      "Backend is not responding. Start FastAPI at http://127.0.0.1:8000."

    );

  }



  const text = await response.text();



  let result: any = {};



  try {

    result = text ? JSON.parse(text) : {};

  } catch {

    result = { detail: text };

  }



  if (!response.ok) {

    throw new Error(

      typeof result.detail === "string"

        ? result.detail

        : `Request failed: ${endpoint} (${response.status})`

    );

  }



  return result;

}



function getScenePage(scene: Scene): number {

  const page = Number(

    scene.source_page ?? scene.page_number ?? 1

  );



  return Number.isFinite(page) && page >= 1

    ? Math.floor(page)

    : 1;

}



function getSceneDuration(scene: Scene): number {

  const duration = Number(

    scene.audio_duration ?? scene.duration ?? 0

  );



  return Number.isFinite(duration) && duration > 0

    ? duration

    : 0;

}



export default function Home() {

  const fileInputRef = useRef<HTMLInputElement>(null);

  const videoRef = useRef<HTMLVideoElement>(null);

  const pagePanelRef = useRef<HTMLDivElement>(null);

  const lastPageRef = useRef(1);



  const [file, setFile] = useState<File | null>(null);
  const [chatSessionKey, setChatSessionKey] = useState(0);

  const [language, setLanguage] = useState("hinglish");

  const [voiceStyle, setVoiceStyle] = useState("friendly");

  const [visualStyle, setVisualStyle] = useState("cinematic");



  const [stages, setStages] =

    useState<Stage[]>(INITIAL_STAGES);



  const [isGenerating, setIsGenerating] = useState(false);
  const [isPreparingChat, setIsPreparingChat] = useState(false);
  const [error, setError] = useState("");

  const [message, setMessage] = useState(

    "Upload a document to get started."

  );



  const [documentId, setDocumentId] = useState("");

  const [videoUrl, setVideoUrl] = useState("");

  const [subtitleUrl, setSubtitleUrl] = useState("");
  const [subtitleTrackUrl, setSubtitleTrackUrl] = useState("");
  const [subtitlesEnabled, setSubtitlesEnabled] = useState(true);



  const [sceneTimeline, setSceneTimeline] = useState<Scene[]>([]);

  const [currentPage, setCurrentPage] = useState(1);

  const [pageCount, setPageCount] = useState(0);

  const [pdfError, setPdfError] = useState("");

  const [videoTime, setVideoTime] = useState(0);



  const [dragging, setDragging] = useState(false);



  const isPdf =

    file?.name.toLowerCase().endsWith(".pdf") ?? false;



  const pdfFile = useMemo(

    () => (isPdf ? file : null),

    [isPdf, file]

  );



  const updateStage = (

    index: number,

    status: StageStatus

  ) => {

    setStages((previous) =>

      previous.map((stage, i) =>

        i === index ? { ...stage, status } : stage

      )

    );

  };



  function selectFile(selectedFile: File | null) {

    if (!selectedFile) return;



    const lowerName = selectedFile.name.toLowerCase();



    if (

      !lowerName.endsWith(".pdf") &&

      !lowerName.endsWith(".pptx")

    ) {

      setError(

        "Please select a PDF or PPTX file. PPT files are not supported by the current backend."

      );

      return;

    }



    if (selectedFile.size > 50 * 1024 * 1024) {

      setError("Maximum file size is 50 MB.");

      return;

    }



    setFile(selectedFile);
    setChatSessionKey((key) => key + 1);

    setError("");

    setPdfError("");

    setMessage("Document selected. Ready to generate video.");



    setDocumentId("");

    setVideoUrl("");

    setSubtitleUrl("");

    setSceneTimeline([]);



    setCurrentPage(1);

    setPageCount(0);

    setVideoTime(0);

    lastPageRef.current = 1;

  }



  function resetProject() {

    if (isGenerating) return;



    setFile(null);
    setChatSessionKey((key) => key + 1);

    setError("");

    setPdfError("");

    setDocumentId("");

    setVideoUrl("");

    setSubtitleUrl("");

    setSceneTimeline([]);

    setCurrentPage(1);

    setPageCount(0);

    setVideoTime(0);

    lastPageRef.current = 1;

    setStages(INITIAL_STAGES);

    setMessage("Upload a document to get started.");



    if (fileInputRef.current) {

      fileInputRef.current.value = "";

    }

  }

  async function prepareDocumentForChat(): Promise<string> {
    if (documentId) return documentId;
    if (!file) {
      throw new Error("Please select a PDF or PPTX first.");
    }

    setIsPreparingChat(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const uploadResult = await apiRequest("/upload", {
        method: "POST",
        body: formData,
      });
      const id = uploadResult.document_id;
      if (!id) {
        throw new Error("Backend did not return document_id.");
      }
      setDocumentId(id);
      return id;
    } finally {
      setIsPreparingChat(false);
    }
  }


  async function generateVideo() {

    if (!file) {

      setError("Please upload a PDF or PPTX first.");

      return;

    }



    setIsGenerating(true);
    setError("");
    setPdfError("");
    setVideoUrl("");

    setSubtitleUrl("");

    setSceneTimeline([]);

    setCurrentPage(1);

    setPageCount(0);

    setVideoTime(0);

    lastPageRef.current = 1;



    setStages(

      INITIAL_STAGES.map((stage) => ({

        ...stage,

        status: "pending",

      }))

    );



    try {

      // 1. Upload

      setMessage("Uploading document...");

      updateStage(0, "running");



      let id = documentId;

      if (!id) {
        const formData = new FormData();
        formData.append("file", file);

        const uploadResult = await apiRequest("/upload", {
          method: "POST",
          body: formData,
        });

        id = uploadResult.document_id;
      }



      if (!id) {

        throw new Error("Backend did not return document_id.");

      }



      setDocumentId(id);

      updateStage(0, "completed");



      // 2. Analyze

      setMessage("Analyzing document...");

      updateStage(1, "running");



      await apiRequest(`/analyze/${id}`, {

        method: "POST",

      });



      updateStage(1, "completed");



      // 3. Script

      setMessage("Creating narration script...");

      updateStage(2, "running");



      await apiRequest(`/script/${id}`, {

        method: "POST",

      });



      updateStage(2, "completed");



      // 4. Translate

      setMessage(`Translating narration into ${language}...`);

      updateStage(3, "running");



      await apiRequest(`/translate/${id}/${language}`, {

        method: "POST",

      });



      updateStage(3, "completed");



      // 5. Create scene plan

      setMessage("Planning document scenes...");

      updateStage(4, "running");



      const sceneResult = await apiRequest(

        `/scenes/${id}/${language}`,

        { method: "POST" }

      );



      const plannedScenes: Scene[] = Array.isArray(

        sceneResult?.scene_plan?.scenes

      )

        ? sceneResult.scene_plan.scenes

        : [];



      updateStage(4, "completed");



      // 6. Generate audio

      setMessage("Generating narration audio...");

      updateStage(5, "running");



      const audioResult = await apiRequest(

        `/audio/${id}/${language}`,

        { method: "POST" }

      );



      updateStage(5, "completed");



      const audioScenes: Scene[] = Array.isArray(

        audioResult?.scenes

      )

        ? audioResult.scenes

        : [];



      // Match audio duration with each planned scene.

      const mergedScenes: Scene[] = plannedScenes.map(

        (scene, index) => {

          const number = Number(

            scene.scene_number ?? index + 1

          );



          const audioScene =

            audioScenes.find(

              (item) =>

                Number(item.scene_number ?? -1) === number

            ) ?? audioScenes[index];



          return {

            ...scene,

            scene_number: number,

            duration:

              getSceneDuration(audioScene ?? {}) ||

              getSceneDuration(scene),

          };

        }

      );



      console.log("Planned scenes:", plannedScenes);

      console.log("Audio scenes:", audioScenes);

      console.log("Merged scene timeline:", mergedScenes);



      setSceneTimeline(mergedScenes);



      // 7. Render video

      setMessage("Rendering the final video...");

      updateStage(6, "running");



      const videoResult = await apiRequest(

        `/video/${id}/${language}`,

        { method: "POST" }

      );



      updateStage(6, "completed");



      const filename = `${id}_${language}.mp4`;



      setVideoUrl(

        `${API_URL}/videos/${encodeURIComponent(filename)}`

      );



      if (videoResult.subtitle_file) {

        setSubtitleUrl(

          `${API_URL}/subtitles/${encodeURIComponent(

            `${id}_${language}.srt`

          )}`

        );

      }



      setMessage("Your video was generated successfully!");

    } catch (err) {

      const reason =

        err instanceof Error

          ? err.message

          : "An unexpected error occurred.";



      setError(reason);

      setMessage("Video generation failed.");



      setStages((previous) =>

        previous.map((stage) =>

          stage.status === "running"

            ? { ...stage, status: "failed" }

            : stage

        )

      );

    } finally {

      setIsGenerating(false);

    }

  }



  // Keep the PDF page synchronized with video playback.

  const syncPdfToVideoTime = useCallback(

    (time: number, videoDuration: number) => {

      setVideoTime(time);



      if (sceneTimeline.length === 0) {

        return;

      }



      const allDurationsValid = sceneTimeline.every(

        (scene) => getSceneDuration(scene) > 0

      );



      let matchedIndex = 0;



      if (allDurationsValid) {

        let elapsed = 0;



        for (let i = 0; i < sceneTimeline.length; i++) {

          const duration = getSceneDuration(

            sceneTimeline[i]

          );



          if (time < elapsed + duration) {

            matchedIndex = i;

            break;

          }



          elapsed += duration;

          matchedIndex = i;

        }

      } else if (videoDuration > 0) {

        const approximateSceneDuration =

          videoDuration / sceneTimeline.length;



        matchedIndex = Math.min(

          Math.floor(time / approximateSceneDuration),

          sceneTimeline.length - 1

        );

      }



      const nextPage = getScenePage(

        sceneTimeline[matchedIndex]

      );



      if (nextPage !== lastPageRef.current) {

        console.log(

          `Video ${time.toFixed(1)}s -> scene ${

            matchedIndex + 1

          } -> PDF page ${nextPage}`

        );



        lastPageRef.current = nextPage;

        setCurrentPage(nextPage);



        pagePanelRef.current?.scrollTo({

          top: 0,

          behavior: "smooth",

        });

      }

    },

    [sceneTimeline]

  );



  const handlePdfLoad = useCallback(

    (pdf: PDFDocumentProxy) => {

      setPageCount(pdf.numPages);

      setPdfError("");

    },

    []

  );



  const handlePdfError = useCallback((reason: Error) => {

    setPdfError(reason.message || "Could not load PDF.");

  }, []);



  // Convert the backend's SRT file to WebVTT, which browsers support as a track.
  useEffect(() => {
    let objectUrl = "";
    let cancelled = false;

    async function loadSubtitleTrack() {
      setSubtitleTrackUrl("");
      if (!subtitleUrl) return;
      try {
        const response = await fetch(subtitleUrl);
        if (!response.ok) throw new Error(`Could not load subtitles (${response.status}).`);
        const srtText = await response.text();
        const vttText = "WEBVTT\n\n" + srtText
          .replace(/^\uFEFF/, "")
          .replace(/(\d{2}:\d{2}:\d{2}),(\d{3})/g, "$1.$2");
        const blob = new Blob([vttText], { type: "text/vtt;charset=utf-8" });
        objectUrl = URL.createObjectURL(blob);
        if (!cancelled) setSubtitleTrackUrl(objectUrl);
      } catch (error) {
        console.error("Subtitle track could not be loaded:", error);
      }
    }

    void loadSubtitleTrack();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [subtitleUrl]);

  // Toggle captions without pausing or restarting the video.
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const applySubtitleMode = () => {
      const track = video.textTracks?.[0];
      if (track) track.mode = subtitlesEnabled ? "showing" : "disabled";
    };
    applySubtitleMode();
    video.addEventListener("loadedmetadata", applySubtitleMode);
    return () => video.removeEventListener("loadedmetadata", applySubtitleMode);
  }, [subtitleTrackUrl, subtitlesEnabled, videoUrl]);

  return (

    <main className="studio-shell min-h-screen">

      <div className="mx-auto max-w-[1440px] px-5 py-6 md:px-8">

        {/* Header */}

        <header className="mb-10 flex flex-wrap items-center justify-between gap-4 border-b border-[#dedfd6] pb-5">

          <div className="flex items-center gap-3">

            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#294d42] text-sm font-bold tracking-wide text-white">
              DM

            </div>



            <div>

              <h1 className="text-lg font-semibold tracking-tight text-[#202a26]">
                DocuMotion

              </h1>

              <p className="text-xs text-[#68716d]">
                Document studio

              </p>

            </div>

          </div>



          <span className="rounded-full border border-[#dedfd6] bg-white px-3 py-1.5 text-xs font-medium text-[#68716d]">
            Workspace

          </span>

        </header>



        {/* Intro */}

        <section className="mb-9 max-w-3xl">
          <span className="inline-flex text-xs font-semibold uppercase tracking-[0.16em] text-[#60766b]">
            DOCUMENT VIDEO WORKSPACE

          </span>



          <h2 className="mt-4 max-w-3xl text-4xl font-medium leading-[1.08] text-[#202a26] md:text-6xl">
            Make a thoughtful video from{" "}
            <span className="text-[#a45a3d]">
              your documents.

            </span>

          </h2>



          <p className="mt-5 max-w-2xl text-base leading-7 text-[#68716d] md:text-lg">
            Bring a PDF or presentation. Build a narrated video, keep the source
            close, and ask questions as you work.

          </p>

        </section>



        <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">

          {/* Configuration */}

          <section className="studio-card rounded-3xl border border-white/10 bg-[#11111b]/90 p-5 md:p-7">

            <h3 className="text-lg font-semibold">

              Create a new video

            </h3>



            <p className="mt-1 text-sm text-gray-400">

              Configure your document and narration.

            </p>



            <div

              onDragOver={(event) => {

                event.preventDefault();

                setDragging(true);

              }}

              onDragLeave={() => setDragging(false)}

              onDrop={(event) => {

                event.preventDefault();

                setDragging(false);

                selectFile(

                  event.dataTransfer.files?.[0] ?? null

                );

              }}

              onClick={() => {

                if (!isGenerating) {

                  fileInputRef.current?.click();

                }

              }}

              className={`mt-6 cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition ${

                dragging

                  ? "border-purple-400 bg-purple-500/10"

                  : "border-white/15 bg-white/[0.02] hover:border-purple-400/60"

              }`}

            >

              <input

                ref={fileInputRef}

                type="file"

                accept=".pdf,.pptx"

                className="hidden"

                disabled={isGenerating}

                onChange={(event) =>

                  selectFile(event.target.files?.[0] ?? null)

                }

              />



              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-purple-500/15 text-3xl">

                {file ? "📄" : "↑"}

              </div>



              <p className="font-medium">

                {file ? file.name : "Drop your document here"}

              </p>



              <p className="mt-2 text-sm text-gray-400">

                {file

                  ? `${(file.size / 1048576).toFixed(2)} MB`

                  : "or click to browse"}

              </p>



              <p className="mt-4 text-xs text-gray-500">

                PDF · PPTX · Maximum 50 MB

              </p>

            </div>



            <div className="mt-6">

              <label

                htmlFor="language"

                className="mb-2 block text-sm font-medium"

              >

                Narration language

              </label>



              <select

                id="language"

                value={language}

                disabled={isGenerating}

                onChange={(event) =>

                  setLanguage(event.target.value)

                }

                className="w-full rounded-xl border border-white/10 bg-[#191925] px-4 py-3 text-sm outline-none focus:border-purple-400"

              >

                <option value="english">English</option>

                <option value="hindi">Hindi</option>

                <option value="hinglish">Hinglish</option>

              </select>

            </div>



            <div className="mt-5">

              <label

                htmlFor="voiceStyle"

                className="mb-2 block text-sm font-medium"

              >

                Narration style

              </label>



              <select

                id="voiceStyle"

                value={voiceStyle}

                disabled={isGenerating}

                onChange={(event) =>

                  setVoiceStyle(event.target.value)

                }

                className="w-full rounded-xl border border-white/10 bg-[#191925] px-4 py-3 text-sm outline-none focus:border-purple-400"

              >

                <option value="friendly">

                  Friendly and explanatory

                </option>

                <option value="professional">

                  Professional

                </option>

                <option value="educational">Educational</option>

                <option value="storytelling">Storytelling</option>

              </select>



              <p className="mt-2 text-xs text-gray-500">

                This setting is not yet connected to the backend.

              </p>

            </div>



            <div className="mt-5">

              <label

                htmlFor="visualStyle"

                className="mb-2 block text-sm font-medium"

              >

                Visual style

              </label>



              <select

                id="visualStyle"

                value={visualStyle}

                disabled={isGenerating}

                onChange={(event) =>

                  setVisualStyle(event.target.value)

                }

                className="w-full rounded-xl border border-white/10 bg-[#191925] px-4 py-3 text-sm outline-none focus:border-purple-400"

              >

                <option value="cinematic">Cinematic motion</option>

                <option value="minimal">Minimal and clean</option>

                <option value="educational">

                  Educational slides

                </option>

              </select>



              <p className="mt-2 text-xs text-gray-500">

                This setting is not yet connected to the backend.

              </p>

            </div>



            <button

              onClick={generateVideo}

              disabled={!file || isGenerating}

              className="mt-8 flex w-full items-center justify-center gap-3 rounded-xl bg-[#294d42] px-5 py-4 font-semibold text-white transition hover:bg-[#25473c] disabled:cursor-not-allowed disabled:opacity-40"

            >

              {isGenerating ? (

                <>

                  <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />

                  Generating video...

                </>

              ) : (

                "✦ Generate Video"

              )}

            </button>



            <button

              onClick={resetProject}

              disabled={isGenerating}

              className="mt-3 w-full rounded-xl border border-white/10 px-5 py-3 text-sm text-gray-400 hover:bg-white/5 disabled:opacity-40"

            >

              Reset project

            </button>

          </section>



          {/* Results */}

          <section className="space-y-6">

            {/* Progress */}

            <div className="studio-card rounded-3xl border border-white/10 bg-[#11111b]/90 p-5 md:p-7">

              <div className="mb-5 flex items-center justify-between gap-3">

                <div>

                  <h3 className="text-lg font-semibold">

                    Generation status

                  </h3>

                  <p className="mt-1 text-sm text-gray-400">

                    Follow each processing stage.

                  </p>

                </div>



                <span className="rounded-full bg-white/5 px-3 py-1 text-xs text-gray-300">

                  {error

                    ? "Failed"

                    : stages.every(

                          (stage) =>

                            stage.status === "completed"

                        )

                      ? "Completed"

                      : isGenerating

                        ? "Processing"

                        : "Ready"}

                </span>

              </div>



              <div className="space-y-4">

                {stages.map((stage, index) => (

                  <div key={stage.name} className="flex gap-3">

                    <div

                      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-sm ${

                        stage.status === "completed"

                          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"

                          : stage.status === "running"

                            ? "border-purple-400/40 bg-purple-500/15 text-purple-300"

                            : stage.status === "failed"

                              ? "border-red-500/30 bg-red-500/10 text-red-300"

                              : "border-white/10 text-gray-500"

                      }`}

                    >

                      {stage.status === "completed"

                        ? "✓"

                        : stage.status === "running"

                          ? "…"

                          : stage.status === "failed"

                            ? "!"

                            : index + 1}

                    </div>



                    <div className="pt-1">

                      <p className="text-sm text-gray-200">

                        {stage.name}

                      </p>

                    </div>

                  </div>

                ))}

              </div>



              <div className="mt-6 rounded-xl border border-white/10 bg-white/[0.03] p-4">

                <p className="mb-1 text-xs uppercase tracking-wider text-gray-500">

                  Current status

                </p>

                <p className="text-sm leading-6 text-gray-300">

                  {message}

                </p>

              </div>



              {error && (

                <div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/[0.07] p-4 text-sm leading-6 text-red-200">

                  {error}

                </div>

              )}

            </div>



            {/* Video */}

            <div className="studio-card rounded-3xl border border-white/10 bg-[#11111b]/90 p-5 md:p-7">

              <h3 className="text-lg font-semibold">

                Video preview

              </h3>



              <p className="mt-1 text-sm text-gray-400">

                Play or seek the video to synchronize the source

                document.

              </p>



              {videoUrl ? (

                <>

                  <video

                    ref={videoRef}

                    key={videoUrl}

                    controls

                    playsInline

                    onTimeUpdate={(event) =>

                      syncPdfToVideoTime(

                        event.currentTarget.currentTime,

                        event.currentTarget.duration

                      )

                    }

                    onSeeked={(event) =>

                      syncPdfToVideoTime(

                        event.currentTarget.currentTime,

                        event.currentTarget.duration

                      )

                    }

                    onLoadedMetadata={(event) =>

                      syncPdfToVideoTime(

                        event.currentTarget.currentTime,

                        event.currentTarget.duration

                      )

                    }

                    className="mt-5 aspect-video w-full rounded-2xl border border-white/10 bg-black"

                  >

                    <source src={videoUrl} type="video/mp4" />
                    {subtitleTrackUrl && (
                      <track
                        key={subtitleTrackUrl}
                        kind="subtitles"
                        src={subtitleTrackUrl}
                        srcLang={language === "hindi" ? "hi" : "en"}
                        label={language === "hindi" ? "Hindi" : language === "hinglish" ? "Hinglish" : "English"}
                        onLoad={() => {
                          const track = videoRef.current?.textTracks?.[0];
                          if (track) track.mode = subtitlesEnabled ? "showing" : "disabled";
                        }}
                      />
                    )}

                    Your browser does not support video playback.

                  </video>

                  {subtitleUrl && (
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                      <p className="text-sm text-gray-400">
                        Subtitles are {subtitlesEnabled ? "on" : "off"}.
                      </p>
                      <button
                        type="button"
                        onClick={() => setSubtitlesEnabled((enabled) => !enabled)}
                        aria-pressed={subtitlesEnabled}
                        className={`rounded-xl border px-4 py-2 text-sm font-medium transition ${
                          subtitlesEnabled
                            ? "border-purple-400/40 bg-purple-500/15 text-purple-200 hover:bg-purple-500/25"
                            : "border-white/10 bg-white/5 text-gray-300 hover:bg-white/10"
                        }`}
                      >
                        {subtitlesEnabled ? "CC Subtitles: ON" : "CC Subtitles: OFF"}
                      </button>
                    </div>
                  )}



                  <p className="mt-3 text-xs text-gray-500">

                    Playback time: {videoTime.toFixed(1)} seconds

                  </p>



                  <div className="mt-4 flex flex-wrap gap-3">

                    <a

                      href={videoUrl}

                      download={`${documentId}_${language}.mp4`}

                      className="rounded-xl bg-purple-600 px-5 py-3 text-sm font-medium hover:bg-purple-500"

                    >

                      ↓ Download video

                    </a>



                    <a

                      href={videoUrl}

                      target="_blank"

                      rel="noreferrer"

                      className="rounded-xl border border-white/10 px-5 py-3 text-sm text-gray-300 hover:bg-white/5"

                    >

                      Open video

                    </a>



                    {subtitleUrl && (

                      <a

                        href={subtitleUrl}

                        download={`${documentId}_${language}.srt`}

                        className="rounded-xl border border-white/10 px-5 py-3 text-sm text-gray-300 hover:bg-white/5"

                      >

                        Download subtitles

                      </a>

                    )}

                  </div>

                </>

              ) : (

                <div className="mt-5 flex aspect-video flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 bg-black/20 p-6 text-center">

                  <span className="text-3xl">▶</span>

                  <p className="mt-4 font-medium">

                    No video generated yet

                  </p>

                  <p className="mt-2 text-sm text-gray-500">

                    Upload a document and click Generate Video.

                  </p>

                </div>

              )}

            </div>



            {/* PDF */}

            <div className="studio-card rounded-3xl border border-white/10 bg-[#11111b]/90 p-5 md:p-7">

              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">

                <div>

                  <h3 className="text-lg font-semibold">

                    Source document

                  </h3>

                  <p className="mt-1 text-sm text-gray-400">

                    The displayed PDF page follows the current scene.

                  </p>

                </div>



                {isPdf && (

                  <span className="rounded-full bg-purple-500/10 px-3 py-1 text-xs text-purple-300">

                    Page {currentPage}

                    {pageCount > 0 ? ` of ${pageCount}` : ""}

                  </span>

                )}

              </div>



              {pdfFile ? (

                <>

                  <div

                    ref={pagePanelRef}

                    className="max-h-[760px] overflow-auto rounded-2xl border border-white/10 bg-[#09090f] p-3"

                  >

                    <PdfViewer

                      file={pdfFile}

                      pageNumber={currentPage}

                      width={720}

                      onLoadSuccess={handlePdfLoad}

                      onLoadError={handlePdfError}

                    />

                  </div>



                  {pdfError && (

                    <p className="mt-3 text-sm text-red-300">

                      {pdfError}

                    </p>

                  )}



                  <div className="mt-4 flex items-center justify-between gap-3">

                    <button

                      onClick={() => {

                        const page = Math.max(1, currentPage - 1);

                        lastPageRef.current = page;

                        setCurrentPage(page);

                      }}

                      disabled={currentPage <= 1}

                      className="rounded-xl border border-white/10 px-4 py-2 text-sm text-gray-300 disabled:opacity-40"

                    >

                      ← Previous

                    </button>



                    <span className="text-xs text-gray-500">

                      {sceneTimeline.length > 0

                        ? "Scene sync enabled"

                        : "Waiting for scene data"}

                    </span>



                    <button

                      onClick={() => {

                        const page =

                          pageCount > 0

                            ? Math.min(pageCount, currentPage + 1)

                            : currentPage + 1;



                        lastPageRef.current = page;

                        setCurrentPage(page);

                      }}

                      disabled={

                        pageCount > 0 &&

                        currentPage >= pageCount

                      }

                      className="rounded-xl border border-white/10 px-4 py-2 text-sm text-gray-300 disabled:opacity-40"

                    >

                      Next →

                    </button>

                  </div>

                </>

              ) : file ? (

                <div className="rounded-2xl border border-dashed border-white/10 p-8 text-center">

                  <p className="text-3xl">📊</p>

                  <p className="mt-3 font-medium">

                    PowerPoint selected

                  </p>

                  <p className="mt-2 text-sm leading-6 text-gray-400">

                    Direct PDF preview is available for PDF files.

                    PPTX slide preview needs a slide-image endpoint.

                  </p>

                </div>

              ) : (

                <div className="rounded-2xl border border-dashed border-white/10 p-8 text-center text-sm text-gray-500">

                  Select a PDF to preview its pages.

                </div>

              )}

            </div>

          </section>

        </div>

        <DocumentChat
          key={chatSessionKey}
          documentId={documentId}
          documentName={file?.name ?? ""}
          isPreparingDocument={isPreparingChat}
          isGenerating={isGenerating}
          onPrepareDocument={prepareDocumentForChat}
          onCitationClick={(page) => {
            const nextPage = Math.max(
              1,
              pageCount > 0 ? Math.min(pageCount, page) : page
            );
            lastPageRef.current = nextPage;
            setCurrentPage(nextPage);
          }}
        />

        <footer className="mt-12 border-t border-white/10 py-6 text-center text-xs text-gray-500">

          DocuMotion · A quieter way to turn documents into video

        </footer>

      </div>

    </main>

  );

}