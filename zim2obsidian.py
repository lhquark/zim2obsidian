#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zim Wiki to Obsidian Converter

This script converts Zim Wiki notebooks to Obsidian vaults.
"""



import os
import re
import shutil
import argparse
import logging
import logging.handlers  # Import handlers module
import datetime
import yaml
from pathlib import Path
import glob

# Setup logging
def setup_logging(log_level, log_file=None):
    """
    Setup logging
    
    Args:
        log_level: The logging level ('debug', 'info', 'warning', 'error', 'critical')
        log_file: Path to the log file. If None, a default path is used.
    
    Returns:
        A configured logger object
    """
    # Map log level strings to logging constants
    log_levels = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    level = log_levels.get(log_level.lower(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger('zim2obsidian')
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplication
    if logger.handlers:
        logger.handlers.clear()
    
    # Log format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (with rotation)
    if log_file is None:
        log_file = "zim2obsidian.log"
    
    try:
        # Use RotatingFileHandler instead of FileHandler to support log rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            # mode='a',  # Append mode, do not overwrite existing logs
            mode='w',  # Overwrite
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3,  # Keep 3 backup files
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (IOError, PermissionError) as e:
        # If the log file cannot be created, log an error but do not interrupt the program
        print(f"Warning: Could not create log file {log_file}: {e}")
        print(f"Logging will only be output to the console")
    
    return logger

class ZimToObsidianConverter:
    """Converter class for Zim Wiki to Obsidian"""
    
    def __init__(self, input_dir, output_dir, logger):
        """Initialize the converter"""
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.logger = logger
        
        # Ensure the output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Store paths of processed equation files
        self.processed_equations = set()
        
    def convert_notebook(self):
        """Convert the entire notebook"""
        self.logger.info(f"Starting conversion: {self.input_dir} -> {self.output_dir}")
        
        # Iterate over all Zim Wiki files
        for zim_file in self.input_dir.glob('**/*.txt'):
            # Skip non-Zim Wiki files
            if not self._is_zim_file(zim_file):
                self.logger.debug(f"Skipping non-Zim file: {zim_file}")
                continue
                
            self.logger.info(f"Processing file: {zim_file}")
            self.convert_file(zim_file)
            
        # Copy attachment files
        self.copy_attachments()
        
        self.logger.info("Conversion complete")

        # Rename Obsidian notes
        self.rename_obsidian_notes()
    
    def _is_zim_file(self, file_path):
        """Check if a file is a Zim Wiki file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                return first_line.startswith('Content-Type: text/x-zim-wiki')
        except Exception as e:
            self.logger.warning(f"Error checking file type: {file_path}, {str(e)}")
            return False
    
    def convert_file(self, zim_file):
        """Convert a single Zim Wiki file to Obsidian format"""
        try:
            # Read Zim file content
            with open(zim_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get relative path
            rel_path = zim_file.relative_to(self.input_dir)
            
            # Create the corresponding Obsidian file path
            obsidian_file = self.output_dir / rel_path.with_suffix('.md')
            obsidian_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert content
            obsidian_content = self.convert_content(content, zim_file)
            
            # Write to Obsidian file
            with open(obsidian_file, 'w', encoding='utf-8') as f:
                f.write(obsidian_content)
                
            self.logger.debug(f"Converted: {zim_file} -> {obsidian_file}")
            
        except Exception as e:
            self.logger.error(f"Error converting file: {zim_file}, {str(e)}")
    
    def convert_content(self, content, file_path):
        """Convert Zim Wiki content to Obsidian format"""
        # Extract metadata
        metadata = self.extract_metadata(content, file_path)
        
        # Remove Zim Wiki header
        content = self.remove_zim_header(content)
        
        # Convert various formats
        content = self.convert_headings(content)
        content = self.convert_text_formatting(content)
        content = self.convert_tags(content)
        content = self.convert_lists(content)
        content = self.convert_checkboxes(content)
        content = self.convert_images(content, file_path)
        content = self.convert_attachments(content, file_path)
        content = self.convert_code_blocks(content)
        content = self.convert_equations(content, file_path)
        content = self.convert_tables(content)
        content = self.convert_links(content, file_path)
        
        # Add Obsidian frontmatter
        content = self.add_frontmatter(content, metadata)
        
        return content
    
    def extract_metadata(self, content, file_path):    # Fix: Use file modification time
        """Extract metadata from Zim Wiki content"""
        metadata = {}
        
        # Extract creation date
        creation_date_match = re.search(r'Creation-Date: (.+)', content)
        if creation_date_match:
            date_str = creation_date_match.group(1).strip()
            try:
                # Parse ISO format date
                dt = datetime.datetime.fromisoformat(date_str)
                metadata['created'] = dt.strftime('%Y-%m-%dT%H:%M')
                
                # Get file modification time
                mtime = file_path.stat().st_mtime
                mtime_dt = datetime.datetime.fromtimestamp(mtime)
                metadata['updated'] = mtime_dt.strftime('%Y-%m-%dT%H:%M')
                
                self.logger.debug(f"File: {file_path}, Extracted creation time from Creation-Date: {dt}, Modification time: {mtime_dt}")
            except ValueError:
                self.logger.warning(f"Could not parse date from Creation-Date: {date_str}")

        # If creation date is not extracted from Creation-Date, try parsing from under H1
        if 'created' not in metadata:
            # Remove Zim Wiki header to avoid interfering with H1 title search
            content_body = self.remove_zim_header(content)
            h1_match = re.search(r'^====== (.+?) ======$', content_body, re.MULTILINE)
            if h1_match:
                h1_end_pos = h1_match.end()
                # Find the first line after the H1 title
                next_line_match = re.search(r'^\s*(.+?)\s*$', content_body[h1_end_pos:], re.MULTILINE)
                if next_line_match:
                    date_line = next_line_match.group(1).strip()
                    # Match "Created Tuesday 21 November 2017" format
                    # Updated regex to be more robust for day and month names
                    date_pattern_match = re.search(
                        r'Created\s+(?:.+?)\s+(\d{1,2})\s+(.+?)\s+(\d{4})',
                        date_line,
                        re.IGNORECASE
                    )
                    if date_pattern_match:
                        day = int(date_pattern_match.group(1))
                        month_str = date_pattern_match.group(2)
                        year = int(date_pattern_match.group(3))
                        
                        # Month mapping, can be extended as needed
                        month_map = {
                            "一月": 1, "二月": 2, "三月": 3, "四月": 4,
                            "五月": 5, "六月": 6, "七月": 7, "八月": 8,
                            "九月": 9, "十月": 10, "十一月": 11, "十二月": 12,
                            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
                            "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
                            "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
                        }
                        
                        month = None
                        for k, v in month_map.items():
                            if k.lower() in month_str.lower():
                                month = v
                                break
                        
                        if month:
                            try:
                                dt = datetime.datetime(year, month, day, 0, 0, 0)
                                metadata['created'] = dt.strftime('%Y-%m-%dT%H:%M')
                                self.logger.info(f"File: {file_path}, Extracted creation time from H1: {dt}")
                                # # If creation date is extracted from H1, ensure updated is also set
                                # if 'updated' not in metadata:
                                #     mtime = file_path.stat().st_mtime
                                #     mtime_dt = datetime.datetime.fromtimestamp(mtime)
                                #     metadata['updated'] = mtime_dt.strftime('%Y-%m-%dT%H:%M')
                                #     self.logger.debug(f"File: {file_path}, Set modification time (based on H1 creation time): {mtime_dt}")
                            except ValueError as e:
                                self.logger.warning(f"Could not construct date from text under H1: {date_line}, Error: {e}")
                        else:
                            self.logger.warning(f"Could not parse month from text under H1: {date_line}")
                    else:
                        self.logger.debug(f"Line under H1 '{date_line}' does not match expected date format")
                else:
                    self.logger.debug(f"No content line after H1 title in file {file_path}")
            else:
                self.logger.debug(f"H1 title not found in file {file_path}")

        # If 'updated' time is still missing, use file modification time as a fallback
        if 'updated' not in metadata:
            mtime = file_path.stat().st_mtime
            mtime_dt = datetime.datetime.fromtimestamp(mtime)
            metadata['updated'] = mtime_dt.strftime('%Y-%m-%dT%H:%M')
            self.logger.debug(f"File: {file_path}, Using file modification time as fallback for updated time: {mtime_dt}")
            # # If 'created' is also missing, use file modification time as well
            # if 'created' not in metadata:
            #     metadata['created'] = mtime_dt.strftime('%Y-%m-%dT%H:%M')
            #     self.logger.debug(f"File: {file_path}, Using file modification time as fallback for created time: {mtime_dt}")

        return metadata
    
    def remove_zim_header(self, content):
        """Remove Zim Wiki header"""
        # Find content after the first blank line
        header_end = re.search(r'\n\n', content)
        if header_end:
            return content[header_end.end():]
        return content
    
    def convert_headings(self, content):
        """Convert heading format"""
        # Replace Zim Wiki heading format with Markdown format
        content = re.sub(r'====== (.+?) ======', r'# \1', content)
        content = re.sub(r'===== (.+?) =====', r'## \1', content)
        content = re.sub(r'==== (.+?) ====', r'### \1', content)
        content = re.sub(r'=== (.+?) ===', r'#### \1', content)
        content = re.sub(r'== (.+?) ==', r'##### \1', content)
        
        return content
    
    def convert_text_formatting(self, content):
        """Convert text formatting"""
        # Bold remains unchanged: **text**
        
        # Italic: //text// -> *text*
        content = re.sub(r'//(.+?)//', r'*\1*', content)
        
        # Highlight: __text__ -> ==text==
        content = re.sub(r'__(.+?)__', r'==\1==', content)
        
        # Strikethrough remains unchanged: ~~text~~
        
        # Code: ''text'' -> `text`
        content = re.sub(r"''(.+?)''", r'`\1`', content)
        
        # Subscript: A_{subscript} -> A<sub>subscript</sub>
        content = re.sub(r'([A-Za-z0-9])_\{(.+?)\}', r'\1<sub>\2</sub>', content)
        
        # Superscript: B^{superscript} -> B<sup>superscript</sup>
        content = re.sub(r'([A-Za-z0-9])\^\{(.+?)\}', r'\1<sup>\2</sup>', content)
        
        return content
    
    def convert_tags(self, content):
        """Convert tag format"""
        # @tag -> #tag
        content = re.sub(r'@(\w+)', r'#\1', content)
        
        return content
    
    def convert_lists(self, content):
        """Convert list format"""
        # Unordered list: * item -> - item
        content = re.sub(r'^\* (.*)$', r'- \1', content, flags=re.MULTILINE)
        
        # Ordered list remains unchanged: 1. item
        
        return content
    
    def convert_checkboxes(self, content):
        """Convert checkbox format"""
        # [ ] -> - [ ]
        content = re.sub(r'^(\s*)?\[ \](.*)$', r'\1- [ ]\2', content, flags=re.MULTILINE)
        
        # [*] -> - [x]
        content = re.sub(r'^(\s*)?\[\*\](.*)$', r'\1- [x]\2', content, flags=re.MULTILINE)
        
        # [x] -> - [-]
        content = re.sub(r'^(\s*)?\[x\](.*)$', r'\1- [-]\2', content, flags=re.MULTILINE)
        
        # [>] -> - [>]
        content = re.sub(r'^(\s*)?\[>\](.*)$', r'\1- [>]\2', content, flags=re.MULTILINE)
        
        # [<] -> - [<]
        content = re.sub(r'^(\s*)?\[<\](.*)$', r'\1- [<]\2', content, flags=re.MULTILINE)
        
        return content
    
    def convert_images(self, content, file_path):
        """Convert image references"""
        # {{./image.png}} -> ![[image.png]]
        def replace_image(match):
            img_path_full = match.group(1) # e.g., "./image.png?width=800" or "./image.png"

            # If it's an equation image, skip it (will be handled in convert_equations)
            if '?type=equation' in img_path_full:
                return match.group(0)

            img_path_base = img_path_full
            
            # Try to extract width parameter
            # {{.\image.png?width=800}} -> ![[image.png|800]]
            width_match = re.search(r'width=(\d+)', img_path_full)
            width_value = None
            if width_match:
                width_value = width_match.group(1)
            
            # Remove the query parameter part to get the pure image path
            # {{.\image.png?height=30}} -> ![[image.png]] (height is ignored)
            if '?' in img_path_base:
                img_path_base = img_path_base.split('?', 1)[0]
            
            # Handle relative paths
            if img_path_base.startswith('./'):
                img_path_base = img_path_base[2:]
            
            img_name = os.path.basename(img_path_base) # e.g., "image.png"

            if width_value:
                return f'![[{img_name}|{width_value}]]'
            else:
                # Cases with height (ignored) or no parameters
                return f'![[{img_name}]]'
            
        content = re.sub(r'\{\{(.+?)\}\}', replace_image, content)
        
        return content
    
    def convert_attachments(self, content, file_path):
        """Convert attachment references"""
        # [[./file.pdf]] -> ![[file.pdf]]
        def replace_attachment(match):
            attachment_path = match.group(1)
            
            # Handle relative paths
            if attachment_path.startswith('./'):
                attachment_path = attachment_path[2:]
                
            # Get attachment filename
            attachment_name = os.path.basename(attachment_path)
            
            return f'![[{attachment_name}]]'
            
        content = re.sub(r'\[\[\.\/(.+?)\]\]', replace_attachment, content)
        
        return content
    
    def convert_code_blocks(self, content):
        """Convert code blocks"""
        # {{{code: lang="sh" linenumbers="True" ... }}} -> ```sh ln:true ... ```
        def replace_code_block(match):
            code_content = match.group(2)
            
            # Extract language and line number settings
            lang_match = re.search(r'lang="([^"]+)"', match.group(1))
            lang = lang_match.group(1) if lang_match else ''
            
            line_numbers = 'ln:true' if 'linenumbers="True"' in match.group(1) else ''
            
            if line_numbers:
                return f'```{lang} {line_numbers}\n{code_content}```'
            else:
                return f'```{lang}\n{code_content}```'
                
        content = re.sub(r'\{\{\{code: ([^\n]*)\n(.*?)\}\}\}', replace_code_block, content, flags=re.DOTALL)
        
        return content
    
    def convert_equations(self, content, file_path):
        """Convert equations"""
        # {{./equation.png?type=equation}} -> $$ ... $$
        def replace_equation(match):
            eq_path = match.group(1)
            
            # Remove query parameters
            eq_path = eq_path.split('?')[0]
            
            # Construct full path
            if eq_path.startswith('./'):
                # In Zim Wiki, ./ is relative to the current file's directory
                # e.g., for {{./image.png}} in dir/subdir/file.txt,
                # the actual path is dir/subdir/image.png
                eq_path = eq_path[2:]  # Remove ./ prefix
                
                # Check if a subdirectory with the same name as the file exists
                # e.g., for file dir/subdir.txt, check for dir/subdir/ directory
                file_name = file_path.stem
                file_dir = file_path.parent
                possible_subdir = file_dir / file_name
                
                if possible_subdir.is_dir():
                    # If a same-name subdirectory exists, look for the equation file in it
                    full_eq_path = possible_subdir / eq_path
                    self.logger.debug(f"Searching in same-name subdirectory: {full_eq_path}")
                else:
                    # Otherwise, look in the current file's directory
                    full_eq_path = file_path.parent / eq_path
            else:
                # If it doesn't start with ./, it might be an absolute path or other format
                full_eq_path = Path(self.input_dir) / eq_path
            
            # Find the corresponding .tex file
            tex_path = full_eq_path.with_suffix('.tex')
            
            # Debugging info
            self.logger.debug(f"File path: {file_path}")
            self.logger.debug(f"File name: {file_path.stem}")
            self.logger.debug(f"Equation path: {eq_path}")
            self.logger.debug(f"Full path: {full_eq_path}")
            self.logger.debug(f"TEX file path: {tex_path}")
            self.logger.debug(f"TEX file exists: {tex_path.exists()}")
            
            if tex_path.exists():
                try:
                    with open(tex_path, 'r', encoding='utf-8') as f:
                        tex_content = f.read().strip()
                    
                    # Mark this equation file as processed
                    self.processed_equations.add(str(tex_path))
                    # Also mark the corresponding png file as processed
                    self.processed_equations.add(str(full_eq_path))
                    
                    self.logger.debug(f"Marked as processed: TEX={tex_path}, PNG={full_eq_path}")
                    
                    return f'$$\n{tex_content}\n$$'
                except Exception as e:
                    self.logger.warning(f"Error reading equation file: {tex_path}, {str(e)}")
                    return match.group(0)
            else:
                self.logger.warning(f"Equation file not found: {tex_path}")
                return match.group(0)
                
        content = re.sub(r'\{\{(.+?)\?type=equation\}\}', replace_equation, content)
        
        return content
    
    def convert_tables(self, content):
        """Convert table format"""
        # The table formats of Zim and Obsidian are basically the same, but colons in the separator line need to be removed
        def replace_table_alignment(match):
            # Match the entire table separator line and remove all colons
            line = match.group(0)
            return line.replace(':', '-')
            
        # Match the table separator line, e.g., |:-----|:-----|:-----|
        # Use multiline mode to ensure only table separator lines are matched
        content = re.sub(r'^\|[-:|]+\|$', replace_table_alignment, content, flags=re.MULTILINE)
        
        # New: Replace \n in table cells with <br>
        processed_lines = []
        for line in content.splitlines():
            # Check if it is a table row and not a separator row
            # A table row is defined as: starts with | and ends with | after stripping whitespace
            stripped_line = line.strip()
            if stripped_line.startswith('|') and \
               stripped_line.endswith('|') and \
               not re.match(r'^\|[-:|]+\|$', stripped_line):
                # It is a table data row or header row.
                # In Zim's .txt format, newlines within cells are \n.
                # Directly replace \n in the line with <br>.
                processed_lines.append(line.replace('\\n', '<br>'))
            else:
                # Separator row or non-table row
                processed_lines.append(line)
        
        content = '\n'.join(processed_lines)
        
        return content
    
    def convert_links(self, content, file_path):
        """Convert link format"""
        # Handle top-level links: [[:page]] -> [[page]]
        content = re.sub(r'\[\[:([^\]]+)\]\]', r'[[\1]]', content)
        
        # Handle subpage links: [[+subpage]] -> [[subpage]]
        content = re.sub(r'\[\[\+([^\]]+)\]\]', r'[[\1]]', content)
        
        # Handle links with paths: [[path:page]] -> [[path/page]]
        def _replace_zim_path_colons(match):
            full_match_content = match.group(1)
            # Exclude URLs (e.g., http://, ftp://) and mailto links
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', full_match_content) or \
               re.match(r'^mailto:', full_match_content, re.IGNORECASE):
                return match.group(0)  # Return the original full match, e.g., "[[http://example.com]]"

            # For Zim-style paths like "path:to:note", replace colons with slashes
            return f'[[{full_match_content.replace(":", "/")}]]'

        # Regex to find links like [[path:to:note]] or [[..:sibling:page]]
        # It captures content between [[ and ]] that contains one or more colons
        # and does not contain '|' (ensured by [^:\]|]+).
        # Group 1: The full path string, e.g., "path:to:note"
        # The (?:[^:\]|]+\:) part matches "segment:" (where segment contains no :, ], |)
        # The + ensures there is at least one such "segment:"
        # The [^:\]|]+ part matches the final segment after the last colon.
        content = re.sub(r'\[\[((?:[^:\]|]+\:)+[^:\]|]+)\]\]', _replace_zim_path_colons, content)
        
        # Links with display text remain unchanged: [[link|text]]
        
        return content
    
    def add_frontmatter(self, content, metadata):
        """Add Obsidian frontmatter"""
        if not metadata:
            return content
            
        # Create YAML frontmatter
        frontmatter = yaml.dump(metadata, allow_unicode=True, sort_keys=False).strip()
        
        # Prepend to content
        return f"---\n{frontmatter}\n---\n\n{content}"
    
    def copy_attachments(self):
        """Copy attachment files to the output directory"""
        self.logger.info("Copying attachment files")
        
        # Copy all non-.txt and non-.zim files
        for attachment in self.input_dir.glob('**/*'):
            # Skip directories
            if attachment.is_dir():
                continue
                
            # Skip Zim Wiki files
            if attachment.suffix in ['.txt', '.zim']:
                continue
                
            # Skip .tex files (equation source files)
            if attachment.suffix == '.tex':
                continue
                
            # Skip processed equation files
            if str(attachment) in self.processed_equations:
                self.logger.debug(f"Skipping processed equation file: {attachment}")
                continue
                
            # Skip png files related to equations
            if attachment.suffix == '.png' and attachment.with_suffix('.tex').exists():
                self.logger.debug(f"Skipping png file related to equation: {attachment}")
                continue
                
            # Get relative path
            rel_path = attachment.relative_to(self.input_dir)
            
            # Add debug logs
            self.logger.debug(f"Attachment relative path: {rel_path}")
            self.logger.debug(f"Attachment parent directory: {rel_path.parent}")
            
            # Check if it needs to be moved to the parent directory
            if len(rel_path.parts) > 1:
                # Get filename
                filename = rel_path.name
                # Calculate parent directory path
                parent_dir = rel_path.parent
                self.logger.debug(f"Attachment should be moved to parent directory: {parent_dir} -> {parent_dir.parent}")
                
                # Create new target path (move to parent directory)
                target_path = self.output_dir / parent_dir.parent / filename
                self.logger.debug(f"New target path: {target_path}")
            else:
                # If already in the top-level directory, keep the original path
                target_path = self.output_dir / rel_path
                self.logger.debug(f"Attachment is already in the top-level directory, keeping original path: {target_path}")
            
            # Ensure the target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                # Copy file
                shutil.copy2(attachment, target_path)
                self.logger.debug(f"Copied attachment: {attachment} -> {target_path}")
            except Exception as e:
                self.logger.error(f"Error copying attachment: {attachment}, {str(e)}")

    def rename_obsidian_notes(self):
        """
        Iterate through the output Obsidian notes, extract the first H1 title as the note name,
        and rename the .md file and its corresponding folder using that name.
        """
        self.logger.info("Starting to rename Obsidian notes...")
        for md_file_path in self.output_dir.glob('**/*.md'):
            if not md_file_path.is_file():
                continue

            self.logger.debug(f"Processing file for renaming: {md_file_path}")
            try:
                with open(md_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract the first H1 title
                h1_match = re.search(r'^# (.*)', content, re.MULTILINE)
                if h1_match:
                    new_name_raw = h1_match.group(1).strip()
                    # Sanitize the filename by removing illegal characters
                    new_name_sanitized = re.sub(r'[\\/:*?"<>|]', '_', new_name_raw)
                    # Avoid excessively long or empty filenames
                    if not new_name_sanitized:
                        self.logger.warning(f"Extracted H1 title is empty or contains only illegal characters, skipping rename: {md_file_path}")
                        continue
                    new_name = new_name_sanitized[:200] # Limit filename length

                    old_name_stem = md_file_path.stem
                    new_file_path = md_file_path.with_name(new_name + '.md')
                    
                    # Check if the new filename is different from the old one
                    if md_file_path == new_file_path:
                        self.logger.debug(f"Filename is already the target name, no rename needed: {md_file_path}")
                        continue

                    # Rename the .md file
                    if new_file_path.exists():
                        self.logger.warning(f"Target file {new_file_path} already exists, skipping rename of {md_file_path} to avoid overwrite")
                        continue
                    
                    md_file_path.rename(new_file_path)
                    self.logger.info(f"File renamed: {md_file_path} -> {new_file_path}")
                    
                    # Check for and rename the corresponding folder
                    old_dir_path = md_file_path.with_name(old_name_stem) # Use the old stem to construct the directory path
                    if old_dir_path.is_dir() and old_dir_path.name == old_name_stem : # Ensure it's the corresponding folder
                        new_dir_path = new_file_path.with_name(new_name)
                        if new_dir_path.exists() and new_dir_path.is_dir():
                             self.logger.warning(f"Target folder {new_dir_path} already exists, skipping rename of {old_dir_path} to avoid overwrite")
                        elif new_dir_path.exists() and not new_dir_path.is_dir():
                            self.logger.warning(f"Target path {new_dir_path} already exists and is not a folder, skipping rename of {old_dir_path}")
                        else:
                            old_dir_path.rename(new_dir_path)
                            self.logger.info(f"Folder renamed: {old_dir_path} -> {new_dir_path}")
                else:
                    self.logger.debug(f"No H1 title found in file {md_file_path}, skipping rename.")
            except Exception as e:
                self.logger.error(f"Error renaming note: {md_file_path}, {str(e)}")
        self.logger.info("Obsidian note renaming complete.")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Zim Wiki to Obsidian Converter.")
    parser.add_argument("input_dir", help="Zim Wiki notebook directory.")
    parser.add_argument("output_dir", help="Obsidian vault output directory.")
    parser.add_argument("--log-level", default="info", choices=['debug', 'info', 'warning', 'error', 'critical'], help="Set the logging level.")
    parser.add_argument("--log-file", help="Path to the log file.")
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Set default log file path in the output directory
    log_file = args.log_file
    if log_file is None:
        log_file = str(output_dir / "zim2obsidian.log")
        # log_file = str("zim2obsidian.log")
    
    # Setup logging
    logger = setup_logging(args.log_level, log_file)
    logger.info(f"Log file path: {log_file}")
    
    # Create converter and execute conversion
    converter = ZimToObsidianConverter(args.input_dir, args.output_dir, logger)
    converter.convert_notebook()

if __name__ == '__main__':
    main()