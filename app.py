import streamlit as st
import cv2
import tempfile
import os

# Helper function to convert Streamlit Hex colors (#RRGGBB) to OpenCV BGR format
def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (rgb[2], rgb[1], rgb[0])

def process_video(input_path, output_path, settings):
    cap = cv2.VideoCapture(input_path)
    
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    object_detector = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=40)

    progress_bar = st.progress(0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    current_frame = 0

    # Convert hex UI colors to OpenCV format
    box_color = hex_to_bgr(settings['box_color'])
    conn_color = hex_to_bgr(settings['conn_color'])
    text_color = hex_to_bgr(settings['text_color'])
    thick = settings['stroke_width']

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 1. Apply Background Video Filters
        if settings['filter'] == "Invert":
            frame = cv2.bitwise_not(frame)
        elif settings['filter'] == "Grayscale":
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR) # Convert back so we can draw colored lines
        elif settings['filter'] == "Blur":
            frame = cv2.GaussianBlur(frame, (21, 21), 0)
        elif settings['filter'] == "Edge Detection":
            edges = cv2.Canny(frame, 100, 200)
            frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

        mask = object_detector.apply(frame)
        _, mask = cv2.threshold(mask, 254, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_blobs = []

        # Filter out noise based on user's minimum size
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > settings['min_area']:
                valid_blobs.append(cnt)
                
        # Sort blobs by size and strictly limit how many we track based on UI slider
        valid_blobs = sorted(valid_blobs, key=cv2.contourArea, reverse=True)[:settings['max_blobs']]
        
        blob_centers = []

        for i, cnt in enumerate(valid_blobs):
            x, y, w, h = cv2.boundingRect(cnt)
            center_x, center_y = x + w // 2, y + h // 2
            blob_centers.append((center_x, center_y))

            # Sizing Control Logic
            if settings['size_mode'] == "Fixed Size":
                s = settings['fixed_size'] // 2
                x, y, w, h = center_x - s, center_y - s, s * 2, s * 2

            # Region Shape Control Logic
            if settings['shape'] == "Basic Rectangle":
                cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, thick)
            elif settings['shape'] == "Circle":
                radius = max(w, h) // 2
                cv2.circle(frame, (center_x, center_y), radius, box_color, thick)
            elif settings['shape'] == "L-Frame":
                l = min(w, h) // 4
                cv2.line(frame, (x, y), (x+l, y), box_color, thick)
                cv2.line(frame, (x, y), (x, y+l), box_color, thick)
                cv2.line(frame, (x+w, y), (x+w-l, y), box_color, thick)
                cv2.line(frame, (x+w, y), (x+w, y+l), box_color, thick)
                cv2.line(frame, (x, y+h), (x+l, y+h), box_color, thick)
                cv2.line(frame, (x, y+h), (x, y+h-l), box_color, thick)
                cv2.line(frame, (x+w, y+h), (x+w-l, y+h), box_color, thick)
                cv2.line(frame, (x+w, y+h), (x+w, y+h-l), box_color, thick)
            elif settings['shape'] == "Crosshair":
                l = min(w, h) // 3
                cv2.line(frame, (center_x - l, center_y), (center_x + l, center_y), box_color, thick)
                cv2.line(frame, (center_x, center_y - l), (center_x, center_y + l), box_color, thick)

            # Labels and Text Control Logic
            label = ""
            if settings['label_type'] == "Tracking Index":
                label = f"#{i+1}"
            elif settings['label_type'] == "X/Y Coordinates":
                label = f"{center_x},{center_y}"
                
            if label:
                cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 2)

        # Connection Hub Control Logic
        if len(blob_centers) > 1:
            if settings['connection'] == "Sequential (Line)":
                for i in range(len(blob_centers) - 1):
                    cv2.line(frame, blob_centers[i], blob_centers[i+1], conn_color, thick)
            elif settings['connection'] == "Central Hub":
                hub_x = sum(c[0] for c in blob_centers) // len(blob_centers)
                hub_y = sum(c[1] for c in blob_centers) // len(blob_centers)
                cv2.circle(frame, (hub_x, hub_y), 6, conn_color, -1)
                for center in blob_centers:
                    cv2.line(frame, (hub_x, hub_y), center, conn_color, thick)

        out.write(frame)
        
        current_frame += 1
        if total_frames > 0:
            progress_bar.progress(min(current_frame / total_frames, 1.0))

    cap.release()
    out.release()

st.set_page_config(page_title="Pro Tracker Studio", layout="wide")
st.title("🎛️ Pro Tracker Studio")
st.write("Upload a video and freely customize the aesthetics and logic of the tracking engine.")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("⚙️ Effect Settings")
    
    with st.expander("🎨 Region Style & Shapes", expanded=True):
        shape = st.selectbox("Shape", ["Basic Rectangle", "Circle", "L-Frame", "Crosshair"])
        box_color = st.color_picker("Stroke Color", "#00FF00")
        stroke_width = st.slider("Stroke Width", 1, 10, 2)
        
    with st.expander("🔗 Connections & Lines"):
        connection = st.selectbox("Connection Mode", ["None", "Sequential (Line)", "Central Hub"])
        conn_color = st.color_picker("Line Color", "#FF9600")
        
    with st.expander("📏 Sizing & Count Control"):
        size_mode = st.radio("Bounding Size Behavior", ["Dynamic Size", "Fixed Size"])
        fixed_size = st.selectbox("Fixed Size (px)", [32, 64, 128, 256]) if size_mode == "Fixed Size" else 0
        max_blobs = st.slider("Max Objects to Track", 1, 128, 32)
        min_blob_size = st.slider("Ignore Movement Smaller Than (px)", 16, 256, 64)
        
    with st.expander("🔤 Text Labels & Background Filters"):
        label_type = st.selectbox("Text Content", ["None", "Tracking Index", "X/Y Coordinates"])
        text_color = st.color_picker("Text Color", "#FFFFFF")
        filter_effect = st.selectbox("Video Filter", ["None", "Invert", "Grayscale", "Blur", "Edge Detection"])

with col2:
    uploaded_file = st.file_uploader("Drop your video file here", type=['mp4', 'mov', 'avi'])

    if uploaded_file is not None:
        st.video(uploaded_file) 
        
        if st.button("Render Custom Effects", use_container_width=True):
            
            settings = {
                "shape": shape,
                "box_color": box_color,
                "stroke_width": stroke_width,
                "connection": connection,
                "conn_color": conn_color,
                "size_mode": size_mode,
                "fixed_size": fixed_size,
                "max_blobs": max_blobs,
                "min_area": min_blob_size ** 2,
                "label_type": label_type,
                "text_color": text_color,
                "filter": filter_effect
            }
            
            with st.spinner('Compiling computer vision effects...'):
                tfile_in = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                tfile_out = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                
                tfile_in.write(uploaded_file.read())
                tfile_in.flush()
                
                process_video(tfile_in.name, tfile_out.name, settings)
                
                st.success("Rendering Complete!")
                
                with open(tfile_out.name, 'rb') as f:
                    video_bytes = f.read()
                    
                st.download_button(
                    label="📥 Download Final Video",
                    data=video_bytes,
                    file_name="pro_tracked_output.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )
                
                tfile_in.close()
                tfile_out.close()
                os.unlink(tfile_in.name)
                os.unlink(tfile_out.name)