#!/usr/bin/env python3
"""
Cross-platform Text Editor built with PyQt5
Features: File editing, auto-indentation, bracket/quote matching, file tree explorer
"""

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QWidget, QVBoxLayout,
    QHBoxLayout, QTreeView, QSplitter, QFileDialog, QMessageBox,
    QAction, QMenuBar, QToolBar, QStatusBar, QFileSystemModel,
    QInputDialog, QShortcut, QTextEdit, QLabel, QDialog, QPushButton,
    QLineEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QDir, QModelIndex, QRect
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QTextFormat, QKeySequence,
    QTextCursor, QTextCharFormat, QBrush, QPen, QSyntaxHighlighter
)
from PyQt5.QtGui import QTextDocument
import re


class FindReplaceDialog(QDialog):
    """Dialog for finding and replacing text with traverse and case sensitivity options."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.editor = parent.editor if parent else None
        self.current_search_index = -1
        self.search_results = []
        self.setup_ui()
        self.setWindowTitle("Find and Replace")
        self.setGeometry(200, 200, 500, 250)
    
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout()
        
        # Find section
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("Find:"))
        self.find_input = QLineEdit()
        find_layout.addWidget(self.find_input)
        layout.addLayout(find_layout)
        
        # Replace section
        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("Replace:"))
        self.replace_input = QLineEdit()
        replace_layout.addWidget(self.replace_input)
        layout.addLayout(replace_layout)
        
        # Options section
        options_layout = QHBoxLayout()
        self.case_sensitive_checkbox = QCheckBox("Case Sensitive")
        options_layout.addWidget(self.case_sensitive_checkbox)
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # Buttons section
        buttons_layout = QHBoxLayout()
        
        self.find_next_btn = QPushButton("Find Next")
        self.find_next_btn.clicked.connect(self.find_next)
        buttons_layout.addWidget(self.find_next_btn)
        
        self.find_prev_btn = QPushButton("Find Previous")
        self.find_prev_btn.clicked.connect(self.find_previous)
        buttons_layout.addWidget(self.find_prev_btn)
        
        self.replace_btn = QPushButton("Replace")
        self.replace_btn.clicked.connect(self.replace_current)
        buttons_layout.addWidget(self.replace_btn)
        
        self.replace_all_btn = QPushButton("Replace All")
        self.replace_all_btn.clicked.connect(self.replace_all)
        buttons_layout.addWidget(self.replace_all_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_btn)
        
        layout.addLayout(buttons_layout)
        
        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def find_next(self):
        """Find next instance of search text."""
        if not self.editor:
            return
        
        search_text = self.find_input.text()
        if not search_text:
            self.status_label.setText("Please enter search text")
            return
        
        cursor = self.editor.textCursor()
        document = self.editor.document()
        
        # Create search flags based on case sensitivity
        if self.case_sensitive_checkbox.isChecked():
            flags = QTextDocument.FindCaseSensitively
        else:
            flags = QTextDocument.FindFlags()
        
        # Create a new cursor for finding
        find_cursor = QTextCursor(cursor)
        
        # Find from current position
        found = document.find(search_text, find_cursor, flags)
        
        if found.isNull():
            # Wrap around to beginning
            find_cursor = QTextCursor(document)
            find_cursor.movePosition(QTextCursor.Start)
            found = document.find(search_text, find_cursor, flags)
        
        if not found.isNull():
            self.editor.setTextCursor(found)
            self.status_label.setText("Text found")
        else:
            self.status_label.setText("Text not found")
    
    def find_previous(self):
        """Find previous instance of search text."""
        if not self.editor:
            return
        
        search_text = self.find_input.text()
        if not search_text:
            self.status_label.setText("Please enter search text")
            return
        
        cursor = self.editor.textCursor()
        document = self.editor.document()
        
        # Create search flags
        flags = QTextDocument.FindBackward
        if self.case_sensitive_checkbox.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        
        # Create a new cursor for finding
        find_cursor = QTextCursor(cursor)
        
        # Move to start of current selection if text is selected
        if find_cursor.hasSelection():
            find_cursor.setPosition(find_cursor.selectionStart())
        
        # Find backwards from current position
        found = document.find(search_text, find_cursor, flags)
        
        if found.isNull():
            # Wrap around to end
            find_cursor = QTextCursor(document)
            find_cursor.movePosition(QTextCursor.End)
            found = document.find(search_text, find_cursor, flags)
        
        if not found.isNull():
            self.editor.setTextCursor(found)
            self.status_label.setText("Text found")
        else:
            self.status_label.setText("Text not found")
    
    def replace_current(self):
        """Replace current selection with replacement text."""
        if not self.editor:
            return
        
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            replacement_text = self.replace_input.text()
            cursor.insertText(replacement_text)
            self.editor.setTextCursor(cursor)
            self.status_label.setText("Text replaced")
            # Find next after replacement
            self.find_next()
        else:
            self.status_label.setText("No text selected to replace")
    
    def replace_all(self):
        """Replace all instances of search text."""
        if not self.editor:
            return
        
        search_text = self.find_input.text()
        replacement_text = self.replace_input.text()
        
        if not search_text:
            self.status_label.setText("Please enter search text")
            return
        
        document = self.editor.document()
        
        # Create search flags
        if self.case_sensitive_checkbox.isChecked():
            flags = QTextDocument.FindCaseSensitively
        else:
            flags = QTextDocument.FindFlags()
        
        replacement_count = 0
        current_pos = 0
        
        # Keep replacing until no more matches found
        while True:
            # Create cursor at current position
            find_cursor = QTextCursor(document)
            find_cursor.setPosition(current_pos)
            
            # Find next occurrence
            found = document.find(search_text, find_cursor, flags)
            if found.isNull():
                break
            
            # Replace the found text
            found.removeSelectedText()
            found.insertText(replacement_text)
            
            # Move position past the replacement for next search
            current_pos = found.position()
            replacement_count += 1
        
        self.status_label.setText(f"Replaced {replacement_count} instance(s)")


class StripedOverlay(QWidget):
    """Widget displaying diagonal stripes with centered error text."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")
    
    def paintEvent(self, event):
        """Paint diagonal stripes and error text."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw diagonal stripes
        stripe_width = 20
        stripe_spacing = 10
        angle = 45
        
        # Draw stripes across the entire widget
        width = self.width()
        height = self.height()
        
        # Create a light grey color for stripes
        stripe_color = QColor("#5a5a5a")
        painter.setPen(QPen(stripe_color, 2))
        
        # Draw diagonal lines from top-left to bottom-right
        for i in range(-height, width, stripe_width + stripe_spacing):
            x1 = i
            y1 = 0
            x2 = i + height
            y2 = height
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
        # Draw centered error text
        painter.setPen(QColor("#ff6b6b"))
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        painter.setFont(font)
        
        rect = self.rect()
        painter.drawText(rect, Qt.AlignCenter, "Incompatible File Type")


LANGUAGE_DEFINITIONS = {
    'python': {
        'extensions': ['.py', '.pyw', '.pyi'],
        'keywords': [
            'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
            'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
            'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
            'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try',
            'while', 'with', 'yield'
        ],
        'builtins': [
            'abs', 'all', 'any', 'bin', 'bool', 'bytes', 'callable', 'chr',
            'classmethod', 'compile', 'complex', 'dict', 'dir', 'divmod',
            'enumerate', 'eval', 'exec', 'filter', 'float', 'format', 'frozenset',
            'getattr', 'globals', 'hasattr', 'hash', 'help', 'hex', 'id', 'input',
            'int', 'isinstance', 'issubclass', 'iter', 'len', 'list', 'locals',
            'map', 'max', 'memoryview', 'min', 'next', 'object', 'oct', 'open',
            'ord', 'pow', 'print', 'property', 'range', 'repr', 'reversed',
            'round', 'set', 'setattr', 'slice', 'sorted', 'staticmethod', 'str',
            'sum', 'super', 'tuple', 'type', 'vars', 'zip'
        ],
        'comment_single': '#',
        'comment_multi_start': '"""',
        'comment_multi_end': '"""',
        'string_delimiters': ['"', "'"],
        'indent_triggers': [':'],
        'dedent_triggers': ['return', 'break', 'continue', 'pass', 'raise'],
    },
    'javascript': {
        'extensions': ['.js', '.jsx', '.mjs', '.cjs'],
        'keywords': [
            'await', 'break', 'case', 'catch', 'class', 'const', 'continue',
            'debugger', 'default', 'delete', 'do', 'else', 'export', 'extends',
            'finally', 'for', 'function', 'if', 'import', 'in', 'instanceof',
            'let', 'new', 'of', 'return', 'static', 'super', 'switch', 'this',
            'throw', 'try', 'typeof', 'var', 'void', 'while', 'with', 'yield',
            'async', 'enum', 'implements', 'interface', 'package', 'private',
            'protected', 'public'
        ],
        'builtins': [
            'Array', 'Boolean', 'Date', 'Error', 'Function', 'JSON', 'Math',
            'Number', 'Object', 'Promise', 'RegExp', 'String', 'Symbol',
            'console', 'window', 'document', 'undefined', 'null', 'true', 'false',
            'NaN', 'Infinity', 'parseInt', 'parseFloat', 'isNaN', 'isFinite',
            'Map', 'Set', 'WeakMap', 'WeakSet', 'Proxy', 'Reflect'
        ],
        'comment_single': '//',
        'comment_multi_start': '/*',
        'comment_multi_end': '*/',
        'string_delimiters': ['"', "'", '`'],
        'indent_triggers': ['{'],
        'dedent_triggers': [],
    },
    'typescript': {
        'extensions': ['.ts', '.tsx'],
        'keywords': [
            'await', 'break', 'case', 'catch', 'class', 'const', 'continue',
            'debugger', 'default', 'delete', 'do', 'else', 'export', 'extends',
            'finally', 'for', 'function', 'if', 'import', 'in', 'instanceof',
            'let', 'new', 'of', 'return', 'static', 'super', 'switch', 'this',
            'throw', 'try', 'typeof', 'var', 'void', 'while', 'with', 'yield',
            'async', 'enum', 'implements', 'interface', 'package', 'private',
            'protected', 'public', 'type', 'namespace', 'abstract', 'as',
            'readonly', 'declare', 'module', 'keyof', 'infer', 'never', 'unknown'
        ],
        'builtins': [
            'Array', 'Boolean', 'Date', 'Error', 'Function', 'JSON', 'Math',
            'Number', 'Object', 'Promise', 'RegExp', 'String', 'Symbol',
            'console', 'window', 'document', 'undefined', 'null', 'true', 'false',
            'any', 'string', 'number', 'boolean', 'void', 'object'
        ],
        'comment_single': '//',
        'comment_multi_start': '/*',
        'comment_multi_end': '*/',
        'string_delimiters': ['"', "'", '`'],
        'indent_triggers': ['{'],
        'dedent_triggers': [],
    },
    'java': {
        'extensions': ['.java'],
        'keywords': [
            'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch',
            'char', 'class', 'const', 'continue', 'default', 'do', 'double',
            'else', 'enum', 'extends', 'final', 'finally', 'float', 'for',
            'goto', 'if', 'implements', 'import', 'instanceof', 'int',
            'interface', 'long', 'native', 'new', 'package', 'private',
            'protected', 'public', 'return', 'short', 'static', 'strictfp',
            'super', 'switch', 'synchronized', 'this', 'throw', 'throws',
            'transient', 'try', 'void', 'volatile', 'while'
        ],
        'builtins': [
            'String', 'System', 'Integer', 'Double', 'Float', 'Boolean',
            'Character', 'Byte', 'Short', 'Long', 'Object', 'Class',
            'Exception', 'RuntimeException', 'Thread', 'Runnable',
            'true', 'false', 'null'
        ],
        'comment_single': '//',
        'comment_multi_start': '/*',
        'comment_multi_end': '*/',
        'string_delimiters': ['"'],
        'indent_triggers': ['{'],
        'dedent_triggers': [],
    },
    'c': {
        'extensions': ['.c', '.h'],
        'keywords': [
            'auto', 'break', 'case', 'char', 'const', 'continue', 'default',
            'do', 'double', 'else', 'enum', 'extern', 'float', 'for', 'goto',
            'if', 'inline', 'int', 'long', 'register', 'restrict', 'return',
            'short', 'signed', 'sizeof', 'static', 'struct', 'switch',
            'typedef', 'union', 'unsigned', 'void', 'volatile', 'while',
            '_Bool', '_Complex', '_Imaginary'
        ],
        'builtins': [
            'NULL', 'EOF', 'stdin', 'stdout', 'stderr', 'printf', 'scanf',
            'malloc', 'free', 'sizeof', 'true', 'false'
        ],
        'comment_single': '//',
        'comment_multi_start': '/*',
        'comment_multi_end': '*/',
        'string_delimiters': ['"'],
        'indent_triggers': ['{'],
        'dedent_triggers': [],
    },
    'cpp': {
        'extensions': ['.cpp', '.cxx', '.cc', '.hpp', '.hxx', '.hh'],
        'keywords': [
            'alignas', 'alignof', 'and', 'and_eq', 'asm', 'auto', 'bitand',
            'bitor', 'bool', 'break', 'case', 'catch', 'char', 'char16_t',
            'char32_t', 'class', 'compl', 'concept', 'const', 'consteval',
            'constexpr', 'constinit', 'const_cast', 'continue', 'co_await',
            'co_return', 'co_yield', 'decltype', 'default', 'delete', 'do',
            'double', 'dynamic_cast', 'else', 'enum', 'explicit', 'export',
            'extern', 'false', 'float', 'for', 'friend', 'goto', 'if', 'inline',
            'int', 'long', 'mutable', 'namespace', 'new', 'noexcept', 'not',
            'not_eq', 'nullptr', 'operator', 'or', 'or_eq', 'private',
            'protected', 'public', 'register', 'reinterpret_cast', 'requires',
            'return', 'short', 'signed', 'sizeof', 'static', 'static_assert',
            'static_cast', 'struct', 'switch', 'template', 'this', 'thread_local',
            'throw', 'true', 'try', 'typedef', 'typeid', 'typename', 'union',
            'unsigned', 'using', 'virtual', 'void', 'volatile', 'wchar_t',
            'while', 'xor', 'xor_eq'
        ],
        'builtins': [
            'std', 'cout', 'cin', 'endl', 'string', 'vector', 'map', 'set',
            'list', 'queue', 'stack', 'pair', 'make_pair', 'unique_ptr',
            'shared_ptr', 'weak_ptr', 'NULL', 'nullptr'
        ],
        'comment_single': '//',
        'comment_multi_start': '/*',
        'comment_multi_end': '*/',
        'string_delimiters': ['"'],
        'indent_triggers': ['{'],
        'dedent_triggers': [],
    },
    'csharp': {
        'extensions': ['.cs'],
        'keywords': [
            'abstract', 'as', 'base', 'bool', 'break', 'byte', 'case', 'catch',
            'char', 'checked', 'class', 'const', 'continue', 'decimal', 'default',
            'delegate', 'do', 'double', 'else', 'enum', 'event', 'explicit',
            'extern', 'false', 'finally', 'fixed', 'float', 'for', 'foreach',
            'goto', 'if', 'implicit', 'in', 'int', 'interface', 'internal', 'is',
            'lock', 'long', 'namespace', 'new', 'null', 'object', 'operator',
            'out', 'override', 'params', 'private', 'protected', 'public',
            'readonly', 'ref', 'return', 'sbyte', 'sealed', 'short', 'sizeof',
            'stackalloc', 'static', 'string', 'struct', 'switch', 'this', 'throw',
            'true', 'try', 'typeof', 'uint', 'ulong', 'unchecked', 'unsafe',
            'ushort', 'using', 'virtual', 'void', 'volatile', 'while', 'async',
            'await', 'var', 'dynamic', 'yield', 'partial', 'get', 'set', 'add',
            'remove', 'value', 'where', 'select', 'from', 'orderby', 'group'
        ],
        'builtins': [
            'Console', 'String', 'Int32', 'Int64', 'Double', 'Boolean', 'Object',
            'Array', 'List', 'Dictionary', 'Exception', 'Task', 'Action', 'Func'
        ],
        'comment_single': '//',
        'comment_multi_start': '/*',
        'comment_multi_end': '*/',
        'string_delimiters': ['"'],
        'indent_triggers': ['{'],
        'dedent_triggers': [],
    },
    'go': {
        'extensions': ['.go'],
        'keywords': [
            'break', 'case', 'chan', 'const', 'continue', 'default', 'defer',
            'else', 'fallthrough', 'for', 'func', 'go', 'goto', 'if', 'import',
            'interface', 'map', 'package', 'range', 'return', 'select', 'struct',
            'switch', 'type', 'var'
        ],
        'builtins': [
            'bool', 'byte', 'complex64', 'complex128', 'error', 'float32',
            'float64', 'int', 'int8', 'int16', 'int32', 'int64', 'rune', 'string',
            'uint', 'uint8', 'uint16', 'uint32', 'uint64', 'uintptr', 'true',
            'false', 'iota', 'nil', 'append', 'cap', 'close', 'complex', 'copy',
            'delete', 'imag', 'len', 'make', 'new', 'panic', 'print', 'println',
            'real', 'recover'
        ],
        'comment_single': '//',
        'comment_multi_start': '/*',
        'comment_multi_end': '*/',
        'string_delimiters': ['"', '`'],
        'indent_triggers': ['{'],
        'dedent_triggers': [],
    },
    'rust': {
        'extensions': ['.rs'],
        'keywords': [
            'as', 'async', 'await', 'break', 'const', 'continue', 'crate', 'dyn',
            'else', 'enum', 'extern', 'false', 'fn', 'for', 'if', 'impl', 'in',
            'let', 'loop', 'match', 'mod', 'move', 'mut', 'pub', 'ref', 'return',
            'self', 'Self', 'static', 'struct', 'super', 'trait', 'true', 'type',
            'unsafe', 'use', 'where', 'while'
        ],
        'builtins': [
            'bool', 'char', 'str', 'u8', 'u16', 'u32', 'u64', 'u128', 'usize',
            'i8', 'i16', 'i32', 'i64', 'i128', 'isize', 'f32', 'f64', 'String',
            'Vec', 'Option', 'Result', 'Box', 'Rc', 'Arc', 'Cell', 'RefCell',
            'Some', 'None', 'Ok', 'Err', 'println', 'print', 'format', 'panic'
        ],
        'comment_single': '//',
        'comment_multi_start': '/*',
        'comment_multi_end': '*/',
        'string_delimiters': ['"'],
        'indent_triggers': ['{'],
        'dedent_triggers': [],
    },
    'html': {
        'extensions': ['.html', '.htm', '.xhtml'],
        'keywords': [],
        'builtins': [],
        'tags': [
            'html', 'head', 'body', 'div', 'span', 'p', 'a', 'img', 'table',
            'tr', 'td', 'th', 'ul', 'ol', 'li', 'form', 'input', 'button',
            'select', 'option', 'textarea', 'label', 'h1', 'h2', 'h3', 'h4',
            'h5', 'h6', 'header', 'footer', 'nav', 'section', 'article', 'aside',
            'main', 'script', 'style', 'link', 'meta', 'title', 'br', 'hr',
            'strong', 'em', 'code', 'pre', 'blockquote', 'iframe', 'video',
            'audio', 'canvas', 'svg', 'path'
        ],
        'comment_single': None,
        'comment_multi_start': '<!--',
        'comment_multi_end': '-->',
        'string_delimiters': ['"', "'"],
        'indent_triggers': ['>'],
        'dedent_triggers': [],
    },
    'css': {
        'extensions': ['.css', '.scss', '.sass', '.less'],
        'keywords': [
            'important', 'and', 'or', 'not', 'only', 'screen', 'print', 'all',
            'media', 'keyframes', 'from', 'to', 'import', 'charset', 'font-face',
            'supports', 'page', 'namespace'
        ],
        'builtins': [],
        'properties': [
            'color', 'background', 'background-color', 'background-image',
            'border', 'border-radius', 'margin', 'padding', 'width', 'height',
            'display', 'position', 'top', 'left', 'right', 'bottom', 'float',
            'clear', 'font', 'font-size', 'font-family', 'font-weight',
            'text-align', 'text-decoration', 'line-height', 'overflow',
            'visibility', 'opacity', 'z-index', 'flex', 'grid', 'transform',
            'transition', 'animation', 'box-shadow', 'cursor'
        ],
        'comment_single': None,
        'comment_multi_start': '/*',
        'comment_multi_end': '*/',
        'string_delimiters': ['"', "'"],
        'indent_triggers': ['{'],
        'dedent_triggers': [],
    },
    'json': {
        'extensions': ['.json'],
        'keywords': ['true', 'false', 'null'],
        'builtins': [],
        'comment_single': None,
        'comment_multi_start': None,
        'comment_multi_end': None,
        'string_delimiters': ['"'],
        'indent_triggers': ['{', '['],
        'dedent_triggers': [],
    },
    'xml': {
        'extensions': ['.xml', '.xsl', '.xslt', '.svg'],
        'keywords': [],
        'builtins': [],
        'comment_single': None,
        'comment_multi_start': '<!--',
        'comment_multi_end': '-->',
        'string_delimiters': ['"', "'"],
        'indent_triggers': ['>'],
        'dedent_triggers': [],
    },
    'sql': {
        'extensions': ['.sql'],
        'keywords': [
            'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'INSERT', 'INTO',
            'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE', 'DROP',
            'ALTER', 'INDEX', 'VIEW', 'TRIGGER', 'PROCEDURE', 'FUNCTION',
            'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'FULL', 'ON', 'AS',
            'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET', 'UNION',
            'ALL', 'DISTINCT', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'NULL',
            'IS', 'IN', 'LIKE', 'BETWEEN', 'EXISTS', 'PRIMARY', 'KEY',
            'FOREIGN', 'REFERENCES', 'UNIQUE', 'CHECK', 'DEFAULT', 'CONSTRAINT',
            'ASC', 'DESC', 'BEGIN', 'COMMIT', 'ROLLBACK', 'TRANSACTION'
        ],
        'builtins': [
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'COALESCE', 'NULLIF',
            'CAST', 'CONVERT', 'SUBSTRING', 'TRIM', 'UPPER', 'LOWER',
            'LENGTH', 'CONCAT', 'NOW', 'DATE', 'TIME', 'DATETIME',
            'INTEGER', 'VARCHAR', 'TEXT', 'BOOLEAN', 'FLOAT', 'DECIMAL'
        ],
        'comment_single': '--',
        'comment_multi_start': '/*',
        'comment_multi_end': '*/',
        'string_delimiters': ["'"],
        'indent_triggers': [],
        'dedent_triggers': [],
    },
    'bash': {
        'extensions': ['.sh', '.bash', '.zsh'],
        'keywords': [
            'if', 'then', 'else', 'elif', 'fi', 'case', 'esac', 'for', 'while',
            'until', 'do', 'done', 'in', 'function', 'select', 'time', 'coproc',
            'local', 'return', 'exit', 'break', 'continue', 'export', 'readonly',
            'declare', 'typeset', 'unset', 'shift', 'trap', 'source'
        ],
        'builtins': [
            'echo', 'printf', 'read', 'cd', 'pwd', 'pushd', 'popd', 'dirs',
            'let', 'eval', 'set', 'test', 'true', 'false', 'exec', 'command',
            'type', 'hash', 'alias', 'unalias', 'bind', 'builtin', 'caller',
            'enable', 'help', 'logout', 'mapfile', 'readarray', 'ulimit', 'umask'
        ],
        'comment_single': '#',
        'comment_multi_start': None,
        'comment_multi_end': None,
        'string_delimiters': ['"', "'"],
        'indent_triggers': ['then', 'do', '{'],
        'dedent_triggers': ['fi', 'done', 'esac'],
    },
    'ruby': {
        'extensions': ['.rb', '.rake', '.gemspec'],
        'keywords': [
            'BEGIN', 'END', 'alias', 'and', 'begin', 'break', 'case', 'class',
            'def', 'defined?', 'do', 'else', 'elsif', 'end', 'ensure', 'false',
            'for', 'if', 'in', 'module', 'next', 'nil', 'not', 'or', 'redo',
            'rescue', 'retry', 'return', 'self', 'super', 'then', 'true',
            'undef', 'unless', 'until', 'when', 'while', 'yield', '__FILE__',
            '__LINE__', '__ENCODING__', 'attr_reader', 'attr_writer', 'attr_accessor',
            'private', 'protected', 'public', 'require', 'require_relative', 'include',
            'extend', 'prepend', 'raise', 'lambda', 'proc'
        ],
        'builtins': [
            'Array', 'Hash', 'String', 'Integer', 'Float', 'Symbol', 'TrueClass',
            'FalseClass', 'NilClass', 'Object', 'Class', 'Module', 'Proc',
            'Method', 'Range', 'Regexp', 'IO', 'File', 'Dir', 'Time', 'Date',
            'puts', 'print', 'p', 'gets', 'chomp', 'to_s', 'to_i', 'to_f', 'to_a'
        ],
        'comment_single': '#',
        'comment_multi_start': '=begin',
        'comment_multi_end': '=end',
        'string_delimiters': ['"', "'"],
        'indent_triggers': ['do', 'then', '{'],
        'dedent_triggers': ['end'],
    },
    'php': {
        'extensions': ['.php', '.phtml', '.php3', '.php4', '.php5', '.phps'],
        'keywords': [
            'abstract', 'and', 'array', 'as', 'break', 'callable', 'case',
            'catch', 'class', 'clone', 'const', 'continue', 'declare', 'default',
            'die', 'do', 'echo', 'else', 'elseif', 'empty', 'enddeclare',
            'endfor', 'endforeach', 'endif', 'endswitch', 'endwhile', 'eval',
            'exit', 'extends', 'final', 'finally', 'for', 'foreach', 'function',
            'global', 'goto', 'if', 'implements', 'include', 'include_once',
            'instanceof', 'insteadof', 'interface', 'isset', 'list', 'namespace',
            'new', 'or', 'print', 'private', 'protected', 'public', 'require',
            'require_once', 'return', 'static', 'switch', 'throw', 'trait',
            'try', 'unset', 'use', 'var', 'while', 'xor', 'yield', 'yield from',
            'fn', 'match'
        ],
        'builtins': [
            'true', 'false', 'null', 'self', 'parent', 'this', '__CLASS__',
            '__DIR__', '__FILE__', '__FUNCTION__', '__LINE__', '__METHOD__',
            '__NAMESPACE__', '__TRAIT__'
        ],
        'comment_single': '//',
        'comment_multi_start': '/*',
        'comment_multi_end': '*/',
        'string_delimiters': ['"', "'"],
        'indent_triggers': ['{', ':'],
        'dedent_triggers': [],
    },
    'markdown': {
        'extensions': ['.md', '.markdown', '.mdown', '.mkd'],
        'keywords': [],
        'builtins': [],
        'comment_single': None,
        'comment_multi_start': None,
        'comment_multi_end': None,
        'string_delimiters': [],
        'indent_triggers': [],
        'dedent_triggers': [],
    },
    'yaml': {
        'extensions': ['.yml', '.yaml'],
        'keywords': ['true', 'false', 'null', 'yes', 'no', 'on', 'off'],
        'builtins': [],
        'comment_single': '#',
        'comment_multi_start': None,
        'comment_multi_end': None,
        'string_delimiters': ['"', "'"],
        'indent_triggers': [':'],
        'dedent_triggers': [],
    },
    'toml': {
        'extensions': ['.toml'],
        'keywords': ['true', 'false'],
        'builtins': [],
        'comment_single': '#',
        'comment_multi_start': None,
        'comment_multi_end': None,
        'string_delimiters': ['"', "'"],
        'indent_triggers': [],
        'dedent_triggers': [],
    },
}


