pip install moviepy
import streamlit as st
import os
from moviepy.editor import *
import whisper
import tempfile
import zipfile

# ----- LOGIN GATE -----
allowed_email = "anantthakre595@gmail.com"
st.set_page_config(page_title="Faceless Clipper", layout="centered")

email = st.text_input("Enter your Gmail to use this tool 👇", "")
if email.strip().lower() != allowed_email:
    st.warning("🔒 This tool is private. Only allowed Gmail can access.")
    st.stop()

# ----- UI LAYOUT -----
st.title("🎬 Faceless Video Clipper")
st.markdown("Cut long videos into vertical Shorts with auto-captions, music, logo & end screen.")

# ----- Uploads -----
video_file = st.file_uploader("📹 Upload Main Video (MP4)", type=["mp4"])
logo_file = st.file_uploader("🖼️ Optional Logo (PNG/JPG)", type=["png", "jpg"])
music_file = st.file_uploader("🎵 Optional Background Music (MP3)", type=["mp3"])
end_screen_file = st.file_uploader("🔚 Optional End Screen Video (MP4)", type=["mp4"])

clip_duration = st.slider("Clip Duration (seconds)", 10, 60, 30)
mute_audio = st.checkbox("Mute Original Audio")
add_captions = st.checkbox("Add Auto-Captions (Whisper)", value=True)
vertical_crop = st.checkbox("Convert to Vertical (9:16)", value=True)
base_title = st.text_input("Base File Name", value="MyClip")

start = st.button("🚀 Start Processing")

if start and video_file:
    with st.spinner("Processing... Please wait."):
        temp_dir = tempfile.mkdtemp()
        video_path = os.path.join(temp_dir, "main.mp4")
        with open(video_path, "wb") as f:
            f.write(video_file.read())

        if logo_file:
            logo_path = os.path.join(temp_dir, "logo.png")
            with open(logo_path, "wb") as f:
                f.write(logo_file.read())
        else:
            logo_path = None

        if music_file:
            music_path = os.path.join(temp_dir, "music.mp3")
            with open(music_path, "wb") as f:
                f.write(music_file.read())
        else:
            music_path = None

        if end_screen_file:
            end_screen_path = os.path.join(temp_dir, "end.mp4")
            with open(end_screen_path, "wb") as f:
                f.write(end_screen_file.read())
        else:
            end_screen_path = None

        output_dir = os.path.join(temp_dir, "clips")
        os.makedirs(output_dir, exist_ok=True)

        video = VideoFileClip(video_path)
        model = whisper.load_model("base") if add_captions else None
        parts = int(video.duration // clip_duration)

        all_clips = []
        for i in range(parts):
            subclip = video.subclip(i * clip_duration, min((i + 1) * clip_duration, video.duration))

            # Vertical crop
            if vertical_crop:
                target_ratio = 9 / 16
                new_height = subclip.h
                new_width = int(new_height * target_ratio)
                x_center = subclip.w // 2
                x1 = max(0, x_center - new_width // 2)
                subclip = subclip.crop(x1=x1, x2=x1 + new_width)

            # Logo overlay
            if logo_path:
                logo = (ImageClip(logo_path).set_duration(subclip.duration)
                        .resize(height=50).set_pos(("right", "bottom")))
                subclip = CompositeVideoClip([subclip, logo])

            # Mute or Music
            if mute_audio:
                subclip = subclip.without_audio()
            elif music_path:
                music = AudioFileClip(music_path).subclip(0, subclip.duration)
                subclip = subclip.set_audio(music)

            # Captions
            if add_captions and model:
                audio_temp = os.path.join(temp_dir, f"audio_{i}.mp3")
                subclip.audio.write_audiofile(audio_temp, logger=None)
                text = model.transcribe(audio_temp)["text"]
                txt_clip = (TextClip(text, fontsize=40, color='white', bg_color='black',
                                     size=subclip.size, method='caption', align='center')
                            .set_duration(subclip.duration).set_position(("center", "bottom")))
                subclip = CompositeVideoClip([subclip, txt_clip])

            # End screen
            if end_screen_path:
                end_clip = VideoFileClip(end_screen_path).resize(subclip.size)
                subclip = concatenate_videoclips([subclip, end_clip])

            output_file = os.path.join(output_dir, f"{base_title}_Part_{i + 1}.mp4")
            subclip.write_videofile(output_file, codec="libx264", audio_codec="aac", logger=None)
            all_clips.append(output_file)

        # Zip
        zip_path = os.path.join(temp_dir, "clips.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for clip in all_clips:
                zipf.write(clip, os.path.basename(clip))

        st.success("✅ Done! Download your clips below.")
        with open(zip_path, "rb") as f:
            st.download_button("📦 Download ZIP", f, file_name="final_clips.zip")
