import os
import streamlit as st


def top_header(image_path="assets/topright.png", height=88):
    """Render a compact top-right header image across pages.

    - If `image_path` exists in the workspace, the image is displayed in
      the top-right corner with a small professional frame.
    - If not found, a subtle placeholder is shown with instructions to add
      the image file at the given path.
    """
    try:
        # Use fixed positioning so the image stays top-right on long pages
        css = f"""
        <style>
        .tp-topright {{
            position: fixed;
            top: 12px;
            right: 12px;
            z-index: 9999;
            background: rgba(255,255,255,0.0);
            padding: 4px;
            border-radius: 6px;
        }}
        .tp-topright img {{
            height: {height}px;
            object-fit: contain;
            display:block;
        }}
        </style>
        """

        if os.path.exists(image_path):
            # Relative path will be served by Streamlit static file server
            img_tag = f'<div class="tp-topright"><img src="/{image_path}" alt="Turning Point"></div>'
            st.markdown(css + img_tag, unsafe_allow_html=True)
        else:
            # Placeholder box with instructions to add the image
            placeholder = (
                css +
                '<div class="tp-topright"><div style="height: ' + str(height) + 'px; '
                "padding:6px;border:1px solid #eee;border-radius:6px;background:#fff;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,0.05);">
                "<div style='text-align:center;font-size:12px;color:#444;'>Add header image<br><strong>assets/topright.png</strong></div></div></div>"
            )
            st.markdown(placeholder, unsafe_allow_html=True)
    except Exception:
        # Fail silently so pages still load in non-Streamlit contexts
        pass
