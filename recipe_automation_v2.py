import os
import re
import json
import time
import shutil
import random
import string
import logging
import textwrap
import hashlib
import csv
import argparse
import sys
from datetime import datetime
import pytz
from openai import OpenAI
import pytesseract
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import requests
from io import BytesIO
import base64
from usda_nutrition import USDANutritionAnalyzer

# Load environment variables
load_dotenv()

# Configuration
API_KEY_FILE = "API_KEY.txt"
USDA_API_KEY = "o38esmeZRVmEyldklsEzns8h2DBGakvEQNTsMxvV"

# Global variables for clients (initialized when needed)
client = None
usda_analyzer = None

def initialize_clients():
    """Initialize OpenAI and USDA clients when needed"""
    global client, usda_analyzer
    
    if client is None:
        if os.path.exists(API_KEY_FILE):
            with open(API_KEY_FILE, "r") as f:
                api_key = f.read().strip()
            client = OpenAI(api_key=api_key)
        else:
            print("❌ API_KEY.txt not found.")
            exit(1)
    
    if usda_analyzer is None:
        usda_analyzer = USDANutritionAnalyzer(USDA_API_KEY)

# Constants
IMAGE_DIR = "./Original-Images/"
PRODUCTS_DIR = "./Products/"
MAX_FILENAME_LENGTH = 64
BATCH_SIZE = 5  # Process images in batches to avoid rate limits
PROCESSED_LOG_FILE = "./processed_images.json"  # Track processed images

