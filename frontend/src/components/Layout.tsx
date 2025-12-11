import { Link, useLocation } from 'react-router-dom'
import { ReactNode, createContext, useContext } from 'react'
import { useToast } from '../hooks/useToast'
import { ToastContainer } from './Toast'

interface LayoutProps {
  children: ReactNode
}

const ToastContext = createContext<ReturnType<typeof useToast> | null>(null)

export function useToastContext() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToastContext must be used within Layout')
  }
  return context
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const toast = useToast()

  const navItems = [
    { path: '/', label: 'Comparison' },
    { path: '/run', label: 'Run Backtest' },
    { path: '/algorithms', label: 'Algorithms' },
    { path: '/definitions', label: 'Definitions' },
  ]

  return (
    <ToastContext.Provider value={toast}>
      <div className="min-h-screen bg-dark-bg">
        <nav className="border-b border-dark-border bg-dark-surface">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <h1 className="text-xl font-bold text-white">Odum Backtesting</h1>
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  {navItems.map((item) => (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        location.pathname === item.path
                          ? 'border-blue-500 text-blue-400'
                          : 'border-transparent text-gray-300 hover:text-gray-100 hover:border-gray-300'
                      }`}
                    >
                      {item.label}
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          {children}
        </main>
        <ToastContainer toasts={toast.toasts} onRemove={toast.removeToast} />
      </div>
    </ToastContext.Provider>
  )
}

