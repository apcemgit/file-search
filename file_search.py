import os
import argparse

def search_files(directory, keywords, extensions=None, match_all=True, case_sensitive=False):
    """
    Search for files in a directory that match given keywords and optional extensions.

    :param directory: Root directory to search in
    :param keywords: List of keywords to search for in filenames
    :param extensions: List of file extensions to filter by (e.g., ['pdf', 'docx']). If None, all extensions allowed.
    :param match_all: If True, file must contain all keywords. If False, any keyword matches.
    :param case_sensitive: Whether the search is case-sensitive
    :return: List of matched file paths
    """
    matched_files = []

    # Normalize keywords for case-insensitive search
    search_keywords = [kw.lower() for kw in keywords] if not case_sensitive else keywords
    search_extensions = [ext.lower() for ext in extensions] if extensions and not case_sensitive else extensions

    for root, dirs, files in os.walk(directory):
        for file in files:
            filename = file if case_sensitive else file.lower()
            filepath = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1][1:].lower()  # Remove the dot and lowercase

            # Check extension filter (if provided)
            if extensions and file_ext not in search_extensions:
                continue

            # Check keyword match
            if match_all:
                if all(keyword.lower() in filename for keyword in keywords):
                    matched_files.append(filepath)
            else:
                if any(keyword.lower() in filename for keyword in keywords):
                    matched_files.append(filepath)

    return matched_files


def main():
    parser = argparse.ArgumentParser(description="Search for files by keywords and optional extensions.")
    parser.add_argument('keywords', nargs='+', help="Keywords to search for in filenames")
    parser.add_argument('-d', '--directory', default='.', help="Directory to search in (default: current)")
    parser.add_argument('--match-any', action='store_true', help="Match files that contain any keyword (default: all)")
    parser.add_argument('--case-sensitive', action='store_true', help="Perform case-sensitive search")
    parser.add_argument('-e', '--ext', nargs='+', metavar='EXT',
                        help="Filter by file extension(s), e.g. pdf docx pptx. Case-insensitive.")

    args = parser.parse_args()

    print(f"Searching in: {os.path.abspath(args.directory)}")
    print(f"Keywords: {args.keywords}")
    print(f"Extensions: {args.ext if args.ext else 'All'}")
    print(f"Match mode: {'Any keyword' if args.match_any else 'All keywords'}")
    print(f"Case sensitive: {args.case_sensitive}")
    print("-" * 60)

    if not os.path.isdir(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist.")
        return

    results = search_files(
        directory=args.directory,
        keywords=args.keywords,
        extensions=args.ext,
        match_all=not args.match_any,
        case_sensitive=args.case_sensitive
    )

    if results:
        print("Found matching files:")
        for path in results:
            print(f"  {path}")
    else:
        print("No matching files found.")


if __name__ == "__main__":
    main()