import json
import shutil
import subprocess
import time

from pathlib import Path


# =========================================================
# VIDEO CONFIGURATION
# =========================================================

FPS = 24

VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720

VIDEO_PRESET = "ultrafast"
VIDEO_CRF = "23"

VIDEO_THREADS = "2"

FFMPEG_TIMEOUT = 1800


# =========================================================
# ANIMATION FILTER
# =========================================================

def get_animation_filter(animation, duration):

    """
    Generate an FFmpeg filter for scene animation.

    Supported animations:
        - zoom_in
        - zoom_out
        - pan_left
        - pan_right
        - static
    """

    animation = str(animation or "static").lower()

    total_frames = max(int(float(duration) * FPS), 1)

    if animation == "zoom_in":

        zoom = "min(zoom+0.0015,1.15)"

        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"

    elif animation == "zoom_out":

        zoom = "if(eq(on,0),1.15,max(zoom-0.0015,1.0))"

        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"

    elif animation == "pan_left":

        zoom = "1.10"

        x = (
            f"max(0,(iw-iw/zoom)"
            f"*(1-on/{total_frames}))"
        )

        y = "ih/2-(ih/zoom/2)"

    elif animation == "pan_right":

        zoom = "1.10"

        x = (
            f"max(0,(iw-iw/zoom)"
            f"*on/{total_frames})"
        )

        y = "ih/2-(ih/zoom/2)"

    else:

        return (
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
            "(ow-iw)/2:(oh-ih)/2,"
            f"setsar=1,fps={FPS}"
        )

    # Extra image area provides room for zoom and pan.
    animation_width = int(VIDEO_WIDTH * 1.15)
    animation_height = int(VIDEO_HEIGHT * 1.15)

    return (
        f"scale={animation_width}:{animation_height}:"
        "force_original_aspect_ratio=increase,"
        f"crop={animation_width}:{animation_height},"
        f"zoompan=z='{zoom}':"
        f"x='{x}':"
        f"y='{y}':"
        "d=1:"
        f"s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:"
        f"fps={FPS},"
        "setsar=1"
    )


# =========================================================
# FFMPEG EXECUTION
# =========================================================

def run_ffmpeg(command, description="FFmpeg task"):

    """
    Execute FFmpeg and report errors.

    """

    start_time = time.time()

    try:

        print(f"Starting: {description}", flush=True)

        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT
        )

        elapsed = time.time() - start_time

        print(
            f"Completed: {description} "
            f"in {elapsed:.2f} seconds",
            flush=True
        )

    except subprocess.CalledProcessError as error:

        details = (
            error.stderr
            or error.stdout
            or str(error)
        )

        raise RuntimeError(
            "FFmpeg rendering failed:\n"
            + details[-5000:]
        ) from error

    except subprocess.TimeoutExpired as error:

        raise RuntimeError(
            f"{description} timed out after "
            f"{FFMPEG_TIMEOUT // 60} minutes."
        ) from error


# =========================================================
# VIDEO RENDERER
# =========================================================

