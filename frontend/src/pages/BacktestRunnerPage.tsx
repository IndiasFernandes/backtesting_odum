import { useState, useEffect, useRef } from 'react'
import { backtestApi, BacktestRunRequest } from '../services/api'

export default function BacktestRunnerPage() {
  // Pre-fill with example values for Binance Futures May 23, 19:23-19:28 UTC
  const [formData, setFormData] = useState<BacktestRunRequest>({
    instrument: 'BTCUSDT',
    dataset: 'day-2023-05-23',
    config: 'external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json',
    start: '2023-05-23T19:23',
    end: '2023-05-23T19:28',
    fast: false,
    report: false,
    export_ticks: false,
    snapshot_mode: 'both',
  })

  const generateCLI = () => {
    // Format dates for CLI preview (add Z if not present)
    const formatForCLI = (datetimeLocal: string): string => {
      if (!datetimeLocal) return ''
      let clean = datetimeLocal.replace('Z', '')
      if (!clean.includes(':', 13)) {
        clean = clean + ':00'
      }
      return clean + 'Z'
    }
    
    const flags = [
      `--instrument ${formData.instrument}`,
      `--dataset ${formData.dataset}`,
      `--config ${formData.config}`,
      `--start ${formatForCLI(formData.start)}`,
      `--end ${formatForCLI(formData.end)}`,
    ]
    
    if (formData.fast) flags.push('--fast')
    if (formData.report) flags.push('--report')
    if (formData.export_ticks) flags.push('--export_ticks')
    if (formData.snapshot_mode) flags.push(`--snapshot_mode ${formData.snapshot_mode}`)
    
    return `python backend/run_backtest.py ${flags.join(' \\\n  ')}`
  }

  const [isRunning, setIsRunning] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('')
  const [logs, setLogs] = useState<string[]>([])
  const [copied, setCopied] = useState(false)
  const logsEndRef = useRef<HTMLDivElement>(null)
  
  // Auto-scroll logs to bottom when new logs arrive
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs])

  const copyToClipboard = async () => {
    const cliCommand = generateCLI()
    try {
      await navigator.clipboard.writeText(cliCommand)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsRunning(true)
    setError(null)
    setResult(null)
    setStatus('Initializing backtest...')
    setLogs([])
    
    try {
      // Convert datetime-local format (YYYY-MM-DDTHH:mm) to ISO8601 UTC format (YYYY-MM-DDTHH:mm:ssZ)
      // datetime-local doesn't include seconds, so we add :00 if needed
      const formatToISO = (datetimeLocal: string): string => {
        if (!datetimeLocal) return ''
        // Remove any existing Z
        let clean = datetimeLocal.replace('Z', '')
        // If it doesn't have seconds, add :00
        if (!clean.includes(':', 13)) {
          clean = clean + ':00'
        }
        // Add Z for UTC
        return clean + 'Z'
      }
      
      const startISO = formatToISO(formData.start)
      const endISO = formatToISO(formData.end)
      
      // Use streaming endpoint for real-time logs
      await backtestApi.runBacktestStream(
        {
          ...formData,
          start: startISO,
          end: endISO,
        },
        // onLog callback - receives log lines in real-time
        (log: string) => {
          setLogs(prev => [...prev, log])
        },
        // onStep callback - receives step updates in real-time
        (step: string) => {
          setStatus(step)
        },
        // onComplete callback - receives final result
        (response: any) => {
          setResult(response)
          setStatus('Complete!')
          setIsRunning(false)
          // Clear status after showing success
          setTimeout(() => setStatus(''), 2000)
        },
        // onError callback
        (errorMessage: string) => {
          setStatus('Error occurred')
          setError(errorMessage)
          setIsRunning(false)
        }
      )
    } catch (err: any) {
      setStatus('Error occurred')
      setError(err.message || 'Failed to run backtest')
      setIsRunning(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Run Backtest</h2>
        <div className="bg-blue-900/30 border border-blue-700 rounded-lg p-3 text-sm">
          <div className="text-blue-300 font-medium mb-1">Example Ready to Test:</div>
          <div className="text-blue-200">
            Binance Futures BTCUSDT • May 23, 2023 • 19:23-19:28 UTC
          </div>
        </div>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-dark-surface border border-dark-border rounded-lg p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Instrument
            </label>
            <input
              type="text"
              value={formData.instrument}
              onChange={(e) => setFormData({ ...formData, instrument: e.target.value })}
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white"
              placeholder="BTCUSDT"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Dataset
            </label>
            <input
              type="text"
              value={formData.dataset}
              onChange={(e) => setFormData({ ...formData, dataset: e.target.value })}
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white"
              placeholder="day-2023-05-23"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Config
            </label>
            <input
              type="text"
              value={formData.config}
              onChange={(e) => setFormData({ ...formData, config: e.target.value })}
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white"
              placeholder="external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Start Time (UTC)
              </label>
              <input
                type="datetime-local"
                value={formData.start.replace('Z', '')}
                onChange={(e) => {
                  // datetime-local format: YYYY-MM-DDTHH:mm (no timezone)
                  const value = e.target.value
                  setFormData({ ...formData, start: value })
                }}
                className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                End Time (UTC)
              </label>
              <input
                type="datetime-local"
                value={formData.end.replace('Z', '')}
                onChange={(e) => {
                  // datetime-local format: YYYY-MM-DDTHH:mm (no timezone)
                  const value = e.target.value
                  setFormData({ ...formData, end: value })
                }}
                className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Snapshot Mode
            </label>
            <select
              value={formData.snapshot_mode}
              onChange={(e) => setFormData({ ...formData, snapshot_mode: e.target.value as 'trades' | 'book' | 'both' })}
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white"
            >
              <option value="trades">Trades</option>
              <option value="book">Book</option>
              <option value="both">Both</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.fast}
                onChange={(e) => setFormData({ ...formData, fast: e.target.checked, report: e.target.checked ? false : formData.report })}
                className="mr-2"
              />
              <span className="text-sm text-gray-300">Fast Mode</span>
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.report}
                onChange={(e) => setFormData({ ...formData, report: e.target.checked, fast: e.target.checked ? false : formData.fast })}
                className="mr-2"
              />
              <span className="text-sm text-gray-300">Report Mode</span>
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.export_ticks}
                onChange={(e) => setFormData({ ...formData, export_ticks: e.target.checked })}
                disabled={!formData.report}
                className="mr-2"
              />
              <span className="text-sm text-gray-300">Export Ticks (requires Report Mode)</span>
            </label>
          </div>
        </div>

        <div className="bg-dark-surface border border-dark-border rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold text-white">CLI Preview</h3>
            <button
              type="button"
              onClick={copyToClipboard}
              className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <pre className="bg-dark-bg border border-dark-border rounded p-4 text-sm text-gray-300 overflow-x-auto">
            {generateCLI()}
          </pre>
        </div>

        {(isRunning || logs.length > 0) && (
          <div className="bg-blue-900/30 border border-blue-700 rounded-lg p-4 space-y-4">
            {status && (
              <div className="flex items-center space-x-3">
                {isRunning && (
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-400"></div>
                )}
                <div className="text-blue-300 font-medium">{status}</div>
              </div>
            )}
            
            {logs.length > 0 && (
              <div className="mt-4">
                <div className="text-sm text-blue-200 font-medium mb-2">
                  Logs ({logs.length} lines):
                </div>
                <div className="bg-dark-bg border border-dark-border rounded p-3 max-h-96 overflow-y-auto">
                  <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
                    {logs.map((log, idx) => (
                      <div key={idx} className="mb-1">
                        {log}
                      </div>
                    ))}
                    <div ref={logsEndRef} />
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}

        <button
          type="submit"
          disabled={isRunning}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-medium py-2 px-4 rounded-lg"
        >
          {isRunning ? 'Running Backtest...' : 'Run Backtest'}
        </button>

        {error && (
          <div className="bg-red-900 border border-red-700 rounded-lg p-4 text-red-200">
            <strong>Error:</strong> {error}
          </div>
        )}

        {result && (
          <div className="bg-dark-surface border border-dark-border rounded-lg p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Backtest Results</h3>
            {result.run_id && (
              <div className="mb-4 pb-4 border-b border-dark-border">
                <span className="text-gray-400 text-sm">Run ID:</span>
                <span className="text-white ml-2 font-mono text-sm">{result.run_id}</span>
              </div>
            )}
            <div className="space-y-2 text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-gray-400">Orders:</span>
                  <span className="text-white ml-2">{result.summary?.orders || 0}</span>
                </div>
                <div>
                  <span className="text-gray-400">Fills:</span>
                  <span className="text-white ml-2">{result.summary?.fills || 0}</span>
                </div>
                <div>
                  <span className="text-gray-400">PnL:</span>
                  <span className={`ml-2 ${(result.summary?.pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {result.summary?.pnl?.toFixed(2) || '0.00'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Commissions:</span>
                  <span className="text-white ml-2">{result.summary?.pnl_breakdown?.commissions?.toFixed(2) || '0.00'}</span>
                </div>
              </div>
              {result.summary?.position_stats && (
                <div className="mt-4 pt-4 border-t border-dark-border">
                  <h4 className="text-md font-semibold text-white mb-2">Order Statistics</h4>
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="text-gray-400">Buy Orders:</span>
                      <span className="text-white ml-2">{result.summary.position_stats.buy_orders || 0}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Sell Orders:</span>
                      <span className="text-white ml-2">{result.summary.position_stats.sell_orders || 0}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Market Orders:</span>
                      <span className="text-white ml-2">{result.summary.position_stats.market_orders || 0}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Limit Orders:</span>
                      <span className="text-white ml-2">{result.summary.position_stats.limit_orders || 0}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Total Trades:</span>
                      <span className="text-white ml-2">{result.summary.trades?.total_trades || 0}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Win Rate:</span>
                      <span className="text-white ml-2">{result.summary.trades?.win_rate?.toFixed(2) || '0.00'}%</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </form>
    </div>
  )
}

