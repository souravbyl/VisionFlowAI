Here's your updated README.md file ready to copy and paste:

```markdown
# VisionFlowAI

Real-Time Video Intelligence Engine with Motion Detection, Object Recognition & Tracking

## Table of Contents
- [Project Structure](#project-structure)
- [Architecture Overview](#architecture-overview)
- [Current Implementation](#current-implementation)
- [Component Details](#component-details)
- [Configuration](#configuration)
- [Data Flow](#data-flow)
- [Known Issues & Limitations](#known-issues--limitations)
- [Future Improvements](#future-improvements)

---

## Project Structure

```
VisionFlowAI/
├── main.py                          # Entry point
├── config/
│   ├── dev.yaml                     # Development configuration
│   └── colab.yaml                   # Colab configuration
├── vfai/                            # Main package
│   ├── __init__.py
│   ├── main_impl.py                 # Engine initialization & startup
│   ├── engine.py                    # Main processing pipeline
│   ├── source.py                    # Frame grabbing from video source
│   ├── motion.py                    # Motion detection
│   ├── detector.py                  # YOLO-based object detection
│   ├── tracker.py                   # Object tracking (KCF/CSRT)
│   ├── event_dispatcher.py          # Event handling & logging
│   ├── config.py                    # Configuration model
│   ├── config_loader.py             # YAML config parser
│   ├── loggermgr.py                 # Logging system setup
│   ├── colorcode.py                 # Color constants for visualization
│   ├── coordinate.py                # 2D coordinate wrapper
│   ├── roi.py                       # Region of Interest management
│   ├── streamprop.py                # Stream properties (width, height, FPS)
│   ├── cqueue.py                    # Circular queue for frames
│   ├── frame.py                     # Frame data structure
│   ├── framebuffer.py               # Frame buffering (versioned)
│   ├── timeboundedqueue.py          # TTL-based frame queue
│   ├── cv_util.py                   # OpenCV utility functions
│   └── metrics/
│       ├── __init__.py
│       ├── event.py                 # Metric event dataclass
│       ├── aggregator.py            # Metrics aggregation
│       └── logger.py                # Metrics logging
└── dumps/                           # Detection event snapshots & metadata

```

---

## Architecture Overview

VisionFlowAI is a real-time video processing engine that combines motion detection, YOLO-based object detection, and KCF/CSRT tracking to efficiently identify and track objects in video streams. The system uses a pipeline architecture with frame buffering, motion filtering, and event dispatching.

### Core Design Principles
- **Efficiency**: Motion filtering reduces expensive YOLO inference to relevant regions only
- **Real-time**: Circular queue buffers with configurable sizes and frame throttling
- **Modularity**: Decoupled components with clear responsibilities
- **Async Processing**: Threaded architecture for non-blocking frame grabbing and event handling
- **Configurability**: YAML-based configuration for all parameters

---

## Current Implementation

### System Flow
```
Source (Frame Grabbing)
    ├─ Opens VideoCapture from config URL
    ├─ Throttles frames (50% drop rate, configurable)
    └─ Enqueues valid frames to circular buffer
         ↓
CQueue (Circular Buffer)
    ├─ Fixed-size circular queue (360k frames by default)
    └─ Returns frames to engine on demand
         ↓
Engine (Main Processing Pipeline)
    ├─ Dequeues frames from buffer
    ├─ Extracts ROI (Region of Interest)
    │
    ├─ Motion Detection Phase
    │  ├─ Motion.get_grayscale() → converts to grayscale + Gaussian blur
    │  ├─ Frame differencing with previous frame
    │  ├─ Binary thresholding (threshold=25)
    │  ├─ Morphological operations (dilation)
    │  ├─ Contour detection & filtering (area > 500px)
    │  ├─ Bounding box merging & padding (20px)
    │  └─ Returns motion_roi if motion detected
    │
    ├─ Object Detection Phase (only if motion detected)
    │  ├─ Detector.detect() → YOLO inference on motion_roi
    │  ├─ Filters for person & truck classes only
    │  ├─ Picks highest-confidence detection
    │  ├─ Maps bbox back to full frame coordinates
    │  └─ Initializes tracker and dispatches event
    │
    └─ Tracking Phase (if tracking active)
       ├─ Tracker.update() → updates tracker position on motion_roi
       ├─ Falls back to motion detection if tracker fails
       └─ Forces re-detection after 5 seconds (redirect_interval)
             ↓
EventDispatcher
    ├─ Queues detection events asynchronously
    ├─ Saves snapshots & metadata as JSON
    ├─ Logs to metrics system
    └─ Maintains event history in dumps/ folder
