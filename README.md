# VisionFlowAI

Real-Time Video Intelligence Engine with Motion Detection, Object Recognition & Tracking

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Current Implementation](#current-implementation)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Known Issues & Limitations](#known-issues--limitations)
- [Improvement Plan](#improvement-plan)

---

## Architecture Overview

VisionFlowAI is a real-time video processing engine that combines motion detection, YOLO-based object detection, and KCF/CSRT tracking to efficiently identify and track objects in video streams. The system uses a pipeline architecture with frame buffering, motion filtering, and event dispatching.

### Core Design Principles
- **Efficiency**: Motion filtering reduces expensive YOLO inference to relevant regions only
- **Real-time**: Circular queue buffers with configurable sizes and frame throttling
- **Modularity**: Decoupled components (Source, Motion, Detection, Tracking, Dispatcher)
- **Async Processing**: Threaded architecture for non-blocking frame grabbing and event handling

---

## Current Implementation

### System Flow
```
VFAISource (Frame Grabbing)
    ├─ Opens VideoCapture from config URL
    ├─ Throttles frames (50% drop)
    └─ Enqueues valid frames to circular buffer
         ↓
VFAIQueue (Circular Buffer)
    ├─ Fixed-size circular queue (360k frames by default)
    └─ Returns frames to engine on demand
         ↓
VFAIEngine (Main Processing Pipeline)
    ├─ Dequeues frames from buffer
    ├─ Extracts ROI (Region of Interest)
    │
    ├─ Motion Detection Phase
    │  ├─ VFAIMotion.get_grayscale() → converts to grayscale + Gaussian blur
    │  ├─ Frame differencing with previous frame
    │  ├─ Binary thresholding (threshold=25)
    │  ├─ Morphological operations (dilation)
    │  ├─ Contour detection & filtering (area > 500px)
    │  ├─ Bounding box merging & padding
    │  └─ Returns motion_roi if motion detected
    │
    ├─ Object Detection Phase (only if motion detected)
    │  ├─ VFAIDetector.detect() → YOLO inference on motion_roi
    │  ├─ Picks highest-confidence detection only
    │  ├─ Maps bbox back to full frame coordinates
    │  └─ Dispatches event if object found
    │
    └─ Tracking Phase (if tracking active)
       ├─ VFAITracker.update() → updates tracker position
       ├─ Falls back to motion detection if tracker fails
       └─ Forces re-detection after 5 seconds (redirect_interval)
             ↓
VFAIEventDispatcher
    ├─ Queues detection events
    ├─ Logs to metrics system
    └─ Triggers downstream handlers
```

---

## Component Details

### 1. **VFAISource** (vfaisource.py)
**Purpose**: Captures frames from video source and enqueues them.

**Key Operations**:
- `__init_source()`: Opens cv2.VideoCapture and reads source properties (width, height, FPS)
- `__run_impl()`: Main grab loop
  - Reads frames continuously
  - Applies target resolution scaling if configured
  - **Throttles by 50%** (every even frame dropped)
  - Enqueues every odd frame to buffer
- `get_frame()`: Returns next available frame from queue

**Metrics**: Tracks "grabber" in/out/drop events

---

### 2. **VFAIQueue** (vfaiqueue.py)
**Purpose**: Circular FIFO queue for frame buffering.

**Data Structure**:
- `queue[size]`: Fixed-size array
- `front`, `rear`: Circular pointers
- Enqueue: `rear = (rear + 1) % size`
- Dequeue: `front = (front + 1) % size`

**Behavior**:
- Returns `None` if empty
- Logs fatal error if full (but continues)
- No backpressure mechanism

---

### 3. **VFAIMotion** (vfaimotion.py)
**Purpose**: Detects motion regions in video frames.

**Algorithm**:
1. Convert frame to grayscale + Gaussian blur (5×5 kernel)
2. Compute frame difference with previous frame
3. Binary threshold at fixed value (25)
4. Dilate to connect nearby motion regions (2 iterations)
5. Count motion pixels: if `(pixels / (w*h)) > motion_percent`, motion detected
6. Find contours, filter by area (min 500px)
7. Merge all bounding boxes with 40px padding

**Parameters** (Hardcoded):
- `threshold = 25` (binary threshold)
- `min_area = 500` (contour filter)
- `padding = 40` (bbox expansion)
- `motion_percent` (config-driven)

**Output**: Boolean + merged bbox `(x, y, w, h)` or None

---

### 4. **VFAIDetector** (vfaidetect.py - not provided but used)
**Purpose**: Runs YOLO object detection on motion regions.

**Workflow**:
- `warmup()`: JIT compilation on first use
- `detect(frame)`: Runs YOLOv8 inference
- Returns: boxes, scores, class_ids for each detection
- Only **best detection** (max score) is processed downstream

---

### 5. **VFAITracker** (vfaitracker.py)
**Purpose**: Tracks detected objects across frames.

**Supported Algorithms**:
- `cv2_TrackerKCF`: Kernelized Correlation Filter (faster, less accurate)
- `cv2_TrackerCSRT`: Discriminative Correlation Filters with Spatial Regularization (slower, more accurate)

**Workflow**:
- `init(frame, bbox)`: Initialize tracker with first detection
- `update(frame)`: Track object in next frame, returns `(success, bbox)`

**Behavior**:
- Falls back to motion detection if update fails
- Re-detection forced after 5 seconds (configurable via `redirect_interval`)

---

### 6. **VFAIEventDispatcher** (vfaievent_dispatcher.py - not provided but used)
**Purpose**: Handles detection events (logging, alerts, callbacks).

**Events Captured**:
- Detection class, confidence, bounding box
- Timestamp and frame snapshot
- Unique detection ID

---

## Data Flow

### Detailed Frame Journey

1. **Frame Grab** (VFAISource.__run_impl)
   ```
   VideoCapture.read() → VFAIFrame(id, data, timestamp)
   Every 2nd frame: dropped
   Odd frames: enqueued
   ```

2. **ROI Extraction** (VFAIEngine.__run_impl)
   ```
   roiframe = vfaiframe._data[y1:y2, x1:x2]
   (Crop to configured ROI region)
   ```

3. **Motion Detection** (VFAIMotion.check_if_motion)
   ```
   grayscale → diff → threshold → dilate → contours → merge → bbox
   Output: motion_roi or None
   ```

4. **Object Detection** (VFAIDetector.detect)
   ```
   YOLO inference on motion_roi
   Output: Multiple detections, best picked
   ```

5. **Tracking** (VFAITracker.update)
   ```
   Tracker updates position in roiframe
   If successful: continue tracking
   If failed: back to motion detection
   ```

6. **Event Dispatch** (VFAIEventDispatcher.dispatch_event)
   ```
   Queue event with metadata
   Trigger downstream handlers
   ```

---

## Known Issues & Limitations

### **HIGH PRIORITY**

#### 1. Single Object Per Motion Region
**Issue**: [vfaiengine.py](vfaiengine.py#L270)
```python
i = np.argmax(scores)  # Only highest-confidence detection
```
**Problem**: 
- If 3 people in same motion region, only 1 is detected/tracked
- Others are completely missed

**Current Impact**: Significant detection loss in crowded scenes

---

#### 2. Hardcoded 50% Frame Drop
**Issue**: [vfaisource.py](vfaisource.py#L88-L93)
```python
if self.__frame_count % 2 == 0:
    self.__metrics_q.put(MetricEvent("grabber", "drop", ...))
else:
    self.__frame_queue.enqueue(vfframe)
```
**Problem**:
- No justification or configuration
- Arbitrary throttling reduces temporal resolution by half
- May miss fast-moving objects or quick motions

**Current Impact**: Effective FPS halved (30 FPS → 15 FPS)

---

#### 3. No Multi-Object Tracking
**Issue**: [vfaiengine.py](vfaiengine.py#L295-L301)
```python
tracker = VFAITracker(...)  # Single tracker per frame
```
**Problem**:
- One tracker per scene, not per object
- No persistent object IDs
- Cannot count unique objects or track multiple paths

**Current Impact**: Impossible to track multiple simultaneous objects

---

### **MEDIUM PRIORITY**

#### 4. Hardcoded Motion Detection Parameters
**Issue**: [vfaimotion.py](vfaimotion.py#L24, #L37, #L48)
```python
_, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)  # threshold=25
if area < 500:  # contour area
    continue
pad = 40  # bbox padding
```
**Problem**:
- Not tunable per scenario (night/day, indoor/outdoor, etc.)
- Different environments need different thresholds
- Causes false positives/negatives

**Current Impact**: One-size-fits-all approach, suboptimal for diverse scenarios

---

#### 5. Fixed 5-Second Re-detection Interval
**Issue**: [vfaiengine.py](vfaiengine.py#L82)
```python
redirect_interval = self.__config.source.fps * 5
```
**Problem**:
- Forces re-detection even if tracker is working perfectly
- Wastes computation on stable, tracked objects
- Not adaptive to tracker confidence

**Current Impact**: Unnecessary YOLO inference overhead

---

#### 6. Queue Overflow Silent Failure
**Issue**: [vfaiqueue.py](vfaiqueue.py#L7-L11)
```python
if self.front == (self.rear + 1) % self.size:
    self.__logger.fatal("Queue is full, might lead to drop.")
    return None  # Silently drops frame
```
**Problem**:
- No backpressure; source keeps grabbing
- Engine doesn't know why frames disappeared
- Memory pressure not visible to system

**Current Impact**: Data loss without recovery mechanism

---

#### 7. No Frame TTL (Time-To-Live)
**Issue**: Frames persist in queue indefinitely
**Problem**:
- Stale frames processed if queue stalls
- Old frames mixed with new ones
- Unbounded memory growth possible

**Current Impact**: Latency increases, old data processed

---

### **LOW PRIORITY**

#### 8. Polling Sleep Pattern
**Issue**: [vfaiengine.py](vfaiengine.py#L94-L97)
```python
if vfaiframe is None:
    time.sleep(0.001)
    continue
```
**Problem**:
- Busy-wait loop wastes CPU
- No event-based signaling

**Current Impact**: Minor CPU overhead, not critical

---

## Improvement Plan

### **Phase 1: Multi-Object Detection & Tracking** (HIGH PRIORITY)

#### Fix: Process All Detections Above Confidence Threshold

**File**: `vfaiengine.py`

**Changes**:
1. Replace single object logic with multi-object processing
2. Maintain dictionary of active trackers with unique IDs
3. Implement detection-to-track association (Hungarian algorithm or simple IOU matching)
4. Assign new IDs to unmatched detections

**Implementation**:

```python
# In VFAIEngine.__init__
self.__active_trackers = {}  # {tracker_id: VFAITracker}
self.__next_tracker_id = 0
self.__tracker_iou_threshold = 0.3  # config

# In __run_impl, replace single detection logic with:
def __process_detections(self, results, motion_roi, roiframe, motion_x, motion_y):
    """Process all detections above confidence threshold"""
    
    current_detections = []
    
    for r in results:
        boxes = r.boxes.xyxy.cpu().numpy()
        scores = r.boxes.conf.cpu().numpy()
        class_ids = r.boxes.cls.cpu().numpy().astype(int)
        
        for idx in range(len(boxes)):
            conf = float(scores[idx])
            
            # Filter by confidence threshold (config-driven)
            if conf < self.__config.detection_confidence_threshold:
                continue
            
            dx1, dy1, dx2, dy2 = boxes[idx]
            dx1_full = int(motion_x + dx1)
            dy1_full = int(motion_y + dy1)
            dx2_full = int(motion_x + dx2)
            dy2_full = int(motion_y + dy2)
            
            current_detections.append({
                'bbox': (dx1_full, dy1_full, dx2_full, dy2_full),
                'confidence': conf,
                'class_id': int(class_ids[idx]),
                'class_name': self.__detector.get_class_name(int(class_ids[idx])),
                'iou_matched': False
            })
    
    # Match current detections to active trackers
    self.__match_and_track(current_detections, roiframe, motion_x, motion_y)

def __match_and_track(self, current_detections, roiframe, motion_x, motion_y):
    """Associate detections with existing trackers using IOU"""
    
    unmatched_detections = list(range(len(current_detections)))
    
    # Try to match with existing trackers
    for tracker_id, tracker in list(self.__active_trackers.items()):
        ok, tracker_bbox = tracker.update(roiframe)
        
        if not ok:
            del self.__active_trackers[tracker_id]
            continue
        
        # Find best IOU match
        best_match_idx = -1
        best_iou = 0
        
        for idx, det in enumerate(current_detections):
            if idx not in unmatched_detections:
                continue
            
            iou = self.__compute_iou(tracker_bbox, det['bbox'])
            if iou > best_iou and iou > self.__tracker_iou_threshold:
                best_iou = iou
                best_match_idx = idx
        
        if best_match_idx >= 0:
            unmatched_detections.remove(best_match_idx)
            current_detections[best_match_idx]['iou_matched'] = True
    
    # Create new trackers for unmatched detections
    for idx in unmatched_detections:
        det = current_detections[idx]
        dx1, dy1, dx2, dy2 = det['bbox']
        
        tracker = VFAITracker(self.__config, description=f"tracker_{self.__next_tracker_id}")
        tracker.init(roiframe, (dx1, dy1, dx2 - dx1, dy2 - dy1))
        
        self.__active_trackers[self.__next_tracker_id] = tracker
        self.__next_tracker_id += 1
        
        # Dispatch event
        self.__event_dispatcher.dispatch_event(
            vfaiframe=vfaiframe,
            detection_id=self.__next_tracker_id,
            class_id=det['class_id'],
            class_name=det['class_name'],
            confidence=det['confidence'],
            eventtime=time.perf_counter(),
            snap=roiframe,
            bbox=det['bbox'],
            tracker_id=self.__next_tracker_id
        )

def __compute_iou(self, box1, box2):
    """Compute Intersection over Union"""
    x1_min, y1_min, x1_max, y1_max = box1 if len(box1) == 4 else (box1[0], box1[1], box1[0] + box1[2], box1[1] + box1[3])
    x2_min, y2_min, x2_max, y2_max = box2
    
    inter_x_min = max(x1_min, x2_min)
    inter_y_min = max(y1_min, y2_min)
    inter_x_max = min(x1_max, x2_max)
    inter_y_max = min(y1_max, y2_max)
    
    inter_area = max(0, inter_x_max - inter_x_min) * max(0, inter_y_max - inter_y_min)
    
    box1_area = (x1_max - x1_min) * (y1_max - y1_min)
    box2_area = (x2_max - x2_min) * (y2_max - y2_min)
    
    union_area = box1_area + box2_area - inter_area
    
    return inter_area / union_area if union_area > 0 else 0
```

**Config Additions** (vfaiconfig.py):
```yaml
detection_confidence_threshold: 0.5  # minimum confidence to process
tracker_iou_threshold: 0.3  # IOU threshold for detection-tracker matching
```

---

### **Phase 2: Make Frame Throttling Configurable** (HIGH PRIORITY)

#### Fix: Replace Hardcoded 50% Drop with Smart Throttling

**File**: `vfaisource.py`

**Changes**:

```python
# In VFAISource.__init__
self.__frame_drop_rate = config.frame_drop_rate  # 0.0 = no drop, 0.5 = 50% drop

# In __run_impl, replace:
if self.__frame_count % 2 == 0:
    self.__metrics_q.put(MetricEvent("grabber", "drop", ...))
else:
    self.__frame_queue.enqueue(vframe)

# With:
import random

should_drop = random.random() < self.__frame_drop_rate
if should_drop:
    self.__metrics_q.put(MetricEvent("grabber", "drop", ...))
else:
    self.__frame_queue.enqueue(vframe)
```

**Config Additions** (vfaiconfig.py):
```yaml
frame_drop_rate: 0.0  # 0.0 = no drop, 0.5 = 50%, 1.0 = drop all
```

**Rationale**: 
- Set to `0.0` to process every frame (minimal latency)
- Set to `0.5` if GPU bandwidth is bottleneck
- Monitor queue depth + metrics to tune optimally

---

### **Phase 3: Configurable Motion Detection Parameters** (MEDIUM PRIORITY)

#### Fix: Move Hardcoded Values to Config

**File**: `vfaimotion.py`

**Changes**:

```python
# In VFAIMotion.__init__
self.__motion_threshold = config.motion.threshold  # 25
self.__min_contour_area = config.motion.min_contour_area  # 500
self.__bbox_padding = config.motion.bbox_padding  # 40
self.__blur_kernel = config.motion.blur_kernel  # (5, 5)
self.__dilation_iterations = config.motion.dilation_iterations  # 2

# Update methods to use these:
def check_if_motion(self, gray, w, h):
    diff = cv2.absdiff(self.__prev_gray, gray)
    _, thresh = cv2.threshold(diff, self.__motion_threshold, 255, cv2.THRESH_BINARY)
    thresh = cv2.dilate(thresh, self.__kernel, iterations=self.__dilation_iterations)
    
    # ... (rest of logic)
    
    if area < self.__min_contour_area:
        continue
    
    # ... (rest of logic)
    
    pad = self.__bbox_padding
```

**Config Additions** (vfaiconfig.py):
```yaml
motion:
  threshold: 25
  min_contour_area: 500
  bbox_padding: 40
  blur_kernel: [5, 5]
  dilation_iterations: 2
```

---

### **Phase 4: Adaptive Re-detection Strategy** (MEDIUM PRIORITY)

#### Fix: Replace Fixed Interval with Confidence-Based Trigger

**File**: `vfaiengine.py`

**Changes**:

```python
# In VFAIEngine.__init__
self.__tracker_confidence_threshold = config.tracker_confidence_threshold  # 0.7
self.__max_tracking_age = config.max_tracking_age  # frames
self.__tracker_ages = {}  # {tracker_id: age}

# In __match_and_track:
for tracker_id, tracker in list(self.__active_trackers.items()):
    ok, tracker_bbox = tracker.update(roiframe)
    
    # Increment age
    self.__tracker_ages[tracker_id] = self.__tracker_ages.get(tracker_id, 0) + 1
    
    if not ok or self.__tracker_ages[tracker_id] > self.__max_tracking_age:
        del self.__active_trackers[tracker_id]
        del self.__tracker_ages[tracker_id]
        # Force re-detection by setting motion_detected = True
        continue
    
    # (rest of matching logic)
```

**Config Additions** (vfaiconfig.py):
```yaml
tracker_confidence_threshold: 0.7
max_tracking_age: 300  # frames (e.g., 10 seconds at 30 FPS)
```

---

### **Phase 5: Queue Backpressure & TTL** (MEDIUM PRIORITY)

#### Fix: Implement Bounded Queue with TTL

**File**: `vfaitimeboundedqueue.py` (already exists but needs enhancement)

**New Implementation**:

```python
import logging
import time
from queue import Queue


class TimeBoundedQueue:
    def __init__(self, max_age_sec: float = 5.0, max_size: int = 100):
        self.max_age_sec = max_age_sec
        self.max_size = max_size
        self.queue = []
        self.__logger = logging.getLogger(__name__)
    
    def enqueue(self, element):
        """Add element with timestamp; drop oldest if full"""
        current_time = time.perf_counter()
        
        # Remove stale frames
        self.queue = [
            (item, ts) for item, ts in self.queue
            if (current_time - ts) < self.max_age_sec
        ]
        
        if len(self.queue) >= self.max_size:
            dropped = self.queue.pop(0)
            self.__logger.warning(
                f"Queue full (max_size={self.max_size}), dropped frame id={dropped[0]._id}"
            )
        
        self.queue.append((element, current_time))
    
    def dequeue(self):
        """Remove and return oldest element; drop stale items"""
        current_time = time.perf_counter()
        
        while self.queue:
            item, ts = self.queue[0]
            
            if (current_time - ts) > self.max_age_sec:
                dropped = self.queue.pop(0)
                self.__logger.debug(
                    f"Dropped stale frame id={dropped[0]._id}, age={(current_time - dropped[1]):.2f}s"
                )
                continue
            
            return self.queue.pop(0)[0]
        
        return None
```

**Config Additions** (vfaiconfig.py):
```yaml
queue:
  max_age_sec: 5.0
  max_size: 100
  type: "TimeBoundedQueue"  # or "VFAIQueue" for legacy
```

---

### **Phase 6: Event-Based Frame Signaling** (LOW PRIORITY)

#### Fix: Replace Sleep-Based Polling with Threading Events

**File**: `vfaiqueue.py`

**Changes**:

```python
import logging
import threading


class VFAIQueue:
    def __init__(self, size):
        self.size = size
        self.queue = [None] * self.size
        self.rear = self.front = -1
        self.__logger = logging.getLogger(__name__)
        self.__not_empty = threading.Event()  # Signal when frame available
    
    def enqueue(self, element):
        if self.front == (self.rear + 1) % self.size:
            self.__logger.fatal("Queue is full, might lead to drop.")
            return None
        if self.front == -1:
            self.front = 0
        self.rear = (self.rear + 1) % self.size
        self.queue[self.rear] = element
        self.__not_empty.set()  # Signal availability
    
    def dequeue(self):
        if self.front == -1:
            self.__not_empty.clear()
            return None
        element = self.queue[self.front]
        self.queue[self.front] = None
        if self.front == self.rear:
            self.front = self.rear = -1
            self.__not_empty.clear()
        else:
            self.front = (self.front + 1) % self.size
        return element
    
    def wait_for_frame(self, timeout=1.0):
        """Wait for frame availability instead of polling"""
        self.__not_empty.wait(timeout)
```

**Engine Changes** (vfaiengine.py):

```python
# Replace polling loop:
while not self.__stop_event.is_set():
    if self.__config.debug:
        if cv2.waitKey(1) == ord("q"):
            pass
    
    vfaiframe = self.__source.get_frame()
    if vfaiframe is None:
        time.sleep(0.001)
        continue

# With event-based approach:
while not self.__stop_event.is_set():
    if self.__config.debug:
        if cv2.waitKey(1) == ord("q"):
            pass
    
    vfaiframe = self.__source.get_frame()
    if vfaiframe is None:
        self.__frame_queue.wait_for_frame(timeout=0.1)
        continue
```

---

## Implementation Priority & Effort Estimate

| Phase | Priority | Effort | Impact | Dependencies |
|-------|----------|--------|--------|--------------|
| Phase 1 | HIGH | Medium | High (fixes major detection loss) | None |
| Phase 2 | HIGH | Low | Medium (improves flexibility) | None |
| Phase 3 | MEDIUM | Low | Medium (improves adaptability) | None |
| Phase 4 | MEDIUM | Low | Low (optimization) | None |
| Phase 5 | MEDIUM | Medium | Medium (improves reliability) | None |
| Phase 6 | LOW | Low | Low (CPU optimization) | None |

---

## Recommended Rollout

1. **Start with Phase 1 & 2** (fixes high-priority issues, low risk)
2. **Add Phase 3** (improves configurability)
3. **Implement Phase 4 & 5** (reliability & optimization)
4. **Phase 6 only if CPU profiling shows polling overhead is significant**

---

## Testing Strategy

After each phase, validate:
- Multiple objects in single frame are tracked separately
- Metrics show all detections (not just max confidence)
- Queue depth remains bounded
- No stale frames processed
- Performance metrics improve or remain stable
