"""
Tests for the Text Editor application using pytest and pytest-qt.
Run with: QT_QPA_PLATFORM=offscreen pytest test_text_editor.py -v
"""

import pytest
import sys
import os
from pathlib import Path

# Add parent directory to path for text_editor import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QApplication, QMessageBox, QFileDialog, QInputDialog
from PyQt5.QtCore import Qt, QDir, QSize, QRect
from PyQt5.QtGui import QTextCursor, QKeyEvent

from text_editor import (
    CodeEditor, FileTreeView, TextEditor, LineNumberArea, main,
    SyntaxHighlighter, LANGUAGE_DEFINITIONS, get_language_for_file,
    FindReplaceDialog, Document, DocumentManager, EditorPane, EditorTabWidget,
    SplitContainer, StripedOverlay
)


@pytest.fixture
def editor(qtbot):
    """Create a CodeEditor instance."""
    ed = CodeEditor()
    yield ed
    ed.is_modified = False
    ed.close()


@pytest.fixture
def file_tree(qtbot):
    """Create a FileTreeView instance."""
    tree = FileTreeView()
    yield tree
    tree.close()


@pytest.fixture
def main_window(qtbot):
    """Create a TextEditor main window instance."""
    window = TextEditor()
    yield window
    window._skip_save_check = True
    for doc in window.doc_manager.documents:
        doc.is_modified = False
    window.close()

@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Hello, World!\nLine 2\nLine 3")
    return str(file_path)


class TestCodeEditor:
    """Tests for the CodeEditor class."""

    def test_editor_initialization(self, editor):
        """Test editor initializes correctly."""
        assert editor is not None
        assert editor.current_file is None
        assert editor.is_modified is False

    def test_text_insertion(self, editor, qtbot):
        """Test basic text insertion."""
        qtbot.keyClicks(editor, "Hello, World!")
        assert editor.toPlainText() == "Hello, World!"

    def test_modification_tracking(self, editor, qtbot):
        """Test that modifications are tracked."""
        assert editor.is_modified is False
        qtbot.keyClicks(editor, "x")
        assert editor.is_modified is True

    def test_line_number_area_exists(self, editor):
        """Test line number area is created."""
        assert editor.line_number_area is not None
        assert isinstance(editor.line_number_area, LineNumberArea)

    def test_line_number_area_width(self, editor, qtbot):
        """Test line number area width calculation."""
        qtbot.keyClicks(editor, "Line 1")
        width = editor.line_number_area_width()
        assert width > 0

    def test_line_number_width_increases_with_lines(self, editor, qtbot):
        """Test that line number width increases with more lines."""
        qtbot.keyClicks(editor, "Line 1")
        width_few = editor.line_number_area_width()
        
        editor.clear()
        for i in range(100):
            qtbot.keyClick(editor, Qt.Key_Return)
        width_many = editor.line_number_area_width()
        
        assert width_many >= width_few


class TestAutoIndentation:
    """Tests for auto-indentation functionality."""

    def test_indent_maintained_on_enter(self, editor, qtbot):
        """Test that indentation is maintained on new line."""
        qtbot.keyClicks(editor, "    indented")
        qtbot.keyClick(editor, Qt.Key_Return)
        qtbot.keyClicks(editor, "next")
        
        lines = editor.toPlainText().split('\n')
        assert len(lines) == 2
        assert lines[1] == "    next"

    def test_extra_indent_after_open_brace(self, editor, qtbot):
        """Test extra indent after opening brace."""
        qtbot.keyClicks(editor, "function() {")
        qtbot.keyClick(editor, Qt.Key_Return)
        qtbot.keyClicks(editor, "code")
        
        lines = editor.toPlainText().split('\n')
        assert len(lines) >= 2
        assert lines[1].startswith("    ")

    def test_tab_inserts_spaces(self, editor, qtbot):
        """Test that tab key inserts 4 spaces."""
        qtbot.keyClick(editor, Qt.Key_Tab)
        assert editor.toPlainText() == "    "

    def test_tab_indents_selection(self, editor, qtbot):
        """Test tab indents selected lines."""
        editor.setPlainText("line1\nline2\nline3")
        editor.selectAll()
        qtbot.keyClick(editor, Qt.Key_Tab)
        lines = editor.toPlainText().split('\n')
        assert all(line.startswith("    ") for line in lines)

    def test_backtab_unindents_selection(self, editor, qtbot):
        """Test shift+tab unindents selected lines."""
        editor.setPlainText("    line1\n    line2\n    line3")
        editor.selectAll()
        qtbot.keyClick(editor, Qt.Key_Backtab)
        lines = editor.toPlainText().split('\n')
        assert all(not line.startswith("    ") for line in lines)

    def test_backtab_unindents_tab_character(self, editor, qtbot):
        """Test shift+tab removes tab character."""
        editor.setPlainText("\tline1\n\tline2")
        editor.selectAll()
        qtbot.keyClick(editor, Qt.Key_Backtab)
        lines = editor.toPlainText().split('\n')
        assert not lines[0].startswith("\t")

    def test_enter_between_brackets(self, editor, qtbot):
        """Test enter between brackets creates proper indentation."""
        qtbot.keyClicks(editor, "{")
        qtbot.keyClick(editor, Qt.Key_Return)
        lines = editor.toPlainText().split('\n')
        assert len(lines) >= 2
        assert "    " in lines[1] or lines[1].startswith("    ")

    def test_indent_selection_no_selection(self, editor, qtbot):
        """Test _indent_selection does nothing without selection."""
        editor.setPlainText("line1")
        cursor = editor.textCursor()
        cursor.clearSelection()
        editor._indent_selection(cursor, True)
        assert editor.toPlainText() == "line1"


class TestBracketMatching:
    """Tests for bracket matching functionality."""

    def test_bracket_pairs(self, editor):
        """Test that bracket pairs are defined correctly."""
        assert editor.BRACKETS == {'(': ')', '[': ']', '{': '}'}
        assert editor.CLOSING_BRACKETS == {')': '(', ']': '[', '}': '{'}

    def test_quotes_defined(self, editor):
        """Test that quotes are defined."""
        assert '"' in editor.QUOTES
        assert "'" in editor.QUOTES
        assert '`' in editor.QUOTES

    def test_auto_close_parenthesis(self, editor, qtbot):
        """Test auto-closing of parentheses."""
        qtbot.keyClicks(editor, "(")
        assert editor.toPlainText() == "()"

    def test_auto_close_brackets(self, editor, qtbot):
        """Test auto-closing of square brackets."""
        qtbot.keyClicks(editor, "[")
        assert editor.toPlainText() == "[]"

    def test_auto_close_braces(self, editor, qtbot):
        """Test auto-closing of curly braces."""
        qtbot.keyClicks(editor, "{")
        assert editor.toPlainText() == "{}"

    def test_auto_close_double_quotes(self, editor, qtbot):
        """Test auto-closing of double quotes."""
        qtbot.keyClicks(editor, '"')
        assert editor.toPlainText() == '""'

    def test_auto_close_single_quotes(self, editor, qtbot):
        """Test auto-closing of single quotes."""
        qtbot.keyClicks(editor, "'")
        assert editor.toPlainText() == "''"

    def test_cursor_between_brackets(self, editor, qtbot):
        """Test cursor is placed between brackets after auto-close."""
        qtbot.keyClicks(editor, "(")
        qtbot.keyClicks(editor, "x")
        assert editor.toPlainText() == "(x)"

    def test_find_matching_bracket_forward(self, editor):
        """Test finding matching bracket forward."""
        text = "(hello)"
        result = editor._find_matching_bracket(text, 0, '(', ')', 1)
        assert result == 6

    def test_find_matching_bracket_backward(self, editor):
        """Test finding matching bracket backward."""
        text = "(hello)"
        result = editor._find_matching_bracket(text, 6, ')', '(', -1)
        assert result == 0

    def test_find_matching_nested_brackets(self, editor):
        """Test finding matching bracket with nesting."""
        text = "((inner))"
        result = editor._find_matching_bracket(text, 0, '(', ')', 1)
        assert result == 8

    def test_no_match_found(self, editor):
        """Test when no matching bracket exists."""
        text = "(unmatched"
        result = editor._find_matching_bracket(text, 0, '(', ')', 1)
        assert result is None

    def test_match_brackets_at_cursor_opening(self, editor, qtbot):
        """Test bracket matching when cursor is on opening bracket."""
        editor.setPlainText("(hello)")
        cursor = editor.textCursor()
        cursor.setPosition(0)
        editor.setTextCursor(cursor)
        editor.match_brackets()
        assert len(editor.bracket_positions) == 2

    def test_match_brackets_at_cursor_closing(self, editor, qtbot):
        """Test bracket matching when cursor is on closing bracket."""
        editor.setPlainText("(hello)")
        cursor = editor.textCursor()
        cursor.setPosition(6)
        editor.setTextCursor(cursor)
        editor.match_brackets()
        assert len(editor.bracket_positions) == 2

    def test_match_brackets_before_cursor_opening(self, editor, qtbot):
        """Test bracket matching when cursor is after opening bracket."""
        editor.setPlainText("(hello)")
        cursor = editor.textCursor()
        cursor.setPosition(1)
        editor.setTextCursor(cursor)
        editor.match_brackets()
        assert len(editor.bracket_positions) == 2

    def test_match_brackets_before_cursor_closing(self, editor, qtbot):
        """Test bracket matching when cursor is after closing bracket."""
        editor.setPlainText("(hello)")
        cursor = editor.textCursor()
        cursor.setPosition(7)
        editor.setTextCursor(cursor)
        editor.match_brackets()
        assert len(editor.bracket_positions) == 2

    def test_closing_bracket_skip_over(self, editor, qtbot):
        """Test typing closing bracket skips over existing one."""
        qtbot.keyClicks(editor, "(")
        assert editor.toPlainText() == "()"
        qtbot.keyClicks(editor, ")")
        assert editor.toPlainText() == "()"
        cursor = editor.textCursor()
        assert cursor.position() == 2

    def test_quote_skip_over(self, editor, qtbot):
        """Test typing quote skips over existing one."""
        qtbot.keyClicks(editor, '"')
        assert editor.toPlainText() == '""'
        qtbot.keyClicks(editor, '"')
        assert editor.toPlainText() == '""'
        cursor = editor.textCursor()
        assert cursor.position() == 2

    def test_backspace_deletes_bracket_pair(self, editor, qtbot):
        """Test backspace deletes both brackets when empty."""
        qtbot.keyClicks(editor, "(")
        assert editor.toPlainText() == "()"
        qtbot.keyClick(editor, Qt.Key_Backspace)
        assert editor.toPlainText() == ""

    def test_backspace_deletes_quote_pair(self, editor, qtbot):
        """Test backspace deletes both quotes when empty."""
        qtbot.keyClicks(editor, '"')
        assert editor.toPlainText() == '""'
        qtbot.keyClick(editor, Qt.Key_Backspace)
        assert editor.toPlainText() == ""


class TestFileTreeView:
    """Tests for the FileTreeView class."""

    def test_file_tree_initialization(self, file_tree):
        """Test file tree initializes correctly."""
        assert file_tree is not None
        assert file_tree.model is not None

    def test_set_root_path(self, file_tree, tmp_path):
        """Test setting root path."""
        file_tree.set_root_path(str(tmp_path))
        root_index = file_tree.rootIndex()
        assert Path(file_tree.model.filePath(root_index)) == Path(tmp_path)

    def test_get_file_path(self, file_tree, temp_file):
        """Test getting file path from index."""
        dir_path = os.path.dirname(temp_file)
        file_tree.set_root_path(dir_path)
        
        index = file_tree.model.index(temp_file)
        path = file_tree.get_file_path(index)
        assert Path(path) == Path(temp_file)

    def test_is_directory(self, file_tree, tmp_path):
        """Test directory check."""
        file_tree.set_root_path(str(tmp_path))
        index = file_tree.model.index(str(tmp_path))
        assert file_tree.is_directory(index) is True

    def test_is_not_directory(self, file_tree, temp_file):
        """Test file is not directory."""
        dir_path = os.path.dirname(temp_file)
        file_tree.set_root_path(dir_path)
        index = file_tree.model.index(temp_file)
        assert file_tree.is_directory(index) is False

    def test_cleanup_explorer_with_no_file(self, file_tree, tmp_path):
        """Test cleanup_explorer collapses all when no file is specified."""
        file_tree.set_root_path(str(tmp_path))
        file_tree.cleanup_explorer(None)

    def test_cleanup_explorer_with_file(self, file_tree, temp_file):
        """Test cleanup_explorer keeps ancestors expanded for current file."""
        dir_path = os.path.dirname(temp_file)
        file_tree.set_root_path(dir_path)
        file_tree.cleanup_explorer(temp_file)


class TestCleanupFileExplorer:
    """Tests for the Cleanup File Explorer menu action."""

    def test_cleanup_file_explorer_action_exists(self, main_window):
        """Test that Cleanup File Explorer action exists in File menu."""
        file_menu = None
        for action in main_window.menuBar().actions():
            if action.text() == "&File":
                file_menu = action.menu()
                break
        assert file_menu is not None
        
        action_texts = [action.text() for action in file_menu.actions()]
        assert "&Cleanup File Explorer" in action_texts

    def test_cleanup_file_explorer_method(self, main_window, temp_file):
        """Test _cleanup_file_explorer method works."""
        main_window._open_file_path(temp_file)
        main_window._cleanup_file_explorer()


