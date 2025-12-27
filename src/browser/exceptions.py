"""Browser-related exception definitions."""


class BrowserError(Exception):
    """Base exception for browser operations."""


class BrowserNotFoundError(BrowserError):
    """Exception raised when the specified browser is not installed.

    Raised when the specified browser is not installed on the system.
    """

    def __init__(self, browser: str, available_browsers: list[str] | None = None) -> None:
        """Initialize the exception.

        Args:
            browser: Browser name
            available_browsers: List of available browsers
        """
        self.browser = browser
        self.available_browsers = available_browsers
        message = f"Browser not found: {browser}"
        if available_browsers:
            message += f"\nAvailable browsers: {', '.join(available_browsers[:5])}"
        super().__init__(message)


class BrowserLaunchError(BrowserError):
    """Exception raised when browser launch fails.

    Raised when the browser launch process fails.
    """

    def __init__(self, browser: str, url: str, reason: str) -> None:
        """Initialize the exception.

        Args:
            browser: Browser name
            url: Target URL
            reason: Failure reason
        """
        self.browser = browser
        self.url = url
        self.reason = reason
        super().__init__(f"Failed to launch browser: {browser}, URL: {url}\nReason: {reason}")


class InvalidURLError(BrowserError):
    """Exception raised when URL format is invalid.

    Raised when the URL format is invalid.
    """

    def __init__(self, url: str) -> None:
        """Initialize the exception.

        Args:
            url: Invalid URL
        """
        self.url = url
        super().__init__(f"Invalid URL: {url}\nURL format example: https://www.example.com")


class ElementNotFoundError(BrowserError):
    """Exception raised when an element cannot be found on the page.

    Raised when element location fails after timeout.
    """

    def __init__(self, locator: str, timeout: int | None = None) -> None:
        """Initialize the exception.

        Args:
            locator: The locator string used to find the element
            timeout: Timeout duration in milliseconds
        """
        self.locator = locator
        self.timeout = timeout
        message = f"Element not found: {locator}"
        if timeout:
            message += f" (timeout: {timeout}ms)"
        message += "\nSuggestions:\n- Check if the selector is correct\n- Wait for the page to fully load\n- Increase the timeout value"
        super().__init__(message)


class OperationTimeoutError(BrowserError):
    """Exception raised when a browser automation operation times out.

    Raised when an operation does not complete within the specified time.
    """

    def __init__(self, operation: str, timeout: int) -> None:
        """Initialize the exception.

        Args:
            operation: The operation that timed out
            timeout: Timeout duration in milliseconds
        """
        self.operation = operation
        self.timeout = timeout
        super().__init__(f"Operation timed out: {operation} (timeout: {timeout}ms)")


class ElementNotInteractableError(BrowserError):
    """Exception raised when an element cannot be interacted with.

    Raised when an element is found but cannot be clicked, typed into, etc.
    """

    def __init__(self, locator: str, reason: str) -> None:
        """Initialize the exception.

        Args:
            locator: The element locator
            reason: Reason why the element is not interactable
        """
        self.locator = locator
        self.reason = reason
        super().__init__(f"Element not interactable: {locator}\nReason: {reason}")
