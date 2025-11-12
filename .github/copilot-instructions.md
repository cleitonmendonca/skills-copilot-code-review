## Security

- Validate input sanitization to practices.
- Search for risks that might expose user data.
- Prefer loading configuration and content from the databases instead of hard coded content. If absolutely necessary, load it from environment or a non-committed config file.


## Code Quality
- Use consistent naming conventions for variables and functions.
- try to reduce code duplication
- Prefer maintainability and readability over optimization.
- If a method is used a lot, try to optimize it for performance.
- Prefer explicit error handling over silent failures.