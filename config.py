"""
Configuration file for Recipe Automation System
Modify these settings to customize the automation behavior
"""

# API Configuration
OPENAI_MODEL = "gpt-4"  # or "gpt-3.5-turbo" for faster/cheaper processing
OPENAI_TEMPERATURE = 0.4  # Controls creativity (0.0 = deterministic, 1.0 = very creative)

# Processing Configuration
BATCH_SIZE = 5  # Number of images to process before waiting
RATE_LIMIT_DELAY = 2  # Seconds between individual image processing
BATCH_WAIT_TIME = 30  # Seconds to wait between batches

# Image Generation
GENERATE_IMAGES = True  # Set to False to skip DALL-E image generation
IMAGE_SIZE = "1024x1024"  # DALL-E image size
IMAGE_STYLE = "vintage"  # Style for generated images

# Content Generation
DEFAULT_PRICE = "4.99"  # Default Etsy listing price
DEFAULT_QUANTITY = "100"  # Default inventory quantity
CURRENCY_CODE = "USD"  # Currency for listings

# File Paths
IMAGE_DIR = "./Original-Images/"
PRODUCTS_DIR = "./Products/"

# Recipe Processing
MAX_FILENAME_LENGTH = 64
REMOVE_NAMES = True  # Remove personal names from recipes
INCLUDE_NUTRITION = True  # Generate nutrition information
INCLUDE_ALLERGIES = True  # Analyze for allergens
INCLUDE_DIET_INFO = True  # Analyze diet compatibility
INCLUDE_FAITH_QUOTES = True  # Add faith-based quotes

# PDF Generation
PDF_TITLE_SIZE = 24
PDF_HEADING_SIZE = 16
PDF_BODY_SIZE = 12
PDF_QUOTE_SIZE = 12

# Social Media
INSTAGRAM_HASHTAGS = True  # Include hashtags in Instagram posts
PINTEREST_MAX_LENGTH = 500  # Maximum characters for Pinterest descriptions

# Etsy Export
ETSY_MAX_TAGS = 13  # Maximum number of tags for Etsy
ETSY_DESCRIPTION_LENGTH = 5000  # Maximum description length

# Logging
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "[%(levelname)s] %(message)s"

# Error Handling
CONTINUE_ON_ERROR = True  # Continue processing if one recipe fails
SAVE_FAILED_RECIPES = True  # Save failed recipes for manual review
MAX_RETRIES = 3  # Maximum retry attempts for failed API calls

# Content Templates
DESCRIPTION_TEMPLATE = """
Create an enticing Etsy listing description for this vintage recipe. The description should:
- Be warm and nostalgic, mentioning church cookbooks, family traditions
- Describe the end result appealingly
- Mention it's a digital download
- Include suggested uses (gifting, printing, etc.)
- Be 2-3 paragraphs long
"""

FAITH_QUOTE_TEMPLATE = """
Generate a wholesome, faith-based quote that's relevant to this recipe. Consider:
- Recipe title: {title}
- Key ingredients: {ingredients}

The quote should be:
- Biblical or faith-based
- Related to food, family, or community
- Wholesome and uplifting
- Include the verse reference

Return format: "Quote text" — Book Chapter:Verse
"""

IMAGE_PROMPT_TEMPLATE = """
Professional food photography of {recipe_name}, beautifully presented on a rustic wooden table with natural lighting, 
vintage aesthetic, warm colors, appetizing appearance, high quality, no text or watermarks
"""

# Diet and Allergy Keywords
ALLERGY_KEYWORDS = {
    "gluten": ["flour", "wheat", "bread", "cake mix", "pasta", "cereal"],
    "dairy": ["milk", "cheese", "butter", "cream", "yogurt", "sour cream"],
    "eggs": ["egg", "eggs", "egg white", "egg yolk"],
    "nuts": ["nuts", "peanuts", "almonds", "walnuts", "pecans", "cashews"],
    "soy": ["soy", "soybean", "tofu", "soy sauce"],
    "shellfish": ["shrimp", "crab", "lobster", "oysters", "clams"],
    "fish": ["fish", "salmon", "tuna", "cod", "halibut"]
}

DIET_KEYWORDS = {
    "vegan": ["no animal products", "plant-based"],
    "vegetarian": ["no meat", "vegetarian"],
    "gluten-free": ["gluten-free", "no gluten"],
    "dairy-free": ["dairy-free", "no dairy", "lactose-free"],
    "paleo": ["paleo", "grain-free"],
    "keto": ["keto", "low-carb", "ketogenic"],
    "low-carb": ["low-carb", "keto", "carb-free"]
} 