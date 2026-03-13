import streamlit as st
import oirfile
import tifffile
import io
import os
import numpy as np

st.set_page_config(page_title="OIR to TIFF Converter", page_icon="🔬")

st.title("🔬 OIR to TIFF (Raw Data)")
st.write("Convert Olympus .oir files to 16-bit TIFFs. No alterations are made to the pixel values to ensure 100% data integrity.")

# 1. File Uploader
uploaded_file = st.file_uploader("Choose an .oir file", type=['oir'])

if uploaded_file is not None:
    temp_filename = "temp_render.oir"
    with open(temp_filename, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        with st.spinner('Extracting raw data...'):
            # 2. Extract data using oirfile
            with oirfile.OirFile(temp_filename) as oir:
                # asarray() returns the full volume (Z, C, H, W) or (C, H, W)
                data = oir.asarray()
                
                # Ensure data is uint16 as expected for raw OIR data
                if data.dtype != np.uint16:
                    data = data.astype(np.uint16)

                # 3. Create an in-memory buffer for the TIFF
                # We use imagej=True to properly store multi-dimensional stacks
                tif_buffer = io.BytesIO()
                tifffile.imwrite(
                    tif_buffer, 
                    data, 
                    imagej=True, 
                    photometric='minisblack',
                    metadata={'mode': 'composite'} # Helps viewers like ImageJ show channels correctly
                )
                tif_buffer.seek(0)

            st.success(f"Conversion successful! Output shape: {data.shape}")
            st.info(f"File size: {tif_buffer.getbuffer().nbytes / (1024*1024):.1f} MB")

            # 4. Download Button
            output_name = uploaded_file.name.replace(".oir", ".tif")
            st.download_button(
                label="Download RAW TIFF",
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
st.warning("⚠️ **Note on Visibility**: These are raw 16-bit images. They will appear dark in standard photo viewers. For scientific analysis and proper visualization, please open them in software like **ImageJ (Fiji)**.")
