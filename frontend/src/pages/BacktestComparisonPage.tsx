import { useQuery } from '@tanstack/react-query'
import { backtestApi } from '../services/api'
import { format } from 'date-fns'

export default function BacktestComparisonPage() {
  const { data: results, isLoading, error } = useQuery({
    queryKey: ['backtest-results'],
    queryFn: () => backtestApi.getResults(),
    staleTime: 5000, // Consider data fresh for 5 seconds
    cacheTime: 30000, // Keep in cache for 30 seconds
    refetchOnWindowFocus: false, // Don't refetch on window focus
  })

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-white mb-4">Backtest Comparison</h2>
        <div className="bg-dark-surface border border-dark-border rounded-lg overflow-x-auto">
          <table className="min-w-full divide-y divide-dark-border" style={{ minWidth: '1200px' }}>
            <thead className="bg-dark-surface">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider min-w-[200px]">Run ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Instrument</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Time Window</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Orders</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Fills</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">P&L</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider whitespace-nowrap">Unrealized P&L</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Commissions</th>
              </tr>
            </thead>
            <tbody className="bg-dark-bg divide-y divide-dark-border">
              {[1, 2, 3].map((i) => (
                <tr key={i} className="animate-pulse">
                  <td className="px-4 py-4"><div className="h-4 bg-gray-700 rounded w-32"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-20"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-24"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-12"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-12"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-16"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-16"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-700 rounded w-16"></div></td>
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
        <h2 className="text-2xl font-bold text-white mb-4">Backtest Comparison</h2>
        <div className="bg-dark-surface border border-dark-border rounded-lg overflow-x-auto">
          <table className="min-w-full divide-y divide-dark-border" style={{ minWidth: '1200px' }}>
            <thead className="bg-dark-surface">
              <tr>
                <th className="px-left text-xs font-medium text-gray-400 uppercase tracking-wider min-w-[200px]">
                  Run ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Instrument
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Time Window
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Orders
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Fills
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
              </tr>
            </thead>
            <tbody className="bg-dark-bg divide-y divide-dark-border">
              {results.map((result) => (
                <tr key={result.run_id} className="hover:bg-dark-surface">
                  <td className="px-4 py-4 text-sm text-gray-300 max-w-xs truncate" title={result.run_id}>
                    {result.run_id}
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
                        const startDate = new Date(startStr)
                        const endDate = new Date(endStr)
                        if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
                          return <span className="text-gray-500">Invalid date</span>
                        }
                        return (
                          <>
                            {format(startDate, 'MMM dd, HH:mm')} - {format(endDate, 'HH:mm')}
                          </>
                        )
                      } catch (e) {
                        return <span className="text-gray-500">Error</span>
                      }
                    })()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {result.summary?.orders ?? 0}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {result.summary?.fills ?? 0}
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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

