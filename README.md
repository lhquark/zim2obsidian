# Zim to Obsidian Converter

This Python script provides a robust solution for converting Zim Wiki notebooks into Obsidian vaults. It aims to preserve as much formatting, structure, and metadata as possible during the migration process, ensuring a smooth transition for users moving from Zim to Obsidian.

## Features

The converter handles a wide range of Zim Wiki syntax and features, including:

- **Headers**: Converts Zim's heading styles (`====== H1 ======`, `===== H2 =====`, etc.) to Markdown's `# H1`, `## H2`.
- **Text Formatting**:
    - Bold (`**text**`)
    - Italic (`//text//` to `*text*`)
    - Highlight (`__text__` to `==text==`)
    - Strikethrough (`~~text~~`)
    - Inline Code (`''text''` to `` `text` ``)
    - Subscript and Superscript
- **Lists**: Translates both unordered and ordered lists.
- **Checkboxes**: Converts Zim's various checkbox states (`[ ]`, `[*]`, `[x]`) into Markdown-compatible task list items (`- [ ]`, `- [x]`).
- **Tags**: Migrates Zim tags (`@tag`) to Obsidian's hashtag format (`#tag`).
- **Links**: Intelligently converts internal Zim links (`+Page:SubPage`) to Obsidian's wikilink format (`[[Page/SubPage]]`).
- **Attachments & Images**:
    - Embeds images (`{{image.png}}`) and other file attachments (`[[file.pdf]]`) using Obsidian's `![[attachment]]` syntax.
    - Preserves image width attributes (`{{image.png?width=300}}` becomes `![[image.png|300]]`).
    - Copies all associated files from the Zim notebook directory to the new Obsidian vault.
- **Code Blocks**: Converts formatted code blocks, preserving the specified language for syntax highlighting.
- **Equations**: For equations rendered as images, the script finds the corresponding `.tex` file and embeds the LaTeX source in the Markdown file using `$$...$$`.
- **Metadata**: Extracts the `Creation-Date` from Zim files and uses file modification time to generate `created` and `updated` fields in Obsidian's frontmatter.
- **Logging**: Generates a detailed log file (`zim2obsidian.log`) to track the conversion process and troubleshoot any issues.

## Requirements

- Python 3.6+
- `PyYAML`

## Installation

1.  Clone or download the repository.
2.  Navigate to the `code` directory.
3.  Install the required dependency:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

The script is executed from the command line.

```bash
python zim2obsidian.py <path_to_zim_notebook> <path_to_output_obsidian_vault> [options]
```

### Arguments

-   `input_dir`: (Required) The full path to the root directory of your Zim Wiki notebook.
-   `output_dir`: (Required) The full path to the directory where the Obsidian vault will be created.
-   `--log-level`: (Optional) Set the logging level. Choices are `debug`, `info`, `warning`, `error`, `critical`. Default is `info`.
-   `--log-file`: (Optional) Specify a custom path for the log file. Default is `zim2obsidian.log` in the output directory.

### Example

```bash
python zim2obsidian.py "C:\Users\YourUser\Documents\ZimNotes" "C:\Users\YourUser\Documents\ObsidianVault" --log-level debug
```

This command will convert the Zim notebook located at `C:\Users\YourUser\Documents\ZimNotes` and create a new Obsidian vault at `C:\Users\YourUser\Documents\ObsidianVault` with debug-level logging.
