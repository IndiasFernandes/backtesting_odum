import { useEffect } from 'react'

export type ToastType = 'success' | 'error' | 'info'

export interface Toast {
  id: string
  message: string
  type: ToastType
}

interface ToastProps {
  toast: Toast
  onRemove: (id: string) => void
}

export function ToastComponent({ toast, onRemove }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onRemove(toast.id)
    }, 3000)

    return () => clearTimeout(timer)
  }, [toast.id, onRemove])

  const bgColor = {
    success: 'bg-green-900/90 border-green-700',
    error: 'bg-red-900/90 border-red-700',
    info: 'bg-blue-900/90 border-blue-700',
  }[toast.type]

  const textColor = {
    success: 'text-green-200',
    error: 'text-red-200',
    info: 'text-blue-200',
  }[toast.type]

  return (
    <div
      className={`${bgColor} border rounded-lg p-4 mb-2 shadow-lg flex items-center justify-between min-w-[300px] max-w-[500px]`}
    >
      <p className={textColor}>{toast.message}</p>
      <button
        onClick={() => onRemove(toast.id)}
        className={`${textColor} ml-4 hover:opacity-70`}
      >
        ×
      </button>
    </div>
  )
}

interface ToastContainerProps {
  toasts: Toast[]
  onRemove: (id: string) => void
}

export function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  if (toasts.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-50">
      {toasts.map((toast) => (
        <ToastComponent key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>
  )
}

