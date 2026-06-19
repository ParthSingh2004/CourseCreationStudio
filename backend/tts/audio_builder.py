import os
import asyncio
import edge_tts
from pydub import AudioSegment
from config import Config
from models.schemas import LessonContent, LessonAudio, SegmentTiming


async def generate_audio_for_lesson(
    lesson: LessonContent,
    lesson_id: str,
    voice: str = "en-US-JennyNeural",
) -> LessonAudio | None:
    """
    Generate a full-lesson MP3 using Microsoft Edge TTS (edge-tts).
    Synthesises each narration segment individually, measures duration with
    pydub, stitches them into one MP3, then cleans up the segment files.
    """
    segments_audio = []
    created_files = []
    cumulative_time = 0.0

    try:
        for i, segment in enumerate(lesson.segments):
            text = segment.narration
            if not text.strip():
                continue

            segment_file = os.path.join(
                Config.AUDIO_OUTPUT_DIR, f"{lesson_id}_seg_{i}.mp3"
            )
            created_files.append(segment_file)

            # edge-tts is natively async — no thread offload needed for synthesis.
            print(f"[audio_builder] Synthesizing segment {i} via Edge TTS (voice={voice})...")
            communicate = edge_tts.Communicate(text=text, voice=voice)
            await communicate.save(segment_file)

            # Measure duration with pydub (CPU-bound) — offload to thread.
            def load_audio(path):
                try:
                    return AudioSegment.from_mp3(path)
                except Exception as e:
                    err_msg = str(e)
                    if "ffprobe" in err_msg or "ffmpeg" in err_msg or isinstance(e, FileNotFoundError):
                        raise RuntimeError(
                            f"Failed to decode audio file: {path}. "
                            "Ensure ffmpeg is installed and on your PATH. "
                            f"Original error: {e}"
                        ) from e
                    raise

            try:
                audio_seg = await asyncio.to_thread(load_audio, segment_file)
            except Exception as e:
                print(f"[audio_builder] ✗ Failed to decode audio segment: {e}")
                raise

            duration_sec = len(audio_seg) / 1000.0

            segments_audio.append(
                {
                    "slide_index": segment.slide_index,
                    "audio_file": segment_file,
                    "start_time": cumulative_time,
                    "duration": duration_sec,
                    "audio_segment": audio_seg,
                }
            )

            cumulative_time += duration_sec

        if not segments_audio:
            print(f"[audio_builder] – No narration segments to synthesize for lesson {lesson_id}")
            return None

        # Stitch segments together and export the full lesson MP3.
        def stitch_and_export(segs, out_path):
            full = AudioSegment.empty()
            for seg in segs:
                full += seg["audio_segment"]
            full.export(out_path, format="mp3")

        full_audio_path = os.path.join(Config.AUDIO_OUTPUT_DIR, f"{lesson_id}_full.mp3")
        print(f"[audio_builder] Stitching and exporting full lesson audio → {full_audio_path}...")
        await asyncio.to_thread(stitch_and_export, segments_audio, full_audio_path)

        timing_manifest = [
            SegmentTiming(
                slide_index=seg["slide_index"],
                start_time=seg["start_time"],
                duration=seg["duration"],
            )
            for seg in segments_audio
        ]

        return LessonAudio(
            lesson_id=lesson_id,
            audio_file=full_audio_path,
            timing_manifest=timing_manifest,
        )

    finally:
        # Always clean up per-segment temp files, even on error.
        for file_path in created_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                pass


async def generate_course_audio(
    lessons: list[LessonContent],
    course_id: str,
    voice: str = "en-US-JennyNeural",
) -> list[LessonAudio]:
    # Limit to 3 concurrent lesson syntheses to avoid hammering Edge TTS.
    sem = asyncio.Semaphore(3)

    async def throttled_generate(lesson: LessonContent, lesson_id: str, voice_val: str):
        async with sem:
            return await generate_audio_for_lesson(lesson, lesson_id, voice_val)

    tasks = [
        throttled_generate(
            lesson,
            f"{course_id}_m{lesson.module_index}_l{lesson.lesson_index}",
            voice,
        )
        for lesson in lessons
    ]

    # Gather with concurrency throttling; filter out None (no-narration lessons).
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]