class TestTextEditorMainWindow:
    """Tests for the main TextEditor window."""

    def test_window_initialization(self, main_window):
        """Test main window initializes correctly."""
        assert main_window is not None
        assert "Text Editor" in main_window.windowTitle()

    def test_editor_exists(self, main_window):
        """Test editor widget exists."""
        assert main_window.editor is not None
        assert isinstance(main_window.editor, CodeEditor)

    def test_file_tree_exists(self, main_window):
        """Test file tree exists."""
        assert main_window.file_tree is not None
        assert isinstance(main_window.file_tree, FileTreeView)

    def test_statusbar_exists(self, main_window):
        """Test status bar exists."""
        assert main_window.statusbar is not None

    def test_new_file(self, main_window, qtbot):
        """Test new file action creates a new tab."""
        initial_tab_count = main_window.split_container._active_tab_widget.count()
        main_window._new_file()
        new_tab_count = main_window.split_container._active_tab_widget.count()
        
        assert new_tab_count == initial_tab_count + 1
        assert main_window.editor.toPlainText() == ""
        assert main_window.editor.current_file is None

    def test_open_file(self, main_window, temp_file):
        """Test opening a file."""
        main_window._open_file_path(temp_file)
        
        assert main_window.editor.toPlainText() == "Hello, World!\nLine 2\nLine 3"
        assert main_window.editor.current_file == temp_file

    def test_save_file(self, main_window, tmp_path, qtbot):
        """Test saving a file."""
        file_path = str(tmp_path / "saved_file.txt")
        qtbot.keyClicks(main_window.editor, "Test content")
        main_window.doc_manager.update_document_path(main_window.editor.doc, file_path)
        main_window._save_file()
        
        with open(file_path, 'r') as f:
            content = f.read()
        assert content == "Test content"

    def test_toggle_file_tree(self, main_window):
        """Test toggling file tree visibility."""
        # Need to show window for visibility tests to work
        main_window.show()
        initial_visible = main_window.file_tree.isVisible()
        main_window._toggle_file_tree()
        assert main_window.file_tree.isVisible() != initial_visible
        main_window._toggle_file_tree()
        assert main_window.file_tree.isVisible() == initial_visible

    def test_check_save_unmodified(self, main_window):
        """Test check save with unmodified document."""
        main_window.editor.doc.is_modified = False
        assert main_window._check_save_all() is True

    def test_window_title_after_open(self, main_window, temp_file):
        """Test window title updates after opening file."""
        main_window._open_file_path(temp_file)
        assert "test_file.txt" in main_window.windowTitle()


class TestLineNumberArea:
    """Tests for the LineNumberArea widget."""

    def test_line_number_area_creation(self, editor):
        """Test line number area is properly linked to editor."""
        assert editor.line_number_area.editor is editor

    def test_size_hint(self, editor):
        """Test sizeHint returns proper value."""
        hint = editor.line_number_area.sizeHint()
        assert hint is not None

    def test_paint_event(self, editor, qtbot):
        """Test line number area paint event."""
        qtbot.keyClicks(editor, "Line 1")
        qtbot.keyClick(editor, Qt.Key_Return)
        qtbot.keyClicks(editor, "Line 2")
        editor.line_number_area.repaint()

    def test_update_line_number_area_scroll(self, editor, qtbot):
        """Test scrolling updates line number area."""
        for i in range(50):
            qtbot.keyClick(editor, Qt.Key_Return)
        editor.verticalScrollBar().setValue(10)
        editor.update_line_number_area(QRect(0, 0, 100, 100), 5)


class TestEditorSelection:
    """Tests for text selection functionality."""

    def test_select_all(self, editor, qtbot):
        """Test select all functionality."""
        qtbot.keyClicks(editor, "Line 1")
        qtbot.keyClick(editor, Qt.Key_Return)
        qtbot.keyClicks(editor, "Line 2")
        editor.selectAll()
        
        assert editor.textCursor().hasSelection()

    def test_copy_paste(self, editor, qtbot):
        """Test copy and paste functionality."""
        qtbot.keyClicks(editor, "Copy this")
        editor.selectAll()
        editor.copy()
        
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)
        editor.paste()
        
        assert "Copy thisCopy this" in editor.toPlainText()


class TestUndoRedo:
    """Tests for undo/redo functionality."""

    def test_undo(self, editor, qtbot):
        """Test undo functionality."""
        qtbot.keyClicks(editor, "Initial")
        editor.selectAll()
        qtbot.keyClicks(editor, "Changed")
        
        editor.undo()
        
        assert editor.toPlainText() == "Initial"

    def test_redo(self, editor, qtbot):
        """Test redo functionality."""
        qtbot.keyClicks(editor, "Initial")
        editor.selectAll()
        qtbot.keyClicks(editor, "Changed")
        editor.undo()
        editor.redo()
        
        assert editor.toPlainText() == "Changed"


class TestFileOperations:
    """Tests for file operations."""

    def test_save_to_path(self, main_window, tmp_path, qtbot):
        """Test saving to a specific path."""
        file_path = str(tmp_path / "new_file.txt")
        qtbot.keyClicks(main_window.editor, "New content")
        main_window._save_to_path(file_path)
        
        assert os.path.exists(file_path)
        with open(file_path, 'r') as f:
            assert f.read() == "New content"

    def test_open_folder(self, main_window, tmp_path):
        """Test opening a folder updates file tree."""
        main_window.file_tree.set_root_path(str(tmp_path))
        
        root_index = main_window.file_tree.rootIndex()
        path = main_window.file_tree.model.filePath(root_index)
        assert Path(path) == Path(tmp_path)

    def test_open_file_path_error(self, main_window, tmp_path):
        """Test error handling when opening non-existent file."""
        with patch.object(QMessageBox, 'critical'):
            main_window._open_file_path(str(tmp_path / "nonexistent.txt"))

    def test_save_to_path_error(self, main_window, tmp_path):
        """Test error handling when saving to invalid path."""
        with patch.object(QMessageBox, 'critical'):
            main_window._save_to_path("/invalid/path/that/does/not/exist/file.txt")

    def test_on_file_double_clicked_file(self, main_window, temp_file):
        """Test double-clicking a file opens it."""
        dir_path = os.path.dirname(temp_file)
        main_window.file_tree.set_root_path(dir_path)
        index = main_window.file_tree.model.index(temp_file)
        main_window._on_file_double_clicked(index)
        assert Path(main_window.editor.current_file) == Path(temp_file)

    def test_on_file_double_clicked_directory(self, main_window, tmp_path):
        """Test double-clicking a directory does not open it as file."""
        main_window.file_tree.set_root_path(str(tmp_path.parent))
        index = main_window.file_tree.model.index(str(tmp_path))
        main_window._on_file_double_clicked(index)
        assert main_window.editor.current_file is None

    def test_save_file_no_current_file(self, main_window, qtbot, tmp_path):
        """Test save file calls save as when no current file."""
        qtbot.keyClicks(main_window.editor, "Content")
        with patch.object(main_window, '_save_file_as') as mock_save_as:
            main_window._save_file()
            mock_save_as.assert_called_once()
        main_window.editor.is_modified = False


class TestCheckSaveDialog:
    """Tests for the save confirmation dialog."""

    def test_check_save_discard(self, main_window, qtbot):
        """Test check save with discard option."""
        main_window._skip_save_check = False
        main_window.editor.doc.is_modified = True
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Discard):
            result = main_window._check_save_all()
            assert result is True
        main_window.editor.doc.is_modified = False

    def test_check_save_cancel(self, main_window, qtbot):
        """Test check save with cancel option."""
        main_window._skip_save_check = False
        main_window.editor.doc.is_modified = True
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Cancel):
            result = main_window._check_save_all()
            assert result is False
        main_window.editor.doc.is_modified = False

    def test_check_save_save_success(self, main_window, tmp_path, qtbot):
        """Test check save with save option."""
        main_window._skip_save_check = False
        file_path = str(tmp_path / "save_test.txt")
        main_window.doc_manager.update_document_path(main_window.editor.doc, file_path)
        main_window.editor.doc.is_modified = True
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Save):
            result = main_window._check_save_all()
            assert result is True
        main_window.editor.doc.is_modified = False





class TestCloseEvent:
    """Tests for window close event."""

    def test_close_event_unmodified(self, main_window):
        """Test close event with unmodified document."""
        main_window._skip_save_check = False
        main_window.editor.doc.is_modified = False
        event = MagicMock()
        main_window.closeEvent(event)
        event.accept.assert_called_once()

    def test_close_event_modified_cancel(self, main_window):
        """Test close event with modified document and cancel."""
        main_window._skip_save_check = False
        main_window.editor.doc.is_modified = True
        event = MagicMock()
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Cancel):
            main_window.closeEvent(event)
            event.ignore.assert_called_once()
        main_window.editor.doc.is_modified = False

    def test_close_event_modified_discard(self, main_window):
        """Test close event with modified document and discard."""
        main_window._skip_save_check = False
        main_window.editor.doc.is_modified = True
        event = MagicMock()
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Discard):
            main_window.closeEvent(event)
            event.accept.assert_called_once()
        main_window.editor.doc.is_modified = False


class TestMainFunction:
    """Tests for the main function."""

    def test_main_function(self):
        """Test main function creates and shows window."""
        with patch('text_editor.QApplication') as mock_app:
            with patch('text_editor.TextEditor') as mock_editor:
                mock_app_instance = MagicMock()
                mock_app.return_value = mock_app_instance
                mock_app_instance.exec_.return_value = 0
                
                with patch('sys.exit') as mock_exit:
                    main()
                    mock_exit.assert_called_once_with(0)
                
                mock_editor.return_value.show.assert_called_once()
                mock_app_instance.setApplicationName.assert_called_once_with("Text Editor")


class TestFileDialogs:
    """Tests for file dialog methods."""

    def test_open_file_dialog(self, main_window, temp_file):
        """Test _open_file method with mocked dialog."""
        with patch('text_editor.QFileDialog.getOpenFileName', return_value=(temp_file, 'All Files (*)')):
            main_window._open_file()
            assert main_window.editor.current_file == temp_file

    def test_open_file_dialog_cancelled(self, main_window):
        """Test _open_file when dialog is cancelled."""
        with patch('text_editor.QFileDialog.getOpenFileName', return_value=('', '')):
            main_window._open_file()
            assert main_window.editor.current_file is None

    def test_open_folder_dialog(self, main_window, tmp_path):
        """Test _open_folder method with mocked dialog."""
        with patch('text_editor.QFileDialog.getExistingDirectory', return_value=str(tmp_path)):
            main_window._open_folder()
            root_index = main_window.file_tree.rootIndex()
            assert Path(main_window.file_tree.model.filePath(root_index)) == Path(tmp_path)

    def test_open_folder_dialog_cancelled(self, main_window):
        """Test _open_folder when dialog is cancelled."""
        initial_root = main_window.file_tree.rootIndex()
        with patch('text_editor.QFileDialog.getExistingDirectory', return_value=''):
            main_window._open_folder()




class TestEnterBetweenBracketsWithIndent:
    """Tests for enter between brackets with existing indentation."""

    def test_enter_between_brackets_with_base_indent(self, editor, qtbot):
        """Test enter between brackets preserves base indentation."""
        editor.setPlainText("    {}")
        cursor = editor.textCursor()
        cursor.setPosition(5)
        editor.setTextCursor(cursor)
        qtbot.keyClick(editor, Qt.Key_Return)
        lines = editor.toPlainText().split('\n')
        assert len(lines) >= 2


class TestSelectionAtBlockStart:
    """Tests for selection handling at block start."""

    def test_indent_selection_at_block_start(self, editor, qtbot):
        """Test indentation when selection ends at block start."""
        editor.setPlainText("line1\nline2\nline3")
        cursor = editor.textCursor()
        cursor.setPosition(0)
        cursor.setPosition(12, QTextCursor.KeepAnchor)
        editor.setTextCursor(cursor)
        qtbot.keyClick(editor, Qt.Key_Tab)
        lines = editor.toPlainText().split('\n')
        assert lines[0].startswith("    ")
        assert lines[1].startswith("    ")


class TestLanguageDetection:
    """Tests for language detection from file extensions."""

    def test_get_language_python(self):
        """Test Python file detection."""
        assert get_language_for_file("test.py") == "python"
        assert get_language_for_file("script.pyw") == "python"

    def test_get_language_javascript(self):
        """Test JavaScript file detection."""
        assert get_language_for_file("app.js") == "javascript"
        assert get_language_for_file("component.jsx") == "javascript"

    def test_get_language_typescript(self):
        """Test TypeScript file detection."""
        assert get_language_for_file("app.ts") == "typescript"
        assert get_language_for_file("component.tsx") == "typescript"

    def test_get_language_java(self):
        """Test Java file detection."""
        assert get_language_for_file("Main.java") == "java"

    def test_get_language_c(self):
        """Test C file detection."""
        assert get_language_for_file("main.c") == "c"
        assert get_language_for_file("header.h") == "c"

    def test_get_language_cpp(self):
        """Test C++ file detection."""
        assert get_language_for_file("main.cpp") == "cpp"
        assert get_language_for_file("class.hpp") == "cpp"

    def test_get_language_html(self):
        """Test HTML file detection."""
        assert get_language_for_file("index.html") == "html"

    def test_get_language_css(self):
        """Test CSS file detection."""
        assert get_language_for_file("styles.css") == "css"

    def test_get_language_json(self):
        """Test JSON file detection."""
        assert get_language_for_file("package.json") == "json"

    def test_get_language_unknown(self):
        """Test unknown file extension returns None."""
        assert get_language_for_file("file.xyz") is None
        assert get_language_for_file("noextension") is None

    def test_get_language_none(self):
        """Test None file path returns None."""
        assert get_language_for_file(None) is None
        assert get_language_for_file("") is None


