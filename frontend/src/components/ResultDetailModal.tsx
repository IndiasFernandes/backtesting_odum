import { useState, useEffect } from 'react'
import { BacktestResult, backtestApi } from '../services/api'
import { format, parseISO } from 'date-fns'
import { BacktestCharts } from './BacktestCharts'
import { PnLChart } from './PnLChart'
import { TickPriceChart } from './TickPriceChart'

interface ResultDetailModalProps {
  result: BacktestResult | null
  onClose: () => void
}

export function ResultDetailModal({ result, onClose }: ResultDetailModalProps) {
  const [fills, setFills] = useState<Array<{ order_id?: string; id?: string; price: number; quantity?: number; amount?: number; side?: string; timestamp?: string }>>([])
  const [rejectedOrders, setRejectedOrders] = useState<{
    rejected_orders: Array<{ id: string; side: string; price: number; amount: number; status: string }>
    analysis: any
  } | null>(null)
  const [timeline, setTimeline] = useState<Array<{ ts: string; event: string; data: any }>>([])
  const [tickData, setTickData] = useState<Array<any>>([])
  const [loadingFills, setLoadingFills] = useState(false)
  const [loadingRejected, setLoadingRejected] = useState(false)
  const [loadingTimeline, setLoadingTimeline] = useState(false)
  const [loadingTicks, setLoadingTicks] = useState(false)

  useEffect(() => {
    if (result && result.mode === 'report') {
      // Load fills, rejected orders, and timeline for report mode
      setLoadingFills(true)
      setLoadingRejected(true)
      setLoadingTimeline(true)
      
      backtestApi.getFills(result.run_id)
        .then(setFills)
        .catch(console.error)
        .finally(() => setLoadingFills(false))
      
      backtestApi.getRejectedOrders(result.run_id)
        .then(setRejectedOrders)
        .catch(console.error)
        .finally(() => setLoadingRejected(false))
      
      // Load full report result to get timeline
      backtestApi.getReportResult(result.run_id)
        .then((fullResult) => {
          if (fullResult.timeline) {
            setTimeline(fullResult.timeline)
          }
        })
        .catch(console.error)
        .finally(() => setLoadingTimeline(false))
      
      // Load tick data if available
      setLoadingTicks(true)
      backtestApi.getTickData(result.run_id)
        .then((ticks) => {
          if (Array.isArray(ticks)) {
            setTickData(ticks)
          }
        })
        .catch((err) => {
          console.error('Failed to load tick data:', err)
          // Tick data might not be available for all backtests
        })
        .finally(() => setLoadingTicks(false))
    }
  }, [result])

  if (!result) return null

  const downloadJson = (data: any, filename: string) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-dark-surface border border-dark-border rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-dark-surface border-b border-dark-border p-6 flex justify-between items-center">
          <h2 className="text-2xl font-bold text-white">Backtest Result Details</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl"
          >
            ×
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Summary Section */}
          <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
            <h3 className="text-lg font-semibold text-white mb-4">Summary</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Run ID:</span>
                <span className="text-white ml-2 font-mono text-xs">{result.run_id}</span>
              </div>
              <div>
                <span className="text-gray-400">Instrument:</span>
                <span className="text-white ml-2">{result.instrument}</span>
              </div>
              <div>
                <span className="text-gray-400">Dataset:</span>
                <span className="text-white ml-2">{result.dataset}</span>
              </div>
              <div>
                <span className="text-gray-400">Mode:</span>
                <span className={`ml-2 inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                  result.mode === 'fast' 
                    ? 'bg-blue-900/50 text-blue-300 border border-blue-700' 
                    : 'bg-purple-900/50 text-purple-300 border border-purple-700'
                }`}>
                  {result.mode === 'fast' ? '⚡ Fast' : '📊 Report'}
                </span>
              </div>
              <div className="col-span-2">
                <span className="text-gray-400">Time Window:</span>
                <span className="text-white ml-2">
                  {(() => {
                    try {
                      if (!result.start || !result.end) return 'N/A'
                      let startStr = String(result.start).replace(/\+00:00Z$/, 'Z').replace(/\+00:00$/, 'Z')
                      let endStr = String(result.end).replace(/\+00:00Z$/, 'Z').replace(/\+00:00$/, 'Z')
                      const startDate = new Date(startStr)
                      const endDate = new Date(endStr)
                      if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
                        return 'Invalid date'
                      }
                      const formatUTC = (date: Date) => {
                        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                        const month = months[date.getUTCMonth()]
                        const day = date.getUTCDate()
                        const hours = date.getUTCHours().toString().padStart(2, '0')
                        const minutes = date.getUTCMinutes().toString().padStart(2, '0')
                        const seconds = date.getUTCSeconds().toString().padStart(2, '0')
                        return `${month} ${day}, ${hours}:${minutes}:${seconds} UTC`
                      }
                      return `${formatUTC(startDate)} - ${formatUTC(endDate)}`
                    } catch (e) {
                      return 'Error formatting date'
                    }
                  })()}
                </span>
              </div>
              <div className="col-span-2">
                <span className="text-gray-400">Executed At:</span>
                <span className="text-white ml-2">
                  {(() => {
                    try {
                      if (!result.execution_time) return 'N/A'
                      let execStr = String(result.execution_time).replace(/\+00:00Z$/, 'Z').replace(/\+00:00$/, 'Z')
                      const execDate = new Date(execStr)
                      if (isNaN(execDate.getTime())) {
                        return 'Invalid date'
                      }
                      const formatUTC = (date: Date) => {
                        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                        const month = months[date.getUTCMonth()]
                        const day = date.getUTCDate()
                        const hours = date.getUTCHours().toString().padStart(2, '0')
                        const minutes = date.getUTCMinutes().toString().padStart(2, '0')
                        const seconds = date.getUTCSeconds().toString().padStart(2, '0')
                        return `${month} ${day}, ${hours}:${minutes}:${seconds} UTC`
                      }
                      return formatUTC(execDate)
                    } catch (e) {
                      return 'Error formatting date'
                    }
                  })()}
                </span>
              </div>
            </div>
          </div>

          {/* Performance Metrics */}
          {result.summary && (
            <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
              <h3 className="text-lg font-semibold text-white mb-4">Performance Metrics</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">Orders:</span>
                  <span className="text-white ml-2">{result.summary.orders ?? 0}</span>
                </div>
                <div>
                  <span className="text-gray-400">Fills:</span>
                  <span className="text-white ml-2">{result.summary.fills ?? 0}</span>
                </div>
                <div>
                  <span className="text-gray-400">PnL:</span>
                  <span className={`ml-2 ${(result.summary.pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {(result.summary.pnl ?? 0).toFixed(2)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Max Drawdown:</span>
                  <span className="text-white ml-2">{(result.summary.max_drawdown ?? 0).toFixed(2)}</span>
                </div>
                {result.summary.pnl_breakdown && (
                  <>
                    <div>
                      <span className="text-gray-400">Commissions:</span>
                      <span className="text-yellow-400 ml-2">
                        {(result.summary.pnl_breakdown.commissions ?? 0).toFixed(2)}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-400">Unrealized P&L:</span>
                      <span className={`ml-2 ${
                        (result.summary.pnl_breakdown.unrealized_before_closing ?? 0) >= 0
                          ? 'text-green-400'
                          : 'text-red-400'
                      }`}>
                        {(result.summary.pnl_breakdown.unrealized_before_closing ?? 0).toFixed(2)}
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Order Statistics */}
          {result.summary?.position_stats && (
            <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
              <h3 className="text-lg font-semibold text-white mb-4">Order Statistics</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">Buy Orders:</span>
                  <span className="text-white ml-2">{result.summary.position_stats.buy_orders ?? 0}</span>
                </div>
                <div>
                  <span className="text-gray-400">Buy Quantity:</span>
                  <span className="text-white ml-2">{(result.summary.position_stats.buy_quantity ?? 0).toFixed(6)}</span>
                </div>
                <div>
                  <span className="text-gray-400">Sell Orders:</span>
                  <span className="text-white ml-2">{result.summary.position_stats.sell_orders ?? 0}</span>
                </div>
                <div>
                  <span className="text-gray-400">Sell Quantity:</span>
                  <span className="text-white ml-2">{(result.summary.position_stats.sell_quantity ?? 0).toFixed(6)}</span>
                </div>
                <div>
                  <span className="text-gray-400">Market Orders:</span>
                  <span className="text-white ml-2">{result.summary.position_stats.market_orders ?? 0}</span>
                </div>
                <div>
                  <span className="text-gray-400">Limit Orders:</span>
                  <span className="text-white ml-2">{result.summary.position_stats.limit_orders ?? 0}</span>
                </div>
              </div>
            </div>
          )}

          {/* Performance Charts */}
          {result.mode === 'report' && timeline.length > 0 && (
            <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
              {loadingTimeline ? (
                <div className="text-gray-400">Loading charts...</div>
              ) : (
                <BacktestCharts result={result} timeline={timeline} />
              )}
            </div>
          )}

          {/* PnL Over Time Chart */}
          {result.mode === 'report' && timeline.length > 0 && (
            <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
              {loadingTimeline ? (
                <div className="text-gray-400">Loading PnL chart...</div>
              ) : (
                <PnLChart result={result} timeline={timeline} />
              )}
            </div>
          )}

          {/* Tick Price Chart with Filled Orders */}
          {result.mode === 'report' && tickData.length > 0 && fills.length > 0 && (
            <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
              {loadingTicks || loadingFills ? (
                <div className="text-gray-400">Loading tick chart...</div>
              ) : (
                <TickPriceChart tickData={tickData} fills={fills} />
              )}
            </div>
          )}

          {/* Trade Stats */}
          {result.summary?.trades && (
            <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
              <h3 className="text-lg font-semibold text-white mb-4">Trade Statistics</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">Total Trades:</span>
                  <span className="text-white ml-2">{result.summary.trades.total_trades ?? 0}</span>
                </div>
                <div>
                  <span className="text-gray-400">Win Rate:</span>
                  <span className="text-white ml-2">
                    {(result.summary.trades.win_rate ?? 0).toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Metadata */}
          {result.metadata && (
            <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
              <h3 className="text-lg font-semibold text-white mb-4">Metadata</h3>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="text-gray-400">Config Path:</span>
                  <span className="text-white ml-2 font-mono text-xs">{result.metadata.config_path}</span>
                </div>
                <div>
                  <span className="text-gray-400">Snapshot Mode:</span>
                  <span className="text-white ml-2">{result.metadata.snapshot_mode}</span>
                </div>
                {result.metadata.catalog_root && (
                  <div>
                    <span className="text-gray-400">Catalog Root:</span>
                    <span className="text-white ml-2 font-mono text-xs">{result.metadata.catalog_root}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Fills Section - Report Mode Only */}
          {result.mode === 'report' && (
            <>
              <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
                <h3 className="text-lg font-semibold text-white mb-4">Fills</h3>
                {loadingFills ? (
                  <div className="text-gray-400">Loading fills...</div>
                ) : fills.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-sm text-gray-400 mb-2">
                      Total Fills: <span className="text-white font-medium">{fills.length}</span>
                    </div>
                    <div className="max-h-64 overflow-y-auto">
                      <table className="min-w-full text-xs">
                        <thead className="bg-dark-surface">
                          <tr>
                            <th className="px-3 py-2 text-left text-gray-400">Time</th>
                            <th className="px-3 py-2 text-left text-gray-400">Order ID</th>
                            <th className="px-3 py-2 text-left text-gray-400">Price</th>
                            <th className="px-3 py-2 text-left text-gray-400">Quantity</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-dark-border">
                          {fills.slice(0, 100).map((fill, idx) => {
                            const fillTime = fill.timestamp ? (() => {
                              try {
                                return format(parseISO(fill.timestamp), 'HH:mm:ss.SSS')
                              } catch {
                                return fill.timestamp
                              }
                            })() : 'N/A'
                            return (
                              <tr key={idx}>
                                <td className="px-3 py-2 text-gray-400 font-mono text-xs">{fillTime}</td>
                                <td className="px-3 py-2 text-gray-300 font-mono text-xs">{fill.order_id}</td>
                                <td className="px-3 py-2 text-white">{fill.price.toFixed(2)}</td>
                                <td className="px-3 py-2 text-white">{fill.quantity.toFixed(6)}</td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                      {fills.length > 100 && (
                        <div className="mt-2 text-xs text-gray-500">
                          Showing first 100 of {fills.length} fills
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-gray-400">No fills data available</div>
                )}
              </div>

              {/* Rejected Orders Section */}
              <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
                <h3 className="text-lg font-semibold text-white mb-4">Rejected Orders</h3>
                {loadingRejected ? (
                  <div className="text-gray-400">Loading rejected orders...</div>
                ) : rejectedOrders ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-400">Total Rejected:</span>
                        <span className="text-red-400 ml-2 font-medium">{rejectedOrders.analysis.total_rejected}</span>
                      </div>
                      {rejectedOrders.analysis.by_side && (
                        <>
                          <div>
                            <span className="text-gray-400">Buy Rejected:</span>
                            <span className="text-red-400 ml-2">{rejectedOrders.analysis.by_side.buy}</span>
                          </div>
                          <div>
                            <span className="text-gray-400">Sell Rejected:</span>
                            <span className="text-red-400 ml-2">{rejectedOrders.analysis.by_side.sell}</span>
                          </div>
                        </>
                      )}
                      {rejectedOrders.analysis.price_range && (
                        <div>
                          <span className="text-gray-400">Price Range:</span>
                          <span className="text-white ml-2 text-xs">
                            {rejectedOrders.analysis.price_range.min.toFixed(2)} - {rejectedOrders.analysis.price_range.max.toFixed(2)}
                          </span>
                        </div>
                      )}
                    </div>
                    {rejectedOrders.rejected_orders.length > 0 ? (
                      <div className="mt-4">
                        <div className="text-sm text-gray-400 mb-2">
                          Sample Rejected Orders (showing first 50):
                        </div>
                        <div className="max-h-64 overflow-y-auto">
                          <table className="min-w-full text-xs">
                            <thead className="bg-dark-surface">
                              <tr>
                                <th className="px-3 py-2 text-left text-gray-400">Time</th>
                                <th className="px-3 py-2 text-left text-gray-400">Order ID</th>
                                <th className="px-3 py-2 text-left text-gray-400">Side</th>
                                <th className="px-3 py-2 text-left text-gray-400">Price</th>
                                <th className="px-3 py-2 text-left text-gray-400">Amount</th>
                                <th className="px-3 py-2 text-left text-gray-400">Status</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-dark-border">
                              {rejectedOrders.rejected_orders.slice(0, 50).map((order) => {
                                const orderTime = order.timestamp ? (() => {
                                  try {
                                    return format(parseISO(order.timestamp), 'HH:mm:ss.SSS')
                                  } catch {
                                    return order.timestamp
                                  }
                                })() : 'N/A'
                                return (
                                  <tr key={order.id}>
                                    <td className="px-3 py-2 text-gray-400 font-mono text-xs">{orderTime}</td>
                                    <td className="px-3 py-2 text-gray-300 font-mono text-xs">{order.id}</td>
                                    <td className={`px-3 py-2 ${
                                      order.side === 'buy' ? 'text-green-400' : 'text-red-400'
                                    }`}>
                                      {order.side.toUpperCase()}
                                    </td>
                                    <td className="px-3 py-2 text-white">{order.price?.toFixed(2) || 'N/A'}</td>
                                    <td className="px-3 py-2 text-white">{order.amount?.toFixed(6) || 'N/A'}</td>
                                    <td className="px-3 py-2 text-red-400">{order.status}</td>
                                  </tr>
                                )
                              })}
                            </tbody>
                          </table>
                        </div>
                        {rejectedOrders.rejected_orders.length > 50 && (
                          <div className="mt-2 text-xs text-gray-500">
                            Showing first 50 of {rejectedOrders.rejected_orders.length} rejected orders
                          </div>
                        )}
                        <div className="mt-4 text-xs text-gray-400">
                          <strong>Note:</strong> Orders are typically rejected due to insufficient balance, margin requirements, 
                          or risk limits. In backtesting, rejections often occur when trying to place orders that exceed available 
                          account balance or margin capacity.
                        </div>
                      </div>
                    ) : (
                      <div className="text-gray-400">No rejected orders</div>
                    )}
                  </div>
                ) : (
                  <div className="text-gray-400">No rejected orders data available</div>
                )}
              </div>
            </>
          )}

          {/* Download Buttons */}
          <div className="flex gap-4">
            <button
              onClick={() => downloadJson(result, `${result.run_id}.json`)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
            >
              Download Full Result JSON
            </button>
            {result.summary && (
              <button
                onClick={() => downloadJson(result.summary, `${result.run_id}_summary.json`)}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg"
              >
                Download Summary JSON
              </button>
            )}
            {result.mode === 'report' && fills.length > 0 && (
              <button
                onClick={() => downloadJson(fills, `${result.run_id}_fills.json`)}
                className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg"
              >
                Download Fills JSON
              </button>
            )}
            {result.mode === 'report' && rejectedOrders && rejectedOrders.rejected_orders.length > 0 && (
              <button
                onClick={() => downloadJson(rejectedOrders, `${result.run_id}_rejected_orders.json`)}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg"
              >
                Download Rejected Orders JSON
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

