#!/usr/bin/env python3
"""
Script to validate all links in README.md are working and accessible.
"""
import re
import sys
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse
import argparse
import time


def extract_links_from_markdown(content):
    """Extract all links from markdown content."""
    # Pattern for markdown links: [text](url)
    link_pattern = r'\[([^\]]*)\]\(([^)]+)\)'
    links = re.findall(link_pattern, content)
    
    # Pattern for direct URLs
    url_pattern = r'https?://[^\s\)>]+'
    direct_urls = re.findall(url_pattern, content)
    
    # Combine and deduplicate
    all_links = []
    
    # Add markdown links
    for text, url in links:
        all_links.append({
            'text': text,
            'url': url,
            'type': 'markdown'
        })
    
    # Add direct URLs
    for url in direct_urls:
        # Skip if already in markdown links
        if not any(link['url'] == url for link in all_links):
            all_links.append({
                'text': url,
                'url': url,
                'type': 'direct'
            })
    
    return all_links


def check_internal_link(base_path, url):
    """Check if an internal link exists."""
    # Remove leading ./ if present
    clean_url = url.lstrip('./')
    
    # Remove anchors (#section) for file existence check
    file_url = clean_url.split('#')[0]
    
    if not file_url:  # Just an anchor link
        return True, "Anchor link (cannot verify without HTML)"
    
    file_path = base_path / file_url
    
    if file_path.exists():
        return True, f"File exists: {file_path}"
    else:
        return False, f"File not found: {file_path}"


def check_external_link(url, timeout=10):
    """Check if an external link is accessible."""
    try:
        # Use HEAD request first (faster)
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        
        # Some servers don't support HEAD, try GET if HEAD fails
        if response.status_code >= 400:
            response = requests.get(url, timeout=timeout, allow_redirects=True)
        
        if response.status_code < 400:
            return True, f"HTTP {response.status_code}"
        else:
            return False, f"HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)}"


def is_external_url(url):
    """Check if URL is external (starts with http/https)."""
    return url.startswith(('http://', 'https://'))


def validate_readme_links(readme_path, check_external=True, timeout=10):
    """Validate all links in README.md."""
    if not readme_path.exists():
        print(f"❌ README.md not found at: {readme_path}")
        return False
    
    print(f"🔍 Validating links in: {readme_path}")
    print("-" * 60)
    
    # Read README content
    content = readme_path.read_text(encoding='utf-8')
    
    # Extract all links
    links = extract_links_from_markdown(content)
    
    if not links:
        print("ℹ️  No links found in README.md")
        return True
    
    print(f"📊 Found {len(links)} links to validate")
    print()
    
    # Separate internal and external links
    internal_links = [link for link in links if not is_external_url(link['url'])]
    external_links = [link for link in links if is_external_url(link['url'])]
    
    all_passed = True
    base_path = readme_path.parent
    
    # Check internal links
    if internal_links:
        print("🔗 Internal Links:")
        for link in internal_links:
            success, message = check_internal_link(base_path, link['url'])
            status = "✅" if success else "❌"
            print(f"  {status} {link['url']} - {message}")
            if not success:
                all_passed = False
        print()
    
    # Check external links
    if external_links and check_external:
        print("🌐 External Links:")
        for i, link in enumerate(external_links):
            print(f"  🔄 Checking {link['url']}...", end='', flush=True)
            success, message = check_external_link(link['url'], timeout)
            status = "✅" if success else "❌"
            print(f"\r  {status} {link['url']} - {message}")
            if not success:
                all_passed = False
            
            # Rate limiting to be nice to servers
            if i < len(external_links) - 1:
                time.sleep(0.5)
        print()
    elif external_links and not check_external:
        print(f"🌐 External Links: {len(external_links)} found (skipped - use --check-external to verify)")
        print()
    
    # Summary
    print("-" * 60)
    if all_passed:
        print("✅ All links validated successfully!")
        return True
    else:
        print("❌ Some links failed validation!")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Validate README.md links")
    parser.add_argument(
        "readme_path", 
        nargs='?', 
        default="README.md",
        help="Path to README.md file (default: README.md)"
    )
    parser.add_argument(
        "--check-external", 
        action="store_true",
        help="Check external URLs (requires internet connection)"
    )
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=10,
        help="Timeout for external URL checks in seconds (default: 10)"
    )
    
    args = parser.parse_args()
    
    readme_path = Path(args.readme_path)
    
    # Make path relative to script location if not absolute
    if not readme_path.is_absolute():
        script_dir = Path(__file__).parent
        readme_path = script_dir.parent / readme_path
    
    success = validate_readme_links(
        readme_path, 
        check_external=args.check_external,
        timeout=args.timeout
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()