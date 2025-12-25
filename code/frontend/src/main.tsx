import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/globals.css';

// 添加全局错误处理
window.onerror = function(msg, url, line, col, error) {
  console.error('Global error:', msg, url, line, col, error);
  const root = document.getElementById('root');
  if (root) {
    root.innerHTML = `<div style="color: red; padding: 20px;">
      <h2>JavaScript Error</h2>
      <p>${msg}</p>
      <p>Line: ${line}, Col: ${col}</p>
    </div>`;
  }
};

window.onunhandledrejection = function(event) {
  console.error('Unhandled rejection:', event.reason);
};

// 错误边界组件
class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean, error: Error | null}> {
  constructor(props: {children: React.ReactNode}) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('React Error Boundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ color: 'white', padding: '20px', backgroundColor: '#1a1a2e' }}>
          <h2>应用加载出错</h2>
          <p style={{ color: '#ff6b6b' }}>{this.state.error?.message}</p>
          <button 
            onClick={() => window.location.reload()}
            style={{ padding: '10px 20px', marginTop: '10px', cursor: 'pointer' }}
          >
            重新加载
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

console.log('TheatreOS: Starting React app...');

try {
  const rootElement = document.getElementById('root');
  if (!rootElement) {
    throw new Error('Root element not found');
  }
  
  console.log('TheatreOS: Root element found, creating React root...');
  
  const root = ReactDOM.createRoot(rootElement);
  
  console.log('TheatreOS: Rendering App...');
  
  root.render(
    <React.StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </React.StrictMode>
  );
  
  console.log('TheatreOS: App rendered successfully');
} catch (error) {
  console.error('TheatreOS: Failed to render app:', error);
  const root = document.getElementById('root');
  if (root) {
    root.innerHTML = `<div style="color: white; padding: 20px; background: #1a1a2e;">
      <h2>启动失败</h2>
      <p style="color: #ff6b6b;">${error instanceof Error ? error.message : 'Unknown error'}</p>
    </div>`;
  }
}
