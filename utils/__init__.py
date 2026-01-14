try:
    # Importing ui here ensures that any page importing `utils.*` will also
    # render the common top header when running under Streamlit.
    from .ui import top_header

    # Render header (safe to call multiple times; UI function is idempotent)
    try:
        top_header()
    except Exception:
        pass
except Exception:
    # If anything goes wrong during package import, don't break page imports.
    pass
