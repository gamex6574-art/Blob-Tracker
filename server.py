from flask import Flask, request, send_file
from flask_cors import CORS
import cv2
import tempfile
import os

app = Flask(__name__)
# Allow your HTML frontend to communicate with this server
CORS(app) 

# Helper function to convert UI Hex colors to OpenCV's BGR format
def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (rgb[2], rgb[1], rgb[0])

def process_video_logic(input_path, output_path, settings):
    cap = cv2.VideoCapture(input_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    object_detector = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=40)

    # Convert all incoming UI colors
    box_color = hex_to_bgr(settings['box_color'])
    conn_color = hex_to_bgr(settings['conn_color'])
    text_color = hex_to_bgr(settings['text_color'])
    thick = int(settings['stroke_width'])
    min_area = int(settings['min_size']) ** 2
    max_blobs = int(settings['max_blobs'])

    while True:
        ret, frame = cap.read()
        if not ret: break

        mask = object_detector.apply(frame)
        _, mask = cv2.threshold(mask, 254, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter by size and limit the count
        valid_blobs = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
        valid_blobs = sorted(valid_blobs, key=cv2.contourArea, reverse=True)[:max_blobs]
        
        blob_centers = []

        for i, cnt in enumerate(valid_blobs):
            x, y, w, h = cv2.boundingRect(cnt)
            center_x, center_y = x + w // 2, y + h // 2
            blob_centers.append((center_x, center_y))

            # --- 1. Draw Shapes ---
            if settings['shape'] == "Basic Rectangle":
                cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, thick)
            
            elif settings['shape'] == "Circle":
                radius = max(w, h) // 2
                cv2.circle(frame, (center_x, center_y), radius, box_color, thick)
            
            elif settings['shape'] == "L-Frame":
                l = min(w, h) // 4
                # Top-left
                cv2.line(frame, (x, y), (x+l, y), box_color, thick)
                cv2.line(frame, (x, y), (x, y+l), box_color, thick)
                # Top-right
                cv2.line(frame, (x+w, y), (x+w-l, y), box_color, thick)
                cv2.line(frame, (x+w, y), (x+w, y+l), box_color, thick)
                # Bottom-left
                cv2.line(frame, (x, y+h), (x+l, y+h), box_color, thick)
                cv2.line(frame, (x, y+h), (x, y+h-l), box_color, thick)
                # Bottom-right
                cv2.line(frame, (x+w, y+h), (x+w-l, y+h), box_color, thick)
                cv2.line(frame, (x+w, y+h), (x+w, y+h-l), box_color, thick)
                
            elif settings['shape'] == "Crosshair":
                l = min(w, h) // 3
                cv2.line(frame, (center_x - l, center_y), (center_x + l, center_y), box_color, thick)
                cv2.line(frame, (center_x, center_y - l), (center_x, center_y + l), box_color, thick)

            # --- 2. Draw Text Labels ---
            label = ""
            if settings['label_type'] == "index":
                label = f"#{i+1}"
            elif settings['label_type'] == "custom":
                label = settings['custom_text']

            if label:
                # Offset the text slightly above the bounding box
                cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 2)

        # --- 3. Draw Connections ---
        if len(blob_centers) > 1:
            if settings['connection'] == "Sequential (Line)":
                for i in range(len(blob_centers) - 1):
                    cv2.line(frame, blob_centers[i], blob_centers[i+1], conn_color, thick)
            
            elif settings['connection'] == "Central Hub":
                # Calculate the mathematical center of all objects
                hub_x = sum(c[0] for c in blob_centers) // len(blob_centers)
                hub_y = sum(c[1] for c in blob_centers) // len(blob_centers)
                
                # Draw the hub and connect everything to it
                cv2.circle(frame, (hub_x, hub_y), 6, conn_color, -1)
                for center in blob_centers:
                    cv2.line(frame, (hub_x, hub_y), center, conn_color, thick)

        out.write(frame)

    cap.release()
    out.release()

# --- Flask API Endpoint ---
@app.route('/process', methods=['POST'])
def process_api():
    if 'video' not in request.files:
        return "No video uploaded", 400

    video_file = request.files['video']
    
    # Catch all the new variables sent from app.js
    settings = {
        'shape': request.form.get('shape'),
        'box_color': request.form.get('box_color'),
        'stroke_width': request.form.get('stroke_width'),
        'connection': request.form.get('connection'),
        'conn_color': request.form.get('conn_color'),
        'label_type': request.form.get('label_type'),
        'custom_text': request.form.get('custom_text', ''),
        'text_color': request.form.get('text_color'),
        'max_blobs': request.form.get('max_blobs'),
        'min_size': request.form.get('min_size')
    }

    tfile_in = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile_out = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    
    video_file.save(tfile_in.name)
    process_video_logic(tfile_in.name, tfile_out.name, settings)

    # Return the processed video back to the JavaScript frontend
    response = send_file(tfile_out.name, mimetype='video/mp4')
    
    # Clean up files in the background
    @response.call_on_close
    def cleanup():
        os.unlink(tfile_in.name)
        os.unlink(tfile_out.name)
        
    return response

if __name__ == '__main__':
    app.run(port=5000, debug=True)