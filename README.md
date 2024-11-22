# ServiceNow Knowledge Base Extractor

This tool extracts knowledge base articles from a ServiceNow instance and converts them to markdown format for easy reading and processing.

## Features

- Extracts articles from specified knowledge bases
- Maintains folder structure (knowledge base > category > articles)
- Converts HTML content to clean markdown
- Preserves article metadata (author, dates, etc.)
- Handles authentication securely
- Supports filtering specific knowledge bases

## Prerequisites

- Python 3.8 or higher
- Access to a ServiceNow instance
- API credentials with access to knowledge bases

## Installation

1. Clone this repository:

```bash
git clone <repository-url>
cd servicenow-kb-extractor
```

2. Create and activate a virtual environment (recommended):

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

3. Install required packages:

```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` file with your ServiceNow instance details:

```ini
SERVICENOW_INSTANCE=your-instance.service-now.com
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
# Optional: Specify knowledge bases to extract (comma-separated)
SERVICENOW_KNOWLEDGE_BASES=IT,HR and Benefits
```

## Usage

Run the script:

```bash
python extract-articles.py
```

The script will:
1. Connect to your ServiceNow instance
2. Extract specified knowledge bases (or all if none specified)
3. Create an 'articles' folder in the script directory
4. Save all articles as markdown files with metadata

The output structure will be:

```
articles/
├── IT/
│   ├── Security/
│   │   └── What-is-Spam.md
│   └── General/
│       └── About-Windows-10.md
└── HR/
    └── Benefits/
        └── Employee-Benefits.md
```
