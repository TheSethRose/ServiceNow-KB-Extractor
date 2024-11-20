import requests
import json
from urllib.parse import urljoin
import os
import sys
from requests.exceptions import RequestException
import html2text
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# ServiceNow instance URL, username, and password from environment variables
instance_url = f'https://{os.getenv("SERVICENOW_INSTANCE")}'
username = os.getenv('SERVICENOW_USERNAME')
password = os.getenv('SERVICENOW_PASSWORD')

# Validate environment variables to ensure all required information is provided
if not all([os.getenv("SERVICENOW_INSTANCE"), username, password]):
    print("Error: Missing required environment variables. Please check your .env file.")
    sys.exit(1)

# Base output folder path for saving exported articles
output_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'articles')

# Define API endpoints for ServiceNow tables
kb_bases_endpoint = urljoin(instance_url, '/api/now/table/kb_knowledge_base')
kb_categories_endpoint = urljoin(instance_url, '/api/now/table/kb_category')
articles_endpoint = urljoin(instance_url, '/api/now/table/kb_knowledge')
users_endpoint = urljoin(instance_url, '/api/now/table/sys_user')

# Set headers for API requests
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Get knowledge bases to process based on the filter provided in the environment variables
kb_filter = os.getenv('SERVICENOW_KNOWLEDGE_BASES', '').strip()
selected_kbs = [kb.strip() for kb in kb_filter.split(',')] if kb_filter else []

def make_request(method, url, **kwargs):
    """
    Make an HTTP request with error handling
    :param method: HTTP method (GET, POST, etc.)
    :param url: URL for the request
    :param kwargs: Additional arguments for the request
    :return: JSON response from the request
    """
    # Add basic authentication to request
    kwargs['auth'] = (username, password)

    try:
        # Make the HTTP request
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {instance_url}. Please check your internet connection and the instance URL.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"Error: Request to {url} timed out. Please try again.")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"Error: HTTP request failed: {e}")
        if response.status_code == 401:
            print("Authentication failed. Please check your username and password.")
        elif response.status_code == 403:
            print("Access forbidden. Please check your permissions.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error: An unexpected error occurred: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Received invalid JSON response from {url}")
        sys.exit(1)

def sanitize_filename(filename):
    """
    Sanitize the filename by removing/replacing invalid characters
    :param filename: The original filename
    :return: Sanitized filename
    """
    if not filename:
        return "unnamed"

    # Replace invalid characters with underscores
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Clean up whitespace
    filename = ' '.join(filename.split())  # Replace multiple spaces/newlines with a single space
    filename = filename.strip()  # Remove leading/trailing whitespace

    # Replace remaining problematic characters
    filename = filename.replace('\n', ' ')  # Replace newlines with space
    filename = filename.replace('\t', ' ')  # Replace tabs with space

    # Replace spaces with dashes
    filename = filename.replace(' ', '-')

    # Remove trailing underscores and dashes
    filename = filename.rstrip('_-')

    # Limit filename length (optional, adjust as needed)
    max_length = 100
    if len(filename) > max_length:
        filename = filename[:max_length].strip().rstrip('_-')

    return filename

def create_folder(path):
    """
    Create a folder if it doesn't exist
    :param path: Path to the folder
    """
    if not os.path.exists(path):
        os.makedirs(path)

def convert_html_to_markdown(html_content):
    """
    Convert HTML content to Markdown
    :param html_content: HTML content to be converted
    :return: Converted Markdown content
    """
    h = html2text.HTML2Text()
    h.body_width = 0  # Don't wrap text to keep formatting consistent
    h.ignore_emphasis = False
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_tables = False
    return h.handle(html_content).strip()

def get_user_details(user_sys_id):
    """
    Fetch user details from ServiceNow
    :param user_sys_id: The system ID of the user
    :return: Dictionary containing user's name and sys_id
    """
    if not user_sys_id:
        return {"name": "Unknown", "sys_id": ""}

    try:
        # Make a request to get user details
        response = make_request('GET', f"{users_endpoint}/{user_sys_id}", headers=headers)
        user = response.get('result', {})
        return {
            "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Unknown",
            "sys_id": user_sys_id
        }
    except Exception:
        return {"name": "Unknown", "sys_id": user_sys_id}

