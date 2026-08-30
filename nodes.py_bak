"""
Prompt Preset Selector Node for ComfyUI (Enhanced Version)
Allows selection of text presets from external .txt and .yaml files with:
- Sequential and random selection modes
- Keyword filtering with AND/OR/phrase search
- Preset list display for easy reference
- Absolute path support
"""

import os
import random
import re
from pathlib import Path
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
    
    def get_preset_files(self):
        """Get list of .txt, .yaml, .yml files from both presets and wildcards directories"""
        try:
            files = []
            
            # 1. Get files from presets directory
            if self.preset_dir.exists():
                for pattern in ["*.txt", "*.yaml", "*.yml"]:
                    preset_files = [f.name for f in self.preset_dir.glob(pattern)]
                    files.extend(preset_files)
            
            # 2. Get files from Impact Pack wildcards directory (if exists)
            wildcard_dir = self._get_wildcard_dir()
            if wildcard_dir and wildcard_dir.exists():
                for pattern in ["*.txt", "*.yaml", "*.yml"]:
                    wildcard_files = [f.name for f in wildcard_dir.glob(pattern)]
                    # Add files that don't already exist in presets (avoid duplicates)
                    for wf in wildcard_files:
                        if wf not in files:
                            files.append(wf)
            
            return sorted(files) if files else []
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


# Register the node
NODE_CLASS_MAPPINGS = {
    "PromptPresetSelector": PromptPresetSelector,
    "PromptPresetSelectorWithWildcard": PromptPresetSelectorWithWildcard
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptPresetSelector": "Prompt Preset Selector",
    "PromptPresetSelectorWithWildcard": "Prompt Preset Selector (Wildcard)"
}
