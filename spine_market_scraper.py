import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
from typing import Dict, List, Optional


class SpineMarketScraper:
    '''
    A Beautiful Soup-based scraper for multiple spine industry news sources.
    No Selenium or Playwright required.

    Supported sources:
    - Spine Market Group
    - Ortho Spine News
    - Becker's Spine Review
    '''

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Source configurations
        self.sources = {
            'spine_market_group': {
                'name': 'Spine Market Group',
                'base_url': 'https://thespinemarketgroup.com',
                'category_url': 'https://thespinemarketgroup.com/category/articles/',
            },
            'ortho_spine_news': {
                'name': 'Ortho Spine News',
                'base_url': 'https://orthospinenews.com',
                'category_url': 'https://orthospinenews.com/',
            },
            'beckers_spine': {
                'name': 'Becker\'s Spine Review',
                'base_url': 'https://www.beckersspine.com',
                'category_url': 'https://www.beckersspine.com/',
            }
        }
        
    def extract_financial_mentions(self, text: str) -> List[str]:
        '''Extract financial mentions like $50 billion, $9.2 billion, etc.'''
        pattern = r'\$\s*\d+(?:,\d{3})*(?:\.\d+)?\s*(?:billion|million|thousand|B|M|K)?'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        financial_mentions = []
        for match in matches:
            cleaned = re.sub(r'\s+', ' ', match.strip())
            if cleaned not in financial_mentions:
                financial_mentions.append(cleaned)
        
        return financial_mentions
    
    def extract_spine_procedures(self, text: str) -> List[str]:
        '''Extract spine-related procedures and keywords from content.'''
        spine_keywords = [
            'spinal fusion', 'laminectomy', 'discectomy', 'foraminotomy',
            'kyphoplasty', 'vertebroplasty', 'spinal decompression',
            'cervical', 'lumbar', 'thoracic', 'spine surgery', 'vertebral',
            'intervertebral', 'disc replacement', 'spinal stenosis',
            'scoliosis', 'kyphosis', 'lordosis', 'herniated disc',
            'spinal cord', 'orthopaedics', 'orthopedics', 'depuy synthes',
            'spine business', 'spinal implant', 'pedicle screw'
        ]
        
        found_procedures = []
        text_lower = text.lower()
        
        for keyword in spine_keywords:
            if keyword in text_lower:
                if keyword not in found_procedures:
                    found_procedures.append(keyword)
        
        return found_procedures

    def detect_source(self, url: str) -> Optional[str]:
        '''Detect which news source a URL belongs to.'''
        if 'thespinemarketgroup.com' in url:
            return 'spine_market_group'
        elif 'orthospinenews.com' in url:
            return 'ortho_spine_news'
        elif 'beckersspine.com' in url:
            return 'beckers_spine'
        return None

    def scrape_article_listing_page(self, source_key: str, limit: int = 10) -> List[str]:
        '''
        Scrape article URLs from a source's listing/category page.
        Handles pagination to get the requested number of articles.

        Args:
            source_key: Key for the source (e.g., 'spine_market_group')
            limit: Maximum number of article URLs to return

        Returns:
            List of article URLs
        '''
        if source_key not in self.sources:
            print(f"Unknown source: {source_key}")
            return []

        source = self.sources[source_key]
        category_url = source['category_url']
        article_urls = []
        page = 1
        max_pages = 10  # Safety limit to prevent infinite loops

        while len(article_urls) < limit and page <= max_pages:
            # Construct paginated URL
            if page == 1:
                url = category_url
            else:
                # Different pagination patterns for different sources
                if source_key == 'spine_market_group':
                    url = f"{category_url}page/{page}/"
                elif source_key == 'ortho_spine_news':
                    url = f"{category_url}page/{page}/"
                elif source_key == 'beckers_spine':
                    url = f"{category_url}page/{page}/"
                else:
                    url = f"{category_url}page/{page}/"

            try:
                print(f"  Fetching page {page}...")
                response = requests.get(url, headers=self.headers, timeout=30)

                # If we get a 404, we've reached the end
                if response.status_code == 404:
                    print(f"  Reached end of articles at page {page}")
                    break

                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')

                page_article_urls = []

                # Different scraping strategies based on source
                if source_key == 'spine_market_group':
                    # Look for article links in the articles category page
                    # Focus on h2/h3 article titles with links
                    article_links = []

                    # Try to find article containers
                    for article_elem in soup.find_all(['article', 'div'], class_=lambda x: x and ('post' in x.lower() or 'article' in x.lower() or 'entry' in x.lower())):
                        link = article_elem.find('a', href=True)
                        if link:
                            article_links.append(link)

                    # If no article containers found, look for links in h2/h3 tags
                    if not article_links:
                        for heading in soup.find_all(['h2', 'h3']):
                            link = heading.find('a', href=True)
                            if link:
                                article_links.append(link)

                    # Process found links
                    for link in article_links:
                        href = link['href']
                        # Ensure it's an absolute URL
                        if not href.startswith('http'):
                            if href.startswith('/'):
                                href = source['base_url'] + href
                            else:
                                href = source['base_url'] + '/' + href

                        # IMPORTANT: Only include URLs from the same domain
                        if not href.startswith(source['base_url']):
                            continue

                        # Filter out non-article pages
                        exclude_patterns = ['/category/', '/tag/', '/page/', '/author/', '/about', '/contact', '/product', '/companies']
                        if any(pattern in href for pattern in exclude_patterns):
                            continue

                        if href not in article_urls and href not in page_article_urls and href != source['base_url'] and href != source['base_url'] + '/':
                            page_article_urls.append(href)

                elif source_key == 'ortho_spine_news':
                    # Look for article links on homepage
                    article_links = []

                    # Try to find article containers
                    for article_elem in soup.find_all(['article', 'div'], class_=lambda x: x and ('post' in x.lower() or 'article' in x.lower() or 'entry' in x.lower())):
                        link = article_elem.find('a', href=True)
                        if link:
                            article_links.append(link)

                    # If no article containers found, look for links in h2/h3 tags
                    if not article_links:
                        for heading in soup.find_all(['h2', 'h3']):
                            link = heading.find('a', href=True)
                            if link:
                                article_links.append(link)

                    # Process found links
                    for link in article_links:
                        href = link['href']
                        # Make absolute URL if relative
                        if not href.startswith('http'):
                            if href.startswith('/') and not href.startswith('//'):
                                href = source['base_url'] + href
                            elif href.startswith('./'):
                                href = source['base_url'] + href[1:]
                            else:
                                href = source['base_url'] + '/' + href

                        # IMPORTANT: Only include URLs from the same domain
                        if not href.startswith(source['base_url']):
                            continue

                        # Exclude common non-article pages
                        exclude_patterns = ['/category/', '/tag/', '/author/', '/about', '/contact', '/privacy', '/terms', '/page/']
                        if any(pattern in href for pattern in exclude_patterns):
                            continue

                        if href not in article_urls and href not in page_article_urls and href != source['base_url'] and href != source['base_url'] + '/':
                            page_article_urls.append(href)

                elif source_key == 'beckers_spine':
                    # Becker's Spine Review specific scraping
                    article_links = []

                    # Try to find article containers
                    for article_elem in soup.find_all(['article', 'div'], class_=lambda x: x and ('post' in x.lower() or 'article' in x.lower() or 'entry' in x.lower())):
                        link = article_elem.find('a', href=True)
                        if link:
                            article_links.append(link)

                    # If no article containers found, look for links in h2/h3 tags
                    if not article_links:
                        for heading in soup.find_all(['h2', 'h3', 'h4']):
                            link = heading.find('a', href=True)
                            if link:
                                article_links.append(link)

                    # Process found links
                    for link in article_links:
                        href = link['href']
                        # Make absolute URL if relative
                        if not href.startswith('http'):
                            if href.startswith('/') and not href.startswith('//'):
                                href = source['base_url'] + href
                            elif href.startswith('./'):
                                href = source['base_url'] + href[1:]
                            else:
                                href = source['base_url'] + '/' + href

                        # IMPORTANT: Only include URLs from the same domain
                        if not href.startswith(source['base_url']):
                            continue

                        # Exclude common non-article pages
                        exclude_patterns = ['/category/', '/tag/', '/author/', '/about', '/contact', '/privacy', '/terms', '/advertise', '/page/', '/spine/', '/spinal-tech/', '/spine-leaders/']
                        if any(pattern in href for pattern in exclude_patterns):
                            continue

                        if href not in article_urls and href not in page_article_urls and href != source['base_url'] and href != source['base_url'] + '/':
                            page_article_urls.append(href)

                # Add page articles to total list
                article_urls.extend(page_article_urls)
                print(f"    Found {len(page_article_urls)} articles on page {page} (total: {len(article_urls)})")

                # If no articles found on this page, we've likely reached the end
                if len(page_article_urls) == 0:
                    print(f"  No more articles found at page {page}")
                    break

                page += 1

            except requests.exceptions.RequestException as e:
                print(f"  Error fetching page {page}: {e}")
                break
            except Exception as e:
                print(f"  Error parsing page {page}: {e}")
                break

        print(f"Found {len(article_urls)} total article URLs from {source['name']}")
        return article_urls[:limit]

    def scrape_article(self, url: str) -> Dict:
        '''
        Scrape a single article from the given URL and return structured data.

        Args:
            url: The URL of the article to scrape

        Returns:
            Dictionary containing article data in the specified format
        '''
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Detect source
            source_key = self.detect_source(url)
            if source_key and source_key in self.sources:
                website_name = self.sources[source_key]['name']
            else:
                website_name = "Unknown Source"

            # Extract title
            title_tag = soup.find('h1', class_='entry-title') or soup.find('h1') or soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else ""

            # Add source suffix if not present
            if title and website_name not in title:
                title = f"{title} - {website_name}"

            category = "industry_news"
            
            # Extract main content
            content = ""
            
            article_tag = soup.find('article')
            if article_tag:
                for tag in article_tag.find_all(['script', 'style', 'nav', 'header', 'footer']):
                    tag.decompose()
                content = article_tag.get_text(separator='\n', strip=True)
            
            if not content:
                content_selectors = [
                    {'class': 'entry-content'},
                    {'class': 'post-content'},
                    {'class': 'article-content'},
                    {'class': 'content'},
                ]
                
                for selector in content_selectors:
                    content_div = soup.find('div', selector)
                    if content_div:
                        for tag in content_div.find_all(['script', 'style']):
                            tag.decompose()
                        content = content_div.get_text(separator='\n', strip=True)
                        break
            
            if not content:
                paragraphs = soup.find_all('p')
                content = '\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            
            content = re.sub(r'\n\s*\n+', '\n', content)
            content = content.strip()
            
            content_length = len(content)
            financial_mentions = self.extract_financial_mentions(content)
            spine_procedures = self.extract_spine_procedures(content)
            scraped_at = datetime.utcnow().isoformat()
            
            result = {
                "title": title,
                "url": url,
                "website_name": website_name,
                "category": category,
                "content": content,
                "content_length": content_length,
                "scraped_at": scraped_at,
                "method": "beautiful_soup",
                "spine_procedures": spine_procedures,
                "financial_mentions": financial_mentions
            }
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching URL {url}: {e}")
            return None
        except Exception as e:
            print(f"Error parsing article from {url}: {e}")
            return None
    
    def scrape_multiple_articles(self, urls: List[str]) -> List[Dict]:
        '''Scrape multiple articles from a list of URLs.'''
        results = []
        
        for i, url in enumerate(urls, 1):
            print(f"Scraping article {i}/{len(urls)}: {url}")
            article_data = self.scrape_article(url)
            
            if article_data:
                results.append(article_data)
                print(f"  ✓ Successfully scraped: {article_data['title'][:60]}...")
            else:
                print(f"  ✗ Failed to scrape: {url}")
        
        return results
    
    def save_to_json(self, data: List[Dict], filename: str):
        '''Save scraped data to a JSON file.'''
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\nSaved {len(data)} articles to {filename}")


if __name__ == "__main__":
    scraper = SpineMarketScraper()
    
    url = "https://thespinemarketgroup.com/johnson-johnson-announces-intent-to-separate-its-orthopaedics-business/"
    
    print("Scraping single article...")
    article_data = scraper.scrape_article(url)
    
    if article_data:
        print("\n" + "="*80)
        print("SCRAPING RESULTS")
        print("="*80)
        print(f"Title: {article_data['title']}")
        print(f"URL: {article_data['url']}")
        print(f"Website: {article_data['website_name']}")
        print(f"Category: {article_data['category']}")
        print(f"Content Length: {article_data['content_length']} characters")
        print(f"Scraped At: {article_data['scraped_at']}")
        print(f"Method: {article_data['method']}")
        print(f"\nSpine Procedures Found ({len(article_data['spine_procedures'])}): {article_data['spine_procedures']}")
        print(f"\nFinancial Mentions Found ({len(article_data['financial_mentions'])}): {article_data['financial_mentions']}")
        print(f"\nContent Preview (first 300 chars):\n{article_data['content'][:300]}...")
        print("="*80)
        
        scraper.save_to_json([article_data], 'output/scraped_article.json')
