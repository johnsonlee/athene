import { createBrowserRouter } from 'react-router-dom';
import { App } from './App';
import { Dashboard } from './components/dashboard/Dashboard';
import { ScreenerPage } from './components/screener/ScreenerPage';
import { StockDetailPage } from './components/detail/StockDetailPage';
import { About } from './components/About';

export const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <App />,
      children: [
        { index: true, element: <Dashboard /> },
        { path: 'screener', element: <ScreenerPage /> },
        { path: 'stock/:ticker', element: <StockDetailPage /> },
        { path: 'about', element: <About /> },
      ],
    },
  ],
  { basename: '/athene' }
);
