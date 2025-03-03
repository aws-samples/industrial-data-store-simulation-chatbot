# Chatbot To Query Industrial Data Stores Powered by Amazon Bedrock

## Conversational Interface From Industrial Data Stores in Manufacturing: Revolutionizing Data Queries

In the modern manufacturing landscape, data-driven decision-making has become paramount. With the advent of Industry 4.0, manufacturing facilities are inundated with vast amounts of data from various sources such as sensors, machines, ERP systems, and more.

Generative AI technologies have made strides in bridging the gap between users and the vast amounts of textual data available. However, their focus has primarily been on text-based information, leaving a gap in accessing and interpreting operational data from complex industrial systems. Integrating these AI capabilities with a natural language interface that connects directly to operational data platforms can simplify this process. By doing so, it becomes easier for all users to access the real-time data needed for critical decision-making, without the need for deep technical expertise.

Navigating this sea of data to extract meaningful insights can be daunting, especially for those without extensive technical expertise in SQL or data analysis. This sample focuses on text-to-sql, but the same pattern can be used to query other industrial databases that may be powered by knowledge graphs, or other data stores.

The following is the high-level diagram of the chatbot that can be deployed with this sample code. It also stores the chat history in-memory.

![MES System Architecture](assets/MES-chatbot-sys-architecture.png)

### Use Cases in Manufacturing

**1. Simplified Access to Complex Data:** A conversational interface enables manufacturing personnel to query complex industrial data stores using simple natural language. For instance, a plant manager could ask, "Show me the production output of Machine A last week," and receive the relevant data without writing a single line of SQL code or have to consult a visualization tool that is tied to a specific system.

**2. Enhanced Operational Efficiency:** By democratizing data access, generative AI reduces the time and effort required to generate reports or analyze production metrics. This swift access to data empowers teams to make informed decisions quickly, enhancing overall operational efficiency.

**3. Proactive Maintenance and Downtime Reduction:** Maintenance teams can use natural language queries to assess the health and performance of equipment, identify potential issues before they escalate, and schedule preventative maintenance, thereby reducing unplanned downtime.

**4. Quality Control:** Quality assurance teams can easily query data related to product quality, defect rates, or batch inconsistencies using natural language, streamlining the quality control process and ensuring product standards are met consistently.

**5. Inventory and Supply Chain Management:** Inventory managers can effortlessly access real-time information about stock levels, reorder points, or supplier performance, optimizing inventory management and supply chain operations without needing to consult external applications or write complex queries.

### The Future is Now

Being able to interact with industrial data stores using natural language is not just futuristic concepts - these tools being integrated into manufacturing operations today. They bridge the gap between complex data systems and end-users, ensuring that actionable insights are just a question away. As we move forward, the adoption of such technologies will continue to grow, further transforming the manufacturing industry into a more efficient, data-savvy, and responsive domain.

## 0. Pre-requisites

This code sample leverages Anthropic Claude models on Amazon Bedrock. See [Model access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) to enable model access. For smaller schemas, Claude 3 Haiku is recommended, for larger more complex ones, use Claude 3 Sonnet. Claude 3 Haiku will improve inference latency and minimize cost, but Claude 3 Sonnet has better reasoning capabilities.

## 1. Environment setup

> Note: If using this sample on `AWS Cloud9` or `Amazon SageMaker Studio JupyterLab` (recommended), you can skip to step #1.2.

The following requires an installation of `python3`.

It is recommended to create a virtualenv

```bash
python3 -m venv .venv
```

After the `init` process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```bash
source .venv/bin/activate
```

You will need access to your AWS environment. See [How to set environment variables](https://docs.aws.amazon.com/sdkref/latest/guide/environment-variables.html) for details.

Create a `.env` file in the root directory and add values for the following

```text
AWS_REGION="YourRegion" #example us-east-1
AWS_PROFILE="myprofile" #from ~/.aws/config
```

### 1.2 Install the required packages

To install the required packages, run the following command:

```bash
pip install -r requirements.txt
```

## 2. Creating the simulated MES

This folder contains scripts to simulate a Manufacturing Execution System (MES) that manages and monitors the production process of an e-bike manufacturing facility. The simulated data provides a realistic foundation for testing and demonstrating SQL-based analytics and reporting capabilities.

## 2.1 Database Structure

The MES database includes tables for:

- **Products**: E-bikes and their components
- **Bill of Materials**: Component relationships and quantities
- **Inventory**: Raw materials and components tracking
- **Suppliers**: External vendor information
- **Work Centers**: Manufacturing areas and their capabilities
- **Machines**: Equipment specifications and maintenance schedules
- **Employees**: Personnel records with roles and skills
- **Work Orders**: Production jobs with schedules and status
- **Quality Control**: Inspection results with defect details
- **Material Consumption**: Component usage tracking
- **Downtimes**: Machine downtime events and reasons
- **OEE Metrics**: Overall Equipment Effectiveness measurements

## 2.2 Creating the Database

To create the database tables and populate them with synthetic data, run:

```bash
# Create tables and simulation data
python3 MES-synthetic-data/sqlite-synthetic-mes-data.py
```

For additional details on how to modify the simulation, use the `--help` argument and consult the simulator detailed info [here](MES-synthetic-data/mes-simulation.md)

## 3. Chatbot Interface

> Disclaimer: The chatbot is designed to operate with this demo database. If using against a real system, make sure that the user connecting the database has read-only access and to implement guardrails that would ensure the database would not get overloaded and apply SQL injection protections.

A demo streamlit application has been built to demonstrate how one can interact with an MES system using a natural language interface by asking questions about the data.

It implements in-memory storage for conversation history and is designed to generate SQL Queries and execute them against the simulated MES. It will automatically retrieve the database metadata (tables, column names, data types, sample data) to allow it to generate accurate queries. If an error is returned during the query, it will attempt to re-write the query based on the error returned. Finally, once it has retrieved the data from the system, it will use this information to answer the original user question.

Since this is built for demo purposes, it also shows intermediary steps in the console and will display the query generated in the chat interface. Processing time is also provided to the user: the time to generate the SQL query and the time to generate the response from the data returned by the query and the original question.

You can use the **reset button** to clear the chat history and ask a new question.

Some sample questions are provided. As this is a demo, the application has been set to show what happens in a more verbose way, so it will also show the specific SQL queries generated, how long it took to execute, and the result set returned from the MES to answer the question.

To start the streamlit app, simply run:

```bash
streamlit run chatbot/Chat.py 
```

> If running this example in AWS Cloud9, append `--server.port 8080` so you can access the streamlit app by clicking `Preview -> Preview Running Application` from the menu at the top of the screen. This way, you can access it securely without exposing any ports to the internet.

> If running this example in Amazon SageMaker Studio JupyterLab, you can access the streamlit app through the proxy on `https://{domainId}.studio.{region}.sagemaker.aws/jupyterlab/default/proxy/{port}/`, e.g. `https://d-abcd12345xyz.studio.us-east-1.sagemaker.aws/jupyterlab/default/proxy/8501/`. Make sure to include the trailing forward slash.

On the sidebar (left-hand side), you can reset the chat to clear the chat history and ask a new question. You can use one of the example questions provided or ask your own in the chat box at the bottom.

![chatbot](assets/chatwithMES.gif)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
