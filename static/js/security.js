/**
 * Security Utilities - XSS Prevention
 * 
 * Provides utilities to safely render user-generated content
 * and prevent Cross-Site Scripting (XSS) attacks.
 */

/**
 * Escapes HTML special characters to prevent XSS.
 * 
 * Use this function when setting textContent would alter formatting,
 * but you still need to display user-generated content safely.
 * 
 * @param {string} text - Potentially unsafe user input
 * @returns {string} HTML-escaped safe string
 * 
 * @example
 * const userInput = "<script>alert('xss')</script>";
 * element.innerHTML = escapeHtml(userInput);
 * // Results in: &lt;script&gt;alert('xss')&lt;/script&gt;
 */
function escapeHtml(text) {
    if (!text) return '';

    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Safely sets innerHTML by escaping user-generated content.
 * 
 * Preferred method for rendering dynamic content.
 * Always use textContent when possible, this when formatting is needed.
 * 
 * @param {HTMLElement} element - Target element
 * @param {string} html - HTML template
 * @param {Object} data - Data object with values to escape
 * 
 * @example
 * safeInnerHTML(div, '<h4>{title}</h4><p>{summary}</p>', {
 *   title: article.title,  // Will be escaped
 *   summary: article.summary  // Will be escaped
 * });
 */
function safeInnerHTML(element, html, data) {
    let safeHtml = html;

    // Replace all {key} placeholders with escaped values
    for (const [key, value] of Object.entries(data)) {
        const escapedValue = escapeHtml(value);
        safeHtml = safeHtml.replace(new RegExp(`{${key}}`, 'g'), escapedValue);
    }

    element.innerHTML = safeHtml;
}

/**
 * Creates a DOM element with safe text content.
 * 
 * Safest method - recommended over innerHTML whenever possible.
 * 
 * @param {string} tag - HTML tag name
 * @param {string} text - Text content (automatically escaped)
 * @param {Object} attributes - Optional attributes to set
 * @returns {HTMLElement} Created element
 * 
 * @example
 * const heading = createSafeElement('h4', article.title, {
 *   class: 'article-title',
 *   'data-id': article.id
 * });
 */
function createSafeElement(tag, text, attributes = {}) {
    const element = document.createElement(tag);
    element.textContent = text;  // Safe - no HTML parsing

    for (const [key, value] of Object.entries(attributes)) {
        element.setAttribute(key, value);
    }

    return element;
}

/**
 * Validates and sanitizes URL to prevent javascript: protocol injection.
 * 
 * @param {string} url - URL to validate
 * @returns {string} Sanitized URL or '#' if invalid
 * 
 * @example
 * element.href = sanitizeUrl(userProvidedUrl);
 */
function sanitizeUrl(url) {
    if (!url) return '#';

    const trimmed = url.trim().toLowerCase();

    // Block dangerous protocols
    const dangerousProtocols = ['javascript:', 'data:', 'vbscript:'];
    for (const protocol of dangerousProtocols) {
        if (trimmed.startsWith(protocol)) {
            console.warn('Blocked dangerous URL protocol:', url);
            return '#';
        }
    }

    return url;
}

// Export utilities to global scope
window.securityUtils = {
    escapeHtml,
    safeInnerHTML,
    createSafeElement,
    sanitizeUrl
};
