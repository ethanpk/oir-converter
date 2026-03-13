import streamlit as st
import oirfile
import tifffile
import numpy as np
import io
import os
from PIL import Image

st.set_page_config(page_title="OIR to Red TIFF Converter", page_icon="🔬")

st.title("🔬 OIR to Bright Red TIFF")
st.write("This tool flattens 3D stacks and 'bakes' the red color into a standard image.")

uploaded_file = st.file_uploader("Upload your .oir file", type=['oir'])

if uploaded_file:
    temp_path = "temp_file.oir"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        with st.spinner("Processing..."):
            with oirfile.OirFile(temp_path) as oir:
                # 1. Get raw data. 
                # Shape could be (Z, C, Y, X) or (C, Z, Y, X)
                data = oir.asarray()
                
                # 2. Max Intensity Projection (Flatten the Z-stack)
                # We need to find which axis is Z. For Z-stacks it is typically 0 or 1.
                if data.ndim == 4:
                    # Logic: In (Z, C, Y, X), Z is axis 0. In (C, Z, Y, X), Z is axis 1.
                    # We assume the user wants to collapse the dimension that is NOT Channels (C).
                    # Since Channels is usually 1-3, we find the index of the smallest dimension among the first two.
                    if data.shape[0] < data.shape[1]: # Likely (C, Z, Y, X)
                        projected = np.max(data, axis=1)
                    else: # Likely (Z, C, Y, X)
                        projected = np.max(data, axis=0)
                else:
                    projected = data

                # 3. Focus on the Red Channel (Usually Channel 0)
                # We create an RGB image where Red = our data, Green = 0, Blue = 0
                red_channel = projected[0].astype(float)

                # 4. "Auto-Contrast" - Scale brightness to the 0-255 range
                p_low, p_high = np.percentile(red_channel, (0.5, 99.5))
                red_channel = np.clip(red_channel, p_low, p_high)
                
                # Avoid division by zero
                den = red_channel.max() - red_channel.min()
                if den > 0:
                    red_channel = ((red_channel - red_channel.min()) / den * 255).astype(np.uint8)
                else:
                    red_channel = np.zeros_like(red_channel, dtype=np.uint8)

                # 5. Create the RGB Image
                height, width = red_channel.shape
                rgb_image = np.zeros((height, width, 3), dtype=np.uint8)
                rgb_image[:, :, 0] = red_channel # Set Red channel

                # Preview for the user
                st.subheader("Preview (Flattened Red Projection)")
                st.image(rgb_image, caption="Processed Red Image", use_container_width=True)

                # 6. Prepare for Download
                buf = io.BytesIO()
                # Saving as a standard TIFF
                result_img = Image.fromarray(rgb_image)
                result_img.save(buf, format="TIFF")
                byte_im = buf.getvalue()

                st.success("Conversion successful!")
                st.download_button(
                    label="📥 Download Red TIFF",
                    data=byte_im,
                    file_name=uploaded_file.name.replace(".oir", "_Red.tif"),
                    mime="image/tiff"
                )

    except Exception as e:
        st.error(f"Error processing file: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

st.info("Tip: This flattens the 3D layers into one sharp image, just like a 'Max Projection' in Fiji.")