# Logging setup
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class RecipeProcessor:
    def __init__(self, ocr_method='vision-api'):
        self.processed_count = 0
        self.failed_count = 0
        self.ocr_method = ocr_method
        self.processed_images = self.load_processed_images()
        # Initialize clients when RecipeProcessor is created
        initialize_clients()
    
    def load_processed_images(self):
        """Load list of already processed images"""
        try:
            if os.path.exists(PROCESSED_LOG_FILE):
                with open(PROCESSED_LOG_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load processed images log: {e}")
        return {}
    
    def save_processed_images(self):
        """Save list of processed images"""
        try:
            with open(PROCESSED_LOG_FILE, 'w') as f:
                json.dump(self.processed_images, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save processed images log: {e}")
    
    def mark_image_processed(self, image_path, recipe_title, success=True, images_generated=False):
        """Mark an image as processed"""
        image_name = os.path.basename(image_path)
        self.processed_images[image_name] = {
            'processed_at': datetime.now().isoformat(),
            'recipe_title': recipe_title,
            'success': success,
            'ocr_method': self.ocr_method,
            'images_generated': images_generated
        }
        self.save_processed_images()
    
    def mark_images_generated(self, image_path):
        """Mark that images have been generated for this recipe"""
        image_name = os.path.basename(image_path)
        if image_name in self.processed_images:
            self.processed_images[image_name]['images_generated'] = True
            self.save_processed_images()
            logger.info(f"📸 Marked images as generated for {image_name}")
    
    def has_images_generated(self, image_path):
        """Check if images have been generated for this recipe"""
        image_name = os.path.basename(image_path)
        if image_name in self.processed_images:
            return self.processed_images[image_name].get('images_generated', False)
        return False
    
    def is_image_processed(self, image_path):
        """Check if an image has already been processed"""
        image_name = os.path.basename(image_path)
        return image_name in self.processed_images
        
    def slugify(self, text):
        """Convert text to URL-friendly slug"""
        text = re.sub(r'[^a-zA-Z0-9\s]+', '', text.lower())
        text = re.sub(r'\s+', '-', text.strip())
        return text[:MAX_FILENAME_LENGTH]
    
    def random_hash(self):
        """Generate random hash for unique identifiers"""
        return ''.join(random.choices('0123456789abcdef', k=6))
    
    def extract_text_from_image(self, image_path):
        """Extract text from recipe image using OCR"""
        try:
            image = Image.open(image_path)
            
            # Enhanced preprocessing for better OCR
            # Convert to grayscale
            image = image.convert('L')
            
            # Resize if too small (helps with OCR accuracy)
            width, height = image.size
            if width < 800 or height < 600:
                scale_factor = max(800/width, 600/height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Try different OCR configurations for better results
            text = ""
            
            # First try with default settings
            text = pytesseract.image_to_string(image, config='--psm 6')
            
            # If text is too short or unclear, try different PSM modes
            if len(text.strip()) < 50 or not any(word in text.lower() for word in ['ingredients', 'instructions', 'directions', 'preheat', 'bake', 'mix', 'sugar', 'flour', 'eggs', 'milk']):
                # Try PSM 3 (fully automatic page segmentation)
                text2 = pytesseract.image_to_string(image, config='--psm 3')
                if len(text2.strip()) > len(text.strip()):
                    text = text2
                
                # Try PSM 4 (single column of text)
                text3 = pytesseract.image_to_string(image, config='--psm 4')
                if len(text3.strip()) > len(text.strip()):
                    text = text3
                
                # Try with different language models for handwritten text
                try:
                    text4 = pytesseract.image_to_string(image, config='--psm 6 --oem 1')
                    if len(text4.strip()) > len(text.strip()):
                        text = text4
                except:
                    pass
            
            # Clean up the text
            lines = text.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if line and len(line) > 2:  # Remove very short lines
                    # Remove lines that are mostly symbols or numbers
                    if len([c for c in line if c.isalnum()]) > len(line) * 0.3:
                        cleaned_lines.append(line)
            
            cleaned_text = '\n'.join(cleaned_lines)
            
            return cleaned_text.strip()
        except Exception as e:
            logger.error(f"OCR failed on {image_path}: {e}")
            return ""
    
    def extract_text_with_vision_api(self, image_path):
        """Extract text from recipe image using ChatGPT's vision API"""
        try:
            # Read the image file
            with open(image_path, "rb") as image_file:
                # Use ChatGPT's vision model for OCR
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Extract all the text from this recipe image. Return only the raw text content, preserving the original formatting and structure. Do not add any commentary or interpretation."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64.b64encode(image_file.read()).decode('utf-8')}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=2000
                )
                
                extracted_text = response.choices[0].message.content.strip()
                logger.info(f"Vision API extracted {len(extracted_text)} characters from {os.path.basename(image_path)}")
                return extracted_text
                
        except Exception as e:
            logger.error(f"Vision API OCR failed on {image_path}: {e}")
            return ""
    
    def ask_gpt(self, prompt, model="gpt-4", temperature=0.4):
        """Make API call to OpenAI"""
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that processes recipe information and generates marketing content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return ""
    
    def generate_image(self, prompt, output_path, size="1024x1024"):
        """Generate image using DALL-E"""
        try:
            response = client.images.generate(
                prompt=prompt,
                n=1,
                size=size
            )
            
            image_url = response.data[0].url
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(image_response.content)
            
            logger.info(f"🖼️  Image generated: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return False
    
    def parse_recipe_structure(self, ocr_text):
        """Parse OCR text into structured recipe data"""
        # If OCR text is very poor, create a generic recipe structure
        if len(ocr_text.strip()) < 30:
            return self.create_generic_recipe()
        
        prompt = f"""
        Parse this recipe text into a JSON structure. Extract:
        - title: Recipe name (be specific and descriptive)
        - ingredients: List of ingredients with quantities (each ingredient should be a complete string like "6 egg yolks", "3/4 c. dry farina (cereal)")
        - instructions: Step-by-step cooking instructions
        - servings: Number of servings (if mentioned)
        - prep_time: Preparation time (if mentioned)
        - cook_time: Cooking time (if mentioned)
        
        IMPORTANT: For ingredients, extract the COMPLETE ingredient line including quantity, unit, and ingredient name.
        Do NOT separate quantity and ingredient name. Keep them together as one string per ingredient.
        
        Handle dual-part recipes (like cake + frosting) by separating them clearly.
        Remove any personal names from the recipe.
        
        If the OCR text is unclear or too short, try to extract what you can and make reasonable assumptions.
        If you can't determine specific ingredients, use common ingredients for the type of recipe.
        
        OCR Text:
        {ocr_text}
        
        Return only valid JSON with ingredients as complete strings:
        """
        
        response = self.ask_gpt(prompt)
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                # Validate and clean the parsed data
                if not parsed.get('title') or parsed['title'] == "Untitled Recipe":
                    # Try to extract a better title from the OCR text
                    lines = ocr_text.split('\n')
                    for line in lines[:5]:  # Check first 5 lines
                        line = line.strip()
                        if line and len(line) > 3 and len(line) < 100:
                            if not any(word in line.lower() for word in ['ingredients', 'instructions', 'directions', 'preheat']):
                                parsed['title'] = line
                                break
                
                # If still no good title, create one based on ingredients
                if not parsed.get('title') or parsed['title'] == "Untitled Recipe":
                    parsed['title'] = self.generate_recipe_title(parsed.get('ingredients', []))
                
                return parsed
            else:
                # Fallback parsing
                return self.fallback_parse(ocr_text)
        except json.JSONDecodeError:
            return self.fallback_parse(ocr_text)
    
    def create_generic_recipe(self):
        """Create a generic recipe structure when OCR fails"""
        return {
            "title": "Vintage Family Recipe",
            "ingredients": [
                "2 cups all-purpose flour",
                "1 cup sugar", 
                "1/2 cup butter or margarine",
                "2 eggs",
                "1 tsp vanilla extract",
                "1 tsp baking powder",
                "1/4 tsp salt"
            ],
            "instructions": [
                "Preheat oven to 350°F (175°C)",
                "Cream together butter and sugar until light and fluffy",
                "Beat in eggs one at a time, then stir in vanilla",
                "In a separate bowl, whisk together flour, baking powder, and salt",
                "Gradually mix dry ingredients into wet ingredients",
                "Drop by rounded tablespoons onto greased baking sheet",
                "Bake for 10-12 minutes or until edges are lightly golden"
            ],
            "servings": "24 cookies",
            "prep_time": "15 minutes",
            "cook_time": "12 minutes"
        }
    
    def generate_recipe_title(self, ingredients):
        """Generate a recipe title based on ingredients"""
        if not ingredients:
            return "Vintage Family Recipe"
        
        # Look for key ingredients to determine recipe type
        ingredient_text = ' '.join(ingredients).lower()
        
        if any(word in ingredient_text for word in ['chocolate', 'cocoa']):
            if any(word in ingredient_text for word in ['chip', 'chips']):
                return "Vintage Chocolate Chip Cookies"
            else:
                return "Vintage Chocolate Cake"
        elif any(word in ingredient_text for word in ['apple', 'apples']):
            return "Vintage Apple Pie"
        elif any(word in ingredient_text for word in ['banana', 'bananas']):
            return "Vintage Banana Bread"
        elif any(word in ingredient_text for word in ['pumpkin']):
            return "Vintage Pumpkin Bread"
        elif any(word in ingredient_text for word in ['brownie', 'brownies']):
            return "Vintage Brownies"
        elif any(word in ingredient_text for word in ['cookie', 'cookies']):
            return "Vintage Sugar Cookies"
        elif any(word in ingredient_text for word in ['cake', 'cakes']):
            return "Vintage Layer Cake"
        elif any(word in ingredient_text for word in ['pie', 'pies']):
            return "Vintage Fruit Pie"
        else:
            return "Vintage Family Dessert"
    
    def fallback_parse(self, text):
        """Fallback parsing when JSON parsing fails"""
        lines = text.split('\n')
        title = "Untitled Recipe"
        ingredients = []
        instructions = []
        
        in_ingredients = False
        in_instructions = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect title (usually first non-empty line)
            if not title or title == "Untitled Recipe":
                if len(line) < 100 and not any(word in line.lower() for word in ['ingredients', 'instructions', 'directions', 'preheat']):
                    title = line
                    continue
            
            # Detect sections
            if any(word in line.lower() for word in ['ingredients', 'ingredient']):
                in_ingredients = True
                in_instructions = False
                continue
            elif any(word in line.lower() for word in ['instructions', 'directions', 'method', 'steps']):
                in_ingredients = False
                in_instructions = True
                continue
            
            # Parse ingredients
            if in_ingredients and line and not any(word in line.lower() for word in ['instructions', 'directions']):
                if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    ingredients.append(line[1:].strip())
                elif re.match(r'^\d+', line):  # Starts with number
                    ingredients.append(line)
            
            # Parse instructions
            elif in_instructions and line:
                if re.match(r'^\d+[\.\)]', line):  # Numbered step
                    instructions.append(line)
                elif instructions:  # Continuation of previous step
                    instructions[-1] += " " + line
        
        return {
            "title": title,
            "ingredients": ingredients,
            "instructions": instructions,
            "servings": "Unknown",
            "prep_time": "Unknown",
            "cook_time": "Unknown"
        }
    
    def generate_recipe_description(self, recipe_data):
        """Generate enticing Etsy description"""
        # Ensure ingredients are strings before joining
        def stringify(item):
            if isinstance(item, dict):
                # Handle ingredient dictionaries with quantity and ingredient fields
                if 'ingredient' in item and 'quantity' in item:
                    return f"{item['quantity']} {item['ingredient']}"
                elif 'ingredient' in item:
                    return item['ingredient']
                elif 'quantity' in item:
                    return item['quantity']
                else:
                    # Try to get the first value
                    return next(iter(item.values()), str(item))
            return str(item)

        ingredients = [stringify(ing) for ing in recipe_data.get('ingredients', [])]
        ingredients_text = ', '.join(ingredients[:5]) if ingredients else 'Traditional ingredients'
        
        prompt = f"""
        Create an enticing Etsy listing description for this vintage recipe. The description should:
        - Be warm and nostalgic, mentioning family traditions and vintage cookbooks
        - Describe the end result appealingly
        - Mention it's a digital download
        - Include suggested uses (gifting, printing, etc.)
        - Be 2-3 paragraphs long
        
        Recipe: {recipe_data['title']}
        Servings: {recipe_data.get('servings', 'Unknown')}
        Prep Time: {recipe_data.get('prep_time', 'Unknown')}
        Cook Time: {recipe_data.get('cook_time', 'Unknown')}
        Ingredients: {ingredients_text}
        Instructions: {len(recipe_data['instructions'])} steps
        
        Write a compelling description:
        """
        
        return self.ask_gpt(prompt)
    
    def analyze_allergies(self, ingredients):
        """Analyze ingredients for potential allergies"""
        if not ingredients:
            return {"allergens": []}
        
        # Ensure ingredients are strings
        def stringify(item):
            if isinstance(item, dict):
                # Handle ingredient dictionaries with quantity and ingredient fields
                if 'ingredient' in item and 'quantity' in item:
                    return f"{item['quantity']} {item['ingredient']}"
                elif 'ingredient' in item:
                    return item['ingredient']
                elif 'quantity' in item:
                    return item['quantity']
                else:
                    # Try to get the first value
                    return next(iter(item.values()), str(item))
            return str(item)

        ingredients_list = [stringify(ing) for ing in ingredients]
        ingredients_text = ', '.join(ingredients_list)
            
        prompt = f"""
        Analyze these ingredients for potential allergies. Return a JSON list of allergens:
        {ingredients_text}
        
        Common allergens: gluten, dairy, eggs, nuts, soy, shellfish, fish, peanuts
        Consider that "cake mix" contains gluten, "milk" contains dairy, etc.
        
        Return JSON: {{"allergens": ["allergen1", "allergen2"]}}
        """
        
        response = self.ask_gpt(prompt)
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"allergens": []}
        except:
            return {"allergens": []}
    
    def analyze_diet_compatibility(self, ingredients, instructions):
        """Analyze recipe for diet compatibility"""
        if not ingredients:
            return {"diets": [], "not_compatible": []}
        
        # Ensure ingredients and instructions are strings
        def stringify(item):
            if isinstance(item, dict):
                # Handle ingredient dictionaries with quantity and ingredient fields
                if 'ingredient' in item and 'quantity' in item:
                    return f"{item['quantity']} {item['ingredient']}"
                elif 'ingredient' in item:
                    return item['ingredient']
                elif 'quantity' in item:
                    return item['quantity']
                else:
                    # Try to get the first value
                    return next(iter(item.values()), str(item))
            return str(item)

        ingredients_list = [stringify(ing) for ing in ingredients]
        instructions_list = [stringify(inst) for inst in instructions]
        ingredients_text = ', '.join(ingredients_list)
        instructions_text = ' '.join(instructions_list)
            
        prompt = f"""
        Analyze this recipe for diet compatibility. Return a JSON object:
        
        Ingredients: {ingredients_text}
        Instructions: {instructions_text}
        
        Check for: vegan, vegetarian, gluten-free, dairy-free, paleo, keto, low-carb, nut-free
        
        Return JSON: {{"diets": ["diet1", "diet2"], "not_compatible": ["diet3"]}}
        """
        
        response = self.ask_gpt(prompt)
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"diets": [], "not_compatible": []}
        except:
            return {"diets": [], "not_compatible": []}
    
    def generate_nutrition_label(self, ingredients, instructions):
        """Generate nutrition information using USDA API"""
        if not ingredients:
            return {"calories": "Unknown", "fat": "Unknown", "carbs": "Unknown", "protein": "Unknown"}
        
        # Ensure ingredients are strings
        def stringify(item):
            if isinstance(item, dict):
                # Handle ingredient dictionaries with quantity and ingredient fields
                if 'ingredient' in item and 'quantity' in item:
                    return f"{item['quantity']} {item['ingredient']}"
                elif 'ingredient' in item:
                    return item['ingredient']
                elif 'quantity' in item:
                    return item['quantity']
                else:
                    # Try to get the first value
                    return next(iter(item.values()), str(item))
            return str(item)

        ingredients_list = [stringify(ing) for ing in ingredients]
        
        try:
            # Use USDA API for accurate nutrition analysis
            nutrition_data = usda_analyzer.analyze_recipe_nutrition(ingredients_list)
            
            # Format the results
            per_serving = nutrition_data['per_serving']
            
            return {
                "calories": f"{per_serving['calories']:.0f}",
                "fat": f"{per_serving['fat']:.1f}g",
                "carbs": f"{per_serving['carbs']:.1f}g",
                "protein": f"{per_serving['protein']:.1f}g",
                "fiber": f"{per_serving['fiber']:.1f}g",
                "sugar": f"{per_serving['sugar']:.1f}g",
                "sodium": f"{per_serving['sodium']:.0f}mg"
            }
            
        except Exception as e:
            logger.error(f"USDA nutrition analysis failed: {e}")
            
            # Fallback to LLM estimation
            ingredients_text = ', '.join(ingredients_list)
            instructions_list = [stringify(inst) for inst in instructions]
            instructions_text = ' '.join(instructions_list)
                
            prompt = f"""
            Estimate nutrition information for this recipe. Consider typical serving sizes.
            
            Ingredients: {ingredients_text}
            Instructions: {instructions_text}
            
            Return JSON with estimated values per serving:
            {{"calories": 300, "fat": "12g", "carbs": "45g", "protein": "5g", "fiber": "2g", "sugar": "25g", "sodium": "200mg"}}
            """
            
            response = self.ask_gpt(prompt)
            try:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                return {"calories": "Unknown", "fat": "Unknown", "carbs": "Unknown", "protein": "Unknown"}
            except:
                return {"calories": "Unknown", "fat": "Unknown", "carbs": "Unknown", "protein": "Unknown"}
    

    
    def generate_social_content(self, recipe_data, description):
        """Generate social media content"""
        # Instagram post
        instagram_prompt = f"""
        Create an Instagram post for this recipe. Include:
        - Engaging opening with emojis
        - Brief description
        - Call to action
        - Relevant hashtags
        
        Recipe: {recipe_data['title']}
        Description: {description[:200]}...
        
        Format with emojis and hashtags.
        """
        
        instagram_content = self.ask_gpt(instagram_prompt)
        
        # Pinterest description
        pinterest_prompt = f"""
        Create a Pinterest description for this recipe. Keep it under 500 characters.
        
        Recipe: {recipe_data['title']}
        Description: {description[:100]}...
        """
        
        pinterest_content = self.ask_gpt(pinterest_prompt)
        
        return {
            "instagram": instagram_content,
            "pinterest": pinterest_content
        }
    
    def estimate_recipe_details(self, recipe_data):
        """Estimate servings, prep time, and cook time using AI"""
        # Ensure ingredients and instructions are strings
        def stringify(item):
            if isinstance(item, dict):
                if 'ingredient' in item and 'quantity' in item:
                    return f"{item['quantity']} {item['ingredient']}"
                elif 'ingredient' in item:
                    return item['ingredient']
                elif 'quantity' in item:
                    return item['quantity']
                else:
                    return next(iter(item.values()), str(item))
            return str(item)

        ingredients = [stringify(ing) for ing in recipe_data.get('ingredients', [])]
        instructions = [stringify(inst) for inst in recipe_data.get('instructions', [])]
        
        prompt = f"""
        Analyze this recipe and estimate the missing details. Return only a JSON object with these fields:
        - servings: Number of servings (e.g., "6 servings", "24 cookies", "1 loaf")
        - prep_time: Preparation time (e.g., "15 minutes", "30 minutes")
        - cook_time: Cooking/baking time (e.g., "45 minutes", "1 hour", "12-15 minutes")
        
        Recipe: {recipe_data['title']}
        Ingredients: {', '.join(ingredients)}
        Instructions: {' '.join(instructions)}
        
        Consider:
        - Recipe type (cookies, cake, bread, etc.)
        - Ingredient quantities
        - Number of steps
        - Typical cooking methods mentioned
        
        IMPORTANT: Always use standardized formats:
        - servings: Use "X servings" for general recipes, "X cookies/bars" for cookies, "1 loaf/cake" for breads/cakes
        - prep_time: Always include "minutes" or "hours" (e.g., "20 minutes", "1 hour")
        - cook_time: Always include "minutes" or "hours" (e.g., "45 minutes", "1 hour")
        
        Return only valid JSON: {{"servings": "X servings", "prep_time": "X minutes", "cook_time": "X minutes"}}
        """
        
        response = self.ask_gpt(prompt)
        logger.info(f"🤖 AI estimation response: {response[:200]}...")
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                estimated = json.loads(json_match.group())
                logger.info(f"✅ AI estimation successful: {estimated}")
                return estimated
            else:
                logger.warning("❌ No JSON found in AI estimation response")
        except Exception as e:
            logger.error(f"❌ JSON parsing failed for AI estimation: {e}")
        
        # Fallback estimates based on recipe type
        logger.info("🔄 Using fallback estimates based on recipe type")
        
        # Analyze recipe title and ingredients to determine type
        title_lower = recipe_data['title'].lower()
        ingredients_text = ' '.join(ingredients).lower()
        
        # Determine recipe type for better fallback estimates
        if any(word in title_lower for word in ['cookie', 'cookies']):
            return {
                "servings": "24 cookies",
                "prep_time": "15 minutes", 
                "cook_time": "12 minutes"
            }
        elif any(word in title_lower for word in ['cake', 'bread']):
            return {
                "servings": "8 servings",
                "prep_time": "20 minutes", 
                "cook_time": "45 minutes"
            }
        elif any(word in title_lower for word in ['pie', 'tart']):
            return {
                "servings": "8 servings",
                "prep_time": "30 minutes", 
                "cook_time": "1 hour"
            }
        elif any(word in title_lower for word in ['brownie', 'brownies']):
            return {
                "servings": "16 brownies",
                "prep_time": "15 minutes", 
                "cook_time": "25 minutes"
            }
        elif any(word in title_lower for word in ['bar', 'bars']):
            return {
                "servings": "16 bars",
                "prep_time": "15 minutes", 
                "cook_time": "25 minutes"
            }
        else:
            # Default fallback
            return {
                "servings": "8 servings",
                "prep_time": "20 minutes", 
                "cook_time": "30 minutes"
            }

    def generate_tags(self, recipe_data, description):
        """Generate Etsy tags"""
        prompt = f"""
        Generate 13 relevant Etsy tags for this recipe listing. Include:
        - Recipe type
        - Vintage/retro themes
        - Digital download
        - Cooking/baking terms
        
        Recipe: {recipe_data['title']}
        Description: {description[:200]}...
        
        Return as comma-separated list.
        """
        
        response = self.ask_gpt(prompt)
        tags = [tag.strip() for tag in response.split(',')]
        return tags[:13]  # Etsy allows max 13 tags
    
    def create_recipe_pdf(self, recipe_data, nutrition, output_path):
        """Create beautiful recipe PDF"""
        try:
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Ensure ingredients and instructions are strings
            def stringify(item):
                if isinstance(item, dict):
                    # Handle ingredient dictionaries with quantity and ingredient fields
                    if 'ingredient' in item and 'quantity' in item:
                        return f"{item['quantity']} {item['ingredient']}"
                    elif 'ingredient' in item:
                        return item['ingredient']
                    elif 'quantity' in item:
                        return item['quantity']
                    else:
                        # Try to get the first value
                        return next(iter(item.values()), str(item))
                return str(item)

            ingredients = [stringify(ing) for ing in recipe_data.get('ingredients', [])]
            instructions = [stringify(inst) for inst in recipe_data.get('instructions', [])]
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=1  # Center
            )
            story.append(Paragraph(recipe_data['title'], title_style))
            story.append(Spacer(1, 20))
            
            # Recipe details
            details_text = f"Servings: {recipe_data.get('servings', 'Unknown')} | Prep Time: {recipe_data.get('prep_time', 'Unknown')} | Cook Time: {recipe_data.get('cook_time', 'Unknown')}"
            story.append(Paragraph(details_text, styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Ingredients
            story.append(Paragraph("Ingredients", styles['Heading2']))
            for ingredient in ingredients:
                story.append(Paragraph(f"• {ingredient}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Instructions
            story.append(Paragraph("Instructions", styles['Heading2']))
            for i, instruction in enumerate(instructions, 1):
                story.append(Paragraph(f"{i}. {instruction}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Nutrition info
            if nutrition.get('calories') != "Unknown":
                story.append(Paragraph("Nutrition Information (per serving)", styles['Heading2']))
                nutrition_text = f"Calories: {nutrition.get('calories', 'Unknown')} | Fat: {nutrition.get('fat', 'Unknown')} | Carbs: {nutrition.get('carbs', 'Unknown')} | Protein: {nutrition.get('protein', 'Unknown')}"
                if nutrition.get('fiber') != "Unknown":
                    nutrition_text += f" | Fiber: {nutrition.get('fiber', 'Unknown')}"
                if nutrition.get('sugar') != "Unknown":
                    nutrition_text += f" | Sugar: {nutrition.get('sugar', 'Unknown')}"
                if nutrition.get('sodium') != "Unknown":
                    nutrition_text += f" | Sodium: {nutrition.get('sodium', 'Unknown')}"
                story.append(Paragraph(nutrition_text, styles['Normal']))
                story.append(Spacer(1, 20))
            

            
            doc.build(story)
            logger.info(f"📄 PDF created: {output_path}")
            
        except Exception as e:
            logger.error(f"PDF creation error: {e}")
    
    def create_product_folder(self, recipe_data, image_path):
        """Create product folder and organize files"""
        slug = self.slugify(recipe_data['title'])
        unique_id = f"{slug}-{self.random_hash()}"
        product_dir = os.path.join(PRODUCTS_DIR, unique_id)
        os.makedirs(product_dir, exist_ok=True)
        
        # Move original image
        dest_image_path = os.path.join(product_dir, f"original-{os.path.basename(image_path)}")
        shutil.copy2(image_path, dest_image_path)
        
        return product_dir, slug, unique_id
    
    def generate_product_images(self, recipe_data, product_dir, slug, image_path=None):
        """Generate finished product and serving images"""
        try:
            # Generate finished product image
            finished_prompt = f"""
            Professional food photography of {recipe_data['title']}, beautifully presented on a rustic wooden table with natural lighting, 
            vintage aesthetic, warm colors, appetizing appearance, high quality, no text or watermarks
            """
            
            finished_image_path = os.path.join(product_dir, "image-main.png")
            success1 = self.generate_image(finished_prompt, finished_image_path)
            
            # Generate single serving image
            serving_prompt = f"""
            Close-up photography of a single serving of {recipe_data['title']}, elegantly plated on a vintage dish, 
            soft natural lighting, appetizing presentation, high quality, no text or watermarks
            """
            
            serving_image_path = os.path.join(product_dir, "image-served.png")
            success2 = self.generate_image(serving_prompt, serving_image_path)
            
            if success1 and success2:
                logger.info(f"🖼️  Product images generated for {recipe_data['title']}")
                # Mark images as generated in tracking file
                if image_path:
                    self.mark_images_generated(image_path)
                return True
            else:
                logger.error(f"❌ Some images failed to generate for {recipe_data['title']}")
                return False
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return False
    
    def save_content_files(self, product_dir, recipe_data, description, social_content, tags, nutrition, allergies, diet_info):
        """Save all content files to product directory"""
        
        # Ensure ingredients and instructions are lists of strings
        def stringify(item):
            if isinstance(item, dict):
                # Handle ingredient dictionaries with quantity and ingredient fields
                if 'ingredient' in item and 'quantity' in item:
                    return f"{item['quantity']} {item['ingredient']}"
                elif 'ingredient' in item:
                    return item['ingredient']
                elif 'quantity' in item:
                    return item['quantity']
                else:
                    # Try to get the first value
                    return next(iter(item.values()), str(item))
            return str(item)

        ingredients = [stringify(ing) for ing in recipe_data.get('ingredients', [])]
        if not ingredients:
            ingredients = ["Traditional ingredients"]
            
        instructions = [stringify(inst) for inst in recipe_data.get('instructions', [])]
        if not instructions:
            instructions = ["Follow traditional baking methods"]
        
        # Recipe text file
        recipe_text = f"""Title: {recipe_data['title']}

Servings: {recipe_data.get('servings', 'Unknown')}
Prep Time: {recipe_data.get('prep_time', 'Unknown')}
Cook Time: {recipe_data.get('cook_time', 'Unknown')}

Ingredients:
{chr(10).join([f"- {ingredient}" for ingredient in ingredients])}

Instructions:
{chr(10).join([f"{i+1}. {instruction}" for i, instruction in enumerate(instructions)])}

Nutrition Information (per serving):
Calories: {nutrition.get('calories', 'Unknown')}
Fat: {nutrition.get('fat', 'Unknown')}
Carbohydrates: {nutrition.get('carbs', 'Unknown')}
Protein: {nutrition.get('protein', 'Unknown')}
Fiber: {nutrition.get('fiber', 'Unknown')}
Sugar: {nutrition.get('sugar', 'Unknown')}
Sodium: {nutrition.get('sodium', 'Unknown')}

Allergies: {', '.join(allergies.get('allergens', []))}
Diet Compatibility: {', '.join(diet_info.get('diets', []))}
"""
        
        with open(os.path.join(product_dir, "Recipe.txt"), "w") as f:
            f.write(recipe_text)
        
        # Listing description
        listing_text = f"""Title:
{recipe_data['title']} | Digital Recipe Download

Servings: {recipe_data.get('servings', 'Unknown')}
Prep Time: {recipe_data.get('prep_time', 'Unknown')}
Cook Time: {recipe_data.get('cook_time', 'Unknown')}

Tags:
{', '.join(tags)}

Description:
{description}

Suggested Price: $4.99
"""
        
        with open(os.path.join(product_dir, "Listing.txt"), "w") as f:
            f.write(listing_text)
        
        # Social media content
        with open(os.path.join(product_dir, "Instagram.txt"), "w") as f:
            f.write(social_content['instagram'])
        
        with open(os.path.join(product_dir, "Pinterest.txt"), "w") as f:
            f.write(social_content['pinterest'])
        
        # CSV for Etsy import
        csv_data = {
            'Title': f"{recipe_data['title']} | Digital Recipe Download",
            'Description': description,
            'Price': '4.99',
            'Currency Code': 'USD',
            'Quantity': '100',
            'Tags': ', '.join(tags)
        }
        
        with open(os.path.join(product_dir, "listing.csv"), "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=csv_data.keys())
            writer.writeheader()
            writer.writerow(csv_data)
        
        logger.info(f"📁 Content files saved to {product_dir}")
    
    def process_single_recipe(self, image_path, generate_images=False, force_reprocess=False):
        """Process a single recipe image"""
        try:
            # Check if image has already been processed
            if self.is_image_processed(image_path) and not force_reprocess:
                logger.info(f"⏭️  Skipping already processed: {os.path.basename(image_path)}")
                return True
            
            logger.info(f"🔄 Processing: {os.path.basename(image_path)}")
            
            # Extract text via OCR using selected method
            if self.ocr_method == 'vision-api':
                ocr_text = self.extract_text_with_vision_api(image_path)
            else:
                ocr_text = self.extract_text_from_image(image_path)
                
            if not ocr_text.strip():
                logger.warning(f"No OCR text found in {os.path.basename(image_path)}")
                self.mark_image_processed(image_path, "Failed - No OCR text", success=False)
                return False
            
            # Debug: Log OCR text for troubleshooting
            logger.info(f"📝 OCR Text extracted ({len(ocr_text)} chars): {ocr_text[:200]}...")
            
            # Parse recipe structure
            recipe_data = self.parse_recipe_structure(ocr_text)
            if not recipe_data.get('title') or recipe_data['title'] == "Untitled Recipe":
                logger.warning(f"Could not extract recipe title from {os.path.basename(image_path)}")
                self.mark_image_processed(image_path, "Failed - No recipe title", success=False)
                return False
            
            # Debug: Log parsed recipe data
            logger.info(f"📋 Parsed recipe: {recipe_data['title']} - {len(recipe_data.get('ingredients', []))} ingredients, {len(recipe_data.get('instructions', []))} instructions")
            
            # Create product folder
            product_dir, slug, unique_id = self.create_product_folder(recipe_data, image_path)
            
            # Estimate missing recipe details
            estimated_details = self.estimate_recipe_details(recipe_data)
            
            # Merge estimated details with original data
            # Use estimated values if original values are missing, None, or "Unknown"
            def use_estimated_if_needed(original, estimated, field_name):
                """Check if original value is meaningful or should be replaced with estimated value"""
                
                # Helper function to check if a value contains meaningful content
                def is_meaningful(value):
                    if not value:
                        return False
                    
                    # Convert to string and normalize
                    value_str = str(value).strip().lower()
                    
                    # Check for common "unknown" or empty patterns
                    unknown_patterns = [
                        'unknown', 'not mentioned', 'n/a', 'none', 'unspecified',
                        'not specified', 'not given', 'missing', 'blank', '',
                        'null', 'undefined', 'tbd', 'to be determined'
                    ]
                    
                    if value_str in unknown_patterns:
                        return False
                    
                    # Check if it contains meaningful content (numbers, units, descriptive words)
                    # For servings: should contain numbers or descriptive words like "servings", "cookies", "loaf"
                    # For times: should contain numbers and time units
                    if field_name == 'servings':
                        # Check for numbers or descriptive serving terms
                        has_numbers = any(char.isdigit() for char in value_str)
                        has_serving_terms = any(term in value_str for term in ['serving', 'cookie', 'slice', 'piece', 'loaf', 'cake', 'bar', 'cup', 'portion'])
                        return has_numbers or has_serving_terms
                    
                    elif field_name in ['prep_time', 'cook_time']:
                        # Check for numbers and time units
                        has_numbers = any(char.isdigit() for char in value_str)
                        has_time_units = any(unit in value_str for unit in ['minute', 'hour', 'second', 'min', 'hr', 'sec'])
                        return has_numbers and has_time_units
                    
                    # Default: if it's not obviously "unknown", consider it meaningful
                    return True
                
                if is_meaningful(original):
                    logger.info(f"📊 Using original {field_name}: {original}")
                    return original
                else:
                    logger.info(f"📊 Using AI-estimated {field_name}: {estimated}")
                    return estimated
            
            recipe_data['servings'] = use_estimated_if_needed(
                recipe_data.get('servings'), 
                estimated_details.get('servings', 'Unknown'), 
                'servings'
            )
            recipe_data['prep_time'] = use_estimated_if_needed(
                recipe_data.get('prep_time'), 
                estimated_details.get('prep_time', 'Unknown'), 
                'prep_time'
            )
            recipe_data['cook_time'] = use_estimated_if_needed(
                recipe_data.get('cook_time'), 
                estimated_details.get('cook_time', 'Unknown'), 
                'cook_time'
            )
            
            # Generate content
            description = self.generate_recipe_description(recipe_data)
            allergies = self.analyze_allergies(recipe_data.get('ingredients', []))
            diet_info = self.analyze_diet_compatibility(recipe_data.get('ingredients', []), recipe_data.get('instructions', []))
            nutrition = self.generate_nutrition_label(recipe_data.get('ingredients', []), recipe_data.get('instructions', []))
            social_content = self.generate_social_content(recipe_data, description)
            tags = self.generate_tags(recipe_data, description)
            
            # Save content files
            self.save_content_files(product_dir, recipe_data, description, social_content, tags, nutrition, allergies, diet_info)
            
            # Create PDFs
            pdf_path = os.path.join(product_dir, f"{slug}_Recipe-Card.pdf")
            self.create_recipe_pdf(recipe_data, nutrition, pdf_path)
            
            fancy_pdf_path = os.path.join(product_dir, f"{slug}_Recipe-Card-fancy.pdf")
            self.create_recipe_pdf(recipe_data, nutrition, fancy_pdf_path)
            
            # Generate product images (only if requested)
            if generate_images:
                self.generate_product_images(recipe_data, product_dir, slug, image_path)
            else:
                logger.info(f"🖼️  Skipping image generation (use --generate-images to enable)")
            
            logger.info(f"✅ Successfully processed: {recipe_data['title']}")
            self.mark_image_processed(image_path, recipe_data['title'], success=True)
            self.processed_count += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to process {os.path.basename(image_path)}: {e}")
            self.mark_image_processed(image_path, f"Failed - {str(e)}", success=False)
            self.failed_count += 1
            return False
    
    def process_all_images(self, start_index=0, batch_size=None, limit=None, generate_images=False, force_reprocess=False):
        """Process all recipe images"""
        if batch_size is None:
            batch_size = BATCH_SIZE
        
        image_files = sorted([f for f in os.listdir(IMAGE_DIR) 
                            if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
        
        total_images = len(image_files)
        logger.info(f"📷 Found {total_images} images to process")
        
        # Apply limit if specified
        if limit:
            total_images = min(total_images, start_index + limit)
            logger.info(f"📊 Limiting to {limit} images (starting from index {start_index})")
        
        # Process in batches
        for i in range(start_index, total_images, batch_size):
            batch = image_files[i:i + batch_size]
            logger.info(f"🔄 Processing batch {i//batch_size + 1}: images {i+1}-{min(i+batch_size, total_images)}")
            
            for img_file in batch:
                img_path = os.path.join(IMAGE_DIR, img_file)
                self.process_single_recipe(img_path, generate_images, force_reprocess)
                time.sleep(2)  # Rate limiting
            
            logger.info(f"⏸️  Batch complete. Processed: {self.processed_count}, Failed: {self.failed_count}")
            
            if i + batch_size < total_images:
                logger.info("⏳ Waiting 30 seconds before next batch...")
                time.sleep(30)
        
        logger.info(f"🎉 Processing complete! Processed: {self.processed_count}, Failed: {self.failed_count}")
    
    def generate_images_for_processed_recipes(self, batch_size=None, limit=None):
        """Generate images only for recipes that have been processed but don't have images yet"""
        if batch_size is None:
            batch_size = BATCH_SIZE
        
        image_files = sorted([f for f in os.listdir(IMAGE_DIR) 
                            if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
        
        # Filter for images that have been processed but don't have images generated
        images_needing_images = []
        for img_file in image_files:
            img_path = os.path.join(IMAGE_DIR, img_file)
            if self.is_image_processed(img_path) and not self.has_images_generated(img_path):
                images_needing_images.append(img_file)
        
        total_images = len(images_needing_images)
        logger.info(f"📷 Found {total_images} processed recipes that need images generated")
        
        if total_images == 0:
            logger.info("✅ All processed recipes already have images!")
            return
        
        # Apply limit if specified
        if limit:
            total_images = min(total_images, limit)
            logger.info(f"📊 Limiting to {limit} images")
        
        # Process in batches
        for i in range(0, total_images, batch_size):
            batch = images_needing_images[i:i + batch_size]
            logger.info(f"🖼️  Generating images for batch {i//batch_size + 1}: images {i+1}-{min(i+batch_size, total_images)}")
            
            for img_file in batch:
                img_path = os.path.join(IMAGE_DIR, img_file)
                self.generate_images_for_single_recipe(img_path)
                time.sleep(2)  # Rate limiting
            
            logger.info(f"⏸️  Batch complete. Images generated: {self.processed_count}, Failed: {self.failed_count}")
            
            if i + batch_size < total_images:
                logger.info("⏳ Waiting 30 seconds before next batch...")
                time.sleep(30)
        
        logger.info(f"🎉 Image generation complete! Generated: {self.processed_count}, Failed: {self.failed_count}")
    
    def generate_images_for_single_recipe(self, image_path):
        """Generate images for a single recipe that has already been processed"""
        try:
            image_name = os.path.basename(image_path)
            logger.info(f"🖼️  Generating images for: {image_name}")
            
            # Find the product directory for this recipe
            product_dir = None
            for dir_name in os.listdir(PRODUCTS_DIR):
                dir_path = os.path.join(PRODUCTS_DIR, dir_name)
                if os.path.isdir(dir_path):
                    # Check if this directory contains the original image
                    original_image = f"original-{image_name}"
                    if os.path.exists(os.path.join(dir_path, original_image)):
                        product_dir = dir_path
                        break
            
            if not product_dir:
                logger.error(f"❌ Could not find product directory for {image_name}")
                self.failed_count += 1
                return False
            
            # Load recipe data from the saved files
            recipe_file = os.path.join(product_dir, "Recipe.txt")
            if not os.path.exists(recipe_file):
                logger.error(f"❌ Recipe file not found for {image_name}")
                self.failed_count += 1
                return False
            
            # Parse recipe data from the saved file
            with open(recipe_file, 'r') as f:
                recipe_text = f.read()
            
            # Extract recipe title from the file
            lines = recipe_text.split('\n')
            title = "Vintage Recipe"
            for line in lines:
                if line.startswith('Title:'):
                    title = line.replace('Title:', '').strip()
                    break
            
            # Create recipe data structure
            recipe_data = {
                'title': title,
                'ingredients': [],
                'instructions': [],
                'servings': 'Unknown',
                'prep_time': 'Unknown',
                'cook_time': 'Unknown'
            }
            
            # Extract other details from the file
            in_ingredients = False
            in_instructions = False
            for line in lines:
                line = line.strip()
                if line.startswith('Servings:'):
                    recipe_data['servings'] = line.replace('Servings:', '').strip()
                elif line.startswith('Prep Time:'):
                    recipe_data['prep_time'] = line.replace('Prep Time:', '').strip()
                elif line.startswith('Cook Time:'):
                    recipe_data['cook_time'] = line.replace('Cook Time:', '').strip()
                elif line == 'Ingredients:':
                    in_ingredients = True
                    in_instructions = False
                elif line == 'Instructions:':
                    in_ingredients = False
                    in_instructions = True
                elif in_ingredients and line.startswith('- '):
                    recipe_data['ingredients'].append(line[2:])
                elif in_instructions and line and line[0].isdigit() and '. ' in line:
                    recipe_data['instructions'].append(line.split('. ', 1)[1])
            
            # Generate slug for the recipe
            slug = self.slugify(recipe_data['title'])
            
            # Generate images
            success = self.generate_product_images(recipe_data, product_dir, slug, image_path)
            
            if success:
                logger.info(f"✅ Images generated for {recipe_data['title']}")
                self.processed_count += 1
                return True
            else:
                logger.error(f"❌ Failed to generate images for {recipe_data['title']}")
                self.failed_count += 1
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to generate images for {os.path.basename(image_path)}: {e}")
            self.failed_count += 1
            return False
    
    def create_master_csv(self):
        """Create master CSV file for all processed recipes"""
        csv_data = []
        
        for product_dir in os.listdir(PRODUCTS_DIR):
            product_path = os.path.join(PRODUCTS_DIR, product_dir)
            if os.path.isdir(product_path):
                csv_file = os.path.join(product_path, "listing.csv")
                if os.path.exists(csv_file):
                    with open(csv_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            row['Product Folder'] = product_dir
                            csv_data.append(row)
        
        if csv_data:
            master_csv_path = os.path.join(PRODUCTS_DIR, "master_listing.csv")
            with open(master_csv_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['Product Folder'] + list(csv_data[0].keys() - {'Product Folder'})
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in csv_data:
                    writer.writerow(row)
            
            logger.info(f"📊 Master CSV created: {master_csv_path}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Recipe Automation System v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python recipe_automation_v2.py --single                    # Process first image
  python recipe_automation_v2.py --single --image 2         # Process second image
  python recipe_automation_v2.py --single --image IMG_0844.jpeg  # Process specific image
  python recipe_automation_v2.py --all                      # Process all images
  python recipe_automation_v2.py --all --generate-images    # Process all images with AI image generation
  python recipe_automation_v2.py --all --force-reprocess    # Reprocess already processed images
  python recipe_automation_v2.py --images-only              # Generate images for processed recipes only
  python recipe_automation_v2.py --csv-only                 # Create master CSV only
        """
    )
    
    # Action group
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        '--single', 
        action='store_true',
        help='Process a single recipe image'
    )
    action_group.add_argument(
        '--all', 
        action='store_true',
        help='Process all recipe images (production mode)'
    )
    action_group.add_argument(
        '--csv-only', 
        action='store_true',
        help='Create master CSV file only'
    )
    action_group.add_argument(
        '--images-only', 
        action='store_true',
        help='Generate images only for recipes that have been processed but don\'t have images yet'
    )
    
    # Options for single processing
    parser.add_argument(
        '--image', 
        type=str,
        help='Image filename or number (1-based) for single processing'
    )
    
    # Batch processing options
    parser.add_argument(
        '--batch-size', 
        type=int,
        default=5,
        help='Number of images to process in each batch (default: 5)'
    )
    parser.add_argument(
        '--start-index', 
        type=int,
        default=0,
        help='Starting index for batch processing (default: 0)'
    )
    parser.add_argument(
        '--limit', 
        type=int,
        help='Limit total number of images to process (default: no limit)'
    )
    
    # Verbose logging
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    # OCR method selection
    parser.add_argument(
        '--ocr-method',
        choices=['tesseract', 'vision-api'],
        default='vision-api',
        help='OCR method to use: tesseract (free) or vision-api (better accuracy)'
    )
    
    # Image generation control
    parser.add_argument(
        '--generate-images',
        action='store_true',
        help='Generate AI images for recipes (disabled by default to save API costs)'
    )
    
    # Processing control
    parser.add_argument(
        '--force-reprocess',
        action='store_true',
        help='Force reprocessing of already processed images'
    )
    
    return parser.parse_args()

def main():
    """Main execution function"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Validate argument combinations
    if args.images_only and args.force_reprocess:
        print("⚠️  Warning: --force-reprocess is ignored when using --images-only mode")
        print("   Images-only mode only generates images for already processed recipes")
    
    # Set up logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Log command execution
    mst = pytz.timezone('US/Mountain')
    timestamp = datetime.now(mst).strftime("%Y-%m-%d %H:%M:%S %Z")
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Log the command that was executed
    command_log_file = f"logs/command_execution_{datetime.now(mst).strftime('%Y%m%d_%H%M%S')}.log"
    with open(command_log_file, 'w') as f:
        f.write(f"Command Execution Log\n")
        f.write(f"=" * 50 + "\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Command: python recipe_automation_v2.py {' '.join(sys.argv[1:])}\n")
        f.write(f"Arguments: {vars(args)}\n")
        f.write(f"=" * 50 + "\n\n")
    
    processor = RecipeProcessor(ocr_method=args.ocr_method)
    
    print("🍳 Recipe Automation System v2.0")
    print("=" * 50)
    
    # Check if images exist
    if not os.path.exists(IMAGE_DIR):
        print(f"❌ Image directory not found: {IMAGE_DIR}")
        return
    
    image_files = [f for f in os.listdir(IMAGE_DIR) 
                  if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if not image_files:
        print(f"❌ No images found in {IMAGE_DIR}")
        return
    
    print(f"📷 Found {len(image_files)} recipe images")
    
    # Handle different modes
    if args.single:
        # Process single image
        if len(image_files) == 1:
            img_path = os.path.join(IMAGE_DIR, image_files[0])
            print(f"\nProcessing: {image_files[0]}")
        elif args.image:
            # User specified an image
            try:
                # Try to parse as number first
                img_index = int(args.image) - 1
                if 0 <= img_index < len(image_files):
                    img_path = os.path.join(IMAGE_DIR, image_files[img_index])
                    print(f"Processing: {image_files[img_index]}")
                else:
                    print(f"❌ Invalid image number: {args.image}")
                    return
            except ValueError:
                # Treat as filename
                img_path = os.path.join(IMAGE_DIR, args.image)
                if not os.path.exists(img_path):
                    print(f"❌ Image not found: {args.image}")
                    return
                print(f"Processing: {args.image}")
        else:
            # No image specified, show available options
            print("\nAvailable images:")
            for i, img_file in enumerate(image_files[:10], 1):
                print(f"{i}. {img_file}")
            if len(image_files) > 10:
                print(f"... and {len(image_files) - 10} more")
            
            img_choice = input(f"\nEnter image number (1-{min(10, len(image_files))}) or filename: ").strip()
            
            try:
                img_index = int(img_choice) - 1
                if 0 <= img_index < len(image_files):
                    img_path = os.path.join(IMAGE_DIR, image_files[img_index])
                    print(f"Processing: {image_files[img_index]}")
                else:
                    print("❌ Invalid image number")
                    return
            except ValueError:
                img_path = os.path.join(IMAGE_DIR, img_choice)
                if not os.path.exists(img_path):
                    print(f"❌ Image not found: {img_choice}")
                    return
                print(f"Processing: {img_choice}")
        
        success = processor.process_single_recipe(img_path, args.generate_images, args.force_reprocess)
        if success:
            print(f"✅ Successfully processed recipe!")
        else:
            print(f"❌ Failed to process recipe")
            
    elif args.all:
        # Process all images
        print("🔄 Processing all images...")
        processor.process_all_images(
            start_index=args.start_index,
            batch_size=args.batch_size,
            limit=args.limit,
            generate_images=args.generate_images,
            force_reprocess=args.force_reprocess
        )
        
    elif args.images_only:
        # Generate images only for processed recipes
        print("🖼️  Generating images for processed recipes...")
        # Force reprocess flag should not affect images-only mode
        processor.generate_images_for_processed_recipes(
            batch_size=args.batch_size,
            limit=args.limit
        )
        
    elif args.csv_only:
        # Create master CSV only
        print("📊 Creating master CSV...")
        processor.create_master_csv()
    
    # Create master CSV (unless csv-only mode or images-only mode)
    if not args.csv_only and not args.images_only:
        processor.create_master_csv()
    
    print(f"\n🎉 Processing complete!")
    print(f"✅ Successfully processed: {processor.processed_count}")
    print(f"❌ Failed: {processor.failed_count}")

if __name__ == "__main__":
    main() 