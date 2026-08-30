"""
Multi-File / Folder Prompt Preset Selector nodes for ComfyUI

Adds two nodes that build on PromptPresetSelectorWithWildcard:

- MultiFilePromptPresetSelector
    Up to 3 preset files (each selectable via dropdown or absolute_path)
    are loaded, prefixed with their filename, and merged into a single
    searchable pool. Wildcard expansion (including {__key__|__key__}
    YAML key selection) works across all combined files.

- FolderPromptPresetSelector
    All .txt/.yaml/.yml files under a given folder (recursively) are
    loaded, prefixed with their path relative to that folder, and
    merged into a single searchable pool. An exclude_pattern field
    (comma/newline separated glob patterns) lets you skip files such
    as backups or temp files.

Both nodes reuse PromptPresetSelector's keyword filtering
(parse_keywords / filter_by_keywords), preset listing, and
PromptPresetSelectorWithWildcard's wildcard expansion engine
({A|B|C}, __filename__, {__key__|__key__}) without modifying the
original classes.
"""

import fnmatch
import random
import re
from pathlib import Path

from .nodes import PromptPresetSelectorWithWildcard, YAML_AVAILABLE


def merge_yaml_structures(structures):
    """
    Shallow-merge a list of top-level YAML dicts into one, for
    {__key__|__key__} lookups that need to search across multiple
    source files. On a top-level key collision, the later file wins
    (matches the order files/folder entries are loaded in).
    """
    merged = {}
    for data in structures:
        if isinstance(data, dict):
            merged.update(data)
    return merged


def strip_all_prefixes(text):
    """
    Like PromptPresetSelector.strip_key_hierarchy, but repeats until no
    more "key: " style prefix remains. Needed here because a combined
    line can carry two stacked prefixes, e.g.:
        "colors.txt: camera_angles:close_up: front view"
    -> strip "colors.txt: "            -> "camera_angles:close_up: front view"
    -> strip "camera_angles:close_up: " -> "front view"
    """
    while True:
        parts = text.split(': ', 1)
        if len(parts) == 2:
            key_part = parts[0]
            if ':' in key_part or (key_part and ' ' not in key_part):
                text = parts[1]
                continue
        break
    return text


def select_from_filtered(filtered_items, selection_mode, preset_index, seed, state_key, continue_state):
    """
    Shared Manual/Sequential/Sequential (continue)/Random selection logic,
    factored out of PromptPresetSelector.select_preset so both new nodes
    can use it against their own combined+filtered lists.

    filtered_items: list of (original_index, text) tuples
    continue_state: the node class's own _continue_state dict (for
                     Sequential (continue) persistence)

    Returns (selected_text, selected_index_in_filtered_list, original_index)
    """
    if selection_mode == "Sequential (continue)":
        if state_key not in continue_state:
            continue_state[state_key] = preset_index % len(filtered_items)
        idx = continue_state[state_key]
        original_index, text = filtered_items[idx]
        continue_state[state_key] = (idx + 1) % len(filtered_items)
    elif selection_mode == "Random":
        rnd = random.Random(seed)
        idx = rnd.randint(0, len(filtered_items) - 1)
        original_index, text = filtered_items[idx]
    else:
        # Manual and Sequential both just index into the filtered list
        # starting from preset_index (Sequential's "advance" happens via
        # the user changing preset_index between queues, same as the
        # original single-file node).
        idx = preset_index % len(filtered_items)
        original_index, text = filtered_items[idx]

    return text, idx, original_index


class _MergedYamlWildcardMixin:
    """
    Overrides PromptPresetSelectorWithWildcard._expand_yaml_key_wildcards
    so that {__key__|__key__} expansion searches across a merged YAML
    structure (self._merged_yaml_data) built from all combined source
    files, instead of a single current_file.
    """

    def _expand_yaml_key_wildcards(self, text, is_sequential, state_key, current_file):
        yaml_data = getattr(self, '_merged_yaml_data', None)
        if not yaml_data:
            return text

        pattern = r'\{(__[^}]+__(?:\|__[^}]+__)*)\}'

        def replace_yaml_key(match):
            keys_str = match.group(1)
            keys = re.findall(r'__(.+?)__', keys_str)
            if not keys:
                return match.group(0)

            all_choices = []
            for key in keys:
                key_content = self.get_yaml_key_content(yaml_data, key)
                all_choices.extend(key_content)

            if not all_choices:
                print(f"[Multi-Source Preset Selector] Warning: No content found for YAML keys: {keys}")
                return match.group(0)

            if is_sequential:
                wc_state_key = f"{state_key}_yamlkey_{keys_str}"
                if wc_state_key not in self._wildcard_state:
                    self._wildcard_state[wc_state_key] = 0
                index = self._wildcard_state[wc_state_key] % len(all_choices)
                selected = all_choices[index]
                self._wildcard_state[wc_state_key] = (index + 1) % len(all_choices)
                return selected
            else:
                return random.choice(all_choices)

        return re.sub(pattern, replace_yaml_key, text)


