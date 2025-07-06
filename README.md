# Etsy Recipe Automation System

A comprehensive Python system for automating the processing of vintage recipe images into Etsy-ready digital products.

## 🍳 Features

- **Smart OCR Processing**: Uses OpenAI Vision API for high-quality text extraction
- **AI-Powered Analysis**: USDA nutrition database integration with fallback LLM estimation
- **Recipe Detail Estimation**: AI-generated servings, prep time, and cook time
- **Batch Processing**: Efficient processing with rate limiting and duplicate prevention
- **Content Generation**: Creates PDFs, listings, social media content, and nutrition labels
- **Cost Control**: Disabled image generation by default to save API costs
- **Comprehensive Logging**: Detailed logs with timestamps and rate limit tracking

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **OpenAI API Key** (for Vision API OCR)
3. **USDA API Key** (for nutrition analysis)
4. **Required packages**: See `requirements.txt`

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd Etsy-Automation

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip3 install -r requirements.txt

# Set up API keys
echo "your-openai-api-key" > API_KEY.txt
```

### Basic Usage

```bash
# Process a single recipe
python3 recipe_automation_v2.py --single --image IMG_0844.jpeg

# Process all recipes (skips already processed)
python3 recipe_automation_v2.py --all --limit 10

# Process with AI image generation
python3 recipe_automation_v2.py --all --generate-images

# Force reprocess already processed images
python3 recipe_automation_v2.py --all --force-reprocess
```

## 📁 Project Structure

```
Etsy-Automation/
├── recipe_automation_v2.py    # Main automation script
├── usda_nutrition.py          # USDA nutrition analysis module
├── config.py                  # Configuration settings
├── API_KEY.txt               # OpenAI API key (not in git)
├── Original-Images/          # Source recipe images
├── Products/                 # Generated content
├── logs/                     # Processing logs
├── venv/                     # Virtual environment
└── README.md                 # This file
```

## 🎯 Command Line Options

### Action Modes
- `--single`: Process one recipe image
- `--all`: Process all recipe images
- `--csv-only`: Create master CSV only

### Processing Options
- `--image <filename>`: Specify image to process
- `--limit <number>`: Limit total images to process
- `--batch-size <number>`: Images per batch (default: 5)
- `--start-index <number>`: Starting index for batch processing

### OCR Options
- `--ocr-method <method>`: `tesseract` or `vision-api` (default: vision-api)

### Content Generation
- `--generate-images`: Enable AI image generation
- `--force-reprocess`: Reprocess already processed images

### Logging
- `-v, --verbose`: Enable verbose logging

## 📊 Generated Content

For each processed recipe, the system creates:

### Files
- **Recipe.txt**: Complete recipe with ingredients, instructions, nutrition
- **Listing.txt**: Etsy listing description and tags
- **Instagram.txt**: Social media content for Instagram
- **Pinterest.txt**: Pinterest-optimized description
- **listing.csv**: Etsy import-ready CSV
- **Recipe-Card.pdf**: Beautiful recipe PDF
- **Recipe-Card-fancy.pdf**: Enhanced PDF version

### Content Features
- **Nutrition Analysis**: USDA database integration with detailed breakdown
- **Allergy Information**: Automatic allergen detection
- **Diet Compatibility**: Vegan, gluten-free, etc. analysis
- **AI-Generated Descriptions**: Compelling Etsy listings
- **Social Media Content**: Platform-optimized posts

## 🔧 Configuration

### API Keys
- **OpenAI**: Required for Vision API OCR and content generation
- **USDA**: Required for nutrition analysis (included in script)

### Rate Limiting
- **Vision API**: Built-in retry logic with exponential backoff
- **USDA API**: 3600 requests per hour limit
- **Batch Processing**: 30-second delays between batches

## 📈 Tracking & Logging

### Processed Images Tracking
- **File**: `processed_images.json`
- **Tracks**: Timestamp, recipe title, success status, OCR method
- **Prevents**: Duplicate processing
- **Allows**: Force reprocessing with `--force-reprocess`

### Log Files
- **Command Execution**: `logs/command_execution_YYYYMMDD_HHMMSS.log`
- **USDA Nutrition**: `logs/usda_nutrition_YYYYMMDD_HHMMSS.log`
- **Rate Limits**: Detailed API call tracking with headers

## 💰 Cost Optimization

### Default Settings (Cost-Effective)
- ✅ **Vision API OCR**: High-quality text extraction
- ✅ **USDA Nutrition**: Free API for nutrition data
- ❌ **AI Image Generation**: Disabled by default
- ✅ **Smart Skipping**: Prevents duplicate processing

### Optional Features (Additional Cost)
- **AI Image Generation**: `--generate-images` flag
- **Enhanced Content**: More detailed AI descriptions

## 🐛 Troubleshooting

### Common Issues

1. **OpenAI API Quota Exceeded**
   - Check your API key and billing
   - Use `--ocr-method tesseract` as fallback

2. **Poor OCR Results**
   - Ensure images are clear and well-lit
   - Try `--ocr-method vision-api` for better results

3. **Missing Nutrition Data**
   - System falls back to LLM estimation
   - Check USDA API key configuration

4. **Duplicate Processing**
   - System automatically skips processed images
   - Use `--force-reprocess` to override

### Debug Mode
```bash
python3 recipe_automation_v2.py --single --verbose
```

## 🔄 Development

### Adding New Features
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Testing
```bash
# Test single recipe processing
python3 recipe_automation_v2.py --single --image test.jpg

# Test batch processing
python3 recipe_automation_v2.py --all --limit 2

# Test with different OCR methods
python3 recipe_automation_v2.py --single --ocr-method tesseract
```

## 📝 License

This project is for personal use. Please respect API usage limits and terms of service.

## 🤝 Contributing

Contributions are welcome! Please ensure:
- Code follows PEP 8 style guidelines
- New features include appropriate logging
- API costs are considered in design decisions
- Documentation is updated for new features

---

**Happy Recipe Processing! 🍳✨** 