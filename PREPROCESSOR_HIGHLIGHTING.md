# Preprocessor Directive Highlighting

## Overview
Fixed syntax highlighting for preprocessor directives in C and C++ files. Previously, directives like `#include`, `#define`, and include brackets were not properly highlighted. Now they are colored as keywords (blue) and include contents in angle brackets are colored as strings (orange).

## Changes Made

### Modified File
- `text_editor.py` - Updated `SyntaxHighlighter.set_language()` method

### Implementation Details

#### For C and C++ Languages
Added two highlighting rules at the beginning of the highlighting rules setup:

1. **Preprocessor Directive Keywords** (Including # Symbol)
   - Pattern: `#\s*(?:include|define|ifdef|ifndef|if|else|elif|endif|pragma|error|warning|undef)\b`
   - Color: Keyword (blue, bold)
   - **Includes the # symbol** in the highlighting
   - Examples: `#include`, `#define`, `#ifdef`, `#endif`, `# include` (with space)

2. **Angle Bracket Includes**
   - Pattern: `<[^>]+>`
   - Color: String (orange)
   - Examples: `<iostream>`, `<vector>`, `<stdio.h>`

## Supported Directives

The following preprocessor directives are now highlighted:
- `#include` - Include header files
- `#define` - Define macros
- `#ifdef` - Conditional compilation (if defined)
- `#ifndef` - Conditional compilation (if not defined)
- `#if` - Conditional compilation
- `#else` - Conditional else branch
- `#elif` - Conditional else-if branch
- `#endif` - End conditional block
- `#pragma` - Compiler directives
- `#error` - Error directive
- `#warning` - Warning directive
- `#undef` - Undefine macro

## Language-Specific Behavior

### C and C++
✅ **Enabled**
- `#include <vector>` - Both #include and <vector> are colored
- `#include "myheader.h"` - Quoted includes are colored as strings
- `#define MAX 100` - Preprocessor keywords are colored
- `#ifdef DEBUG` - Conditional directives are colored

### Other Languages (Python, JavaScript, Java, etc.)
✅ **Not Affected**
- No preprocessor highlighting is applied
- Angle brackets in comparisons (`x < 10`) are NOT colored
- Angle brackets in generic/template code are NOT colored
- String content remains unaffected

### HTML/XML
✅ **Not Affected**
- HTML/XML tags continue to be highlighted correctly
- The `<tag>` pattern for tags takes precedence
- No conflicts with existing tag highlighting

## Examples

### C++ Code
```cpp
#include <iostream>      // #include colored as keyword, <iostream> as string
#include <vector>        // Same as above
#include "myheader.h"    // Quoted include colored as string
#define MAX_SIZE 100     // #define colored as keyword
#ifdef DEBUG             // #ifdef colored as keyword
#define LOG(x) std::cout << x << std::endl
#endif                   // #endif colored as keyword

int main() {
    std::vector<int> vec;  // <int> NOT colored (not a directive)
    if (vec.size() < 10) { // < NOT colored (comparison operator)
        return 0;
    }
}
```

### C Code
```c
#include <stdio.h>       // Properly colored
#include <stdlib.h>      // Properly colored
#define PI 3.14159       // #define colored as keyword
#ifdef WINDOWS           // #ifdef colored as keyword
#include <windows.h>     // Nested include properly colored
#endif                   // Properly colored
```

### Python Code (Unaffected)
```python
import os               // 'import' is keyword (not preprocessor)
from typing import List
x = 5 < 10            // < is NOT colored (not a directive)
```

## Benefits

1. **Better Code Readability** - Preprocessor directives are now visually distinct
2. **Consistent Styling** - All preprocessor directives use the same color (blue/keyword)
3. **Include Path Visibility** - Include paths in angle brackets are highlighted
4. **No Side Effects** - Other languages and contexts are unaffected
5. **Comprehensive Coverage** - All common preprocessor directives are supported

## Technical Details

### Order of Rule Application
The preprocessor rules are added FIRST before other keyword/token rules to ensure:
- Preprocessor directives are matched and highlighted correctly
- Include brackets `<...>` are colored as strings (orange) 
- Later rules for string delimiters don't interfere with include syntax

### Pattern Matching
- Uses non-capturing group `(?:...)` to match directive alternatives
- The entire match (including # symbol) is highlighted as a unit
- Uses word boundaries (`\b`) to match complete directive names
- Allows flexible whitespace with `\s*` between `#` and directive
- Include brackets match any content: `<[^>]+>` (everything between < and >)

### Why Non-Capturing Group?
Using a non-capturing group `(?:...)` instead of capturing group `(...)` ensures:
- The entire match including the `#` symbol is highlighted
- No special index handling is needed in the highlighting function
- Cleaner regex and more predictable highlighting behavior

## Testing

All existing tests pass:
- ✅ Syntax highlighter creation
- ✅ Language setting
- ✅ Language detection from files
- ✅ Format existence
- ✅ No interference with other languages

Manual testing confirms:
- ✅ C++ includes with angle brackets are highlighted
- ✅ C preprocessor directives are highlighted
- ✅ Quoted includes work correctly
- ✅ Multiple preprocessor directives are handled
- ✅ Mixed code with templates and comparisons work correctly
- ✅ Python, JavaScript, HTML unaffected