def get_language_for_file(file_path):
    """Determine language from file extension."""
    if not file_path:
        return None
    ext = os.path.splitext(file_path)[1].lower()
    for lang, definition in LANGUAGE_DEFINITIONS.items():
        if ext in definition['extensions']:
            return lang
    return None


class SyntaxHighlighter(QSyntaxHighlighter):
    """Multi-language syntax highlighter using static definitions."""
    
    COLORS = {
        'keyword': '#569cd6',
        'builtin': '#4ec9b0',
        'string': '#ce9178',
        'comment': '#6a9955',
        'number': '#b5cea8',
        'operator': '#d4d4d4',
        'function': '#dcdcaa',
        'class': '#4ec9b0',
        'decorator': '#d7ba7d',
        'tag': '#569cd6',
        'attribute': '#9cdcfe',
        'property': '#9cdcfe',
    }
    
    def __init__(self, document, language=None):
        super().__init__(document)
        self.language = language
        self.highlighting_rules = []
        self.multi_line_comment_start = None
        self.multi_line_comment_end = None
        self.multi_line_string_char = None
        
        self._setup_formats()
        if language:
            self.set_language(language)
    
    def _setup_formats(self):
        """Set up text formats for different token types."""
        self.formats = {}
        for name, color in self.COLORS.items():
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if name == 'keyword':
                fmt.setFontWeight(QFont.Bold)
            self.formats[name] = fmt
    
    def set_language(self, language):
        """Set the language and update highlighting rules."""
        self.language = language
        self.highlighting_rules = []
        
        if language not in LANGUAGE_DEFINITIONS:
            self.rehighlight()
            return
        
        lang_def = LANGUAGE_DEFINITIONS[language]
        
        # Add preprocessor directive handling for C, C++
        if language in ('c', 'cpp'):
            # Highlight preprocessor directives (#include, #define, etc.) as keywords (including the # symbol)
            self.highlighting_rules.append((re.compile(r'#\s*(?:include|define|ifdef|ifndef|if|else|elif|endif|pragma|error|warning|undef)\b'), 'keyword'))
            # Highlight angle bracket includes <...> and quoted includes "..."
            self.highlighting_rules.append((re.compile(r'<[^>]+>'), 'string'))
        
        if lang_def.get('keywords'):
            pattern = r'\b(' + '|'.join(re.escape(kw) for kw in lang_def['keywords']) + r')\b'
            self.highlighting_rules.append((re.compile(pattern, re.IGNORECASE if language == 'sql' else 0), 'keyword'))
        
        if lang_def.get('builtins'):
            pattern = r'\b(' + '|'.join(re.escape(b) for b in lang_def['builtins']) + r')\b'
            self.highlighting_rules.append((re.compile(pattern), 'builtin'))
        
        if lang_def.get('tags'):
            pattern = r'</?(' + '|'.join(lang_def['tags']) + r')(?:\s|>|/)'
            self.highlighting_rules.append((re.compile(pattern, re.IGNORECASE), 'tag'))
        
        if lang_def.get('properties'):
            pattern = r'\b(' + '|'.join(re.escape(p) for p in lang_def['properties']) + r')\s*:'
            self.highlighting_rules.append((re.compile(pattern), 'property'))
        
        self.highlighting_rules.append((re.compile(r'\b[0-9]+\.?[0-9]*([eE][+-]?[0-9]+)?\b'), 'number'))
        self.highlighting_rules.append((re.compile(r'\b0x[0-9a-fA-F]+\b'), 'number'))
        
        self.highlighting_rules.append((re.compile(r'\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\()'), 'function'))
        
        if language == 'python':
            self.highlighting_rules.append((re.compile(r'@[A-Za-z_][A-Za-z0-9_]*'), 'decorator'))
            self.highlighting_rules.append((re.compile(r'\bclass\s+([A-Za-z_][A-Za-z0-9_]*)'), 'class'))
        
        if language in ('html', 'xml'):
            self.highlighting_rules.append((re.compile(r'\s([a-zA-Z-]+)='), 'attribute'))
        
        for delim in lang_def.get('string_delimiters', []):
            if delim == '"':
                self.highlighting_rules.append((re.compile(r'"(?:[^"\\]|\\.)*"'), 'string'))
            elif delim == "'":
                self.highlighting_rules.append((re.compile(r"'(?:[^'\\]|\\.)*'"), 'string'))
            elif delim == '`':
                self.highlighting_rules.append((re.compile(r'`(?:[^`\\]|\\.)*`'), 'string'))
        
        if lang_def.get('comment_single'):
            pattern = re.escape(lang_def['comment_single']) + r'.*$'
            self.highlighting_rules.append((re.compile(pattern), 'comment'))
        
        self.multi_line_comment_start = lang_def.get('comment_multi_start')
        self.multi_line_comment_end = lang_def.get('comment_multi_end')
        
        if language == 'python':
            self.multi_line_string_char = '"""'
        
        self.rehighlight()
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text."""
        for pattern, format_name in self.highlighting_rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - match.start()
                if match.lastindex:
                    start = match.start(1)
                    length = match.end(1) - match.start(1)
                self.setFormat(start, length, self.formats[format_name])
        
        self._highlight_multiline(text)
    
    def _highlight_multiline(self, text):
        """Handle multi-line comments and strings."""
        if not self.multi_line_comment_start:
            return
        
        self.setCurrentBlockState(0)
        
        start_index = 0
        if self.previousBlockState() != 1:
            start_index = text.find(self.multi_line_comment_start)
        
        while start_index >= 0:
            end_index = text.find(self.multi_line_comment_end, start_index + len(self.multi_line_comment_start))
            
            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = end_index - start_index + len(self.multi_line_comment_end)
            
            self.setFormat(start_index, comment_length, self.formats['comment'])
            start_index = text.find(self.multi_line_comment_start, start_index + comment_length)


class LineNumberArea(QWidget):
    """Widget for displaying line numbers alongside the editor."""
    
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
    
    def sizeHint(self):
        return self.editor.line_number_area_width(), 0
    
    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """Custom text editor with auto-indentation and bracket/quote matching."""
    
    BRACKETS = {
        '(': ')',
        '[': ']',
        '{': '}',
    }
    CLOSING_BRACKETS = {v: k for k, v in BRACKETS.items()}
    QUOTES = ['"', "'", '`']
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file = None
        self.current_language = None
        self.highlighter = None
        self.is_invalid_file = False
        
        self._setup_editor()
        self._setup_line_numbers()
        self._setup_highlighter()
    
    def _setup_editor(self):
        """Configure editor appearance and behavior."""
        font = QFont("Monospace", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.setTabStopWidth(4 * self.fontMetrics().horizontalAdvance(' '))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        
        self.bracket_positions = []
    
    def _setup_line_numbers(self):
        """Set up line number display."""
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.cursorPositionChanged.connect(self.match_brackets)
        self.update_line_number_area_width(0)
    
    def _setup_highlighter(self):
        """Set up syntax highlighter."""
        self.highlighter = SyntaxHighlighter(self.document())
    
    def set_language(self, language):
        """Set the current language for syntax highlighting and indentation."""
        self.current_language = language
        if self.highlighter:
            self.highlighter.set_language(language)
    
    def set_language_from_file(self, file_path):
        """Auto-detect and set language from file extension."""
        language = get_language_for_file(file_path)
        self.set_language(language)
    
    @property
    def is_modified(self):
        """Check if document has been modified."""
        return self.document().isModified()
    
    @is_modified.setter
    def is_modified(self, value):
        """Set document modification state."""
        self.document().setModified(value)
    
    def line_number_area_width(self):
        """Calculate width needed for line numbers."""
        digits = len(str(max(1, self.blockCount())))
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space
    
    def update_line_number_area_width(self, _):
        """Update editor margins for line numbers."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
    
    def update_line_number_area(self, rect, dy):
        """Scroll line number area with editor."""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), 
                                         self.line_number_area.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)
    
    def resizeEvent(self, event):
        """Handle editor resize."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )
    
    def line_number_area_paint_event(self, event):
        """Paint line numbers."""
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#2b2b2b"))
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#858585"))
                painter.drawText(
                    0, top, self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignRight, number
                )
            
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1
    
    def highlight_current_line(self):
        """Highlight the line containing the cursor."""
        extra_selections = []
        
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#3a3a3a")
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        
        for pos in self.bracket_positions:
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#4a6a4a"))
            cursor = self.textCursor()
            cursor.setPosition(pos)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            selection.cursor = cursor
            extra_selections.append(selection)
        
        self.setExtraSelections(extra_selections)
    
    def match_brackets(self):
        """Find and highlight matching brackets."""
        self.bracket_positions = []
        cursor = self.textCursor()
        pos = cursor.position()
        text = self.toPlainText()
        
        if not text:
            return
        
        char_at = text[pos] if pos < len(text) else ''
        char_before = text[pos - 1] if pos > 0 else ''
        
        if char_at in self.BRACKETS:
            match_pos = self._find_matching_bracket(text, pos, char_at, self.BRACKETS[char_at], 1)
            if match_pos is not None:
                self.bracket_positions = [pos, match_pos]
        elif char_at in self.CLOSING_BRACKETS:
            match_pos = self._find_matching_bracket(text, pos, char_at, self.CLOSING_BRACKETS[char_at], -1)
            if match_pos is not None:
                self.bracket_positions = [pos, match_pos]
        elif char_before in self.BRACKETS:
            match_pos = self._find_matching_bracket(text, pos - 1, char_before, self.BRACKETS[char_before], 1)
            if match_pos is not None:
                self.bracket_positions = [pos - 1, match_pos]
        elif char_before in self.CLOSING_BRACKETS:
            match_pos = self._find_matching_bracket(text, pos - 1, char_before, self.CLOSING_BRACKETS[char_before], -1)
            if match_pos is not None:
                self.bracket_positions = [pos - 1, match_pos]
        
        self.highlight_current_line()
    
    def _find_matching_bracket(self, text, start, open_char, close_char, direction):
        """Find position of matching bracket."""
        count = 0
        pos = start
        
        while 0 <= pos < len(text):
            if text[pos] == open_char:
                count += direction
            elif text[pos] == close_char:
                count -= direction
            
            if count == 0:
                return pos
            pos += direction
        
        return None
    
    def keyPressEvent(self, event):
        """Handle special key presses for auto-indent and bracket matching."""
        key = event.key()
        text = event.text()
        cursor = self.textCursor()
        
        if key == Qt.Key_Up:
            if cursor.blockNumber() == 0:
                cursor.movePosition(QTextCursor.StartOfLine)
                self.setTextCursor(cursor)
                return
        
        if key == Qt.Key_Down:
            if cursor.blockNumber() == self.document().blockCount() - 1:
                cursor.movePosition(QTextCursor.EndOfLine)
                self.setTextCursor(cursor)
                return
        
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self._handle_enter(cursor)
            return
        
        if key == Qt.Key_Tab:
            if cursor.hasSelection():
                self._indent_selection(cursor, True)
            else:
                cursor.insertText("    ")
            return
        
        if key == Qt.Key_Backtab:
            self._indent_selection(cursor, False)
            return
        
        if text in self.BRACKETS:
            cursor.insertText(text + self.BRACKETS[text])
            cursor.movePosition(QTextCursor.Left)
            self.setTextCursor(cursor)
            return
        
        if text in self.QUOTES:
            doc_text = self.toPlainText()
            pos = cursor.position()
            char_after = doc_text[pos] if pos < len(doc_text) else ''
            
            if char_after == text:
                cursor.movePosition(QTextCursor.Right)
                self.setTextCursor(cursor)
                return
            else:
                cursor.insertText(text + text)
                cursor.movePosition(QTextCursor.Left)
                self.setTextCursor(cursor)
                return
        
        if text in self.CLOSING_BRACKETS:
            doc_text = self.toPlainText()
            pos = cursor.position()
            char_after = doc_text[pos] if pos < len(doc_text) else ''
            
            if char_after == text:
                cursor.movePosition(QTextCursor.Right)
                self.setTextCursor(cursor)
                return
        
        if key == Qt.Key_Backspace:
            pos = cursor.position()
            doc_text = self.toPlainText()
            
            if pos > 0 and pos < len(doc_text):
                char_before = doc_text[pos - 1]
                char_after = doc_text[pos]
                
                if ((char_before in self.BRACKETS and char_after == self.BRACKETS[char_before]) or
                    (char_before in self.QUOTES and char_after == char_before)):
                    cursor.deleteChar()
        
        super().keyPressEvent(event)
    
    def _handle_enter(self, cursor):
        """Handle enter key with language-aware auto-indentation."""
        line = cursor.block().text()
        indent = ""
        for char in line:
            if char in (' ', '\t'):
                indent += char
            else:
                break
        
        text_before = line[:cursor.positionInBlock()].rstrip()
        
        should_indent = False
        if text_before:
            if text_before[-1] in self.BRACKETS:
                should_indent = True
            elif self.current_language and self.current_language in LANGUAGE_DEFINITIONS:
                lang_def = LANGUAGE_DEFINITIONS[self.current_language]
                for trigger in lang_def.get('indent_triggers', []):
                    if text_before.endswith(trigger):
                        should_indent = True
                        break
        
        if should_indent:
            indent += "    "
        
        pos = cursor.position()
        doc_text = self.toPlainText()
        char_before = doc_text[pos - 1] if pos > 0 else ''
        char_after = doc_text[pos] if pos < len(doc_text) else ''
        
        if char_before in self.BRACKETS and char_after == self.BRACKETS[char_before]:
            base_indent = ""
            for char in line:
                if char in (' ', '\t'):
                    base_indent += char
                else:
                    break
            cursor.insertText("\n" + indent + "\n" + base_indent)
            cursor.movePosition(QTextCursor.Up)
            cursor.movePosition(QTextCursor.EndOfLine)
            self.setTextCursor(cursor)
        else:
            cursor.insertText("\n" + indent)
    
    def _indent_selection(self, cursor, indent):
        """Indent or unindent selected lines."""
        if not cursor.hasSelection():
            return
        
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.StartOfBlock)
        start_block = cursor.blockNumber()
        
        cursor.setPosition(end)
        if cursor.atBlockStart() and end > start:
            cursor.movePosition(QTextCursor.Left)
        end_block = cursor.blockNumber()
        
        cursor.beginEditBlock()
        
        for block_num in range(start_block, end_block + 1):
            cursor.setPosition(self.document().findBlockByNumber(block_num).position())
            if indent:
                cursor.insertText("    ")
            else:
                line = cursor.block().text()
                if line.startswith("    "):
                    for _ in range(4):
                        cursor.deleteChar()
                elif line.startswith("\t"):
                    cursor.deleteChar()
        
        cursor.endEditBlock()


class FileTreeView(QTreeView):
    """File system tree view with collapsible folders."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.homePath())
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)
        
        self.setModel(self.model)
        self.setRootIndex(self.model.index(QDir.homePath()))
        
        self.hideColumn(1)
        self.hideColumn(2)
        self.hideColumn(3)
        
        self.setHeaderHidden(True)
        self.setAnimated(True)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)
    
    def set_root_path(self, path):
        """Set the root directory for the file tree."""
        if os.path.isdir(path):
            self.model.setRootPath(path)
            self.setRootIndex(self.model.index(path))
    
    def get_file_path(self, index):
        """Get the file path for a given index."""
        return self.model.filePath(index)
    
    def is_directory(self, index):
        """Check if index is a directory."""
        return self.model.isDir(index)
    
    def select_file(self, file_path):
        """Select and highlight a file in the tree, expanding parent directories."""
        if not file_path or not os.path.exists(file_path):
            return
        
        index = self.model.index(file_path)
        if not index.isValid():
            return
        
        # Expand all ancestors from root to file
        parent = index.parent()
        while parent.isValid():
            self.expand(parent)
            parent = parent.parent()
        
        self.setCurrentIndex(index)
        self.scrollTo(index)
    
    def cleanup_explorer(self, current_file_path):
        """Collapse all directories except for ancestors of the current file."""
        if not current_file_path or not os.path.exists(current_file_path):
            # If no file is open, collapse everything
            self.collapseAll()
            return
        
        index = self.model.index(current_file_path)
        if not index.isValid():
            self.collapseAll()
            return
        
        # Collect all ancestor indices of the current file
        ancestors = set()
        parent = index.parent()
        while parent.isValid():
            ancestors.add(parent)
            parent = parent.parent()
        
        # Collapse only directories that are not ancestors of the current file
        self._collapse_non_ancestors(self.rootIndex(), ancestors)
    
    def _collapse_non_ancestors(self, parent_index, ancestors):
        """Recursively collapse directories that are not ancestors of the target file."""
        row_count = self.model.rowCount(parent_index)
        for row in range(row_count):
            child_index = self.model.index(row, 0, parent_index)
            if not child_index.isValid():
                continue
            if self.model.isDir(child_index):
                if child_index in ancestors:
                    # Recurse into ancestors to collapse their non-ancestor children
                    self._collapse_non_ancestors(child_index, ancestors)
                else:
                    # Collapse non-ancestor directories
                    self.collapse(child_index)


