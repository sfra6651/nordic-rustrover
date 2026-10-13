#!/usr/bin/env python3
"""Build the Nordic RustRover plugin (editor color scheme + Islands UI theme).

The palette and highlight roles are taken from AlexvZyl/nordic.nvim with its default
options (reduced_blue = true, italic_comments = true, bold_keywords = false), and every
Rust mapping below was checked against what Neovim actually renders for the same code
(treesitter + rust-analyzer semantic tokens), not just against nordic's group table.

    python3 build.py            # writes resources/ and dist/nordic-rustrover-<version>.jar
"""
import json
import os
import re
import sys
import zipfile
from xml.sax.saxutils import escape

VERSION = '1.0.0'
SCHEME_NAME = 'Nordic'
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, 'resources')


# --------------------------------------------------------------------------------------
# Palette: lua/nordic/colors/nordic.lua + lua/nordic/colors/init.lua
# --------------------------------------------------------------------------------------
def blend(fg, bg, alpha):
    """nordic.utils.blend (adapted from tokyonight)."""
    f = [int(fg[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(bg[i:i + 2], 16) for i in (0, 2, 4)]
    return ''.join('%02X' % int(min(max(0, alpha * x + (1 - alpha) * y), 255) + 0.5) for x, y in zip(f, b))


P = dict(
    black0='191D24', black1='1E222A', black2='222630',
    gray0='242933', gray1='2E3440', gray2='3B4252', gray3='434C5E', gray4='4C566A', gray5='60728A',
    white0='C0C8D8',  # white0_reduce_blue (reduced_blue = true is nordic's default)
    white1='D8DEE9', white2='E5E9F0', white3='ECEFF4',
    blue0='5E81AC', blue1='81A1C1', blue2='88C0D0',
    cyan='8FBCBB', cyan_bright='9FC6C5', cyan_dim='80B3B2',
    red='BF616A', red_bright='C5727A', red_dim='B74E58',
    orange='D08770', orange_bright='D79784', orange_dim='CB775D',
    yellow='EBCB8B', yellow_bright='EFD49F', yellow_dim='E7C173',
    green='A3BE8C', green_bright='B1C89D', green_dim='97B67C',
    magenta='B48EAD', magenta_bright='BE9DB8', magenta_dim='A97EA1',
)
P.update(
    bg=P['gray0'], fg=P['white0'], bg_dark=P['black0'], bg_float=P['black1'], bg_selected=P['gray2'],
    bg_cursorline=blend(P['black0'], P['gray0'], 0.85),  # cursorline.theme = 'dark', blend = 0.85
    bg_visual=blend(P['black0'], P['gray0'], 0.85),      # visual.theme = 'dark', blend = 0.85
    error=P['red_bright'], warn=P['yellow'], hint=P['green_bright'], info=P['blue2'],
    diff_add=blend(P['green'], P['gray0'], 0.2), diff_delete=blend(P['red'], P['gray0'], 0.2),
    diff_change0=blend(P['blue1'], P['gray0'], 0.05), diff_change1=blend(P['blue2'], P['gray0'], 0.2),
)

# --------------------------------------------------------------------------------------
# TextAttributes helpers
# --------------------------------------------------------------------------------------
PLAIN, BOLD, ITALIC, BOLD_ITALIC = 0, 1, 2, 3
BOX, UNDERLINE, WAVE, STRIKE, BOLD_UNDERLINE, BOLD_DOTTED = 0, 1, 2, 3, 4, 5


def A(fg=None, bg=None, font=PLAIN, effect=None, effect_color=None, stripe=None):
    """A TextAttributes value. Every key is written out in full, so nothing leaks in
    from the Darcula parent (or from RustRover's own Darcula additions for Rust)."""
    return dict(fg=fg, bg=bg, font=font, effect=effect, effect_color=effect_color, stripe=stripe)


EMPTY = A()

# nordic.nvim roles (lua/nordic/groups/native.lua)
Keyword = A(P['orange'])
Type = A(P['yellow'])
Function = A(P['blue2'])
Field = A(P['cyan'])
Constant = A(P['magenta_bright'])
String = A(P['green'])
Comment = A(P['gray4'], font=ITALIC)
Macro = A(P['red'])
Namespace = A(P['yellow_dim'])
Builtin = A(P['blue0'])
Delimiter = A(P['gray5'], font=ITALIC)
Special = A(P['blue1'])
Text = A(P['fg'])
Parameter = A(P['fg'], font=ITALIC)

# --------------------------------------------------------------------------------------
# Rust (org.rust.*): one entry for every key in RustRover 2026.2's RsColor enum.
# Comments give the Neovim source of each colour as observed in a real render.
# --------------------------------------------------------------------------------------
RUST = {
    # variables / bindings: @variable (fg). nvim shows no underline for `mut`.
    'VARIABLE': Text,
    'MUT_BINDING': Text,
    'FIELD': Field,                                  # @lsp.type.property -> Field
    'CONSTANT': Constant,                            # ALL_CAPS -> @constant
    'STATIC': Constant,
    'MUT_STATIC': Constant,
    'CONST_PARAMETER': Constant,
    'SELF_EXPRESSION': Builtin,                      # @lsp.type.selfKeyword -> Builtin
    'SELF_PARAMETER': Builtin,
    'MUT_SELF_PARAMETER': Builtin,
    'PARAMETER': Parameter,                          # @lsp.type.parameter -> @parameter (italic)
    'MUT_PARAMETER': Parameter,
    # functions: @lsp.type.function / method -> Function (never italic in nordic)
    'FUNCTION': Function,
    'METHOD': Function,
    'TRAIT_METHOD': Function,
    'ASSOC_FUNCTION': Function,
    'ASSOC_TRAIT_FUNCTION': Function,
    'FUNCTION_CALL': Function,
    'METHOD_CALL': Function,
    'TRAIT_METHOD_CALL': Function,
    'ASSOC_FUNCTION_CALL': Function,
    'ASSOC_TRAIT_FUNCTION_CALL': Function,
    'OVERLOADED_OPERATOR': Text,                     # `a += b` on String/Vec3 etc. -> Operator (fg)
    'CLOSURE': Text,                                 # closure bars `|x|` -> fg
    # macros: std macros (println!, vec!, ...) are red; the `!` is magenta.
    # User/3rd-party macro calls are magenta in nvim; RustRover has one key, std wins ~3:1.
    'MACRO': Macro,
    'MACRO_EXCL': Constant,                          # `!` of println! / macro_rules!
    'MACRO_RULES': Macro,
    'MACRO_IDENTIFIER': Constant,                    # name in `macro_rules! name`
    'MACRO_DOLLAR': Macro,
    'MACRO_META_VAR_IDENTIFIER': Macro,              # $name
    'MACRO_COLON': Delimiter,
    'MACRO_BINDING_IDENTIFIER': Text,                # ident / ty / tt
    'MACRO_GROUP_ELEMENTS': Text,                    # $( ... )*
    # types
    'PRIMITIVE_TYPE': Type,
    'STRUCT': Type,
    'UNION': Type,
    'ENUM': Type,
    'TYPE_ALIAS': Type,
    'TYPE_PARAMETER': Type,
    'TRAIT': Keyword,                                # @lsp.type.interface -> Keyword (orange)
    # User and 3rd-party variants are cyan, std's Some/None/Ok/Err magenta.
    # Measured on real-world code: cyan covers 70% of variant characters.
    'ENUM_VARIANT': Field,
    # lifetimes: 'static / '_ are blue1, 'a is orange-tick + red; blue1 covers the most
    # lifetime characters in real-world code.
    'LIFETIME': A(P['blue1']),
    'CRATE': Namespace,
    'MODULE': Namespace,
    # keywords (use/mod/async/await are red in nvim, true/false magenta: RustRover has
    # a single keyword key, so they follow the majority orange)
    'KEYWORD': Keyword,
    'KEYWORD_UNSAFE': Keyword,
    # literals
    'CHAR': String,
    'STRING': String,
    'NUMBER': Constant,
    'VALID_STRING_ESCAPE': A(P['magenta_bright']),   # @string.escape
    'INVALID_STRING_ESCAPE': A(P['error']),
    'FORMAT_PARAMETER': Macro,                       # `{`, `:?`, `}` -> @lsp.type.formatSpecifier -> Macro
    'FORMAT_SPECIFIER': String,                      # the name / width inside `{name:4}` stays string-green
    # comments (nvim-treesitter does not inject markdown into Rust doc comments: plain Comment)
    'BLOCK_COMMENT': Comment,
    'EOL_COMMENT': Comment,
    'DOC_COMMENT': Comment,
    'DOC_HEADING': Comment,
    'DOC_LINK': Comment,
    'DOC_EMPHASIS': Comment,
    'DOC_STRONG': Comment,
    'DOC_CODE': Comment,
    # punctuation
    'BRACES': Text,
    'BRACKETS': Text,
    'PARENTHESES': Text,
    'COMMA': Delimiter,
    'SEMICOLON': Delimiter,
    'DOT': Delimiter,
    # RustRover's operator key covers `:: : -> =>` (Delimiter in nvim) *and* `= & < > + |`
    # (fg in nvim). By characters, the delimiter group is the larger one in real-world code.
    'OPERATORS': Delimiter,
    'Q_OPERATOR': Text,                              # `?` -> fg
    # RustRover colours the whole #[...] one colour; `#` and the attribute name are red.
    'ATTRIBUTE': Macro,
    # semantic extras
    'UNSAFE_CODE': EMPTY,                            # nvim has no unsafe background
    'CFG_DISABLED_CODE': Comment,                    # inactive-code diagnostic -> DiagnosticUnnecessary
    'GENERATED_ITEM': EMPTY,
    'DIMMED_TEXT': A(P['gray4']),
    'SECONDARY_SPOT': A(effect=BOX, effect_color=P['blue1']),
    # inline diagnostics ~ DiagnosticVirtualText*
    'INLINE_ERROR_DESCRIPTION': A(P['error'], P['gray1'], font=BOLD),
    'INLINE_WARNING_DESCRIPTION': A(P['warn'], P['gray1']),
    'INLINE_EXPLANATION': A(P['info'], P['gray1']),
}

# --------------------------------------------------------------------------------------
# TOML (Cargo.toml) — checked against nvim's treesitter TOML render
# --------------------------------------------------------------------------------------
TOML = {
    'KEY': Field,                # @property
    'COMMENT': Comment,
    'BOOLEAN': Constant,
    'NUMBER': Constant,
    'DATE': Type,                # @string.special -> yellow
    'STRING': String,
    'VALID_STRING_ESCAPE': A(P['magenta_bright']),
    'INVALID_STRING_ESCAPE': A(P['error']),
}

# --------------------------------------------------------------------------------------
# Language defaults (used by every language that has no explicit key above)
# --------------------------------------------------------------------------------------
GENERAL = {
    'TEXT': A(P['fg'], P['bg']),
    'DEFAULT_IDENTIFIER': Text,
    'DEFAULT_KEYWORD': Keyword,
    'DEFAULT_NUMBER': Constant,
    'DEFAULT_STRING': String,
    'DEFAULT_VALID_STRING_ESCAPE': A(P['magenta_bright']),
    'DEFAULT_INVALID_STRING_ESCAPE': A(P['error'], effect=WAVE, effect_color=P['error']),
    'DEFAULT_LINE_COMMENT': Comment,
    'DEFAULT_BLOCK_COMMENT': Comment,
    'DEFAULT_DOC_COMMENT': Comment,
    'DEFAULT_DOC_COMMENT_TAG': A(P['gray5'], font=ITALIC),
    'DEFAULT_DOC_COMMENT_TAG_VALUE': A(P['gray5'], font=ITALIC),
    'DEFAULT_DOC_MARKUP': Comment,
    'DEFAULT_CONSTANT': Constant,
    'DEFAULT_LOCAL_VARIABLE': Text,
    'DEFAULT_REASSIGNED_LOCAL_VARIABLE': Text,
    'DEFAULT_GLOBAL_VARIABLE': Text,
    'DEFAULT_PARAMETER': Parameter,
    'DEFAULT_REASSIGNED_PARAMETER': Parameter,
    'DEFAULT_FUNCTION_DECLARATION': Function,
    'DEFAULT_FUNCTION_CALL': Function,
    'DEFAULT_INSTANCE_METHOD': Function,
    'DEFAULT_STATIC_METHOD': Function,
    'DEFAULT_CLASS_NAME': Type,
    'DEFAULT_CLASS_REFERENCE': Type,
    'DEFAULT_INTERFACE_NAME': Keyword,     # nordic: @lsp.type.interface -> Keyword
    'DEFAULT_INSTANCE_FIELD': Field,
    'DEFAULT_STATIC_FIELD': Field,
    'DEFAULT_METADATA': Macro,             # @attribute -> Macro
    'DEFAULT_PREDEFINED_SYMBOL': Builtin,
    'DEFAULT_LABEL': Keyword,
    'DEFAULT_ENTITY': A(P['magenta_bright']),
    'DEFAULT_OPERATION_SIGN': Text,
    'DEFAULT_BRACES': Text,
    'DEFAULT_BRACKETS': Text,
    'DEFAULT_PARENTHS': Text,
    'DEFAULT_COMMA': Delimiter,
    'DEFAULT_SEMICOLON': Delimiter,
    'DEFAULT_DOT': Delimiter,
    'DEFAULT_TAG': A(P['blue1']),          # @tag
    'DEFAULT_ATTRIBUTE': Type,             # @tag.attribute
    'DEFAULT_HIGHLIGHTED_REFERENCE': A(effect=UNDERLINE, effect_color=P['gray4']),
    'DEFAULT_TEMPLATE_LANGUAGE_COLOR': A(bg=P['black2']),
    'TYPE_PARAMETER_NAME_ATTRIBUTES': Type,
    'ANNOTATION_NAME_ATTRIBUTES': Macro,
    'ANNOTATION_ATTRIBUTE_NAME_ATTRIBUTES': Text,
    'CUSTOM_KEYWORD1_ATTRIBUTES': Keyword,
    'CUSTOM_KEYWORD2_ATTRIBUTES': Type,
    'CUSTOM_KEYWORD3_ATTRIBUTES': Function,
    'CUSTOM_KEYWORD4_ATTRIBUTES': Constant,
    'CUSTOM_STRING_ATTRIBUTES': String,
    'CUSTOM_NUMBER_ATTRIBUTES': Constant,
    'CUSTOM_LINE_COMMENT_ATTRIBUTES': Comment,
    'CUSTOM_MULTI_LINE_COMMENT_ATTRIBUTES': Comment,
    'CUSTOM_VALID_STRING_ESCAPE_ATTRIBUTES': A(P['magenta_bright']),
    'CUSTOM_INVALID_STRING_ESCAPE_ATTRIBUTES': A(P['error']),
    # JSON / YAML / Markdown (nvim treesitter roles)
    'JSON.PROPERTY_KEY': Field,
    'JSON.KEYWORD': Constant,
    'JSON.STRING': String,
    'JSON.NUMBER': Constant,
    'JSON.BRACES': Text,
    'JSON.BRACKETS': Text,
    'JSON.COMMA': Delimiter,
    'JSON.COLON': Delimiter,
    'YAML_SCALAR_KEY': Field,
    'YAML_SCALAR_VALUE': String,
    'YAML_SCALAR_STRING': String,
    'YAML_SCALAR_DSTRING': String,
    'YAML_SCALAR_LIST': String,
    'YAML_TEXT': String,
    'YAML_COMMENT': Comment,
    'YAML_SIGN': Delimiter,
    'YAML_ANCHOR': A(P['blue1']),
    'MARKDOWN_HEADER_LEVEL_1': A(P['yellow'], font=BOLD),
    'MARKDOWN_HEADER_LEVEL_2': A(P['orange'], font=BOLD),
    'MARKDOWN_HEADER_LEVEL_3': A(P['magenta'], font=BOLD),
    'MARKDOWN_HEADER_LEVEL_4': A(P['green']),
    'MARKDOWN_HEADER_LEVEL_5': A(P['blue2'], font=ITALIC),
    'MARKDOWN_HEADER_LEVEL_6': A(P['cyan'], font=ITALIC),
    'MARKDOWN_BOLD': A(font=BOLD),
    'MARKDOWN_ITALIC': A(font=ITALIC),
    'MARKDOWN_CODE_SPAN': A(P['fg'], P['black2']),
    'MARKDOWN_CODE_BLOCK': A(P['fg'], P['black1']),
    'MARKDOWN_CODE_FENCE': A(P['cyan'], font=BOLD),
    'MARKDOWN_LINK_TEXT': A(P['blue1'], effect=UNDERLINE, effect_color=P['blue1']),
    'MARKDOWN_LINK_DESTINATION': A(P['cyan']),
    'MARKDOWN_AUTO_LINK': A(P['blue1'], effect=UNDERLINE, effect_color=P['blue1']),
    'MARKDOWN_LIST_ITEM': A(P['yellow'], font=BOLD),
    'MARKDOWN_BLOCK_QUOTE': Comment,
    'HTML_TAG_NAME': A(P['blue1']),
    'HTML_TAG': Text,
    'HTML_ATTRIBUTE_NAME': Type,
    'HTML_ATTRIBUTE_VALUE': String,
    'XML_TAG_NAME': A(P['blue1']),
    'XML_TAG': Text,
    'XML_ATTRIBUTE_NAME': Type,
    'XML_ATTRIBUTE_VALUE': String,
    'XML_PROLOGUE': Macro,
}

# --------------------------------------------------------------------------------------
# Editor chrome, diagnostics, search, VCS, console (nordic native.lua / integrations)
# --------------------------------------------------------------------------------------
EDITOR = {
    # Diagnostics: DiagnosticUnderline* (undercurl), DiagnosticUnnecessary, DiagnosticDeprecated
    'ERRORS_ATTRIBUTES': A(effect=WAVE, effect_color=P['error'], stripe=P['error']),
    'WARNING_ATTRIBUTES': A(effect=WAVE, effect_color=P['warn'], stripe=P['warn']),
    'GENERIC_SERVER_ERROR_OR_WARNING': A(effect=WAVE, effect_color=P['warn'], stripe=P['warn']),
    'WEAK_WARNING_ATTRIBUTES': A(effect=WAVE, effect_color=P['hint'], stripe=P['hint']),
    'INFO_ATTRIBUTES': A(effect=WAVE, effect_color=P['info'], stripe=P['info']),
    'RUNTIME_ERROR': A(effect=WAVE, effect_color=P['error'], stripe=P['error']),
    'WRONG_REFERENCES_ATTRIBUTES': A(effect=WAVE, effect_color=P['error'], stripe=P['error']),
    'BAD_CHARACTER': A(effect=WAVE, effect_color=P['error']),
    'NOT_USED_ELEMENT_ATTRIBUTES': Comment,
    'DEPRECATED_ATTRIBUTES': A(effect=STRIKE, effect_color=P['fg']),
    'MARKED_FOR_REMOVAL_ATTRIBUTES': A(effect=STRIKE, effect_color=P['error']),
    'TYPO': A(effect=WAVE, effect_color=P['hint']),
    'TEXT_STYLE_ERROR': A(effect=WAVE, effect_color=P['error']),
    'TEXT_STYLE_WARNING': A(effect=WAVE, effect_color=P['warn']),
    'TEXT_STYLE_SUGGESTION': A(effect=WAVE, effect_color=P['info']),
    # Search: Search / IncSearch
    'SEARCH_RESULT_ATTRIBUTES': A(P['yellow_bright'], P['bg_visual'], font=BOLD, effect=UNDERLINE, effect_color=P['yellow_bright'], stripe=P['yellow']),
    'WRITE_SEARCH_RESULT_ATTRIBUTES': A(P['yellow_bright'], P['bg_visual'], font=BOLD, effect=UNDERLINE, effect_color=P['orange'], stripe=P['orange']),
    'TEXT_SEARCH_RESULT_ATTRIBUTES': A(P['yellow_bright'], P['bg_visual'], font=BOLD, effect=UNDERLINE, effect_color=P['yellow_bright'], stripe=P['yellow']),
    # References under caret (nvim shows nothing; keep a quiet gray1 so the IDE feature is still usable)
    'IDENTIFIER_UNDER_CARET_ATTRIBUTES': A(bg=P['gray1'], stripe=P['gray5']),
    'WRITE_IDENTIFIER_UNDER_CARET_ATTRIBUTES': A(bg=P['gray1'], effect=UNDERLINE, effect_color=P['gray5'], stripe=P['blue1']),
    # MatchParen = bold + underline (white1)
    'MATCHED_BRACE_ATTRIBUTES': A(font=BOLD, effect=UNDERLINE, effect_color=P['white1']),
    'UNMATCHED_BRACE_ATTRIBUTES': A(P['error'], font=BOLD),
    'MATCHED_TAG_NAME': A(font=BOLD, effect=UNDERLINE, effect_color=P['white1']),
    # TODO: without the treesitter `comment` parser, TODOs render as plain comments; keep a stripe mark only
    'TODO_DEFAULT_ATTRIBUTES': A(P['gray4'], font=ITALIC, stripe=P['yellow_dim']),
    # Links (Link group)
    'HYPERLINK_ATTRIBUTES': A(P['blue1'], effect=UNDERLINE, effect_color=P['blue1']),
    'FOLLOWED_HYPERLINK_ATTRIBUTES': A(P['magenta'], effect=UNDERLINE, effect_color=P['magenta']),
    'INACTIVE_HYPERLINK_ATTRIBUTES': A(effect=UNDERLINE, effect_color=P['gray4']),
    'CTRL_CLICKABLE': A(P['blue1'], effect=UNDERLINE, effect_color=P['blue1']),
    # Folds (Folded)
    'FOLDED_TEXT_ATTRIBUTES': A(P['fg'], P['gray2']),
    # Inlay hints (LspInlayHint -> NonText gray4)
    'INLAY_DEFAULT': A(P['gray4'], P['black2']),
    'INLAY_TEXT_WITHOUT_BACKGROUND': A(P['gray4']),
    'INLINE_PARAMETER_HINT': A(P['gray4'], P['black2']),
    'INLINE_PARAMETER_HINT_CURRENT': A(P['blue1'], P['gray1']),
    'INLINE_PARAMETER_HINT_HIGHLIGHTED': A(P['white1'], P['gray2']),
    'CODE_LENS_BORDER_COLOR': A(effect=BOX, effect_color=P['gray2']),
    # Debugger
    'BREAKPOINT_ATTRIBUTES': A(bg=blend(P['red'], P['bg'], 0.2), stripe=P['red']),
    'EXECUTIONPOINT_ATTRIBUTES': A(bg=blend(P['blue0'], P['bg'], 0.35)),
    'NOT_TOP_FRAME_ATTRIBUTES': A(bg=blend(P['blue0'], P['bg'], 0.15)),
    'DEBUGGER_INLINED_VALUES': A(P['gray5'], font=ITALIC),
    'DEBUGGER_INLINED_VALUES_MODIFIED': A(P['orange'], font=ITALIC),
    'DEBUGGER_INLINED_VALUES_EXECUTION_LINE': A(P['blue1'], font=ITALIC),
    # Live templates / misc
    'LIVE_TEMPLATE_ATTRIBUTES': A(effect=BOX, effect_color=P['blue1']),
    'LIVE_TEMPLATE_INACTIVE_SEGMENT': A(effect=BOX, effect_color=P['gray4']),
    'TEMPLATE_VARIABLE_ATTRIBUTES': A(P['magenta_bright']),
    'INJECTED_LANGUAGE_FRAGMENT': EMPTY,             # e.g. code in doc comments: plain Comment in nvim
    'BOOKMARKS_ATTRIBUTES': A(stripe=P['yellow']),
    'LINE_FULL_COVERAGE': A(P['green'], font=BOLD),
    'LINE_PARTIAL_COVERAGE': A(P['yellow'], font=BOLD),
    'LINE_NONE_COVERAGE': A(P['red'], font=BOLD),
    'BREADCRUMBS_DEFAULT': A(P['gray5']),
    'BREADCRUMBS_HOVERED': A(P['white1'], P['gray1']),
    'BREADCRUMBS_CURRENT': A(P['white1'], P['gray1']),
    'BREADCRUMBS_INACTIVE': A(P['gray4']),
    'DOC_CODE_INLINE': A(P['fg'], P['black2']),
    'DOC_CODE_BLOCK': A(P['fg'], P['black1']),
    # Diff (DiffAdd / DiffDelete / DiffChange / DiffText)
    'DIFF_INSERTED': A(bg=P['diff_add'], stripe=P['green']),
    'DIFF_DELETED': A(bg=P['diff_delete'], stripe=P['red']),
    'DIFF_MODIFIED': A(bg=P['diff_change1'], stripe=P['blue1']),
    'DIFF_CONFLICT': A(bg=blend(P['orange'], P['bg'], 0.2), stripe=P['orange']),
    # Console + built-in terminal (nordic groups/terminal.lua)
    'CONSOLE_NORMAL_OUTPUT': Text,
    'CONSOLE_SYSTEM_OUTPUT': A(P['gray5']),
    'CONSOLE_ERROR_OUTPUT': A(P['error']),
    'CONSOLE_USER_INPUT': A(P['green'], font=ITALIC),
    'CONSOLE_RANGE_TO_EXECUTE': A(effect=BOX, effect_color=P['green']),
    'CONSOLE_BLACK_OUTPUT': A(P['black0']),
    'CONSOLE_RED_OUTPUT': A(P['red']),
    'CONSOLE_GREEN_OUTPUT': A(P['green']),
    'CONSOLE_YELLOW_OUTPUT': A(P['yellow']),
    'CONSOLE_BLUE_OUTPUT': A(P['blue0']),
    'CONSOLE_MAGENTA_OUTPUT': A(P['magenta']),
    'CONSOLE_CYAN_OUTPUT': A(P['cyan']),
    'CONSOLE_GRAY_OUTPUT': A(P['white0']),
    'CONSOLE_DARKGRAY_OUTPUT': A(P['gray2']),
    'CONSOLE_RED_BRIGHT_OUTPUT': A(P['red_bright']),
    'CONSOLE_GREEN_BRIGHT_OUTPUT': A(P['green_bright']),
    'CONSOLE_YELLOW_BRIGHT_OUTPUT': A(P['yellow_bright']),
    'CONSOLE_BLUE_BRIGHT_OUTPUT': A(P['blue2']),
    'CONSOLE_MAGENTA_BRIGHT_OUTPUT': A(P['magenta_bright']),
    'CONSOLE_CYAN_BRIGHT_OUTPUT': A(P['cyan_bright']),
    'CONSOLE_WHITE_OUTPUT': A(P['white1']),
    'LOG_ERROR_OUTPUT': A(P['error']),
    'LOG_WARNING_OUTPUT': A(P['warn']),
    'LOG_INFO_OUTPUT': A(P['blue2']),
    'LOG_VERBOSE_OUTPUT': A(P['gray5']),
    'LOG_DEBUG_OUTPUT': A(P['gray5']),
    'LOG_EXPIRED_ENTRY': A(P['gray4']),
}

COLORS = {
    'CARET_COLOR': P['fg'],                          # Cursor bg
    'CARET_ROW_COLOR': P['bg_cursorline'],
    'SELECTION_BACKGROUND': P['bg_visual'],          # Visual
    'SELECTION_FOREGROUND': '',
    'GUTTER_BACKGROUND': P['bg'],
    'EDITOR_GUTTER_BACKGROUND': P['bg'],
    'CONSOLE_BACKGROUND_KEY': P['bg'],
    'LINE_NUMBERS_COLOR': P['gray2'],                # LineNr (fg_sidebar)
    'LINE_NUMBER_ON_CARET_ROW_COLOR': P['gray5'],    # CursorLineNr
    'INDENT_GUIDE': P['gray1'],                      # IndentBlanklineChar
    'SELECTED_INDENT_GUIDE': P['gray2'],             # IndentBlanklineContextChar
    'VISUAL_INDENT_GUIDE': P['gray1'],
    'MATCHED_BRACES_INDENT_GUIDE_COLOR': P['gray2'],
    'WHITESPACES': P['gray4'],                       # Whitespace
    'SOFT_WRAP_SIGN_COLOR': P['gray4'],
    'RIGHT_MARGIN_COLOR': P['gray1'],
    'METHOD_SEPARATORS_COLOR': P['gray1'],
    'TEARLINE_COLOR': P['gray1'],
    'SELECTED_TEARLINE_COLOR': P['gray2'],
    'FOLDED_TEXT_BORDER_COLOR': P['gray2'],
    'DOC_COMMENT_GUIDE': P['gray1'],
    'DOC_COMMENT_LINK': P['blue1'],
    'ADDED_LINES_COLOR': P['green'],                 # GitSignsAdd
    'MODIFIED_LINES_COLOR': P['blue1'],              # GitSignsChange
    'DELETED_LINES_COLOR': P['red'],                 # GitSignsDelete
    'WHITESPACES_MODIFIED_LINES_COLOR': blend(P['blue1'], P['bg'], 0.5),
    'BORDER_LINES_COLOR': P['gray2'],
    'IGNORED_ADDED_LINES_BORDER_COLOR': P['green'],
    'IGNORED_MODIFIED_LINES_BORDER_COLOR': P['blue1'],
    'IGNORED_DELETED_LINES_BORDER_COLOR': P['red'],
    'DIFF_SEPARATORS_BACKGROUND': P['black2'],
    'ANNOTATIONS_COLOR': P['gray5'],
    'ANNOTATIONS_LAST_COMMIT_COLOR': P['fg'],
    'VCS_ANNOTATIONS_COLOR_1': blend(P['blue0'], P['bg'], 0.45),
    'VCS_ANNOTATIONS_COLOR_2': blend(P['blue0'], P['bg'], 0.33),
    'VCS_ANNOTATIONS_COLOR_3': blend(P['blue0'], P['bg'], 0.22),
    'VCS_ANNOTATIONS_COLOR_4': blend(P['blue0'], P['bg'], 0.12),
    'VCS_ANNOTATIONS_COLOR_5': blend(P['blue0'], P['bg'], 0.05),
    # floats / popups (NormalFloat, Pmenu, FloatBorder)
    'DOCUMENTATION_COLOR': P['bg_float'],
    'LOOKUP_COLOR': P['bg_float'],
    'ERROR_HINT': P['bg_float'],
    'INFORMATION_HINT': P['bg_float'],
    'QUESTION_HINT': P['bg_float'],
    'HINT_BORDER': P['gray2'],
    'NOTIFICATION_BACKGROUND': P['bg_float'],
    'PROMOTION_PANE': P['bg_float'],
    'RECENT_LOCATIONS_SELECTION': P['gray1'],
    'INLINE_REFACTORING_SETTINGS_DEFAULT': P['gray1'],
    'INLINE_REFACTORING_SETTINGS_FOCUSED': P['gray2'],
    'INLINE_REFACTORING_SETTINGS_HOVERED': P['gray2'],
    # file status colours (nvim-tree git integration)
    'FILESTATUS_ADDED': P['green'],
    'FILESTATUS_COPIED': P['green'],
    'FILESTATUS_MODIFIED': P['blue1'],
    'FILESTATUS_RENAMED': P['blue1'],
    'FILESTATUS_NOT_CHANGED_IMMEDIATE': P['blue1'],
    'FILESTATUS_NOT_CHANGED_RECURSIVE': P['blue1'],
    'FILESTATUS_DELETED': P['gray4'],
    'FILESTATUS_UNKNOWN': P['orange'],               # TreeGitUntracked
    'FILESTATUS_IDEA_FILESTATUS_IGNORED': P['gray4'],
    'FILESTATUS_IDEA_FILESTATUS_DELETED_FROM_FILE_SYSTEM': P['gray4'],
    'FILESTATUS_MERGED': P['magenta'],
    'FILESTATUS_IDEA_FILESTATUS_MERGED_WITH_CONFLICTS': P['red'],
    'FILESTATUS_IDEA_FILESTATUS_MERGED_WITH_BOTH_CONFLICTS': P['red'],
    'FILESTATUS_IDEA_FILESTATUS_MERGED_WITH_PROPERTY_CONFLICTS': P['red'],
    'FILESTATUS_changelistConflict': P['red'],
    'FILESTATUS_addedOutside': P['green'],
    'FILESTATUS_modifiedOutside': P['blue1'],
}


# --------------------------------------------------------------------------------------
# Writers
# --------------------------------------------------------------------------------------
def attr_xml(name, a):
    opts = []
    if a['fg']: opts.append(('FOREGROUND', a['fg']))
    if a['bg']: opts.append(('BACKGROUND', a['bg']))
    if a['font']: opts.append(('FONT_TYPE', a['font']))
    if a['stripe']: opts.append(('ERROR_STRIPE_COLOR', a['stripe']))
    if a['effect_color']:
        opts.append(('EFFECT_COLOR', a['effect_color']))
        opts.append(('EFFECT_TYPE', a['effect'] if a['effect'] is not None else BOX))
    if not opts:
        return f'    <option name="{escape(name)}">\n      <value />\n    </option>'
    inner = '\n'.join(f'        <option name="{k}" value="{v}" />' for k, v in opts)
    return f'    <option name="{escape(name)}">\n      <value>\n{inner}\n      </value>\n    </option>'


def scheme_xml():
    attrs = {}
    attrs.update(GENERAL)
    attrs.update(EDITOR)
    attrs.update({'org.rust.' + k: v for k, v in RUST.items()})
    attrs.update({'org.toml.' + k: v for k, v in TOML.items()})
    colors = '\n'.join(f'    <option name="{k}" value="{v}" />' for k, v in sorted(COLORS.items()))
    body = '\n'.join(attr_xml(k, attrs[k]) for k in sorted(attrs))
    return (f'<scheme name="{SCHEME_NAME}" version="142" parent_scheme="Darcula">\n'
            f'  <metaInfo>\n'
            f'    <property name="created">generated by build.py from nordic.nvim</property>\n'
            f'  </metaInfo>\n'
            f'  <colors>\n{colors}\n  </colors>\n'
            f'  <attributes>\n{body}\n  </attributes>\n'
            f'</scheme>\n')


PLUGIN_XML = f'''<idea-plugin>
  <id>io.github.sfra6651.nordic</id>
  <name>Nordic</name>
  <version>{VERSION}</version>
  <vendor url="https://github.com/sfra6651/nordic-rustrover">sfra6651</vendor>
  <description><![CDATA[
    A port of <a href="https://github.com/AlexvZyl/nordic.nvim">nordic.nvim</a> (default options)
    with Rust highlighting mapped from what Neovim actually renders with treesitter and
    rust-analyzer semantic tokens.
    <ul>
      <li><b>Nordic</b> editor color scheme (Settings | Editor | Color Scheme)</li>
      <li><b>Nordic</b> Islands UI theme (Settings | Appearance &amp; Behavior | Appearance)</li>
    </ul>
  ]]></description>
  <change-notes><![CDATA[
    <b>1.0.0</b>: first release: Nordic editor color scheme (every Rust key mapped from Neovim's
    treesitter + rust-analyzer rendering, plus TOML, Markdown, JSON, YAML, console and diagnostics)
    and the Nordic Islands UI theme.
  ]]></change-notes>
  <idea-version since-build="253"/>
  <depends>com.intellij.modules.platform</depends>
  <extensions defaultExtensionNs="com.intellij">
    <bundledColorScheme id="{SCHEME_NAME}" path="/colors/{SCHEME_NAME}.xml"/>
    <themeProvider id="nordic-islands" path="/themes/{SCHEME_NAME}.theme.json" targetUi="islands"/>
  </extensions>
</idea-plugin>
'''


def build():
    os.makedirs(os.path.join(RES, 'META-INF'), exist_ok=True)
    os.makedirs(os.path.join(RES, 'colors'), exist_ok=True)
    with open(os.path.join(RES, 'colors', SCHEME_NAME + '.xml'), 'w') as f:
        f.write(scheme_xml())
    with open(os.path.join(RES, 'META-INF', 'plugin.xml'), 'w') as f:
        f.write(PLUGIN_XML)
    theme = os.path.join(RES, 'themes', SCHEME_NAME + '.theme.json')
    if not os.path.exists(theme):
        sys.exit(f'missing {theme}: run tools/derive_ui_theme.py first')
    os.makedirs(os.path.join(HERE, 'dist'), exist_ok=True)
    out = os.path.join(HERE, 'dist', f'nordic-rustrover-{VERSION}.jar')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for rel in ('META-INF/plugin.xml', 'META-INF/pluginIcon.svg', f'colors/{SCHEME_NAME}.xml', f'themes/{SCHEME_NAME}.theme.json'):
            z.write(os.path.join(RES, rel), rel)
    print('wrote', out)


if __name__ == '__main__':
    build()
