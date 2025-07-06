#!/usr/bin/env python3
"""
Simple OCR test script to debug image processing
"""

import os
import pytesseract
from PIL import Image

def test_ocr_on_image(image_path):
    """Test OCR on a single image with different settings"""
    print(f"🔍 Testing OCR on: {os.path.basename(image_path)}")
    print("=" * 60)
    
    try:
        # Load image
        image = Image.open(image_path)
        print(f"📐 Image size: {image.size}")
        
        # Convert to grayscale
        image = image.convert('L')
        
        # Test different OCR configurations
        configs = [
            ('Default PSM 6', '--psm 6'),
            ('PSM 3 (Auto)', '--psm 3'),
            ('PSM 4 (Single Column)', '--psm 4'),
            ('PSM 8 (Single Word)', '--psm 8'),
            ('PSM 13 (Raw Line)', '--psm 13')
        ]
        
        best_text = ""
        best_config = ""
        
        for config_name, config in configs:
            print(f"\n🔧 Testing {config_name}:")
            try:
                text = pytesseract.image_to_string(image, config=config)
                text = text.strip()
                print(f"📝 Length: {len(text)} characters")
                print(f"📄 Text: {text[:300]}...")
                
                if len(text) > len(best_text):
                    best_text = text
                    best_config = config_name
                    
            except Exception as e:
                print(f"❌ Error with {config_name}: {e}")
        
        print(f"\n🏆 Best result ({best_config}):")
        print(f"📝 Length: {len(best_text)} characters")
        print(f"📄 Full text:")
        print("-" * 40)
        print(best_text)
        print("-" * 40)
        
        return best_text
        
    except Exception as e:
        print(f"❌ Failed to process image: {e}")
        return ""

def main():
    """Main function"""
    # Find first image
    image_dir = "./Original-Images/"
    image_files = [f for f in os.listdir(image_dir) 
                  if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if not image_files:
        print("❌ No images found")
        return
    
    # Test first few images
    for i, img_file in enumerate(image_files[:3]):
        img_path = os.path.join(image_dir, img_file)
        test_ocr_on_image(img_path)
        
        if i < 2:  # Don't add separator after last image
            print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main() 