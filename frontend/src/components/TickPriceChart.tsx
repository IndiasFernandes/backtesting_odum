import { useMemo } from 'react'
import { ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { parseISO } from 'date-fns'

interface TickData {
  timestamp?: string
  ts_event?: number
  price: number
  size?: number
  amount?: number
}

interface FillData {
  order_id?: string
  id?: string
  timestamp?: string
  price: number
  quantity: number
  amount?: number
  side?: string
}

interface TickPriceChartProps {
  tickData: TickData[]
  fills: FillData[]
}

export function TickPriceChart({ tickData, fills }: TickPriceChartProps) {
  const chartData = useMemo(() => {
    if (!tickData || tickData.length === 0) return []

    // Process tick data - sample if too many points for performance
    const maxPoints = 1000
    const sampleRate = Math.max(1, Math.floor(tickData.length / maxPoints))
    const sampledTicks = tickData.filter((_, index) => index % sampleRate === 0)

    return sampledTicks.map((tick, index) => {
      // Get timestamp from various possible fields
      let timestamp: number
      if (tick.timestamp) {
        timestamp = parseISO(tick.timestamp).getTime()
      } else if (tick.ts_event) {
        // ts_event is typically in nanoseconds, convert to milliseconds
        timestamp = tick.ts_event / 1000000
      } else {
        // Fallback: use index as proxy
        timestamp = Date.now() + (index * 1000)
      }

      const date = new Date(timestamp)
      const timeStr = `${String(date.getUTCHours()).padStart(2, '0')}:${String(date.getUTCMinutes()).padStart(2, '0')}:${String(date.getUTCSeconds()).padStart(2, '0')}.${String(date.getUTCMilliseconds()).padStart(3, '0')}`
      
      return {
        time: timeStr,
        timestamp,
        price: tick.price,
        size: tick.size || tick.amount || 0,
      }
    }).sort((a, b) => a.timestamp - b.timestamp)
  }, [tickData])

  const fillPoints = useMemo(() => {
    if (!fills || fills.length === 0) return []

    return fills.map((fill) => {
      let timestamp: number
      if (fill.timestamp) {
        timestamp = parseISO(fill.timestamp).getTime()
      } else {
        timestamp = Date.now()
      }

      const date = new Date(timestamp)
      const timeStr = `${String(date.getUTCHours()).padStart(2, '0')}:${String(date.getUTCMinutes()).padStart(2, '0')}:${String(date.getUTCSeconds()).padStart(2, '0')}.${String(date.getUTCMilliseconds()).padStart(3, '0')}`
      
      return {
        time: timeStr,
        timestamp,
        price: fill.price,
        quantity: fill.quantity || fill.amount || 0,
        side: fill.side?.toLowerCase() || 'unknown',
        order_id: fill.order_id || fill.id || '',
      }
    }).sort((a, b) => a.timestamp - b.timestamp)
  }, [fills])

  if (chartData.length === 0) {
    return <div className="text-gray-400 text-center py-8">No tick data available</div>
  }

  // Merge fills into chart data - add fill markers directly to tick data points
  const chartDataWithFills = useMemo(() => {
    // Create a map of fills by timestamp (rounded to nearest second for matching)
    const fillsByTime = new Map<string, Array<{ price: number; side: string; quantity: number }>>()
    
    fillPoints.forEach(fill => {
      const fillDate = new Date(fill.timestamp)
      const timeKey = `${String(fillDate.getUTCHours()).padStart(2, '0')}:${String(fillDate.getUTCMinutes()).padStart(2, '0')}:${String(fillDate.getUTCSeconds()).padStart(2, '0')}`
      
      if (!fillsByTime.has(timeKey)) {
        fillsByTime.set(timeKey, [])
      }
      fillsByTime.get(timeKey)!.push({
        price: fill.price,
        side: fill.side,
        quantity: fill.quantity,
      })
    })

    // Add fill markers to chart data
    return chartData.map(tick => {
      const tickTime = tick.time.substring(0, 8) // Extract HH:MM:SS part
      const fillsAtTime = fillsByTime.get(tickTime) || []
      
      const buyFills = fillsAtTime.filter(f => f.side === 'buy')
      const sellFills = fillsAtTime.filter(f => f.side === 'sell')
      
      return {
        ...tick,
        buyFillPrice: buyFills.length > 0 ? buyFills[0].price : null,
        sellFillPrice: sellFills.length > 0 ? sellFills[0].price : null,
        buyFillCount: buyFills.length,
        sellFillCount: sellFills.length,
      }
    })
  }, [chartData, fillPoints])

  return (
    <div className="w-full">
      <h4 className="text-lg font-semibold text-white mb-4">Tick Price with Filled Orders</h4>
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={chartDataWithFills}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis 
            dataKey="time" 
            stroke="#9CA3AF"
            tick={{ fill: '#9CA3AF', fontSize: 10 }}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis 
            stroke="#9CA3AF"
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
            tickFormatter={(value) => value.toFixed(2)}
            domain={['dataMin - 10', 'dataMax + 10']}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1F2937',
              border: '1px solid #374151',
              borderRadius: '8px',
              color: '#F3F4F6',
            }}
            labelStyle={{ color: '#9CA3AF' }}
            formatter={(value: number, name: string) => {
              if (name === 'price') return [value.toFixed(2), 'Price']
              if (name === 'buyFillPrice') return [value.toFixed(2), 'Buy Fill']
              if (name === 'sellFillPrice') return [value.toFixed(2), 'Sell Fill']
              return [value, name]
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#10B981"
            strokeWidth={1.5}
            dot={false}
            name="Tick Price"
          />
          <Line
            type="monotone"
            dataKey="buyFillPrice"
            stroke="#22C55E"
            strokeWidth={4}
            dot={{ fill: '#22C55E', r: 6 }}
            connectNulls={false}
            name="Buy Fills"
          />
          <Line
            type="monotone"
            dataKey="sellFillPrice"
            stroke="#EF4444"
            strokeWidth={4}
            dot={{ fill: '#EF4444', r: 6 }}
            connectNulls={false}
            name="Sell Fills"
          />
        </ComposedChart>
      </ResponsiveContainer>
      <div className="mt-4 flex gap-4 text-sm text-gray-400">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <span>Buy Fills ({fillPoints.filter(f => f.side?.toLowerCase() === 'buy').length})</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-500 rounded-full"></div>
          <span>Sell Fills ({fillPoints.filter(f => f.side?.toLowerCase() === 'sell').length})</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-emerald-500 rounded-full"></div>
          <span>Tick Price</span>
        </div>
      </div>
    </div>
  )
}

