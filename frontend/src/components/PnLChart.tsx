import { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { BacktestResult } from '../services/api'
import { parseISO } from 'date-fns'

interface PnLChartProps {
  result: BacktestResult
  timeline: Array<{ ts: string; event: string; data: any }>
}

export function PnLChart({ result, timeline }: PnLChartProps) {
  const chartData = useMemo(() => {
    if (!timeline || timeline.length === 0) return []

    const startingBalance = result.summary?.account?.starting_balance || 1000000
    const totalPnL = result.summary?.pnl || 0
    
    // Process timeline to calculate cumulative PnL over time
    const dataPoints: Array<{
      time: string
      timestamp: number
      cumulativePnL: number
      balance: number
    }> = []

    let cumulativePnL = 0.0
    const startTime = parseISO(timeline[0].ts).getTime()
    const endTime = parseISO(timeline[timeline.length - 1].ts).getTime()
    const duration = endTime - startTime

    // Create time buckets (every 5 seconds for granularity)
    const bucketSize = Math.max(5000, duration / 100) // At least 5 seconds, or divide into 100 buckets
    const buckets: Map<number, number> = new Map()

    // Process fills to estimate PnL progression
    // We'll interpolate PnL based on fill count
    let fillCount = 0
    const totalFills = result.summary?.fills || 1

    for (const event of timeline) {
      if (event.event === 'Order' && event.data?.status === 'filled') {
        fillCount++
      } else if (event.event === 'Fill') {
        fillCount++
      }

      const ts = parseISO(event.ts).getTime()
      const bucketIndex = Math.floor((ts - startTime) / bucketSize)
      
      // Interpolate PnL based on progress
      const progress = fillCount / totalFills
      const estimatedPnL = totalPnL * progress
      
      buckets.set(bucketIndex, estimatedPnL)
    }

    // Convert buckets to data points
    for (let i = 0; i <= Math.floor(duration / bucketSize); i++) {
      const bucketTime = startTime + (i * bucketSize)
      const pnl = buckets.get(i) ?? (i === 0 ? 0 : dataPoints[dataPoints.length - 1]?.cumulativePnL ?? 0)
      
      const date = new Date(bucketTime)
      const timeStr = `${String(date.getUTCHours()).padStart(2, '0')}:${String(date.getUTCMinutes()).padStart(2, '0')}:${String(date.getUTCSeconds()).padStart(2, '0')}`
      
      dataPoints.push({
        time: timeStr,
        timestamp: bucketTime,
        cumulativePnL: pnl,
        balance: startingBalance + pnl,
      })
    }

    return dataPoints
  }, [timeline, result.summary])

  if (chartData.length === 0) {
    return <div className="text-gray-400 text-center py-8">No data available for PnL chart</div>
  }

  return (
    <div className="w-full">
      <h4 className="text-lg font-semibold text-white mb-4">PnL Over Time</h4>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis 
            dataKey="time" 
            stroke="#9CA3AF"
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
          />
          <YAxis 
            stroke="#9CA3AF"
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
            tickFormatter={(value) => value.toFixed(0)}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1F2937',
              border: '1px solid #374151',
              borderRadius: '8px',
              color: '#F3F4F6',
            }}
            labelStyle={{ color: '#9CA3AF' }}
            formatter={(value: number) => [value.toFixed(2), 'PnL']}
          />
          <Area
            type="monotone"
            dataKey="cumulativePnL"
            stroke="#3B82F6"
            fill="#3B82F6"
            fillOpacity={0.3}
            name="Cumulative PnL"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