```

---

## Component Details

### 1. **Main Implementation** (main_impl.py)
**Purpose**: Application startup, threading, and graceful shutdown.

**Key Responsibilities**:
- Load YAML configuration file
- Initialize LoggerManager for rotating file logs
- Create and coordinate worker threads (Source, Engine, EventDispatcher, Metrics)
- Handle SIGINT (Ctrl+C) and SIGTERM signals
- Graceful shutdown with proper thread joining

---

### 2. **Source** (source.py)
**Purpose**: Captures frames from video source and enqueues them.

**Key Operations**:
- `__init_source()`: Opens cv2.VideoCapture, detects source properties (width, height, FPS)
- `__run_impl()`: Main grab loop
  - Reads frames continuously
  - Applies target resolution scaling if configured
  - **Throttles by 50%** (every even frame dropped - configurable)
  - Enqueues every odd frame to circular buffer
  - Metrics tracking for grabber in/out/drop events
- `get_frame()`: Returns next available frame from queue

**Metrics**: Tracks "grabber" in/out/drop events

---

### 3. **CQueue** (cqueue.py)
**Purpose**: Circular FIFO queue for efficient frame buffering.

**Data Structure**:
- `queue[size]`: Fixed-size array (360k elements default)
- `front`, `rear`: Circular pointers
- Enqueue: `rear = (rear + 1) % size`
- Dequeue: `front = (front + 1) % size`

**Behavior**:
- Returns `None` if empty
- Logs fatal error if full (but continues, dropping frames)
- No backpressure mechanism

---

### 4. **Motion Detection** (motion.py)
**Purpose**: Detects motion regions in video frames using frame differencing.

**Algorithm**:
1. Convert frame to grayscale + Gaussian blur (5×5 kernel)
2. Compute frame difference with previous frame
3. Binary threshold at fixed value (threshold=25)
4. Dilate to connect nearby motion regions (2 iterations)
5. Count motion pixels: if `(pixels / (w*h)) > motion_percent`, motion detected
6. Find contours, filter by area (min 500px)
7. Merge all bounding boxes with 20px padding

**Parameters**:
- `threshold = 25` (binary threshold - hardcoded)
- `min_area = 500` (contour filter - hardcoded)
- `padding = 20` (bbox expansion - hardcoded)
- `motion_percent` (config-driven, default 0.002)

**Output**: `(detected: bool, bbox: (x, y, w, h) | None)`

---

### 5. **Detector** (detector.py)
**Purpose**: Runs YOLO object detection on motion regions.

**Workflow**:
- `warmup()`: JIT compilation on first use (5 dummy forward passes)
- `detect(frame)`: Runs YOLOv8 inference with confidence threshold
  - Filters for classes: **person (0) & truck (7) only**
  - Returns: boxes, scores, class_ids for each detection
- Only **best detection** (max score) is processed downstream
- Returns YOLOv8 results object

**Model**: YOLOv8n (lightweight, real-time)

---

### 6. **Tracker** (tracker.py)
**Purpose**: Tracks detected objects across frames using correlation filters.

**Supported Algorithms**:
- `cv2_TrackerKCF`: Kernelized Correlation Filter (faster, less accurate)
- `cv2_TrackerCSRT`: Discriminative Correlation Filters with Spatial Regularization (slower, more accurate)

**Workflow**:
- `init(frame, bbox)`: Initialize tracker with detection in motion_roi
- `update(frame)`: Track object in next frame, returns `(success, bbox)`
- Returns local coordinates relative to motion_roi

**Behavior**:
- Falls back to motion detection if update fails (`success=False`)
- Re-detection forced after 5 seconds (configurable via `redirect_interval`)
- Tracker is cleaned up on failure or timeout

---

### 7. **Engine** (engine.py)
**Purpose**: Main processing pipeline orchestrating all components.

**Pipeline**:
1. Starts source thread for frame grabbing
2. Warmup detector on first frame
3. Main loop:
   - Dequeue frame from buffer
   - Extract ROI region
   - Run motion detection
   - If tracking active: update tracker with motion_roi
   - If motion detected & not tracking: run YOLO detection
   - Initialize new tracker on detection
   - Dispatch event to EventDispatcher
4. Cleanup on shutdown

**State Variables**:
- `tracker`: Current tracker object or None
- `tracking`: Boolean flag if actively tracking
- `last_detect_frame`: Frame ID of last detection (for timeout logic)
- `redirect_interval`: Frames before forced re-detection (fps * 5 seconds)

---

### 8. **Event Dispatcher** (event_dispatcher.py)
**Purpose**: Handles detection events asynchronously.

**Operations**:
- `dispatch_event()`: Queues detection with metadata
- Saves snapshot image as JPEG
- Saves metadata as JSON with detection details
- Logs event to console and rotating file

**Event Metadata**:
```json
{
  "id": 0,
  "class_name": "person",
  "class_id": 0,
  "confidence": "0.95",
  "since_start": "23.45",
  "epoch": "1234567890",
  "detected_at": "1234567893",
  "input_frame_id": "42"
}
```

**Output**: `dumps/F{frame_id}-D{detection_id}_C{class_name}-P{confidence}.{jpg,json}`

---

### 9. **Configuration System** (config.py, config_loader.py)
**Purpose**: Centralized configuration management.

**Components**:
- `Config`: Main configuration object with properties
- `ConfigLoader`: Parses YAML files into Config objects
- `StreamProperties`: Encapsulates video stream metadata
- `ROI`: Region of Interest management

**Config Sections**:
```yaml
app:
  debug: true/false              # Debug logging
  loglevel: d|i|w|e|c           # Log level

