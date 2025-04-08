# Manufacturing Operations Hub

A demonstration application that provides two interfaces for manufacturing operations:

1. **MES Insight Chat** - An interactive chatbot for analyzing Manufacturing Execution System (MES) data
2. **Daily Production Meeting** - A structured interface for daily lean meetings and production status reviews

This application is built on a synthetic MES database for an e-bike manufacturing facility and uses Amazon Bedrock for the AI-powered chatbot capabilities.

## Key Features

### MES Insight Chat

- Natural language interface to query MES data
- Interactive conversation with an AI assistant
- Data visualization for query results
- Deep insights into production processes, inventory, quality, and equipment

### Daily Production Meeting

- Structured dashboard for daily production meetings
- Real-time KPIs and production metrics
- Equipment status monitoring
- Quality issue tracking
- Inventory alerts
- Action item management
- Meeting report generation

## Installation

### Prerequisites

- Python 3.9 or higher
- [SQLite](https://www.sqlite.org/download.html)
- AWS account with access to Amazon Bedrock
  - Access to at least one model with support for `Converse` and `Tool use`. See [Supported models and model features](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-supported-models-features.html)

### Setup

1. **Environment Setup**

   If using Amazon SageMaker AI JupyterLab (recommended), you can skip to step 3.

   Create and activate a Python virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **AWS Configuration**

   Configure AWS environment variables by creating a `.env` file:

   ```text
   AWS_REGION="YourRegion" #example us-east-1
   AWS_PROFILE="myprofile" #from ~/.aws/config
   ```

3. **Install Required Packages**

   ```bash
   pip install -r requirements.txt
   ```

4. **Generate the MES Database**

   ```bash
   # Create tables and simulation data (auto-detects if database exists)
   python3 app_factory/data_generator/sqlite-synthetic-mes-data.py --config app_factory/data_generator/data_pools.json --lookback 90 --lookahead 14
   ```

   This will create the database file `mes.db` in the project root directory if it doesn't exist, or refresh the data if it does.

   **Operation Modes**

   The script supports different operation modes:

   ```bash
   # Always create a new database (deletes existing if present)
   python3 app_factory/data_generator/sqlite-synthetic-mes-data.py --mode create

   # Refresh an existing database (errors if database doesn't exist)
   python3 app_factory/data_generator/sqlite-synthetic-mes-data.py --mode refresh

   # Auto-detect what to do based on whether the database exists (default)
   python3 app_factory/data_generator/sqlite-synthetic-mes-data.py --mode auto
   ```

   **Additional Options**

   ```bash
   # Get help on all configuration options
   python3 app_factory/data_generator/sqlite-synthetic-mes-data.py --help
   ```

   Common options include:

   - `--lookback <days>`: Number of days of historical data to generate (default: 90)
   - `--lookahead <days>`: Number of days of future data to generate (default: 14)
   - `--seed <number>`: Random seed for reproducibility (omit for random data each run)
   - `--db <path>`: Custom database file path (default: mes.db)

5. **Run the Application**

   ```bash
   # Start the application
   streamlit run app_factory/app.py
   ```

## Using the Application

Once the application is running, you can choose between:

### Application - MES Insight Chat

In the MES Chat interface, you can:

1. Ask questions about production data in natural language
2. Select example questions from predefined categories
3. View query results in tabular or chart format
4. Download data as CSV

Example questions:

- "What's our current production schedule for the next week?"
- "Which inventory items are below their reorder level?"
- "What's the OEE for our Frame Welding machines?"
- "Show me the most common defect types and their severity"

### Application - Daily Production Meeting

The Production Meeting dashboard includes:

1. **Production Summary** - KPIs, completion rates, and current work orders
2. **Equipment Status** - Machine availability and upcoming maintenance
3. **Quality Issues** - Defect rates and quality metrics
4. **Inventory Alerts** - Items below reorder level
5. **Productivity** - Employee and shift performance
6. **Action Items** - Track and manage action items
7. **Meeting Notes** - Document discussions and decisions
8. **Reports** - Generate meeting summaries and weekly reports

The meeting interface is designed for daily lean meetings, shift handovers, or production status reviews.

## Project Structure

```text
app_factory/
├── app.py                      # Main entry point
├── shared/                     # Shared utilities
│   ├── __init__.py
│   ├── database.py             # Database access
│   └── bedrock_utils.py        # Amazon Bedrock client
├── mes_chat/                   # MES Chat application
│   ├── __init__.py
│   └── app.py                  # Chat interface
├── production_meeting/         # Production Meeting application
│   ├── __init__.py
│   ├── app.py                  # Main dashboard
│   ├── dashboards.py           # Production dashboards
│   ├── action_tracker.py       # Action item management
│   └── report.py               # Meeting report generation
├── data_generator/             # Database generator
│   ├── __init__.py
│   ├── sqlite-synthetic-mes-data.py  # MES database generator
│   ├── refresh-mes-data.py     # Refresh data
│   └── data_pools.json         # Configuration for database generator
└── data/                       # Data files
    ├── sample_questions.json   # Example questions
    └── meeting_templates.json  # Meeting templates
```

## Database Schema

The MES database includes tables for:

- Products (e-bikes, components, and parts)
- Work Orders (production jobs with schedules and status)
- Inventory (raw materials, components, and stock levels)
- Work Centers (manufacturing areas)
- Machines (equipment with efficiency metrics)
- Quality Control (inspection results, defects)
- Material Consumption (component usage tracking)
- Downtime Events (machine issues and reasons)
- OEE Metrics (Overall Equipment Effectiveness)
- Employees (operators, technicians, managers)

## AWS Configuration

This application uses Amazon Bedrock for natural language understanding and AI capabilities. For the list of supported models, see [Supported models and model features](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-supported-models-features.html) and filter by models that support both **Converse API** and **Tool use**, such as:

- Claude 3, 3.5, 3.7 (Haiku, Sonnet, Opus)
- Amazon Nova (Micro, Lite, Pro)
- Other models that support the Converse API and tool use

Ensure your AWS account has access to these models and appropriate permissions. See [Add or remove access to Amazon Bedrock foundation models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html) for detailed instructions.

## Customization

### Adding Custom Questions

Edit `data/sample_questions.json` to add your own example questions.

### Meeting Templates

Modify `data/meeting_templates.json` to create custom meeting templates.

### Database Customization

The database is generated using `data_generator/sqlite-synthetic-mes-data.py` and leveraging the data from `data_generator/data_pools.json`. You can modify this script to create different products, work centers, or other manufacturing elements.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Frameworks and tools used

- Data generation uses the Faker library for creating realistic synthetic data
- Visualizations are powered by Plotly
- UI is built with Streamlit
- AI capabilities provided by Amazon Bedrock
