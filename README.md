# Text Editor

A cross-platform text editor built with PyQt5 featuring syntax highlighting, auto-indentation, and file management.

# R1
To begin I made a very specific request for what I want as well as clearly displaying what I don't want. I wanted to have the AI build as much as possible in one request. This was decided because my experience has shown that the more layers added onto the AI, the more likely it is to put itself in a hole. If I didn't like how it approached the initial query, I would steer course and try again. Fortunately, it nailed it. The design was simple and user friendly for the most part, and simple functionality worked. I wanted to see if the AI could debug itself so I had it set up simple tests with pytest. Initially, the coverage was limited however I ensured it was modified to cover as much of the codebase as possible. I noticed some sytax features it naturally built, so I have it expand those features for different languages. I tested unique cases with nesting and keywords, and thus far I have not discovered any issues. It has struggled to understand some user inconveniences. For example, opening and closing files repeatedly inserts pop ups which ask to save the existing file. This isn't an "error" so it has a hard time understanding what I want. All in all, I am very impressed with its ability to perform complex tasks, but as expected, it seems to struggle with layering on data bases, and human centered inconveniences.

# R2
    What about the feature works and doesn't work
The opening and saving of files was a feature that the AI struggled with. When a file was saved, if the user did anything other than instantly open a new file, the text editor would ask to save it again. This would be a frustrating bug for a user because upon doing almost any action to open or close the file, it would ask to save first, even if it was already saved. It has been fixed to only ask to save if leaving an unsaved file.

    Brag about the feature a little bit -- tell us something about how you approached it, how you solved it, or some interesting bit of your software architecture.
In order to approach this problem, I tested every possible case in which I would be leaving a file (opening a new or saved file, closing the program, canceling and open before opening a file, ...) and listed the results. I then input very specific example cases of when this issue would arrise before detailing how I want the text editor to respond. Interestingly, Qt has a saved/edited file feature that the AI didn't consider until I specified my experience. The AI incorporated this and all the error cases have been resolved.

    How does this feature fit into the modular structure of your editor?
This feature fit really well into the structure of the editor because it was already built into Qt. This means that the handling if this feature is treated fairly independently of the rest of the editor.

    For the parts that work, explain how you know that they work as intended. other words, explain what kind of tests you are using to validate the functionality of your editor.
I tried extensive cases manually to try and reproduce the error in ways that even a human would likely never encounter. For example, I tested many combinations of requests (open/save/undo/redo/new...) as well as canceling the requests or modifying the content. Thus far, I have not found any similar user inconveniences.

# R3
    What about the feature works and doesn't work.
I will choose to discuss the file tree explorer with collapsable folders. Everything works as intended. I did have an issue with the file explorer being visually glitchy due to a feature where it would close unused filepaths. I also noticed an issue where, upon saving a new file, the file explorer would not automatically open to that files location. These are both issues that cause no logical issues, however they would prove to be frustrating for a human user.

    Brag about the feature a little bit -- tell us something about how you approached it, how you solved it, or some interesting bit of your software architecture.
This weeks work was mostly ensuring user friendly interactions, such as how incompatable files are handled, appear seamless rather than irritating. For the file tree explorer, there were a few inconveniences with how it functioned. Initially I made the design choice to close filepaths that aren't in use. This makes the file explorer look clean, however because I did not have the multiple tab feature, I realized this could prove to be bothersome for people switching between multiple files. I liked the idea, however, so I repurposed it to be an option. The user can now chose to close unused filepaths with one click, rather than having to manually close each. This can help a user stay organized in projects or multitasking.

    How does this feature fit into the modular structure of your editor?
Although I realized the initial design choice was not very thoughtful, I was able to turn direction and reuse that feature as a smaller feature some users may find useful. This fit very smoothly into the modular structure of the editor because it only required reworking a function that already existed in the editor. As a counter example (and side not), I tried adding in syntax error highlighting to my text editor this week. This is a huge task and I soon decided to back out because it did not at all fit into the modular structure of the editor. The deeper I dove into this challenge the more I realized the text editor would have needed to be built with this in mind, it was too big of an afterthough to add in late. I'm sure, had I included this feature in the initial prompt, it would have had no problem achieving this.
    
    For the parts that work, explain how you know that they work as intended. other words, explain what kind of tests you are using to validate the functionality of your editor.
