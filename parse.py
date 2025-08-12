#!/usr/bin/env python3
import os
import argparse

def extract_files_from_data_file(data_file_path, target_dir):
    with open(data_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_path = None
    buffer = []

    for line in lines:
        if line.startswith("# filename:"):
            stripped = line.strip()

            # Start of a new file block
            if not stripped.startswith("# end file"):
                if current_path and buffer:
                    write_file(current_path, buffer, target_dir)
                    buffer = []

                current_path = stripped[12:].strip()
                #print ( "current path:", current_path )

            # End of current file block
            elif stripped == "# end file":
                if current_path and buffer:
                    write_file(current_path, buffer, target_dir)
                current_path = None
                buffer = []
                continue  # Skip '# end file'

        elif current_path and not line.startswith("# end file"):
            if line.strip() == "":
                buffer.append("\n")
            else:
                buffer.append(line)

    # Write last file if not closed
    if current_path and buffer:
        write_file(current_path, buffer, target_dir)

def write_file(rel_path, content_lines, base_dir):
    full_path = os.path.join(base_dir, rel_path)
    dir_path = os.path.dirname(full_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    with open(full_path, 'w', encoding='utf-8') as f:
        f.writelines(content_lines)

    print(f"Wrote file: {full_path}")

def main():
    parser = argparse.ArgumentParser(description="Extract and write code files from a data file.")
    parser.add_argument('-f', '--file', required=True, help='Path to the input data file')
    parser.add_argument('-d', '--directory', required=True, help='Target directory to write files to')
    args = parser.parse_args()

    extract_files_from_data_file(args.file, args.directory)

if __name__ == "__main__":
    main()
