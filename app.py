import streamlit as st
import oirfile
import tifffile
import numpy as np
import io
import os

st.set_page_config(page_title="Fiji-Optimized OIR Converter", page_icon="🔬")
st.title("🔬 Fiji-Optimized OIR Converter")
st.write("Convert Olympus .oir files to intensity-normalized 16-bit TIFFs for perfect visibility in Fiji.")

uploaded_file = st.file_uploader("Upload .oir file", type=['oir'])

if uploaded_file:
    temp_path = "temp.oir"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        with st.spinner('Converting...'):
            with oirfile.OirFile(temp_path) as oir:
                data = oir.asarray() # Format: (C, Y, X) or (Z, C, Y, X)
                
                # --- SPATIAL CALIBRATION ---
                pixel_size_x = 1.0
                unit = 'pixel'
                if hasattr(oir, 'coords') and 'X' in oir.coords and len(oir.coords['X']) > 1:
                    pixel_size_x = abs(oir.coords['X'][1] - oir.coords['X'][0])
                    if pixel_size_x < 0.001: pixel_size_x *= 1000 # mm to microns
                    unit = 'micron'

                # --- FIXING THE VISIBILITY (Per-Channel Normalization) ---
                # We normalize each channel individually so weak signals aren't lost
                normalized_data = np.zeros_like(data, dtype=np.uint16)
                
                # Check dimensions to handle Z-stacks (Z, C, Y, X) vs (C, Y, X)
                if data.ndim == 4:
                    num_z, num_c = data.shape[0], data.shape[1]
                    for c in range(num_c):
                        ch_data = data[:, c, :, :]
                        c_min, c_max = ch_data.min(), ch_data.max()
                        if c_max > c_min:
                            normalized_data[:, c, :, :] = ((ch_data - c_min) / (c_max - c_min) * 65535).astype(np.uint16)
                else:
                    num_c = data.shape[0]
                    for c in range(num_c):
                        ch_data = data[c]
                        c_min, c_max = ch_data.min(), ch_data.max()
                        if c_max > c_min:
                            normalized_data[c] = ((ch_data - c_min) / (c_max - c_min) * 65535).astype(np.uint16)
                
                # --- SAVE FOR FIJI ---
                buf = io.BytesIO()
                # 'imagej=True' ensures Fiji recognizes it as a stack with channels
                # resolution ensures the scale is correct (microns)
                tifffile.imwrite(
                    buf, 
                    normalized_data, 
                    imagej=True, 
                    resolution=(1.0/pixel_size_x, 1.0/pixel_size_x),
                    metadata={'unit': unit, 'mode': 'composite'}
                )
                buf.seek(0)

                st.success("Conversion complete! Each channel has been auto-stretched for maximum clarity.")
                st.info(f"Calibration: {pixel_size_x:.4f} {unit}/pixel")
                
                st.download_button(
                    label="Download for Fiji", 
                    data=buf, 
                    file_name=uploaded_file.name.replace(".oir", "_fiji.tif"),
                    mime="image/tiff"
                )

    except Exception as e:
        st.error(f"Error: {e}")
    finally:
        if os.path.exists(temp_path): 
            os.remove(temp_path)

st.divider()
st.info("💡 **Fiji Hint**: This file contains embedded spatial calibration. Once opened in Fiji, you can use the 'Analyze > Measure' tool directly.")
