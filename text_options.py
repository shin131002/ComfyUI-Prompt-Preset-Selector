"""
Common output options shared by all Prompt Preset Selector nodes.

Adds three widgets at the bottom of each node:
- enable_additional_text : ON/OFF switch for the additional text
- additional_text        : text appended to the preset output when ON
                           (lines starting with # are ignored; wildcards
                           are expanded on nodes with enable_wildcard)
- strength               : weight applied to the whole output as (text:strength)
                           1.0 = no change
"""

import functools
import hashlib
from pathlib import Path


TEXT_OPTION_INPUTS = {
    "enable_additional_text": ("BOOLEAN", {"default": False, "label_on": "ON", "label_off": "OFF"}),
    "additional_text": ("STRING", {"default": "", "multiline": True,
                                   "placeholder": "Appended to the preset output when ON (# at line start = comment, wildcards OK)"}),
    "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.05, "round": 0.01}),
}

_OPTION_KEYS = tuple(TEXT_OPTION_INPUTS.keys())

# Inputs that change on every run by design; left out of the sequential
# state key so the additional-text wildcards keep cycling.
_VOLATILE_KEYS = ("seed", "preset_index", "image_index")


def clean_additional_text(additional_text):
    """
    Drop comment lines (first non-space character is #) and empty lines,
    then join the remaining lines with ", ".
    """
    lines = []
    for line in (additional_text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = line.rstrip(",").rstrip()
        if line:
            lines.append(line)
    return ", ".join(lines)


def apply_text_options(text, enable_additional_text=False, additional_text="", strength=1.0, expand=None):
    """
    Return (modified_text, info_lines).
    expand: optional callable that expands wildcards in the additional text
            (comments are removed before it is called).
    """
    info = []
    text = text or ""

    extra = clean_additional_text(additional_text) if enable_additional_text else ""
    if extra:
        if expand is not None:
            expanded = expand(extra)
            if expanded != extra:
                info.append("[Wildcards expanded in additional text]")
            extra = expanded.strip().rstrip(",").rstrip()
    if extra:
        base = text.rstrip().rstrip(",").rstrip()
        text = f"{base}, {extra}" if base else extra
        info.insert(0, "[Additional text appended]")

    strength = round(float(strength), 2)
    body = text.strip().rstrip(",").rstrip()
    if body and strength != 1.0:
        text = f"({body}:{strength:g})"
        info.append(f"[Strength: {strength:g}]")

    return text, info


def _additional_seed(seed):
    """
    Seed for the additional text, derived from the node's seed.
    Reusing the seed itself would restart the same random sequence as the
    preset's own wildcards, so e.g. {red|blue} in both places would always
    pick the same option.
    """
    digest = hashlib.sha256(f"additional_text:{seed}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _yaml_file_for(node, kwargs):
    """
    The selected preset file, for {__key__|__key__} lookups, resolved the
    same way select_preset_with_wildcard does. Only YAML files are returned.
    Multi-File / Folder nodes ignore this and use their merged YAML data.
    """
    path = None
    absolute_path = (kwargs.get("absolute_path") or "").strip()
    preset_file = kwargs.get("preset_file")
    if absolute_path:
        path = Path(absolute_path)
    elif preset_file and not str(preset_file).startswith("("):
        for base in (getattr(node, "preset_dir", None), getattr(node, "wildcard_dir", None)):
            if base and (Path(base) / preset_file).is_file():
                path = Path(base) / preset_file
                break
    if path and path.is_file() and path.suffix.lower() in (".yaml", ".yml"):
        return path
    return None


def _make_expander(node, kwargs):
    """Wildcard expander for the additional text, or None if not applicable."""
    if not hasattr(node, "expand_wildcards") or not kwargs.get("enable_wildcard", False):
        return None

    seed = kwargs.get("seed", 0)
    selection_mode = kwargs.get("selection_mode", "Manual")
    current_file = _yaml_file_for(node, kwargs)
    ident = "|".join(f"{k}={kwargs[k]}" for k in sorted(kwargs) if k not in _VOLATILE_KEYS)

    def expand(text):
        state_key = f"{type(node).__name__}|{ident}|additional_text|{text}"
        return node.expand_wildcards(text, _additional_seed(seed), selection_mode,
                                     state_key, current_file)
    return expand


def with_text_options(cls):
    """
    Class decorator: adds the common options as optional inputs and
    post-processes the first output (text) of the node's FUNCTION.
    Uses only attributes defined on `cls` itself so subclasses that are
    decorated separately keep working.
    """
    orig_input_types = cls.__dict__["INPUT_TYPES"].__func__
    orig_is_changed = cls.__dict__["IS_CHANGED"].__func__
    core_name = cls.__dict__["FUNCTION"]
    info_index = list(cls.__dict__["RETURN_NAMES"]).index("selected_info")

    def _split(kwargs):
        opts = {k: kwargs.pop(k) for k in _OPTION_KEYS if k in kwargs}
        return opts

    @classmethod
    def INPUT_TYPES(klass):
        types = orig_input_types(klass)
        types.setdefault("optional", {}).update(TEXT_OPTION_INPUTS)
        return types

    @classmethod
    def IS_CHANGED(klass, **kwargs):
        opts = _split(kwargs)
        base = orig_is_changed(klass, **kwargs)
        return f"{base}_" + "_".join(str(opts.get(k, "")) for k in _OPTION_KEYS)

    core = getattr(cls, core_name)

    @functools.wraps(core)
    def run(self, **kwargs):
        opts = _split(kwargs)
        result = list(core(self, **kwargs))
        # built after core() so Multi-File / Folder nodes have their merged
        # YAML data ready for {__key__|__key__} in the additional text
        expand = _make_expander(self, kwargs)
        result[0], info = apply_text_options(result[0], expand=expand, **opts)
        if info:
            result[info_index] = "\n".join(filter(None, [result[info_index]] + info))
        return tuple(result)

    run_name = f"_run_with_text_options_{cls.__name__}"
    setattr(cls, run_name, run)
    cls.INPUT_TYPES = INPUT_TYPES
    cls.IS_CHANGED = IS_CHANGED
    cls.FUNCTION = run_name
    return cls
