import streamlit as st
import oirfile
import tifffile
import numpy as np
import io
import os
from PIL import Image

st.set_page_config(page_title="OIR Preview & Convert", layout="wide", page_icon="🔬")
st.title("🔬 OIR to TIFF with Live Preview")
st.write("Convert Olympus .oir files with real-time preview and full spatial calibration.")

uploaded_file = st.file_uploader("Upload .oir file", type=['oir'])

if uploaded_file:
    temp_path = "temp.oir"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        with oirfile.OirFile(temp_path) as oir:
            # raw_data typically returns (Z, C, Y, X) or (C, Y, X)
            raw_data = oir.asarray()
            
            # --- SPATIAL CALIBRATION ---
            pixel_size_x = 1.0
            pixel_size_y = 1.0
            unit = 'pixel'
            
            if hasattr(oir, 'coords'):
                if 'X' in oir.coords and len(oir.coords['X']) > 1:
                    pixel_size_x = abs(oir.coords['X'][1] - oir.coords['X'][0])
                    if pixel_size_x < 0.001: pixel_size_x *= 1000 # mm to microns
                    unit = 'micron'
                
                if 'Y' in oir.coords and len(oir.coords['Y']) > 1:
                    pixel_size_y = abs(oir.coords['Y'][1] - oir.coords['Y'][0])
                    if pixel_size_y < 0.001: pixel_size_y *= 1000
            
            # --- PREVIEW LOGIC ---
            st.divider()
            col_preview, col_info = st.columns([2, 1])
            
            with col_preview:
                st.subheader("Image Preview")
                shape = raw_data.shape
                
                # Deduce dimensions: (Z, C, Y, X) vs (C, Y, X)
                if raw_data.ndim == 4:
                    num_z, num_c = shape[0], shape[1]
                    mid_z = num_z // 2
                    preview_slice = raw_data[mid_z, 0, :, :]
                    caption = f"Preview: Channel 0, Z-Slice {mid_z} (Total: {num_z} slices, {num_c} channels)"
                elif raw_data.ndim == 3:
                    num_c = shape[0]
                    preview_slice = raw_data[0, :, :]
                    caption = f"Preview: Channel 0 (Total: {num_c} channels)"
                else:
                    preview_slice = raw_data
                    caption = "Preview: Single Plane"

                # Normalize for browser display (0-255)
                p_min, p_max = preview_slice.min(), preview_slice.max()
                if p_max > p_min:
                    normalized = ((preview_slice - p_min) / (p_max - p_min) * 255).astype(np.uint8)
                else:
                    normalized = np.zeros_like(preview_slice, dtype=np.uint8)

                st.image(normalized, caption=caption, use_container_width=True)

            with col_info:
                st.subheader("Metadata")
                st.write(f"**Dimensions**: {shape}")
                st.write(f"**Dtype**: {raw_data.dtype}")
                if unit == 'micron':
                    st.write(f"**Resolution**: {pixel_size_x:.4f} x {pixel_size_y:.4f} µm/pixel")
                    total_w = pixel_size_x * shape[-1]
                    total_h = pixel_size_y * shape[-2]
                    st.write(f"**Physical Size**: {total_w:.2f} x {total_h:.2f} µm")

            # --- CONVERSION OPTIONS ---
            st.divider()
            st.subheader("Export Options")
            opt1, opt2, opt3 = st.columns(3)
            with opt1:
                bit_depth = st.radio("Output Bit Depth", [16, 8], index=0, help="16-bit preserves all scientific data; 8-bit is smaller.")
            with opt2:
                stretch = st.checkbox("Auto-Stretch Contrast", value=False, help="Scales pixel values to full range. Warning: This ALTERS the raw data!")
            with opt3:
                fiji_tags = st.checkbox("Include Fiji Metadata", value=True, help="Embeds calibration and display ranges for immediate clarity in Fiji.")

            # --- PROCESSING FOR DOWNLOAD ---
            if st.button("✨ Prepare High-Quality TIFF"):
                with st.spinner("Processing..."):
                    # Calculate display parameters for metadata
                    d_min = float(np.min(raw_data))
                    d_max = float(np.max(raw_data))

                    # Logic for Export
                    if stretch:
                        max_target = 65535 if bit_depth == 16 else 255
                        if d_max > d_min:
                            export_data = ((raw_data - d_min) / (d_max - d_min) * max_target)
                        else:
                            export_data = raw_data
                    else:
                        export_data = raw_data
                    
                    final_dtype = np.uint16 if bit_depth == 16 else np.uint8
                    export_data = export_data.astype(final_dtype)

                    # Build Metadata
                    ij_metadata = {'unit': unit, 'mode': 'composite'}
                    if fiji_tags:
                        ij_metadata['min'] = d_min
                        ij_metadata['max'] = d_max

                    buf = io.BytesIO()
                    tifffile.imwrite(
                        buf, 
                        export_data, 
                        imagej=True, 
                        resolution=(1.0/pixel_size_x, 1.0/pixel_size_y),
                        metadata=ij_metadata
                    )
                    buf.seek(0)

                    st.success(f"File Ready! Size: {buf.getbuffer().nbytes / (1024*1024):.1f} MB")
                    st.download_button(
                        label="🚀 Download TIFF Now",
                        data=buf,
                        file_name=uploaded_file.name.replace(".oir", ".tif"),
                        mime="image/tiff"
                    )

    except Exception as e:
        st.error(f"An error occurred: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

st.divider()
st.info("💡 **Tip**: Use 16-bit and 'Fiji Metadata' for scientific work. Use 8-bit and 'Auto-Stretch' for presentations.")
