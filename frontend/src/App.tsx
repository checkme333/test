import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { TrendingUp, Activity, AlertTriangle, Brain, Twitter, Coins } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

interface ModelAccount {
  model: string
  initial_balance: number
  current_balance: number
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

interface DashboardStats {
  accounts: ModelAccount[]
  prices: Record<string, number>
  recent_decisions: Decision[]
  positions: Position[]
  timestamp: string
}

const MODEL_COLORS = {
  chatgpt: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-500', chart: '#3b82f6' },
  grok: { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-500', chart: '#a855f7' },
  claude: { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-500', chart: '#f97316' },
  deepseek: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-500', chart: '#10b981' }
}

function App() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [equityHistory, setEquityHistory] = useState<any[]>([])

  const fetchData = async () => {
    try {
      const res = await fetch(`${API_BASE}/dashboard/stats`)
      if (!res.ok) throw new Error('Failed to fetch data')
      
      const data = await res.json()
      setStats(data)
      
      const timestamp = new Date().toLocaleTimeString()
      const newDataPoint: any = { timestamp }
      data.accounts.forEach((acc: ModelAccount) => {
        newDataPoint[acc.model] = acc.current_balance
      })
      
      setEquityHistory(prev => {
        const updated = [...prev, newDataPoint]
        return updated.slice(-50)
      })
      
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [])

  const ModelCompetitionCard = ({ account }: { account: ModelAccount }) => {
    const color = MODEL_COLORS[account.model as keyof typeof MODEL_COLORS]
    const winRate = account.total_trades > 0 
      ? (account.winning_trades / account.total_trades * 100).toFixed(1) 
      : '0.0'
    const pnlPercent = ((account.total_pnl / account.initial_balance) * 100).toFixed(2)
    const isProfitable = account.total_pnl >= 0

    return (
      <Card className={`${color.bg} border-2 ${color.border}`}>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Brain className={`w-5 h-5 ${color.text}`} />
              <span className={color.text}>{account.model.toUpperCase()}</span>
            </div>
            <Badge variant={isProfitable ? "default" : "destructive"}>
              {pnlPercent}%
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Balance</span>
              <span className="text-xl font-bold">${account.current_balance.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">P&L</span>
              <span className={`text-lg font-semibold ${isProfitable ? 'text-green-600' : 'text-red-600'}`}>
                {isProfitable ? '+' : ''}${account.total_pnl.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Win Rate</span>
              <span className="text-lg font-semibold">{winRate}%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Trades</span>
              <span className="text-sm">{account.winning_trades}W / {account.losing_trades}L</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Max DD</span>
              <span className="text-sm text-red-600">{(account.max_drawdown * 100).toFixed(2)}%</span>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-16 h-16 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-xl text-gray-300">Loading AI Trading Arena...</p>
        </div>
      </div>
    )
  }

  const sortedAccounts = stats?.accounts.sort((a, b) => b.total_pnl - a.total_pnl) || []
  const leader = sortedAccounts[0]

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      <div className="max-w-7xl mx-auto p-6">
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent mb-2">
                AI Trading Arena
              </h1>
              <p className="text-gray-400 text-lg">4 AI Models Competing in Real-Time Trading</p>
            </div>
            <div className="flex gap-4">
              <a 
                href="https://twitter.com/your_project" 
                target="_blank" 
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition"
              >
                <Twitter className="w-5 h-5" />
                <span>Follow Us</span>
              </a>
            </div>
          </div>

          {leader && (
            <Alert className="bg-yellow-900/30 border-yellow-600">
              <TrendingUp className="w-4 h-4 text-yellow-500" />
              <AlertDescription className="text-yellow-200">
                <strong>{leader.model.toUpperCase()}</strong> is currently leading with ${leader.total_pnl.toFixed(2)} profit!
              </AlertDescription>
            </Alert>
          )}
        </div>

        {error && (
          <Alert className="mb-6 bg-red-900/30 border-red-600">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            <AlertDescription className="text-red-200">{error}</AlertDescription>
          </Alert>
        )}

        <div className="mb-8">
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Coins className="w-5 h-5 text-yellow-500" />
                Project Token (Coming Soon)
              </CardTitle>
              <CardDescription className="text-gray-400">
                Our official token will be launched soon. Stay tuned for updates!
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-gray-300">
                <p className="mb-2">This AI trading competition is powered by our upcoming token ecosystem.</p>
                <p className="text-sm text-gray-400">Token holders will get exclusive access to advanced features and trading insights.</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {sortedAccounts.map((account) => (
            <ModelCompetitionCard key={account.model} account={account} />
          ))}
        </div>

        {stats && stats.prices && Object.keys(stats.prices).length > 0 && (
          <Card className="bg-gray-800/50 border-gray-700 mb-8">
            <CardHeader>
              <CardTitle className="text-white">Live Market Prices</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                {Object.entries(stats.prices).map(([symbol, price]) => (
                  <div key={symbol} className="text-center">
                    <p className="text-gray-400 text-sm">{symbol}</p>
                    <p className="text-2xl font-bold text-white">${price.toFixed(2)}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <Tabs defaultValue="chart" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 bg-gray-800/50">
            <TabsTrigger value="chart">Equity Curves</TabsTrigger>
            <TabsTrigger value="decisions">AI Decisions</TabsTrigger>
            <TabsTrigger value="positions">Positions</TabsTrigger>
            <TabsTrigger value="stats">Statistics</TabsTrigger>
          </TabsList>

          <TabsContent value="chart">
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white">Real-Time Equity Curves</CardTitle>
                <CardDescription className="text-gray-400">
                  Live performance comparison across all AI models
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-96">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={equityHistory}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="timestamp" stroke="#9ca3af" />
                      <YAxis stroke="#9ca3af" />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
                        labelStyle={{ color: '#9ca3af' }}
                      />
                      <Legend />
                      <Line type="monotone" dataKey="chatgpt" stroke={MODEL_COLORS.chatgpt.chart} strokeWidth={2} />
                      <Line type="monotone" dataKey="grok" stroke={MODEL_COLORS.grok.chart} strokeWidth={2} />
                      <Line type="monotone" dataKey="claude" stroke={MODEL_COLORS.claude.chart} strokeWidth={2} />
                      <Line type="monotone" dataKey="deepseek" stroke={MODEL_COLORS.deepseek.chart} strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="decisions">
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white">Recent AI Decisions</CardTitle>
                <CardDescription className="text-gray-400">
                  Latest trading decisions with AI reasoning
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {stats?.recent_decisions.slice(0, 10).map((decision) => {
                    const color = MODEL_COLORS[decision.model as keyof typeof MODEL_COLORS]
                    return (
                      <div key={decision.id} className="bg-gray-900/50 p-4 rounded-lg border border-gray-700">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Badge className={`${color.bg} ${color.text}`}>
                              {decision.model.toUpperCase()}
                            </Badge>
                            <Badge variant={
                              decision.action === 'BUY' ? 'default' : 
                              decision.action === 'SELL' ? 'destructive' : 
                              'outline'
                            }>
                              {decision.action}
                            </Badge>
                            <span className="text-sm text-gray-400">{decision.symbol}</span>
                          </div>
                          <span className="text-xs text-gray-500">
                            {new Date(decision.created_at).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-gray-300 text-sm mb-2">{decision.reasoning}</p>
                        {decision.decision_data && (
                          <div className="flex gap-4 text-xs text-gray-400">
                            <span>Size: ${decision.decision_data.size_usd?.toFixed(2)}</span>
                            <span>Confidence: {(decision.decision_data.confidence * 100).toFixed(0)}%</span>
                          </div>
                        )}
                      </div>
                    )
                  })}
                  {(!stats?.recent_decisions || stats.recent_decisions.length === 0) && (
                    <div className="text-center py-8 text-gray-500">
                      No decisions yet. AI models will start making decisions soon.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="positions">
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white">Current Positions</CardTitle>
                <CardDescription className="text-gray-400">
                  Active positions across all AI models
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left p-2 text-gray-400">Model</th>
                        <th className="text-left p-2 text-gray-400">Symbol</th>
                        <th className="text-left p-2 text-gray-400">Side</th>
                        <th className="text-right p-2 text-gray-400">Size</th>
                        <th className="text-right p-2 text-gray-400">Entry</th>
                        <th className="text-right p-2 text-gray-400">Current</th>
                        <th className="text-right p-2 text-gray-400">P&L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats?.positions.map((pos, idx) => {
                        const color = MODEL_COLORS[pos.model as keyof typeof MODEL_COLORS]
                        const isProfitable = pos.unrealized_pnl >= 0
                        return (
                          <tr key={idx} className="border-b border-gray-800 hover:bg-gray-900/50">
                            <td className="p-2">
                              <Badge className={`${color.bg} ${color.text}`}>
                                {pos.model}
                              </Badge>
                            </td>
                            <td className="p-2 text-gray-300">{pos.symbol}</td>
                            <td className="p-2">
                              <Badge variant={pos.side === 'long' ? 'default' : 'destructive'}>
                                {pos.side.toUpperCase()}
                              </Badge>
                            </td>
                            <td className="text-right p-2 text-gray-300">{pos.size}</td>
                            <td className="text-right p-2 text-gray-300">${pos.entry_price.toFixed(2)}</td>
                            <td className="text-right p-2 text-gray-300">${pos.current_price?.toFixed(2) || '-'}</td>
                            <td className={`text-right p-2 font-semibold ${isProfitable ? 'text-green-500' : 'text-red-500'}`}>
                              {isProfitable ? '+' : ''}${pos.unrealized_pnl.toFixed(2)}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                  {(!stats?.positions || stats.positions.length === 0) && (
                    <div className="text-center py-8 text-gray-500">
                      No open positions
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="stats">
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white">Detailed Statistics</CardTitle>
                <CardDescription className="text-gray-400">
                  Comprehensive performance metrics for all models
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left p-2 text-gray-400">Model</th>
                        <th className="text-right p-2 text-gray-400">Initial</th>
                        <th className="text-right p-2 text-gray-400">Current</th>
                        <th className="text-right p-2 text-gray-400">P&L</th>
                        <th className="text-right p-2 text-gray-400">ROI</th>
                        <th className="text-right p-2 text-gray-400">Win Rate</th>
                        <th className="text-right p-2 text-gray-400">Trades</th>
                        <th className="text-right p-2 text-gray-400">Max DD</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedAccounts.map((account) => {
                        const color = MODEL_COLORS[account.model as keyof typeof MODEL_COLORS]
                        const roi = ((account.total_pnl / account.initial_balance) * 100).toFixed(2)
                        const winRate = account.total_trades > 0 
                          ? (account.winning_trades / account.total_trades * 100).toFixed(1) 
                          : '0.0'
                        const isProfitable = account.total_pnl >= 0
                        
                        return (
                          <tr key={account.model} className="border-b border-gray-800 hover:bg-gray-900/50">
                            <td className="p-2">
                              <Badge className={`${color.bg} ${color.text}`}>
                                {account.model.toUpperCase()}
                              </Badge>
                            </td>
                            <td className="text-right p-2 text-gray-300">${account.initial_balance.toFixed(2)}</td>
                            <td className="text-right p-2 text-gray-300">${account.current_balance.toFixed(2)}</td>
                            <td className={`text-right p-2 font-semibold ${isProfitable ? 'text-green-500' : 'text-red-500'}`}>
                              {isProfitable ? '+' : ''}${account.total_pnl.toFixed(2)}
                            </td>
                            <td className={`text-right p-2 font-semibold ${isProfitable ? 'text-green-500' : 'text-red-500'}`}>
                              {isProfitable ? '+' : ''}{roi}%
                            </td>
                            <td className="text-right p-2 text-gray-300">{winRate}%</td>
                            <td className="text-right p-2 text-gray-300">
                              {account.total_trades} ({account.winning_trades}W/{account.losing_trades}L)
                            </td>
                            <td className="text-right p-2 text-red-500">{(account.max_drawdown * 100).toFixed(2)}%</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>Last updated: {stats?.timestamp ? new Date(stats.timestamp).toLocaleString() : 'N/A'}</p>
          <p className="mt-2">Auto-refreshing every 10 seconds</p>
        </div>
      </div>
    </div>
  )
}

export default App
