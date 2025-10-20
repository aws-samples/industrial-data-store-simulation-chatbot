# Contributing Guidelines

Thank you for your interest in contributing to our project. Whether it's a bug report, new feature, correction, or additional
documentation, we greatly value feedback and contributions from our community.

Please read through this document before submitting any issues or pull requests to ensure we have all the necessary
information to effectively respond to your bug report or contribution.


## Reporting Bugs/Feature Requests

We welcome you to use the GitHub issue tracker to report bugs or suggest features.

When filing an issue, please check existing open, or recently closed, issues to make sure somebody else hasn't already
reported the issue. Please try to include as much information as you can. Details like these are incredibly useful:

* A reproducible test case or series of steps
* The version of our code being used
* Any modifications you've made relevant to the bug
* Anything unusual about your environment or deployment


## Development Setup

This project uses `uv` for Python package management. Follow these steps to set up your development environment:

### Prerequisites
- Python 3.9 or higher
- `uv` package manager (install from https://docs.astral.sh/uv/getting-started/installation/)

### Setting up the Development Environment

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd manufacturing-operations-hub
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```
   This will create a virtual environment and install all project dependencies from `pyproject.toml`.

3. **Run the applications:**
   - Main application: `uv run streamlit run app_factory/app.py`
   - MES Chat: `uv run streamlit run app_factory/mes_chat/app.py`
   - Production Meeting: `uv run streamlit run app_factory/production_meeting/app.py`

4. **Generate sample data:**
   ```bash
   uv run python app_factory/data_generator/sqlite-synthetic-mes-data.py
   ```

5. **Start Jupyter notebook (if needed):**
   ```bash
   uv run jupyter notebook
   ```

### Adding Dependencies

When you need to add new dependencies to the project:

- **For runtime dependencies:**
  ```bash
  uv add <package-name>
  ```

- **For development dependencies:**
  ```bash
  uv add --dev <package-name>
  ```

This will automatically update both `pyproject.toml` and `uv.lock` files.

### Running Tests and Development Commands

All Python commands should be run using `uv run` to ensure they execute in the correct environment:

```bash
# Run tests (if available)
uv run pytest

# Run linting (if configured)
uv run flake8

# Run formatting (if configured)
uv run black .

# Any other Python script
uv run python <script-name>.py
```

## Contributing via Pull Requests
Contributions via pull requests are much appreciated. Before sending us a pull request, please ensure that:

1. You are working against the latest source on the *main* branch.
2. You check existing open, and recently merged, pull requests to make sure someone else hasn't addressed the problem already.
3. You open an issue to discuss any significant work - we would hate for your time to be wasted.

To send us a pull request, please:

1. Fork the repository.
2. Modify the source; please focus on the specific change you are contributing. If you also reformat all the code, it will be hard for us to focus on your change.
3. Ensure local tests pass using `uv run` commands.
4. If you add new dependencies, make sure both `pyproject.toml` and `uv.lock` are updated and included in your commit.
5. Commit to your fork using clear commit messages.
6. Send us a pull request, answering any default questions in the pull request interface.
7. Pay attention to any automated CI failures reported in the pull request, and stay involved in the conversation.

### Important Notes for Pull Requests
- When adding dependencies, include both `pyproject.toml` and `uv.lock` changes in your pull request
- Use `uv run` for all Python command execution to ensure consistency
- Test your changes with `uv sync` to verify the environment setup works correctly

GitHub provides additional document on [forking a repository](https://help.github.com/articles/fork-a-repo/) and
[creating a pull request](https://help.github.com/articles/creating-a-pull-request/).


## Finding contributions to work on
Looking at the existing issues is a great way to find something to contribute on. As our projects, by default, use the default GitHub issue labels (enhancement/bug/duplicate/help wanted/invalid/question/wontfix), looking at any 'help wanted' issues is a great place to start.


## Code of Conduct
This project has adopted the [Amazon Open Source Code of Conduct](https://aws.github.io/code-of-conduct).
For more information see the [Code of Conduct FAQ](https://aws.github.io/code-of-conduct-faq) or contact
opensource-codeofconduct@amazon.com with any additional questions or comments.


## Security issue notifications
If you discover a potential security issue in this project we ask that you notify AWS/Amazon Security via our [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/). Please do **not** create a public github issue.


## Licensing

See the [LICENSE](LICENSE) file for our project's licensing. We will ask you to confirm the licensing of your contribution.