def format_article_markdown(article_data, markdown_content, file_path):
    """
    Format article with frontmatter and content in Markdown
    :param article_data: Article data from ServiceNow
    :param markdown_content: Markdown version of the article content
    :param file_path: Path to save the formatted markdown file
    :return: Full formatted article as Markdown
    """
    # Extract and clean up title
    title = (article_data.get('short_description') or article_data.get('title', '')).strip()
    title = ' '.join(title.split())  # Replace multiple spaces/newlines with a single space

    # Get author details using the system ID
    author_sys_id = article_data.get('author', {}).get('value', '')
    author_details = get_user_details(author_sys_id)

    # Extract metadata for the article
    metadata = {
        'title': title,
        'author': author_details['name'],
        'author_sys_id': author_details['sys_id'],
        'created_date': article_data.get('sys_created_on', ''),
        'updated_date': article_data.get('sys_updated_on', ''),
        'views': article_data.get('view_count', 0),
        'rating': article_data.get('rating', ''),
        'knowledge_base': article_data.get('kb_knowledge_base.title', ''),
        'category': article_data.get('kb_category.label', ''),
        'sys_id': article_data.get('sys_id', '')
    }

    # Clean up metadata values (remove leading/trailing spaces)
    metadata = {k: str(v).strip() for k, v in metadata.items() if v}

    # Create frontmatter for the markdown file
    frontmatter = ['---']
    for key, value in metadata.items():
        frontmatter.append(f'{key}: "{value}"')
    frontmatter.append('---')

    # Remove any duplicate title headers from the content
    content_lines = markdown_content.split('\n')
    while content_lines and (
        content_lines[0].strip() == '' or
        content_lines[0].strip().startswith('# ' + metadata['title']) or
        content_lines[0].strip() == metadata['title']
    ):
        content_lines.pop(0)

    # Clean up content by removing multiple blank lines
    cleaned_content = []
    prev_blank = False
    for line in content_lines:
        is_blank = not line.strip()
        if not (is_blank and prev_blank):  # Only add line if we don't have consecutive blanks
            cleaned_content.append(line)
        prev_blank = is_blank

    # Combine frontmatter with cleaned content
    full_content = [
        '\n'.join(frontmatter),
        '',
        f'# {metadata["title"]}',
        '',
        '\n'.join(cleaned_content).strip()
    ]

    return '\n'.join(full_content)

def print_article_content(original_title, sanitized_title, article_data, file_path):
    """
    Save article content to file
    :param original_title: Original article title
    :param sanitized_title: Sanitized version of the article title
    :param article_data: Article data from ServiceNow
    :param file_path: Path to save the article
    """
    # Convert HTML content to Markdown
    markdown_content = convert_html_to_markdown(article_data.get('text', ''))

    # Format full article with frontmatter and Markdown content
    full_markdown = format_article_markdown(article_data, markdown_content, file_path)

    # Save the article to the specified file path
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(full_markdown)

def main():
    try:
        # Create base output folder if it doesn't exist
        create_folder(output_folder)

        print("Starting knowledge base export...")

        # Fetch all knowledge bases from ServiceNow
        print("\nFetching knowledge bases and categories...")
        kb_response = make_request('GET', kb_bases_endpoint, headers=headers)
        knowledge_bases = kb_response.get('result', [])
        if not knowledge_bases:
            print("Warning: No knowledge bases found")
            return

        # Filter knowledge bases if specified
        if selected_kbs:
            print(f"Filtering knowledge bases: {', '.join(selected_kbs)}")
            knowledge_bases = [kb for kb in knowledge_bases if kb.get('title', '').strip() in selected_kbs]
            if not knowledge_bases:
                print("Warning: No matching knowledge bases found")
                return

        # Fetch all categories from ServiceNow
        cat_response = make_request('GET', kb_categories_endpoint, headers=headers)
        categories = {str(cat['sys_id']): cat for cat in cat_response.get('result', [])}

        # Process each knowledge base
        for kb in knowledge_bases:
            try:
                # Sanitize and prepare the knowledge base title and folder
                kb_title = sanitize_filename(kb.get('title', 'Unnamed Knowledge Base'))
                kb_folder = os.path.join(output_folder, kb_title)
                create_folder(kb_folder)
                print(f"\nProcessing knowledge base: {kb_title}")
                print("-" * (len(kb_title) + 24))  # Underline the knowledge base title

                # Get articles for this knowledge base
                kb_articles_params = {'knowledge_base': kb['sys_id']}
                articles_response = make_request('GET', articles_endpoint,
                                              headers=headers,
                                              params=kb_articles_params)
                articles = articles_response.get('result', [])

                if not articles:
                    print(f"No articles found in knowledge base: {kb_title}")
                    continue

                # Process each article in the knowledge base
                for article in articles:
                    try:
                        # Get the article ID
                        article_id = article.get('sys_id')
                        if not article_id:
                            continue

                        # Get the article content with all fields
                        article_api_endpoint = urljoin(instance_url, f'/api/now/table/kb_knowledge/{article_id}')
                        article_response = make_request('GET', article_api_endpoint, headers=headers)
                        article_data = article_response['result']

                        # Extract and sanitize the article title
                        original_title = (article_data.get('short_description') or
                                        article_data.get('title', f'Unnamed Article {article_id}')).strip()
                        article_title = sanitize_filename(original_title)

                        # Determine the category for saving the article
                        category_id = str(article_data.get('kb_category', ''))

                        # Determine the save location based on category
                        if category_id and category_id in categories:
                            category = categories[category_id]
                            category_title = sanitize_filename(category.get('label', 'Unnamed_Category'))
                            category_folder = os.path.join(kb_folder, category_title)
                            create_folder(category_folder)
                            save_folder = category_folder
                            location = f"{kb_title}/{category_title}"
                        else:
                            save_folder = kb_folder
                            location = kb_title

                        # Save the article to the appropriate file path
                        file_path = os.path.join(save_folder, f"{article_title}.md")
                        print(f"→ {location}/{article_title}.mdx")
                        print_article_content(original_title, article_title, article_data, file_path)

                    except KeyError as e:
                        print(f"  Warning: Skipping article due to missing data: {e}")
                        continue

            except KeyError as e:
                print(f"Warning: Error processing knowledge base: {e}")
                continue

        print("\n✓ Knowledge base export completed successfully!")
        print(f"  Articles saved to: {output_folder}")

    except Exception as e:
        print(f"\n✗ Error: An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
