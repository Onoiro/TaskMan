# Contributing to TaskMan

First off, thank you for considering contributing to TaskMan!

## How to contribute

1. Go to the [Issues](https://github.com/Onoiro/TaskMan/issues) tab

2. Find an issue labeled `help wanted` or `good first issue`

3. Leave a comment: "I would like to work on this"
   (so others know the issue is taken)

4. Fork the repository

5. Clone your fork locally

6. Setup the project locally.

For development, use the traditional (non-Docker) setup.
It is simpler and faster for writing and testing code.

- Django dev server restarts automatically when you change files
- SQLite database - no extra setup needed
- DEBUG=True - you see full error details in the browser
- Django Debug Toolbar - panel for inspecting database queries and debugging performance issues

Follow the **Option 2: Traditional Setup** section in README.md.

Docker setup is not needed for development.
You can use it at the end to verify your changes work in a production-like environment - but this is optional.

7. Create a new branch for your feature or bug fix.
It is best to include the issue number in the branch name.
Example: `git checkout -b feature/123-feature-name` or `git checkout -b bugfix/123-fix-name`.

8. Make your changes

9. Run checks locally:
```bash
make lint # must pass with no errors
make test-cov # must pass, coverage must not drop below 95%
```

10. Commit with a clear message that includes the issue number:
```bash
git commit -m "Fix deleted user filter in task list (#123)"
```

11. Push your branch to your fork on GitHub.

12. Open a Pull Request against the `main` branch of the original TaskMan repository.

13. Fill out the Pull Request template and wait for the review.

## What happens after you open a PR

- CI runs automatically: lint + tests on Python 3.12 and 3.13
- The maintainer reviews the PR
- If changes are needed - the maintainer will leave comments
- After approval and CI pass - the PR is merged

## Rules for Code and Pull Requests

To ensure good code quality, please follow these rules:
- **Write Tests:** If you add a new feature, please add tests for it.
- **Pass CI/CD:** Before creating a Pull Request, run tests locally (`make test`) and check code style (`make lint`).
- **Update Documentation:** If your changes affect how the app works, please update the `README.md` file.
- **English Language:** Please write all code comments and commit messages in simple English.
- **Do not change the version number:** Please do not update the version number in your files. The repository maintainer will handle version updates (SemVer) during the release process.
- **Translations (i18n):** TaskMan is a multi-language app. Any new text that a user will see MUST be translatable.

Use `gettext_lazy` for this:

  `from django.utils.translation import gettext_lazy as _`
  
  `my_text = _("Some text here")`

In Django templates:

  `{% load i18n %}`
  
  `<p>{% trans "Some text." %}</p>`

Translations are optional for contributors.
If you can - add translations for your new strings:
1. Run make messages - this finds all new strings
2. Open .po files in the locale/ directory
3. Add translations for each language
4. Run make compile - this applies the translations

If you cannot translate - that is fine. Just make sure all new strings are wrapped with _() or {% trans %}. The maintainer will handle missing translations.

## Questions

If something in the issue description is unclear - ask in the issue comments. The maintainer will clarify.

Thank you for your help!
