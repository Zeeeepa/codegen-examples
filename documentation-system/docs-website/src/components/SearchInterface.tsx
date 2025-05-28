'use client'

import { useState, useEffect, useRef } from 'react'
import { Search, X, FileText, Code, Book, Settings } from 'lucide-react'
import Fuse from 'fuse.js'

interface SearchResult {
  id: string
  title: string
  content: string
  url: string
  type: 'page' | 'api' | 'tutorial' | 'config'
  section?: string
}

// Mock search data - in a real implementation, this would come from an API or search index
const searchData: SearchResult[] = [
  {
    id: '1',
    title: 'Quick Start Guide',
    content: 'Get started with Codegen AI Workflow Platform in minutes. Install, configure, and run your first workflow.',
    url: '/getting-started/quick-start',
    type: 'page',
    section: 'Getting Started'
  },
  {
    id: '2',
    title: 'Task Manager API',
    content: 'REST API for managing tasks, workflows, and agent coordination in the Codegen platform.',
    url: '/api-reference/task-manager',
    type: 'api',
    section: 'API Reference'
  },
  {
    id: '3',
    title: 'Creating Custom Agents',
    content: 'Learn how to build and deploy custom AI agents for your specific use cases.',
    url: '/tutorials/custom-agents',
    type: 'tutorial',
    section: 'Tutorials'
  },
  {
    id: '4',
    title: 'AWS Deployment',
    content: 'Deploy the Codegen platform to Amazon Web Services using Terraform and Docker.',
    url: '/deployment/aws',
    type: 'config',
    section: 'Deployment'
  },
  {
    id: '5',
    title: 'Webhook Orchestrator',
    content: 'FastAPI-based service for handling webhook events and orchestrating workflow execution.',
    url: '/api-reference/webhook-orchestrator',
    type: 'api',
    section: 'API Reference'
  },
]

const fuse = new Fuse(searchData, {
  keys: ['title', 'content', 'section'],
  threshold: 0.3,
  includeScore: true,
})

interface SearchInterfaceProps {
  isOpen: boolean
  onClose: () => void
}

export function SearchInterface({ isOpen, onClose }: SearchInterfaceProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  useEffect(() => {
    if (query.trim()) {
      const searchResults = fuse.search(query).map(result => result.item)
      setResults(searchResults.slice(0, 8))
      setSelectedIndex(0)
    } else {
      setResults([])
      setSelectedIndex(0)
    }
  }, [query])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return

      switch (e.key) {
        case 'Escape':
          onClose()
          break
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex(prev => Math.min(prev + 1, results.length - 1))
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex(prev => Math.max(prev - 1, 0))
          break
        case 'Enter':
          e.preventDefault()
          if (results[selectedIndex]) {
            window.location.href = results[selectedIndex].url
            onClose()
          }
          break
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, results, selectedIndex, onClose])

  const getIcon = (type: string) => {
    switch (type) {
      case 'api':
        return <Code className="h-4 w-4 text-blue-500" />
      case 'tutorial':
        return <Book className="h-4 w-4 text-green-500" />
      case 'config':
        return <Settings className="h-4 w-4 text-purple-500" />
      default:
        return <FileText className="h-4 w-4 text-gray-500" />
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-start justify-center pt-20">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
        <div className="flex items-center px-4 py-3 border-b border-gray-200">
          <Search className="h-5 w-5 text-gray-400 mr-3" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search documentation..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 outline-none text-lg"
          />
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <X className="h-5 w-5 text-gray-400" />
          </button>
        </div>

        {results.length > 0 && (
          <div className="max-h-96 overflow-y-auto">
            {results.map((result, index) => (
              <a
                key={result.id}
                href={result.url}
                onClick={onClose}
                className={`block px-4 py-3 border-b border-gray-100 hover:bg-gray-50 transition-colors ${
                  index === selectedIndex ? 'bg-blue-50' : ''
                }`}
              >
                <div className="flex items-start space-x-3">
                  {getIcon(result.type)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <h3 className="text-sm font-medium text-gray-900 truncate">
                        {result.title}
                      </h3>
                      {result.section && (
                        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                          {result.section}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                      {result.content}
                    </p>
                  </div>
                </div>
              </a>
            ))}
          </div>
        )}

        {query && results.length === 0 && (
          <div className="px-4 py-8 text-center text-gray-500">
            <Search className="h-8 w-8 mx-auto mb-2 text-gray-300" />
            <p>No results found for "{query}"</p>
            <p className="text-sm mt-1">Try different keywords or check the spelling</p>
          </div>
        )}

        {!query && (
          <div className="px-4 py-8 text-center text-gray-500">
            <Search className="h-8 w-8 mx-auto mb-2 text-gray-300" />
            <p>Start typing to search the documentation</p>
            <div className="flex items-center justify-center space-x-4 mt-4 text-xs">
              <div className="flex items-center space-x-1">
                <kbd className="px-2 py-1 bg-gray-100 rounded">↑↓</kbd>
                <span>Navigate</span>
              </div>
              <div className="flex items-center space-x-1">
                <kbd className="px-2 py-1 bg-gray-100 rounded">Enter</kbd>
                <span>Select</span>
              </div>
              <div className="flex items-center space-x-1">
                <kbd className="px-2 py-1 bg-gray-100 rounded">Esc</kbd>
                <span>Close</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

