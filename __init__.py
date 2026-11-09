"""
Comfy UI Prompt Preset Selector
A simple node for selecting text presets from external files
"""

from .nodes import NODE_CLASS_MAPPINGS as _BASE_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as _BASE_NAME_MAPPINGS
from .text_options import with_text_options
from .multi_source_nodes import NODE_CLASS_MAPPINGS as _MULTI_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as _MULTI_NAME_MAPPINGS

NODE_CLASS_MAPPINGS = {**_BASE_MAPPINGS, **_MULTI_MAPPINGS}
NODE_DISPLAY_NAME_MAPPINGS = {**_BASE_NAME_MAPPINGS, **_MULTI_NAME_MAPPINGS}

# Add additional-text / strength options to every node
for _cls in NODE_CLASS_MAPPINGS.values():
    with_text_options(_cls)

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
