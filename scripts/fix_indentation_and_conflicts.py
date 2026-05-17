import os
import re



def clean_merge_markers(lines):
    return [line for line in lines if not any(marker in line for marker in MERGE_MARKERS)]


def fix_indentation(lines):
    fixed_lines = []
    indent_stack = [0]
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped:
            fixed_lines.append(line)
            continue
        # Detect function or class definition with no indented block
        if re.match(r"^(def|class) ", stripped):
            fixed_lines.append(line)
            # Look ahead for next non-empty, non-comment line
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith('#')):
                fixed_lines.append(lines[j])
                j += 1
            if j < len(lines):
                next_line = lines[j]
                if not next_line.startswith((' ', '\t')):
                    # Insert a pass statement
                    fixed_lines.append('    pass\n')
            continue
        fixed_lines.append(line)
    return fixed_lines


def process_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
    orig_lines = list(lines)
    lines = clean_merge_markers(lines)
    lines = fix_indentation(lines)
    if lines != orig_lines:
        with open(filepath, 'w') as f:
            f.writelines(lines)
        return True
    return False


def main():
    changed = []
    for root, _, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                if process_file(path):
                    changed.append(path)
    if changed:
        print("Fixed indentation/merge markers in:")
        for path in changed:
            print(f"  {path}")
    else:
        print("No changes needed.")


if __name__ == "__main__":
    main()
