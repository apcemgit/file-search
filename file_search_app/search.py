"""
Core file search logic.
"""
import os
import re
from . import file_reader

class FileSearcher:
    def __init__(self, params):
        self.params = params

    def _matches_pattern(self, text, pattern):
        use_regex = self.params['use_regex']
        case_sensitive = self.params['case_sensitive']

        if use_regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                return re.search(pattern, text, flags) is not None
            except re.error as e:
                # In a real app, this should be logged or reported back to the UI
                print(f"Regex Error: {e}")
                return False
        else:
            keywords = pattern.split()
            if not case_sensitive:
                text = text.lower()
                keywords = [k.lower() for k in keywords]
            
            if self.params['match_any']:
                return any(k in text for k in keywords)
            else:
                return all(k in text for k in keywords)

    def search(self, progress_callback, result_callback, completion_callback):
        """Walks through directories and searches for files."""
        directory = self.params['directory']
        pattern = self.params['pattern']
        extensions = self.params['extensions']
        search_content = self.params['search_content']
        case_sensitive = self.params['case_sensitive']
        use_regex = self.params['use_regex']

        all_files = [os.path.join(r, f) for r, d, fs in os.walk(directory) for f in fs]
        total_files = len(all_files)
        scanned = 0

        for filepath in all_files:
            scanned += 1
            if progress_callback:
                progress_callback(scanned, total_files)

            file_ext = os.path.splitext(filepath)[1][1:].lower()
            if extensions and file_ext not in extensions:
                continue

            filename_to_match = os.path.basename(filepath) if case_sensitive else os.path.basename(filepath).lower()
            name_match = self._matches_pattern(filename_to_match, pattern)

            content_match = False
            content_snippet = ""
            if search_content:
                content = file_reader.read_file_content(filepath)
                content_to_match = content if case_sensitive else content.lower()
                pattern_for_search = pattern if use_regex or case_sensitive else pattern.lower()
                content_match = self._matches_pattern(content_to_match, pattern_for_search)
                if content_match:
                    try:
                        pos = -1
                        if use_regex:
                            match = re.search(pattern, content, re.IGNORECASE if not case_sensitive else 0)
                            if match:
                                pos = match.start()
                        else:
                            # Find position in the correct case for snippet extraction
                            pos = content_to_match.find(pattern_for_search.split()[0])

                        if pos != -1:
                            start = max(0, pos - 75)
                            end = min(len(content), pos + 75)
                            content_snippet = content[start:end].strip()
                        else:
                            content_snippet = content[:150].strip()
                    except Exception:
                        content_snippet = content[:150].strip()


            if (search_content and content_match) or (not search_content and name_match):
                try:
                    stat = os.stat(filepath)
                    result = {
                        'name': os.path.basename(filepath),
                        'path': filepath,
                        'size': stat.st_size,
                        'mtime': stat.st_mtime,
                        'ext': file_ext,
                        'snippet': content_snippet
                    }
                    if result_callback:
                        result_callback(result)
                except OSError:
                    continue # Skip files that can't be accessed
        
        if completion_callback:
            completion_callback()