display:
  imshow_source_frames: bool     # Show source
  imshow_motion_results: bool    # Show motion detection
  imshow_tracker_results: bool   # Show tracking
  imshow_detection_results: bool # Show detections

event:
  dump_path: string              # Where to save snapshots

model:
  name: string                   # YOLO model file
  threshold: float               # Detection confidence threshold (0-1)

source:
  url: string                    # Video file or stream URL
  reconnect_on_failure: bool     # Restart on disconnection
  roi:
    enabled: bool
    x1, y1, x2, y2: int         # ROI coordinates

motion:
  percent: float                 # Motion threshold (0-1)

tracker:
  enabled: bool                  # Enable tracking
  name: cv2_TrackerKCF|cv2_TrackerCSRT
```

---

### 10. **Logging Manager** (loggermgr.py)
**Purpose**: Non-blocking, asynchronous logging with file rotation.

**Features**:
- Queue-based logging (non-blocking writes)
- Time-based file rotation (daily by default)
- Dual output: console + file
- Configurable log level

**Log Format**:
```
2026-04-26 15:48:56,099 CRITICAL vfai.main_impl [main_impl.py:36:engine_loader] Message
```

---

## Configuration

### Quick Start
```bash
# Development (local video file)
python main.py --config config/dev.yaml

# Google Colab (streaming)
python main.py --config config/colab.yaml
```

### Example dev.yaml
```yaml
app:
  debug: true
  loglevel: i

display:
  imshow_source_frames: true
  imshow_motion_threshold: false
  imshow_motion_results: false
  imshow_tracker_results: false
  imshow_detection_results: true

event:
  dump_path: dumps

model:
  name: yolov8n.pt
  threshold: 0.3

source:
  url: "path/to/video.mp4"
  reconnect_on_failure: false
  roi:
    enabled: false
    x1: null
    y1: null
    x2: null
    y2: null

motion:
  percent: 0.002

tracker:
  enabled: true
  name: cv2_TrackerCSRT
```

---

## Data Flow

### Detailed Frame Journey

**1. Frame Capture** (Source.__run_impl)
```
VideoCapture.read() → Frame(id, data, timestamp, epoch, since_start)
Every 2nd frame: dropped (metrics: "grabber.drop")
Odd frames: enqueued to CQueue
```

**2. ROI Extraction** (Engine.__run_impl)
```
roiframe = full_frame[y1:y2, x1:x2]
Extract configured ROI region from full frame
```

**3. Motion Detection** (Motion.check_if_motion)
```
grayscale → diff → threshold → dilate → contours → merge → bbox
If motion_pixels / (w*h) > motion_percent:
  Output: motion_roi (cropped frame)
Else:
  Output: None, skip detection
```

**4. Tracking Update** (Engine tracking phase)
```
If tracker active:
  ok, bbox = tracker.update(motion_roi)
  If ok AND frame_id - last_detect < timeout:
    Continue tracking
  Else:
    Clean up tracker, back to detection
```

**5. Object Detection** (Detector.detect)
```
YOLO inference on motion_roi
Filter results: conf >= threshold AND class in [person, truck]
Pick best confidence detection
Map bbox from motion_roi to roiframe coordinates
```

**6. Tracker Initialization** (Engine detection phase)
```
Create new Tracker instance
tracker.init(motion_roi, local_bbox_coords)
Set tracking = True
Store frame_id for timeout logic
```

**7. Event Dispatch** (EventDispatcher)
```
Create event metadata
Save snapshot: dumps/F{frame_id}-D{id}_C{class}-P{conf}.jpg
Save metadata: dumps/F{frame_id}-D{id}_C{class}-P{conf}.json
Log to console and rotating file
```

---

## Known Issues & Limitations

### **HIGH PRIORITY**

#### 1. Single Object Detection Per Motion Region
**Issue**: Engine only processes highest-confidence detection per frame
```python
# engine.py
i = np.argmax(scores)  # Only best detection
```

**Problem**: 
- If multiple people in same motion region, only highest-confidence detected
- Others completely missed
- No multi-object tracking support

**Impact**: Significant detection loss in crowded scenes

**Solution**: Implement Hungarian algorithm for multi-object detection-to-tracker association

---

#### 2. Hardcoded 50% Frame Drop Rate
**Issue**: Source throttles by 50% regardless of processing capability
```python
# source.py - Line ~134-137
if self.__frame_count % 2 == 0:
    drop frame
