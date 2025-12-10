import { useMemo } from 'react'
import { ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { parseISO, format } from 'date-fns'

interface TickData {
  timestamp?: string
  ts_event?: number
  price: number
  size?: number
  amount?: number
}

interface OHLCChartProps {
  tickData?: TickData[]
  timeline?: Array<{ ts: string; event: string; data: any }>
  startTime?: string
  endTime?: string
}

interface OHLCBar {
  time: string
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  isBullish: boolean
}

export function OHLCChart({ tickData, timeline, startTime: startTimeStr, endTime: endTimeStr }: OHLCChartProps) {
  // Process tick data or timeline data into OHLC bars
  const ohlcData = useMemo(() => {
    let processedTicks: Array<{ timestamp: number; price: number; size: number }> = []

    // Determine the time window
    let chartStartTime: number | null = null
    let chartEndTime: number | null = null

    if (startTimeStr && endTimeStr) {
      chartStartTime = parseISO(startTimeStr).getTime()
      chartEndTime = parseISO(endTimeStr).getTime()
    }

    // Process tick data if available
    if (tickData && tickData.length > 0) {
      processedTicks = tickData
        .map((tick) => {
          let timestamp: number
          if (tick.timestamp) {
            timestamp = parseISO(tick.timestamp).getTime()
          } else if (tick.ts_event) {
            timestamp = tick.ts_event / 1_000_000 // Convert nanoseconds to milliseconds
          } else {
            return null as any
          }
          return {
            timestamp,
            price: tick.price,
            size: tick.size || tick.amount || 0,
          }
        })
        .filter((t) => t !== null)
        .sort((a, b) => a.timestamp - b.timestamp)
    }

    // Process timeline Trade events if no tick data
    if (processedTicks.length === 0 && timeline && timeline.length > 0) {
      processedTicks = timeline
        .filter((event) => event.event === 'Trade')
        .map((event) => {
          const timestamp = parseISO(event.ts).getTime()
          const price = event.data?.price || event.data?.last_price || 0
          const size = event.data?.size || event.data?.quantity || event.data?.amount || 0
          return {
            timestamp,
            price,
            size,
          }
        })
        .filter((t) => t.price > 0)
        .sort((a, b) => a.timestamp - b.timestamp)
    }

    if (processedTicks.length === 0) return []

    // Use actual data range if time window not provided
    if (!chartStartTime || !chartEndTime) {
      chartStartTime = processedTicks[0].timestamp
      chartEndTime = processedTicks[processedTicks.length - 1].timestamp
    }

    // Create time buckets (1 second buckets for granularity)
    const bucketSize = 1000 // 1 second in milliseconds
    const buckets: Map<number, {
      open: number | null
      high: number
      low: number
      close: number | null
      volume: number
      timestamps: number[]
    }> = new Map()

    // Initialize buckets for the full time window
    for (let time = chartStartTime; time <= chartEndTime; time += bucketSize) {
      const bucketKey = Math.floor(time / bucketSize)
      buckets.set(bucketKey, {
        open: null,
        high: -Infinity,
        low: Infinity,
        close: null,
        volume: 0,
        timestamps: [],
      })
    }

    // Process ticks into buckets
    processedTicks.forEach((tick) => {
      const bucketKey = Math.floor(tick.timestamp / bucketSize)
      const bucket = buckets.get(bucketKey)
      
      if (bucket) {
        bucket.timestamps.push(tick.timestamp)
        if (bucket.open === null) {
          bucket.open = tick.price
        }
        bucket.high = Math.max(bucket.high, tick.price)
        bucket.low = Math.min(bucket.low, tick.price)
        bucket.close = tick.price
        bucket.volume += tick.size
      }
    })

    // Convert buckets to OHLC bars
    const bars: OHLCBar[] = []
    const sortedBuckets = Array.from(buckets.entries()).sort((a, b) => a[0] - b[0])

    sortedBuckets.forEach(([bucketKey, bucket]) => {
      if (bucket.open === null || bucket.high === -Infinity || bucket.low === Infinity || bucket.close === null) {
        return // Skip empty buckets
      }

      const bucketTime = bucketKey * bucketSize
      bars.push({
        time: format(new Date(bucketTime), 'HH:mm:ss'),
        timestamp: bucketTime,
        open: bucket.open,
        high: bucket.high,
        low: bucket.low,
        close: bucket.close,
        volume: bucket.volume,
        isBullish: bucket.close >= bucket.open,
      })
    })

    // Limit to max 2000 candles for performance
    const maxCandles = 2000
    if (bars.length > maxCandles) {
      const step = Math.ceil(bars.length / maxCandles)
      return bars.filter((_, i) => i % step === 0)
    }

    return bars
  }, [tickData, timeline, startTimeStr, endTimeStr])

  if (ohlcData.length === 0) {
    return (
      <div className="w-full">
        <h4 className="text-lg font-semibold text-white mb-4">OHLC Chart</h4>
        <div className="text-gray-400 text-center py-8">
          <p>No market data available for OHLC chart.</p>
          <p className="text-sm mt-2">Please ensure tick data is exported from the backtest.</p>
        </div>
      </div>
    )
  }

  // Prepare chart data
  const chartData = ohlcData.map((bar, index) => ({
    index,
    time: bar.time,
    timestamp: bar.timestamp,
    open: bar.open,
    high: bar.high,
    low: bar.low,
    close: bar.close,
    volume: bar.volume,
    isBullish: bar.isBullish,
  }))

  // Calculate price domain
  const allPrices = ohlcData.flatMap(bar => [bar.high, bar.low])
  const priceMin = Math.min(...allPrices)
  const priceMax = Math.max(...allPrices)
  const priceRange = priceMax - priceMin
  const priceDomain = [
    priceMin - priceRange * 0.01,
    priceMax + priceRange * 0.01
  ]

  return (
    <div className="w-full">
      <h4 className="text-lg font-semibold text-white mb-4">OHLC Chart</h4>
      <ResponsiveContainer width="100%" height={500}>
        <ComposedChart
          data={chartData}
          margin={{ top: 5, right: 5, bottom: 60, left: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="index"
            type="number"
            scale="linear"
            stroke="#9CA3AF"
            tick={{ fill: '#9CA3AF', fontSize: 10 }}
            tickFormatter={(value) => {
              const bar = chartData[Math.round(value)]
              return bar ? bar.time : ''
            }}
            domain={[0, Math.max(0, chartData.length - 1)]}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis
            yAxisId="y"
            stroke="#9CA3AF"
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
            tickFormatter={(value) => value.toFixed(2)}
            domain={priceDomain}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1F2937',
              border: '1px solid #374151',
              borderRadius: '4px',
              color: '#F3F4F6',
            }}
            formatter={(value: number, name: string) => {
              if (name === 'open' || name === 'high' || name === 'low' || name === 'close') {
                return [value.toFixed(2), name.toUpperCase()]
              }
              return [value, name]
            }}
            labelFormatter={(label) => {
              const bar = chartData[Math.round(label)]
              return bar ? `Time: ${bar.time}` : ''
            }}
          />
          
          {/* High-Low wicks */}
          {chartData.map((bar, index) => (
            <Line
              key={`wick-${index}`}
              yAxisId="y"
              type="linear"
              data={[
                { index: bar.index, price: bar.high },
                { index: bar.index, price: bar.low }
              ]}
              dataKey="price"
              stroke="#9CA3AF"
              strokeWidth={1}
              dot={false}
              connectNulls={true}
              isAnimationActive={false}
              hide={true}
            />
          ))}
          
          {/* Candlestick bodies */}
          {chartData.map((bar, index) => {
            const color = bar.isBullish ? '#22C55E' : '#EF4444'
            const barWidth = Math.max(Math.min(400 / chartData.length, 8), 2)
            return (
              <Line
                key={`body-${index}`}
                yAxisId="y"
                type="linear"
                data={[
                  { index: bar.index, price: Math.min(bar.open, bar.close) },
                  { index: bar.index, price: Math.max(bar.open, bar.close) }
                ]}
                dataKey="price"
                stroke={color}
                strokeWidth={barWidth}
                dot={false}
                connectNulls={true}
                isAnimationActive={false}
                hide={true}
              />
            )
          })}
        </ComposedChart>
      </ResponsiveContainer>
      <div className="mt-4 flex gap-4 text-sm text-gray-400 justify-center">
        <div className="flex items-center gap-2">
          <div className="w-3 h-1 bg-green-500"></div>
          <span>Bullish (Close ≥ Open)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-1 bg-red-500"></div>
          <span>Bearish (Close &lt; Open)</span>
        </div>
      </div>
    </div>
  )
}
