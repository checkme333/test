import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts'
import { TrendingUp, Activity, AlertTriangle } from 'lucide-react'
import { MaintenancePage } from '@/components/MaintenancePage'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const MAINTENANCE_MODE = import.meta.env.VITE_MAINTENANCE_MODE === 'true'

interface ModelAccount {
  model: string
  initial_balance: number
  current_balance: number
  total_position_value: number
  total_position_margin: number
  unrealized_pnl: number
  total_equity: number
  total_pnl: number
  total_trades: number
  winning_trades: number
  losing_trades: number
  max_drawdown: number
}

interface Decision {
  id: number
  model: string
  symbol: string
  action: string
  reasoning: string
  decision_data: {
    action: string
    size_usd: number
    reasoning: string
    confidence: number
  }
  created_at: string
}

interface Position {
  model: string
  symbol: string
  side: string
  size: number
  entry_price: number
  current_price: number
  unrealized_pnl: number
}

interface Order {
  id: number
  model: string
  symbol: string
  side: string
  price: number
  qty: number
  status: string
  pnl: number
  created_at: string
}

interface DashboardStats {
  accounts: ModelAccount[]
  prices: Record<string, number>
  price_changes: Record<string, number>
  recent_decisions: Decision[]
  positions: Position[]
  orders: Order[]
  timestamp: string
}

const MODEL_CONFIG = {
  chatgpt: { 
    name: 'ChatGPT',
    color: '#10b981', // green
    bgColor: 'bg-green-500/10',
    textColor: 'text-green-400',
    borderColor: 'border-green-500/30',
    logo: '/logos/chatgpt.png'
  },
  grok: { 
    name: 'Grok',
    color: '#a855f7',
    bgColor: 'bg-purple-500/10',
    textColor: 'text-purple-400',
    borderColor: 'border-purple-500/30',
    logo: '/logos/grok.webp'
  },
  claude: { 
    name: 'Claude',
    color: '#f97316', // orange
    bgColor: 'bg-orange-500/10',
    textColor: 'text-orange-400',
    borderColor: 'border-orange-500/30',
    logo: '/logos/claude.png'
  },
  deepseek: { 
    name: 'DeepSeek',
    color: '#3b82f6', // blue
    bgColor: 'bg-blue-500/10',
    textColor: 'text-blue-400',
    borderColor: 'border-blue-500/30',
    logo: '/logos/deepseek.png'
  }
}

