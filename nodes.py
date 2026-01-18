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
        """Get list of .txt, .yaml, .yml files in presets directory"""
        try:
            if not self.preset_dir.exists():
                return []
            
            files = []
            for pattern in ["*.txt", "*.yaml", "*.yml"]:
                files.extend([f.name for f in self.preset_dir.glob(pattern)])
            
            return sorted(files) if files else []
        except Exception as e:
            print(f"[Prompt Preset Selector] Error reading preset directory: {e}")
            return []
    
    def load_preset_lines(self, preset_file):
        """
        Load lines from preset file, filtering out comments and empty lines
        Supports .txt, .yaml, .yml files
        
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
                    file_path = self.preset_dir / preset_file
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
        
        return (selected_text, preset_list, info)


# Register the node
NODE_CLASS_MAPPINGS = {
    "PromptPresetSelector": PromptPresetSelector
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptPresetSelector": "Prompt Preset Selector"
}