class MultiFilePromptPresetSelector(_MergedYamlWildcardMixin, PromptPresetSelectorWithWildcard):
    """
    Prompt Preset Selector variant that searches up to 3 files at once.
    Each slot works like the original node's preset_file/absolute_path
    pair. Slots 2 and 3 may be left as "(None)" with no absolute_path
    to use only 1 or 2 files.
    """

    _continue_state = {}
    _wildcard_state = {}

    def __init__(self):
        super().__init__()
        self._merged_yaml_data = None

    @classmethod
    def INPUT_TYPES(cls):
        instance = cls()
        files = instance.get_preset_files()
        dropdown = ["(None)"] + files if files else ["(None)"]

        def file_slot(n):
            return {
                f"enabled{n}": ("BOOLEAN", {"default": True, "label_on": "enabled", "label_off": "disabled"}),
                f"preset_file{n}": (dropdown,),
                f"absolute_path{n}": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": f"Optional: /absolute/path/to/file{n}.txt or .yaml"
                }),
            }

        required = {}
        required.update(file_slot(1))
        required.update(file_slot(2))
        required.update(file_slot(3))
        required.update({
            "keyword": ("STRING", {"default": "", "multiline": False}),
            "keyword_mode": (["OFF", "AND", "OR"], {"default": "OFF"}),
            "selection_mode": (["Manual", "Sequential", "Sequential (continue)", "Random"], {"default": "Manual"}),
            "preset_index": ("INT", {"default": 0, "min": 0, "max": 9999, "step": 1}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            "enable_wildcard": ("BOOLEAN", {"default": True}),
        })

        return {"required": required}

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("text", "preset_list", "selected_info")
    FUNCTION = "select_multi_preset"
    CATEGORY = "text"
    OUTPUT_NODE = False

    @classmethod
    def IS_CHANGED(cls, enabled1, preset_file1, absolute_path1,
                    enabled2, preset_file2, absolute_path2,
                    enabled3, preset_file3, absolute_path3,
                    keyword, keyword_mode, selection_mode,
                    preset_index, seed, enable_wildcard):
        return (f"{enabled1}_{preset_file1}_{absolute_path1}_"
                f"{enabled2}_{preset_file2}_{absolute_path2}_"
                f"{enabled3}_{preset_file3}_{absolute_path3}_"
                f"{keyword}_{keyword_mode}_"
                f"{selection_mode}_{preset_index}_{seed}_{enable_wildcard}")

    def _resolve_source(self, enabled, preset_file, absolute_path):
        """
        Resolve one file slot to a Path, or None if the slot is
        disabled, unused, or invalid.
        """
        if not enabled:
            return None

        if absolute_path and absolute_path.strip():
            p = Path(absolute_path.strip())
            if not p.exists():
                print(f"[Multi-File Preset Selector] Warning: file not found: {p}")
                return None
            if p.suffix.lower() not in ('.txt', '.yaml', '.yml'):
                print(f"[Multi-File Preset Selector] Warning: unsupported file type: {p}")
                return None
            return p

        if preset_file and preset_file not in ("(None)", "(No preset files found)"):
            p = self.preset_dir / preset_file
            if p.exists():
                return p
            wildcard_dir = self._get_wildcard_dir()
            if wildcard_dir:
                wp = wildcard_dir / preset_file
                if wp.exists():
                    return wp
            print(f"[Multi-File Preset Selector] Warning: preset file not found: {preset_file}")
            return None

        return None

    def select_multi_preset(self, enabled1, preset_file1, absolute_path1,
                             enabled2, preset_file2, absolute_path2,
                             enabled3, preset_file3, absolute_path3,
                             keyword, keyword_mode, selection_mode,
                             preset_index, seed, enable_wildcard):

        sources = []
        for en, pf, ap in ((enabled1, preset_file1, absolute_path1),
                           (enabled2, preset_file2, absolute_path2),
                           (enabled3, preset_file3, absolute_path3)):
            path = self._resolve_source(en, pf, ap)
            if path is not None:
                sources.append(path)

        if not sources:
            msg = "No active files (enable a slot and set preset_file or absolute_path)"
            print(f"[Multi-File Preset Selector] Warning: {msg}")
            return ("", "(No preset files selected)", msg)

        all_lines = []
        yaml_structures = []
        for path in sources:
            lines = self.load_preset_lines(path)
            prefix = f"{path.name}: "
            all_lines.extend(prefix + line for line in lines)
            if path.suffix.lower() in ('.yaml', '.yml'):
                data = self.load_yaml_structure(path)
                if isinstance(data, dict):
                    yaml_structures.append(data)

        if not all_lines:
            warning = "All selected files are empty or failed to load"
            print(f"[Multi-File Preset Selector] Warning: {warning}")
            return ("", f"({warning})", "")

        self._merged_yaml_data = merge_yaml_structures(yaml_structures) if yaml_structures else None

        preset_list = self.generate_preset_list(all_lines)
        include_keywords, exclude_keywords = self.parse_keywords(keyword)
        filtered_items = self.filter_by_keywords(all_lines, include_keywords, exclude_keywords, keyword_mode)

        if not filtered_items:
            warning = f"No presets match keywords: {keyword}"
            print(f"[Multi-File Preset Selector] Warning: {warning}")
            return ("", preset_list, warning)

        file_identifier = "|".join(str(p) for p in sources)
        state_key = f"{file_identifier}_{keyword}_{keyword_mode}"

        selected_text, _, original_index = select_from_filtered(
            filtered_items, selection_mode, preset_index, seed, state_key, self._continue_state
        )

        info = (f"Selected: {original_index}: {selected_text}\n"
                f"Mode: {selection_mode}\n"
                f"Filtered: {len(filtered_items)}/{len(all_lines)} presets\n"
                f"Sources: {', '.join(p.name for p in sources)}")

        output_text = strip_all_prefixes(selected_text)

        if enable_wildcard and output_text:
            original_text = output_text
            wc_state_key = f"{state_key}_wildcard"
            output_text = self.expand_wildcards(output_text, seed, selection_mode, wc_state_key, current_file=None)
            if output_text != original_text:
                mode_info = "sequential" if selection_mode in ["Sequential", "Sequential (continue)"] else "random"
                info += f"\n[Wildcards expanded: {mode_info}]"

        return (output_text, preset_list, info)


class FolderPromptPresetSelector(_MergedYamlWildcardMixin, PromptPresetSelectorWithWildcard):
    """
    Prompt Preset Selector variant that recursively searches every
    .txt/.yaml/.yml file under a given folder, merging them into a
    single searchable pool. Each line is prefixed with its path
    relative to folder_path (e.g. "sub/colors.txt: ") so same-named
    files in different subfolders don't collide, and so you can filter
    to a specific file/subfolder via keyword search.
    """

    _continue_state = {}
    _wildcard_state = {}

    SUPPORTED_EXTENSIONS = ("*.txt", "*.yaml", "*.yml")

    def __init__(self):
        super().__init__()
        self._merged_yaml_data = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "", "multiline": False, "placeholder": "Absolute path to folder"}),
                "exclude_pattern": ("STRING", {"default": "", "multiline": False,
                                                "placeholder": "Optional glob patterns, comma-separated (e.g. *_backup*, temp_*)"}),
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
    FUNCTION = "select_folder_preset"
    CATEGORY = "text"
    OUTPUT_NODE = False

    @classmethod
    def IS_CHANGED(cls, folder_path, exclude_pattern, keyword, keyword_mode, selection_mode,
                    preset_index, seed, enable_wildcard):
        return (f"{folder_path}_{exclude_pattern}_{keyword}_{keyword_mode}_"
                f"{selection_mode}_{preset_index}_{seed}_{enable_wildcard}")

    def _collect_folder_files(self, folder_path, exclude_pattern):
        """
        Recursively find .txt/.yaml/.yml files under folder_path,
        excluding any that match exclude_pattern (comma/newline
        separated glob patterns, matched against both the filename
        and the path relative to folder_path).

        Returns (list of (relative_path_str, Path), error_message_or_None)
        """
        base = Path(folder_path.strip())
        if not base.exists() or not base.is_dir():
            return [], f"Folder not found: {folder_path}"

        patterns = [p.strip() for p in re.split(r'[,\n]', exclude_pattern or "") if p.strip()]

        matched = []
        for ext in self.SUPPORTED_EXTENSIONS:
            matched.extend(base.rglob(ext))

        results = []
        for p in matched:
            try:
                rel = p.relative_to(base).as_posix()
            except ValueError:
                rel = p.name

            if patterns and any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(p.name, pat) for pat in patterns):
                continue

            results.append((rel, p))

        results.sort(key=lambda item: item[0])
        return results, None

    def select_folder_preset(self, folder_path, exclude_pattern, keyword, keyword_mode,
                              selection_mode, preset_index, seed, enable_wildcard):

        if not folder_path or not folder_path.strip():
            msg = "folder_path is empty"
            print(f"[Folder Preset Selector] Warning: {msg}")
            return ("", "(No folder specified)", msg)

        entries, err = self._collect_folder_files(folder_path, exclude_pattern)
        if err:
            print(f"[Folder Preset Selector] Warning: {err}")
            return ("", "", err)

        if not entries:
            warning = "No matching files found in folder"
            print(f"[Folder Preset Selector] Warning: {warning}")
            return ("", f"({warning})", "")

        all_lines = []
        yaml_structures = []
        for rel, path in entries:
            lines = self.load_preset_lines(path)
            prefix = f"{rel}: "
            all_lines.extend(prefix + line for line in lines)
            if path.suffix.lower() in ('.yaml', '.yml'):
                data = self.load_yaml_structure(path)
                if isinstance(data, dict):
                    yaml_structures.append(data)

        if not all_lines:
            warning = "All matching files are empty or failed to load"
            print(f"[Folder Preset Selector] Warning: {warning}")
            return ("", f"({warning})", "")

        self._merged_yaml_data = merge_yaml_structures(yaml_structures) if yaml_structures else None

        preset_list = self.generate_preset_list(all_lines)
        include_keywords, exclude_keywords = self.parse_keywords(keyword)
        filtered_items = self.filter_by_keywords(all_lines, include_keywords, exclude_keywords, keyword_mode)

        if not filtered_items:
            warning = f"No presets match keywords: {keyword}"
            print(f"[Folder Preset Selector] Warning: {warning}")
            return ("", preset_list, warning)

        state_key = f"{folder_path.strip()}_{exclude_pattern}_{keyword}_{keyword_mode}"

        selected_text, _, original_index = select_from_filtered(
            filtered_items, selection_mode, preset_index, seed, state_key, self._continue_state
        )

        info = (f"Selected: {original_index}: {selected_text}\n"
                f"Mode: {selection_mode}\n"
                f"Filtered: {len(filtered_items)}/{len(all_lines)} presets\n"
                f"Files: {len(entries)} (folder: {folder_path.strip()})")

        output_text = strip_all_prefixes(selected_text)

        if enable_wildcard and output_text:
            original_text = output_text
            wc_state_key = f"{state_key}_wildcard"
            output_text = self.expand_wildcards(output_text, seed, selection_mode, wc_state_key, current_file=None)
            if output_text != original_text:
                mode_info = "sequential" if selection_mode in ["Sequential", "Sequential (continue)"] else "random"
                info += f"\n[Wildcards expanded: {mode_info}]"

        return (output_text, preset_list, info)


NODE_CLASS_MAPPINGS = {
    "MultiFilePromptPresetSelector": MultiFilePromptPresetSelector,
    "FolderPromptPresetSelector": FolderPromptPresetSelector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MultiFilePromptPresetSelector": "Prompt Preset Selector (Multi-File, Wildcard)",
    "FolderPromptPresetSelector": "Prompt Preset Selector (Folder, Wildcard)",
}