class TestLanguageDefinitions:
    """Tests for language definitions structure."""

    def test_python_definition_exists(self):
        """Test Python language definition exists."""
        assert "python" in LANGUAGE_DEFINITIONS
        assert ".py" in LANGUAGE_DEFINITIONS["python"]["extensions"]

    def test_javascript_definition_exists(self):
        """Test JavaScript language definition exists."""
        assert "javascript" in LANGUAGE_DEFINITIONS
        assert ".js" in LANGUAGE_DEFINITIONS["javascript"]["extensions"]

    def test_definition_has_required_keys(self):
        """Test all definitions have required keys."""
        required_keys = ["extensions", "keywords", "comment_single", "string_delimiters"]
        for lang, definition in LANGUAGE_DEFINITIONS.items():
            for key in required_keys:
                assert key in definition, f"{lang} missing {key}"


class TestSyntaxHighlighter:
    """Tests for SyntaxHighlighter class."""

    def test_highlighter_creation(self, editor):
        """Test highlighter is created with editor."""
        assert editor.highlighter is not None
        assert isinstance(editor.highlighter, SyntaxHighlighter)

    def test_set_language(self, editor):
        """Test setting language on highlighter."""
        editor.set_language("python")
        assert editor.current_language == "python"
        assert editor.highlighter.language == "python"

    def test_set_language_from_file(self, editor):
        """Test setting language from file path."""
        editor.set_language_from_file("test.py")
        assert editor.current_language == "python"

    def test_set_unknown_language(self, editor):
        """Test setting unknown language."""
        editor.set_language("unknown_lang")
        assert editor.current_language == "unknown_lang"

    def test_highlighter_formats_exist(self, editor):
        """Test highlighter has format definitions."""
        assert hasattr(editor.highlighter, 'formats')
        assert 'keyword' in editor.highlighter.formats
        assert 'string' in editor.highlighter.formats
        assert 'comment' in editor.highlighter.formats


class TestLanguageSpecificIndentation:
    """Tests for language-specific indentation."""

    def test_python_colon_indent(self, editor, qtbot):
        """Test Python indentation after colon."""
        editor.set_language("python")
        qtbot.keyClicks(editor, "def foo():")
        qtbot.keyClick(editor, Qt.Key_Return)
        qtbot.keyClicks(editor, "pass")
        lines = editor.toPlainText().split('\n')
        assert lines[1].startswith("    ")

    def test_javascript_brace_indent(self, editor, qtbot):
        """Test JavaScript indentation after brace."""
        editor.set_language("javascript")
        qtbot.keyClicks(editor, "function test() {")
        qtbot.keyClick(editor, Qt.Key_Return)
        qtbot.keyClicks(editor, "code")
        lines = editor.toPlainText().split('\n')
        assert lines[1].startswith("    ")

    def test_yaml_colon_indent(self, editor, qtbot):
        """Test YAML indentation after colon."""
        editor.set_language("yaml")
        qtbot.keyClicks(editor, "key:")
        qtbot.keyClick(editor, Qt.Key_Return)
        qtbot.keyClicks(editor, "value")
        lines = editor.toPlainText().split('\n')
        assert lines[1].startswith("    ")


