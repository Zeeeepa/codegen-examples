import Link from 'next/link'
import { ArrowRight, Zap, Shield, Globe } from 'lucide-react'

export function Hero() {
  return (
    <div className="text-center py-12">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-5xl font-bold text-gray-900 mb-6">
          Codegen AI Workflow Platform
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          Comprehensive documentation and deployment guides for building, deploying, and maintaining 
          AI-powered development workflows with Claude Code integration.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
          <Link
            href="/getting-started/quick-start"
            className="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            Get Started
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
          <Link
            href="/api-reference/explorer"
            className="inline-flex items-center px-6 py-3 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors"
          >
            Explore APIs
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-16">
          <div className="text-center">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <Zap className="h-6 w-6 text-blue-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Fast Setup</h3>
            <p className="text-gray-600">
              Get your AI workflow platform running in minutes with our automated deployment scripts.
            </p>
          </div>
          
          <div className="text-center">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <Shield className="h-6 w-6 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Production Ready</h3>
            <p className="text-gray-600">
              Enterprise-grade security, monitoring, and scalability built-in from day one.
            </p>
          </div>
          
          <div className="text-center">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <Globe className="h-6 w-6 text-purple-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Multi-Cloud</h3>
            <p className="text-gray-600">
              Deploy to AWS, GCP, Azure, or run locally with Docker. Your choice, our support.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

