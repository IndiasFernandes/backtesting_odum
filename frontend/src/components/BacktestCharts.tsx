import { useMemo } from 'react'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { BacktestResult } from '../services/api'
import { parseISO } from 'date-fns'

interface BacktestChartsProps {
  result: BacktestResult
  timeline: Array<{ ts: string; event: string; data: any }>
}

export function BacktestCharts({ result, timeline }: BacktestChartsProps) {
  // Process timeline data to create time-series data points
  const chartData = useMemo(() => {
    if (!timeline || timeline.length === 0) return []

    const startingBalance = (result.summary as any)?.account?.starting_balance || 1000000
    const totalPnL = result.summary?.pnl || 0
    
    // Create time buckets (every 10 seconds for better granularity)
    const buckets: Array<{
      time: string
      timestamp: number
      buyOrders: number
      sellOrders: number
      fills: number
      orders: number
      totalFillPrice: number
      fillCount: number
      buyQuantity: number
      sellQuantity: number
    }> = []

    // Track cumulative values
    let cumulativeBuyOrders = 0
    let cumulativeSellOrders = 0
    let cumulativeFills = 0
    let cumulativeOrders = 0
    let cumulativeFillPrice = 0
    let cumulativeFillCount = 0
    let cumulativeBuyQty = 0
    let cumulativeSellQty = 0

    // Use backtest time window if available, otherwise use timeline range
    let startTime: number
    let endTime: number
    
    if (result.start && result.end) {
      try {
        startTime = parseISO(result.start.replace(/\+00:00Z$/, 'Z').replace(/\+00:00$/, 'Z')).getTime()
        endTime = parseISO(result.end.replace(/\+00:00Z$/, 'Z').replace(/\+00:00$/, 'Z')).getTime()
      } catch (e) {
        // Fallback to timeline range
        startTime = parseISO(timeline[0].ts).getTime()
        endTime = parseISO(timeline[timeline.length - 1].ts).getTime()
      }
    } else {
      startTime = parseISO(timeline[0].ts).getTime()
      endTime = parseISO(timeline[timeline.length - 1].ts).getTime()
    }

    // Process timeline events and create buckets
    for (const event of timeline) {
      const ts = event.ts
      const eventDate = parseISO(ts)
      const timestamp = eventDate.getTime()
      
      // Check if we need a new bucket (every 10 seconds or on first event)
      const bucketIndex = Math.floor((timestamp - startTime) / 10000) // 10 second buckets
      
      // Ensure we have enough buckets up to the current event
      while (buckets.length <= bucketIndex) {
        const prevTimestamp = buckets.length > 0 ? buckets[buckets.length - 1].timestamp : startTime
        const newTimestamp = prevTimestamp + 10000
        const newDate = new Date(newTimestamp)
        buckets.push({
          time: `${String(newDate.getUTCHours()).padStart(2, '0')}:${String(newDate.getUTCMinutes()).padStart(2, '0')}:${String(newDate.getUTCSeconds()).padStart(2, '0')}`,
          timestamp: newTimestamp,
          buyOrders: 0,
          sellOrders: 0,
          fills: 0,
          orders: 0,
          totalFillPrice: 0,
          fillCount: 0,
          buyQuantity: 0,
          sellQuantity: 0,
        })
      }

      const bucket = buckets[bucketIndex]

      if (event.event === 'Order') {
        cumulativeOrders++
        bucket.orders++
        const side = event.data?.side?.toLowerCase()
        const amount = event.data?.amount || 0
        const price = event.data?.price || 0
        
        if (side === 'buy') {
          cumulativeBuyOrders++
          bucket.buyOrders++
          cumulativeBuyQty += amount
          bucket.buyQuantity += amount
        } else if (side === 'sell') {
          cumulativeSellOrders++
          bucket.sellOrders++
          cumulativeSellQty += amount
          bucket.sellQuantity += amount
        }
        
        // Check if order is filled
        if (event.data?.status === 'filled') {
          cumulativeFills++
          bucket.fills++
          cumulativeFillCount++
          bucket.fillCount++
          cumulativeFillPrice += price
          bucket.totalFillPrice += price
        }
      } else if (event.event === 'Fill') {
        cumulativeFills++
        bucket.fills++
        cumulativeFillCount++
        bucket.fillCount++
        const fillPrice = event.data?.price || 0
        const fillQty = event.data?.quantity || 0
        cumulativeFillPrice += fillPrice
        bucket.totalFillPrice += fillPrice
        
        const side = event.data?.side?.toLowerCase()
        if (side === 'buy') {
          cumulativeBuyQty += fillQty
          bucket.buyQuantity += fillQty
        } else if (side === 'sell') {
          cumulativeSellQty += fillQty
          bucket.sellQuantity += fillQty
        }
      }

    }

    // Fill in buckets for the entire time window (not just where events occurred)
    const totalBuckets = Math.ceil((endTime - startTime) / 10000)
    while (buckets.length < totalBuckets) {
      const prevTimestamp = buckets.length > 0 ? buckets[buckets.length - 1].timestamp : startTime
      const newTimestamp = prevTimestamp + 10000
      const newDate = new Date(newTimestamp)
      buckets.push({
        time: `${String(newDate.getUTCHours()).padStart(2, '0')}:${String(newDate.getUTCMinutes()).padStart(2, '0')}:${String(newDate.getUTCSeconds()).padStart(2, '0')}`,
        timestamp: newTimestamp,
        buyOrders: 0,
        sellOrders: 0,
        fills: 0,
        orders: 0,
        totalFillPrice: 0,
        fillCount: 0,
        buyQuantity: 0,
        sellQuantity: 0,
      })
    }

    // Convert to chart data format with cumulative values
    let runningBuyOrders = 0
    let runningSellOrders = 0
    let runningFills = 0
    let runningOrders = 0
    let runningFillPrice = 0
    let runningFillCount = 0
    let runningBuyQty = 0
    let runningSellQty = 0

    return buckets.map((bucket, index) => {
      // Accumulate running totals
      runningBuyOrders += bucket.buyOrders
      runningSellOrders += bucket.sellOrders
      runningFills += bucket.fills
      runningOrders += bucket.orders
      runningFillPrice += bucket.totalFillPrice
      runningFillCount += bucket.fillCount
      runningBuyQty += bucket.buyQuantity
      runningSellQty += bucket.sellQuantity
      
      // Interpolate PnL based on progress through timeline
      const progress = buckets.length > 1 ? index / (buckets.length - 1) : 0
      const cumulativePnL = totalPnL * progress
      const balance = startingBalance + cumulativePnL
      
      // Calculate fill rate (cumulative)
      const fillRate = runningOrders > 0 ? (runningFills / runningOrders) * 100 : 0
      
      // Calculate average fill price (cumulative)
      const avgFillPrice = runningFillCount > 0 ? runningFillPrice / runningFillCount : 0

      return {
        time: bucket.time,
        timestamp: bucket.timestamp,
        buyOrders: runningBuyOrders,
        sellOrders: runningSellOrders,
        fills: runningFills,
        orders: runningOrders,
        cumulativePnL,
        balance,
        avgFillPrice,
        fillRate,
        buyQuantity: runningBuyQty,
        sellQuantity: runningSellQty,
      }
    })
  }, [timeline, result.summary])

  if (chartData.length === 0) {
    return (
      <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
        <p className="text-gray-400">No timeline data available for charts</p>
      </div>
    )
  }

  // Calculate domains for better Y-axis alignment
  const priceValues = chartData.map(d => d.avgFillPrice).filter(v => v != null && v > 0 && !isNaN(v))
  const priceMin = priceValues.length > 0 ? Math.min(...priceValues) : 0
  const priceMax = priceValues.length > 0 ? Math.max(...priceValues) : 100
  const priceRange = priceMax - priceMin
  const priceDomain = [
    priceMin - priceRange * 0.02,
    priceMax + priceRange * 0.02
  ]

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white mb-4">Performance Charts</h3>
      
      {/* Chart 1: Order Flow (Buy vs Sell) Over Time */}
      <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
        <h4 className="text-md font-semibold text-white mb-3">Order Flow Over Time (Buy vs Sell)</h4>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              dataKey="time" 
              stroke="#9CA3AF"
              tick={{ fill: '#9CA3AF' }}
              interval="preserveStartEnd"
            />
            <YAxis 
              stroke="#9CA3AF"
              tick={{ fill: '#9CA3AF' }}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', color: '#F3F4F6' }}
            />
            <Legend wrapperStyle={{ color: '#9CA3AF' }} />
            <Bar dataKey="buyOrders" fill="#10B981" name="Buy Orders" />
            <Bar dataKey="sellOrders" fill="#EF4444" name="Sell Orders" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Chart 2: Fill Rate Over Time */}
      <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
        <h4 className="text-md font-semibold text-white mb-3">Fill Rate Over Time</h4>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              dataKey="time" 
              stroke="#9CA3AF"
              tick={{ fill: '#9CA3AF' }}
              interval="preserveStartEnd"
            />
            <YAxis 
              stroke="#9CA3AF"
              tick={{ fill: '#9CA3AF' }}
              domain={[0, 100]}
              tickFormatter={(value) => value + '%'}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', color: '#F3F4F6' }}
              formatter={(value: number) => [value.toFixed(1) + '%', 'Fill Rate']}
            />
            <Legend wrapperStyle={{ color: '#9CA3AF' }} />
            <Line 
              type="monotone" 
              dataKey="fillRate" 
              stroke="#F59E0B" 
              strokeWidth={2}
              name="Fill Rate (%)"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Chart 3: Average Fill Price Over Time */}
      <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
        <h4 className="text-md font-semibold text-white mb-3">Average Fill Price Over Time</h4>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              dataKey="time" 
              stroke="#9CA3AF"
              tick={{ fill: '#9CA3AF' }}
              interval="preserveStartEnd"
            />
            <YAxis 
              stroke="#9CA3AF"
              tick={{ fill: '#9CA3AF' }}
              tickFormatter={(value) => value.toFixed(0)}
              domain={priceDomain}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', color: '#F3F4F6' }}
              formatter={(value: number) => [value.toFixed(2), 'Avg Price']}
            />
            <Legend wrapperStyle={{ color: '#9CA3AF' }} />
            <Line 
              type="monotone" 
              dataKey="avgFillPrice" 
              stroke="#8B5CF6" 
              strokeWidth={2}
              name="Average Fill Price"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

