import streamlit as st
import oirfile
import tifffile
import io
import os

st.set_page_config(page_title="OIR to TIFF Converter", page_icon="🔬")

st.title("🔬 OIR to TIFF Converter")
st.write("Upload an Olympus .oir file to convert it to a downloadable TIFF.")

# 1. File Uploader
uploaded_file = st.file_uploader("Choose an .oir file", type=['oir'])

if uploaded_file is not None:
    # Oirfile needs a physical file path or a bytes-like object
    # We save the uploaded file temporarily to read it
    temp_filename = "temp_render.oir"
    with open(temp_filename, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        with st.spinner('Processing image...'):
            # 2. Extract data using oirfile
            with oirfile.OirFile(temp_filename) as oir:
                data = oir.asarray()
                
                # 3. Create an in-memory buffer for the TIFF
                tif_buffer = io.BytesIO()
                tifffile.imwrite(tif_buffer, data, imagej=True)
                tif_buffer.seek(0)

            st.success("Conversion successful!")

            # 4. Download Button
            output_name = uploaded_file.name.replace(".oir", ".tif")
            st.download_button(
                label="Click here to download TIFF",
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
st.info("Note: Large confocal files may take a moment to process depending on your RAM.")
