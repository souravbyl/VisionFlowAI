import cv2


def CV_Show(name, frame, max_w=640, max_h=360):
    cv2.namedWindow(name, cv2.WINDOW_NORMAL)
    h, w = frame.shape[:2]

    # compute scale (only shrink, never enlarge)
    scale = min(max_w / w, max_h / h, 1.0)

    if scale < 1.0:
        new_w = int(w * scale)
        new_h = int(h * scale)
        frame = cv2.resize(frame, (new_w, new_h))

    cv2.imshow(name, frame)
