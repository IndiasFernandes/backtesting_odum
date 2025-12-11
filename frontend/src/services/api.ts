import axios from 'axios'

// Use relative URL for API calls - Vite proxy will forward to backend
// This works both in development (via Vite proxy) and production (via nginx/reverse proxy)
const API_URL = '' // Empty string means use relative URLs, Vite proxy handles /api/* -> backend:8000

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface BacktestRunRequest {
  instrument: string
  dataset?: string  // Optional - auto-detected from time window
  config: string
  start: string
  end: string
  fast?: boolean
  report?: boolean
  export_ticks?: boolean
  snapshot_mode?: 'trades' | 'book' | 'both'
  data_source?: 'local' | 'gcs' | 'auto'
}

export interface DataCheckRequest {
  instrument_id: string
  start: string
  end: string
  snapshot_mode?: 'trades' | 'book' | 'both'
  data_source?: 'local' | 'gcs' | 'auto'
}

export interface DataCheckResult {
  valid: boolean
  has_trades: boolean
  has_book: boolean
  date: string
  dataset: string
  source: string
  messages: string[]
  errors: string[]
  warnings: string[]
}

export interface BacktestResult {
  run_id: string
  mode: 'fast' | 'report'
  instrument: string
  dataset: string
  start: string
  end: string
  execution_time?: string
  summary: {
    orders: number
    fills: number
    pnl: number
    max_drawdown: number
    pnl_breakdown?: {
      realized: number
      unrealized: number
      unrealized_before_closing: number
      commissions: number
      net: number
    }
    position_stats?: {
      buy_orders: number
      buy_quantity: number
      sell_orders: number
      sell_quantity: number
      market_orders: number
      limit_orders: number
    }
    trades?: {
      total_trades: number
      win_rate: number
      avg_loss_pct?: number
    }
    account?: Record<string, unknown>
    returns?: Record<string, unknown>
    position?: Record<string, unknown>
    drawdown?: Record<string, unknown>
  }
  timeline?: Array<{
    ts: string
    event: string
    data: Record<string, unknown>
  }>
  orders?: Array<{
    id: string
    side: string
    price: number
    amount: number
    status: string
    timestamp?: string
    rejection_reason?: string
  }>
  ticks_path?: string
  metadata: {
    config_path: string
    snapshot_mode: string
    catalog_root?: string
  }
}

export interface VenueInfo {
  code: string
  name: string
  types: string[]
}

export interface VenuesResponse {
  cefi: VenueInfo[]
  tradfi: VenueInfo[]
}

export interface InstrumentTypesResponse {
  venue_code: string
  types: string[]
}

export interface InstrumentInfo {
  symbol: string
  gcs_id: string
  nautilus_id: string
  config_id: string
}

export interface InstrumentsResponse {
  venue_code: string
  product_type: string
  instruments: InstrumentInfo[]
}

