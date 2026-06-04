# Advanced QR Code Detector & Decoder

A production-grade Python desktop application for detecting and decoding QR codes from images and videos, even when they are damaged, blurry, rotated, tilted, low-light, noisy, or partially obscured.

**Powered by:** ZXing-CPP + OpenCV + CustomTkinter

---

## Features

- **Robust ZXing-CPP decoding** - Uses the native C++ ZXing backend, with no Java dependency.
- **Direct, grayscale, rotation, and scale fallbacks** - Tries multiple decode strategies before reporting failure.
- **30+ step enhancement pipeline** - Recovers QR codes using thresholding, CLAHE, sharpening, morphology, rotation sweeps, resizing, deblurring, and combination pipelines.
- **Smart image quality assessment** - Measures sharpness, contrast, brightness, and noise to explain image quality problems.
- **ROI detection and crop retries** - Locates QR candidate regions with OpenCV and contour analysis, then retries decoding on targeted crops.
- **Perspective correction support** - Includes QR corner ordering and perspective correction helpers for skewed QR regions.
- **Multiple QR support** - Detects and decodes all readable QR/barcode results returned by ZXing in a single image or frame.
- **Video scanning** - Samples frames at configurable intervals and decodes the highest quality candidates first.
- **Weighted frame quality ranking** - Scores video frames by sharpness, contrast, QR visibility, and brightness.
- **Top-N video retry logic** - If the best frame fails, the app tries enhanced versions of the best frame and then the next best ranked frames.
- **Batch image processing** - Processes multiple image files sequentially and records each result.
- **Live progress and status updates** - Runs long scans in background threads with progress bars and current-stage messages.
- **Preview with zoom controls** - Displays the selected image or best video frame with fit, zoom in, and zoom out controls.
- **Structured result metadata** - Shows decoded text plus format, confidence, processing time, resolution, frame number, and enhancement used.
- **Scan history** - Keeps timestamped scan results with filename, success/failure status, metadata, and decoded values.
- **Searchable and clearable history** - Filter previous scans by filename or result text, and clear the history when needed.
- **Dashboard statistics** - Tracks total scans, successful scans, and failed scans in the sidebar.
- **Export tools** - Copy decoded text, save a text result, export history to JSON/CSV, and save the current preview image.
- **Dark/light theme switching** - Modern CustomTkinter interface with configurable appearance.
- **Runtime logging** - Creates timestamped log files under `logs/` for startup, decode, and error diagnostics.

---

## Installation

### Prerequisites

- **Python 3.9+** (recommended: 3.10 or 3.11)
- **pip** (Python package manager)

### Step-by-Step Setup

```bash
# 1. Open a terminal and navigate to the project directory
cd "c:\Users\Admin\Desktop\qr project"

# 2. Create a virtual environment
python -m venv venv

# 3. Activate the virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
# source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the application
python main.py
```

### Dependencies

| Package | Purpose |
|---|---|
| `zxing-cpp` | QR and barcode decoding through the ZXing C++ backend |
| `opencv-python` | Image/video processing, QR region detection, enhancement pipeline |
| `Pillow` | Image loading, conversion, and preview support |
| `numpy` | Array operations for image processing |
| `customtkinter` | Modern desktop GUI framework |

---

## Usage Guide

### Scanning an Image

1. Launch the app with `python main.py`.
2. Click **Browse Image** and select an image file.
3. The app shows a preview, attempts direct decode first, then automatically runs enhancement and ROI recovery if needed.
4. Results include decoded text, format, confidence, processing time, resolution, and the enhancement strategy that succeeded.

### Scanning a Video

1. Click **Browse Video** and select a video file.
2. The app samples frames at the configured interval.
3. Frames are ranked by sharpness, contrast, QR visibility, and brightness.
4. The best frame is decoded first; if that fails, enhanced and top-N frame retries are attempted.
5. Results include the frame number used and video scan metadata.

### Batch Processing

1. Click **Batch Process** and select multiple image files.
2. Each image is processed using the same direct, enhancement, and ROI workflow.
3. Results are added to scan history.

### Exporting Results

- **Copy** - Copy decoded text to the clipboard.
- **Save** - Save the current decoded text to a `.txt` file.
- **Export JSON** - Export scan history with metadata as JSON.
- **Export CSV** - Export scan history as CSV.
- **Save Screenshot** - Save the current preview image.

### Settings

- **Appearance Theme** - Switch between Dark and Light mode.
- **Video Frame Interval** - Control how often frames are sampled from videos, in seconds.
- **Top N Video Frames** - Set how many ranked video frames are retried during difficult scans.

---

## Project Architecture

```text
project/
|-- main.py                    # Entry point, logging, required directories
|-- requirements.txt           # Dependencies
|-- README.md                  # Project documentation
|
|-- ui/
|   |-- dashboard.py           # Main application window and workflows
|   |-- widgets.py             # Status cards, result card, preview, progress, history, file picker
|   |-- themes.py              # Color palette and theme config
|   `-- __init__.py
|
|-- core/
|   |-- image_decoder.py       # Image decode orchestration
|   |-- video_decoder.py       # Video decode orchestration
|   |-- enhancer.py            # Enhancement pipeline and quality assessment
|   |-- frame_selector.py      # Video frame scoring and ranking
|   |-- qr_detector.py         # QR region detection, ROI crop, perspective correction
|   |-- zxing_decoder.py       # ZXing-CPP wrapper and structured decode results
|   `-- __init__.py
|
|-- assets/                    # App resources
`-- logs/                      # Runtime logs
```

---

## Decode Workflow

### Image Workflow

1. Load image with OpenCV, falling back to Pillow if needed.
2. Attempt direct ZXing decode with `try_harder=True`.
3. If direct decode fails, assess image quality.
4. Run progressive enhancement and decode each enhanced variant.
5. Detect QR candidate regions, crop with padding, and retry direct/enhanced decode on each ROI.
6. Return structured results and scan metadata.

### Video Workflow

1. Open the video with OpenCV.
2. Extract frames at the configured interval.
3. Rank sampled frames by weighted quality score.
4. Try direct decode on the best frame.
5. Enhance the best frame if direct decode fails.
6. Try the remaining top-N ranked frames with direct and enhanced decode attempts.
7. Return structured results with frame metadata.

---

## Enhancement Pipeline

The system applies enhancements when direct decode fails:

1. Grayscale, histogram equalization, and CLAHE.
2. Adaptive thresholding and OTSU thresholding.
3. Gaussian blur reduction, median filtering, and bilateral filtering.
4. Sharpening and unsharp masking.
5. Contrast stretching, brightness correction, and gamma correction.
6. Morphological opening, closing, erosion, and dilation.
7. Edge enhancement.
8. Rotation attempts at 45, 90, 135, 180, 225, 270, and 315 degrees.
9. Multi-scale resize at 1.5x, 2x, 3x, and 4x.
10. Noise removal, deblurring, super-resolution simulation, and combination pipelines.

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError: zxingcpp` | Run `pip install zxing-cpp` |
| App will not start | Make sure Python 3.9+ is installed and dependencies are installed |
| Video will not open | Install or update OpenCV with `pip install -U opencv-python` |
| Theme looks wrong | Update CustomTkinter with `pip install -U customtkinter` |
| No QR decoded | Try a sharper image, crop closer to the QR code, or lower the video frame interval |

---

## License

This project is for educational and personal use.
