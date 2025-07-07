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
import openai
import pytesseract
from PIL import Image
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Load environment variables
load_dotenv()

# Load API key from environment
openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key:
    openai.api_key = openai_api_key
else:
    print("❌ OPENAI_API_KEY environment variable not found.")
    print("   Please set OPENAI_API_KEY in your .env file or environment variables.")
    exit(1)

# Constants
IMAGE_DIR = "./Original-Images/"
PRODUCTS_DIR = "./Products/"
MAX_FILENAME_LENGTH = 64

# Logging setup
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Utility functions
def slugify(text):
    text = re.sub(r'[^a-zA-Z0-9]+', '-', text.lower()).strip('-')
    return text[:MAX_FILENAME_LENGTH]

def random_hash():
    return ''.join(random.choices('0123456789abcdef', k=6))

def extract_text_from_image(image_path):
    try:
        return pytesseract.image_to_string(Image.open(image_path))
    except Exception as e:
        logging.error(f"OCR failed on {image_path}: {e}")
        return ""

def ask_gpt(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Extract and structure recipe information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return ""

def parse_recipe(text):
    prompt = f"""
    Here is a scanned recipe. Parse it into:
    - Title
    - Ingredients (as a list)
    - Instructions (as steps)
    Text:
    ---
    {text}
    ---
    """
    response = ask_gpt(prompt)
    return response

def generate_pdf(title, ingredients, steps, output_path):
    try:
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter

        # Decorative lines
        c.setStrokeColor(colors.black)
        c.setLineWidth(2)
        c.line(0.5 * inch, height - 0.75 * inch, width - 0.5 * inch, height - 0.75 * inch)
        c.line(0.5 * inch, 0.75 * inch, width - 0.5 * inch, 0.75 * inch)

        # Title
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width / 2.0, height - 1.2 * inch, title)

        # Ingredients box
        c.setFont("Helvetica", 12)
        c.rect(width - 3.5 * inch, height - 3.75 * inch, 3 * inch, 2.75 * inch)
        c.drawString(width - 3.3 * inch, height - 1.5 * inch, "Ingredients:")
        text = c.beginText(width - 3.3 * inch, height - 1.75 * inch)
        for item in ingredients:
            text.textLine(f"• {item.strip()}")
        c.drawText(text)

        # Instructions
        y = height - 4.25 * inch
        c.setFont("Helvetica", 12)
        c.drawString(0.75 * inch, y, "Instructions:")
        y -= 0.25 * inch
        for idx, step in enumerate(steps):
            wrapped = textwrap.wrap(step, width=85)
            for line in wrapped:
                if y < 1 * inch:
                    c.showPage()
                    y = height - 1 * inch
                c.drawString(0.75 * inch, y, line)
                y -= 0.2 * inch
            y -= 0.15 * inch

        # Footer note
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(0.75 * inch, 0.5 * inch, "Nutrition info estimated. For reference only.")

        c.save()
        logging.info(f"🧾 PDF saved: {output_path}")

    except Exception as e:
        logging.error(f"PDF generation error: {e}")

# Main automation pipeline
def process_images(count):
    image_files = sorted([f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    selected_files = image_files[:count]

    for img_file in selected_files:
        try:
            img_path = os.path.join(IMAGE_DIR, img_file)
            ocr_text = extract_text_from_image(img_path)

            if not ocr_text.strip():
                logging.warning(f"No OCR text found in {img_file}. Skipping.")
                continue

            parsed = parse_recipe(ocr_text)

            # Naive parsing until GPT returns structure
            title = "Untitled Recipe"
            ingredients = ["Unknown"]
            instructions = ["Unknown"]

            title_match = re.search(r'Title: (.*)', parsed)
            if title_match:
                title = title_match.group(1).strip()

            ing_match = re.findall(r'- (.+)', parsed)
            if ing_match:
                ingredients = ing_match

            step_match = re.findall(r'\d+\. (.+)', parsed)
            if step_match:
                instructions = step_match

            slug = slugify(title)
            unique_id = f"{slug}-{random_hash()}"
            recipe_dir = os.path.join(PRODUCTS_DIR, unique_id)
            os.makedirs(recipe_dir, exist_ok=True)

            # Move image
            dest_image_path = os.path.join(recipe_dir, f"original-{img_file}")
            shutil.move(img_path, dest_image_path)

            # Generate PDF
            pdf_path = os.path.join(recipe_dir, f"{slug}_Recipe-Card.pdf")
            generate_pdf(title, ingredients, instructions, pdf_path)

        except Exception as e:
            logging.error(f"❌ Failed on {img_file}: {e}")
            continue

# Run script interactively
if __name__ == '__main__':
    image_files = sorted([f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    print(f"📷 Found {len(image_files)} images.")
    count = input(f"How many recipe images to process? (1–{len(image_files)}): ")
    try:
        process_images(int(count))
    except Exception as e:
        logging.error(f"⚠️ Failed to run script: {e}")
