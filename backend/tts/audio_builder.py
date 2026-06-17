import os
import asyncio
from gtts import gTTS
from pydub import AudioSegment
from config import Config
from models.schemas import LessonContent, LessonAudio, SegmentTiming

async def generate_audio_for_lesson(lesson: LessonContent, lesson_id: str, voice: str = "en-US-JennyNeural") -> LessonAudio | None:
    """
    Generate a full-lesson MP3 using Google TTS (gTTS).
    Stitches individual segment audios together and returns a LessonAudio object.
    Offloads CPU/IO bound pydub and gTTS operations to worker threads to prevent event loop blocking.
    """
    segments_audio = []
    created_files = []
    cumulative_time = 0.0
    
    # Simple language mapping. gTTS defaults lang to 'en'.
    lang = "en"
    
    try:
        # Generate MP3 for each segment
        for i, segment in enumerate(lesson.segments):
            text = segment.narration
            if not text.strip():
                continue
                
            segment_file = os.path.join(Config.AUDIO_OUTPUT_DIR, f"{lesson_id}_seg_{i}.mp3")
            created_files.append(segment_file)
            
            # gTTS save is synchronous. Offload to a worker thread to keep event loop responsive.
            def save_gtts():
                tts = gTTS(text=text, lang=lang)
                tts.save(segment_file)
                
            print(f"[audio_builder] Synthesizing segment {i} using Google TTS...")
            await asyncio.to_thread(save_gtts)
            
            # Load with pydub to measure duration. Offload to a worker thread.
            def load_audio(path):
                try:
                    return AudioSegment.from_mp3(path)
                except Exception as e:
                    err_msg = str(e)
                    if "ffprobe" in err_msg or "ffmpeg" in err_msg or isinstance(e, FileNotFoundError):
                        raise RuntimeError(
                            f"Failed to load/decode audio file: {path}. "
                            "This error is usually caused by 'ffmpeg' not being installed or not added to your system's PATH. "
                            "Please install ffmpeg and ensure it is available in your PATH. "
                            f"Original error: {e}"
                        ) from e
                    raise
            
            try:
                audio_seg = await asyncio.to_thread(load_audio, segment_file)
            except Exception as e:
                print(f"[audio_builder] ✗ Failed to decode audio segment: {e}")
                raise
                
            duration_sec = len(audio_seg) / 1000.0
            
            segments_audio.append({
                "slide_index": segment.slide_index,
                "audio_file": segment_file,
                "start_time": cumulative_time,
                "duration": duration_sec,
                "audio_segment": audio_seg
            })
            
            cumulative_time += duration_sec
            
        if not segments_audio:
            print(f"[audio_builder] – No narration segments to synthesize for lesson {lesson_id}")
            return None
            
        # Stitch together and export full MP3. Offload to worker thread.
        def stitch_and_export(segs, out_path):
            full = AudioSegment.empty()
            for seg in segs:
                full += seg["audio_segment"]
            full.export(out_path, format="mp3")
            
        full_audio_path = os.path.join(Config.AUDIO_OUTPUT_DIR, f"{lesson_id}_full.mp3")
        print(f"[audio_builder] Stitching and exporting full lesson audio to {full_audio_path}...")
        await asyncio.to_thread(stitch_and_export, segments_audio, full_audio_path)
        
        timing_manifest = []
        for seg in segments_audio:
            timing_manifest.append(SegmentTiming(
                slide_index=seg["slide_index"],
                start_time=seg["start_time"],
                duration=seg["duration"]
            ))
            
        return LessonAudio(
            lesson_id=lesson_id,
            audio_file=full_audio_path,
            timing_manifest=timing_manifest
        )
    finally:
        # Cleanup segment files always, even on error
        for file_path in created_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                pass

async def generate_course_audio(lessons: list[LessonContent], course_id: str, voice: str = "en-US-JennyNeural") -> list[LessonAudio]:
    sem = asyncio.Semaphore(3)  # Limit concurrent lesson TTS synthesis to 3
    
    async def throttled_generate(lesson: LessonContent, lesson_id: str, voice_val: str):
        async with sem:
            return await generate_audio_for_lesson(lesson, lesson_id, voice_val)
            
    tasks = []
    for lesson in lessons:
        lesson_id = f"{course_id}_m{lesson.module_index}_l{lesson.lesson_index}"
        tasks.append(throttled_generate(lesson, lesson_id, voice))
        
    # Generate lesson audios with concurrency throttling
    audio_results = await asyncio.gather(*tasks)
    # Filter out None values (lessons with no narration segments)
    return [r for r in audio_results if r is not None]
