import random
import os

# List of available man files
MAN_FILES = [
    "man-unix.txt",
    "man-python.txt",
    "man-sed.txt",
    "man-grep.txt",
    "man-bash.txt",
    "man-ffmpeg.txt"
]

# Cache for loaded man file contents
MAN_FILE_CONTENTS = {}

def load_man_file(filename):
    """Load a man file from the man_files directory."""
    if filename in MAN_FILE_CONTENTS:
        return MAN_FILE_CONTENTS[filename]

    try:
        # Try first directly in man_files
        file_path = os.path.join("man_files", filename + ".txt")

        # If the file doesn't exist, try without .txt extension
        if not os.path.exists(file_path):
            file_path = os.path.join("man_files", filename)

        # If still doesn't exist, try old location for backward compatibility
        if not os.path.exists(file_path):
            file_path = os.path.join("../workload-generator/long-contexts", filename)

        print(f"Attempting to load from: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Cache the content
        MAN_FILE_CONTENTS[filename] = content
        print(f"Successfully loaded {filename} ({len(content)} bytes)")
        return content
    except Exception as e:
        print(f"Failed to load man file {filename}: {e}")
        # Return a short message instead of error to avoid breaking the demo
        return f"Sample documentation for {filename}"

def get_doc_chunk(doc_content, chunk_size=500):
    """Get a coherent chunk of documentation."""
    if len(doc_content) <= chunk_size:
        return doc_content

    # Split by paragraphs
    paragraphs = doc_content.split("\n\n")
    chunk = ""

    # Start from a random paragraph
    start_idx = random.randint(0, max(0, len(paragraphs) - 5))

    # Add paragraphs until we reach our target size
    for i in range(start_idx, len(paragraphs)):
        if len(chunk) + len(paragraphs[i]) + 2 <= chunk_size:
            chunk += paragraphs[i] + "\n\n"
        else:
            break

    return chunk.strip()

def generate_question(doc1, doc2, question_id):
    """Generate a question about the documentation."""
    templates = [
        "Question #{}: I don't fully understand, can you re-explain the key concepts in the {} documentation and also explain the {} documentation in great detail?",

        "Question #{}: Can you provide a comprehensive explanation of how {} works based on the documentation? Also, I'd like to understand the relationship between {} and {}.",

        "Question #{}: I'm trying to understand the advanced features described in the {} manual. Could you analyze and explain the key sections in detail? Additionally, how might these concepts relate to what's described in the {} documentation?",

        "Question #{}: What are the most important commands or functions in the {} documentation? Also, how do they compare to similar functionality in {}?",

        "Question #{}: The {} documentation seems complex. Can you break down the most important parts and explain them in detail? I'm also curious how these concepts might apply when working with {} tools."
    ]

    template = random.choice(templates)
    return template.format(
        question_id,
        doc1,
        doc2,
        doc1  # For templates that need a third parameter
    )

def generate_system_response(doc1, doc2):
    """Generate a simulated system response about the documentation."""
    # This is a simplified version to create believable system responses
    response_templates = [
        f"The {doc1} documentation primarily covers tools for {get_doc_topic(doc1)}. It includes commands like {get_random_commands(doc1, 3)}. When comparing to {doc2}, which focuses on {get_doc_topic(doc2)}, you'll notice several differences in approach...",

        f"In the {doc1} manual, you'll find comprehensive information about {get_doc_topic(doc1)}. Key concepts include {get_random_features(doc1, 2)}. The {doc2} documentation takes a different approach by focusing on {get_doc_topic(doc2)}...",

        f"Looking at {doc1}, the main functionality revolves around {get_doc_topic(doc1)}. Important sections cover {get_random_features(doc1, 2)}. When considering {doc2}, the documentation emphasizes {get_doc_topic(doc2)} instead...",

        f"The {doc1} system provides tools for {get_doc_topic(doc1)}, with commands such as {get_random_commands(doc1, 2)}. In contrast, {doc2} is designed for {get_doc_topic(doc2)} and offers different capabilities..."
    ]

    return random.choice(response_templates)

def get_doc_topic(doc_name):
    """Return a topic description based on the doc name."""
    topics = {
        "man-unix.txt": "operating system management and file operations",
        "man-python.txt": "programming in the Python language",
        "man-sed.txt": "stream editing and text transformation",
        "man-grep.txt": "pattern matching and text searching",
        "man-bash.txt": "shell scripting and command execution",
        "man-ffmpeg.txt": "multimedia processing and conversion",
        "man-gcc.txt": "C/C++ compilation and optimization"
    }
    return topics.get(doc_name, "specialized technical operations")

def get_random_commands(doc_name, count=2):
    """Return random command examples based on the doc name."""
    commands = {
        "man-unix.txt": ["ls", "cd", "cp", "mv", "chmod", "chown", "rm", "mkdir"],
        "man-python.txt": ["import", "def", "class", "print()", "open()", "with"],
        "man-sed.txt": ["s/pattern/replacement/", "d", "p", "i\\", "a\\", "c\\"],
        "man-grep.txt": ["grep pattern file", "grep -i", "grep -v", "grep -r"],
        "man-bash.txt": ["if", "for", "while", "case", "function", "export", "source"],
        "man-ffmpeg.txt": ["ffmpeg -i", "ffmpeg -c:v", "ffmpeg -f", "ffprobe"],
        "man-gcc.txt": ["gcc", "g++", "-Wall", "-O2", "-c", "-o"]
    }
    doc_commands = commands.get(doc_name, ["command1", "command2", "command3"])
    selected = random.sample(doc_commands, min(count, len(doc_commands)))
    return ", ".join(selected)

def get_random_features(doc_name, count=2):
    """Return random feature descriptions based on the doc name."""
    features = {
        "man-unix.txt": ["file permissions", "directory structures", "user management", "process control"],
        "man-python.txt": ["object-oriented programming", "list comprehensions", "exception handling", "module imports"],
        "man-sed.txt": ["regular expressions", "in-place editing", "address ranges", "hold space"],
        "man-grep.txt": ["regular expression patterns", "context lines", "recursive search", "inverted matching"],
        "man-bash.txt": ["variable expansion", "control structures", "function definitions", "command substitution"],
        "man-ffmpeg.txt": ["codec selection", "filtering options", "format conversion", "stream mapping"],
        "man-gcc.txt": ["optimization levels", "warning flags", "linking options", "preprocessor directives"]
    }
    doc_features = features.get(doc_name, ["feature1", "feature2", "feature3", "feature4"])
    selected = random.sample(doc_features, min(count, len(doc_features)))
    return " and ".join(selected)

def generate_conversation(num_rounds=3):
    """Generate a full conversation with documentation"""
    # First, randomly select 7 documentation files
    doc_files = os.listdir("man_files")

    # Always include all 7 documentation files
    doc1_file = "man_files/man-python.txt"
    doc2_file = "man_files/man-grep.txt"
    doc3_file = "man_files/man-sed.txt"
    doc4_file = "man_files/man-unix.txt"
    doc5_file = "man_files/man-bash.txt"
    doc6_file = "man_files/man-gcc.txt"
    doc7_file = "man_files/man-ffmpeg.txt"

    doc1_name = os.path.basename(doc1_file).replace(".txt", "")
    doc2_name = os.path.basename(doc2_file).replace(".txt", "")
    doc3_name = os.path.basename(doc3_file).replace(".txt", "")
    doc4_name = os.path.basename(doc4_file).replace(".txt", "")
    doc5_name = os.path.basename(doc5_file).replace(".txt", "")
    doc6_name = os.path.basename(doc6_file).replace(".txt", "")
    doc7_name = os.path.basename(doc7_file).replace(".txt", "")

    # Load the documentation content
    with open(doc1_file, "r") as f:
        doc1_content = f.read().strip()
    with open(doc2_file, "r") as f:
        doc2_content = f.read().strip()
    with open(doc3_file, "r") as f:
        doc3_content = f.read().strip()
    with open(doc4_file, "r") as f:
        doc4_content = f.read().strip()
    with open(doc5_file, "r") as f:
        doc5_content = f.read().strip()
    with open(doc6_file, "r") as f:
        doc6_content = f.read().strip()
    with open(doc7_file, "r") as f:
        doc7_content = f.read().strip()

    # Create a system message
    system_message = {
        "role": "system",
        "content": f"""You are a helpful assistant that answers questions about Unix command line tools and programming.
You have access to the following documentation:
1. {doc1_name}
2. {doc2_name}
3. {doc3_name}
4. {doc4_name}
5. {doc5_name}
6. {doc6_name}
7. {doc7_name}

Please provide accurate and helpful responses based on this documentation."""
    }

    # Create a conversation
    conversation = [system_message]

    # Generate rounds of question-answer pairs
    for i in range(num_rounds):
        question = generate_question_seven_docs(
            i+1, doc1_name, doc2_name, doc3_name, doc4_name, doc5_name, doc6_name, doc7_name
        )
        conversation.append({"role": "user", "content": question, "simulated": True})

        response = generate_system_response_seven_docs(
            question, doc1_name, doc2_name, doc3_name, doc4_name, doc5_name, doc6_name, doc7_name
        )
        conversation.append({"role": "assistant", "content": response, "simulated": True})

    return conversation, doc1_name, doc2_name, doc3_name, doc4_name, doc5_name, doc6_name, doc7_name

def generate_question_seven_docs(round_num, doc1, doc2, doc3, doc4, doc5, doc6, doc7):
    """Generate a question about the documentation"""
    templates = [
        f"Can you explain how to use the {doc1} module for string manipulation?",
        f"What's the difference between the {doc2} and {doc3} commands?",
        f"How can I combine {doc4} and {doc5} to process text files efficiently?",
        f"What are the most useful options for {doc6} when compiling C++ code?",
        f"How do I use {doc7} to convert video formats?",
        f"Can you show me examples of using {doc1} with {doc3}?",
        f"What are the performance considerations when using {doc4} with large files?",
        f"How can I use {doc2} with regular expressions to find patterns in text?",
        f"What's the best way to automate tasks using {doc5} scripts?",
        f"Can you explain the different compression options in {doc7}?",
        f"How do I optimize code compilation with {doc6}?",
        f"What are some advanced techniques for text processing with {doc3} and {doc2}?",
        f"How can I use {doc1} for file I/O operations?",
        f"What's the correct syntax for using {doc4} pipes with {doc5}?",
        f"How do I use {doc7} to extract audio from video files?",
        f"What are the most common flags used with {doc2} and {doc3}?"
    ]

    return random.choice(templates)

def generate_system_response_seven_docs(question, doc1, doc2, doc3, doc4, doc5, doc6, doc7):
    """Generate a simulated system response based on the question"""
    # Create a realistic-looking but synthetic response
    if doc1.lower() in question.lower():
        return f"""Based on the {doc1} documentation, you can perform string manipulation using various built-in methods.

For example:
- `str.strip()` removes whitespace from both ends of a string
- `str.split(sep)` splits a string into a list at the specified separator
- `str.replace(old, new)` replaces occurrences of 'old' with 'new'
- `str.format()` formats a string using specified values

Here's a practical example:
```python
text = "  Hello, World!  "
stripped = text.strip()  # "Hello, World!"
split_words = stripped.split(', ')  # ["Hello", "World!"]
replaced = stripped.replace('World', 'Python')  # "Hello, Python!"
```

The {doc1} documentation provides many more string manipulation functions that can be combined for complex text processing tasks.
"""

    elif doc2.lower() in question.lower() and doc3.lower() in question.lower():
        return f"""The main difference between {doc2} and {doc3} is their purpose and functionality:

{doc2}:
- Primarily used for searching text using patterns (regular expressions)
- Great for finding and printing lines that match specific patterns
- Can search through multiple files at once
- Options like -i (ignore case), -r (recursive), -v (invert match)

{doc3}:
- Primarily used for transforming text (search and replace)
- More powerful for complex text transformations
- Operates on streams of text line by line
- Uses a scripting language for transformations

While {doc2} is best for finding and filtering text, {doc3} excels at modifying and transforming text. They are often used together in pipelines where {doc2} finds relevant lines and {doc3} transforms them.

Example combining both:
```bash
grep -i "error" logfile.txt | sed 's/ERROR/WARNING/g'
```

This finds all lines containing "error" (case insensitive) and then replaces "ERROR" with "WARNING".
"""

    elif doc4.lower() in question.lower() or doc5.lower() in question.lower():
        return f"""To combine {doc4} and {doc5} for efficient text processing, you can use pipes, redirections, and script automation.

Here are some effective techniques:

1. Use pipes to chain commands:
```bash
cat large_file.txt | grep "pattern" | sort | uniq > results.txt
```

2. Use {doc5} loops for batch processing:
```bash
for file in *.txt; do
  grep "important" "$file" >> results.txt
done
```

3. Create reusable {doc5} functions:
```bash
process_file() {{
  grep "$1" "$2" | sort | uniq
}}

process_file "error" logfile.txt
```

4. Use {doc5} script with {doc4} tools for complex processing:
```bash
#!/bin/bash
while IFS= read -r line; do
  if [[ $line == *"critical"* ]]; then
    echo "$line" | awk '{{print $1, $2, $NF}}'
  fi
done < input.txt > output.txt
```

These techniques leverage the strengths of both {doc4} utilities (grep, awk, sed) and {doc5} scripting capabilities for powerful text processing workflows.
"""

    elif doc6.lower() in question.lower():
        return f"""When compiling C++ code with {doc6}, several options can significantly improve your workflow:

Most useful {doc6} options:

1. Optimization flags:
   - `-O0` to `-O3`: Different optimization levels (0=none, 3=maximum)
   - `-Ofast`: Enables all optimizations, even potentially unsafe ones

2. Warning and error flags:
   - `-Wall`: Enable all common warnings
   - `-Werror`: Treat warnings as errors
   - `-Wextra`: Enable extra warnings

3. Standard specification:
   - `-std=c++17`: Specify C++ standard (11, 14, 17, 20)

4. Debugging:
   - `-g`: Include debugging information
   - `-ggdb`: Include GDB-specific debugging info

5. Output control:
   - `-o file`: Specify output filename
   - `-c`: Compile without linking

Example command for development:
```bash
g++ -Wall -Wextra -std=c++17 -g -o myprogram main.cpp utils.cpp
```

Example for release build:
```bash
g++ -O3 -march=native -DNDEBUG -o myprogram main.cpp utils.cpp
```

The `-march=native` optimizes for your specific CPU architecture, which can provide significant performance improvements.
"""

    elif doc7.lower() in question.lower():
        return f"""To convert video formats using {doc7}, you can use its powerful conversion capabilities.

Basic video conversion:
```bash
ffmpeg -i input.mp4 output.avi
```

Convert with specific codec:
```bash
ffmpeg -i input.mp4 -c:v libx264 -c:a aac output.mkv
```

Change resolution:
```bash
ffmpeg -i input.mp4 -s 1280x720 output.mp4
```

Adjust bitrate:
```bash
ffmpeg -i input.mp4 -b:v 2M -b:a 128k output.mp4
```

Convert a sequence of images to video:
```bash
ffmpeg -i image%d.jpg -c:v libx264 -r 30 output.mp4
```

Extract audio from video:
```bash
ffmpeg -i input.mp4 -vn -c:a copy output.mp3
```

The {doc7} tool is extremely versatile and supports nearly all video and audio formats. The basic syntax is:
`ffmpeg -i input [options] output`

You can combine multiple options to precisely control the conversion process, such as codecs, bitrates, frame rates, and filters.
"""

    else:
        return f"""Based on the documentation you've asked about, here are some key insights:

The combination of Unix tools can be very powerful when used together. For example:

1. You can use {doc2} to search for patterns in text files:
```bash
grep "pattern" file.txt
```

2. Then pipe that to {doc3} for text transformation:
```bash
grep "pattern" file.txt | sed 's/old/new/g'
```

3. Use {doc5} scripts to automate complex sequences:
```bash
for file in *.log; do
  grep "ERROR" "$file" | sed 's/ERROR/CRITICAL/' >> errors.txt
done
```

4. When working with {doc1}, you can leverage its built-in functions:
```python
with open('file.txt', 'r') as f:
    content = f.read()
    processed = content.replace('old', 'new')
```

5. For video processing with {doc7}, you can extract frames or convert formats:
```bash
ffmpeg -i input.mp4 -r 1 frames/%04d.png
```

6. When compiling with {doc6}, optimization flags can significantly improve performance:
```bash
gcc -O3 -march=native -o program program.c
```

These tools each have specific strengths, but they become even more powerful when combined in workflows.
"""

if __name__ == "__main__":
    # Test the conversation generator
    conversation, doc1, doc2, doc3, doc4, doc5, doc6, doc7 = generate_conversation(3)
    print(f"Generated conversation about {doc1}, {doc2}, {doc3}, {doc4}, {doc5}, {doc6}, and {doc7}")
    for msg in conversation:
        print(f"\n[{msg['role']}]")
        print(msg['content'])