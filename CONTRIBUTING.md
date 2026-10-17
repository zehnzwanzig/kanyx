# Contributing

Thank you for contributing to Kanyx.

1. Open an issue describing the bug or change before large work.
2. Create a branch and keep changes focused.
3. Run `python -m unittest discover -s tests -v` from the project root.
4. When modifying database behavior, include a regression test using a temporary workspace.
5. Keep user-visible strings translatable in `i18n.py` (English, German, Spanish, French, Japanese and Korean).
6. Do not commit local databases, exported workspaces, personal attachments, build output, or secrets.
7. Test visual changes with PySide6 on a desktop before asserting they work cross-platform.

Please keep Kanyx offline-first, portable and simple.
