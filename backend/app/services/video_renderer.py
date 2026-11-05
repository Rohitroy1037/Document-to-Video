

import json

import subprocess

from pathlib import Path





FPS = 30

VIDEO_WIDTH = 1280

VIDEO_HEIGHT = 720





def get_animation_filter(animation):

    """

    Create a video filter for the requested scene animation.

    """



    animation = str(animation or "static").lower()



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

        x = "max(0,(iw-iw/zoom)*(1-on/900))"

        y = "ih/2-(ih/zoom/2)"



    elif animation == "pan_right":

        zoom = "1.10"

        x = "max(0,(iw-iw/zoom)*on/900)"

        y = "ih/2-(ih/zoom/2)"



    else:

        return (

            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"

            "force_original_aspect_ratio=decrease,"

            f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"

            "(ow-iw)/2:(oh-ih)/2,"

            "setsar=1,fps=30"

        )



    return (

        "scale=1920:1080:"

        "force_original_aspect_ratio=increase,"

        "crop=1920:1080,"

        f"zoompan=z='{zoom}':"

        f"x='{x}':"

        f"y='{y}':"

        "d=1:"

        "s=1280x720:"

        "fps=30,"

        "setsar=1"

    )





def escape_subtitle_path(path):

    """

    Escape a path for FFmpeg's subtitles filter on Windows.

    """



    path = str(Path(path).resolve())

    path = path.replace("\\\\", "/")

    path = path.replace(":", r"**\:**")

    path = path.replace("'", r"**\\'**")

    path = path.replace(",", r"**\\,**")

    path = path.replace("[", r"**\\[**")

    path = path.replace("]", r"**\\]**")



    return path





def run_ffmpeg(command):

    """

    Run FFmpeg and report useful error details.

    """



    try:

        subprocess.run(

            command,

            check=True,

            capture_output=True,

            text=True,

            timeout=1800

        )



    except subprocess.CalledProcessError as error:

        details = error.stderr or error.stdout or str(error)



        raise RuntimeError(

            "FFmpeg rendering failed:\n"

            + details[-5000:]

        ) from error



    except subprocess.TimeoutExpired as error:

        raise RuntimeError(

            "FFmpeg rendering timed out after 30 minutes."

        ) from error