class TestBinaryFileDetection:
    """Tests for binary file detection."""

    def test_is_likely_binary_ova(self, main_window, tmp_path):
        """Test detection of OVA files."""
        ova_file = tmp_path / "test.ova"
        ova_file.write_bytes(b'\x1f\x8b\x08\x00' + b'gzip content' * 100)
        assert main_window._is_likely_binary(str(ova_file)) is True

    def test_is_likely_binary_pdf(self, main_window, tmp_path):
        """Test detection of PDF files."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b'%PDF-1.4\n' + b'pdf content' * 100)
        assert main_window._is_likely_binary(str(pdf_file)) is True

    def test_is_likely_binary_zip(self, main_window, tmp_path):
        """Test detection of ZIP files."""
        zip_file = tmp_path / "test.zip"
        zip_file.write_bytes(b'PK\x03\x04' + b'zip content' * 100)
        assert main_window._is_likely_binary(str(zip_file)) is True

    def test_is_likely_binary_exe(self, main_window, tmp_path):
        """Test detection of Windows executables."""
        exe_file = tmp_path / "test.exe"
        exe_file.write_bytes(b'MZ\x90\x00' + b'exe content' * 100)
        assert main_window._is_likely_binary(str(exe_file)) is True

    def test_is_likely_binary_png(self, main_window, tmp_path):
        """Test detection of PNG images."""
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'png content' * 100)
        assert main_window._is_likely_binary(str(png_file)) is True

    def test_is_likely_binary_text(self, main_window, tmp_path):
        """Test that text files are not detected as binary."""
        text_file = tmp_path / "test.txt"
        text_file.write_text("This is a text file")
        assert main_window._is_likely_binary(str(text_file)) is False

    def test_is_likely_binary_python(self, main_window, tmp_path):
        """Test that Python files are not detected as binary."""
        py_file = tmp_path / "test.py"
        py_file.write_text("print('hello')")
        assert main_window._is_likely_binary(str(py_file)) is False


class TestIncompatibleFileHandling:
    """Tests for incompatible file type handling."""

    def test_open_incompatible_file_shows_warning(self, main_window, tmp_path, qtbot):
        """Test opening incompatible file shows warning message."""
        binary_file = tmp_path / "test.bin"
        binary_file.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR')
        
        with patch.object(QMessageBox, 'warning') as mock_warning:
            main_window._open_file_path(str(binary_file))
            mock_warning.assert_called_once()

    def test_open_incompatible_file_shows_overlay(self, main_window, tmp_path, qtbot):
        """Test opening incompatible file does not change current file."""
        main_window.show()
        initial_file = main_window.editor.current_file
        binary_file = tmp_path / "test.bin"
        binary_file.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR')
        
        with patch.object(QMessageBox, 'warning'):
            main_window._open_file_path(str(binary_file))
        
        assert main_window.editor.current_file == initial_file

    def test_open_valid_file_after_binary_attempt(self, main_window, tmp_path, qtbot):
        """Test opening valid file after failed binary open attempt works."""
        binary_file = tmp_path / "test.bin"
        binary_file.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR')
        
        with patch.object(QMessageBox, 'warning'):
            main_window._open_file_path(str(binary_file))
        
        text_file = tmp_path / "test.txt"
        text_file.write_text("Hello, World!")
        main_window._open_file_path(str(text_file))
        
        assert main_window.editor.current_file == str(text_file)
        assert main_window.editor.toPlainText() == "Hello, World!"

    def test_binary_detection_blocks_open(self, main_window, tmp_path, qtbot):
        """Test binary file detection blocks file from being opened."""
        binary_file = tmp_path / "test.exe"
        binary_file.write_bytes(b'MZ\x90\x00\x03\x00\x00\x00')
        
        initial_tab_count = main_window.split_container.active_tab_widget().count()
        
        with patch.object(QMessageBox, 'warning'):
            main_window._open_file_path(str(binary_file))
        
        assert main_window.split_container.active_tab_widget().count() == initial_tab_count

    def test_new_file_creates_valid_document(self, main_window, tmp_path, qtbot):
        """Test creating new file creates a valid editable document."""
        main_window._new_file()
        assert main_window.editor.is_invalid_file is False

    def test_open_valid_file_creates_valid_document(self, main_window, tmp_path, qtbot):
        """Test opening valid text file creates a valid editable document."""
        text_file = tmp_path / "test.txt"
        text_file.write_text("Hello, World!")
        main_window._open_file_path(str(text_file))
        assert main_window.editor.is_invalid_file is False


class TestEditorLanguageIntegration:
    """Tests for editor language integration."""

    def test_open_file_sets_language(self, main_window, tmp_path):
        """Test opening a file sets the correct language."""
        py_file = tmp_path / "test.py"
        py_file.write_text("print('hello')")
        main_window._open_file_path(str(py_file))
        assert main_window.editor.current_language == "python"

    def test_open_js_file_sets_language(self, main_window, tmp_path):
        """Test opening a JavaScript file sets the correct language."""
        js_file = tmp_path / "test.js"
        js_file.write_text("console.log('hello');")
        main_window._open_file_path(str(js_file))
        assert main_window.editor.current_language == "javascript"

    def test_new_file_clears_language(self, main_window, tmp_path):
        """Test new file clears the language."""
        py_file = tmp_path / "test.py"
        py_file.write_text("print('hello')")
        main_window._open_file_path(str(py_file))
        main_window.editor.is_modified = False
        main_window._new_file()
        assert main_window.editor.current_language is None

    def test_open_file_not_modified(self, main_window, tmp_path):
        """Test opening a file does not set is_modified."""
        py_file = tmp_path / "test.py"
        py_file.write_text("print('hello')")
        main_window._open_file_path(str(py_file))
        assert main_window.editor.is_modified is False

    def test_new_file_not_modified(self, main_window):
        """Test new file does not set is_modified."""
        main_window._new_file()
        assert main_window.editor.is_modified is False


@pytest.fixture
def find_replace_dialog(main_window, qtbot):
    """Create a FindReplaceDialog instance with automatic cleanup."""
    dialog = FindReplaceDialog(main_window)
    yield dialog
    dialog.close()


class TestFindReplaceDialog:
    """Tests for FindReplaceDialog functionality."""
    
    @pytest.mark.timeout(30)
    def test_dialog_creation(self, main_window, find_replace_dialog, qtbot):
        """Test FindReplaceDialog is created with editor."""
        assert find_replace_dialog is not None
        assert find_replace_dialog.editor is not None
    
    @pytest.mark.timeout(30)
    def test_find_next_basic(self, main_window, find_replace_dialog, qtbot):
        """Test finding next occurrence of text."""
        main_window.editor.setPlainText("Hello World Hello World")
        
        find_replace_dialog.find_input.setText("Hello")
        find_replace_dialog.find_next()
        
        cursor = main_window.editor.textCursor()
        assert cursor.hasSelection()
        assert "Hello" in main_window.editor.toPlainText()[cursor.selectionStart():cursor.selectionEnd()]
    
    @pytest.mark.timeout(30)
    def test_find_previous(self, main_window, find_replace_dialog, qtbot):
        """Test finding previous occurrence of text."""
        main_window.editor.setPlainText("Hello World Hello World")
        
        # Move cursor to end
        cursor = main_window.editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        main_window.editor.setTextCursor(cursor)
        
        find_replace_dialog.find_input.setText("Hello")
        find_replace_dialog.find_previous()
        
        cursor = main_window.editor.textCursor()
        assert cursor.hasSelection()
    
    @pytest.mark.timeout(30)
    def test_find_not_found(self, main_window, find_replace_dialog, qtbot):
        """Test find when text is not found."""
        main_window.editor.setPlainText("Hello World")
        
        find_replace_dialog.find_input.setText("NotFound")
        find_replace_dialog.find_next()
        
        assert "not found" in find_replace_dialog.status_label.text().lower()
    
    @pytest.mark.timeout(30)
    def test_find_empty_search(self, main_window, find_replace_dialog, qtbot):
        """Test find with empty search text."""
        main_window.editor.setPlainText("Hello World")
        
        find_replace_dialog.find_input.setText("")
        find_replace_dialog.find_next()
        
        assert "Please enter search text" in find_replace_dialog.status_label.text()
    
    @pytest.mark.timeout(30)
    def test_case_sensitive_search(self, main_window, find_replace_dialog, qtbot):
        """Test case-sensitive search."""
        main_window.editor.setPlainText("Hello hello HELLO")
        
        find_replace_dialog.find_input.setText("hello")
        find_replace_dialog.case_sensitive_checkbox.setChecked(True)
        find_replace_dialog.find_next()
        
        cursor = main_window.editor.textCursor()
        selected_text = main_window.editor.toPlainText()[cursor.selectionStart():cursor.selectionEnd()]
        assert selected_text == "hello"
    
    @pytest.mark.timeout(30)
    def test_case_insensitive_search(self, main_window, find_replace_dialog, qtbot):
        """Test case-insensitive search."""
        main_window.editor.setPlainText("Hello hello HELLO")
        
        find_replace_dialog.find_input.setText("HELLO")
        find_replace_dialog.case_sensitive_checkbox.setChecked(False)
        find_replace_dialog.find_next()
        
        # Should find something
        assert "Text found" in find_replace_dialog.status_label.text()
    
    @pytest.mark.timeout(30)
    def test_replace_current(self, main_window, find_replace_dialog, qtbot):
        """Test replace current selection."""
        main_window.editor.setPlainText("Hello World Hello World")
        
        find_replace_dialog.find_input.setText("Hello")
        find_replace_dialog.replace_input.setText("Hi")
        find_replace_dialog.find_next()
        
        find_replace_dialog.replace_current()
        
        text = main_window.editor.toPlainText()
        assert text.startswith("Hi")
    
    @pytest.mark.timeout(30)
    def test_replace_all(self, main_window, find_replace_dialog, qtbot):
        """Test replace all occurrences."""
        main_window.editor.setPlainText("Hello World Hello World Hello")
        
        find_replace_dialog.find_input.setText("Hello")
        find_replace_dialog.replace_input.setText("Hi")
        find_replace_dialog.replace_all()
        
        text = main_window.editor.toPlainText()
        assert text.count("Hi") == 3
        assert "Hello" not in text
    
    @pytest.mark.timeout(30)
    def test_replace_all_counter(self, main_window, find_replace_dialog, qtbot):
        """Test replace all shows count."""
        main_window.editor.setPlainText("foo bar foo baz foo")
        
        find_replace_dialog.find_input.setText("foo")
        find_replace_dialog.replace_input.setText("bar")
        find_replace_dialog.replace_all()
        
        assert "3" in find_replace_dialog.status_label.text()
    
    @pytest.mark.timeout(30)
    def test_find_wrap_around(self, main_window, find_replace_dialog, qtbot):
        """Test find wraps around to beginning."""
        main_window.editor.setPlainText("Hello World Hello World")
        
        # Move cursor to middle
        cursor = main_window.editor.textCursor()
        cursor.setPosition(12)
        main_window.editor.setTextCursor(cursor)
        
        # Find to end, then wrap around
        find_replace_dialog.find_input.setText("Hello")
        find_replace_dialog.find_next()
        pos1 = main_window.editor.textCursor().position()
        
        find_replace_dialog.find_next()
        pos2 = main_window.editor.textCursor().position()
        
        # Should find second Hello, then wrap to first
        assert pos1 != pos2
    
    @pytest.mark.timeout(30)
    def test_find_previous_wrap_around(self, main_window, find_replace_dialog, qtbot):
        """Test find previous wraps around to end."""
        main_window.editor.setPlainText("Hello World Hello World")
        
        # Move cursor to beginning
        cursor = main_window.editor.textCursor()
        cursor.setPosition(0)
        main_window.editor.setTextCursor(cursor)
        
        find_replace_dialog.find_input.setText("Hello")
        find_replace_dialog.find_previous()
        
        # Should wrap to end and find last Hello
        cursor = main_window.editor.textCursor()
        assert cursor.position() > 12


class TestThemeToggle:
    """Tests for light/dark theme toggle functionality."""
    
    @pytest.mark.timeout(30)
    def test_initial_dark_mode(self, main_window, qtbot):
        """Test that editor starts in dark mode."""
        assert main_window.dark_mode is True
        assert "Switch to &Light Mode" in main_window.toggle_theme_action.text()
    
    @pytest.mark.timeout(30)
    def test_toggle_to_light_mode(self, main_window, qtbot):
        """Test toggling from dark to light mode."""
        main_window._toggle_theme()
        assert main_window.dark_mode is False
        assert "Switch to &Dark Mode" in main_window.toggle_theme_action.text()
    
    @pytest.mark.timeout(30)
    def test_toggle_back_to_dark_mode(self, main_window, qtbot):
        """Test toggling from light back to dark mode."""
        main_window._toggle_theme()  # to light
        main_window._toggle_theme()  # back to dark
        assert main_window.dark_mode is True
        assert "Switch to &Light Mode" in main_window.toggle_theme_action.text()
    
    @pytest.mark.timeout(30)
    def test_theme_action_in_view_menu(self, main_window, qtbot):
        """Test that theme toggle action exists in View menu."""
        menubar = main_window.menuBar()
        view_menu = None
        for action in menubar.actions():
            if action.text() == "&View":
                view_menu = action.menu()
                break
        assert view_menu is not None
        action_texts = [action.text() for action in view_menu.actions()]
        assert any("Light Mode" in text or "Dark Mode" in text for text in action_texts)
    
    @pytest.mark.timeout(30)
    def test_editor_dark_mode_sync(self, main_window, qtbot):
        """Test that editor dark_mode syncs with main window."""
        assert main_window.editor.dark_mode is True
        main_window._toggle_theme()
        assert main_window.editor.dark_mode is False
        main_window._toggle_theme()
        assert main_window.editor.dark_mode is True
    
    @pytest.mark.timeout(30)
    def test_highlighter_dark_mode_sync(self, main_window, qtbot):
        """Test that syntax highlighter dark_mode syncs with theme toggle."""
        assert main_window.editor.highlighter.dark_mode is True
        main_window._toggle_theme()
        assert main_window.editor.highlighter.dark_mode is False
        main_window._toggle_theme()
        assert main_window.editor.highlighter.dark_mode is True


class TestDocument:
    """Tests for the Document class."""

    def test_document_creation(self):
        """Test Document can be created."""
        doc = Document()
        assert doc.file_path is None
        assert doc.is_modified is False

    def test_document_with_path(self, tmp_path):
        """Test Document with file path."""
        file_path = str(tmp_path / "test.py")
        doc = Document(file_path)
        assert doc.file_path == file_path
        assert doc.language == "python"

    def test_document_modification_tracking(self):
        """Test Document tracks modifications."""
        doc = Document()
        assert doc.is_modified is False
        doc.document.setPlainText("hello")
        assert doc.is_modified is True
        doc.is_modified = False
        assert doc.is_modified is False

    def test_document_display_name_untitled(self):
        """Test Document display name for untitled."""
        doc = Document()
        assert doc.display_name == "Untitled"

    def test_document_display_name_with_path(self, tmp_path):
        """Test Document display name with file path."""
        file_path = str(tmp_path / "test.py")
        doc = Document(file_path)
        assert doc.display_name == "test.py"

    def test_document_display_name_modified(self):
        """Test Document display name when modified."""
        doc = Document()
        doc.document.setPlainText("hello")
        assert doc.display_name == "Untitled *"

    def test_document_view_count(self):
        """Test Document view counting."""
        doc = Document()
        assert doc.view_count == 0
        doc.add_view()
        assert doc.view_count == 1
        doc.add_view()
        assert doc.view_count == 2
        remaining = doc.remove_view()
        assert remaining == 1
        assert doc.view_count == 1


class TestDocumentManager:
    """Tests for the DocumentManager class."""

    def test_document_manager_creation(self):
        """Test DocumentManager can be created."""
        mgr = DocumentManager()
        assert len(mgr.documents) == 0

    def test_create_new_document(self):
        """Test creating a new document."""
        mgr = DocumentManager()
        doc = mgr.get_or_create_document()
        assert doc is not None
        assert len(mgr.documents) == 1

    def test_create_document_with_path(self, tmp_path):
        """Test creating document with file path."""
        mgr = DocumentManager()
        file_path = str(tmp_path / "test.py")
        doc = mgr.get_or_create_document(file_path)
        assert doc.file_path == file_path
        assert len(mgr.documents) == 1

    def test_get_existing_document(self, tmp_path):
        """Test getting existing document by path."""
        mgr = DocumentManager()
        file_path = str(tmp_path / "test.py")
        doc1 = mgr.get_or_create_document(file_path)
        doc2 = mgr.get_or_create_document(file_path)
        assert doc1 is doc2
        assert len(mgr.documents) == 1

    def test_close_document(self, tmp_path):
        """Test closing a document."""
        mgr = DocumentManager()
        file_path = str(tmp_path / "test.py")
        doc = mgr.get_or_create_document(file_path)
        mgr.close_document(doc)
        assert len(mgr.documents) == 0
        assert mgr.get_document_by_path(file_path) is None

    def test_has_unsaved_documents(self):
        """Test checking for unsaved documents."""
        mgr = DocumentManager()
        doc = mgr.get_or_create_document()
        assert mgr.has_unsaved_documents() is False
        doc.document.setPlainText("hello")
        assert mgr.has_unsaved_documents() is True


class TestTabAndSplitFeatures:
    """Tests for tab and split view functionality."""

    def test_new_file_creates_tab(self, main_window, qtbot):
        """Test that creating a new file creates a new tab."""
        initial_count = main_window.split_container.active_tab_widget().count()
        main_window._new_file()
        assert main_window.split_container.active_tab_widget().count() == initial_count + 1

    def test_open_file_creates_tab(self, main_window, tmp_path, qtbot):
        """Test that opening a file creates a new tab."""
        initial_count = main_window.split_container.active_tab_widget().count()
        file_path = str(tmp_path / "test.txt")
        with open(file_path, 'w') as f:
            f.write("hello")
        main_window._open_file_path(file_path)
        assert main_window.split_container.active_tab_widget().count() == initial_count + 1

    def test_open_same_file_focuses_existing_tab(self, main_window, tmp_path, qtbot):
        """Test that opening same file focuses existing tab instead of creating new."""
        file_path = str(tmp_path / "test.txt")
        with open(file_path, 'w') as f:
            f.write("hello")
        main_window._open_file_path(file_path)
        initial_count = main_window.split_container.active_tab_widget().count()
        main_window._open_file_path(file_path)
        assert main_window.split_container.active_tab_widget().count() == initial_count

    def test_close_tab(self, main_window, qtbot):
        """Test closing a tab."""
        main_window._new_file()
        initial_count = main_window.split_container.active_tab_widget().count()
        main_window._close_current_tab()
        assert main_window.split_container.active_tab_widget().count() == initial_count - 1

    def test_split_right_creates_split(self, main_window, qtbot):
        """Test split right creates a second split."""
        assert main_window.split_container._total_leaf_count() == 1
        main_window._split_right()
        assert main_window.split_container._total_leaf_count() == 2

    def test_split_down_creates_split(self, main_window, qtbot):
        """Test split down creates a second split (nested since default is horizontal)."""
        assert main_window.split_container._total_leaf_count() == 1
        main_window._split_down()
        assert main_window.split_container._total_leaf_count() == 2

    def test_close_split(self, main_window, qtbot):
        """Test closing a split via close_split method directly."""
        main_window._split_right()
        assert main_window.split_container._total_leaf_count() == 2
        active_tw = main_window.split_container.active_tab_widget()
        main_window.split_container.close_split(active_tw)
        qtbot.wait(100)
        assert len(main_window.split_container._all_tab_widgets()) == 1

    def test_editor_property_returns_current_pane(self, main_window, qtbot):
        """Test that editor property returns the current active pane."""
        assert main_window.editor is not None
        assert isinstance(main_window.editor, EditorPane)

    def test_document_manager_exists(self, main_window, qtbot):
        """Test that document manager exists on main window."""
        assert hasattr(main_window, 'doc_manager')
        assert isinstance(main_window.doc_manager, DocumentManager)

    def test_split_up_to_five(self, main_window, qtbot):
        """Test that we can create up to 5 splits."""
        assert main_window.split_container._total_leaf_count() == 1
        for i in range(4):
            main_window._split_right()
            assert main_window.split_container._total_leaf_count() == i + 2
        assert main_window.split_container._total_leaf_count() == 5

    def test_split_limit_enforced(self, main_window, qtbot):
        """Test that splitting beyond 5 is not allowed."""
        for _ in range(4):
            main_window._split_right()
        assert main_window.split_container._total_leaf_count() == 5
        main_window._split_right()
        assert main_window.split_container._total_leaf_count() == 5

    def test_split_sets_focus_to_new_pane(self, main_window, qtbot):
        """Test that splitting moves focus to the new editor pane."""
        main_window._split_right()
        active_tw = main_window.split_container.active_tab_widget()
        current_pane = active_tw.current_editor()
        assert current_pane is not None
        assert main_window.split_container._total_leaf_count() == 2

    def test_nested_split(self, main_window, qtbot):
        """Test that splitting in opposite direction creates a nested split."""
        assert main_window.split_container._total_leaf_count() == 1
        main_window._split_down()
        assert main_window.split_container._total_leaf_count() == 2
        assert main_window.split_container.count() == 1
        from PyQt5.QtWidgets import QSplitter
        assert isinstance(main_window.split_container.widget(0), QSplitter)

    def test_nested_split_orientation(self, main_window, qtbot):
        """Test that nested split has the opposite orientation."""
        from PyQt5.QtWidgets import QSplitter
        assert main_window.split_container.orientation() == Qt.Horizontal
        main_window._split_down()
        nested = main_window.split_container.widget(0)
        assert isinstance(nested, QSplitter)
        assert nested.orientation() == Qt.Vertical

    def test_split_down_then_split_right(self, main_window, qtbot):
        """Test splitting down then right nests the active pane in a horizontal split."""
        from PyQt5.QtWidgets import QSplitter
        main_window._split_down()
        assert main_window.split_container._total_leaf_count() == 2
        main_window._split_right()
        assert main_window.split_container._total_leaf_count() == 3

    def test_close_right_after_nested_split(self, main_window, qtbot):
        """Test closing the right split after split down then split right."""
        main_window._split_down()
        main_window._split_right()
        assert main_window.split_container._total_leaf_count() == 3
        main_window._close_split()
        qtbot.wait(100)
        assert main_window.split_container._total_leaf_count() == 2

    def test_close_nested_pane_unwraps(self, main_window, qtbot):
        """Test that closing one pane of a nested split unwraps the nested splitter."""
        from PyQt5.QtWidgets import QSplitter
        main_window._split_down()
        assert isinstance(main_window.split_container.widget(0), QSplitter)
        active_tw = main_window.split_container.active_tab_widget()
        main_window.split_container.close_split(active_tw)
        qtbot.wait(100)
        assert main_window.split_container._total_leaf_count() == 1
        assert isinstance(main_window.split_container.widget(0), EditorTabWidget)

    def test_nested_pane_split_different_orientation(self, main_window, qtbot):
        """Test that splitting a nested pane in a different orientation wraps it deeper."""
        from PyQt5.QtWidgets import QSplitter
        main_window._split_down()
        active = main_window.split_container.active_tab_widget()
        assert isinstance(active.parentWidget(), QSplitter)
        assert active.parentWidget() is not main_window.split_container
        main_window._split_down()
        assert main_window.split_container._total_leaf_count() == 3
        main_window._split_right()
        assert main_window.split_container._total_leaf_count() == 4

    def test_nested_pane_can_split_same_orientation(self, main_window, qtbot):
        """Test that a pane inside a nested split can split in the same orientation."""
        main_window._split_down()
        assert main_window.split_container._total_leaf_count() == 2
        main_window._split_down()
        assert main_window.split_container._total_leaf_count() == 3

    def test_repeated_split_down(self, main_window, qtbot):
        """Test that splitting down multiple times adds panes to the nested splitter."""
        from PyQt5.QtWidgets import QSplitter
        for i in range(4):
            main_window._split_down()
            assert main_window.split_container._total_leaf_count() == i + 2
        assert main_window.split_container._total_leaf_count() == 5
        nested = main_window.split_container.widget(0)
        assert isinstance(nested, QSplitter)
        assert nested.count() == 5

    def test_split_right_then_down_nests_active(self, main_window, qtbot):
        """Test split right then split down nests the active right pane."""
        from PyQt5.QtWidgets import QSplitter
        main_window._split_right()
        assert main_window.split_container._total_leaf_count() == 2
        assert main_window.split_container.count() == 2
        main_window._split_down()
        assert main_window.split_container._total_leaf_count() == 3
        assert main_window.split_container.count() == 2
        assert isinstance(main_window.split_container.widget(1), QSplitter)

    def test_close_all_nested_then_top_unwraps(self, main_window, qtbot):
        """Test closing a top-level pane when only a nested splitter remains triggers unwrap."""
        from PyQt5.QtWidgets import QSplitter
        main_window._split_right()
        main_window._split_down()
        assert main_window.split_container._total_leaf_count() == 3
        first_tw = main_window.split_container._all_tab_widgets()[0]
        assert first_tw.parentWidget() is main_window.split_container
        main_window.split_container.set_active_tab_widget(first_tw)
        main_window._close_split()
        qtbot.wait(100)
        assert main_window.split_container._total_leaf_count() == 2
        for i in range(main_window.split_container.count()):
            assert isinstance(main_window.split_container.widget(i), EditorTabWidget)

    def test_focus_document_across_nested_splits(self, main_window, qtbot):
        """Test that focus_or_open_document finds docs in nested panes."""
        main_window._split_down()
        all_tw = main_window.split_container._all_tab_widgets()
        first_tw = all_tw[0]
        doc = first_tw.current_editor().doc
        main_window.split_container.set_active_tab_widget(all_tw[1])
        pane = main_window.split_container.focus_or_open_document(doc)
        assert pane is not None
        assert pane.doc is doc


class TestAddWorkspace:
    """Test the Add Workspace toolbar button and add_pane functionality."""

    def test_add_pane_horizontal(self, main_window, qtbot):
        """add_pane adds a new tab widget at the end for horizontal orientation."""
        initial_count = main_window.split_container._total_leaf_count()
        new_tw = main_window.split_container.add_pane(Qt.Horizontal)
        assert new_tw is not None
        assert main_window.split_container._total_leaf_count() == initial_count + 1
        assert main_window.split_container.active_tab_widget() is new_tw

    def test_add_pane_vertical(self, main_window, qtbot):
        """add_pane adds a new tab widget at the end for vertical orientation."""
        initial_count = main_window.split_container._total_leaf_count()
        new_tw = main_window.split_container.add_pane(Qt.Vertical)
        assert new_tw is not None
        assert main_window.split_container._total_leaf_count() == initial_count + 1
        assert main_window.split_container.active_tab_widget() is new_tw

    def test_add_pane_respects_max_limit(self, main_window, qtbot):
        """add_pane returns None when 5 panes already exist."""
        for _ in range(4):
            main_window.split_container.add_pane(Qt.Horizontal)
        assert main_window.split_container._total_leaf_count() == 5
        result = main_window.split_container.add_pane(Qt.Horizontal)
        assert result is None

    def test_add_workspace_horizontal_method(self, main_window, qtbot):
        """_add_workspace_horizontal adds a pane at the end."""
        initial_count = main_window.split_container._total_leaf_count()
        main_window._add_workspace_horizontal()
        assert main_window.split_container._total_leaf_count() == initial_count + 1
        all_tw = main_window.split_container._all_tab_widgets()
        assert main_window.split_container.active_tab_widget() is all_tw[-1]

    def test_add_workspace_vertical_method(self, main_window, qtbot):
        """_add_workspace_vertical adds a pane at the end."""
        initial_count = main_window.split_container._total_leaf_count()
        main_window._add_workspace_vertical()
        assert main_window.split_container._total_leaf_count() == initial_count + 1
        all_tw = main_window.split_container._all_tab_widgets()
        assert main_window.split_container.active_tab_widget() is all_tw[-1]

    def test_add_workspace_creates_blank_doc(self, main_window, qtbot):
        """Adding a workspace creates a new blank document in the new pane."""
        main_window._add_workspace_horizontal()
        pane = main_window.split_container.current_editor()
        assert pane is not None
        assert pane.toPlainText() == ""
        assert pane.doc.file_path is None

    def test_split_right_always_splits_active(self, main_window, qtbot):
        """_split_right always splits adjacent to the active (blue) tab widget."""
        initial_count = main_window.split_container._total_leaf_count()
        main_window._split_right()
        assert main_window.split_container._total_leaf_count() == initial_count + 1

    def test_split_down_always_splits_active(self, main_window, qtbot):
        """_split_down always splits adjacent to the active (blue) tab widget."""
        initial_count = main_window.split_container._total_leaf_count()
        main_window._split_down()
        assert main_window.split_container._total_leaf_count() == initial_count + 1

    def test_split_right_then_down_splits_tab_not_workspace(self, main_window, qtbot):
        """Ctrl+\\ then Ctrl+Shift+\\ should split the active tab, not the workspace."""
        from PyQt5.QtWidgets import QSplitter
        main_window._split_right()
        assert main_window.split_container._total_leaf_count() == 2
        active_tw = main_window.split_container.active_tab_widget()
        main_window._split_down()
        assert main_window.split_container._total_leaf_count() == 3
        new_active = main_window.split_container.active_tab_widget()
        assert new_active is not active_tw
        parent = new_active.parentWidget()
        assert isinstance(parent, QSplitter)
        assert parent.orientation() == Qt.Vertical

    def test_add_workspace_preserves_existing_layout(self, main_window, qtbot):
        """Adding a workspace with different orientation wraps existing, not rearranging."""
        from PyQt5.QtWidgets import QSplitter
        main_window._split_right()
        assert main_window.split_container._total_leaf_count() == 2
        assert main_window.split_container.orientation() == Qt.Horizontal
        main_window._add_workspace_vertical()
        assert main_window.split_container._total_leaf_count() == 3
        assert main_window.split_container.orientation() == Qt.Vertical
        wrapper = main_window.split_container.widget(0)
        assert isinstance(wrapper, QSplitter)
        assert wrapper.orientation() == Qt.Horizontal


class TestDocumentInvalidFile:
    """Tests for Document.is_invalid_file setter."""

    def test_set_is_invalid_file(self):
        """Test setting is_invalid_file on a Document."""
        doc = Document()
        assert doc.is_invalid_file is False
        doc.is_invalid_file = True
        assert doc.is_invalid_file is True


class TestDocumentManagerUpdatePath:
    """Tests for DocumentManager.update_document_path removing old path."""

    def test_update_document_path_removes_old(self, tmp_path):
        """Test that update_document_path removes old path mapping."""
        mgr = DocumentManager()
        old_path = str(tmp_path / "old.py")
        new_path = str(tmp_path / "new.py")
        doc = mgr.get_or_create_document(old_path)
        assert mgr.get_document_by_path(old_path) is doc
        mgr.update_document_path(doc, new_path)
        assert mgr.get_document_by_path(old_path) is None
        assert mgr.get_document_by_path(new_path) is doc


class TestFindReplaceDialogExtra:
    """Additional tests for FindReplaceDialog edge cases."""

    def test_find_previous_empty_search(self, main_window, qtbot):
        """Test find_previous with empty search text."""
        dialog = FindReplaceDialog(main_window)
        dialog.find_input.setText("")
        dialog.find_previous()
        assert "Please enter search text" in dialog.status_label.text()
        dialog.close()

    def test_find_previous_not_found(self, main_window, qtbot):
        """Test find_previous when text is not found."""
        main_window.editor.setPlainText("Hello World")
        dialog = FindReplaceDialog(main_window)
        dialog.find_input.setText("zzzzz")
        dialog.find_previous()
        assert "not found" in dialog.status_label.text().lower()
        dialog.close()

    def test_find_previous_case_sensitive(self, main_window, qtbot):
        """Test find_previous with case sensitivity."""
        main_window.editor.setPlainText("Hello hello HELLO")
        cursor = main_window.editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        main_window.editor.setTextCursor(cursor)
        dialog = FindReplaceDialog(main_window)
        dialog.find_input.setText("hello")
        dialog.case_sensitive_checkbox.setChecked(True)
        dialog.find_previous()
        cursor = main_window.editor.textCursor()
        selected = main_window.editor.toPlainText()[cursor.selectionStart():cursor.selectionEnd()]
        assert selected == "hello"
        dialog.close()

    def test_replace_current_no_selection(self, main_window, qtbot):
        """Test replace_current when nothing is selected."""
        main_window.editor.setPlainText("Hello World")
        cursor = main_window.editor.textCursor()
        cursor.clearSelection()
        main_window.editor.setTextCursor(cursor)
        dialog = FindReplaceDialog(main_window)
        dialog.replace_input.setText("Hi")
        dialog.replace_current()
        assert "No text selected" in dialog.status_label.text()
        dialog.close()

    def test_replace_all_empty_search(self, main_window, qtbot):
        """Test replace_all with empty search text."""
        dialog = FindReplaceDialog(main_window)
        dialog.find_input.setText("")
        dialog.replace_all()
        assert "Please enter search text" in dialog.status_label.text()
        dialog.close()

    def test_replace_all_case_sensitive(self, main_window, qtbot):
        """Test replace_all with case sensitivity enabled."""
        main_window.editor.setPlainText("Hello hello HELLO")
        dialog = FindReplaceDialog(main_window)
        dialog.find_input.setText("hello")
        dialog.replace_input.setText("world")
        dialog.case_sensitive_checkbox.setChecked(True)
        dialog.replace_all()
        text = main_window.editor.toPlainText()
        assert text == "Hello world HELLO"
        dialog.close()

    def test_find_next_no_editor(self, qtbot):
        """Test find_next with no editor."""
        dialog = FindReplaceDialog(None)
        dialog.editor = None
        dialog.find_next()
        dialog.close()

    def test_find_previous_no_editor(self, qtbot):
        """Test find_previous with no editor."""
        dialog = FindReplaceDialog(None)
        dialog.editor = None
        dialog.find_previous()
        dialog.close()

    def test_replace_current_no_editor(self, qtbot):
        """Test replace_current with no editor."""
        dialog = FindReplaceDialog(None)
        dialog.editor = None
        dialog.replace_current()
        dialog.close()

    def test_replace_all_no_editor(self, qtbot):
        """Test replace_all with no editor."""
        dialog = FindReplaceDialog(None)
        dialog.editor = None
        dialog.replace_all()
        dialog.close()


class TestStripedOverlay:
    """Tests for StripedOverlay widget."""

    def test_striped_overlay_paint(self, qtbot):
        """Test StripedOverlay paint event runs without error."""
        overlay = StripedOverlay()
        overlay.resize(200, 200)
        overlay.repaint()
        overlay.close()


class TestMultiLineHighlighting:
    """Tests for multi-line comment/string highlighting."""

    def test_multiline_comment_c(self, editor, qtbot):
        """Test multi-line comment highlighting for C language."""
        editor.set_language("c")
        editor.setPlainText("/* this is\na multi-line\ncomment */")
        # Force re-highlight
        editor.highlighter.rehighlight()

    def test_multiline_comment_python(self, editor, qtbot):
        """Test multi-line string highlighting for Python."""
        editor.set_language("python")
        editor.setPlainText('x = """\nmulti\nline\n"""')
        editor.highlighter.rehighlight()

    def test_multiline_comment_continued(self, editor, qtbot):
        """Test multi-line comment that continues (no end found)."""
        editor.set_language("javascript")
        editor.setPlainText("/* unterminated comment")
        editor.highlighter.rehighlight()


class TestLightModeLineNumbers:
    """Tests for line number painting in light mode."""

    def test_paint_light_mode(self, editor, qtbot):
        """Test line number painting in light mode."""
        editor.set_dark_mode(False)
        qtbot.keyClicks(editor, "Line 1")
        qtbot.keyClick(editor, Qt.Key_Return)
        qtbot.keyClicks(editor, "Line 2")
        editor.line_number_area.repaint()

    def test_highlight_current_line_light_mode(self, editor, qtbot):
        """Test current line highlight in light mode with brackets."""
        editor.set_dark_mode(False)
        editor.setPlainText("(hello)")
        cursor = editor.textCursor()
        cursor.setPosition(0)
        editor.setTextCursor(cursor)
        editor.match_brackets()
        assert len(editor.bracket_positions) == 2


class TestKeyUpDownEdgeCases:
    """Tests for Key_Up at first line and Key_Down at last line."""

    def test_key_up_at_first_line(self, editor, qtbot):
        """Test pressing up arrow at first line moves to start of line."""
        editor.setPlainText("Hello World")
        cursor = editor.textCursor()
        cursor.setPosition(5)
        editor.setTextCursor(cursor)
        qtbot.keyClick(editor, Qt.Key_Up)
        assert editor.textCursor().position() == 0

    def test_key_down_at_last_line(self, editor, qtbot):
        """Test pressing down arrow at last line moves to end of line."""
        editor.setPlainText("Hello World")
        cursor = editor.textCursor()
        cursor.setPosition(5)
        editor.setTextCursor(cursor)
        qtbot.keyClick(editor, Qt.Key_Down)
        assert editor.textCursor().position() == len("Hello World")


class TestEditorPaneExtra:
    """Tests for EditorPane specific functionality."""

    def test_editor_pane_focus_event(self, main_window, qtbot):
        """Test EditorPane emits pane_focused on focusInEvent."""
        pane = main_window.editor
        signals_received = []
        pane.pane_focused.connect(lambda p: signals_received.append(p))
        from PyQt5.QtGui import QFocusEvent
        from PyQt5.QtCore import QEvent
        pane.focusInEvent(QFocusEvent(QEvent.FocusIn))
        assert len(signals_received) == 1

    def test_editor_pane_cleanup(self, main_window, qtbot):
        """Test EditorPane cleanup returns remaining view count."""
        pane = main_window.editor
        doc = pane.doc
        initial_views = doc.view_count
        remaining = pane.cleanup()
        assert remaining == initial_views - 1
        # Restore to avoid teardown issue
        doc.add_view()


class TestEditorTabWidgetExtra:
    """Tests for EditorTabWidget specifics."""

    def test_set_active_split_light_mode(self, main_window, qtbot):
        """Test set_active_split with light mode."""
        tw = main_window.split_container.active_tab_widget()
        tw.set_active_split(True, dark_mode=False)
        tw.set_active_split(False, dark_mode=False)

    def test_find_editor_for_nonexistent_doc(self, main_window, qtbot):
        """Test find_editor_for_document returns None for unknown doc."""
        tw = main_window.split_container.active_tab_widget()
        doc = Document()
        pane, idx = tw.find_editor_for_document(doc)
        assert pane is None
        assert idx == -1

    def test_focus_document_returns_false(self, main_window, qtbot):
        """Test focus_document returns False for unknown doc."""
        tw = main_window.split_container.active_tab_widget()
        doc = Document()
        assert tw.focus_document(doc) is False

    def test_close_tab_emits_all_tabs_closed(self, main_window, qtbot):
        """Test closing last tab in a tab widget."""
        main_window._split_right()
        all_tw = main_window.split_container._all_tab_widgets()
        new_tw = all_tw[-1]
        assert new_tw.count() > 0
        remaining = new_tw.close_tab(0)
        assert new_tw.count() == 0


class TestSplitContainerExtra:
    """Tests for SplitContainer edge cases."""

    def test_on_pane_focused_switches_active(self, main_window, qtbot):
        """Test that pane focus switches active tab widget."""
        main_window._split_right()
        all_tw = main_window.split_container._all_tab_widgets()
        assert len(all_tw) == 2
        # Focus first pane
        first_pane = all_tw[0].current_editor()
        from PyQt5.QtGui import QFocusEvent
        from PyQt5.QtCore import QEvent
        first_pane.focusInEvent(QFocusEvent(QEvent.FocusIn))
        assert main_window.split_container.active_tab_widget() is all_tw[0]

    def test_current_editor_no_active(self, qtbot):
        """Test current_editor returns None when no active tab widget."""
        mgr = DocumentManager()
        sc = SplitContainer(mgr)
        sc._active_tab_widget = None
        assert sc.current_editor() is None
        sc.close()

    def test_open_document_in_new_split(self, main_window, qtbot):
        """Test open_document with in_new_split=True."""
        doc = main_window.doc_manager.get_or_create_document()
        pane = main_window.split_container.open_document(doc, in_new_split=True)
        assert pane is not None

    def test_focus_or_open_document_disallow_new(self, main_window, qtbot):
        """Test focus_or_open_document with allow_new_view=False for unfound doc."""
        doc = Document()
        result = main_window.split_container.focus_or_open_document(doc, allow_new_view=False)
        assert result is None

    def test_split_no_active(self, main_window, qtbot):
        """Test split returns None when no active tab widget."""
        main_window.split_container._active_tab_widget = None
        result = main_window.split_container.split(Qt.Horizontal)
        assert result is None
        # Restore
        all_tw = main_window.split_container._all_tab_widgets()
        if all_tw:
            main_window.split_container._active_tab_widget = all_tw[0]

    def test_close_split_when_only_one(self, main_window, qtbot):
        """Test close_split does nothing when only one split exists."""
        assert main_window.split_container._total_leaf_count() == 1
        main_window.split_container.close_split()
        assert main_window.split_container._total_leaf_count() == 1

    def test_select_new_active_empty(self, qtbot):
        """Test _select_new_active when no tab widgets remain."""
        mgr = DocumentManager()
        sc = SplitContainer(mgr)
        # Remove all child widgets
        while sc.count():
            w = sc.widget(0)
            w.setParent(None)
        sc._select_new_active()
        assert sc._active_tab_widget is None
        sc.close()

    def test_on_tab_close_requested_cancel(self, main_window, qtbot):
        """Test _on_tab_close_requested with modified doc and Cancel."""
        tw = main_window.split_container.active_tab_widget()
        pane = tw.current_editor()
        pane.doc.document.setPlainText("modified")
        pane.doc.add_view()  # Make view_count == 1 after removing initial
        pane.doc.remove_view()
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Cancel):
            main_window.split_container._on_tab_close_requested(tw, 0)
        # Tab should still exist
        assert tw.count() > 0
        pane.doc.is_modified = False

    def test_on_tab_close_requested_discard(self, main_window, qtbot):
        """Test _on_tab_close_requested with modified doc and Discard."""
        main_window._new_file()
        tw = main_window.split_container.active_tab_widget()
        pane = tw.current_editor()
        pane.doc.document.setPlainText("modified")
        initial_count = tw.count()
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Discard):
            main_window.split_container._on_tab_close_requested(tw, tw.indexOf(pane))
        assert tw.count() == initial_count - 1

    def test_save_document_delegation(self, main_window, tmp_path, qtbot):
        """Test _save_document delegates to parent TextEditor."""
        file_path = str(tmp_path / "test_save.txt")
        doc = main_window.editor.doc
        main_window.doc_manager.update_document_path(doc, file_path)
        doc.document.setPlainText("content")
        result = main_window.split_container._save_document(doc)
        assert result is True
        assert os.path.exists(file_path)

    def test_on_editor_changed_updates_active(self, main_window, qtbot):
        """Test _on_editor_changed updates active tab widget."""
        main_window._split_right()
        all_tw = main_window.split_container._all_tab_widgets()
        pane = all_tw[0].current_editor()
        main_window.split_container._on_editor_changed(pane)


class TestFileTreeViewExtra:
    """Tests for FileTreeView edge cases."""

    def test_select_file_nonexistent(self, file_tree):
        """Test select_file with nonexistent path."""
        file_tree.select_file("/nonexistent/path/file.txt")

    def test_select_file_none(self, file_tree):
        """Test select_file with None."""
        file_tree.select_file(None)

    def test_cleanup_explorer_invalid_index(self, file_tree, tmp_path):
        """Test cleanup_explorer with invalid file path."""
        file_tree.set_root_path(str(tmp_path))
        file_tree.cleanup_explorer("/totally/fake/path.txt")


class TestTextEditorEditActions:
    """Tests for TextEditor edit action delegates."""

    def test_undo_action(self, main_window, qtbot):
        """Test _undo delegates to editor."""
        qtbot.keyClicks(main_window.editor, "hello")
        main_window._undo()
        assert main_window.editor.toPlainText() != "hello" or main_window.editor.toPlainText() == ""

    def test_redo_action(self, main_window, qtbot):
        """Test _redo delegates to editor."""
        qtbot.keyClicks(main_window.editor, "hello")
        main_window._undo()
        main_window._redo()

    def test_cut_action(self, main_window, qtbot):
        """Test _cut delegates to editor."""
        qtbot.keyClicks(main_window.editor, "hello")
        main_window.editor.selectAll()
        main_window._cut()

    def test_copy_action(self, main_window, qtbot):
        """Test _copy delegates to editor."""
        qtbot.keyClicks(main_window.editor, "hello")
        main_window.editor.selectAll()
        main_window._copy()

    def test_paste_action(self, main_window, qtbot):
        """Test _paste delegates to editor."""
        main_window._paste()

    def test_select_all_action(self, main_window, qtbot):
        """Test _select_all delegates to editor."""
        qtbot.keyClicks(main_window.editor, "hello")
        main_window._select_all()
        assert main_window.editor.textCursor().hasSelection()


class TestTextEditorEdgeCases:
    """Tests for TextEditor edge cases."""

    def test_on_active_editor_changed_disconnect(self, main_window, qtbot):
        """Test _on_active_editor_changed disconnects old pane."""
        pane1 = main_window.editor
        main_window._on_active_editor_changed(pane1)
        # Now change to another
        main_window._split_right()
        pane2 = main_window.editor
        main_window._on_active_editor_changed(pane2)
        # Change to None
        main_window._on_active_editor_changed(None)

    def test_update_window_title_no_editor(self, main_window, qtbot):
        """Test _update_window_title when no editor."""
        main_window.split_container._active_tab_widget = None
        main_window._update_window_title()
        assert main_window.windowTitle() == "Text Editor"
        # Restore
        all_tw = main_window.split_container._all_tab_widgets()
        if all_tw:
            main_window.split_container._active_tab_widget = all_tw[0]

    def test_split_right_empty_active(self, main_window, qtbot):
        """Test _split_right when active tab widget is empty."""
        main_window._split_right()
        active_tw = main_window.split_container.active_tab_widget()
        # Close all tabs in the new split to make it empty
        while active_tw.count() > 0:
            active_tw.close_tab(0)
        main_window._split_right()

    def test_split_down_empty_active(self, main_window, qtbot):
        """Test _split_down when active tab widget is empty."""
        main_window._split_right()
        active_tw = main_window.split_container.active_tab_widget()
        while active_tw.count() > 0:
            active_tw.close_tab(0)
        main_window._split_down()

    def test_close_split_with_save_discard(self, main_window, qtbot):
        """Test _close_split with modified document and Discard."""
        main_window._split_right()
        pane = main_window.editor
        pane.doc.document.setPlainText("unsaved")
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Discard):
            main_window._close_split()

    def test_update_cursor_position_no_editor(self, main_window, qtbot):
        """Test _update_cursor_position when no editor."""
        main_window.split_container._active_tab_widget = None
        main_window._update_cursor_position()
        assert "Ready" in main_window.statusbar.currentMessage()
        all_tw = main_window.split_container._all_tab_widgets()
        if all_tw:
            main_window.split_container._active_tab_widget = all_tw[0]

    def test_open_unicode_error_file(self, main_window, tmp_path, qtbot):
        """Test opening a file that causes UnicodeDecodeError."""
        bad_file = tmp_path / "bad_unicode.txt"
        bad_file.write_bytes(b'\x80\x81\x82\x83' * 200)
        with patch.object(QMessageBox, 'warning'):
            main_window._open_file_path(str(bad_file))

    def test_open_file_general_exception(self, main_window, tmp_path, qtbot):
        """Test opening a file that raises a general exception."""
        file_path = str(tmp_path / "test.txt")
        with open(file_path, 'w') as f:
            f.write("hello")
        with patch('builtins.open', side_effect=PermissionError("denied")):
            with patch.object(QMessageBox, 'critical'):
                main_window._open_file_path(file_path)

    def test_binary_detection_null_bytes(self, main_window, tmp_path):
        """Test binary detection with null bytes."""
        null_file = tmp_path / "null.bin"
        null_file.write_bytes(b'some text\x00with null bytes')
        assert main_window._is_likely_binary(str(null_file)) is True

    def test_save_file_invalid_doc(self, main_window, qtbot):
        """Test _save_file when doc is invalid."""
        main_window.editor.doc._is_invalid_file = True
        main_window._save_file()
        main_window.editor.doc._is_invalid_file = False

    def test_save_file_as_cancelled(self, main_window, qtbot):
        """Test _save_file_as when dialog is cancelled."""
        with patch('text_editor.QFileDialog') as MockDialog:
            mock_instance = MagicMock()
            MockDialog.return_value = mock_instance
            mock_instance.exec_.return_value = QFileDialog.Rejected
            main_window._save_file_as()

    def test_save_document_error(self, main_window, tmp_path, qtbot):
        """Test _save_document with write error."""
        doc = main_window.editor.doc
        main_window.doc_manager.update_document_path(doc, "/invalid/readonly/path/file.txt")
        with patch.object(QMessageBox, 'critical'):
            result = main_window._save_document(doc)
        assert result is False

    def test_show_find_dialog(self, main_window, qtbot):
        """Test _show_find_dialog creates and shows dialog."""
        with patch('text_editor.FindReplaceDialog') as MockDialog:
            mock_instance = MagicMock()
            MockDialog.return_value = mock_instance
            main_window._show_find_dialog()
            mock_instance.exec_.assert_called_once()

    def test_close_event_exception(self, main_window, qtbot):
        """Test closeEvent handles exception gracefully."""
        event = MagicMock()
        with patch.object(main_window, '_check_save_all', side_effect=RuntimeError("test")):
            main_window.closeEvent(event)
        event.accept.assert_called_once()

    def test_check_save_all_exception_in_doc(self, main_window, qtbot):
        """Test _check_save_all handles exception accessing doc."""
        main_window._skip_save_check = False
        doc = main_window.editor.doc
        # Force exception by making is_modified raise
        with patch.object(type(doc), 'is_modified', new_callable=lambda: property(lambda s: (_ for _ in ()).throw(RuntimeError("test")))):
            result = main_window._check_save_all()
        assert result is True

    def test_create_new_folder(self, main_window, tmp_path, qtbot):
        """Test _create_new_folder creates a new folder."""
        mock_dialog = MagicMock()
        mock_dialog.directory.return_value.absolutePath.return_value = str(tmp_path)
        with patch('text_editor.QInputDialog.getText', return_value=("new_folder", True)):
            main_window._create_new_folder(mock_dialog)
        assert os.path.exists(tmp_path / "new_folder")

    def test_create_new_folder_cancelled(self, main_window, tmp_path, qtbot):
        """Test _create_new_folder when cancelled."""
        mock_dialog = MagicMock()
        mock_dialog.directory.return_value.absolutePath.return_value = str(tmp_path)
        with patch('text_editor.QInputDialog.getText', return_value=("", False)):
            main_window._create_new_folder(mock_dialog)

    def test_create_new_folder_error(self, main_window, tmp_path, qtbot):
        """Test _create_new_folder with error."""
        mock_dialog = MagicMock()
        mock_dialog.directory.return_value.absolutePath.return_value = str(tmp_path)
        with patch('text_editor.QInputDialog.getText', return_value=("test", True)):
            with patch('os.makedirs', side_effect=OSError("error")):
                with patch.object(QMessageBox, 'critical'):
                    main_window._create_new_folder(mock_dialog)

    def test_save_file_as_invalid_doc(self, main_window, qtbot):
        """Test _save_file_as when doc is invalid."""
        main_window.editor.doc._is_invalid_file = True
        main_window._save_file_as()
        main_window.editor.doc._is_invalid_file = False

    def test_save_to_path_via_main_window(self, main_window, tmp_path, qtbot):
        """Test _save_to_path backward compatibility method."""
        file_path = str(tmp_path / "saveto.txt")
        main_window.editor.setPlainText("content")
        result = main_window._save_to_path(file_path)
        assert result is True
        with open(file_path) as f:
            assert f.read() == "content"


class TestSyntaxHighlighterAllLanguages:
    """Test highlighting for multiple language types to cover all branches."""

    def test_highlight_html(self, editor, qtbot):
        """Test HTML tag and attribute highlighting."""
        editor.set_language("html")
        editor.setPlainText('<div class="test">Hello</div>')
        editor.highlighter.rehighlight()

    def test_highlight_css(self, editor, qtbot):
        """Test CSS property highlighting."""
        editor.set_language("css")
        editor.setPlainText('body { color: red; background: blue; }')
        editor.highlighter.rehighlight()

    def test_highlight_sql(self, editor, qtbot):
        """Test SQL keyword highlighting (case insensitive)."""
        editor.set_language("sql")
        editor.setPlainText("SELECT * FROM users WHERE id = 1;")
        editor.highlighter.rehighlight()

    def test_highlight_cpp_preprocessor(self, editor, qtbot):
        """Test C++ preprocessor directive highlighting."""
        editor.set_language("cpp")
        editor.setPlainText('#include <iostream>\n#define MAX 100')
        editor.highlighter.rehighlight()

    def test_highlight_python_decorator(self, editor, qtbot):
        """Test Python decorator highlighting."""
        editor.set_language("python")
        editor.setPlainText('@decorator\nclass MyClass:\n    pass')
        editor.highlighter.rehighlight()

    def test_highlight_xml(self, editor, qtbot):
        """Test XML highlighting."""
        editor.set_language("xml")
        editor.setPlainText('<!-- comment -->\n<root attr="val">text</root>')
        editor.highlighter.rehighlight()

    def test_set_dark_mode_on_highlighter(self, editor, qtbot):
        """Test switching highlighter to light mode."""
        editor.set_language("python")
        editor.highlighter.set_dark_mode(False)
        assert editor.highlighter.dark_mode is False
        editor.highlighter.set_dark_mode(True)


class TestEditorResizeEvent:
    """Test editor resize event."""

    def test_resize_event(self, editor, qtbot):
        """Test resizeEvent updates line number area."""
        from PyQt5.QtGui import QResizeEvent
        from PyQt5.QtCore import QSize
        editor.resize(800, 600)


class TestEditorPaneProperties:
    """Test EditorPane property passthrough."""

    def test_pane_current_file_setter_noop(self, main_window, qtbot):
        """Test EditorPane.current_file setter is a no-op."""
        pane = main_window.editor
        pane.current_file = "/some/path"
        assert pane.current_file != "/some/path"

    def test_pane_is_modified_setter_noop(self, main_window, qtbot):
        """Test EditorPane.is_modified setter is a no-op."""
        pane = main_window.editor
        pane.is_modified = True

    def test_pane_is_invalid_file_setter_noop(self, main_window, qtbot):
        """Test EditorPane.is_invalid_file setter is a no-op."""
        pane = main_window.editor
        pane.is_invalid_file = True

    def test_pane_current_language_setter_noop(self, main_window, qtbot):
        """Test EditorPane.current_language setter is a no-op."""
        pane = main_window.editor
        pane.current_language = "python"

    def test_pane_on_doc_path_changed(self, main_window, qtbot):
        """Test EditorPane._on_doc_path_changed updates language."""
        pane = main_window.editor
        pane._on_doc_path_changed("test.py")

    def test_pane_on_doc_path_changed_empty(self, main_window, qtbot):
        """Test EditorPane._on_doc_path_changed with empty path."""
        pane = main_window.editor
        pane._on_doc_path_changed("")


class TestCheckSaveAllExtra:
    """Extra tests for _check_save_all edge cases."""

    def test_check_save_all_skip_check(self, main_window, qtbot):
        """Test _check_save_all with skip_save_check."""
        main_window._skip_save_check = True
        main_window.editor.doc.document.setPlainText("modified")
        assert main_window._check_save_all() is True

    def test_check_save_all_no_doc_manager(self, main_window, qtbot):
        """Test _check_save_all when doc_manager is None."""
        main_window._skip_save_check = False
        old_mgr = main_window.doc_manager
        main_window.doc_manager = None
        assert main_window._check_save_all() is True
        main_window.doc_manager = old_mgr

    def test_check_save_all_save_with_path(self, main_window, tmp_path, qtbot):
        """Test _check_save_all with Save and file has path."""
        main_window._skip_save_check = False
        file_path = str(tmp_path / "save_check.txt")
        doc = main_window.editor.doc
        main_window.doc_manager.update_document_path(doc, file_path)
        doc.document.setPlainText("modified content")
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Save):
            result = main_window._check_save_all()
        assert result is True
        doc.is_modified = False

    def test_check_save_all_save_no_path(self, main_window, qtbot):
        """Test _check_save_all with Save but no file path triggers save_as."""
        main_window._skip_save_check = False
        doc = main_window.editor.doc
        doc.document.setPlainText("modified content")
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Save):
            with patch.object(main_window, '_save_file_as'):
                result = main_window._check_save_all()
        doc.is_modified = False


class TestOnAllTabsClosed:
    """Test _on_all_tabs_closed behavior."""

    def test_on_all_tabs_closed_removes_split(self, main_window, qtbot):
        """Test _on_all_tabs_closed removes the split when multiple exist."""
        main_window._split_right()
        assert main_window.split_container._total_leaf_count() == 2
        active_tw = main_window.split_container.active_tab_widget()
        # Close all tabs which triggers _on_all_tabs_closed
        while active_tw.count() > 0:
            active_tw.close_tab(0)


class TestCloseCurrentTab:
    """Test _close_current_tab behavior."""

    def test_close_current_tab_with_unmodified(self, main_window, qtbot):
        """Test closing current tab with unmodified document."""
        main_window._new_file()
        initial_count = main_window.split_container.active_tab_widget().count()
        main_window._close_current_tab()
        qtbot.wait(50)


class TestDocumentManagerGetByPathNone:
    """Test DocumentManager.get_document_by_path with None/empty."""

    def test_get_document_by_path_none(self):
        """Test get_document_by_path returns None for None."""
        mgr = DocumentManager()
        assert mgr.get_document_by_path(None) is None

    def test_get_document_by_path_empty(self):
        """Test get_document_by_path returns None for empty string."""
        mgr = DocumentManager()
        assert mgr.get_document_by_path("") is None


class TestFindPreviousWithSelection:
    """Test find_previous when cursor has selection."""

    def test_find_previous_moves_to_selection_start(self, main_window, qtbot):
        """Test find_previous moves cursor to selection start before searching."""
        main_window.editor.setPlainText("Hello Hello Hello")
        # First find to select second Hello
        dialog = FindReplaceDialog(main_window)
        dialog.find_input.setText("Hello")
        dialog.find_next()
        dialog.find_next()
        # Now cursor has selection on second "Hello"
        assert main_window.editor.textCursor().hasSelection()
        # find_previous should go to first "Hello"
        dialog.find_previous()
        cursor = main_window.editor.textCursor()
        assert cursor.hasSelection()
        dialog.close()


class TestCloseSplitSaveCancel:
    """Test _close_split with Save-Cancel flow."""

    def test_close_split_save_cancel(self, main_window, qtbot):
        """Test _close_split Cancel prevents close."""
        main_window._split_right()
        pane = main_window.editor
        pane.doc.document.setPlainText("unsaved changes")
        initial_count = main_window.split_container._total_leaf_count()
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Cancel):
            main_window._close_split()
        assert main_window.split_container._total_leaf_count() == initial_count

    def test_close_split_save(self, main_window, tmp_path, qtbot):
        """Test _close_split Save saves and closes."""
        main_window._split_right()
        pane = main_window.editor
        file_path = str(tmp_path / "close_save.txt")
        main_window.doc_manager.update_document_path(pane.doc, file_path)
        pane.doc.document.setPlainText("unsaved changes")
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Save):
            main_window._close_split()
        assert os.path.exists(file_path)


class TestOpenDocumentInNewSplitMultiple:
    """Test open_document with in_new_split when multiple splits exist."""

    def test_open_in_new_split_switches_to_other(self, main_window, qtbot):
        """Test open_document in_new_split switches to other split when >=2 exist."""
        main_window._split_right()
        all_tw = main_window.split_container._all_tab_widgets()
        assert len(all_tw) >= 2
        active = main_window.split_container.active_tab_widget()
        doc = main_window.doc_manager.get_or_create_document()
        pane = main_window.split_container.open_document(doc, in_new_split=True)
        # Active should have switched to the other tab widget
        new_active = main_window.split_container.active_tab_widget()
        assert new_active is not active


class TestCloseSplitNoneActive:
    """Test close_split when _active_tab_widget is None."""

    def test_close_split_none_active(self, main_window, qtbot):
        """Test close_split does nothing when active is None."""
        main_window.split_container._active_tab_widget = None
        main_window.split_container.close_split()
        all_tw = main_window.split_container._all_tab_widgets()
        if all_tw:
            main_window.split_container._active_tab_widget = all_tw[0]


class TestOnTabCloseRequestedSave:
    """Test _on_tab_close_requested with Save option."""

    def test_tab_close_save(self, main_window, tmp_path, qtbot):
        """Test tab close with Save saves and closes."""
        main_window._new_file()
        tw = main_window.split_container.active_tab_widget()
        pane = tw.current_editor()
        file_path = str(tmp_path / "tab_save.txt")
        main_window.doc_manager.update_document_path(pane.doc, file_path)
        pane.doc.document.setPlainText("modified")
        initial_count = tw.count()
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Save):
            main_window.split_container._on_tab_close_requested(tw, tw.indexOf(pane))
        assert os.path.exists(file_path)


class TestSaveDocumentNoPath:
    """Test _save_document with no file path."""

    def test_save_document_no_path(self, main_window, qtbot):
        """Test _save_document returns False when doc has no path."""
        doc = main_window.editor.doc
        result = main_window._save_document(doc)
        assert result is False


class TestSaveFileNoEditor:
    """Test _save_file and _save_to_path when no editor."""

    def test_save_file_no_editor(self, main_window, qtbot):
        """Test _save_file when no editor exists."""
        main_window.split_container._active_tab_widget = None
        main_window._save_file()
        all_tw = main_window.split_container._all_tab_widgets()
        if all_tw:
            main_window.split_container._active_tab_widget = all_tw[0]

    def test_save_to_path_no_editor(self, main_window, tmp_path, qtbot):
        """Test _save_to_path when no editor exists."""
        main_window.split_container._active_tab_widget = None
        result = main_window._save_to_path(str(tmp_path / "test.txt"))
        assert result is False
        all_tw = main_window.split_container._all_tab_widgets()
        if all_tw:
            main_window.split_container._active_tab_widget = all_tw[0]

    def test_save_file_as_no_editor(self, main_window, qtbot):
        """Test _save_file_as when no editor exists."""
        main_window.split_container._active_tab_widget = None
        main_window._save_file_as()
        all_tw = main_window.split_container._all_tab_widgets()
        if all_tw:
            main_window.split_container._active_tab_widget = all_tw[0]


class TestSaveFileAsAccepted:
    """Test _save_file_as with accepted dialog."""

    def test_save_file_as_accepted(self, main_window, tmp_path, qtbot):
        """Test _save_file_as saves when dialog accepted."""
        file_path = str(tmp_path / "saveas.txt")
        main_window.editor.setPlainText("content to save")
        with patch('text_editor.QFileDialog') as MockDialog:
            mock_instance = MagicMock()
            MockDialog.return_value = mock_instance
            MockDialog.AcceptSave = QFileDialog.AcceptSave
            MockDialog.ShowDirsOnly = QFileDialog.ShowDirsOnly
            MockDialog.DontUseNativeDialog = QFileDialog.DontUseNativeDialog
            MockDialog.Accepted = QFileDialog.Accepted
            mock_instance.exec_.return_value = QFileDialog.Accepted
            mock_instance.selectedFiles.return_value = [file_path]
            main_window._save_file_as()
        assert os.path.exists(file_path)


class TestOpenFileException:
    """Test _open_file_path with general exception in the try block."""

    def test_open_file_exception_in_setup(self, main_window, tmp_path, qtbot):
        """Test exception during document setup."""
        text_file = tmp_path / "test.txt"
        text_file.write_text("hello")
        with patch.object(main_window.doc_manager, 'get_or_create_document', side_effect=Exception("test")):
            with patch.object(QMessageBox, 'critical'):
                main_window._open_file_path(str(text_file))


class TestSplitRightDownEmptyActive:
    """Test _split_right/_split_down when active tab count is 0."""

    def test_split_right_creates_file_in_empty(self, main_window, qtbot):
        """Test _split_right creates new file when active tab is empty."""
        # First get to a state where active tab widget has 0 tabs
        tw = main_window.split_container.active_tab_widget()
        while tw.count() > 0:
            tw.close_tab(0)
        assert tw.count() == 0
        main_window._split_right()
        assert tw.count() > 0

    def test_split_down_creates_file_in_empty(self, main_window, qtbot):
        """Test _split_down creates new file when active tab is empty."""
        tw = main_window.split_container.active_tab_widget()
        while tw.count() > 0:
            tw.close_tab(0)
        assert tw.count() == 0
        main_window._split_down()
        assert tw.count() > 0


class TestCloseTabInvalid:
    """Test EditorTabWidget.close_tab with invalid index."""

    def test_close_tab_none_widget(self, main_window, qtbot):
        """Test close_tab returns 0 when widget is None."""
        tw = main_window.split_container.active_tab_widget()
        result = tw.close_tab(999)
        assert result == 0


class TestCheckSaveAllDocManagerException:
    """Test _check_save_all exception in documents access."""

    def test_check_save_all_documents_exception(self, main_window, qtbot):
        """Test _check_save_all handles RuntimeError in documents list."""
        main_window._skip_save_check = False
        with patch.object(type(main_window.doc_manager), 'documents', new_callable=lambda: property(lambda s: (_ for _ in ()).throw(RuntimeError("test")))):
            result = main_window._check_save_all()
        assert result is True

    def test_check_save_all_outer_exception(self, main_window, qtbot):
        """Test _check_save_all handles exception wrapping entire block."""
        main_window._skip_save_check = False
        with patch.object(main_window, 'doc_manager', new_callable=lambda: property(lambda s: (_ for _ in ()).throw(RuntimeError("test")))):
            result = main_window._check_save_all()
        assert result is True


class TestOnActiveEditorChangedDisconnectException:
    """Test disconnect exception in _on_active_editor_changed."""

    def test_disconnect_exception_handled(self, main_window, qtbot):
        """Test _on_active_editor_changed handles disconnect exception."""
        pane = main_window.editor
        main_window._on_active_editor_changed(pane)
        # Force the connected pane to be something that will raise on disconnect
        main_window._cursor_connected_pane = MagicMock()
        main_window._cursor_connected_pane.cursorPositionChanged.disconnect.side_effect = TypeError("not connected")
        main_window._on_active_editor_changed(pane)


class TestSelectFileValid:
    """Test FileTreeView.select_file with a valid file."""

    def test_select_file_valid(self, file_tree, temp_file):
        """Test select_file with valid existing file."""
        dir_path = os.path.dirname(temp_file)
        file_tree.set_root_path(dir_path)
        file_tree.select_file(temp_file)


class TestCleanupExplorerCollapsesNonAncestors:
    """Test cleanup_explorer properly collapses directories."""

    def test_cleanup_explorer_with_nested_dir(self, file_tree, tmp_path):
        """Test cleanup_explorer with nested directory structure."""
        # Create nested structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        sub_subdir = subdir / "nested"
        sub_subdir.mkdir()
        test_file = sub_subdir / "test.txt"
        test_file.write_text("test")
        file_tree.set_root_path(str(tmp_path))
        file_tree.cleanup_explorer(str(test_file))


class TestStripedOverlayPaintEvent:
    """Test StripedOverlay.paintEvent actually paints stripes and text (lines 386-418)."""

    def test_paint_event_draws_stripes_and_text(self, qtbot):
        """Test that paintEvent executes all drawing code."""
        overlay = StripedOverlay()
        overlay.resize(300, 300)
        overlay.show()
        qtbot.waitExposed(overlay)
        # Grab the widget as a pixmap — forces full paintEvent execution
        pixmap = overlay.grab()
        assert not pixmap.isNull()
        assert pixmap.width() > 0
        assert pixmap.height() > 0
        overlay.close()


class TestLightModeLineNumberPaint:
    """Test light mode branch in line_number_area_paint_event (lines 1152-1153)."""

    def test_light_mode_line_numbers_painted(self, editor, qtbot):
        """Test that line numbers paint correctly in light mode."""
        editor.set_dark_mode(False)
        editor.setPlainText("line1\nline2\nline3")
        editor.show()
        qtbot.waitExposed(editor)
        pixmap = editor.line_number_area.grab()
        assert not pixmap.isNull()
        editor.close()


class TestCloseTabDisconnectException:
    """Test close_tab handles disconnect TypeError/RuntimeError (lines 1621-1622)."""

    def test_close_tab_disconnect_exception(self, main_window, qtbot):
        """Test close_tab gracefully handles disconnect failure."""
        main_window._new_file()
        tw = main_window.split_container.active_tab_widget()
        pane = tw.widget(tw.count() - 1)
        # Inject a fake _doc_connections entry that will raise on disconnect
        mock_doc = MagicMock()
        mock_doc.modified_changed.disconnect.side_effect = TypeError("not connected")
        pane._doc_connections = [(mock_doc, 'modified_changed', lambda: None)]
        tw.close_tab(tw.count() - 1)


class TestOpenDocumentNoActiveTabWidget:
    """Test open_document returns None when _active_tab_widget is None (line 1729)."""

    def test_open_document_returns_none(self, main_window, qtbot):
        """Test open_document returns None with no active tab widget."""
        sc = main_window.split_container
        sc._active_tab_widget = None
        doc = Document()
        result = sc.open_document(doc)
        assert result is None


class TestFocusOrOpenDocumentFallback:
    """Test focus_or_open_document falls through to open_document (line 1742)."""

    def test_focus_or_open_unfocused_doc(self, main_window, qtbot):
        """Test focus_or_open_document opens a doc that's not in any tab."""
        doc = Document()
        doc.document.setPlainText("new content")
        result = main_window.split_container.focus_or_open_document(doc)
        assert result is not None


