'use client'

import { useState } from 'react'
import { Search, Menu, Github, ExternalLink } from 'lucide-react'
import { SearchInterface } from './SearchInterface'

export function Header() {
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  return (
    <>
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="md:hidden p-2 rounded-md hover:bg-gray-100"
              >
                <Menu className="h-5 w-5" />
              </button>
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">C</span>
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900">Codegen</h1>
                  <p className="text-xs text-gray-500">AI Workflow Platform</p>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <button
                onClick={() => setIsSearchOpen(true)}
                className="flex items-center space-x-2 px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                <Search className="h-4 w-4 text-gray-500" />
                <span className="text-sm text-gray-500 hidden sm:inline">Search docs...</span>
                <kbd className="hidden sm:inline-flex items-center px-2 py-1 text-xs font-mono bg-white border border-gray-300 rounded">
                  ⌘K
                </kbd>
              </button>

              <a
                href="https://github.com/Zeeeepa/codegen-examples"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 text-gray-500 hover:text-gray-700 transition-colors"
              >
                <Github className="h-5 w-5" />
              </a>

              <a
                href="https://codegen.sh"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center space-x-1 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <span className="text-sm font-medium">Get Started</span>
                <ExternalLink className="h-4 w-4" />
              </a>
            </div>
          </div>
        </div>
      </header>

      <SearchInterface isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />
    </>
  )
}

