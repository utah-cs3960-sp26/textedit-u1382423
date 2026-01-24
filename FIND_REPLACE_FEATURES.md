# Find and Replace Features

## Overview
The text editor now includes a comprehensive Find and Replace dialog that allows users to search for and replace text with multiple options.

## Features

### Find Operations
- **Find Next**: Searches forward from the current cursor position. Wraps around to the beginning of the document if the end is reached.
- **Find Previous**: Searches backward from the current cursor position. Wraps around to the end of the document if the beginning is reached.
- **Case Sensitive Toggle**: Checkbox to enable/disable case-sensitive searching. When unchecked, "hello", "Hello", and "HELLO" are treated as identical.

### Replace Operations
- **Replace Current**: Replaces the currently selected/found text with the replacement text, then automatically finds the next occurrence.
- **Replace All**: Replaces all instances of the search text with the replacement text throughout the document. Shows a status message indicating how many replacements were made.

### User Interface
- Find and Replace text input fields
- Case Sensitive checkbox
- Five action buttons:
  - Find Next
  - Find Previous
  - Replace
  - Replace All
  - Close
- Status label displaying operation results:
  - "Text found" - when search succeeds
  - "Text not found" - when no match is found
  - "Please enter search text" - when search field is empty
  - "Replaced X instance(s)" - after replace all operation
  - "No text selected to replace" - when trying to replace without an active selection

## Technical Implementation

### Class: FindReplaceDialog
Located in `text_editor.py`, this dialog:
- Extends `QDialog` for modal behavior
- Uses `QTextDocument.find()` with proper flag handling
- Manages cursor positions for both forward and backward searches
- Handles document modifications safely during replace operations

### Search Algorithm
The search algorithm:
1. Creates a new cursor at the current position
2. Uses `QTextDocument.find()` with appropriate flags (case sensitivity, backward search)
3. Returns a cursor with the found text selected
4. Handles wraparound by moving cursor to Start/End when no more matches found

### Replace All Algorithm
The replace all operation:
1. Starts from position 0 in the document
2. Iteratively finds occurrences using `document.find()`
3. For each match:
   - Removes the selected text
   - Inserts the replacement text
   - Advances position past the replacement
4. Counts total replacements and displays result

## Keyboard Shortcuts (via Menu)
Access the Find and Replace dialog through:
- **Menu**: Edit → Find and Replace (or Ctrl+H)

## Usage Examples

### Example 1: Find and Replace a Single Word
1. Open Find and Replace dialog (Ctrl+H)
2. Type "old" in Find field
3. Type "new" in Replace field
4. Click "Replace All" to replace all instances

### Example 2: Case-Sensitive Search
1. Type "myFunction" in Find field
2. Check "Case Sensitive" checkbox
3. Click "Find Next" to find only exact matches (not "myfunction" or "MyFunction")

### Example 3: Navigate Multiple Occurrences
1. Type search term in Find field
2. Click "Find Next" repeatedly to step through each occurrence
3. Or click "Find Previous" to go backwards

### Example 4: Replace and Continue
1. Type search and replace terms
2. Click "Replace" to replace current occurrence and move to next
3. Repeat step 2 for selective replacements

## Edge Cases Handled
- ✅ Empty search text validation
- ✅ Search wraparound at document boundaries
- ✅ Case-sensitive and case-insensitive searching
- ✅ Replacing text with longer/shorter text
- ✅ Replace all works independently of cursor position
- ✅ Multiple sequential replace all operations
- ✅ Replace operations on documents with existing replacements

## Testing
Comprehensive test suite includes 12 test cases covering:
- Basic find/previous functionality
- Text not found scenarios
- Empty search validation
- Case-sensitive and insensitive searches
- Replace current selection
- Replace all with counters
- Wraparound behavior
- Multiple sequential operations
