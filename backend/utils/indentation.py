from dataclasses import dataclass
from typing import List


@dataclass
class ParsedLine:
    """Represents a parsed line with metadata."""
    original: str
    line_num: int
    indent_level: int
    construct_type: str
    content: str
    block_start: bool = False
    block_level: int = 0

    def get_target_indent(self, target_lang: str, spaces_per_level: int = None) -> str:
        """Get proper indentation for target language."""
        if spaces_per_level is None:
            spaces_per_level = 2 if target_lang in ["javascript", "java"] else 4
        return " " * (self.indent_level * spaces_per_level)


class IndentationTracker:
    """Tracks indentation levels and block structure during conversion."""

    def __init__(self, source_lang: str = "python"):
        self.source_lang = source_lang
        self.current_indent = 0
        self.current_block_level = 0
        self.block_stack: List[str] = []
        self.max_indent_level = 0
        self.block_count = 0
        self.indent_history: List[int] = []

    def get_indent_level(self, line: str) -> int:
        """
        Determine indentation level of a line.
        Python: Count spaces/tabs at start
        """
        if not line.strip():
            return self.current_indent

        if self.source_lang == "python":
            # Count leading spaces (assuming 4-space indentation)
            leading_spaces = len(line) - len(line.lstrip())
            # Calculate indent level (divide by 4 for Python standard)
            return leading_spaces // 4 if leading_spaces >= 4 else (1 if leading_spaces > 0 else 0)
        return self.current_indent

    def enter_block(self):
        """Called when entering a new block (function, loop, condition)."""
        self.current_block_level += 1
        self.block_stack.append("block")
        self.block_count += 1
        self.max_indent_level = max(self.max_indent_level, self.current_block_level)

    def exit_block(self):
        """Called when exiting a block."""
        if self.block_stack:
            self.block_stack.pop()
            self.current_block_level = len(self.block_stack)

    def reset(self):
        """Reset tracker state."""
        self.current_indent = 0
        self.current_block_level = 0
        self.block_stack = []
        self.max_indent_level = 0
        self.block_count = 0
        self.indent_history = []

    @property
    def is_in_block(self) -> bool:
        """Check if currently inside a block."""
        return len(self.block_stack) > 0

    def get_closing_braces(self, prev_indent: int, curr_indent: int) -> int:
        """Calculate how many closing braces needed when indentation decreases."""
        return max(0, prev_indent - curr_indent)