else:
    enqueue frame
```

**Problem**:
- No configuration or justification
- Arbitrary throttling reduces temporal resolution by half
- May miss fast-moving objects
- Doesn't adapt to load

**Impact**: Effective FPS halved (30 FPS input → 15 FPS processed)

**Solution**: Make frame drop rate configurable based on available compute

---

#### 3. No Multi-Object Tracking
**Issue**: Single tracker per entire scene
```python
# engine.py
tracker = Tracker(...)  # Single tracker
```

**Problem**:
- Cannot track multiple simultaneous objects
- No persistent object IDs across frames
- Cannot count unique objects
- Cannot track multiple paths

**Impact**: System limited to single-object scenarios

---

### **MEDIUM PRIORITY**

#### 4. Hardcoded Motion Detection Parameters
**Issue**: Hardcoded motion thresholds not tunable
```python
# motion.py
threshold = 25           # binary threshold
min_area = 500          # contour area
padding = 20            # bbox padding
```

**Problem**:
- Different environments need different thresholds (night/day, indoor/outdoor)
- Current values cause false positives/negatives
- No per-scenario tuning possible

**Impact**: One-size-fits-all approach, suboptimal accuracy

---

#### 5. Fixed 5-Second Re-detection Interval
**Issue**: Forces re-detection even if tracking works perfectly
```python
# engine.py - Line ~102
redirect_interval = self.__config.source.fps * 5
```

**Problem**:
- Wastes YOLO inference on stable, tracked objects
- Not adaptive to tracker confidence
- Unnecessary compute overhead

**Impact**: 20% of frames forced through expensive YOLO inference

---

#### 6. Silent Queue Overflow
**Issue**: CQueue silently drops frames when full
```python
# cqueue.py
if full:
    logger.fatal("Queue full")
    return None  # Silent drop
```

**Problem**:
- No backpressure; grabber continues regardless
- Engine unaware of frame loss
- No recovery mechanism

**Impact**: Data loss without visibility

---

#### 7. No Frame TTL (Time-To-Live)
**Issue**: Frames persist in queue indefinitely
```python
# No expiration mechanism in CQueue
```

**Problem**:
- Stale frames processed if queue stalls
- Unbounded memory growth possible
- Latency increases over time

**Impact**: System degrades as queue grows

---

#### 8. Tracker Initialization Uses Full ROI Coordinates
**Issue**: Tracker bbox might mismatch motion_roi frame reference
```python
# engine.py tracking phase
tracker.update(motion_roi)  # Frame is motion_roi
```

**Status**: **FIXED** - Now uses consistent coordinate system

---

### **LOW PRIORITY**

#### 9. Busy-Wait Polling Pattern
**Issue**: Inefficient CPU usage in wait loops
```python
# Multiple places
while not stop_event.is_set():
    frame = get_frame()
    if frame is None:
        time.sleep(0.001)
        continue
```

**Problem**: CPU wakeups for fixed intervals

**Impact**: Minor, < 5% CPU overhead

---

## Future Improvements

### Phase 1: Multi-Object Detection & Tracking
- Process all detections above confidence threshold (not just best)
- Maintain dict of active trackers with unique IDs
- Implement Hungarian algorithm for detection-to-tracker association
- Assign new IDs to unmatched detections

### Phase 2: Configurable Frame Throttling
- Replace hardcoded 50% drop with config parameter
- Implement smart adaptive throttling based on queue depth
- Add metrics for queue utilization

### Phase 3: Tunable Motion Detection
- Move hardcoded thresholds to config.yaml
- Per-scenario motion profiles (day/night/indoor/outdoor)
- Adaptive thresholding based on lighting conditions

### Phase 4: Advanced Tracking
- Per-object tracker assignment (Kalman filter for prediction)
- Trajectory history and analytics
- Persistent object ID across disconnections

### Phase 5: Performance Optimization
- GPU acceleration for motion detection
- Batch YOLO inference on multiple motion regions
- Optimized queue implementation (avoid numpy copies)

---

## Dependencies

```
opencv-python==4.13.0.92
opencv-contrib-python==4.13.0.92
numpy==2.4.4
ultralytics==8.x (YOLOv8)
pyyaml==6.0.3
```

## License

See LICENSE file

```

Copy and paste this entire content into your README.md file!Copy and paste this entire content into your README.md file!