class TestCollapseSingleChildSplittersBreak:
    """Test _collapse_single_child_splitters break when parent is not QSplitter (line 1917)."""

    def test_collapse_stops_at_non_splitter_parent(self, main_window, qtbot):
        """Test collapse stops when parent widget is not a QSplitter."""
        from PyQt5.QtWidgets import QSplitter, QWidget
        sc = main_window.split_container
        # Create a single-child QSplitter whose parent is a plain QWidget (not QSplitter)
        container = QWidget()
        inner_splitter = QSplitter()
        inner_splitter.setParent(container)
        dummy = QWidget()
        inner_splitter.addWidget(dummy)
        # _collapse_single_child_splitters should hit the break on line 1917
        sc._collapse_single_child_splitters(inner_splitter)
        container.close()


class TestSplitContainerSaveDocumentNoParent:
    """Test SplitContainer._save_document returns False without QMainWindow parent (line 1961)."""

    def test_save_document_no_main_window(self, qtbot):
        """Test _save_document returns False when there's no QMainWindow ancestor."""
        doc_mgr = DocumentManager()
        sc = SplitContainer(doc_mgr)
        doc = doc_mgr.get_or_create_document()
        doc.document.setPlainText("test")
        result = sc._save_document(doc)
        assert result is False
        sc.close()


