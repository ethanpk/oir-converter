import streamlit as st
import oirfile
import tifffile
import io
import os
import numpy as np

st.set_page_config(page_title="OIR to TIFF Converter", page_icon="🔬")

st.title("🔬 OIR to TIFF (Standard Fiji Format)")
st.write("Convert Olympus .oir files to 16-bit TIFFs with Fiji-compatible display metadata. Pixel values remain 100% original.")

# 1. File Uploader
uploaded_file = st.file_uploader("Choose an .oir file", type=['oir'])

if uploaded_file is not None:
    temp_filename = "temp_render.oir"
    with open(temp_filename, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        with st.spinner('Reading file and calculating display parameters...'):
            # 2. Extract data using oirfile
            with oirfile.OirFile(temp_filename) as oir:
                data = oir.asarray()
                
                # Ensure data is uint16
                if data.dtype != np.uint16:
                    data = data.astype(np.uint16)

                # Calculate display range for Fiji (Min/Max brightness)
                # This doesn't change the pixels, just adds a tag for the viewer
                d_min = float(np.min(data))
                d_max = float(np.max(data))

                # Handle edge cases (blank images)
                if d_max <= d_min:
                    d_max = d_min + 1

                # 3. Create an in-memory buffer for the TIFF
                tif_buffer = io.BytesIO()
                
                # We use ImageJ metadata to store the display range
                # This makes the image look 'bright' in Fiji immediately
                ij_metadata = {
                    'mode': 'composite',
                    'min': d_min,
                    'max': d_max
                }

                tifffile.imwrite(
                    tif_buffer, 
                    data, 
                    imagej=True, 
                    photometric='minisblack',
                    metadata=ij_metadata
                )
                tif_buffer.seek(0)

            st.success(f"Conversion successful! Output shape: {data.shape}")
            st.info(f"Fiji Display Range set to: {int(d_min)} - {int(d_max)}")

            # 4. Download Button
            output_name = uploaded_file.name.replace(".oir", ".tif")
            st.download_button(
                label="Download TIFF (Fiji Compatible)",
                data=tif_buffer,
                file_name=output_name,
                mime="image/tiff"
            )
            
    except Exception as e:
        st.error(f"Error: {e}")
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

st.divider()
st.info("💡 **Pro Tip**: Open this file in **Fiji/ImageJ**. It will automatically adjust its brightness based on the metadata I've embedded, showing you the full detail without modifying your raw scientific data.")
