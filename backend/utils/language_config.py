# Language support configuration
SUPPORTED_LANGUAGES = {
    # European Languages
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'nl': 'Dutch',
    'sv': 'Swedish',
    'da': 'Danish',
    'no': 'Norwegian',
    'fi': 'Finnish',
    'pl': 'Polish',
    'cs': 'Czech',
    'sk': 'Slovak',
    'hu': 'Hungarian',
    'ro': 'Romanian',
    'bg': 'Bulgarian',
    'hr': 'Croatian',
    'sr': 'Serbian',
    'sl': 'Slovenian',
    'et': 'Estonian',
    'lv': 'Latvian',
    'lt': 'Lithuanian',
    'el': 'Greek',
    
    # Asian Languages
    'zh': 'Chinese (Simplified)',
    'zh-tw': 'Chinese (Traditional)',
    'ja': 'Japanese',
    'ko': 'Korean',
    'hi': 'Hindi',
    'bn': 'Bengali',
    'ur': 'Urdu',
    'ta': 'Tamil',
    'te': 'Telugu',
    'ml': 'Malayalam',
    'kn': 'Kannada',
    'gu': 'Gujarati',
    'pa': 'Punjabi',
    'mr': 'Marathi',
    'ne': 'Nepali',
    'si': 'Sinhala',
    'my': 'Myanmar (Burmese)',
    'th': 'Thai',
    'vi': 'Vietnamese',
    'id': 'Indonesian',
    'ms': 'Malay',
    'tl': 'Filipino',
    'km': 'Khmer',
    'lo': 'Lao',
    
    # Middle Eastern and African Languages
    'ar': 'Arabic',
    'fa': 'Persian (Farsi)',
    'tr': 'Turkish',
    'he': 'Hebrew',
    'sw': 'Swahili',
    'am': 'Amharic',
    'ha': 'Hausa',
    'yo': 'Yoruba',
    'zu': 'Zulu',
    'af': 'Afrikaans',
    
    # Other Languages
    'eu': 'Basque',
    'ca': 'Catalan',
    'cy': 'Welsh',
    'ga': 'Irish',
    'is': 'Icelandic',
    'mt': 'Maltese',
    'sq': 'Albanian',
    'mk': 'Macedonian',
    'be': 'Belarusian',
    'uk': 'Ukrainian',
    'ka': 'Georgian',
    'hy': 'Armenian',
    'az': 'Azerbaijani',
    'kk': 'Kazakh',
    'ky': 'Kyrgyz',
    'uz': 'Uzbek',
    'tg': 'Tajik',
    'mn': 'Mongolian'
}

# Languages that work well with the current embedding model
WELL_SUPPORTED_LANGUAGES = [
    'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko',
    'ar', 'hi', 'tr', 'nl', 'pl', 'sv', 'da', 'no', 'fi'
]

# Languages that might need special handling
SPECIAL_HANDLING_LANGUAGES = {
    'ar': 'right_to_left',
    'he': 'right_to_left',
    'fa': 'right_to_left',
    'ur': 'right_to_left',
    'zh': 'no_spaces',
    'ja': 'no_spaces',
    'th': 'no_spaces',
    'km': 'no_spaces',
    'lo': 'no_spaces',
    'my': 'no_spaces'
}

def get_language_name(lang_code):
    """Get human-readable language name from code"""
    return SUPPORTED_LANGUAGES.get(lang_code, f"Language ({lang_code})")

def is_well_supported(lang_code):
    """Check if language is well supported by the embedding model"""
    return lang_code in WELL_SUPPORTED_LANGUAGES

def needs_special_handling(lang_code):
    """Check if language needs special text processing"""
    return lang_code in SPECIAL_HANDLING_LANGUAGES

def get_special_handling_type(lang_code):
    """Get the type of special handling needed"""
    return SPECIAL_HANDLING_LANGUAGES.get(lang_code, None)