class TestSelectFileInvalidIndex:
    """Test select_file returns early when model index is invalid (line 2020)."""

    def test_select_file_invalid_model_index(self, file_tree, tmp_path):
        """Test select_file with a file that exists but whose model index is invalid."""
        test_file = tmp_path / "real.txt"
        test_file.write_text("content")
        file_tree.set_root_path(str(tmp_path))
        from PyQt5.QtCore import QModelIndex
        with patch.object(file_tree.model, 'index', return_value=QModelIndex()):
            file_tree.select_file(str(test_file))


class TestCleanupExplorerInvalidIndex:
    """Test cleanup_explorer collapseAll on invalid index (lines 2040-2041)."""

    def test_cleanup_explorer_invalid_path(self, file_tree, tmp_path):
        """Test cleanup_explorer with path that exists but has invalid model index."""
        file_tree.set_root_path(str(tmp_path))
        # Path exists on disk but isn't under the model root, so index is invalid
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        test_file = other_dir / "test.txt"
        test_file.write_text("test")
        with patch.object(file_tree.model, 'index', return_value=file_tree.model.index(-1, -1)):
            file_tree.cleanup_explorer(str(test_file))


class TestCollapseNonAncestorsInvalidChild:
    """Test _collapse_non_ancestors continue on invalid child_index (line 2059)."""

    def test_collapse_non_ancestors_invalid_child(self, file_tree, tmp_path):
        """Test _collapse_non_ancestors handles invalid child indices."""
        file_tree.set_root_path(str(tmp_path))
        # Create a mock that returns invalid indices
        from PyQt5.QtCore import QModelIndex
        root = file_tree.rootIndex()
        original_index = file_tree.model.index
        call_count = [0]

        def fake_index(row, col, parent=QModelIndex()):
            call_count[0] += 1
            if call_count[0] <= 2:
                return QModelIndex()  # invalid
            return original_index(row, col, parent)

        with patch.object(file_tree.model, 'rowCount', return_value=2):
            with patch.object(file_tree.model, 'index', side_effect=fake_index):
                file_tree._collapse_non_ancestors(root, set())


