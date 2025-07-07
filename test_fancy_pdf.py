#!/usr/bin/env python3
"""
Test script for the new fancy recipe card PDF generation
"""

import os
import sys
from recipe_automation_v2 import RecipeProcessor

def test_fancy_pdf():
    """Test the fancy PDF generation with sample recipe data"""
    
    # Sample recipe data
    sample_recipe = {
        "title": "Vintage Chocolate Chip Cookies",
        "ingredients": [
            "2 cups all-purpose flour",
            "1 cup butter, softened",
            "1 cup brown sugar",
            "1/2 cup white sugar",
            "2 eggs",
            "1 tsp vanilla extract",
            "1 tsp baking soda",
            "1/2 tsp salt",
            "2 cups chocolate chips"
        ],
        "instructions": [
            "Preheat oven to 375°F (190°C)",
            "Cream together butter and sugars until light and fluffy",
            "Beat in eggs one at a time, then stir in vanilla",
            "In a separate bowl, whisk together flour, baking soda, and salt",
            "Gradually mix dry ingredients into wet ingredients",
            "Stir in chocolate chips",
            "Drop by rounded tablespoons onto ungreased baking sheets",
            "Bake for 9 to 11 minutes or until golden brown",
            "Let stand for 2 minutes before removing from baking sheets"
        ],
        "servings": "24 cookies",
        "prep_time": "15 minutes",
        "cook_time": "11 minutes"
    }
    
    # Sample nutrition data
    sample_nutrition = {
        "calories": "150",
        "fat": "8g",
        "carbs": "18g",
        "protein": "2g",
        "fiber": "1g",
        "sugar": "12g",
        "sodium": "120mg"
    }
    
    # Initialize processor
    processor = RecipeProcessor()
    
    # Create test output directory
    test_dir = "test_output"
    os.makedirs(test_dir, exist_ok=True)
    
    # Test regular fancy PDF
    fancy_pdf_path = os.path.join(test_dir, "test_fancy_recipe.pdf")
    processor.create_fancy_recipe_pdf(sample_recipe, sample_nutrition, fancy_pdf_path)
    
    print(f"✅ Regular fancy PDF created: {fancy_pdf_path}")
    
    # Test fancy PDF with images (if any exist)
    image_paths = []
    test_images = ["image-main.png", "image-served.png"]
    
    for img in test_images:
        if os.path.exists(img):
            image_paths.append(img)
    
    if image_paths:
        fancy_with_images_path = os.path.join(test_dir, "test_fancy_recipe_with_images.pdf")
        processor.create_fancy_recipe_pdf_with_images(sample_recipe, sample_nutrition, fancy_with_images_path, image_paths)
        print(f"✅ Fancy PDF with images created: {fancy_with_images_path}")
    else:
        print("ℹ️  No test images found - skipping image-enhanced PDF test")
    
    print("\n🎨 Fancy PDF test completed!")
    print("Check the 'test_output' directory for generated PDFs")

if __name__ == "__main__":
    test_fancy_pdf() 