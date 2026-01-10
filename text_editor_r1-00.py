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
    QInputDialog, QShortcut, QTextEdit
)
from PyQt5.QtCore import Qt, QDir, QModelIndex, QRect
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QTextFormat, QKeySequence,
    QTextCursor, QTextCharFormat, QBrush, QPen
)


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
        self.is_modified = False
        
        self._setup_editor()
        self._setup_line_numbers()
        self._setup_signals()
    
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
    
    def _setup_signals(self):
        """Set up document modification tracking."""
        self.textChanged.connect(self._on_text_changed)
    
    def _on_text_changed(self):
        """Track document modifications."""
        self.is_modified = True
    
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
        """Handle enter key with auto-indentation."""
        line = cursor.block().text()
        indent = ""
        for char in line:
            if char in (' ', '\t'):
                indent += char
            else:
                break
        
        text_before = line[:cursor.positionInBlock()].rstrip()
        if text_before and text_before[-1] in self.BRACKETS:
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
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.Hidden)
        
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
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal)
        
        self.file_tree = FileTreeView()
        self.file_tree.setMinimumWidth(200)
        self.file_tree.setMaximumWidth(400)
        self.file_tree.doubleClicked.connect(self._on_file_double_clicked)
        
        self.editor = CodeEditor()
        
        splitter.addWidget(self.file_tree)
        splitter.addWidget(self.editor)
        splitter.setSizes([250, 950])
        
        layout.addWidget(splitter)
    
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
        
        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self._save_file_as)
        file_menu.addAction(save_as_action)
        
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
        toolbar.addAction("Save", self._save_file)
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
        pass
    
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
        self.statusbar.showMessage(f"Line {line}, Column {col}")
    
    def _on_file_double_clicked(self, index):
        """Handle double-click on file tree item."""
        if not self.file_tree.is_directory(index):
            file_path = self.file_tree.get_file_path(index)
            self._open_file_path(file_path)
    
    def _new_file(self):
        """Create a new file."""
        if self._check_save():
            self.editor.clear()
            self.editor.current_file = None
            self.editor.is_modified = False
            self.setWindowTitle("Text Editor - New File")
    
    def _open_file(self):
        """Open a file dialog to select a file."""
        if self._check_save():
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Open File", "",
                "All Files (*);;Text Files (*.txt);;Python Files (*.py)"
            )
            if file_path:
                self._open_file_path(file_path)
    
    def _open_file_path(self, file_path):
        """Open a specific file."""
        if self._check_save():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.editor.setPlainText(content)
                self.editor.current_file = file_path
                self.editor.is_modified = False
                self.setWindowTitle(f"Text Editor - {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file:\n{str(e)}")
    
    def _open_folder(self):
        """Open a folder in the file tree."""
        folder_path = QFileDialog.getExistingDirectory(self, "Open Folder")
        if folder_path:
            self.file_tree.set_root_path(folder_path)
    
    def _save_file(self):
        """Save the current file."""
        if self.editor.current_file:
            self._save_to_path(self.editor.current_file)
        else:
            self._save_file_as()
    
    def _save_file_as(self):
        """Save file with a new name."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "",
            "All Files (*);;Text Files (*.txt);;Python Files (*.py)"
        )
        if file_path:
            self._save_to_path(file_path)
    
    def _save_to_path(self, file_path):
        """Save content to a specific path."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            self.editor.current_file = file_path
            self.editor.is_modified = False
            self.setWindowTitle(f"Text Editor - {os.path.basename(file_path)}")
            self.statusbar.showMessage("File saved", 3000)
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
        """Show find dialog."""
        text, ok = QInputDialog.getText(self, "Find", "Search for:")
        if ok and text:
            cursor = self.editor.textCursor()
            document = self.editor.document()
            found = document.find(text, cursor)
            if not found.isNull():
                self.editor.setTextCursor(found)
            else:
                found = document.find(text)
                if not found.isNull():
                    self.editor.setTextCursor(found)
                else:
                    QMessageBox.information(self, "Find", "Text not found")
    
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