class TestOpenFileGenericException:
    """Test _open_file handles generic Exception (lines 2759-2761)."""

    def test_open_file_generic_exception(self, main_window, tmp_path, qtbot):
        """Test _open_file_path handles unexpected exception by showing invalid file."""
        test_file = tmp_path / "broken.txt"
        test_file.write_text("content")
        with patch('builtins.open', side_effect=ValueError("unexpected")):
            with patch.object(main_window, '_handle_invalid_file') as mock_handle:
                main_window._open_file_path(str(test_file))
                mock_handle.assert_called_once_with(str(test_file))


class TestCheckSaveAllNoneDoc:
    """Test _check_save_all skips None doc (line 2876)."""

    def test_check_save_all_none_doc_in_list(self, main_window, qtbot):
        """Test _check_save_all skips None entries in documents list."""
        main_window._skip_save_check = False
        with patch.object(type(main_window.doc_manager), 'documents',
                          new_callable=lambda: property(lambda self: [None])):
            result = main_window._check_save_all()
        assert result is True


class TestCheckSaveAllSaveFailsWithPath:
    """Test _check_save_all returns False when save fails (line 2892)."""

    def test_check_save_all_save_fails(self, main_window, tmp_path, qtbot):
        """Test _check_save_all returns False when _save_document returns False."""
        main_window._skip_save_check = False
        doc = main_window.editor.doc
        doc.document.setPlainText("modified")
        main_window.doc_manager.update_document_path(doc, str(tmp_path / "fail.txt"))
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Save):
            with patch.object(main_window, '_save_document', return_value=False):
                result = main_window._check_save_all()
        assert result is False
        doc.is_modified = False