def render_video(
    scene_plan,
    audio_plan,
    page_dir,
    subtitle_path,
    output_path
):

    """
    Render a final video from:

        - PDF pages or PPTX slides
        - Scene audio
        - Scene animations
        - Subtitle SRT file

    The final output is an MP4 video.
    """

    overall_start = time.time()

    page_dir = Path(page_dir)

    output_path = Path(output_path)

    subtitle_path = (
        Path(subtitle_path)
        if subtitle_path
        else None
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # -----------------------------------------------------
    # Validate input directories
    # -----------------------------------------------------

    if not page_dir.exists():

        raise FileNotFoundError(
            f"Visual assets directory not found: {page_dir}"
        )

    scenes = scene_plan.get("scenes", [])

    audio_scenes = audio_plan.get("scenes", [])

    if not scenes:

        raise ValueError(
            "Scene plan contains no scenes."
        )

    if not audio_scenes:

        raise ValueError(
            "Audio plan contains no audio scenes."
        )

    # -----------------------------------------------------
    # Match audio with scene numbers
    # -----------------------------------------------------

    audio_by_number = {}

    for audio_scene in audio_scenes:

        number = audio_scene.get("scene_number")

        if number is None:

            raise ValueError(
                "Audio entry is missing scene_number."
            )

        audio_by_number[int(number)] = audio_scene

    # -----------------------------------------------------
    # Validate document type
    # -----------------------------------------------------

    document_type = str(
        scene_plan.get("document_type", "pdf")
    ).lower()

    if document_type not in {"pdf", "pptx"}:

        raise ValueError(
            f"Unsupported document type: {document_type}"
        )

    # -----------------------------------------------------
    # Temporary rendering directory
    # -----------------------------------------------------

    temp_dir = output_path.parent / (
        output_path.stem + "_render_temp"
    )

    temp_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    clip_paths = []

    print("=" * 55, flush=True)
    print("VIDEO RENDERING STARTED", flush=True)
    print("Document type:", document_type, flush=True)
    print("Total scenes:", len(scenes), flush=True)
    print("FPS:", FPS, flush=True)
    print("Resolution:", f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}", flush=True)
    print("Encoding preset:", VIDEO_PRESET, flush=True)
    print("=" * 55, flush=True)

    # =====================================================
    # STEP 1: RENDER INDIVIDUAL SCENES
    # =====================================================

    for index, scene in enumerate(scenes, start=1):

        scene_start = time.time()

        scene_number = int(
            scene.get("scene_number", index)
        )

        print(
            f"\nPreparing scene {scene_number}/{len(scenes)}",
            flush=True
        )

        # -------------------------------------------------
        # Determine source visual
        # -------------------------------------------------

        source_page = int(scene["source_page"])

        if document_type == "pptx":

            image_filename = f"slide_{source_page}.png"

        else:

            image_filename = f"page_{source_page}.png"

        image_path = page_dir / image_filename

        if not image_path.exists():

            raise FileNotFoundError(
                f"Document image not found: {image_path}"
            )

        # -------------------------------------------------
        # Find corresponding audio
        # -------------------------------------------------

        if scene_number not in audio_by_number:

            raise FileNotFoundError(
                f"Audio entry missing for scene {scene_number}."
            )

        audio_scene = audio_by_number[scene_number]

        audio_path = Path(
            audio_scene["audio_path"]
        )

        # Resolve relative paths.
        if not audio_path.is_absolute():

            audio_path = Path.cwd() / audio_path

        audio_path = audio_path.resolve()

        if not audio_path.exists():

            raise FileNotFoundError(
                f"Scene audio file not found: {audio_path}"
            )

        # -------------------------------------------------
        # Determine duration
        # -------------------------------------------------

        duration = float(
            audio_scene.get("duration", 0)
        )

        if duration <= 0:

            duration = float(
                scene.get("duration", 0)
            )

        if duration <= 0:

            raise ValueError(
                f"Invalid duration for scene {scene_number}."
            )

        # -------------------------------------------------
        # Animation
        # -------------------------------------------------

        animation = scene.get(
            "animation",
            "static"
        )

        video_filter = get_animation_filter(
            animation,
            duration
        )

        clip_path = temp_dir / (
            f"clip_{scene_number:03d}.mp4"
        )

        # -------------------------------------------------
        # FFmpeg command
        # -------------------------------------------------

        command = [

            "ffmpeg",

            "-y",

            "-hide_banner",

            "-loglevel",
            "error",

            # Input image
            "-loop",
            "1",

            "-framerate",
            str(FPS),

            "-i",
            str(image_path),

            # Input audio
            "-i",
            str(audio_path),

            # Video filter
            "-vf",
            video_filter,

            # Stream mapping
            "-map",
            "0:v:0",

            "-map",
            "1:a:0",

            # Duration
            "-t",
            f"{duration:.3f}",

            "-r",
            str(FPS),

            # Video encoding
            "-c:v",
            "libx264",

            "-preset",
            VIDEO_PRESET,

            "-crf",
            VIDEO_CRF,

            "-threads:v",
            VIDEO_THREADS,

            "-pix_fmt",
            "yuv420p",

            # Audio encoding
            "-c:a",
            "aac",

            "-b:a",
            "128k",

            "-ar",
            "44100",

            "-ac",
            "2",

            "-af",
            "aresample=async=1",

            # Stop when the shorter stream ends.
            "-shortest",

            # MP4 optimization
            "-movflags",
            "+faststart",

            str(clip_path)

        ]

        print(
            f"Rendering scene {scene_number}: "
            f"{image_filename}, "
            f"animation={animation}, "
            f"duration={duration:.2f}s",
            flush=True
        )

        # Execute FFmpeg.
        run_ffmpeg(
            command,
            description=f"Scene {scene_number}"
        )

        # -------------------------------------------------
        # Validate generated clip
        # -------------------------------------------------

        if (
            not clip_path.exists()
            or clip_path.stat().st_size == 0
        ):

            raise RuntimeError(
                f"Scene {scene_number} "
                "produced an empty video clip."
            )

        clip_paths.append(clip_path)

        scene_elapsed = time.time() - scene_start

        print(
            f"Scene {scene_number} completed. "
            f"Elapsed: {scene_elapsed:.2f}s",
            flush=True
        )

    # =====================================================
    # STEP 2: CREATE CONCAT MANIFEST
    # =====================================================

    print(
        "\nAll scene clips generated successfully.",
        flush=True
    )

    concat_file = temp_dir / "concat_list.txt"

    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as file:

        for clip_path in clip_paths:

            escaped_path = (
                str(clip_path.resolve())
                .replace("\\", "/")
                .replace("'", "'\\''")
            )

            file.write(
                f"file '{escaped_path}'\n"
            )

    # =====================================================
    # STEP 3: COMBINE SCENE CLIPS
    # =====================================================

    combined_video = temp_dir / "combined.mp4"

    concat_command = [

        "ffmpeg",

        "-y",

        "-hide_banner",

        "-loglevel",
        "error",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        str(concat_file),

        "-c",
        "copy",

        "-movflags",
        "+faststart",

        str(combined_video)

    ]

    print(
        "\nCombining all scene clips...",
        flush=True
    )

    run_ffmpeg(
        concat_command,
        description="Combining scene clips"
    )

    if (
        not combined_video.exists()
        or combined_video.stat().st_size == 0
    ):

        raise RuntimeError(
            "Combined video file is empty."
        )

    # =====================================================
    # STEP 4: KEEP SUBTITLES AS SEPARATE SRT
    # =====================================================

    if subtitle_path and subtitle_path.exists():

        print(
            f"Subtitles saved separately: {subtitle_path}",
            flush=True
        )

    else:

        print(
            "Subtitle file not found. "
            "Final video will have no subtitle file.",
            flush=True
        )

    # =====================================================
    # STEP 5: COPY FINAL VIDEO
    # =====================================================

    shutil.copy2(
        combined_video,
        output_path
    )

    if (
        not output_path.exists()
        or output_path.stat().st_size == 0
    ):

        raise RuntimeError(
            "Final video was not generated successfully."
        )

    # =====================================================
    # STEP 6: VERIFY FINAL VIDEO WITH FFPROBE
    # =====================================================

    probe_command = [

        "ffprobe",

        "-v",
        "error",

        "-show_entries",
        "format=duration",

        "-of",
        "json",

        str(output_path)

    ]

    probe_result = subprocess.run(
        probe_command,
        check=True,
        capture_output=True,
        text=True,
        timeout=60
    )

    probe_data = json.loads(
        probe_result.stdout
    )

    actual_duration = float(
        probe_data["format"]["duration"]
    )

    # =====================================================
    # FINAL STATUS
    # =====================================================

    total_elapsed = time.time() - overall_start

    print("\n" + "=" * 55, flush=True)

    print(
        "VIDEO RENDERING COMPLETED SUCCESSFULLY",
        flush=True
    )

    print(
        "Final video:",
        output_path,
        flush=True
    )

    print(
        "Final duration:",
        f"{actual_duration:.2f} seconds",
        flush=True
    )

    print(
        "Total scenes:",
        len(clip_paths),
        flush=True
    )

    print(
        "Final video size:",
        f"{output_path.stat().st_size / (1024 * 1024):.2f} MB",
        flush=True
    )

    print(
        "Total rendering time:",
        f"{total_elapsed:.2f} seconds",
        flush=True
    )

    print("=" * 55, flush=True)

    return {

        "output_path": str(output_path),

        "duration": actual_duration,

        "scene_count": len(clip_paths),

        "document_type": document_type,

        "rendering_time": round(total_elapsed, 2)

    }