function App() {
  if (MAINTENANCE_MODE) {
    return <MaintenancePage />
  }

  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [equityHistory, setEquityHistory] = useState<any[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('all') // For filtering decisions/positions

  const fetchData = async () => {
    try {
      const res = await fetch(`${API_BASE}/dashboard/stats`)
      if (!res.ok) {
        console.warn('Failed to fetch data, will retry...')
        return
      }
      
      const data = await res.json()
      setStats(data)
      
      const now = new Date()
      const timestamp = now.toLocaleString('en-US', { 
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      }).replace(',', '')
      
      const newDataPoint: any = { timestamp, time: now.getTime() }
      data.accounts.forEach((acc: ModelAccount) => {
        newDataPoint[acc.model] = acc.total_pnl
      })
      
      setEquityHistory(prev => {
        if (prev.length === 0) {
          const twentyMinutesFromNow = new Date(now.getTime() + 20 * 60000)
          const startTimestamp = twentyMinutesFromNow.toLocaleString('en-US', { 
            month: 'short',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
          }).replace(',', '')
          
          const startPoint = { 
            timestamp: startTimestamp, 
            time: twentyMinutesFromNow.getTime(),
            chatgpt: 0,
            grok: 0,
            claude: 0,
            deepseek: 0
          }
          return [startPoint]
        }
        
        const lastPoint = prev[prev.length - 1]
        const thirtyMinutes = 30 * 60000 // 30 minutes in milliseconds
        
        if (lastPoint && now.getTime() - lastPoint.time >= thirtyMinutes) {
          const updated = [...prev, newDataPoint]
          return updated.slice(-8) // Keep last 8 points (4 hours of data at 30-min intervals)
        }
        
        if (prev.length > 0 && now.getTime() < prev[0].time) {
          return prev
        }
        
        if (prev.length > 0) {
          const updated = [...prev]
          updated[updated.length - 1] = newDataPoint
          return updated
        }
        
        return prev
      })
      
      setError(null)
    } catch (err) {
      console.warn('Error fetching data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-16 h-16 animate-spin mx-auto mb-4 text-green-500" />
          <p className="text-xl text-gray-300">Loading AI Trading Competition...</p>
        </div>
      </div>
    )
  }

  const sortedAccounts = stats?.accounts.sort((a, b) => b.total_pnl - a.total_pnl) || []

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <div className="border-b border-gray-800 bg-black/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img src="/logo.png" alt="AlgoArena" className="w-10 h-10 object-contain" />
              <div>
                <h1 className="text-2xl font-bold text-white">AlgoArena</h1>
                <p className="text-sm text-gray-400">AI Trading Competition</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <a 
                href="https://x.com/ArenaAlgo" 
                target="_blank" 
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-white hover:bg-gray-100 transition-colors"
                title="Follow us on X (Twitter)"
              >
                <img src="/logos/x-logo.png" alt="X" className="w-5 h-5 object-contain" />
              </a>
              <div className="text-right">
                <p className="text-xs text-gray-500">Last Update</p>
                <p className="text-sm text-gray-300">{new Date().toLocaleTimeString()}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6 space-y-6">
        {error && (
          <Alert className="bg-red-900/20 border-red-600/50">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            <AlertDescription className="text-red-200">{error}</AlertDescription>
          </Alert>
        )}

        {/* Main Chart - Like nof1.ai */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-white text-xl">Portfolio Value Over Time</CardTitle>
                <CardDescription className="text-gray-400">
                  Real-time equity curves for all AI models
                </CardDescription>
              </div>
              <div className="flex gap-2">
                {Object.entries(MODEL_CONFIG).map(([key, config]) => {
                  return (
                    <div key={key} className="flex items-center gap-2 px-3 py-1 rounded-full bg-gray-800/50">
                      <img src={config.logo} alt={config.name} className="w-5 h-5 object-contain" />
                      <span className="text-sm text-gray-300">{config.name}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-[400px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={equityHistory}>
                  <defs>
                    {Object.entries(MODEL_CONFIG).map(([key, config]) => (
                      <linearGradient key={key} id={`gradient-${key}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={config.color} stopOpacity={0.3}/>
                        <stop offset="95%" stopColor={config.color} stopOpacity={0}/>
                      </linearGradient>
                    ))}
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                  <XAxis 
                    dataKey="timestamp" 
                    stroke="#6b7280" 
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    tickLine={false}
                    angle={-15}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis 
                    stroke="#6b7280" 
                    tick={{ fill: '#9ca3af', fontSize: 12 }}
                    tickLine={false}
                    domain={[(dataMin: number) => Math.min(dataMin, 0), 'auto']}
                    tickFormatter={(value) => {
                      const sign = value >= 0 ? '+' : '';
                      return `${sign}$${value.toFixed(0)}`;
                    }}
                  />
                  {/* Zero reference line */}
                  <line x1="0" y1="50%" x2="100%" y2="50%" stroke="#6b7280" strokeWidth={1} strokeDasharray="5 5" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#111827', 
                      border: '1px solid #374151',
                      borderRadius: '8px',
                      padding: '12px'
                    }}
                    labelStyle={{ color: '#9ca3af', marginBottom: '8px' }}
                    itemStyle={{ color: '#fff' }}
                    formatter={(value: any) => {
                      const numValue = Number(value);
                      const sign = numValue >= 0 ? '+' : '';
                      return `${sign}$${numValue.toFixed(2)}`;
                    }}
                  />
                  <Legend 
                    wrapperStyle={{ paddingTop: '20px' }}
                    iconType="line"
                  />
                  {Object.entries(MODEL_CONFIG).map(([key, config]) => (
                    <Area
                      key={key}
                      type="monotone"
                      dataKey={key}
                      stroke={config.color}
                      strokeWidth={2}
                      fill={`url(#gradient-${key})`}
                      name={config.name}
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Model Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {sortedAccounts.map((account, index) => {
            const config = MODEL_CONFIG[account.model as keyof typeof MODEL_CONFIG]
            const winRate = account.total_trades > 0 
              ? (account.winning_trades / account.total_trades * 100).toFixed(1) 
              : '0.0'
            const pnlPercent = ((account.total_pnl / account.initial_balance) * 100).toFixed(2)
            const isProfitable = account.total_pnl >= 0

            return (
              <Card 
                key={account.model} 
                className={`${config.bgColor} border ${config.borderColor} relative overflow-hidden`}
              >
                {index === 0 && (
                  <div className="absolute top-2 right-2">
                    <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30">
                      🏆 Leader
                    </Badge>
                  </div>
                )}
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${config.bgColor} border ${config.borderColor}`}>
                      <img src={config.logo} alt={config.name} className="w-8 h-8 object-contain" />
                    </div>
                    <div>
                      <CardTitle className="text-white text-lg">{config.name}</CardTitle>
                      <p className="text-xs text-gray-500">AI Model #{index + 1}</p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between items-baseline">
                    <span className="text-sm text-gray-400">Total Equity</span>
                    <span className="text-2xl font-bold text-white">
                      ${account.total_equity.toFixed(2)}
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-gray-500">Cash Balance</span>
                    <span className="text-gray-300">${account.current_balance.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-gray-500">Position Margin</span>
                    <span className="text-gray-300">${(account.total_position_margin || 0).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-gray-500">Unrealized PNL</span>
                    <span className={`${(account.unrealized_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {(account.unrealized_pnl || 0) >= 0 ? '+' : ''}${(account.unrealized_pnl || 0).toFixed(2)}
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-400">P&L</span>
                    <div className="text-right">
                      <span className={`text-lg font-semibold ${isProfitable ? 'text-green-400' : 'text-red-400'}`}>
                        {isProfitable ? '+' : ''}${account.total_pnl.toFixed(2)}
                      </span>
                      <Badge 
                        variant={isProfitable ? "default" : "destructive"}
                        className="ml-2"
                      >
                        {pnlPercent}%
                      </Badge>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-gray-800 space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">Win Rate</span>
                      <span className="text-gray-300 font-medium">{winRate}%</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">Trades</span>
                      <span className="text-gray-300">
                        <span className="text-green-400">{account.winning_trades}W</span>
                        {' / '}
                        <span className="text-red-400">{account.losing_trades}L</span>
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">Max Drawdown</span>
                      <span className="text-red-400">{account.max_drawdown.toFixed(2)}%</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Recent AI Decisions with Model Filter */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-white">Recent AI Decisions</CardTitle>
                <CardDescription className="text-gray-400">
                  Latest trading decisions with AI reasoning
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedModel('all')}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                    selectedModel === 'all' 
                      ? 'bg-gray-700 text-white' 
                      : 'bg-gray-800/50 text-gray-400 hover:bg-gray-800'
                  }`}
                >
                  All
                </button>
                {Object.entries(MODEL_CONFIG).map(([key, config]) => (
                  <button
                    key={key}
                    onClick={() => setSelectedModel(key)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition flex items-center gap-2 ${
                      selectedModel === key 
                        ? `${config.bgColor} ${config.textColor} border ${config.borderColor}` 
                        : 'bg-gray-800/50 text-gray-400 hover:bg-gray-800'
                    }`}
                  >
                    <img src={config.logo} alt={config.name} className="w-4 h-4 object-contain" />
                    {config.name}
                  </button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
              {stats?.recent_decisions
                .filter(d => selectedModel === 'all' || d.model === selectedModel)
                .slice(0, 50)
                .map((decision) => {
                  const config = MODEL_CONFIG[decision.model as keyof typeof MODEL_CONFIG]
                  return (
                    <div 
                      key={decision.id} 
                      className="bg-gray-800/50 p-4 rounded-lg border border-gray-700 hover:border-gray-600 transition"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <div className={`p-1.5 rounded ${config.bgColor}`}>
                            <img src={config.logo} alt={config.name} className="w-5 h-5 object-contain" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className={`font-semibold ${config.textColor}`}>
                                {config.name}
                              </span>
                              <Badge 
                                className={
                                  decision.action === 'BUY' ? 'bg-green-500 text-white hover:bg-green-600' : 
                                  decision.action === 'SELL' ? 'bg-red-500 text-white hover:bg-red-600' : 
                                  'bg-white text-black hover:bg-gray-100'
                                }
                              >
                                {decision.action}
                              </Badge>
                              <span className="text-sm text-gray-500">{decision.symbol}</span>
                            </div>
                            <p className="text-sm text-gray-400 mt-1">{decision.reasoning}</p>
                          </div>
                        </div>
                        <span className="text-xs text-gray-500 whitespace-nowrap">
                          {new Date(decision.created_at).toLocaleTimeString()}
                        </span>
                      </div>
                      {decision.decision_data && (
                        <div className="flex gap-4 text-xs text-gray-500 mt-2 pl-11">
                          <span>Size: ${decision.decision_data.size_usd?.toFixed(2)}</span>
                          <span>Confidence: {(decision.decision_data.confidence * 100).toFixed(0)}%</span>
                        </div>
                      )}
                    </div>
                  )
                })}
              {(!stats?.recent_decisions || stats.recent_decisions.filter(d => selectedModel === 'all' || d.model === selectedModel).length === 0) && (
                <div className="text-center py-12 text-gray-500">
                  <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No decisions yet. AI models will start making decisions soon.</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Current Positions with Model Filter */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Current Positions</CardTitle>
            <CardDescription className="text-gray-400">
              Active positions {selectedModel === 'all' ? 'across all AI models' : `for ${MODEL_CONFIG[selectedModel as keyof typeof MODEL_CONFIG]?.name}`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {stats?.positions && stats.positions.filter(p => selectedModel === 'all' || p.model === selectedModel).length > 0 ? (
              <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-800">
                      <th className="text-left p-3 text-gray-400 font-medium">Model</th>
                      <th className="text-left p-3 text-gray-400 font-medium">Symbol</th>
                      <th className="text-left p-3 text-gray-400 font-medium">Side</th>
                      <th className="text-right p-3 text-gray-400 font-medium">Size</th>
                      <th className="text-right p-3 text-gray-400 font-medium">Entry</th>
                      <th className="text-right p-3 text-gray-400 font-medium">Current</th>
                      <th className="text-right p-3 text-gray-400 font-medium">P&L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.positions
                      .filter(p => selectedModel === 'all' || p.model === selectedModel)
                      .map((pos, idx) => {
                        const config = MODEL_CONFIG[pos.model as keyof typeof MODEL_CONFIG]
                        const isProfitable = pos.unrealized_pnl >= 0
                        return (
                          <tr key={idx} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                            <td className="p-3">
                              <div className="flex items-center gap-2">
                                <img src={config.logo} alt={config.name} className="w-5 h-5 object-contain" />
                                <span className="text-gray-300">{config.name}</span>
                              </div>
                            </td>
                            <td className="p-3 text-gray-300">{pos.symbol}</td>
                            <td className="p-3">
                              <Badge 
                                className={pos.side.toLowerCase() === 'long' ? 'bg-green-500/20 text-green-400 border-green-500/30' : 'bg-red-500/20 text-red-400 border-red-500/30'}
                              >
                                {pos.side.toUpperCase()}
                              </Badge>
                            </td>
                            <td className="text-right p-3 text-gray-300">{pos.size}</td>
                            <td className="text-right p-3 text-gray-300">${pos.entry_price.toFixed(2)}</td>
                            <td className="text-right p-3 text-gray-300">${pos.current_price?.toFixed(2) || '-'}</td>
                            <td className={`text-right p-3 font-semibold ${isProfitable ? 'text-green-400' : 'text-red-400'}`}>
                              {isProfitable ? '+' : ''}${pos.unrealized_pnl.toFixed(2)}
                            </td>
                          </tr>
                        )
                      })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500">
                <TrendingUp className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No open positions</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Order History */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Order History</CardTitle>
            <CardDescription className="text-gray-400">
              Completed orders {selectedModel === 'all' ? 'across all AI models' : `for ${MODEL_CONFIG[selectedModel as keyof typeof MODEL_CONFIG]?.name}`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {stats?.orders && stats.orders.filter(o => selectedModel === 'all' || o.model === selectedModel).length > 0 ? (
              <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-800">
                      <th className="text-left p-3 text-gray-400 font-medium">Model</th>
                      <th className="text-left p-3 text-gray-400 font-medium">Symbol</th>
                      <th className="text-left p-3 text-gray-400 font-medium">Side</th>
                      <th className="text-right p-3 text-gray-400 font-medium">Price</th>
                      <th className="text-right p-3 text-gray-400 font-medium">Qty</th>
                      <th className="text-left p-3 text-gray-400 font-medium">Status</th>
                      <th className="text-right p-3 text-gray-400 font-medium">P&L</th>
                      <th className="text-right p-3 text-gray-400 font-medium">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.orders
                      .filter(o => selectedModel === 'all' || o.model === selectedModel)
                      .slice(0, 100)
                      .map((order) => {
                        const config = MODEL_CONFIG[order.model as keyof typeof MODEL_CONFIG]
                        const isProfitable = order.pnl >= 0
                        return (
                          <tr key={order.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                            <td className="p-3">
                              <div className="flex items-center gap-2">
                                <img src={config.logo} alt={config.name} className="w-5 h-5 object-contain" />
                                <span className="text-gray-300">{config.name}</span>
                              </div>
                            </td>
                            <td className="p-3 text-gray-300">{order.symbol}</td>
                            <td className="p-3">
                              <Badge 
                                className={order.side.toLowerCase() === 'buy' || order.side.toLowerCase() === 'long' ? 'bg-green-500/20 text-green-400 border-green-500/30' : 'bg-red-500/20 text-red-400 border-red-500/30'}
                              >
                                {order.side.toUpperCase()}
                              </Badge>
                            </td>
                            <td className="text-right p-3 text-gray-300">${order.price.toFixed(2)}</td>
                            <td className="text-right p-3 text-gray-300">{order.qty}</td>
                            <td className="p-3">
                              <Badge 
                                className={
                                  order.status === 'FILLED' ? 'bg-green-500/20 text-green-400 border-green-500/30' : 
                                  order.status === 'CANCELLED' ? 'bg-gray-500/20 text-gray-400 border-gray-500/30' : 
                                  'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
                                }
                              >
                                {order.status}
                              </Badge>
                            </td>
                            <td className={`text-right p-3 font-semibold ${isProfitable ? 'text-green-400' : 'text-red-400'}`}>
                              {isProfitable ? '+' : ''}${order.pnl.toFixed(2)}
                            </td>
                            <td className="text-right p-3 text-gray-500 text-xs">
                              {new Date(order.created_at).toLocaleString()}
                            </td>
                          </tr>
                        )
                      })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500">
                <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No order history yet</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Token Cards - BTC, ETH, BNB, ASTER */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {['BTC', 'ETH', 'BNB', 'ASTER'].map((symbol) => {
            const price = stats?.prices?.[`${symbol}USDT`] || 0
            const priceStr = price > 0 ? `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'N/A'
            const change24h = stats?.price_changes?.[`${symbol}USDT`] || 0
            const isPositive = change24h >= 0
            
            return (
              <Card key={symbol} className="bg-gray-900/50 border-gray-800 hover:border-gray-700 transition">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-orange-500 to-yellow-500 flex items-center justify-center text-white font-bold">
                        {symbol.charAt(0)}
                      </div>
                      <span className="font-bold text-white text-lg">{symbol}/USDT</span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="text-3xl font-bold text-white">{priceStr}</div>
                    <div className={`text-sm font-medium ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                      {isPositive ? '+' : ''}{change24h.toFixed(2)}% (24h)
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-gray-800 mt-12">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="text-center text-gray-500 text-sm">
            <p>AI Trading Competition • Real-time Performance Tracking</p>
            <p className="mt-1">Powered by ChatGPT, Grok, Claude, and DeepSeek</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
