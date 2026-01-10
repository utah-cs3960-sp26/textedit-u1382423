"""
Tests for the Text Editor application using pytest and pytest-qt.
Run with: QT_QPA_PLATFORM=offscreen pytest test_text_editor.py -v
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QDir, QSize, QRect
from PyQt5.QtGui import QTextCursor, QKeyEvent

from text_editor import (
    CodeEditor, FileTreeView, TextEditor, LineNumberArea, main,
    SyntaxHighlighter, LANGUAGE_DEFINITIONS, get_language_for_file
)


@pytest.fixture
def editor(qtbot):
    """Create a CodeEditor instance."""
    ed = CodeEditor()
    qtbot.addWidget(ed)
    ed.show()
    qtbot.waitExposed(ed)
    return ed


@pytest.fixture
def file_tree(qtbot):
    """Create a FileTreeView instance."""
    tree = FileTreeView()
    qtbot.addWidget(tree)
    tree.show()
    qtbot.waitExposed(tree)
    return tree


@pytest.fixture
def main_window(qtbot):
    """Create a TextEditor main window instance."""
    window = TextEditor()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


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
        assert file_tree.model.filePath(root_index) == str(tmp_path)

    def test_get_file_path(self, file_tree, temp_file):
        """Test getting file path from index."""
        dir_path = os.path.dirname(temp_file)
        file_tree.set_root_path(dir_path)
        
        index = file_tree.model.index(temp_file)
        path = file_tree.get_file_path(index)
        assert path == temp_file

    def test_is_directory(self, file_tree, tmp_path):
        """Test directory check."""
        file_tree.set_root_path(str(tmp_path))
        index = file_tree.model.index(str(tmp_path))
        assert file_tree.is_directory(index) is True

    def test_is_not_directory(self, file_tree, temp_file):
        """Test file is not directory."""
        index = file_tree.model.index(temp_file)
        assert file_tree.is_directory(index) is False


class TestTextEditorMainWindow:
    """Tests for the main TextEditor window."""

    def test_window_initialization(self, main_window):
        """Test main window initializes correctly."""
        assert main_window is not None
        assert main_window.windowTitle() == "Text Editor"

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
        """Test new file action."""
        qtbot.keyClicks(main_window.editor, "Some content")
        main_window.editor.is_modified = False
        main_window._new_file()
        
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
        main_window.editor.current_file = file_path
        main_window._save_file()
        
        with open(file_path, 'r') as f:
            content = f.read()
        assert content == "Test content"

    def test_toggle_file_tree(self, main_window):
        """Test toggling file tree visibility."""
        initial_visible = main_window.file_tree.isVisible()
        main_window._toggle_file_tree()
        assert main_window.file_tree.isVisible() != initial_visible
        main_window._toggle_file_tree()
        assert main_window.file_tree.isVisible() == initial_visible

    def test_check_save_unmodified(self, main_window):
        """Test check save with unmodified document."""
        main_window.editor.is_modified = False
        assert main_window._check_save() is True

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
        assert path == str(tmp_path)

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
        assert main_window.editor.current_file == temp_file

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
        main_window.editor.is_modified = True
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Discard):
            result = main_window._check_save()
            assert result is True
        main_window.editor.is_modified = False

    def test_check_save_cancel(self, main_window, qtbot):
        """Test check save with cancel option."""
        main_window.editor.is_modified = True
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Cancel):
            result = main_window._check_save()
            assert result is False
        main_window.editor.is_modified = False

    def test_check_save_save_success(self, main_window, tmp_path, qtbot):
        """Test check save with save option."""
        file_path = str(tmp_path / "save_test.txt")
        main_window.editor.current_file = file_path
        main_window.editor.is_modified = True
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Save):
            result = main_window._check_save()
            assert result is True
        main_window.editor.is_modified = False


class TestFindDialog:
    """Tests for find dialog functionality."""

    def test_show_find_dialog_found(self, main_window, qtbot):
        """Test find dialog when text is found."""
        main_window.editor.setPlainText("Hello world, hello again")
        with patch('text_editor.QInputDialog.getText', return_value=("hello", True)):
            main_window._show_find_dialog()
            cursor = main_window.editor.textCursor()
            assert cursor.hasSelection()

    def test_show_find_dialog_not_found(self, main_window, qtbot):
        """Test find dialog when text is not found."""
        main_window.editor.setPlainText("Hello world")
        with patch('text_editor.QInputDialog.getText', return_value=("xyz", True)):
            with patch('text_editor.QMessageBox.information'):
                main_window._show_find_dialog()

    def test_show_find_dialog_cancelled(self, main_window, qtbot):
        """Test find dialog when cancelled."""
        main_window.editor.setPlainText("Hello world")
        with patch('text_editor.QInputDialog.getText', return_value=("", False)):
            main_window._show_find_dialog()

    def test_find_wraps_around(self, main_window, qtbot):
        """Test find wraps to beginning if not found from cursor."""
        main_window.editor.setPlainText("Hello world")
        cursor = main_window.editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        main_window.editor.setTextCursor(cursor)
        with patch('text_editor.QInputDialog.getText', return_value=("Hello", True)):
            main_window._show_find_dialog()
            cursor = main_window.editor.textCursor()
            assert cursor.hasSelection()


class TestCloseEvent:
    """Tests for window close event."""

    def test_close_event_unmodified(self, main_window):
        """Test close event with unmodified document."""
        main_window.editor.is_modified = False
        event = MagicMock()
        main_window.closeEvent(event)
        event.accept.assert_called_once()

    def test_close_event_modified_cancel(self, main_window):
        """Test close event with modified document and cancel."""
        main_window.editor.is_modified = True
        event = MagicMock()
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Cancel):
            main_window.closeEvent(event)
            event.ignore.assert_called_once()
        main_window.editor.is_modified = False

    def test_close_event_modified_discard(self, main_window):
        """Test close event with modified document and discard."""
        main_window.editor.is_modified = True
        event = MagicMock()
        with patch('text_editor.QMessageBox.question', return_value=QMessageBox.Discard):
            main_window.closeEvent(event)
            event.accept.assert_called_once()
        main_window.editor.is_modified = False


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
            assert main_window.file_tree.model.filePath(root_index) == str(tmp_path)

    def test_open_folder_dialog_cancelled(self, main_window):
        """Test _open_folder when dialog is cancelled."""
        initial_root = main_window.file_tree.rootIndex()
        with patch('text_editor.QFileDialog.getExistingDirectory', return_value=''):
            main_window._open_folder()

    def test_save_file_as_dialog(self, main_window, tmp_path, qtbot):
        """Test _save_file_as method with mocked dialog."""
        file_path = str(tmp_path / "new_save.txt")
        qtbot.keyClicks(main_window.editor, "Content to save")
        with patch('text_editor.QFileDialog.getSaveFileName', return_value=(file_path, 'All Files (*)')):
            main_window._save_file_as()
            assert main_window.editor.current_file == file_path
            assert os.path.exists(file_path)
        main_window.editor.is_modified = False

    def test_save_file_as_dialog_cancelled(self, main_window, qtbot):
        """Test _save_file_as when dialog is cancelled."""
        qtbot.keyClicks(main_window.editor, "Content")
        with patch('text_editor.QFileDialog.getSaveFileName', return_value=('', '')):
            main_window._save_file_as()
            assert main_window.editor.current_file is None
        main_window.editor.is_modified = False


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
