#!/usr/bin/env python3
"""
Test script for Recipe Automation System
Tests individual components before running full automation
"""

import os
import sys
from recipe_automation_v2 import RecipeProcessor

def test_ocr():
    """Test OCR functionality"""
    print("🔍 Testing OCR...")
    processor = RecipeProcessor()
    
    # Find first image
    image_files = [f for f in os.listdir("./Original-Images/") 
                  if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if not image_files:
        print("❌ No images found for testing")
        return False
    
    test_image = os.path.join("./Original-Images/", image_files[0])
    print(f"📷 Testing with: {image_files[0]}")
    
    ocr_text = processor.extract_text_from_image(test_image)
    if ocr_text.strip():
        print("✅ OCR working")
        print(f"📝 Sample text: {ocr_text[:200]}...")
        return True
    else:
        print("❌ OCR failed")
        return False

def test_api_connection():
    """Test OpenAI API connection"""
    print("🔌 Testing API connection...")
    processor = RecipeProcessor()
    
    test_prompt = "Say 'Hello World' if you can read this."
    response = processor.ask_gpt(test_prompt)
    
    if response and "Hello" in response:
        print("✅ API connection working")
        return True
    else:
        print("❌ API connection failed")
        return False

def test_recipe_parsing():
    """Test recipe parsing with sample text"""
    print("📋 Testing recipe parsing...")
    processor = RecipeProcessor()
    
    sample_recipe = """
    Chocolate Chip Cookies
    
    Ingredients:
    - 2 cups flour
    - 1 cup sugar
    - 1/2 cup butter
    - 2 eggs
    - 1 tsp vanilla
    
    Instructions:
    1. Preheat oven to 350F
    2. Mix ingredients
    3. Bake for 12 minutes
    """
    
    parsed = processor.parse_recipe_structure(sample_recipe)
    
    if parsed.get('title') and parsed.get('ingredients') and parsed.get('instructions'):
        print("✅ Recipe parsing working")
        print(f"📝 Parsed title: {parsed['title']}")
        return True
    else:
        print("❌ Recipe parsing failed")
        return False

def test_content_generation():
    """Test content generation"""
    print("✍️ Testing content generation...")
    processor = RecipeProcessor()
    
    sample_recipe = {
        "title": "Chocolate Chip Cookies",
        "ingredients": ["flour", "sugar", "butter", "eggs"],
        "instructions": ["Mix ingredients", "Bake at 350F"]
    }
    
    description = processor.generate_recipe_description(sample_recipe)
    if description and len(description) > 100:
        print("✅ Content generation working")
        return True
    else:
        print("❌ Content generation failed")
        return False

def test_single_recipe():
    """Test processing a single recipe"""
    print("🧪 Testing single recipe processing...")
    processor = RecipeProcessor()
    
    # Find first image
    image_files = [f for f in os.listdir("./Original-Images/") 
                  if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if not image_files:
        print("❌ No images found for testing")
        return False
    
    test_image = os.path.join("./Original-Images/", image_files[0])
    print(f"📷 Processing: {image_files[0]}")
    
    success = processor.process_single_recipe(test_image)
    
    if success:
        print("✅ Single recipe processing successful")
        return True
    else:
        print("❌ Single recipe processing failed")
        return False

def main():
    """Run all tests"""
    print("🧪 Recipe Automation System - Test Suite")
    print("=" * 50)
    
    tests = [
        ("OCR Functionality", test_ocr),
        ("API Connection", test_api_connection),
        ("Recipe Parsing", test_recipe_parsing),
        ("Content Generation", test_content_generation),
        ("Single Recipe Processing", test_single_recipe)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! System is ready to use.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 