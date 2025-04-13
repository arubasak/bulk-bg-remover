import streamlit as st
import os
import requests
import shutil
from zipfile import ZipFile
import hashlib

# 🔐 Password protection with SHA256 hash
def check_password():
    def password_entered():
        entered = st.session_state["password"]
        entered_hash = hashlib.sha256(entered.encode()).hexdigest()
        if entered_hash == st.secrets["APP_PASSWORD_HASH"]:
            st.session_state["authenticated"] = True
        else:
            st.session_state["authenticated"] = False
            st.error("❌ Incorrect password")

    if "authenticated" not in st.session_state:
        st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
        st.stop()
    elif not st.session_state["authenticated"]:
        st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
        st.stop()

check_password()

# 🔐 API keys from secrets
FREEPIK_API_KEY = st.secrets["FREEPIK_API_KEY"]
IMGBB_API_KEY = st.secrets["IMGBB_API_KEY"]

# 📁 Create output folder
output_folder = "processed_images"
if os.path.exists(output_folder):
    shutil.rmtree(output_folder)
os.makedirs(output_folder, exist_ok=True)

# 📤 Upload interface
st.title("🪄 Background Remover (Powered by Freepik AI)")
uploaded_files = st.file_uploader("Upload image(s)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files and st.button("✨ Remove Backgrounds"):
    zip_path = "processed_images.zip"
    with st.spinner("Processing images..."):
        for uploaded_file in uploaded_files:
            filename = uploaded_file.name
            st.write(f"📷 Processing: {filename}")

            # Save locally
            input_path = os.path.join(output_folder, filename)
            with open(input_path, "wb") as f:
                f.write(uploaded_file.read())

            # Upload to imgbb
            with open(input_path, "rb") as file:
                imgbb_resp = requests.post(
                    "https://api.imgbb.com/1/upload",
                    params={"key": IMGBB_API_KEY},
                    files={"image": file},
                )

            if imgbb_resp.status_code != 200:
                st.error(f"❌ imgbb upload failed for {filename}")
                continue

            image_url = imgbb_resp.json()["data"]["url"]

            # Call Freepik API
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'x-freepik-api-key': FREEPIK_API_KEY
            }
            data = {'image_url': image_url}
            freepik_resp = requests.post("https://api.freepik.com/v1/ai/beta/remove-background", headers=headers, data=data)

            if freepik_resp.status_code != 200:
                st.error(f"❌ Freepik background removal failed for {filename}")
                continue

            processed_url = freepik_resp.json().get('url')
            if not processed_url:
                st.warning(f"⚠️ No processed URL returned for {filename}")
                continue

            # Download processed image
            output_filename = f"{os.path.splitext(filename)[0]}_processed.png"
            output_path = os.path.join(output_folder, output_filename)
            img_data = requests.get(processed_url).content
            with open(output_path, 'wb') as f:
                f.write(img_data)

            # Show preview
            st.image(output_path, caption=f"✅ {output_filename}")

        # Zip results
        with ZipFile(zip_path, 'w') as zipf:
            for file in os.listdir(output_folder):
                zipf.write(os.path.join(output_folder, file), arcname=file)

    # Download button
    with open(zip_path, "rb") as f:
        st.download_button("📦 Download All", f, file_name="processed_images.zip")