export const backtestApi = {
  runBacktest: async (request: BacktestRunRequest): Promise<BacktestResult> => {
    const response = await api.post<BacktestResult>('/api/backtest/run', request)
    return response.data
  },
  runBacktestStream: async (
    request: BacktestRunRequest,
    onLog: (log: string) => void,
    onStep: (step: string) => void,
    onComplete: (result: BacktestResult) => void,
    onError: (error: string) => void
  ): Promise<void> => {
    const response = await fetch('/api/backtest/run/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) {
      throw new Error('No response body reader available')
    }

    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            
            if (data.type === 'log') {
              onLog(data.data)
            } else if (data.type === 'step') {
              onStep(data.data)
            } else if (data.type === 'complete') {
              onComplete(data.data)
              return
            } else if (data.type === 'error') {
              onError(data.data.message || 'Unknown error')
              return
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e, line)
          }
        }
      }
    }
  },
  run: async (request: BacktestRunRequest): Promise<BacktestResult> => {
    const response = await api.post<BacktestResult>('/api/backtest/run', request)
    return response.data
  },

  getResults: async (): Promise<BacktestResult[]> => {
    const response = await api.get<BacktestResult[]>('/api/backtest/results')
    return response.data
  },

  getFastResults: async (): Promise<BacktestResult[]> => {
    const response = await api.get<BacktestResult[]>('/api/backtest/results/fast')
    return response.data
  },

  getReportResults: async (): Promise<BacktestResult[]> => {
    const response = await api.get<BacktestResult[]>('/api/backtest/results/report')
    return response.data
  },

  getResult: async (runId: string): Promise<BacktestResult> => {
    const response = await api.get<BacktestResult>(`/api/backtest/results/${runId}`)
    return response.data
  },

  getReportResult: async (runId: string, timelineLimit: number = 5000, timelineOffset: number = 0): Promise<BacktestResult & {
    timeline_pagination?: {
      total: number
      limit: number
      offset: number
      has_more: boolean
    }
  }> => {
    const response = await api.get<BacktestResult & {
      timeline_pagination?: {
        total: number
        limit: number
        offset: number
        has_more: boolean
      }
    }>(`/api/backtest/results/${runId}/report`, {
      params: { timeline_limit: timelineLimit, timeline_offset: timelineOffset }
    })
    return response.data
  },

  getTickData: async (runId: string): Promise<unknown> => {
    const response = await api.get<unknown>(`/api/backtest/results/${runId}/ticks`)
    return response.data
  },

  getFills: async (runId: string, limit: number = 1000, offset: number = 0): Promise<{
    fills: Array<{ order_id?: string; id?: string; price: number; quantity?: number; amount?: number; timestamp?: string }>
    total: number
    limit: number
    offset: number
    has_more: boolean
  }> => {
    const response = await api.get<{
      fills: Array<{ order_id?: string; id?: string; price: number; quantity?: number; amount?: number; timestamp?: string }>
      total: number
      limit: number
      offset: number
      has_more: boolean
    }>(`/api/backtest/results/${runId}/fills`, {
      params: { limit, offset }
    })
    return response.data
  },

  getRejectedOrders: async (runId: string, limit: number = 1000, offset: number = 0): Promise<{
    rejected_orders: Array<{ id: string; side: string; price: number; amount: number; status: string; timestamp?: string }>
    analysis: {
      total_rejected: number
      by_side: { buy: number; sell: number }
      price_range?: { min: number; max: number; avg: number }
    }
    total: number
    limit: number
    offset: number
    has_more: boolean
  }> => {
    const response = await api.get(`/api/backtest/results/${runId}/rejected-orders`, {
      params: { limit, offset }
    })
    return response.data
  },

  checkDataAvailability: async (request: DataCheckRequest): Promise<DataCheckResult> => {
    const response = await api.post<DataCheckResult>('/api/backtest/check-data', request)
    return response.data
  },

  getDatasets: async (): Promise<string[]> => {
    const response = await api.get<string[]>('/api/datasets')
    return response.data
  },

  getConfigs: async (): Promise<string[]> => {
    const response = await api.get<string[]>('/api/configs')
    return response.data
  },

  getConfig: async (configName: string): Promise<Record<string, unknown>> => {
    const response = await api.get<Record<string, unknown>>(`/api/configs/${configName}`)
    return response.data
  },

  saveConfig: async (name: string, config: Record<string, unknown>): Promise<void> => {
    await api.post('/api/configs', { name, config })
  },
  
  getVenues: async (): Promise<VenuesResponse> => {
    const response = await api.get<VenuesResponse>('/api/instruments/venues')
    return response.data
  },
  
  getInstrumentTypes: async (venueCode: string): Promise<InstrumentTypesResponse> => {
    const response = await api.get<InstrumentTypesResponse>(`/api/instruments/types/${venueCode}`)
    return response.data
  },
  
  getInstruments: async (venueCode: string, productType: string): Promise<InstrumentsResponse> => {
    const response = await api.get<InstrumentsResponse>(`/api/instruments/list/${venueCode}/${productType}`)
    return response.data
  },
}

export default api

