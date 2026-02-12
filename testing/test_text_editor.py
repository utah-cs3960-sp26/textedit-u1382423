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
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QDir, QSize, QRect
from PyQt5.QtGui import QTextCursor, QKeyEvent

from text_editor import (
    CodeEditor, FileTreeView, TextEditor, LineNumberArea, main,
    SyntaxHighlighter, LANGUAGE_DEFINITIONS, get_language_for_file,
    FindReplaceDialog, Document, DocumentManager, EditorPane, EditorTabWidget,
    SplitContainer
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
    window.editor.is_modified = False
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
        """Test opening incompatible file shows striped overlay."""
        # Need to show window for visibility tests to work
        main_window.show()
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
        """Test splitting down then right creates top-level + nested layout."""
        from PyQt5.QtWidgets import QSplitter
        main_window._split_down()
        assert main_window.split_container._total_leaf_count() == 2
        main_window._split_right()
        assert main_window.split_container._total_leaf_count() == 3
        assert main_window.split_container.count() == 2
        assert isinstance(main_window.split_container.widget(0), QSplitter)
        assert isinstance(main_window.split_container.widget(1), EditorTabWidget)

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

    def test_nested_pane_never_creates_double_nesting(self, main_window, qtbot):
        """Test that splitting from a nested pane never creates a 2-deep nesting."""
        from PyQt5.QtWidgets import QSplitter
        main_window._split_down()
        active = main_window.split_container.active_tab_widget()
        assert isinstance(active.parentWidget(), QSplitter)
        assert active.parentWidget() is not main_window.split_container
        main_window._split_down()
        assert main_window.split_container._total_leaf_count() == 3
        main_window._split_right()
        assert main_window.split_container._total_leaf_count() == 4
        for i in range(main_window.split_container.count()):
            child = main_window.split_container.widget(i)
            if isinstance(child, QSplitter):
                for j in range(child.count()):
                    assert isinstance(child.widget(j), EditorTabWidget)

    def test_nested_pane_can_split_same_as_top_level(self, main_window, qtbot):
        """Test that a pane inside a nested split can still split in the top-level direction (adds at top level)."""
        main_window._split_down()
        assert main_window.split_container._total_leaf_count() == 2
        result = main_window.split_container.split(Qt.Horizontal)
        assert result is not None
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
