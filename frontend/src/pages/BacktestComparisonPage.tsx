import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { backtestApi, BacktestResult } from '../services/api'
import { format } from 'date-fns'
import { ResultDetailModal } from '../components/ResultDetailModal'

type SortOption = 'executedAt' | 'timeWindow'

export default function BacktestComparisonPage() {
  const [selectedResult, setSelectedResult] = useState<BacktestResult | null>(null)
  const [sortBy, setSortBy] = useState<SortOption>('executedAt')
  const { data: results, isLoading, error, refetch } = useQuery({
    queryKey: ['backtest-results'],
    queryFn: () => backtestApi.getResults(),
    staleTime: 0, // Always consider data stale, refetch on mount
    cacheTime: 0, // Don't cache, always fetch fresh data
    refetchOnWindowFocus: true, // Refetch when window gets focus
    refetchOnMount: true, // Refetch when component mounts
  })

  // Auto-refresh when component mounts (when navigating to this page)
  useEffect(() => {
    refetch()
  }, [refetch])

  // Sort results based on selected option
  const sortedResults = results ? [...results].sort((a, b) => {
    if (sortBy === 'executedAt') {
      // Sort by execution_time (newest first)
      const aTime = a.execution_time ? new Date(a.execution_time).getTime() : 0
      const bTime = b.execution_time ? new Date(b.execution_time).getTime() : 0
      return bTime - aTime // Descending (newest first)
    } else {
      // Sort by time window start (newest first)
      const aStart = a.start ? new Date(a.start).getTime() : 0
      const bStart = b.start ? new Date(b.start).getTime() : 0
      return bStart - aStart // Descending (newest first)
    }
  }) : []

  const downloadResult = async (result: BacktestResult) => {
    try {
      const fullResult = await backtestApi.getResult(result.run_id)
      const blob = new Blob([JSON.stringify(fullResult, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${result.run_id}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Failed to download result:', err)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-white mb-4">Backtest Comparison</h2>
        <div className="bg-dark-surface border border-dark-border rounded-lg overflow-x-auto">
          <table className="min-w-full divide-y divide-dark-border" style={{ minWidth: '1200px' }}>
            <thead className="bg-dark-surface">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider min-w-[200px]">Run ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Mode</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Instrument</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Time Window</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider whitespace-nowrap">Executed At</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Orders</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Fills</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Rejected</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">P&L</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider whitespace-nowrap">Unrealized P&L</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Commissions</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-dark-bg divide-y divide-dark-border">
              {[1, 2, 3].map((i) => (
                <tr key={i} className="animate-pulse">
                  <td className="px-4 py-4"><div className="h-4 bg-gray-700 rounded w-32"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-16"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-20"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-24"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-24"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-12"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-12"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-12"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-16"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-16"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-16"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-20"></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-500 rounded-lg p-4">
        <p className="text-red-400">Error loading results: {String(error)}</p>
      </div>
    )
  }

  if (!results || results.length === 0) {
    return (
      <div className="bg-dark-surface border border-dark-border rounded-lg p-8 text-center">
        <p className="text-gray-400">No backtest results found. Run a backtest to see results here.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-white">Backtest Comparison</h2>
            {results && results.length > 0 && (
              <p className="text-sm text-gray-400 mt-1">
                Showing {results.length} result{results.length !== 1 ? 's' : ''}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <label htmlFor="sort-by" className="text-sm text-gray-400 whitespace-nowrap">
                Sort by:
              </label>
              <select
                id="sort-by"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className="px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="executedAt">Executed At</option>
                <option value="timeWindow">Time Window</option>
              </select>
            </div>
            <button
              onClick={() => refetch()}
              disabled={isLoading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-medium rounded-lg text-sm flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Loading...</span>
                </>
              ) : (
                <>
                  <span>🔄</span>
                  <span>Refresh</span>
                </>
              )}
            </button>
          </div>
        </div>
        <div className="bg-dark-surface border border-dark-border rounded-lg overflow-x-auto">
          <table className="min-w-full divide-y divide-dark-border" style={{ minWidth: '1200px' }}>
            <thead className="bg-dark-surface">
              <tr>
                <th className="px-left text-xs font-medium text-gray-400 uppercase tracking-wider min-w-[200px]">
                  Run ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Mode
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Instrument
                </th>
                <th 
                  className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider cursor-pointer hover:text-white transition-colors ${
                    sortBy === 'timeWindow' ? 'text-blue-400' : 'text-gray-400'
                  }`}
                  onClick={() => setSortBy('timeWindow')}
                >
                  Time Window
                  {sortBy === 'timeWindow' && <span className="ml-1">↓</span>}
                </th>
                <th 
                  className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider cursor-pointer hover:text-white transition-colors ${
                    sortBy === 'executedAt' ? 'text-blue-400' : 'text-gray-400'
                  }`}
                  onClick={() => setSortBy('executedAt')}
                >
                  Executed At
                  {sortBy === 'executedAt' && <span className="ml-1">↓</span>}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Orders
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Fills
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Rejected
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  P&L
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider whitespace-nowrap">
                  Unrealized P&L
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Commissions
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-dark-bg divide-y divide-dark-border">
              {sortedResults.map((result) => {
                const rejectedCount = result.summary?.orders 
                  ? (result.summary.orders - (result.summary.fills || 0))
                  : 0
                const fillRate = result.summary?.orders 
                  ? ((result.summary.fills || 0) / result.summary.orders * 100).toFixed(1)
                  : '0.0'
                
                return (
                <tr key={result.run_id} className="hover:bg-dark-surface cursor-pointer">
                  <td
                    className="px-4 py-4 text-sm text-gray-300 max-w-xs truncate"
                    title={result.run_id}
                    onClick={() => setSelectedResult(result)}
                  >
                    {result.run_id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                      result.mode === 'fast' 
                        ? 'bg-blue-900/50 text-blue-300 border border-blue-700' 
                        : 'bg-purple-900/50 text-purple-300 border border-purple-700'
                    }`}>
                      {result.mode === 'fast' ? '⚡ Fast' : '📊 Report'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                    {result.instrument}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {(() => {
                      try {
                        if (!result.start || !result.end) return <span className="text-gray-500">N/A</span>
                        // Fix malformed ISO format (remove duplicate Z or timezone)
                        let startStr = String(result.start).replace(/\+00:00Z$/, 'Z').replace(/\+00:00$/, 'Z')
                        let endStr = String(result.end).replace(/\+00:00Z$/, 'Z').replace(/\+00:00$/, 'Z')
                        
                        // Parse as UTC explicitly
                        const startDate = new Date(startStr)
                        const endDate = new Date(endStr)
                        if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
                          return <span className="text-gray-500">Invalid date</span>
                        }
                        
                        // Format using UTC components to display UTC time (not local time)
                        const formatUTC = (date: Date) => {
                          const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                          const month = months[date.getUTCMonth()]
                          const day = date.getUTCDate()
                          const hours = date.getUTCHours().toString().padStart(2, '0')
                          const minutes = date.getUTCMinutes().toString().padStart(2, '0')
                          return `${month} ${day}, ${hours}:${minutes}`
                        }
                        
                        const formatUTCTime = (date: Date) => {
                          const hours = date.getUTCHours().toString().padStart(2, '0')
                          const minutes = date.getUTCMinutes().toString().padStart(2, '0')
                          return `${hours}:${minutes}`
                        }
                        
                        return (
                          <>
                            {formatUTC(startDate)} UTC - {formatUTCTime(endDate)} UTC
                          </>
                        )
                      } catch (e) {
                        return <span className="text-gray-500">Error</span>
                      }
                    })()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {(() => {
                      try {
                        if (!result.execution_time) return <span className="text-gray-500">N/A</span>
                        // Parse execution time and format as UTC
                        let execStr = String(result.execution_time).replace(/\+00:00Z$/, 'Z').replace(/\+00:00$/, 'Z')
                        const execDate = new Date(execStr)
                        if (isNaN(execDate.getTime())) {
                          return <span className="text-gray-500">Invalid</span>
                        }
                        
                        // Format using UTC components
                        const formatUTC = (date: Date) => {
                          const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                          const month = months[date.getUTCMonth()]
                          const day = date.getUTCDate()
                          const hours = date.getUTCHours().toString().padStart(2, '0')
                          const minutes = date.getUTCMinutes().toString().padStart(2, '0')
                          return `${month} ${day}, ${hours}:${minutes} UTC`
                        }
                        
                        return formatUTC(execDate)
                      } catch (e) {
                        return <span className="text-gray-500">Error</span>
                      }
                    })()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {result.summary?.orders ?? 0}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    <div className="flex flex-col">
                      <span>{result.summary?.fills ?? 0}</span>
                      <span className="text-xs text-gray-500">({fillRate}%)</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {result.mode === 'report' ? (
                      <span className="text-red-400">{rejectedCount}</span>
                    ) : (
                      <span className="text-gray-500">-</span>
                    )}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                    (result.summary?.pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {(result.summary?.pnl ?? 0).toFixed(2)}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm ${
                    (result.summary?.pnl_breakdown?.unrealized_before_closing ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {(result.summary?.pnl_breakdown?.unrealized_before_closing ?? 0).toFixed(2)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-yellow-400">
                    {(result.summary?.pnl_breakdown?.commissions ?? 0).toFixed(2)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div className="flex gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedResult(result)
                        }}
                        className="text-blue-400 hover:text-blue-300"
                      >
                        View
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          downloadResult(result)
                        }}
                        className="text-green-400 hover:text-green-300"
                      >
                        Download
                      </button>
                    </div>
                  </td>
                </tr>
              )})}
            </tbody>
          </table>
        </div>
      </div>
      {selectedResult && (
        <ResultDetailModal
          result={selectedResult}
          onClose={() => setSelectedResult(null)}
        />
      )}
    </div>
  )
}

