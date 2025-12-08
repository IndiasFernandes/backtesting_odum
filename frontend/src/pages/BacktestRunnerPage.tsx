import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { backtestApi, BacktestRunRequest } from '../services/api'
import { useToastContext } from '../components/Layout'

export default function BacktestRunnerPage() {
  const toast = useToastContext()
  
  // Pre-fill with example values for Binance Futures May 23, 02:00-02:05 UTC (5 minutes)
  const [formData, setFormData] = useState<BacktestRunRequest>({
    instrument: 'BTCUSDT',
    dataset: 'day-2023-05-23',
    config: 'binance_futures_btcusdt_l2_trades_config.json',
    start: '2023-05-23T02:00',
    end: '2023-05-23T02:05',
    fast: false,
    report: true,
    export_ticks: false,
    snapshot_mode: 'both',
  })

  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})

  const { data: datasets } = useQuery({
    queryKey: ['datasets'],
    queryFn: () => backtestApi.getDatasets(),
  })

  const { data: configs } = useQuery({
    queryKey: ['configs'],
    queryFn: () => backtestApi.getConfigs(),
  })

  // Set default values once datasets and configs are loaded
  useEffect(() => {
    if (datasets && datasets.length > 0) {
      // Set to example dataset if available and not already set, otherwise first available
      const currentDataset = formData.dataset
      if (!currentDataset || !datasets.includes(currentDataset)) {
        const defaultDataset = datasets.includes('day-2023-05-23') 
          ? 'day-2023-05-23' 
          : datasets[0]
        setFormData(prev => ({ ...prev, dataset: defaultDataset }))
      }
    }
  }, [datasets, formData.dataset])

  useEffect(() => {
    if (configs && configs.length > 0) {
      // Set to example config if available and not already set, otherwise first available
      const currentConfig = formData.config
      if (!currentConfig || !configs.includes(currentConfig)) {
        const defaultConfig = configs.includes('binance_futures_btcusdt_l2_trades_config.json')
          ? 'binance_futures_btcusdt_l2_trades_config.json'
          : configs[0]
        setFormData(prev => ({ ...prev, config: defaultConfig }))
      }
    }
  }, [configs, formData.config])

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {}

    // Instrument validation
    if (!formData.instrument || formData.instrument.trim() === '') {
      errors.instrument = 'Instrument is required'
    }

    // Dataset validation
    if (!formData.dataset || formData.dataset.trim() === '') {
      errors.dataset = 'Dataset is required'
    } else if (datasets && !datasets.includes(formData.dataset)) {
      errors.dataset = `Dataset "${formData.dataset}" not found. Available: ${datasets.slice(0, 5).join(', ')}${datasets.length > 5 ? '...' : ''}`
    }

    // Config validation
    if (!formData.config || formData.config.trim() === '') {
      errors.config = 'Config is required'
    } else if (configs && !configs.includes(formData.config)) {
      errors.config = `Config "${formData.config}" not found. Available: ${configs.slice(0, 5).join(', ')}${configs.length > 5 ? '...' : ''}`
    }

    // Time validation
    if (!formData.start || !formData.end) {
      if (!formData.start) errors.start = 'Start time is required'
      if (!formData.end) errors.end = 'End time is required'
    } else {
      const startDate = new Date(formData.start + ':00Z')
      const endDate = new Date(formData.end + ':00Z')
      
      if (isNaN(startDate.getTime())) {
        errors.start = 'Invalid start time format'
      }
      if (isNaN(endDate.getTime())) {
        errors.end = 'Invalid end time format'
      }
      if (!isNaN(startDate.getTime()) && !isNaN(endDate.getTime())) {
        if (endDate <= startDate) {
          errors.end = 'End time must be after start time'
        }
        // Check if time window is reasonable (not too long)
        const durationMs = endDate.getTime() - startDate.getTime()
        const durationHours = durationMs / (1000 * 60 * 60)
        if (durationHours > 24) {
          errors.end = 'Time window cannot exceed 24 hours'
        }
        if (durationMs < 60000) {
          errors.end = 'Time window must be at least 1 minute'
        }
      }
    }

    // Mode validation
    if (!formData.fast && !formData.report) {
      errors.mode = 'Either Fast Mode or Report Mode must be selected'
    }

    setValidationErrors(errors)
    return Object.keys(errors).length === 0
  }

  const generateCLI = () => {
    // Format dates for CLI preview (add Z if not present)
    const formatForCLI = (datetimeLocal: string): string => {
      if (!datetimeLocal) return ''
      // Convert datetime-local format to ISO8601 UTC format for CLI
      // datetime-local format: YYYY-MM-DDTHH:mm
      // CLI expects: YYYY-MM-DDTHH:mm:ssZ
      let clean = datetimeLocal.replace('Z', '')
      // Ensure seconds are included (add :00 if missing)
      const timePart = clean.split('T')[1] || ''
      if (timePart && timePart.split(':').length === 2) {
        clean = clean + ':00'
      }
      return clean + 'Z'
    }
    
    // Config path format - use relative path from project root
    // Only add prefix if config doesn't already have it
    const configPath = formData.config.startsWith('external/') 
      ? formData.config 
      : `external/data_downloads/configs/${formData.config}`
    
    const flags = [
      `--instrument ${formData.instrument}`,
      `--dataset ${formData.dataset}`,
      `--config ${configPath}`,
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
    
    // Validate form before submitting
    if (!validateForm()) {
      toast.error('Please fix form errors before submitting')
      return
    }

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
            Binance Futures BTCUSDT • May 23, 2023 • 02:00-02:05 UTC (5 minutes)
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
              onChange={(e) => {
                setFormData({ ...formData, instrument: e.target.value })
                if (validationErrors.instrument) {
                  setValidationErrors({ ...validationErrors, instrument: '' })
                }
              }}
              className={`w-full bg-dark-bg border rounded px-3 py-2 text-white ${
                validationErrors.instrument ? 'border-red-500' : 'border-dark-border'
              }`}
              placeholder="BTCUSDT"
              required
            />
            {validationErrors.instrument && (
              <p className="mt-1 text-sm text-red-400">{validationErrors.instrument}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Dataset
            </label>
            <select
              value={formData.dataset || ''}
              onChange={(e) => {
                setFormData({ ...formData, dataset: e.target.value })
                if (validationErrors.dataset) {
                  setValidationErrors({ ...validationErrors, dataset: '' })
                }
              }}
              className={`w-full bg-dark-bg border rounded px-3 py-2 text-white ${
                validationErrors.dataset ? 'border-red-500' : 'border-dark-border'
              }`}
              required
              disabled={!datasets || datasets.length === 0}
            >
              <option value="">{datasets && datasets.length > 0 ? 'Select dataset' : 'Loading datasets...'}</option>
              {datasets?.map((ds) => (
                <option key={ds} value={ds}>{ds}</option>
              ))}
            </select>
            {validationErrors.dataset && (
              <p className="mt-1 text-sm text-red-400">{validationErrors.dataset}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Config
            </label>
            <select
              value={formData.config || ''}
              onChange={(e) => {
                setFormData({ ...formData, config: e.target.value })
                if (validationErrors.config) {
                  setValidationErrors({ ...validationErrors, config: '' })
                }
              }}
              className={`w-full bg-dark-bg border rounded px-3 py-2 text-white ${
                validationErrors.config ? 'border-red-500' : 'border-dark-border'
              }`}
              required
              disabled={!configs || configs.length === 0}
            >
              <option value="">{configs && configs.length > 0 ? 'Select config' : 'Loading configs...'}</option>
              {configs?.map((cfg) => (
                <option key={cfg} value={cfg}>{cfg}</option>
              ))}
            </select>
            {validationErrors.config && (
              <p className="mt-1 text-sm text-red-400">{validationErrors.config}</p>
            )}
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
                  const value = e.target.value
                  setFormData({ ...formData, start: value })
                  if (validationErrors.start) {
                    setValidationErrors({ ...validationErrors, start: '' })
                  }
                  // Re-validate end time if it exists
                  if (formData.end && validationErrors.end) {
                    validateForm()
                  }
                }}
                className={`w-full bg-dark-bg border rounded px-3 py-2 text-white ${
                  validationErrors.start ? 'border-red-500' : 'border-dark-border'
                }`}
                required
              />
              {validationErrors.start && (
                <p className="mt-1 text-sm text-red-400">{validationErrors.start}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                End Time (UTC)
              </label>
              <input
                type="datetime-local"
                value={formData.end.replace('Z', '')}
                onChange={(e) => {
                  const value = e.target.value
                  setFormData({ ...formData, end: value })
                  if (validationErrors.end) {
                    setValidationErrors({ ...validationErrors, end: '' })
                  }
                  // Re-validate when end time changes
                  setTimeout(() => validateForm(), 100)
                }}
                className={`w-full bg-dark-bg border rounded px-3 py-2 text-white ${
                  validationErrors.end ? 'border-red-500' : 'border-dark-border'
                }`}
                required
              />
              {validationErrors.end && (
                <p className="mt-1 text-sm text-red-400">{validationErrors.end}</p>
              )}
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
            {validationErrors.mode && (
              <p className="text-sm text-red-400">{validationErrors.mode}</p>
            )}
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.fast}
                onChange={(e) => {
                  setFormData({ ...formData, fast: e.target.checked, report: e.target.checked ? false : formData.report })
                  if (validationErrors.mode) {
                    setValidationErrors({ ...validationErrors, mode: '' })
                  }
                }}
                className="mr-2"
              />
              <span className="text-sm text-gray-300">Fast Mode</span>
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.report}
                onChange={(e) => {
                  setFormData({ ...formData, report: e.target.checked, fast: e.target.checked ? false : formData.fast })
                  if (validationErrors.mode) {
                    setValidationErrors({ ...validationErrors, mode: '' })
                  }
                }}
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

