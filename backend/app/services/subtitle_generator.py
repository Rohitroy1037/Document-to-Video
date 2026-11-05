
from pathlib import Path


MAX_CHARS_PER_LINE = 42
MAX_LINES = 2
MIN_SUBTITLE_DURATION = 1.2


def format_timestamp(seconds: float) -> str:
    """Convert seconds into a valid SRT timestamp."""

    total_milliseconds = max(
        0,
        round(float(seconds) * 1000)
    )

    hours, remainder = divmod(
        total_milliseconds,
        3_600_000
    )

    minutes, remainder = divmod(
        remainder,
        60_000
    )

    secs, milliseconds = divmod(
        remainder,
        1000
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{milliseconds:03d}"
    )


def split_long_line(text: str) -> list[str]:
    """Wrap subtitle text without splitting words."""

    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        if len(word) > MAX_CHARS_PER_LINE:
            if current_line:
                lines.append(current_line)
                current_line = ""

            # Keep unusually long words intact.
            lines.append(word)
            continue

        candidate = (
            f"{current_line} {word}"
            if current_line
            else word
        )

        if len(candidate) <= MAX_CHARS_PER_LINE:
            current_line = candidate
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def create_subtitle_chunks(text: str) -> list[str]:
    """Split narration into readable subtitle chunks."""

    words = text.split()
    chunks = []
    current_words = []
    current_length = 0

    max_chunk_length = MAX_CHARS_PER_LINE * MAX_LINES

    for word in words:
        candidate_length = (
            current_length
            + len(word)
            + (1 if current_words else 0)
        )

        if (
            candidate_length <= max_chunk_length
            or not current_words
        ):
            current_words.append(word)
            current_length = candidate_length
        else:
            chunks.append(" ".join(current_words))
            current_words = [word]
            current_length = len(word)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


def create_subtitle_file(scene_plan, output_path):
    """
    Generate an SRT subtitle file using scene durations.

    Timing is proportional to word count, not actual speech
    timestamps. Each scene's subtitle timeline is constrained
    to that scene's supplied duration.
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    current_time = 0.0
    subtitle_number = 1

    scenes = scene_plan.get("scenes", [])

    with output_path.open("w", encoding="utf-8-sig", newline="\n") as file:
        for scene in scenes:
            narration = str(
                scene.get("narration", "")
            ).strip()

            duration = float(
                scene.get("duration", 5)
            )

            if duration <= 0:
                continue

            scene_start = current_time
            scene_end = scene_start + duration

            if not narration:
                current_time = scene_end
                continue

            chunks = create_subtitle_chunks(narration)

            if not chunks:
                current_time = scene_end
                continue

            word_counts = [
                max(1, len(chunk.split()))
                for chunk in chunks
            ]

            total_words = sum(word_counts)
            elapsed = 0.0

            for index, chunk in enumerate(chunks):
                remaining = duration - elapsed

                if remaining <= 0:
                    break

                # Distribute scene time by word count.
                if index == len(chunks) - 1:
                    chunk_duration = remaining
                else:
                    chunk_duration = (
                        duration
                        * word_counts[index]
                        / total_words
                    )

                # Do not extend the subtitle beyond its scene.
                chunk_duration = min(
                    max(0.0, chunk_duration),
                    remaining
                )

                if chunk_duration <= 0:
                    continue

                chunk_start = scene_start + elapsed
                chunk_end = min(
                    scene_start + elapsed + chunk_duration,
                    scene_end
                )

                lines = split_long_line(chunk)

                # Keep subtitles to at most two lines.
                subtitle_text = "\n".join(
                    lines[:MAX_LINES]
                )

                if not subtitle_text:
                    elapsed += chunk_duration
                    continue

                file.write(f"{subtitle_number}\n")
                file.write(
                    f"{format_timestamp(chunk_start)} --> "
                    f"{format_timestamp(chunk_end)}\n"
                )
                file.write(f"{subtitle_text}\n\n")

                subtitle_number += 1
                elapsed += chunk_duration

            current_time = scene_end

    return str(output_path)
