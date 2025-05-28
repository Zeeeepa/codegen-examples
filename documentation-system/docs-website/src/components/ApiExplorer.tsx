'use client'

import { useState, useEffect } from 'react'
import SwaggerUI from 'swagger-ui-react'
import 'swagger-ui-react/swagger-ui.css'
import { Play, Copy, Check, Download, Settings } from 'lucide-react'

interface ApiExplorerProps {
  specUrl?: string
  spec?: object
}

export function ApiExplorer({ specUrl, spec }: ApiExplorerProps) {
  const [activeTab, setActiveTab] = useState('explorer')
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('https://api.codegen.sh')
  const [copied, setCopied] = useState(false)

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const downloadSpec = () => {
    const dataStr = JSON.stringify(spec || {}, null, 2)
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr)
    
    const exportFileDefaultName = 'openapi-spec.json'
    
    const linkElement = document.createElement('a')
    linkElement.setAttribute('href', dataUri)
    linkElement.setAttribute('download', exportFileDefaultName)
    linkElement.click()
  }

  const tabs = [
    { id: 'explorer', label: 'API Explorer', icon: Play },
    { id: 'examples', label: 'Code Examples', icon: Copy },
    { id: 'settings', label: 'Settings', icon: Settings },
  ]

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8 px-6">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {activeTab === 'explorer' && (
          <div>
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Interactive API Explorer</h3>
              <p className="text-gray-600">
                Test API endpoints directly from the documentation. Configure your API key and base URL in the settings tab.
              </p>
            </div>
            
            <div className="swagger-ui-container">
              <SwaggerUI
                url={specUrl}
                spec={spec}
                docExpansion="list"
                defaultModelsExpandDepth={1}
                defaultModelExpandDepth={1}
                requestInterceptor={(request) => {
                  if (apiKey) {
                    request.headers['Authorization'] = `Bearer ${apiKey}`
                  }
                  if (baseUrl && request.url.startsWith('/')) {
                    request.url = baseUrl + request.url
                  }
                  return request
                }}
              />
            </div>
          </div>
        )}

        {activeTab === 'examples' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Code Examples</h3>
              <p className="text-gray-600 mb-4">
                Ready-to-use code examples in multiple programming languages.
              </p>
            </div>

            <div className="space-y-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-gray-900">cURL</h4>
                  <button
                    onClick={() => handleCopy(`curl -X GET "${baseUrl}/api/v1/tasks" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json"`)}
                    className="flex items-center space-x-1 text-sm text-gray-500 hover:text-gray-700"
                  >
                    {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    <span>{copied ? 'Copied!' : 'Copy'}</span>
                  </button>
                </div>
                <pre className="text-sm bg-gray-900 text-gray-100 p-3 rounded overflow-x-auto">
{`curl -X GET "${baseUrl}/api/v1/tasks" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json"`}
                </pre>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-gray-900">Python</h4>
                  <button
                    onClick={() => handleCopy(`import requests

url = "${baseUrl}/api/v1/tasks"
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)
print(response.json())`)}
                    className="flex items-center space-x-1 text-sm text-gray-500 hover:text-gray-700"
                  >
                    {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    <span>{copied ? 'Copied!' : 'Copy'}</span>
                  </button>
                </div>
                <pre className="text-sm bg-gray-900 text-gray-100 p-3 rounded overflow-x-auto">
{`import requests

url = "${baseUrl}/api/v1/tasks"
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)
print(response.json())`}
                </pre>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-gray-900">JavaScript</h4>
                  <button
                    onClick={() => handleCopy(`const response = await fetch('${baseUrl}/api/v1/tasks', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
console.log(data);`)}
                    className="flex items-center space-x-1 text-sm text-gray-500 hover:text-gray-700"
                  >
                    {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    <span>{copied ? 'Copied!' : 'Copy'}</span>
                  </button>
                </div>
                <pre className="text-sm bg-gray-900 text-gray-100 p-3 rounded overflow-x-auto">
{`const response = await fetch('${baseUrl}/api/v1/tasks', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
console.log(data);`}
                </pre>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">API Configuration</h3>
              <p className="text-gray-600 mb-4">
                Configure your API settings for testing endpoints in the explorer.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label htmlFor="baseUrl" className="block text-sm font-medium text-gray-700 mb-1">
                  Base URL
                </label>
                <input
                  type="url"
                  id="baseUrl"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="https://api.codegen.sh"
                />
              </div>

              <div>
                <label htmlFor="apiKey" className="block text-sm font-medium text-gray-700 mb-1">
                  API Key
                </label>
                <input
                  type="password"
                  id="apiKey"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Enter your API key"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Your API key is stored locally and never sent to our servers.
                </p>
              </div>

              <div className="pt-4 border-t border-gray-200">
                <button
                  onClick={downloadSpec}
                  className="flex items-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                >
                  <Download className="h-4 w-4" />
                  <span>Download OpenAPI Spec</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

