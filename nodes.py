"""
Prompt Preset Selector Node for ComfyUI (Enhanced Version)
Allows selection of text presets from external .txt and .yaml files with:
- Sequential and random selection modes
- Keyword filtering with AND/OR/phrase search
- Preset list display for easy reference
- Absolute path support
- Wildcard expansion support
- Image selection support
"""

import os
import random
import re
from pathlib import Path
import torch
import numpy as np
from PIL import Image

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("[Prompt Preset Selector] Warning: PyYAML not installed. YAML support disabled.")
    print("  Install with: pip install pyyaml --break-system-packages")


class PromptPresetSelector:
    """
    Enhanced preset selector with keyword filtering and multiple selection modes
    """
    
    # Class variable to store continuation state across executions
    _continue_state = {}
    
    def __init__(self):
        self.preset_dir = Path(__file__).parent / "presets"
        self.preset_dir.mkdir(exist_ok=True)
    
    @classmethod
    def INPUT_TYPES(cls):
        instance = cls()
        preset_files = instance.get_preset_files()
        
        if not preset_files:
            preset_files = ["(No preset files found)"]
        
        return {
            "required": {
                "preset_file": (preset_files,),
                "absolute_path": ("STRING", {"default": "", "multiline": False, "placeholder": "Optional: /absolute/path/to/file.txt or .yaml"}),
                "keyword": ("STRING", {"default": "", "multiline": False}),
                "keyword_mode": (["OFF", "AND", "OR"], {"default": "OFF"}),
                "selection_mode": (["Manual", "Sequential", "Sequential (continue)", "Random"], {"default": "Manual"}),
                "preset_index": ("INT", {"default": 0, "min": 0, "max": 9999, "step": 1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("text", "preset_list", "selected_info")
    FUNCTION = "select_preset"
    CATEGORY = "text"
    OUTPUT_NODE = False
    
    @classmethod
    def IS_CHANGED(cls, preset_file, absolute_path, keyword, keyword_mode, selection_mode, preset_index, seed):
        return f"{preset_file}_{absolute_path}_{keyword}_{keyword_mode}_{selection_mode}_{preset_index}_{seed}"
    
    @staticmethod
    def _dropdown_sort_key(rel_path):
        """
        Sort key for the preset dropdown.

        Groups top-level files first, then each subfolder's files together,
        and ignores case so that "Zebra.txt" doesn't jump above "apple.txt".
        Plain sorted() uses code points, which scatters uppercase, underscore
        and non-ASCII names and makes long lists hard to scan.
        """
        parts = rel_path.split('/')
        folder = '/'.join(parts[:-1]).lower()
        return (folder, parts[-1].lower())

    def _scan_preset_dir(self, directory):
        """
        Recursively collect .txt/.yaml/.yml files under a directory,
        returned as paths relative to it (POSIX separators).

        Files directly inside the directory keep their bare file name, so
        preset_file values saved in existing workflows still resolve.
        """
        found = []
        if not directory or not directory.exists():
            return found
        for pattern in ["*.txt", "*.yaml", "*.yml"]:
            for f in directory.rglob(pattern):
                try:
                    found.append(f.relative_to(directory).as_posix())
                except ValueError:
                    found.append(f.name)
        return found

    def get_preset_files(self):
        """Get list of .txt, .yaml, .yml files from both presets and wildcards directories"""
        try:
            files = []
            
            # 1. Get files from presets directory (including subfolders)
            files.extend(self._scan_preset_dir(self.preset_dir))
            
            # 2. Get files from Impact Pack wildcards directory (if exists)
            wildcard_dir = self._get_wildcard_dir()
            for wf in self._scan_preset_dir(wildcard_dir):
                # Add files that don't already exist in presets (avoid duplicates)
                if wf not in files:
                    files.append(wf)
            
            return sorted(files, key=self._dropdown_sort_key) if files else []
        except Exception as e:
            print(f"[Prompt Preset Selector] Error reading preset directories: {e}")
            return []
    
    def _get_wildcard_dir(self):
        """Get the wildcard directory path (for Impact Pack compatibility)"""
        base_dir = Path(__file__).parent
        wildcard_path = base_dir / "../ComfyUI-Impact-Pack/wildcards"
        
        try:
            wildcard_path = wildcard_path.resolve()
            if wildcard_path.exists():
                return wildcard_path
            else:
                return None
        except Exception:
            return None
    
    def load_preset_lines(self, preset_file):
        """
        Load lines from preset file, filtering out comments and empty lines
        Supports .txt, .yaml, .yml files
        
        Searches in:
        1. Absolute path (if provided)
        2. presets directory
        3. wildcards directory (Impact Pack compatibility)
        
        Returns list of strings
        - For .txt files: plain text lines
        - For .yaml files: may include "key1:key2: text" format for nested dicts
        
        Args:
            preset_file: Either a filename (str) or Path object
        """
        try:
            # Handle both relative (from presets dir) and absolute paths
            if isinstance(preset_file, str):
                if os.path.isabs(preset_file):
                    file_path = Path(preset_file)
                else:
                    # Try presets directory first
                    file_path = self.preset_dir / preset_file
                    
                    # If not found, try wildcards directory
                    if not file_path.exists():
                        wildcard_dir = self._get_wildcard_dir()
                        if wildcard_dir:
                            wildcard_path = wildcard_dir / preset_file
                            if wildcard_path.exists():
                                file_path = wildcard_path
            else:
                file_path = preset_file
            
            if not file_path.exists():
                print(f"[Prompt Preset Selector] Warning: Preset file not found: {file_path}")
                return []
            
            suffix = file_path.suffix.lower()
            
            # Handle YAML files
            if suffix in ['.yaml', '.yml']:
                if not YAML_AVAILABLE:
                    print(f"[Prompt Preset Selector] Error: PyYAML not installed. Cannot load {file_path.name}")
                    return []
                
                return self.load_yaml_presets(file_path)
            
            # Handle TXT files
            elif suffix == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = []
                    for line in f:
                        stripped = line.strip()
                        if stripped and not stripped.startswith('#'):
                            lines.append(stripped)
                    return lines
            
            else:
                print(f"[Prompt Preset Selector] Warning: Unsupported file format: {suffix}")
                return []
                
        except Exception as e:
            print(f"[Prompt Preset Selector] Error loading preset file {preset_file}: {e}")
            return []
    
    def load_yaml_presets(self, file_path):
        """
        Load presets from YAML file, supporting multiple formats:
        - Format A: List under 'presets' key
        - Format B: Flat list at root
        - Format C: Nested dictionary structure (keys prepended to text)
        
        Returns list of strings (for dict format, includes "key1:key2: text" format)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if data is None:
                return []
            
            # Format A: {'presets': [...]}
            if isinstance(data, dict) and 'presets' in data:
                presets = data['presets']
                if isinstance(presets, list):
                    return [str(item) for item in presets if item]
            
            # Format B: Direct list [...]
            if isinstance(data, list):
                return [str(item) for item in data if item]
            
            # Format C: Nested dictionary structure
            if isinstance(data, dict):
                return self.flatten_yaml_dict(data)
            
            return []
            
        except Exception as e:
            print(f"[Prompt Preset Selector] Error parsing YAML: {e}")
            return []
    
    def flatten_yaml_dict(self, data, parent_keys=[]):
        """
        Recursively flatten nested dictionary into list of preset strings with key prefix
        Format: "key1:key2:key3: preset_text"
        
        Example:
            {'camera_angles': {'close_up': ['front view', 'back view']}}
            -> ['camera_angles:close_up: front view', 
                'camera_angles:close_up: back view']
        """
        lines = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_keys = parent_keys + [key]
                
                if isinstance(value, list):
                    # List of presets - prepend key hierarchy
                    key_prefix = ":".join(current_keys) + ": "
                    for item in value:
                        if item:
                            lines.append(key_prefix + str(item))
                elif isinstance(value, dict):
                    # Nested dict, recurse with accumulated keys
                    lines.extend(self.flatten_yaml_dict(value, current_keys))
                elif isinstance(value, str):
                    # Single string value
                    key_prefix = ":".join(current_keys) + ": "
                    lines.append(key_prefix + value)
        
        return lines
    
    def parse_keywords(self, keyword_string):
        """
        Parse keyword string into phrases and individual keywords, including exclusions
        Examples:
          'front, "low-angle shot"' -> (['front', 'low-angle shot'], [])
          'front -wide -medium' -> (['front'], ['wide', 'medium'])
          '"front view" -"medium shot"' -> (['front view'], ['medium shot'])
        
        Returns: (include_keywords, exclude_keywords)
        """
        if not keyword_string.strip():
            return ([], [])
        
        include_keywords = []
        exclude_keywords = []
        
        # Match quoted phrases or individual words, with optional minus prefix
        pattern = r'(-?)"([^"]+)"|(-?)([^,\s]+)'
        matches = re.findall(pattern, keyword_string)
        
        for minus1, phrase, minus2, word in matches:
            is_exclude = (minus1 == '-' or minus2 == '-')
            
            if phrase:  # Quoted phrase
                keyword = phrase
            elif word:  # Individual word
                keyword = word
            else:
                continue
            
            if is_exclude:
                exclude_keywords.append(keyword)
            else:
                include_keywords.append(keyword)
        
        return (include_keywords, exclude_keywords)
    
    def filter_by_keywords(self, lines, include_keywords, exclude_keywords, mode):
        """
        Filter lines based on include/exclude keywords and mode (AND/OR)
        
        Process:
        1. Filter by include keywords (if any) using AND/OR mode
        2. Remove lines matching any exclude keyword (always applied)
        
        Returns:
            List of tuples: [(original_index, line_text), ...]
        """
        if not include_keywords and not exclude_keywords:
            return [(i, line) for i, line in enumerate(lines)]
        
        # Step 1: Apply inclusion filter
        if include_keywords and mode != "OFF":
            filtered = []
            for i, line in enumerate(lines):
                line_lower = line.lower()
                keyword_matches = [kw.lower() in line_lower for kw in include_keywords]
                
                if mode == "AND":
                    if all(keyword_matches):
                        filtered.append((i, line))
                elif mode == "OR":
                    if any(keyword_matches):
                        filtered.append((i, line))
        else:
            # No include keywords or mode is OFF, start with all lines
            filtered = [(i, line) for i, line in enumerate(lines)]
        
        # Step 2: Apply exclusion filter (always applied if exclusions exist)
        if exclude_keywords:
            result = []
            for i, line in filtered:
                line_lower = line.lower()
                # Exclude if line contains ANY of the exclude keywords
                has_exclude = any(kw.lower() in line_lower for kw in exclude_keywords)
                if not has_exclude:
                    result.append((i, line))
            return result
        
        return filtered
    
    def generate_preset_list(self, lines):
        """Generate numbered list of all presets"""
        if not lines:
            return "(No presets available)"
        
        result = []
        for i, line in enumerate(lines):
            result.append(f"{i}: {line}")
        return "\n".join(result)
    
    def strip_key_hierarchy(self, text):
        """
        Remove YAML key hierarchy prefix from preset text
        Examples:
          "camera_angles:close_up: front view" -> "front view"
          "lighting: golden hour" -> "golden hour"
          "no keys here" -> "no keys here"
        """
        # Find the last occurrence of ": " which separates keys from content
        # Keys are in format "key1:key2:key3: content"
        parts = text.split(': ', 1)
        if len(parts) == 2:
            # Check if the first part looks like key hierarchy (contains : or is single word)
            key_part = parts[0]
            if ':' in key_part or (key_part and not ' ' in key_part):
                # This looks like "key:" or "key1:key2:", return the content part
                return parts[1]
        
        # No key hierarchy found, return as-is
        return text
    
    def select_preset(self, preset_file, absolute_path, keyword, keyword_mode, selection_mode, preset_index, seed):
        """Main selection logic with support for absolute paths"""
        
        # Determine which file to use: absolute_path takes priority
        if absolute_path and absolute_path.strip():
            # Use absolute path
            file_to_load = absolute_path.strip()
            file_identifier = file_to_load  # For state key
            
            # Validate file exists
            if not os.path.exists(file_to_load):
                error_msg = f"Absolute path not found: {file_to_load}"
                print(f"[Prompt Preset Selector] Error: {error_msg}")
                return ("", "", error_msg)
            
            # Validate file extension
            if not file_to_load.lower().endswith(('.txt', '.yaml', '.yml')):
                error_msg = f"Unsupported file type. Use .txt, .yaml, or .yml: {file_to_load}"
                print(f"[Prompt Preset Selector] Error: {error_msg}")
                return ("", "", error_msg)
        else:
            # Use preset_file from dropdown
            if preset_file == "(No preset files found)":
                print("[Prompt Preset Selector] Warning: No preset files available")
                return ("", "(No preset files found)", "")
            
            file_to_load = preset_file
            file_identifier = preset_file
        
        # Load all presets (unfiltered)
        all_lines = self.load_preset_lines(file_to_load)
        if not all_lines:
            print(f"[Prompt Preset Selector] Warning: Preset file '{file_identifier}' is empty or failed to load")
            return ("", "(File is empty or failed to load)", "")
        
        # Generate full preset list (for reference)
        preset_list = self.generate_preset_list(all_lines)
        
        # Parse and apply keyword filtering
        include_keywords, exclude_keywords = self.parse_keywords(keyword)
        filtered_items = self.filter_by_keywords(all_lines, include_keywords, exclude_keywords, keyword_mode)
        
        # Check if filtering resulted in empty list
        if not filtered_items:
            warning = f"No presets match keywords: {keyword}"
            print(f"[Prompt Preset Selector] Warning: {warning}")
            return ("", preset_list, warning)
        
        # State key for Sequential (continue) mode
        state_key = f"{file_identifier}_{keyword}_{keyword_mode}"
        
        # Selection based on mode
        selected_text = ""
        selected_index = 0  # Index in filtered list
        original_index = 0  # Index in original list
        
        if selection_mode == "Manual":
            # Use preset_index directly on filtered list
            selected_index = preset_index % len(filtered_items)
            original_index, selected_text = filtered_items[selected_index]
            print(f"[Prompt Preset Selector] Manual: index={preset_index} -> {selected_text}")
        
        elif selection_mode == "Sequential":
            # Start from preset_index each time
            selected_index = preset_index % len(filtered_items)
            original_index, selected_text = filtered_items[selected_index]
            print(f"[Prompt Preset Selector] Sequential (from {preset_index}): index={selected_index} -> {selected_text}")
        
        elif selection_mode == "Sequential (continue)":
            # Continue from last position, or start from preset_index
            if state_key not in self._continue_state:
                self._continue_state[state_key] = preset_index % len(filtered_items)
            
            selected_index = self._continue_state[state_key]
            original_index, selected_text = filtered_items[selected_index]
            
            # Advance to next position for next execution
            self._continue_state[state_key] = (selected_index + 1) % len(filtered_items)
            print(f"[Prompt Preset Selector] Sequential (continue): index={selected_index} -> {selected_text}")
        
        elif selection_mode == "Random":
            # Random selection with seed
            random.seed(seed)
            selected_index = random.randint(0, len(filtered_items) - 1)
            original_index, selected_text = filtered_items[selected_index]
            print(f"[Prompt Preset Selector] Random (seed={seed}): index={selected_index} -> {selected_text}")
        
        # Info output shows selection details with ORIGINAL index
        info = f"Selected: {original_index}: {selected_text}\nMode: {selection_mode}\nFiltered: {len(filtered_items)}/{len(all_lines)} presets"
        
        # Strip key hierarchy from text output (for actual prompt use)
        # Keep full text with keys in preset_list and info (for reference)
        output_text = self.strip_key_hierarchy(selected_text)
        
        return (output_text, preset_list, info)


class PromptPresetSelectorWithWildcard(PromptPresetSelector):
    """
    Enhanced preset selector with wildcard expansion support
    Supports {A|B|C} syntax and __filename__ file references
    Also supports Impact Pack style {__key__|__key__} YAML key selection
    """
    
    # Default wildcard directory (shared with ComfyUI-Impact-Pack)
    DEFAULT_WILDCARD_DIR = "../ComfyUI-Impact-Pack/wildcards"
    
    # Class variable to track wildcard state for sequential mode
    _wildcard_state = {}
    
    def __init__(self):
        super().__init__()
        # Set up wildcard directory
        self.wildcard_dir = self._get_wildcard_dir()
        # Cache for YAML structure (for key-based wildcards)
        self._yaml_structure_cache = {}
    
    def _get_wildcard_dir(self):
        """Get the wildcard directory path"""
        base_dir = Path(__file__).parent
        wildcard_path = base_dir / self.DEFAULT_WILDCARD_DIR
        
        # Normalize path
        try:
            wildcard_path = wildcard_path.resolve()
            if wildcard_path.exists():
                return wildcard_path
            else:
                print(f"[Wildcard Preset Selector] Warning: Wildcard directory not found: {wildcard_path}")
                return None
        except Exception as e:
            print(f"[Wildcard Preset Selector] Error resolving wildcard path: {e}")
            return None
    
    def load_yaml_structure(self, file_path):
        """
        Load YAML file and preserve its structure for key-based wildcards
        Caches the structure for reuse
        """
        file_path_str = str(file_path)
        
        # Check cache first
        if file_path_str in self._yaml_structure_cache:
            return self._yaml_structure_cache[file_path_str]
        
        if not YAML_AVAILABLE:
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if data is None:
                return None
            
            # Cache the structure
            self._yaml_structure_cache[file_path_str] = data
            return data
            
        except Exception as e:
            print(f"[Wildcard Preset Selector] Error loading YAML structure: {e}")
            return None
    
    def get_yaml_key_content(self, yaml_data, key):
        """
        Get content from a YAML key - FIXED to handle nested structures
        Returns a list of items under that key, searching recursively
        """
        if not yaml_data:
            return []
        
        # First try to find the key at the top level
        if isinstance(yaml_data, dict) and key in yaml_data:
            content = yaml_data[key]
            return self._extract_content_from_value(content)
        
        # If not found at top level, search recursively
        if isinstance(yaml_data, dict):
            for k, v in yaml_data.items():
                if k == key:
                    return self._extract_content_from_value(v)
                # Recursively search in nested dicts
                if isinstance(v, dict):
                    result = self.get_yaml_key_content(v, key)
                    if result:
                        return result
        
        return []
    
    def _extract_content_from_value(self, content):
        """
        Extract content from a YAML value (list, dict, or string)
        Returns a flat list of strings
        """
        if isinstance(content, list):
            # Simple list - return as is
            return [str(item) for item in content if item]
        
        if isinstance(content, dict):
            # Dict - flatten all values recursively
            result = []
            for sub_key, sub_value in content.items():
                result.extend(self._extract_content_from_value(sub_value))
            return result
        
        # Single value
        return [str(content)] if content else []
    
    @classmethod
    def INPUT_TYPES(cls):
        instance = cls()
        preset_files = instance.get_preset_files()
        
        if not preset_files:
            preset_files = ["(No preset files found)"]
        
        return {
            "required": {
                "preset_file": (preset_files,),
                "absolute_path": ("STRING", {"default": "", "multiline": False, "placeholder": "Optional: /absolute/path/to/file.txt or .yaml"}),
                "keyword": ("STRING", {"default": "", "multiline": False}),
                "keyword_mode": (["OFF", "AND", "OR"], {"default": "OFF"}),
                "selection_mode": (["Manual", "Sequential", "Sequential (continue)", "Random"], {"default": "Manual"}),
                "preset_index": ("INT", {"default": 0, "min": 0, "max": 9999, "step": 1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "enable_wildcard": ("BOOLEAN", {"default": True}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("text", "preset_list", "selected_info")
    FUNCTION = "select_preset_with_wildcard"
    CATEGORY = "text"
    
    @classmethod
    def IS_CHANGED(cls, preset_file, absolute_path, keyword, keyword_mode, selection_mode, preset_index, seed, enable_wildcard):
        return f"{preset_file}_{absolute_path}_{keyword}_{keyword_mode}_{selection_mode}_{preset_index}_{seed}_{enable_wildcard}"
    
    def expand_wildcards(self, text, seed, selection_mode, state_key="", current_file=None):
        """
        Expand wildcard syntax in text - FIXED to recursively expand
        - {A|B|C} -> choice from A, B, C (random or sequential)
        - __filename__ -> line from wildcards/filename.txt (random or sequential)
        - {__key__|__key__} -> content from YAML keys in current file (Impact Pack style)
        - Supports nesting: {A|{B|C}}
        
        selection_mode determines behavior:
        - Sequential / Sequential (continue): cycle through options in order
        - Random / Manual: random selection based on seed
        """
        if not text:
            return text
        
        # Determine if we should use sequential selection
        is_sequential = selection_mode in ["Sequential", "Sequential (continue)"]
        
        if is_sequential:
            # For sequential mode, use state_key to track position
            if not hasattr(self, '_wildcard_state'):
                self._wildcard_state = {}
        else:
            # For random/manual mode, use seed
            random.seed(seed)
        
        # FIXED: Recursively expand wildcards until no more wildcards remain
        max_depth = 10  # Prevent infinite loops
        depth = 0
        
        while depth < max_depth:
            original_text = text
            
            # First, expand YAML key-based wildcards {__key__|__key__}
            text = self._expand_yaml_key_wildcards(text, is_sequential, state_key, current_file)
            
            # Process __filename__ wildcards
            text = self._expand_file_wildcards(text, is_sequential, state_key)
            
            # Process {A|B|C} wildcards with nesting support
            text = self._expand_choice_wildcards(text, is_sequential, state_key)
            
            # If nothing changed, we're done
            if text == original_text:
                break
            
            depth += 1
        
        if depth >= max_depth:
            print(f"[Wildcard Preset Selector] Warning: Maximum recursion depth reached")
        
        return text
    
    def _expand_yaml_key_wildcards(self, text, is_sequential, state_key, current_file):
        """
        Expand Impact Pack style {__key__|__key__} wildcards
        Selects content from YAML keys in the current file
        """
        if not current_file:
            return text
        
        # Load YAML structure
        yaml_data = self.load_yaml_structure(current_file)
        if not yaml_data:
            return text
        
        # Pattern: {__key1__|__key2__|...}
        # Match {...} containing __key__ patterns
        pattern = r'\{(__[^}]+__(?:\|__[^}]+__)*)\}'
        
        def replace_yaml_key(match):
            keys_str = match.group(1)
            # Extract individual __key__ patterns
            # Support all characters except __, |, {, }
            keys = re.findall(r'__(.+?)__', keys_str)
            
            if not keys:
                return match.group(0)
            
            # Collect all possible choices from all keys
            all_choices = []
            for key in keys:
                key_content = self.get_yaml_key_content(yaml_data, key)
                all_choices.extend(key_content)
            
            if not all_choices:
                print(f"[Wildcard Preset Selector] Warning: No content found for YAML keys: {keys}")
                return match.group(0)
            
            # Select based on mode
            if is_sequential:
                # Sequential: cycle through all choices
                wc_state_key = f"{state_key}_yamlkey_{keys_str}"
                if wc_state_key not in self._wildcard_state:
                    self._wildcard_state[wc_state_key] = 0
                
                index = self._wildcard_state[wc_state_key] % len(all_choices)
                selected = all_choices[index]
                
                # Advance position
                self._wildcard_state[wc_state_key] = (index + 1) % len(all_choices)
                return selected
            else:
                # Random selection
                return random.choice(all_choices)
        
        return re.sub(pattern, replace_yaml_key, text)
    
    def _expand_file_wildcards(self, text, is_sequential, state_key):
        """
        Expand __filename__ wildcards by reading from wildcard files
        Searches in:
        1. presets directory
        2. wildcards directory (Impact Pack)
        """
        # Pattern: __filename__
        pattern = r'__([a-zA-Z0-9_-]+)__'
        
        def replace_file_wildcard(match):
            filename = match.group(1)
            filepath = None
            
            # Try presets directory first
            preset_path = self.preset_dir / f"{filename}.txt"
            if preset_path.exists():
                filepath = preset_path
            # Then try wildcards directory
            elif self.wildcard_dir:
                wildcard_path = self.wildcard_dir / f"{filename}.txt"
                if wildcard_path.exists():
                    filepath = wildcard_path
            
            if not filepath:
                print(f"[Wildcard Preset Selector] Warning: Wildcard file not found: {filename}.txt")
                return match.group(0)  # Return original if file not found
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
                if not lines:
                    print(f"[Wildcard Preset Selector] Warning: Wildcard file is empty: {filepath}")
                    return match.group(0)
                
                # Select line based on mode
                if is_sequential:
                    # Sequential: cycle through lines
                    wc_state_key = f"{state_key}_file_{filename}"
                    if wc_state_key not in self._wildcard_state:
                        self._wildcard_state[wc_state_key] = 0
                    
                    index = self._wildcard_state[wc_state_key] % len(lines)
                    selected = lines[index]
                    
                    # Advance position for next execution
                    self._wildcard_state[wc_state_key] = (index + 1) % len(lines)
                    return selected
                else:
                    # Random selection from file
                    return random.choice(lines)
                
            except Exception as e:
                print(f"[Wildcard Preset Selector] Error reading wildcard file {filepath}: {e}")
                return match.group(0)
        
        return re.sub(pattern, replace_file_wildcard, text)
    
    def _expand_choice_wildcards(self, text, is_sequential, state_key):
        """Expand {A|B|C} wildcards with nesting support"""
        max_iterations = 100  # Prevent infinite loops
        iteration = 0
        choice_counter = 0  # Track which choice wildcard we're processing
        
        while '{' in text and '|' in text and iteration < max_iterations:
            # Find innermost {...} block
            # Pattern: find {...} that doesn't contain another {
            pattern = r'\{([^{}]+)\}'
            match = re.search(pattern, text)
            
            if not match:
                break
            
            content = match.group(1)
            
            # Split by | and choose
            if '|' in content:
                choices = [c.strip() for c in content.split('|')]
                
                if is_sequential:
                    # Sequential: cycle through choices
                    wc_state_key = f"{state_key}_choice_{choice_counter}"
                    if wc_state_key not in self._wildcard_state:
                        self._wildcard_state[wc_state_key] = 0
                    
                    index = self._wildcard_state[wc_state_key] % len(choices)
                    selected = choices[index]
                    
                    # Advance position for next execution
                    self._wildcard_state[wc_state_key] = (index + 1) % len(choices)
                else:
                    # Random selection
                    selected = random.choice(choices)
                
                text = text[:match.start()] + selected + text[match.end():]
                choice_counter += 1
            else:
                # No | found, just remove braces
                text = text[:match.start()] + content + text[match.end():]
            
            iteration += 1
        
        if iteration >= max_iterations:
            print(f"[Wildcard Preset Selector] Warning: Max iterations reached in wildcard expansion")
        
        return text
    
    def select_preset_with_wildcard(self, preset_file, absolute_path, keyword, keyword_mode, selection_mode, preset_index, seed, enable_wildcard):
        """Main selection logic with wildcard expansion support"""
        
        # First, use parent class to select preset
        text, preset_list, info = self.select_preset(
            preset_file, absolute_path, keyword, keyword_mode, 
            selection_mode, preset_index, seed
        )
        
        # Determine which file is being used (for YAML key wildcards)
        if absolute_path and absolute_path.strip():
            current_file = Path(absolute_path.strip())
        else:
            # Need to find the actual file location (presets or wildcards)
            if preset_file != "(No preset files found)":
                # Try presets directory first
                preset_path = self.preset_dir / preset_file
                if preset_path.exists():
                    current_file = preset_path
                else:
                    # Try wildcards directory
                    wildcard_dir = self._get_wildcard_dir()
                    if wildcard_dir:
                        wildcard_path = wildcard_dir / preset_file
                        if wildcard_path.exists():
                            current_file = wildcard_path
                        else:
                            current_file = None
                    else:
                        current_file = None
            else:
                current_file = None
        
        # Then expand wildcards if enabled
        if enable_wildcard and text and current_file:
            original_text = text
            
            # Create state key for sequential wildcard tracking
            file_identifier = str(current_file)
            state_key = f"{file_identifier}_{keyword}_{keyword_mode}_wildcard"
            
            # Expand wildcards with mode awareness and current file context
            text = self.expand_wildcards(text, seed, selection_mode, state_key, current_file)
            
            # Update info if wildcards were expanded
            if text != original_text:
                mode_info = "sequential" if selection_mode in ["Sequential", "Sequential (continue)"] else "random"
                info += f"\n[Wildcards expanded: {mode_info}]"
        
        return (text, preset_list, info)


class PromptPresetSelectorWithImage(PromptPresetSelectorWithWildcard):
    """
    Enhanced preset selector with image selection support
    Images are linked to YAML keys using [folder] syntax: "key_name[image_folder]"
    """

    # Set to True to print verbose tracing of image folder lookup and YAML
    # key traversal to the ComfyUI console. Off by default.
    DEBUG = False
    
    def __init__(self):
        super().__init__()
        self.images_dir = self.preset_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
    
    @classmethod
    def INPUT_TYPES(cls):
        instance = cls()
        preset_files = instance.get_preset_files()
        
        if not preset_files:
            preset_files = ["(No preset files found)"]
        
        return {
            "required": {
                "preset_file": (preset_files,),
                "absolute_path": ("STRING", {"default": "", "multiline": False, "placeholder": "Optional: /absolute/path/to/file.yaml"}),
                "keyword": ("STRING", {"default": "", "multiline": False}),
                "keyword_mode": (["OFF", "AND", "OR"], {"default": "OFF"}),
                "selection_mode": (["Manual", "Sequential", "Sequential (continue)", "Random"], {"default": "Manual"}),
                "preset_index": ("INT", {"default": 0, "min": 0, "max": 9999, "step": 1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "enable_wildcard": ("BOOLEAN", {"default": True}),
                # Image selection parameter
                "image_index": ("INT", {"default": 0, "min": 0, "max": 9999, "step": 1}),
            }
        }
    
    RETURN_TYPES = ("STRING", "IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("text", "image", "image_path", "preset_list", "selected_info")
    FUNCTION = "select_preset_with_image"
    CATEGORY = "promptPresetSelector"
    
    @classmethod
    def IS_CHANGED(cls, preset_file, absolute_path, keyword, keyword_mode, selection_mode, 
                   preset_index, seed, enable_wildcard, image_index):
        """Determines if the node output should be recalculated."""
        return f"{preset_file}_{absolute_path}_{keyword}_{keyword_mode}_{selection_mode}_{preset_index}_{seed}_{enable_wildcard}_{image_index}"
    
    def parse_image_folder_from_key(self, key_text):
        """
        Extract image folder name from key text
        Format: "key_name[folder_name]"
        Returns: (clean_key, folder_name or None)
        
        Examples:
        "heroes[hero_poses]" -> ("heroes", "hero_poses")
        "villains" -> ("villains", None)
        """
        pattern = r'^(.+?)\[(.+?)\]$'
        match = re.match(pattern, key_text)
        
        if match:
            clean_key = match.group(1).strip()
            folder_name = match.group(2).strip()
            return (clean_key, folder_name)
        else:
            return (key_text, None)
    
    def get_image_files(self, folder_name):
        """
        Get list of image files from specified folder
        Returns: list of Path objects, or empty list if folder doesn't exist
        """
        if not folder_name:
            return []
        
        folder_path = self.images_dir / folder_name
        
        if not folder_path.exists():
            print(f"[Prompt Preset Selector] Warning: Image folder not found: {folder_path}")
            return []
        
        # Supported image formats (case-insensitive on Windows, matches both on Linux/Mac)
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.webp', '*.PNG', '*.JPG', '*.JPEG', '*.WEBP']
        
        image_files = set()  # Use set to avoid duplicates
        for pattern in image_extensions:
            image_files.update(folder_path.glob(pattern))
        
        if not image_files:
            print(f"[Prompt Preset Selector] Warning: No images found in folder: {folder_path}")
            return []
        
        sorted_files = sorted(image_files)
        
        if self.DEBUG: print(f"[DEBUG FILES] Folder: {folder_name}, Total files: {len(sorted_files)}")
        if self.DEBUG: print(f"[DEBUG FILES] File list: {[f.name for f in sorted_files]}")
        
        return sorted_files
    
    def select_image(self, image_files, image_index):
        """
        Select an image from the list using image_index
        Returns: selected image Path or None
        """
        if not image_files:
            return None
        
        # Use modulo to wrap around
        index = image_index % len(image_files)
        
        if self.DEBUG: print(f"[DEBUG IMAGE SELECT] image_index={image_index}, total_files={len(image_files)}, calculated_index={index}")
        if self.DEBUG: print(f"[DEBUG IMAGE SELECT] Selected: {image_files[index].name}")
        
        return image_files[index]
    
    def load_image_as_tensor(self, image_path):
        """
        Load image file and convert to ComfyUI tensor format
        Returns: torch.Tensor in shape (1, H, W, 3) with values 0-1
        """
        try:
            img = Image.open(image_path).convert('RGB')
            img_array = np.array(img).astype(np.float32) / 255.0
            img_tensor = torch.from_numpy(img_array)[None,]  # Add batch dimension
            return img_tensor
        except Exception as e:
            print(f"[Prompt Preset Selector] Error loading image {image_path}: {e}")
            return self.create_black_image()
    
    def create_black_image(self):
        """
        Create a 1x1 black image tensor
        Returns: torch.Tensor in shape (1, 1, 1, 3)
        """
        return torch.zeros((1, 1, 1, 3), dtype=torch.float32)
    
    def load_preset_lines_with_image_info(self, preset_file):
        """
        Load preset lines and extract image folder information
        Returns: list of tuples (line_text, image_folder)
        
        Example:
        Input YAML:
            heroes[hero_poses]:
              - superman, cape
        
        Returns:
            [("heroes: superman, cape", "hero_poses")]
        """
        # First, get regular preset lines
        lines = self.load_preset_lines(preset_file)
        
        if self.DEBUG: print(f"[DEBUG] Total lines loaded: {len(lines)}")
        if lines:
            if self.DEBUG: print(f"[DEBUG] First 3 lines: {lines[:3]}")
        
        # Then, extract image folder info from lines
        lines_with_images = []
        
        for line in lines:
            # Check if line contains key hierarchy (from nested YAML)
            # Format: "key1:key2: text" or "key1:key2[folder]: text"
            if ':' in line:
                parts = line.split(':', 2)
                
                image_folder = None
                clean_parts = []
                
                # Check each part for [folder] syntax
                for i, part in enumerate(parts[:-1]):  # Don't check the last part (actual text)
                    part = part.strip()
                    clean_key, folder = self.parse_image_folder_from_key(part)
                    clean_parts.append(clean_key)
                    
                    # Use the first folder found
                    if folder and not image_folder:
                        image_folder = folder
                        if self.DEBUG: print(f"[DEBUG] Found image folder '{folder}' in key '{part}'")
                
                # Reconstruct line with clean keys
                if len(parts) == 2:
                    clean_line = f"{':'.join(clean_parts)}: {parts[-1]}"
                else:
                    clean_line = f"{':'.join(clean_parts)}: {parts[-1]}"
                
                lines_with_images.append((clean_line, image_folder))
                if self.DEBUG: print(f"[DEBUG] Processed: '{line}' -> clean_line='{clean_line}', folder='{image_folder}'")
            else:
                lines_with_images.append((line, None))
        
        if self.DEBUG: print(f"[DEBUG] Lines with image info: {len(lines_with_images)}")
        if lines_with_images:
            if self.DEBUG: print(f"[DEBUG] First line with image: {lines_with_images[0]}")
        
        return lines_with_images
    
    def get_image_folder_from_yaml_keys(self, file_path, selected_line):
        """
        Extract image folder from YAML keys by reading the original YAML structure
        
        Args:
            file_path: Path to YAML file
            selected_line: Selected preset line (e.g., "sfw:test: red dress")
        
        Returns:
            Image folder name or None
        """
        if not YAML_AVAILABLE:
            if self.DEBUG: print("[DEBUG YAML] PyYAML not available")
            return None
        
        if self.DEBUG: print(f"[DEBUG YAML] Processing line: '{selected_line}'")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            
            if self.DEBUG: print(f"[DEBUG YAML] YAML data keys: {list(yaml_data.keys()) if isinstance(yaml_data, dict) else 'not a dict'}")
            
            if not isinstance(yaml_data, dict):
                if self.DEBUG: print("[DEBUG YAML] YAML data is not a dict")
                return None
            
            # Extract key path from selected line
            # Format: "key1:key2: content"
            if ':' not in selected_line:
                if self.DEBUG: print("[DEBUG YAML] No ':' in selected line")
                return None
            
            parts = selected_line.split(': ')
            if self.DEBUG: print(f"[DEBUG YAML] Split parts: {parts}")
            
            if len(parts) < 2:
                if self.DEBUG: print("[DEBUG YAML] Less than 2 parts")
                return None
            
            # Get the key hierarchy (everything before the last ": ")
            # Join all parts except the last one (which is the content)
            key_parts = parts[:-1]
            key_path = ':'.join(key_parts)
            if self.DEBUG: print(f"[DEBUG YAML] Key path: '{key_path}'")
            
            keys = key_path.split(':')
            if self.DEBUG: print(f"[DEBUG YAML] Keys to traverse: {keys}")
            
            # Navigate through YAML structure
            current = yaml_data
            for i, key in enumerate(keys):
                if self.DEBUG: print(f"[DEBUG YAML] Level {i}: Looking for key '{key}' in {list(current.keys()) if isinstance(current, dict) else 'not a dict'}")
                
                if not isinstance(current, dict):
                    if self.DEBUG: print(f"[DEBUG YAML] Current level is not a dict")
                    return None
                
                # Try to find matching key (with or without [folder])
                matching_key = None
                for yaml_key in current.keys():
                    clean_key, folder = self.parse_image_folder_from_key(str(yaml_key))
                    if self.DEBUG: print(f"[DEBUG YAML]   Checking yaml_key='{yaml_key}' -> clean_key='{clean_key}', folder='{folder}'")
                    if clean_key == key:
                        matching_key = yaml_key
                        if self.DEBUG: print(f"[DEBUG YAML]   MATCH! Using key '{yaml_key}'")
                        break
                
                if matching_key is None:
                    if self.DEBUG: print(f"[DEBUG YAML] No matching key found for '{key}'")
                    return None
                
                # Check if this key has [folder] syntax
                _, image_folder = self.parse_image_folder_from_key(str(matching_key))
                if image_folder:
                    if self.DEBUG: print(f"[DEBUG YAML] Found image folder: '{image_folder}'")
                    return image_folder
                
                # Move to next level
                current = current[matching_key]
                if self.DEBUG: print(f"[DEBUG YAML] Moving to next level, type: {type(current)}")
            
            if self.DEBUG: print("[DEBUG YAML] Traversed all keys, no folder found")
            return None
            
        except Exception as e:
            print(f"[Prompt Preset Selector] Error reading YAML for image folder: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def select_preset_with_image(self, preset_file, absolute_path, keyword, keyword_mode, 
                                 selection_mode, preset_index, seed, enable_wildcard, image_index):
        """
        Main selection logic with image support
        Returns: (text, image, image_path, preset_list, selected_info)
        """
        
        # Determine file path
        if absolute_path and absolute_path.strip():
            file_to_load = absolute_path.strip()
        else:
            file_to_load = preset_file
        
        # Convert to full path if not absolute
        if not os.path.isabs(file_to_load):
            # Try presets directory first
            file_path_obj = self.preset_dir / file_to_load
            if file_path_obj.exists():
                file_to_load_full = str(file_path_obj)
            else:
                # Try wildcards directory
                wildcard_dir = self._get_wildcard_dir()
                if wildcard_dir:
                    wildcard_path = wildcard_dir / file_to_load
                    if wildcard_path.exists():
                        file_to_load_full = str(wildcard_path)
                    else:
                        file_to_load_full = str(file_path_obj)  # Use presets path even if not exists
                else:
                    file_to_load_full = str(file_path_obj)
        else:
            file_to_load_full = file_to_load
        
        # Get filtered lines (before wildcard expansion)
        filtered_lines_raw = self.load_preset_lines(file_to_load)
        
        if keyword_mode != "OFF" and keyword:
            include_keywords, exclude_keywords = self.parse_keywords(keyword)
            filtered_lines_raw = self.filter_by_keywords(filtered_lines_raw, include_keywords, exclude_keywords, keyword_mode)
        
        # Determine selected index (replicate parent class logic)
        if not filtered_lines_raw:
            selected_raw_index = 0
            selected_raw_line = ""
        elif selection_mode == "Manual":
            selected_raw_index = preset_index % len(filtered_lines_raw)
            selected_raw_line = filtered_lines_raw[selected_raw_index]
        elif selection_mode == "Sequential":
            selected_raw_index = preset_index % len(filtered_lines_raw)
            selected_raw_line = filtered_lines_raw[selected_raw_index]
        elif selection_mode == "Sequential (continue)":
            state_key = f"{file_to_load}_{keyword}_{keyword_mode}"
            if state_key not in self._continue_state:
                self._continue_state[state_key] = preset_index
            selected_raw_index = self._continue_state[state_key] % len(filtered_lines_raw)
            selected_raw_line = filtered_lines_raw[selected_raw_index]
        elif selection_mode == "Random":
            random.seed(seed)
            selected_raw_index = random.randint(0, len(filtered_lines_raw) - 1)
            selected_raw_line = filtered_lines_raw[selected_raw_index]
        else:
            selected_raw_index = 0
            selected_raw_line = filtered_lines_raw[0] if filtered_lines_raw else ""
        
        # Extract image folder from YAML keys
        # First, clean the selected line by removing [folder] from keys
        if ':' in selected_raw_line:
            line_parts = selected_raw_line.split(': ')
            if len(line_parts) >= 2:
                # Clean each key part
                key_parts = line_parts[:-1]  # All parts except the content
                cleaned_key_parts = []
                for part in key_parts:
                    key_components = part.split(':')
                    cleaned_components = []
                    for component in key_components:
                        clean_comp, _ = self.parse_image_folder_from_key(component.strip())
                        cleaned_components.append(clean_comp)
                    cleaned_key_parts.append(':'.join(cleaned_components))
                
                # Reconstruct cleaned line
                cleaned_line = ':'.join(cleaned_key_parts) + ': ' + line_parts[-1]
            else:
                cleaned_line = selected_raw_line
        else:
            cleaned_line = selected_raw_line
        
        if self.DEBUG: print(f"[DEBUG] Original raw line: '{selected_raw_line}'")
        if self.DEBUG: print(f"[DEBUG] Cleaned line for YAML search: '{cleaned_line}'")
        
        selected_image_folder = self.get_image_folder_from_yaml_keys(file_to_load_full, cleaned_line)
        
        if self.DEBUG: print(f"[DEBUG] Image folder from YAML keys: {selected_image_folder}")
        
        # Now get the expanded text from parent class
        text, preset_list, info = self.select_preset_with_wildcard(
            preset_file, absolute_path, keyword, keyword_mode,
            selection_mode, preset_index, seed, enable_wildcard
        )
        
        if self.DEBUG: print(f"[DEBUG] Selected image folder: {selected_image_folder}")
        
        # Select image
        if selected_image_folder:
            image_files = self.get_image_files(selected_image_folder)
            
            if image_files:
                selected_image_path = self.select_image(image_files, image_index)
                image_number = (image_index % len(image_files)) + 1
                
                image_tensor = self.load_image_as_tensor(selected_image_path)
                image_path_str = str(selected_image_path)
                
                image_info = f"\nSelected Image: {selected_image_path.name} ({image_number}/{len(image_files)})"
                image_info += f" [index={image_index}]"
                info += image_info
            else:
                image_tensor = self.create_black_image()
                image_path_str = "No image"
                info += f"\nSelected Image: None (folder '{selected_image_folder}' is empty)"
        else:
            image_tensor = self.create_black_image()
            image_path_str = "No image"
            info += "\nSelected Image: None (no image folder specified)"
        
        return (text, image_tensor, image_path_str, preset_list, info)


# Register the node
NODE_CLASS_MAPPINGS = {
    "PromptPresetSelector": PromptPresetSelector,
    "PromptPresetSelectorWithWildcard": PromptPresetSelectorWithWildcard,
    "PromptPresetSelectorWithImage": PromptPresetSelectorWithImage
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptPresetSelector": "Prompt Preset Selector",
    "PromptPresetSelectorWithWildcard": "Prompt Preset Selector (Wildcard)",
    "PromptPresetSelectorWithImage": "Prompt Preset Selector (Image)"
}
