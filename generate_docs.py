import os
from datetime import datetime
from pathlib import Path

IGNORE_DIRS = {'.git', 'node_modules', '.next', '__pycache__', 'dist', 'build', 'venv_build', 'venv'}
IGNORE_FILES = {'package-lock.json', 'generate_docs.py', 'setup_structure.py', 'README.md', 'PROJECT_STRUCTURE.md', '.run_counter'}
IGNORE_PREFIXES = {'STRUCTURE_RUN_'}  # skip all old snapshot logs
ALLOWED_EXTENSIONS = {'.ts', '.tsx', '.css', '.js', '.jsx', '.mjs', '.json', '.md', '.py'}

COUNTER_FILE = '.run_counter'

def get_next_run_number():
    """Read the current counter, increment it, persist it, and return the new value."""
    counter = 1
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, 'r') as f:
                counter = int(f.read().strip()) + 1
        except (ValueError, IOError):
            counter = 1
    with open(COUNTER_FILE, 'w') as f:
        f.write(str(counter))
    return counter

def should_ignore_file(filename, output_file):
    if filename == output_file:
        return True
    if filename in IGNORE_FILES:
        return True
    if any(filename.startswith(p) for p in IGNORE_PREFIXES):
        return True
    return False

def get_user_choice():
    """Prompt the user to choose between a full snapshot or specific targets (files/folders)."""
    print("Select snapshot mode:")
    print("1. Capture ENTIRE project contents")
    print("2. Capture contents of SPECIFIC files/folders only (Tree view will still show everything)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == '2':
        print("\nEnter relative paths to files or folders, separated by commas.")
        print("Example: src/utils, frontend/components/ui, app.py")
        user_input = input("Targets to include: ")
        
        # Parse inputs into pure Path objects to natively resolve slashes / formatting
        raw_targets = []
        for t in user_input.split(','):
            cleaned = t.strip()
            if cleaned:
                raw_targets.append(Path(cleaned))
        return raw_targets
    return None

def is_file_targeted(file_relative_path, target_paths):
    """Check if a file matches target individual files or lives inside target folders."""
    if target_paths is None:
        return True  # Full snapshot mode

    file_path_obj = Path(file_relative_path)

    for target in target_paths:
        # Exact file match
        if file_path_obj == target:
            return True
        # If target is a directory, check if file lives inside it
        try:
            if target.is_dir() or not target.suffix:  # folder or no extension
                if target in file_path_obj.parents:
                    return True
        except Exception:
            # fallback: string containment
            if str(target) in str(file_path_obj):
                return True

    return False


def generate_markdown():
    # 1. Ask for Snapshot Mode
    target_paths = get_user_choice()
    
    # 2. Ask for Snapshot Comment
    print("\n" + "="*40)
    snapshot_comment = input("Enter snapshot comment/message (or press Enter to skip):\n> ").strip()
    print("="*40)
    
    run_number = get_next_run_number()
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d_%H-%M-%S")
    display_date = now.strftime("%B %d, %Y at %I:%M %p")

    project_name = os.path.basename(os.getcwd())
    output_file = f"STRUCTURE_RUN_{run_number}_{timestamp_str}.md"

    with open(output_file, 'w', encoding='utf-8') as md:
        # --- HEADER SECTION ---
        md.write(f"# Project Snapshot: {project_name}\n")
        md.write(f"**Run Name:** {run_number}_{timestamp_str}\n")
        md.write(f"**Run Number:** {run_number}\n")
        md.write(f"**Date:** {display_date}\n")
        md.write(f"**Status:** Development Phase\n")
        if target_paths:
            md.write(f"**Scope:** Selective ({len(target_paths)} explicit targets)\n")
        else:
            md.write(f"**Scope:** Full Project\n")
            
        # --- COMMENT BLOCK ---
        md.write("\n### 💬 Snapshot Message\n")
        if snapshot_comment:
            md.write(f"> {snapshot_comment}\n\n")
        else:
            md.write(f"> *No snapshot comment provided.*\n\n")
            
        md.write("---\n\n")

        # --- TREE VIEW (Always runs completely) ---
        md.write("## 📂 File Tree\n```text\n")
        for root, dirs, files in os.walk('.'):
            dirs[:] = sorted([d for d in dirs if d not in IGNORE_DIRS])

            rel_path = os.path.relpath(root, '.')
            level = 0 if rel_path == '.' else rel_path.count(os.sep) + 1
            indent = '│   ' * (level - 1) if level > 0 else ""
            folder_name = os.path.basename(root)

            if folder_name and folder_name != '.':
                md.write(f"{indent}├── {folder_name}/\n")

            sub_indent = '│   ' * level
            for f in sorted(files):
                if should_ignore_file(f, output_file):
                    continue
                if any(f.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                    md.write(f"{sub_indent}├── {f}\n")

        md.write("```\n\n---\n\n")

        # --- FILE CONTENTS ---
        md.write("## 📄 File Contents\n\n")
        
        for root, dirs, files in os.walk('.'):
            dirs[:] = sorted([d for d in dirs if d not in IGNORE_DIRS])

            for file in sorted(files):
                if should_ignore_file(file, output_file):
                    continue
                if any(file.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, '.')
                    
                    # Modernized structural lineage check using pathlib
                    if not is_file_targeted(relative_path, target_paths):
                        continue

                    ext = os.path.splitext(file)[1][1:]
                    lang = 'typescript' if ext in ['ts', 'tsx'] else ext

                    md.write(f"### `{relative_path.replace(os.sep, '/')}`\n")
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        md.write(f"```{lang}\n{content}\n```\n\n")
                    except Exception as e:
                        md.write(f"*Error reading file: {e}*\n\n")

    print(f"\n✅ Snapshot saved as: {output_file}")

if __name__ == "__main__":
    generate_markdown()