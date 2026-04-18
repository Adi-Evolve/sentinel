import { Component } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

/**
 * Error Boundary - Catches JavaScript errors in child components
 * and displays a fallback UI instead of crashing the entire app.
 * 
 * This provides graceful error handling and recovery for production resilience.
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render shows the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log error details for debugging
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  handleRetry = () => {
    // Reset error state to retry rendering
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <AlertTriangle className="error-boundary-icon" />
          <h2>Something Went Wrong</h2>
          <p>
            An unexpected error occurred while rendering this component. 
            This could be due to malformed data or a temporary issue.
          </p>
          
          <details className="error-boundary-details">
            <summary>Technical Details (for debugging)</summary>
            <pre>
              {this.state.error?.toString()}
              {"\n"}
              {this.state.errorInfo?.componentStack}
            </pre>
          </details>

          <button 
            className="error-boundary-retry"
            onClick={this.handleRetry}
          >
            <RefreshCw size={18} />
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * PartialError - Component for graceful degradation
 * Shows a smaller error message when a component fails partially
 * but the rest of the app should remain functional.
 */
export function PartialError({ title = "Component Error", message, onRetry }) {
  return (
    <div className="partial-error">
      <AlertTriangle className="partial-error-icon" size={24} />
      <h4>{title}</h4>
      <p>{message || "Failed to load component data."}</p>
      {onRetry && (
        <button className="partial-error-retry" onClick={onRetry}>
          <RefreshCw size={14} style={{ marginRight: "6px" }} />
          Retry
        </button>
      )}
    </div>
  );
}

/**
 * withErrorBoundary - HOC to wrap components with error boundary
 */
export function withErrorBoundary(Component, fallback = null) {
  return function WrappedComponent(props) {
    return (
      <ErrorBoundary fallback={fallback}>
        <Component {...props} />
      </ErrorBoundary>
    );
  };
}

export default ErrorBoundary;
