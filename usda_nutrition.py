import requests
import json
import re
import logging
from datetime import datetime
import pytz
import os
from typing import Dict, List, Optional, Tuple

class USDANutritionAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.nal.usda.gov/fdc/v1"
        
        # Set up logging
        self.setup_logging()
        
    def setup_logging(self):
        """Set up comprehensive logging to file"""
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Create timestamp for log file
        mst = pytz.timezone('US/Mountain')
        timestamp = datetime.now(mst).strftime("%Y%m%d_%H%M%S")
        
        # Set up file handler
        log_filename = f"logs/usda_nutrition_{timestamp}.log"
        file_handler = logging.FileHandler(log_filename, mode='w')
        file_handler.setLevel(logging.INFO)
        
        # Set up console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Set up logger
        self.logger = logging.getLogger('USDANutrition')
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()  # Clear existing handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Log initial setup
        self.logger.info("=" * 80)
        self.logger.info("USDA NUTRITION ANALYZER INITIALIZED")
        self.logger.info("=" * 80)
        self.logger.info(f"Log file: {log_filename}")
        self.logger.info(f"Timestamp: {datetime.now(mst).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        self.logger.info("=" * 80)
        
    def log_api_call(self, method: str, url: str, params: Dict = None, headers: Dict = None, response=None):
        """Log detailed API call information"""
        mst = pytz.timezone('US/Mountain')
        timestamp = datetime.now(mst).strftime("%Y-%m-%d %H:%M:%S %Z")
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"API CALL - {timestamp}")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Method: {method}")
        self.logger.info(f"URL: {url}")
        
        if params:
            self.logger.info(f"Parameters: {json.dumps(params, indent=2)}")
        
        if headers:
            self.logger.info(f"Headers: {json.dumps(headers, indent=2)}")
        
        if response:
            self.logger.info(f"Status Code: {response.status_code}")
            
            # Log rate limit headers
            rate_limit_headers = {
                'X-RateLimit-Limit': response.headers.get('X-RateLimit-Limit', 'Not provided'),
                'X-RateLimit-Remaining': response.headers.get('X-RateLimit-Remaining', 'Not provided'),
                'X-RateLimit-Reset': response.headers.get('X-RateLimit-Reset', 'Not provided')
            }
            self.logger.info(f"Rate Limit Info: {json.dumps(rate_limit_headers, indent=2)}")
            
            # Log response headers
            self.logger.info(f"Response Headers: {dict(response.headers)}")
            
            # Log response body (truncated if too long)
            try:
                response_data = response.json()
                if len(json.dumps(response_data)) > 1000:
                    self.logger.info(f"Response Body (truncated): {json.dumps(response_data, indent=2)[:1000]}...")
                else:
                    self.logger.info(f"Response Body: {json.dumps(response_data, indent=2)}")
            except:
                self.logger.info(f"Response Text: {response.text[:500]}...")
        
        self.logger.info(f"{'='*60}\n")
    
    def search_food(self, query: str) -> List[Dict]:
        """Search for foods in the USDA database"""
        url = f"{self.base_url}/foods/search"
        params = {
            'api_key': self.api_key,
            'query': query,
            'pageSize': 10,
            'dataType': ['Foundation', 'SR Legacy']
        }
        
        self.logger.info(f"🔍 Searching USDA database for: '{query}'")
        
        try:
            response = requests.get(url, params=params)
            self.log_api_call('GET', url, params, response=response)
            
            if response.status_code == 200:
                data = response.json()
                foods = data.get('foods', [])
                self.logger.info(f"✅ Found {len(foods)} results for '{query}'")
                return foods
            else:
                self.logger.error(f"❌ Search failed for '{query}': {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"❌ Exception during search for '{query}': {e}")
            return []
    
    def get_food_details(self, fdc_id: int) -> Optional[Dict]:
        """Get detailed nutrition information for a specific food"""
        url = f"{self.base_url}/food/{fdc_id}"
        params = {'api_key': self.api_key}
        
        self.logger.info(f"📊 Getting nutrition details for FDC ID: {fdc_id}")
        
        try:
            response = requests.get(url, params=params)
            self.log_api_call('GET', url, params, response=response)
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"✅ Retrieved nutrition data for FDC ID: {fdc_id}")
                return data
            else:
                self.logger.error(f"❌ Failed to get details for FDC ID {fdc_id}: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Exception getting details for FDC ID {fdc_id}: {e}")
            return None
    
    def parse_ingredient(self, ingredient: str) -> Tuple[str, str, str]:
        """Parse ingredient into quantity, unit, and food name"""
        # Remove common modifiers and parentheses
        ingredient = re.sub(r'\([^)]*\)', '', ingredient)  # Remove parentheses content
        ingredient = re.sub(r'\b(fresh|dried|frozen|organic|large|small|medium|ripe|unripe)\b', '', ingredient, flags=re.IGNORECASE)
        ingredient = ingredient.strip()
        
        # Common units and their patterns
        units = {
            'cup': r'\b(c\.?|cup|cups)\b',
            'tablespoon': r'\b(tbsp\.?|tablespoon|tablespoons)\b',
            'teaspoon': r'\b(tsp\.?|teaspoon|teaspoons)\b',
            'ounce': r'\b(oz\.?|ounce|ounces)\b',
            'pound': r'\b(lb\.?|pound|pounds)\b',
            'gram': r'\b(g\.?|gram|grams)\b',
            'pint': r'\b(pint|pints)\b',
            'quart': r'\b(qt\.?|quart|quarts)\b',
            'gallon': r'\b(gal\.?|gallon|gallons)\b'
        }
        
        # Remove common prefixes that aren't food names
        prefixes_to_remove = [
            r'^\.\s*',  # Remove leading period
            r'^at least\s+',
            r'^about\s+',
            r'^approximately\s+',
            r'^to taste\s+',
            r'^for decoration\s*',
            r'^chopped\s+',
            r'^diced\s+',
            r'^minced\s+',
            r'^sliced\s+',
            r'^grated\s+',
        ]
        
        for prefix in prefixes_to_remove:
            ingredient = re.sub(prefix, '', ingredient, flags=re.IGNORECASE)
        
        ingredient = ingredient.strip()
        
        # Also remove trailing periods and common suffixes
        ingredient = re.sub(r'\.$', '', ingredient)  # Remove trailing period
        ingredient = re.sub(r',\s*chopped$', '', ingredient, flags=re.IGNORECASE)
        ingredient = re.sub(r',\s*diced$', '', ingredient, flags=re.IGNORECASE)
        ingredient = re.sub(r',\s*minced$', '', ingredient, flags=re.IGNORECASE)
        ingredient = re.sub(r',\s*sliced$', '', ingredient, flags=re.IGNORECASE)
        ingredient = re.sub(r',\s*grated$', '', ingredient, flags=re.IGNORECASE)
        ingredient = re.sub(r'\s+for decoration$', '', ingredient, flags=re.IGNORECASE)
        
        ingredient = ingredient.strip()
        
        # First, try to find fractions
        fraction_pattern = r'^(\d+/\d+)'
        fraction_match = re.match(fraction_pattern, ingredient)
        if fraction_match:
            quantity = fraction_match.group(1)
            remaining = ingredient[len(quantity):].strip()
            
            # Look for unit in remaining text
            unit = ""
            food_name = remaining
            for unit_name, unit_pattern in units.items():
                unit_match = re.search(unit_pattern, remaining, re.IGNORECASE)
                if unit_match:
                    unit = unit_name
                    food_name = remaining[:unit_match.start()] + remaining[unit_match.end():]
                    break
            
            return quantity, unit, food_name.strip()
        
        # Then try decimal numbers
        number_pattern = r'^(\d+(?:\.\d+)?)'
        number_match = re.match(number_pattern, ingredient)
        if number_match:
            quantity = number_match.group(1)
            remaining = ingredient[len(quantity):].strip()
            
            # Look for unit in remaining text
            unit = ""
            food_name = remaining
            for unit_name, unit_pattern in units.items():
                unit_match = re.search(unit_pattern, remaining, re.IGNORECASE)
                if unit_match:
                    unit = unit_name
                    food_name = remaining[:unit_match.start()] + remaining[unit_match.end():]
                    break
            
            return quantity, unit, food_name.strip()
        
        # If no quantity found, assume it's just a food name
        return "1", "", ingredient
    
    def extract_nutrients(self, food_data: Dict) -> Dict[str, float]:
        """Extract nutrition information from food data"""
        nutrients = {}
        
        if 'foodNutrients' not in food_data:
            self.logger.warning(f"⚠️  No foodNutrients found in food data")
            return nutrients
        
        # Nutrient ID mapping with flexible matching
        nutrient_mapping = {
            'calories': ['208', 'ENERC_KCAL', 'calories', 'energy'],
            'protein': ['203', 'PROCNT', 'protein'],
            'fat': ['204', 'FAT', 'total fat', 'fat'],
            'carbs': ['205', 'CHOCDF', 'carbohydrate', 'carbs'],
            'fiber': ['291', 'FIBTG', 'fiber', 'dietary fiber'],
            'sugar': ['269', 'SUGAR', 'sugar', 'total sugars'],
            'sodium': ['307', 'NA', 'sodium'],
            'calcium': ['301', 'CA', 'calcium'],
            'iron': ['303', 'FE', 'iron'],
            'vitamin_c': ['401', 'VITC', 'vitamin c', 'ascorbic acid'],
            'vitamin_a': ['320', 'VITA_RAE', 'vitamin a'],
        }
        
        for nutrient_name, search_terms in nutrient_mapping.items():
            for nutrient in food_data['foodNutrients']:
                # Handle both old and new nutrient data structures
                nutrient_id = str(nutrient.get('nutrientId', nutrient.get('nutrient', {}).get('id', '')))
                nutrient_name_lower = nutrient.get('nutrientName', nutrient.get('nutrient', {}).get('name', '')).lower()
                
                # Check if this nutrient matches any of our search terms
                if (nutrient_id in search_terms or 
                    any(term in nutrient_name_lower for term in search_terms)):
                    
                    value = nutrient.get('value', nutrient.get('amount', 0))
                    unit = nutrient.get('unitName', nutrient.get('nutrient', {}).get('unitName', ''))
                    
                    self.logger.info(f"📊 Found {nutrient_name}: {value} {unit} (ID: {nutrient_id}, Name: {nutrient.get('nutrientName', nutrient.get('nutrient', {}).get('name', 'Unknown'))})")
                    
                    # Convert to standard units if needed
                    if unit.lower() in ['mg', 'milligram'] and nutrient_name in ['sodium', 'calcium', 'iron']:
                        value = value / 1000  # Convert mg to g
                    elif unit.lower() in ['mcg', 'microgram'] and nutrient_name in ['vitamin_a']:
                        value = value / 1000  # Convert mcg to mg
                    
                    nutrients[nutrient_name] = value
                    break
        
        self.logger.info(f"📊 Extracted {len(nutrients)} nutrients: {nutrients}")
        return nutrients
    
    def analyze_recipe_nutrition(self, ingredients: List[str], servings: int = 8) -> Dict:
        """Analyze nutrition for a complete recipe"""
        self.logger.info(f"🍳 Starting nutrition analysis for recipe with {len(ingredients)} ingredients")
        self.logger.info(f"📋 Ingredients: {ingredients}")
        self.logger.info(f"🍽️  Servings: {servings}")
        
        total_nutrients = {
            'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 
            'fiber': 0, 'sugar': 0, 'sodium': 0, 'calcium': 0, 
            'iron': 0, 'vitamin_c': 0, 'vitamin_a': 0
        }
        
        ingredient_results = []
        
        for ingredient in ingredients:
            self.logger.info(f"\n🔍 Processing ingredient: {ingredient}")
            
            # Parse ingredient
            quantity, unit, food_name = self.parse_ingredient(ingredient)
            self.logger.info(f"📝 Parsed: quantity={quantity}, unit='{unit}', food='{food_name}'")
            
            if not food_name:
                self.logger.warning(f"⚠️  Could not parse food name from: {ingredient}")
                continue
            
            # Search for the food
            search_results = self.search_food(food_name)
            
            if not search_results:
                self.logger.warning(f"⚠️  No results found for: {food_name}")
                continue
            
            # Get the best match (usually the first result)
            best_match = search_results[0]
            fdc_id = best_match.get('fdcId')
            description = best_match.get('description', 'Unknown')
            
            self.logger.info(f"✅ Best match: {description} (FDC ID: {fdc_id})")
            
            # Get detailed nutrition
            food_details = self.get_food_details(fdc_id)
            
            if not food_details:
                self.logger.warning(f"⚠️  Could not get nutrition details for: {food_name}")
                continue
            
            # Extract nutrients
            nutrients = self.extract_nutrients(food_details)
            
            if not nutrients:
                self.logger.warning(f"⚠️  No nutrients extracted for: {food_name}")
                continue
            
            # Calculate quantity multiplier
            try:
                qty_multiplier = float(quantity) if quantity else 1.0
                if unit.lower() in ['cup', 'cups']:
                    qty_multiplier *= 240  # grams per cup (approximate)
                elif unit.lower() in ['tbsp', 'tablespoon', 'tablespoons']:
                    qty_multiplier *= 15  # grams per tablespoon
                elif unit.lower() in ['tsp', 'teaspoon', 'teaspoons']:
                    qty_multiplier *= 5  # grams per teaspoon
                elif unit.lower() in ['oz', 'ounce', 'ounces']:
                    qty_multiplier *= 28.35  # grams per ounce
                elif unit.lower() in ['lb', 'pound', 'pounds']:
                    qty_multiplier *= 453.59  # grams per pound
                elif unit.lower() in ['g', 'gram', 'grams']:
                    qty_multiplier *= 1  # already in grams
                else:
                    # Assume it's a count (like "2 eggs")
                    qty_multiplier *= 50  # approximate grams per item
                
                self.logger.info(f"📊 Quantity multiplier: {qty_multiplier}")
                
            except ValueError:
                self.logger.warning(f"⚠️  Could not parse quantity '{quantity}', using 1.0")
                qty_multiplier = 1.0
            
            # Scale nutrients by quantity
            scaled_nutrients = {}
            for nutrient, value in nutrients.items():
                scaled_value = value * qty_multiplier / 100  # USDA data is per 100g
                scaled_nutrients[nutrient] = scaled_value
                total_nutrients[nutrient] += scaled_value
            
            ingredient_results.append({
                'ingredient': ingredient,
                'food_name': food_name,
                'quantity': quantity,
                'unit': unit,
                'fdc_id': fdc_id,
                'description': description,
                'nutrients': scaled_nutrients
            })
            
            self.logger.info(f"📊 Scaled nutrients for {food_name}: {scaled_nutrients}")
        
        # Calculate per-serving values
        per_serving = {}
        for nutrient, total in total_nutrients.items():
            per_serving[nutrient] = total / servings
        
        self.logger.info(f"\n📊 TOTAL NUTRITION (per serving):")
        for nutrient, value in per_serving.items():
            self.logger.info(f"  {nutrient}: {value:.2f}")
        
        self.logger.info(f"\n✅ Nutrition analysis complete!")
        
        return {
            'total': total_nutrients,
            'per_serving': per_serving,
            'ingredients': ingredient_results,
            'servings': servings
        } 