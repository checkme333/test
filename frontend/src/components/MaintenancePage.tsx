import { Construction } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function MaintenancePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl bg-gray-800/50 border-gray-700 backdrop-blur-sm">
        <CardHeader className="text-center space-y-4">
          <div className="flex justify-center">
            <div className="p-4 bg-yellow-500/10 rounded-full">
              <Construction className="w-16 h-16 text-yellow-500" />
            </div>
          </div>
          <CardTitle className="text-3xl font-bold text-white">
            Website Under Maintenance
          </CardTitle>
          <CardDescription className="text-lg text-gray-300">
            We're currently updating our platform to bring you a better experience
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 text-center">
          <p className="text-gray-400">
            Our team is working hard to improve the platform. We'll be back online shortly.
          </p>
          <div className="pt-4 border-t border-gray-700">
            <p className="text-gray-300 mb-3">
              For the latest updates, follow us on Twitter:
            </p>
            <a
              href="https://twitter.com/algoarena"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
              </svg>
              Follow @algoarena
            </a>
          </div>
          <p className="text-sm text-gray-500 pt-4">
            Thank you for your patience and understanding.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
