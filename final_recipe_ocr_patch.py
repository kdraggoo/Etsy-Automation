
import os
import pytesseract
from PIL import Image

def log_error(message):
    print(message)

images_to_process = ['./Original-Images/IMG_0844.jpeg']

for image_path in images_to_process:
    try:
        image = Image.open(image_path).convert("RGB")
        ocr_text = pytesseract.image_to_string(image)

        if not ocr_text or not isinstance(ocr_text, str):
            log_error(f"[ERROR] OCR returned empty or invalid result for {image_path}")
            continue

        ocr_text = ocr_text.strip()
        print(f"OCR Text for {image_path}:
{ocr_text}")
    except Exception as e:
        log_error(f"[ERROR] OCR failed on {image_path}: {str(e)}")
        continue
