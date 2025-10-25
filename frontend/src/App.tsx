import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { TrendingUp, TrendingDown, Activity, AlertTriangle } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

interface ModelMetrics {
  model: string
  symbol: string
  pnl: number
  daily_pnl: number
  win_rate: number
  max_drawdown: number
  exposure: number
  timestamp: string
}

interface PnLSnapshot {
  model: string
  pnl: number
  timestamp: string
}

interface ChartDataPoint {
  timestamp: string
  chatgpt?: number
  grok?: number
  gemini?: number
  deepseek?: number
}

interface Order {
  id: number
  model: string
  symbol: string
  side: string
  price: number
  qty: number
  fill_qty: number
  status: string
  created_at: string
}

function App() {
  const [chatgptMetrics, setChatgptMetrics] = useState<ModelMetrics | null>(null)
  const [grokMetrics, setGrokMetrics] = useState<ModelMetrics | null>(null)
  const [geminiMetrics, setGeminiMetrics] = useState<ModelMetrics | null>(null)
  const [deepseekMetrics, setDeepseekMetrics] = useState<ModelMetrics | null>(null)
  const [orders, setOrders] = useState<Order[]>([])
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    try {
      const [metricsRes, ordersRes, snapshotsRes] = await Promise.all([
        fetch(`${API_BASE}/pnl?window=daily`),
        fetch(`${API_BASE}/orders`),
        fetch(`${API_BASE}/pnl/snapshots?hours=24`)
      ])

      if (!metricsRes.ok || !ordersRes.ok || !snapshotsRes.ok) {
        throw new Error('Failed to fetch data')
      }

      const metricsData = await metricsRes.json()
      const ordersData = await ordersRes.json()
      const snapshotsData = await snapshotsRes.json()

      const chatgpt = metricsData.metrics?.find((m: ModelMetrics) => m.model === 'chatgpt')
      const grok = metricsData.metrics?.find((m: ModelMetrics) => m.model === 'grok')
      const gemini = metricsData.metrics?.find((m: ModelMetrics) => m.model === 'gemini')
      const deepseek = metricsData.metrics?.find((m: ModelMetrics) => m.model === 'deepseek')

      setChatgptMetrics(chatgpt || null)
      setGrokMetrics(grok || null)
      setGeminiMetrics(gemini || null)
      setDeepseekMetrics(deepseek || null)
      setOrders(ordersData.orders || [])
      
      const snapshots: PnLSnapshot[] = snapshotsData.snapshots || []
      const timestampMap = new Map<string, ChartDataPoint>()
      
      const initialPoint: ChartDataPoint = {
        timestamp: 'Start',
        chatgpt: 0,
        grok: 0,
        gemini: 0,
        deepseek: 0
      }
      
      snapshots.forEach((snapshot) => {
        const timestamp = new Date(snapshot.timestamp).toLocaleTimeString('en-US', { 
          hour: '2-digit', 
          minute: '2-digit' 
        })
        
        if (!timestampMap.has(timestamp)) {
          timestampMap.set(timestamp, { timestamp })
        }
        
        const point = timestampMap.get(timestamp)!
        point[snapshot.model as keyof Omit<ChartDataPoint, 'timestamp'>] = snapshot.pnl
      })
      
      const chartDataArray = [initialPoint, ...Array.from(timestampMap.values()).sort((a, b) => {
        const timeA = new Date(`1970-01-01 ${a.timestamp}`)
        const timeB = new Date(`1970-01-01 ${b.timestamp}`)
        return timeA.getTime() - timeB.getTime()
      })]
      
      setChartData(chartDataArray)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  const ModelCard = ({ metrics, title, color }: { metrics: ModelMetrics | null, title: string, color: string }) => {
    if (!metrics) {
      return (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className={`w-5 h-5 ${color}`} />
              {title}
            </CardTitle>
            <CardDescription>No data available</CardDescription>
          </CardHeader>
        </Card>
      )
    }

    const isProfitable = metrics.daily_pnl >= 0

    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className={`w-5 h-5 ${color}`} />
              {title}
            </div>
            <Badge variant={isProfitable ? "default" : "destructive"}>
              {metrics.symbol}
            </Badge>
          </CardTitle>
          <CardDescription>Real-time performance metrics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">Daily PnL</p>
              <p className={`text-2xl font-bold flex items-center gap-1 ${isProfitable ? 'text-green-600' : 'text-red-600'}`}>
                {isProfitable ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
                ${metrics.daily_pnl.toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Total PnL</p>
              <p className="text-2xl font-bold">${metrics.pnl.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Win Rate</p>
              <p className="text-lg font-semibold">{(metrics.win_rate * 100).toFixed(1)}%</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Max Drawdown</p>
              <p className="text-lg font-semibold text-red-600">{(metrics.max_drawdown * 100).toFixed(2)}%</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Exposure</p>
              <p className="text-lg font-semibold">${metrics.exposure.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Status</p>
              <Badge variant="outline">Active</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-12 h-12 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-lg text-gray-600">Loading trading data...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Grid Trading Battle System</h1>
          <p className="text-gray-600">ChatGPT vs Grok - Multi-Model Grid Trading on Aster Perp</p>
        </div>

        {error && (
          <Alert className="mb-6 border-red-200 bg-red-50">
            <AlertTriangle className="w-4 h-4 text-red-600" />
            <AlertDescription className="text-red-800">{error}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <ModelCard metrics={chatgptMetrics} title="ChatGPT" color="text-blue-600" />
          <ModelCard metrics={grokMetrics} title="Grok" color="text-orange-600" />
          <ModelCard metrics={geminiMetrics} title="Gemini" color="text-purple-600" />
          <ModelCard metrics={deepseekMetrics} title="DeepSeek" color="text-green-600" />
        </div>

        <Tabs defaultValue="comparison" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="comparison">Performance Comparison</TabsTrigger>
            <TabsTrigger value="orders">Order Flow</TabsTrigger>
            <TabsTrigger value="grid">Grid Status</TabsTrigger>
          </TabsList>

          <TabsContent value="comparison">
            <Card>
              <CardHeader>
                <CardTitle>PnL Performance Comparison</CardTitle>
                <CardDescription>Real-time PnL tracking (updated every 30 minutes)</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-96">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="timestamp" 
                        tick={{ fontSize: 12 }}
                        angle={-45}
                        textAnchor="end"
                        height={80}
                      />
                      <YAxis 
                        label={{ value: 'PnL ($)', angle: -90, position: 'insideLeft' }}
                        tick={{ fontSize: 12 }}
                        domain={[-600, 600]}
                      />
                      <Tooltip 
                        formatter={(value: number) => `$${value.toFixed(2)}`}
                        labelStyle={{ color: '#000' }}
                      />
                      <Legend />
                      <Line 
                        type="monotone" 
                        dataKey="chatgpt" 
                        stroke="#3b82f6" 
                        strokeWidth={2} 
                        name="ChatGPT"
                        dot={{ r: 4 }}
                        connectNulls
                      />
                      <Line 
                        type="monotone" 
                        dataKey="grok" 
                        stroke="#f97316" 
                        strokeWidth={2} 
                        name="Grok"
                        dot={{ r: 4 }}
                        connectNulls
                      />
                      <Line 
                        type="monotone" 
                        dataKey="gemini" 
                        stroke="#a855f7" 
                        strokeWidth={2} 
                        name="Gemini"
                        dot={{ r: 4 }}
                        connectNulls
                      />
                      <Line 
                        type="monotone" 
                        dataKey="deepseek" 
                        stroke="#22c55e" 
                        strokeWidth={2} 
                        name="DeepSeek"
                        dot={{ r: 4 }}
                        connectNulls
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                {chartData.length === 0 && (
                  <div className="mt-4 text-center text-sm text-gray-500">
                    PnL snapshots will appear here. Data is recorded every 30 minutes.
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="orders">
            <Card>
              <CardHeader>
                <CardTitle>Recent Orders</CardTitle>
                <CardDescription>Latest order executions across both models</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-2">Model</th>
                        <th className="text-left p-2">Symbol</th>
                        <th className="text-left p-2">Side</th>
                        <th className="text-right p-2">Price</th>
                        <th className="text-right p-2">Qty</th>
                        <th className="text-right p-2">Filled</th>
                        <th className="text-left p-2">Status</th>
                        <th className="text-left p-2">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {orders.slice(0, 20).map((order) => (
                        <tr key={order.id} className="border-b hover:bg-gray-50">
                          <td className="p-2">
                            <Badge variant="outline" className={order.model === 'chatgpt' ? 'border-blue-500' : 'border-purple-500'}>
                              {order.model}
                            </Badge>
                          </td>
                          <td className="p-2">{order.symbol}</td>
                          <td className="p-2">
                            <Badge variant={order.side === 'buy' ? 'default' : 'secondary'}>
                              {order.side.toUpperCase()}
                            </Badge>
                          </td>
                          <td className="text-right p-2">${order.price.toFixed(2)}</td>
                          <td className="text-right p-2">{order.qty}</td>
                          <td className="text-right p-2">{order.fill_qty}</td>
                          <td className="p-2">
                            <Badge variant={order.status === 'filled' ? 'default' : 'outline'}>
                              {order.status}
                            </Badge>
                          </td>
                          <td className="p-2 text-gray-500">
                            {new Date(order.created_at).toLocaleTimeString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {orders.length === 0 && (
                    <div className="text-center py-8 text-gray-500">
                      No orders yet. Send a grid signal to start trading.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="grid">
            <Card>
              <CardHeader>
                <CardTitle>Grid Configuration Status</CardTitle>
                <CardDescription>Active grid configurations and controls</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <Alert>
                    <AlertDescription>
                      Grid configurations will appear here once signals are received from ChatGPT or Grok.
                      Send a POST request to the webhook endpoint to create a grid.
                    </AlertDescription>
                  </Alert>
                  
                  <div className="text-sm text-gray-600">
                    <p className="font-semibold mb-2">Webhook Endpoint:</p>
                    <code className="bg-gray-100 px-2 py-1 rounded">
                      POST https://hook.yourdomain.com/signal/grid
                    </code>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

export default App
