"""
Flexible JSON Parser for Medical Flashcard Converter
Handles n8n output format with triple-layer JSON structure and various malformed inputs
"""

import json
import re
import logging
from typing import Any, Dict, List, Optional, Union
from functools import wraps
import time

# Configure logging
logger = logging.getLogger(__name__)


class FlexibleJSONParser:
    """
    Flexible JSON parser designed to handle n8n's triple-layer JSON structure
    and various other malformed JSON inputs from LLMs and automation tools.
    """
    
    def __init__(self):
        self.last_strategy_used = None
        self.parsing_attempts = []
        
    def parse(self, raw_input: str, source_hint: str = None) -> Union[Dict, List]:
        """
        Main parsing method that tries multiple strategies to parse the input.
        
        Args:
            raw_input: The raw string input to parse
            source_hint: Optional hint about the source (e.g., 'n8n', 'llm')
            
        Returns:
            Parsed JSON data (dict or list)
            
        Raises:
            ValueError: If all parsing strategies fail
        """
        self.parsing_attempts = []
        errors = []
        
        # Log the raw input for debugging (first 500 chars)
        logger.debug(f"Raw input preview: {raw_input[:500]}...")
        
        # Strategy 1: Handle n8n triple-layer structure FIRST if hint provided
        if source_hint == 'n8n' or self._looks_like_n8n(raw_input):
            try:
                result = self._parse_n8n_format(raw_input)
                if result is not None:
                    self.last_strategy_used = "n8n_triple_layer"
                    return result
            except Exception as e:
                errors.append(f"n8n parsing: {str(e)}")
        
        # Strategy 2: Direct JSON parsing
        try:
            result = self._parse_standard(raw_input)
            if result is not None:
                self.last_strategy_used = "standard"
                return result
        except Exception as e:
            errors.append(f"Standard parsing: {str(e)}")
            
        
        # Strategy 3: Clean and parse
        try:
            result = self._parse_with_cleanup(raw_input)
            if result is not None:
                self.last_strategy_used = "cleanup"
                return result
        except Exception as e:
            errors.append(f"Cleanup parsing: {str(e)}")
            
        # Strategy 4: Extract JSON from text
        try:
            result = self._parse_with_extraction(raw_input)
            if result is not None:
                self.last_strategy_used = "extraction"
                return result
        except Exception as e:
            errors.append(f"Extraction parsing: {str(e)}")
            
        # Strategy 5: Try to repair JSON
        try:
            result = self._parse_with_repair(raw_input)
            if result is not None:
                self.last_strategy_used = "repair"
                return result
        except Exception as e:
            errors.append(f"Repair parsing: {str(e)}")
        
        # All strategies failed
        error_summary = "; ".join(errors)
        logger.error(f"All parsing strategies failed: {error_summary}")
        raise ValueError(f"Failed to parse JSON. Errors: {error_summary}")
    
    def _parse_standard(self, raw_input: str) -> Any:
        """Standard JSON parsing"""
        self.parsing_attempts.append("standard")
        return json.loads(raw_input.strip())
    
    def _looks_like_n8n(self, raw_input: str) -> bool:
        """Check if input looks like n8n format"""
        # n8n typically has array with objects containing "output" field
        return '"output"' in raw_input and '```json' in raw_input
    
    def _parse_n8n_format(self, raw_input: str) -> List[Dict]:
        """
        Parse n8n's triple-layer format:
        1. Outer array of objects with "output" field
        2. Each output contains markdown-wrapped JSON string
        3. Inside is actual JSON with "cards" array
        """
        self.parsing_attempts.append("n8n_triple_layer")
        
        # First, parse the outer JSON array
        outer_data = json.loads(raw_input.strip())
        
        # Ensure it's a list
        if not isinstance(outer_data, list):
            outer_data = [outer_data]
        
        all_cards = []
        
        # Process each item in the outer array
        for item in outer_data:
            if not isinstance(item, dict):
                continue
                
            # Look for the "output" field
            output_content = item.get('output', '')
            
            if not output_content:
                # Try other common field names
                output_content = item.get('data', '') or item.get('result', '')
            
            if output_content:
                # Extract JSON from markdown code blocks
                json_matches = re.findall(r'```json\s*(.*?)\s*```', output_content, re.DOTALL)
                
                for json_str in json_matches:
                    try:
                        # Parse the inner JSON
                        inner_data = json.loads(json_str)
                        
                        # Extract cards if present
                        if isinstance(inner_data, dict) and 'cards' in inner_data:
                            cards = inner_data['cards']
                            if isinstance(cards, list):
                                all_cards.extend(cards)
                        elif isinstance(inner_data, list):
                            # Direct list of cards
                            all_cards.extend(inner_data)
                        else:
                            # Single card
                            all_cards.append(inner_data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse inner JSON: {e}")
                        continue
        
        # Return the aggregated cards in expected format
        if all_cards:
            return {'cards': all_cards}
        
        # If no cards found, try alternative parsing
        return None
    
    def _parse_with_cleanup(self, raw_input: str) -> Any:
        """Parse after cleaning common issues"""
        self.parsing_attempts.append("cleanup")
        cleaned = self._clean_json_string(raw_input)
        return json.loads(cleaned)
    
    def _clean_json_string(self, raw_string: str) -> str:
        """Clean common JSON formatting issues"""
        # Remove BOM if present
        if raw_string.startswith('\ufeff'):
            raw_string = raw_string[1:]
        
        # Remove markdown code blocks
        raw_string = re.sub(r'```json?\s*', '', raw_string)
        raw_string = re.sub(r'\s*```', '', raw_string)
        
        # Remove common LLM prefixes
        prefixes = [
            "Here is the JSON:",
            "Here's the result:",
            "The JSON output is:",
            "JSON:",
            "Output:",
            "Result:",
        ]
        for prefix in prefixes:
            if raw_string.strip().startswith(prefix):
                raw_string = raw_string[len(prefix):].strip()
        
        # Fix trailing commas
        raw_string = re.sub(r',\s*}', '}', raw_string)
        raw_string = re.sub(r',\s*]', ']', raw_string)
        
        # Remove trailing text after JSON
        # Find the last } or ] and remove everything after
        last_close = max(raw_string.rfind('}'), raw_string.rfind(']'))
        if last_close > 0:
            # Check if there's non-whitespace after the closing bracket
            after_json = raw_string[last_close + 1:].strip()
            if after_json and not after_json.startswith(('}', ']')):
                raw_string = raw_string[:last_close + 1]
        
        return raw_string.strip()
    
    def _parse_with_extraction(self, raw_input: str) -> Any:
        """Extract JSON from surrounding text"""
        self.parsing_attempts.append("extraction")
        
        # Look for JSON-like structures (objects or arrays)
        # This regex handles nested structures better
        json_pattern = r'(\{(?:[^{}]|(?:\{[^{}]*\}))*\}|\[(?:[^\[\]]|(?:\[[^\[\]]*\]))*\])'
        matches = re.findall(json_pattern, raw_input, re.DOTALL)
        
        # Try to parse each match, starting with the largest
        matches_with_size = [(m, len(m)) for m in matches]
        matches_with_size.sort(key=lambda x: x[1], reverse=True)
        
        for match, _ in matches_with_size:
            try:
                result = json.loads(match)
                return result
            except json.JSONDecodeError:
                continue
        
        # If no direct matches, try to find markdown code blocks
        code_blocks = re.findall(r'```(?:json)?\s*(.*?)\s*```', raw_input, re.DOTALL)
        for block in code_blocks:
            try:
                result = json.loads(block)
                return result
            except json.JSONDecodeError:
                continue
        
        return None
    
    def _parse_with_repair(self, raw_input: str) -> Any:
        """Attempt to repair common JSON issues"""
        self.parsing_attempts.append("repair")
        
        repaired = raw_input.strip()
        
        # Fix unescaped quotes inside string values
        # This is a simplified approach - in production, use json_repair library
        repaired = self._fix_unescaped_quotes(repaired)
        
        # Fix missing quotes around keys
        repaired = re.sub(r'(\w+):', r'"\1":', repaired)
        
        # Fix single quotes to double quotes
        # Be careful not to change quotes inside string values
        repaired = self._fix_single_quotes(repaired)
        
        # Try to parse the repaired JSON
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            return None
    
    def _fix_unescaped_quotes(self, json_str: str) -> str:
        """Fix unescaped quotes in JSON strings (simplified version)"""
        # This is a basic implementation - for production, use a proper JSON repair library
        # Look for patterns like: "key": "value with " quote"
        pattern = r'"([^"]*)":\s*"([^"]*)"([^",}\]]*)"'
        
        def replacer(match):
            key = match.group(1)
            value_start = match.group(2)
            value_end = match.group(3)
            # Escape the quotes in the value
            value_end_escaped = value_end.replace('"', '\\"')
            return f'"{key}": "{value_start}{value_end_escaped}"'
        
        return re.sub(pattern, replacer, json_str)
    
    def _fix_single_quotes(self, json_str: str) -> str:
        """Convert single quotes to double quotes (carefully)"""
        # This is simplified - proper implementation would use a parser
        # Only replace single quotes that are likely to be JSON string delimiters
        result = json_str
        
        # Replace single quotes around keys
        result = re.sub(r"'(\w+)':", r'"\1":', result)
        
        # Replace single quotes around simple values
        result = re.sub(r":\s*'([^']*)'", r': "\1"', result)
        
        return result


class N8nFlashcardParser:
    """
    Specialized parser for n8n flashcard output format.
    Handles the specific structure where cards are wrapped in output strings with markdown.
    """
    
    def __init__(self):
        self.flexible_parser = FlexibleJSONParser()
        
    def parse_flashcard_data(self, raw_data: str) -> Dict:
        """
        Parse flashcard data from n8n format.
        
        Returns:
            Dict with 'cards' array and optional 'deck_name'
        """
        start_time = time.time()
        
        try:
            # Use flexible parser with n8n hint
            parsed_data = self.flexible_parser.parse(raw_data, source_hint='n8n')
            
            # Normalize the structure
            normalized = self._normalize_flashcard_structure(parsed_data)
            
            # Log parsing results
            parsing_time = (time.time() - start_time) * 1000
            logger.info(f"Successfully parsed {len(normalized.get('cards', []))} cards in {parsing_time:.2f}ms using {self.flexible_parser.last_strategy_used} strategy")
            
            return normalized
            
        except Exception as e:
            parsing_time = (time.time() - start_time) * 1000
            logger.error(f"Failed to parse flashcard data after {parsing_time:.2f}ms: {e}")
            raise
    
    def _normalize_flashcard_structure(self, data: Any) -> Dict:
        """
        Normalize various flashcard data structures to a consistent format.
        """
        # If already in correct format
        if isinstance(data, dict) and 'cards' in data:
            return data
        
        # If it's a direct array of cards
        if isinstance(data, list):
            return {'cards': data}
        
        # If it's a single card
        if isinstance(data, dict) and any(key in data for key in ['front', 'back', 'question', 'answer']):
            return {'cards': [data]}
        
        # Try to find cards in nested structures
        if isinstance(data, dict):
            for key in ['cards', 'data', 'items', 'flashcards']:
                if key in data and isinstance(data[key], list):
                    return {'cards': data[key]}
        
        # Default - return empty cards array
        logger.warning("Could not find cards in parsed data structure")
        return {'cards': []}


def parse_with_logging(parser_func):
    """Decorator to add logging to parser functions"""
    @wraps(parser_func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = parser_func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            logger.debug(f"{parser_func.__name__} succeeded in {duration:.2f}ms")
            return result
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.debug(f"{parser_func.__name__} failed after {duration:.2f}ms: {e}")
            raise
    return wrapper


# Export main classes and functions
__all__ = ['FlexibleJSONParser', 'N8nFlashcardParser']