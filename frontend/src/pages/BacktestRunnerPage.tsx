import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { backtestApi, BacktestRunRequest, DataCheckResult, InstrumentInfo } from '../services/api'
import { useToastContext } from '../components/Layout'

export default function BacktestRunnerPage() {
  const toast = useToastContext()
  
  // Venue/Instrument selection state
  const [venueCategory, setVenueCategory] = useState<string>('cefi')
  const [selectedVenue, setSelectedVenue] = useState<string>('BINANCE')
  const [selectedProductType, setSelectedProductType] = useState<string>('PERPETUAL')
  const [selectedInstrument, setSelectedInstrument] = useState<string>('BTC-USDT')
  
  // Pre-fill with example values for Binance Futures May 23, 02:00-02:05 UTC (5 minutes)
  const [formData, setFormData] = useState<BacktestRunRequest>({
    instrument: 'BTC-USDT',
    config: '', // Will be auto-generated
    start: '2023-05-25T02:00',
    end: '2023-05-25T02:05',
    fast: false,
    report: true,
    export_ticks: false,
    snapshot_mode: 'both',
    data_source: 'gcs',
  })

  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})
  const [dataValidation, setDataValidation] = useState<DataCheckResult | null>(null)
  const [isCheckingData, setIsCheckingData] = useState(false)

  // Fetch venues
  const { data: venuesData } = useQuery({
    queryKey: ['venues'],
    queryFn: () => backtestApi.getVenues(),
  })

  // Fetch instrument types for selected venue
  const { data: instrumentTypesData } = useQuery({
    queryKey: ['instrumentTypes', selectedVenue],
    queryFn: () => backtestApi.getInstrumentTypes(selectedVenue),
    enabled: !!selectedVenue,
  })

  // Fetch instruments for selected venue and product type
  const { data: instrumentsData } = useQuery({
    queryKey: ['instruments', selectedVenue, selectedProductType],
    queryFn: () => backtestApi.getInstruments(selectedVenue, selectedProductType),
    enabled: !!selectedVenue && !!selectedProductType,
  })

  // Update formData when instrument selection changes
  useEffect(() => {
    if (instrumentsData && selectedInstrument) {
      const instrumentInfo = instrumentsData.instruments.find(
        (inst: InstrumentInfo) => inst.symbol === selectedInstrument
      )
      if (instrumentInfo) {
        setFormData(prev => ({
          ...prev,
          instrument: instrumentInfo.config_id,
        }))
      }
    }
  }, [selectedInstrument, instrumentsData])

  // Reset product type when venue changes
  useEffect(() => {
    if (instrumentTypesData && instrumentTypesData.types.length > 0) {
      // Set to first available type, or PERPETUAL if available
      const preferredType = instrumentTypesData.types.includes('PERPETUAL') 
        ? 'PERPETUAL' 
        : instrumentTypesData.types[0]
      setSelectedProductType(preferredType)
    }
  }, [selectedVenue, instrumentTypesData])

  // Reset instrument when product type changes
  useEffect(() => {
    if (instrumentsData && instrumentsData.instruments.length > 0) {
      // Prefer BTC-USDT if available, otherwise first instrument
      const preferred = instrumentsData.instruments.find((inst: InstrumentInfo) => inst.symbol === 'BTC-USDT')
        || instrumentsData.instruments[0]
      setSelectedInstrument(preferred.symbol)
    }
  }, [selectedProductType, instrumentsData])

  // Real-time data validation when form changes
  useEffect(() => {
    // Wait for instrument to be set (either from formData or from selection)
    const currentInstrumentId = formData.instrument || (instrumentsData && selectedInstrument 
      ? instrumentsData.instruments.find((inst: InstrumentInfo) => inst.symbol === selectedInstrument)?.config_id 
      : '')
    
    if (!formData.start || !formData.end || !currentInstrumentId || !formData.data_source) {
      setDataValidation(null)
      return
    }

    // Debounce validation
    const timeoutId = setTimeout(async () => {
      setIsCheckingData(true)
      try {
        // Format dates for API (add seconds and Z if needed)
        const formatToISO = (datetimeLocal: string): string => {
          if (!datetimeLocal) return ''
          let clean = datetimeLocal.replace('Z', '')
          if (!clean.includes(':', 13)) {
            clean = clean + ':00'
          }
          return clean + 'Z'
        }

        const result = await backtestApi.checkDataAvailability({
          instrument_id: currentInstrumentId,
          start: formatToISO(formData.start),
          end: formatToISO(formData.end),
          snapshot_mode: formData.snapshot_mode || 'both',
          data_source: formData.data_source || 'gcs',
        })
        
        setDataValidation(result)
      } catch (error: any) {
        console.error('Error checking data availability:', error)
        setDataValidation({
          valid: false,
          has_trades: false,
          has_book: false,
          date: '',
          dataset: '',
          source: formData.data_source || 'auto',
          messages: [],
          errors: [`Error checking data: ${error.message || 'Unknown error'}`],
          warnings: [],
        })
      } finally {
        setIsCheckingData(false)
      }
    }, 500) // Debounce 500ms

    return () => clearTimeout(timeoutId)
  }, [formData.start, formData.end, formData.instrument, selectedInstrument, instrumentsData, formData.snapshot_mode, formData.data_source])

  // Re-validate form when dataValidation changes or form data changes
  useEffect(() => {
    if (dataValidation !== null || formData.start || formData.end) {
      // Use setTimeout to avoid calling validateForm during render
      const timeoutId = setTimeout(() => {
        validateForm()
      }, 100)
      return () => clearTimeout(timeoutId)
    }
  }, [dataValidation, formData.start, formData.end, formData.snapshot_mode, formData.instrument, formData.config])

  // Config is now auto-generated from venue/instrument selection
  // No need to auto-select from configs list

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {}

    // Instrument validation
    if (!formData.instrument || formData.instrument.trim() === '') {
      errors.instrument = 'Instrument is required'
    }

    // Data availability validation - only check if dataValidation has been set
    // Don't show errors while checking (isCheckingData) or if validation hasn't run yet
    if (dataValidation && !isCheckingData) {
      if (!dataValidation.valid) {
        if (!dataValidation.has_trades && formData.snapshot_mode !== 'book') {
          errors.data = 'Trades data is required for backtest but not found'
        }
        if (formData.snapshot_mode === 'book' && !dataValidation.has_book) {
          errors.data = 'Book snapshot data is required for snapshot_mode="book" but not found'
        }
        if (formData.snapshot_mode === 'both' && (!dataValidation.has_trades || !dataValidation.has_book)) {
          if (!dataValidation.has_trades) {
            errors.data = 'Trades data is required but not found'
          } else if (!dataValidation.has_book) {
            errors.data = 'Book snapshot data is required but not found'
          }
        }
      }
    }

    // Config validation - now optional, will be auto-generated
    // Config is no longer required as we generate it from venue/instrument selection

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
    if (formData.data_source && formData.data_source !== 'auto') {
      flags.push(`--data_source ${formData.data_source}`)
    }
    // Note: dataset is auto-detected from time window, not included in CLI
    
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
          {/* Venue Category Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Category
            </label>
            <select
              value={venueCategory}
              onChange={(e) => {
                setVenueCategory(e.target.value)
                // Reset venue selection
                const venues = e.target.value === 'cefi' 
                  ? venuesData?.cefi || []
                  : venuesData?.tradfi || []
                if (venues.length > 0) {
                  setSelectedVenue(venues[0].code)
                }
              }}
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white"
            >
              <option value="cefi">CeFi (Crypto)</option>
              <option value="tradfi">TradFi (Traditional Finance)</option>
            </select>
          </div>

          {/* Venue Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Venue
            </label>
            <select
              value={selectedVenue}
              onChange={(e) => setSelectedVenue(e.target.value)}
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white"
              disabled={!venuesData}
            >
              <option value="">Select venue...</option>
              {(venueCategory === 'cefi' ? venuesData?.cefi : venuesData?.tradfi)?.map((venue: any) => (
                <option key={venue.code} value={venue.code}>{venue.name}</option>
              ))}
            </select>
          </div>

          {/* Product Type Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Product Type
            </label>
            <select
              value={selectedProductType}
              onChange={(e) => setSelectedProductType(e.target.value)}
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white"
              disabled={!instrumentTypesData || !selectedVenue}
            >
              <option value="">Select type...</option>
              {instrumentTypesData?.types.map((type: string) => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          {/* Instrument Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Instrument
            </label>
            <select
              value={selectedInstrument}
              onChange={(e) => setSelectedInstrument(e.target.value)}
              className={`w-full bg-dark-bg border rounded px-3 py-2 text-white ${
                validationErrors.instrument ? 'border-red-500' : 'border-dark-border'
              }`}
              disabled={!instrumentsData || !selectedProductType}
              required
            >
              <option value="">Select instrument...</option>
              {instrumentsData?.instruments.map((inst: InstrumentInfo) => (
                <option key={inst.symbol} value={inst.symbol}>
                  {inst.symbol} ({inst.config_id})
                </option>
              ))}
            </select>
            {validationErrors.instrument && (
              <p className="mt-1 text-sm text-red-400">{validationErrors.instrument}</p>
            )}
            {instrumentsData && selectedInstrument && (
              <div className="mt-2 text-xs text-gray-400 space-y-1">
                <div>GCS ID: <span className="font-mono text-gray-300">
                  {instrumentsData.instruments.find((i: InstrumentInfo) => i.symbol === selectedInstrument)?.gcs_id}
                </span></div>
                <div>Nautilus ID: <span className="font-mono text-gray-300">
                  {instrumentsData.instruments.find((i: InstrumentInfo) => i.symbol === selectedInstrument)?.nautilus_id}
                </span></div>
              </div>
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
                  // Don't manually clear errors - let validation system handle it
                  // The useEffect will trigger validation check automatically
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
                  // Don't manually clear errors - let validation system handle it
                  // The useEffect will trigger validation check automatically
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
              onChange={(e) => {
                setFormData({ ...formData, snapshot_mode: e.target.value as 'trades' | 'book' | 'both' })
                // Don't manually clear errors - let validation system handle it
                // The useEffect will trigger validation check automatically
              }}
              className={`w-full bg-dark-bg border rounded px-3 py-2 text-white ${
                validationErrors.data ? 'border-red-500' : 'border-dark-border'
              }`}
            >
              <option value="trades">Trades</option>
              <option value="book">Book</option>
              <option value="both">Both</option>
            </select>
            {dataValidation && (
              <div className="mt-2 space-y-1">
                {isCheckingData && (
                  <p className="text-xs text-gray-400">Checking data availability...</p>
                )}
                {!isCheckingData && dataValidation.valid && (
                  <div className="text-xs">
                    <p className="text-green-400">✅ Data available for {dataValidation.dataset}</p>
                    <p className="text-gray-400 mt-1">
                      Trades: {dataValidation.has_trades ? '✅' : '❌'} | 
                      Book: {dataValidation.has_book ? '✅' : '❌'} | 
                      Source: {dataValidation.source}
                    </p>
                  </div>
                )}
                {!isCheckingData && !dataValidation.valid && (
                  <div className="text-xs">
                    {dataValidation.errors.map((err, idx) => (
                      <p key={idx} className="text-red-400 mb-1">{err}</p>
                    ))}
                    {dataValidation.warnings.map((warn, idx) => (
                      <p key={idx} className="text-yellow-400 mb-1">{warn}</p>
                    ))}
                    {dataValidation.messages.map((msg, idx) => (
                      <p key={idx} className="text-gray-400 mb-1">{msg}</p>
                    ))}
                  </div>
                )}
              </div>
            )}
            {validationErrors.data && (
              <p className="mt-1 text-sm text-red-400">{validationErrors.data}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Data Source
            </label>
            <select
              value={formData.data_source || 'gcs'}
              onChange={(e) => setFormData({ ...formData, data_source: e.target.value as 'local' | 'gcs' })}
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white"
            >
              <option value="gcs">GCS Bucket</option>
              <option value="local">Local Files</option>
            </select>
            <p className="mt-1 text-xs text-gray-400">
              Choose data source: GCS uses cloud bucket, Local uses local files
            </p>
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
          disabled={isRunning || !dataValidation?.valid || Object.keys(validationErrors).length > 0}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-medium py-2 px-4 rounded-lg"
        >
          {isRunning ? 'Running Backtest...' : (!dataValidation?.valid ? 'Fix Validation Errors' : 'Run Backtest')}
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