On top of the AI built tests of the file explorer handling, I have performed extensive manual tests on the use of the explorer. I tried opening and saving files to different locations to ensure the correct location was opened in the file tree explorer. I also tried opening and closing both empty directories and exceptionally large directories. I jumped through countless subdirectories and tries to trick the file explorer by opening hiden files (.* files are hidden - it only shows .* files the user created in that session). All have succeeded.

## Features

### 1. Automatic Indentation and Bracket/Quote Matching

- **Smart auto-indentation**: Automatically indents new lines based on the previous line's indentation level
- **Language-aware indentation**: Recognizes indent triggers (e.g., `:` in Python, `{` in C/JavaScript) and increases indent accordingly
- **Bracket auto-completion**: Typing `(`, `[`, or `{` automatically inserts the matching closing bracket
- **Quote auto-completion**: Typing `"`, `'`, or `` ` `` automatically inserts a matching quote
- **Smart cursor movement**: Cursor skips over auto-inserted closing brackets/quotes when typed
- **Paired deletion**: Backspace removes both the opening and closing bracket/quote when cursor is between them

### 2. Multi-Language Syntax Highlighting

Supports syntax highlighting for 20+ languages using static language definitions:

- **Programming**: Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Rust, Ruby, PHP
- **Web**: HTML, CSS, JSON, XML
- **Data/Config**: SQL, YAML, TOML, Markdown
- **Scripting**: Bash/Shell

Highlighting includes:
- Keywords and built-in functions
- Strings and numbers
- Comments (single-line and multi-line)
- Function calls and decorators
- Preprocessor directives (C/C++)
- Dark and light theme support

### 3. Find and Replace

- **Find Next/Previous**: Navigate through all matches in the document
- **Replace**: Replace the current match with specified text
- **Replace All**: Replace all occurrences in one operation
- **Case Sensitivity**: Toggle case-sensitive searching
- **Wrap-around search**: Automatically continues from the beginning/end of the document

### 4. File Tree Explorer

- **Collapsible folders**: Expand and collapse directories with animated transitions
- **File navigation**: Double-click files to open them in the editor
- **Auto-expand**: Opening a file automatically expands its parent directories
- **Cleanup function**: Collapse all directories except the current file's path
- **Open folder**: Set any directory as the root of the file tree
- **Toggle visibility**: Show/hide the file tree panel

## Getting Started

### Prerequisites

- Python 3.6+
- PyQt5

### Installation

```bash
# Install dependencies
pip install PyQt5

# Or using the virtual environment
source venv/bin/activate
pip install PyQt5
```

### Running the Text Editor

```bash
python text_editor.py
```

Or with the virtual environment:

```bash
source venv/bin/activate
python text_editor.py
```

## Testing

### Running Tests

```bash
# Run all tests with pytest
pytest testing/test_text_editor.py -v

# Run tests with timeout (30 seconds per test)
pytest testing/test_text_editor.py -v --timeout=30

# Run with coverage
python testing/run_coverage.py
```

### Test Coverage

```bash
cd testing
python run_coverage.py
```

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| **File Operations** | |
| New File | `Ctrl+N` |
| Open File | `Ctrl+O` |
| Open Folder | `Ctrl+Shift+O` |
| Save | `Ctrl+S` |
| Save As | `Ctrl+Shift+S` |
| Exit | `Ctrl+Q` |
| **Edit Operations** | |
| Undo | `Ctrl+Z` |
| Redo | `Ctrl+Y` / `Ctrl+Shift+Z` |
| Cut | `Ctrl+X` |
| Copy | `Ctrl+C` |
| Paste | `Ctrl+V` |
| Select All | `Ctrl+A` |
| Find/Replace | `Ctrl+F` |
| **View Operations** | |
| Toggle File Tree | `Ctrl+B` |
| Toggle Theme (Light/Dark) | `Ctrl+Shift+T` |
| **Editor Operations** | |
| Indent Selection | `Tab` |
| Unindent Selection | `Shift+Tab` |
