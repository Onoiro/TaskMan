# Contributing to TaskMan

First off, thank you for considering contributing to TaskMan! It is people like you that make open-source tools great.

## How to start
1. **Fork** the repository on GitHub.
2. **Clone** your fork locally.
3. Create a new branch for your feature or bug fix: `git checkout -b feature/your-feature-name`.
4. Setup the project locally. We highly recommend using the Docker setup (See `README.md` for instructions).

## Rules for Code and Pull Requests
To ensure good code quality, please follow these simple rules:
- **Write Tests:** If you add a new feature, please add tests for it.
- **Pass CI/CD:** Before creating a Pull Request, run tests locally (`make test`) and check code style (`make lint`).
- **Update Documentation:** If your changes affect how the app works, please update the `README.md` file.
- **Do not change the version number:** Please do not update the version number in your files. The repository maintainer will handle version updates (SemVer) during the release process.

## Submitting your Pull Request
1. Push your branch to your fork on GitHub.
2. Open a Pull Request against the `main` branch of the original TaskMan repository.
3. Fill out the Pull Request template and wait for the review.

Thank you for your help!
