'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  BookOpen, 
  Code, 
  Wrench, 
  AlertTriangle, 
  Architecture,
  ChevronDown,
  ChevronRight,
  Home,
  Rocket,
  Settings,
  HelpCircle
} from 'lucide-react'

interface NavItem {
  title: string
  href?: string
  icon?: React.ComponentType<{ className?: string }>
  children?: NavItem[]
}

const navigation: NavItem[] = [
  {
    title: 'Home',
    href: '/',
    icon: Home,
  },
  {
    title: 'Getting Started',
    icon: Rocket,
    children: [
      { title: 'Quick Start', href: '/getting-started/quick-start' },
      { title: 'Installation', href: '/getting-started/installation' },
      { title: 'First Workflow', href: '/getting-started/first-workflow' },
      { title: 'Configuration', href: '/getting-started/configuration' },
    ],
  },
  {
    title: 'API Reference',
    icon: Code,
    children: [
      { title: 'Task Manager API', href: '/api-reference/task-manager' },
      { title: 'Webhook Orchestrator', href: '/api-reference/webhook-orchestrator' },
      { title: 'Codegen Agent API', href: '/api-reference/codegen-agent' },
      { title: 'Monitoring API', href: '/api-reference/monitoring' },
      { title: 'Interactive Explorer', href: '/api-reference/explorer' },
    ],
  },
  {
    title: 'Tutorials',
    icon: BookOpen,
    children: [
      { title: 'Basic Workflows', href: '/tutorials/basic-workflows' },
      { title: 'Custom Agents', href: '/tutorials/custom-agents' },
      { title: 'GitHub Integration', href: '/tutorials/github-integration' },
      { title: 'Claude Code Setup', href: '/tutorials/claude-code-setup' },
      { title: 'Monitoring Setup', href: '/tutorials/monitoring-setup' },
    ],
  },
  {
    title: 'Deployment',
    icon: Settings,
    children: [
      { title: 'Local Development', href: '/deployment/local' },
      { title: 'AWS Deployment', href: '/deployment/aws' },
      { title: 'GCP Deployment', href: '/deployment/gcp' },
      { title: 'Azure Deployment', href: '/deployment/azure' },
      { title: 'Kubernetes', href: '/deployment/kubernetes' },
      { title: 'Docker Compose', href: '/deployment/docker-compose' },
    ],
  },
  {
    title: 'Architecture',
    icon: Architecture,
    children: [
      { title: 'System Overview', href: '/architecture/overview' },
      { title: 'Component Architecture', href: '/architecture/components' },
      { title: 'Data Flow', href: '/architecture/data-flow' },
      { title: 'Security Model', href: '/architecture/security' },
      { title: 'Integration Protocols', href: '/architecture/integrations' },
    ],
  },
  {
    title: 'Troubleshooting',
    icon: AlertTriangle,
    children: [
      { title: 'Common Issues', href: '/troubleshooting/common-issues' },
      { title: 'Diagnostic Tools', href: '/troubleshooting/diagnostic-tools' },
      { title: 'Performance Issues', href: '/troubleshooting/performance' },
      { title: 'Recovery Procedures', href: '/troubleshooting/recovery' },
      { title: 'FAQ', href: '/troubleshooting/faq' },
    ],
  },
  {
    title: 'Help & Support',
    icon: HelpCircle,
    children: [
      { title: 'Community', href: '/help/community' },
      { title: 'Contributing', href: '/help/contributing' },
      { title: 'Changelog', href: '/help/changelog' },
      { title: 'Support', href: '/help/support' },
    ],
  },
]

export function Sidebar() {
  const pathname = usePathname()
  const [expandedItems, setExpandedItems] = useState<string[]>(['Getting Started'])

  const toggleExpanded = (title: string) => {
    setExpandedItems(prev => 
      prev.includes(title) 
        ? prev.filter(item => item !== title)
        : [...prev, title]
    )
  }

  const isActive = (href: string) => pathname === href

  const renderNavItem = (item: NavItem, level = 0) => {
    const hasChildren = item.children && item.children.length > 0
    const isExpanded = expandedItems.includes(item.title)
    const Icon = item.icon

    if (hasChildren) {
      return (
        <div key={item.title}>
          <button
            onClick={() => toggleExpanded(item.title)}
            className={`w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
              level === 0 
                ? 'text-gray-900 hover:bg-gray-100' 
                : 'text-gray-600 hover:bg-gray-50'
            }`}
            style={{ paddingLeft: `${12 + level * 16}px` }}
          >
            <div className="flex items-center space-x-2">
              {Icon && <Icon className="h-4 w-4" />}
              <span>{item.title}</span>
            </div>
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
          {isExpanded && (
            <div className="mt-1 space-y-1">
              {item.children.map(child => renderNavItem(child, level + 1))}
            </div>
          )}
        </div>
      )
    }

    return (
      <Link
        key={item.href}
        href={item.href!}
        className={`flex items-center space-x-2 px-3 py-2 text-sm rounded-lg transition-colors ${
          isActive(item.href!)
            ? 'bg-blue-100 text-blue-700 font-medium'
            : level === 0
            ? 'text-gray-900 hover:bg-gray-100'
            : 'text-gray-600 hover:bg-gray-50'
        }`}
        style={{ paddingLeft: `${12 + level * 16}px` }}
      >
        {Icon && <Icon className="h-4 w-4" />}
        <span>{item.title}</span>
      </Link>
    )
  }

  return (
    <aside className="fixed left-0 top-16 h-[calc(100vh-4rem)] w-64 bg-white border-r border-gray-200 overflow-y-auto">
      <nav className="p-4 space-y-2">
        {navigation.map(item => renderNavItem(item))}
      </nav>
    </aside>
  )
}

