import sys
import os
import urllib.parse
import requests

def search_word(word):
    """Search DuckDuckGo for a word and return titles and URLs of results."""
    query = urllib.parse.quote_plus(word)
    url = f'https://duckduckgo.com/html/?q={query}'
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp.raise_for_status()
    except Exception as e:
        print(f'Error fetching results for "{word}": {e}', file=sys.stderr)
        return []
    # Very simple parsing: look for <a class="result__a" href="...">Title</a>
    results = []
    for line in resp.text.splitlines():
        if 'class="result__a"' in line:
            # extract href and title
            try:
                href_part = line.split('href="', 1)[1]
                url_part, _ = href_part.split('"', 1)
                title_part = line.split('>')[1].split('<')[0]
                results.append((title_part, url_part))
            except Exception:
                continue
    return results

def load_words_from_file(filepath):
    """Read a file and return a list of non‑empty stripped words."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f'Could not read file "{filepath}": {e}', file=sys.stderr)
        return []

def main():
    if len(sys.argv) < 2:
        print('Usage: python search_internet.py <word1> [word2 ...] or python search_internet.py <file_with_words>')
        sys.exit(1)
    # If a single argument points to an existing file, treat it as a list source
    if len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
        words = load_words_from_file(sys.argv[1])
        if not words:
            print('No words found in the file.', file=sys.stderr)
            sys.exit(1)
    else:
        words = sys.argv[1:]

    for w in words:
        print(f'\nResults for "{w}":')
        res = search_word(w)
        if not res:
            print('  No results or error.')
        else:
            for title, link in res[:5]:  # show top 5
                print(f'  - {title}\n    {link}')

if __name__ == '__main__':
    main()