class TextEditor(QMainWindow):
    """Main text editor window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Text Editor")
        self.setGeometry(100, 100, 1200, 800)
        
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._setup_shortcuts()
        
        self._apply_dark_theme()
    
    def _setup_ui(self):
        """Set up the main UI components."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_layout = QHBoxLayout(self.central_widget)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal)
        
        self.file_tree = FileTreeView()
        self.file_tree.setMinimumWidth(200)
        self.file_tree.setMaximumWidth(400)
        self.file_tree.doubleClicked.connect(self._on_file_double_clicked)
        
        self.editor = CodeEditor()
        
        splitter.addWidget(self.file_tree)
        splitter.addWidget(self.editor)
        splitter.setSizes([250, 950])
        
        self.central_layout.addWidget(splitter)
        self.splitter = splitter
    
    def _setup_menu(self):
        """Set up the menu bar."""
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)
        
        open_folder_action = QAction("Open &Folder...", self)
        open_folder_action.setShortcut("Ctrl+Shift+O")
        open_folder_action.triggered.connect(self._open_folder)
        file_menu.addAction(open_folder_action)
        
        file_menu.addSeparator()
        
        cleanup_explorer_action = QAction("&Cleanup File Explorer", self)
        cleanup_explorer_action.triggered.connect(self._cleanup_file_explorer)
        file_menu.addAction(cleanup_explorer_action)
        
        file_menu.addSeparator()
        
        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut(QKeySequence.Save)
        self.save_action.triggered.connect(self._save_file)
        file_menu.addAction(self.save_action)
        
        self.save_as_action = QAction("Save &As...", self)
        self.save_as_action.setShortcut(QKeySequence.SaveAs)
        self.save_as_action.triggered.connect(self._save_file_as)
        file_menu.addAction(self.save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        edit_menu = menubar.addMenu("&Edit")
        
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.editor.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self.editor.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("Cu&t", self)
        cut_action.setShortcut(QKeySequence.Cut)
        cut_action.triggered.connect(self.editor.cut)
        edit_menu.addAction(cut_action)
        
        copy_action = QAction("&Copy", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.editor.copy)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("&Paste", self)
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(self.editor.paste)
        edit_menu.addAction(paste_action)
        
        edit_menu.addSeparator()
        
        select_all_action = QAction("Select &All", self)
        select_all_action.setShortcut(QKeySequence.SelectAll)
        select_all_action.triggered.connect(self.editor.selectAll)
        edit_menu.addAction(select_all_action)
        
        find_action = QAction("&Find...", self)
        find_action.setShortcut(QKeySequence.Find)
        find_action.triggered.connect(self._show_find_dialog)
        edit_menu.addAction(find_action)
        
        view_menu = menubar.addMenu("&View")
        
        toggle_tree_action = QAction("Toggle File &Tree", self)
        toggle_tree_action.setShortcut("Ctrl+B")
        toggle_tree_action.triggered.connect(self._toggle_file_tree)
        view_menu.addAction(toggle_tree_action)
    
    def _setup_toolbar(self):
        """Set up the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        toolbar.addAction("New", self._new_file)
        toolbar.addAction("Open", self._open_file)
        self.save_toolbar_action = toolbar.addAction("Save", self._save_file)
        self.save_as_toolbar_action = toolbar.addAction("Save As", self._save_file_as)
        toolbar.addSeparator()
        toolbar.addAction("Undo", self.editor.undo)
        toolbar.addAction("Redo", self.editor.redo)
    
    def _setup_statusbar(self):
        """Set up the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")
        
        self.editor.cursorPositionChanged.connect(self._update_cursor_position)
    
    def _setup_shortcuts(self):
        """Set up additional keyboard shortcuts."""
        redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        redo_shortcut.activated.connect(self.editor.redo)
    
    def _apply_dark_theme(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
                selection-background-color: #264f78;
            }
            QTreeView {
                background-color: #252526;
                color: #d4d4d4;
                border: none;
            }
            QTreeView::item:selected {
                background-color: #094771;
            }
            QTreeView::item:hover {
                background-color: #2a2d2e;
            }
            QMenuBar {
                background-color: #3c3c3c;
                color: #d4d4d4;
            }
            QMenuBar::item:selected {
                background-color: #094771;
            }
            QMenu {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #454545;
            }
            QMenu::item:selected {
                background-color: #094771;
            }
            QToolBar {
                background-color: #3c3c3c;
                border: none;
                spacing: 5px;
            }
            QToolButton {
                background-color: transparent;
                color: #d4d4d4;
                border: none;
                padding: 5px;
            }
            QToolButton:hover {
                background-color: #094771;
            }
            QStatusBar {
                background-color: #007acc;
                color: white;
            }
            QSplitter::handle {
                background-color: #3c3c3c;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 14px;
            }
            QScrollBar::handle:vertical {
                background-color: #5a5a5a;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #7a7a7a;
            }
            QScrollBar:horizontal {
                background-color: #1e1e1e;
                height: 14px;
            }
            QScrollBar::handle:horizontal {
                background-color: #5a5a5a;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #7a7a7a;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                background: none;
                border: none;
            }
        """)
    
    def _update_cursor_position(self):
        """Update cursor position in status bar."""
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        lang = self.editor.current_language or "Plain Text"
        self.statusbar.showMessage(f"Line {line}, Column {col}  |  {lang.title()}")
    
    def _update_language_status(self):
        """Update the status bar with current language."""
        self._update_cursor_position()
    
    def _on_file_double_clicked(self, index):
        """Handle double-click on file tree item."""
        if not self.file_tree.is_directory(index):
            file_path = self.file_tree.get_file_path(index)
            self._open_file_path(file_path)
    
    def _cleanup_file_explorer(self):
        """Collapse all file explorer directories except for the current file's path."""
        current_file = self.editor.current_file
        self.file_tree.cleanup_explorer(current_file)
    
    def _new_file(self):
        """Create a new file."""
        if self._check_save():
            self.editor.blockSignals(True)
            self.editor.clear()
            self.editor.set_language(None)
            self.editor.blockSignals(False)
            self.editor.current_file = None
            self.editor.is_modified = False
            self.editor.is_invalid_file = False
            self.setWindowTitle("Text Editor - New File")
            self._update_language_status()
            self.editor.update_line_number_area_width(0)
    
    def _open_file(self):
        """Open a file dialog to select a file."""
        if self._check_save():
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Open File", "",
                "All Files (*);;Text Files (*.txt);;Python Files (*.py)"
            )
            if file_path:
                self._open_file_path(file_path, check_save=False)
    
    def _is_likely_binary(self, file_path):
        """Check if file is likely binary by reading first bytes."""
        try:
            with open(file_path, 'rb') as f:
                initial_bytes = f.read(512)
            
            # Common binary file signatures
            binary_signatures = [
                b'\x7fELF',        # ELF executable
                b'MZ\x90\x00',     # Windows executable
                b'\x89PNG\r\n',    # PNG image
                b'\xff\xd8\xff',   # JPEG image
                b'GIF8',           # GIF image
                b'%PDF',           # PDF
                b'PK\x03\x04',     # ZIP archive
                b'\x1f\x8b\x08',   # GZIP compressed
                b'BM',             # BMP image
                b'II\x2a\x00',     # TIFF image (little-endian)
                b'MM\x00\x2a',     # TIFF image (big-endian)
                b'Rar!',           # RAR archive
                b'7z\xbc\xaf',     # 7-zip archive
                b'\xca\xfe\xba\xbe',  # Java class file
                b'\xfe\xed\xfa',   # Mach-O binary
                b'Kadu\x00',       # KDE Krita file
                b'\x00\x00\x01\x00',  # Windows icon
            ]
            
            for sig in binary_signatures:
                if initial_bytes.startswith(sig):
                    return True
            
            # Check for null bytes (common in binary files)
            if b'\x00' in initial_bytes:
                return True
                
            return False
        except Exception:
            # If we can't determine, assume it's not binary
            return False
    
    def _open_file_path(self, file_path, check_save=True):
        """Open a specific file."""
        if check_save and not self._check_save():
            return
        
        # Check for binary files before attempting to read
        if self._is_likely_binary(file_path):
            self._handle_invalid_file(file_path)
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, UnicodeError):
            # Binary or incompatible file type - show error overlay instead of popup
            self._handle_invalid_file(file_path)
            return
        except (FileNotFoundError, IsADirectoryError, PermissionError) as e:
            # Actual file access errors - show error dialog
            QMessageBox.critical(self, "Error", f"Could not open file:\n{str(e)}")
            return
        except Exception as e:
            # Any other exception during read - treat as invalid file for safety
            self._handle_invalid_file(file_path)
            return
        
        # File was successfully read as text
        try:
            self.editor.blockSignals(True)
            self.editor.setPlainText(content)
            self.editor.set_language_from_file(file_path)
            self.editor.blockSignals(False)
            self.editor.current_file = file_path
            self.editor.is_modified = False
            self.editor.is_invalid_file = False
            self.setWindowTitle(f"Text Editor - {os.path.basename(file_path)}")
            self._update_language_status()
            self.editor.update_line_number_area_width(0)
            self.file_tree.select_file(file_path)
            self._show_error_overlay(False)
        except Exception as e:
            # Any error during editor setup - show error dialog
            QMessageBox.critical(self, "Error", f"Could not open file:\n{str(e)}")
    
    def _handle_invalid_file(self, file_path):
        """Handle opening of incompatible file type."""
        try:
            self.editor.blockSignals(True)
            self.editor.clear()
            self.editor.blockSignals(False)
            self.editor.current_file = file_path
            self.editor.is_modified = False
            self.editor.is_invalid_file = True
            self.setWindowTitle(f"Text Editor - {os.path.basename(file_path)}")
            self._update_language_status()
            self._show_error_overlay(True)
        except Exception as e:
            # Fallback error handling if invalid file display fails
            QMessageBox.critical(self, "Error", f"Could not open file:\n{str(e)}")
    
    def _open_folder(self):
        """Open a folder in the file tree."""
        folder_path = QFileDialog.getExistingDirectory(self, "Open Folder")
        if folder_path:
            self.file_tree.set_root_path(folder_path)
    
    def _save_file(self):
        """Save the current file."""
        if self.editor.is_invalid_file:
            return
        if self.editor.current_file:
            self._save_to_path(self.editor.current_file)
        else:
            self._save_file_as()
    
    def _save_file_as(self):
        """Save file with a new name."""
        if self.editor.is_invalid_file:
            return
        dialog = QFileDialog(self, "Save File")
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilters(["All Files (*)", "Text Files (*.txt)", "Python Files (*.py)"])
        dialog.setOption(QFileDialog.ShowDirsOnly, False)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        
        from PyQt5.QtWidgets import QPushButton
        new_folder_btn = QPushButton("New Folder")
        new_folder_btn.clicked.connect(lambda: self._create_new_folder(dialog))
        dialog.layout().addWidget(new_folder_btn)
        
        if dialog.exec_() == QFileDialog.Accepted:
            file_path = dialog.selectedFiles()[0]
            if file_path:
                self._save_to_path(file_path)
    
    def _create_new_folder(self, dialog):
        """Create a new folder in the current directory of the file dialog."""
        current_dir = dialog.directory().absolutePath()
        folder_name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and folder_name:
            new_folder_path = os.path.join(current_dir, folder_name)
            try:
                os.makedirs(new_folder_path, exist_ok=True)
                dialog.setDirectory(new_folder_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create folder:\n{str(e)}")
    
    def _save_to_path(self, file_path):
        """Save content to a specific path."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            self.editor.current_file = file_path
            self.editor.is_modified = False
            self.setWindowTitle(f"Text Editor - {os.path.basename(file_path)}")
            self.statusbar.showMessage("File saved", 3000)
            self.file_tree.select_file(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file:\n{str(e)}")
    
    def _check_save(self):
        """Check if document needs saving before proceeding."""
        if self.editor.is_modified:
            reply = QMessageBox.question(
                self, "Save Changes?",
                "The document has been modified. Save changes?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self._save_file()
                return not self.editor.is_modified
            elif reply == QMessageBox.Cancel:
                return False
        return True
    
    def _toggle_file_tree(self):
        """Toggle file tree visibility."""
        self.file_tree.setVisible(not self.file_tree.isVisible())
    
    def _show_find_dialog(self):
        """Show find and replace dialog."""
        dialog = FindReplaceDialog(self)
        dialog.exec_()
    
    def _show_error_overlay(self, show_error):
        """Show or hide error overlay for incompatible files."""
        if show_error:
            if not hasattr(self, 'striped_overlay'):
                self.striped_overlay = StripedOverlay()
            
            # Hide editor and show striped overlay
            self.editor.hide()
            # Check if overlay is already in splitter
            if self.splitter.indexOf(self.striped_overlay) < 0:
                self.splitter.addWidget(self.striped_overlay)
            self.striped_overlay.show()
            
            # Disable and grey out save actions
            self.save_action.setEnabled(False)
            self.save_as_action.setEnabled(False)
            self.save_toolbar_action.setEnabled(False)
            self.save_as_toolbar_action.setEnabled(False)
        else:
            # Show editor and hide striped overlay
            if hasattr(self, 'striped_overlay') and self.splitter.indexOf(self.striped_overlay) >= 0:
                self.striped_overlay.hide()
            self.editor.show()
            
            # Enable save actions
            self.save_action.setEnabled(True)
            self.save_as_action.setEnabled(True)
            self.save_toolbar_action.setEnabled(True)
            self.save_as_toolbar_action.setEnabled(True)
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self._check_save():
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Text Editor")
    
    editor = TextEditor()
    editor.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