def render_video(

    scene_plan,

    audio_plan,

    page_dir,

    subtitle_path,

    output_path

):

    """

    Render a video from PDF pages or PPTX slides, scene audio,

    scene animations, and optional subtitles.

    """



    page_dir = Path(page_dir)

    output_path = Path(output_path)



    output_path.parent.mkdir(

        parents=True,

        exist_ok=True

    )



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



    # Match audio files to their scene numbers.

    audio_by_number = {}



    for audio_scene in audio_scenes:

        number = audio_scene.get("scene_number")



        if number is not None:

            audio_by_number[int(number)] = audio_scene



    document_type = str(

        scene_plan.get("document_type", "pdf")

    ).lower()



    if document_type not in {"pdf", "pptx"}:

        raise ValueError(

            f"Unsupported document type: {document_type}"

        )



    # Keep temporary scene clips separate from final output.

    temp_dir = output_path.parent / (

        output_path.stem + "_render_temp"

    )



    temp_dir.mkdir(

        parents=True,

        exist_ok=True

    )



    clip_paths = []



    for index, scene in enumerate(scenes, start=1):



        scene_number = int(

            scene.get("scene_number", index)

        )



        source_page = int(scene["source_page"])



        # PPTX images use slide_N.png.

        # PDF images use page_N.png.

        if document_type == "pptx":

            image_filename = f"slide_{source_page}.png"

        else:

            image_filename = f"page_{source_page}.png"



        image_path = page_dir / image_filename



        if not image_path.exists():

            raise FileNotFoundError(

                f"Document image not found: {image_path}"

            )



        if scene_number not in audio_by_number:

            raise FileNotFoundError(

                f"Audio entry missing for scene {scene_number}."

            )



        audio_scene = audio_by_number[scene_number]



        audio_path = Path(audio_scene["audio_path"])



        # Relative paths are resolved from the backend working directory.

        if not audio_path.is_absolute():

            audio_path = Path.cwd() / audio_path



        audio_path = audio_path.resolve()



        if not audio_path.exists():

            raise FileNotFoundError(

                f"Scene audio file not found: {audio_path}"

            )



        # Prefer the actual audio duration from the audio plan.

        duration = float(audio_scene.get("duration", 0))



        if duration <= 0:

            duration = float(scene.get("duration", 0))



        if duration <= 0:

            raise ValueError(

                f"Invalid duration for scene {scene_number}."

            )



        animation = scene.get("animation", "static")



        video_filter = get_animation_filter(animation)



        clip_path = temp_dir / (

            f"clip_{scene_number:03d}.mp4"

        )



        command = [

            "ffmpeg",

            "-y",

            "-hide_banner",

            "-loglevel",

            "error",

            "-loop", "1",

            "-framerate", str(FPS),

            "-i", str(image_path),

            "-i", str(audio_path),

            "-vf", video_filter,

            "-map", "0:v:0",

            "-map", "1:a:0",

            "-t", f"{duration:.3f}",

            "-r", str(FPS),

            "-c:v", "libx264",

            "-preset", "medium",

            "-crf", "20",

            "-pix_fmt", "yuv420p",

            "-c:a", "aac",

            "-b:a", "192k",

            "-ar", "44100",

            "-ac", "2",

            "-af", "aresample=async=1",

            "-shortest",

            "-movflags", "+faststart",

            str(clip_path)

        ]



        print(

            f"Rendering scene {scene_number}: "

            f"{image_filename}, animation={animation}, "

            f"duration={duration:.2f}s"

        )



        run_ffmpeg(command)



        if not clip_path.exists() or clip_path.stat().st_size == 0:

            raise RuntimeError(

                f"Scene {scene_number} produced an empty video clip."

            )



        clip_paths.append(clip_path)



    # Create the FFmpeg concat manifest.

    concat_file = temp_dir / "concat_list.txt"



    with open(

        concat_file,

        "w",

        encoding="utf-8"

    ) as file:

        for clip_path in clip_paths:

            escaped_path = (

                str(clip_path.resolve())

                .replace("\\\\", "/")

                .replace("'", "'\\\\''")

            )



            file.write(

                f"file '{escaped_path}'\n"

            )



    # Combine all scene clips.

    silent_subtitled_video = temp_dir / "combined.mp4"



    concat_command = [

        "ffmpeg",

        "-y",

        "-hide_banner",

        "-loglevel",

        "error",

        "-f", "concat",

        "-safe", "0",

        "-i", str(concat_file),

        "-c", "copy",

        "-movflags", "+faststart",

        str(silent_subtitled_video)

    ]



    print("Combining scene clips...")



    run_ffmpeg(concat_command)



    # Keep subtitles as a separate SRT file instead of burning them into the MP4.
    # The frontend converts this SRT file to WebVTT and lets viewers toggle captions.
    subtitle_path = Path(subtitle_path) if subtitle_path else None
    if subtitle_path and subtitle_path.exists():
        print(f"Subtitles saved separately: {subtitle_path}")
    else:
        print("Subtitle file not found; final video will have no subtitle track.")

    # Copy the combined scene video without applying any subtitle filter.
    output_path.write_bytes(silent_subtitled_video.read_bytes())

    if not output_path.exists() or output_path.stat().st_size == 0:

        raise RuntimeError(

            "Final video was not generated successfully."

        )



    # Report the actual output duration using ffprobe.

    probe_command = [

        "ffprobe",

        "-v", "error",

        "-show_entries", "format=duration",

        "-of", "json",

        str(output_path)

    ]



    probe_result = subprocess.run(

        probe_command,

        check=True,

        capture_output=True,

        text=True,

        timeout=60

    )



    probe_data = json.loads(probe_result.stdout)



    actual_duration = float(

        probe_data["format"]["duration"]

    )



    print(f"Final video: {output_path}")

    print(f"Final duration: {actual_duration:.2f} seconds")



    return {

        "output_path": str(output_path),

        "duration": actual_duration,

        "scene_count": len(clip_paths),

        "document_type": document_type

    }