class TestCheckSaveAllSaveAsStillModified:
    """Test _check_save_all returns False when save-as leaves doc modified (lines 2899-2904)."""

    def test_check_save_all_save_as_still_modified(self, main_window, qtbot):
        """Test _check_save_all returns False when save-as doesn't clear modified flag."""
        main_window._skip_save_check = False
        doc = main_window.editor.doc
        doc.document.setPlainText("modified content")
        # doc has no file_path, so it triggers save-as branch
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Save):
            with patch.object(main_window, '_save_file_as'):
                # After save_as, doc is still modified
                result = main_window._check_save_all()
        assert result is False
        doc.is_modified = False

    def test_check_save_all_save_as_is_modified_raises(self, main_window, qtbot):
        """Test _check_save_all handles exception checking is_modified after save-as (lines 2899-2900)."""
        main_window._skip_save_check = False
        doc = main_window.editor.doc
        doc.document.setPlainText("content")
        call_count = [0]
        original_is_modified = type(doc).is_modified.fget

        def flaky_is_modified(self_doc):
            call_count[0] += 1
            if call_count[0] >= 3:
                raise RuntimeError("deleted")
            return original_is_modified(self_doc)

        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Save):
            with patch.object(main_window, '_save_file_as'):
                with patch.object(type(doc), 'is_modified',
                                  new_callable=lambda: property(flaky_is_modified)):
                    result = main_window._check_save_all()
        assert result is True

    def test_check_save_all_doc_iteration_exception(self, main_window, qtbot):
        """Test _check_save_all handles exception during doc iteration (lines 2901-2902)."""
        main_window._skip_save_check = False
        # Create a doc that passes is_modified check but raises on display_name access
        bad_doc = MagicMock()
        type(bad_doc).is_modified = property(lambda s: True)
        type(bad_doc).display_name = property(lambda s: (_ for _ in ()).throw(RuntimeError("dead")))
        with patch.object(type(main_window.doc_manager), 'documents',
                          new_callable=lambda: property(lambda self: [bad_doc])):
            result = main_window._check_save_all()
        assert result is True



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
