import Link from 'next/link'
import { 
  Code, 
  Rocket, 
  BookOpen, 
  Wrench, 
  AlertTriangle, 
  Architecture,
  Database,
  Monitor,
  GitBranch,
  Cloud
} from 'lucide-react'

const features = [
  {
    title: 'Interactive API Documentation',
    description: 'OpenAPI/Swagger specs with live testing capabilities for all platform APIs.',
    icon: Code,
    href: '/api-reference/explorer',
    color: 'blue'
  },
  {
    title: 'One-Click Deployment',
    description: 'Automated deployment scripts for AWS, GCP, Azure, and local environments.',
    icon: Rocket,
    href: '/deployment/local',
    color: 'green'
  },
  {
    title: 'Step-by-Step Tutorials',
    description: 'Comprehensive guides with working examples and best practices.',
    icon: BookOpen,
    href: '/tutorials/basic-workflows',
    color: 'purple'
  },
  {
    title: 'Troubleshooting Tools',
    description: 'Diagnostic utilities and recovery procedures for common issues.',
    icon: Wrench,
    href: '/troubleshooting/diagnostic-tools',
    color: 'orange'
  },
  {
    title: 'System Architecture',
    description: 'Detailed documentation of component interactions and data flow.',
    icon: Architecture,
    href: '/architecture/overview',
    color: 'indigo'
  },
  {
    title: 'Database Schema',
    description: 'PostgreSQL schema documentation with migration scripts.',
    icon: Database,
    href: '/architecture/database-schema',
    color: 'cyan'
  },
  {
    title: 'Monitoring & Observability',
    description: 'Health checks, metrics, and logging configuration guides.',
    icon: Monitor,
    href: '/tutorials/monitoring-setup',
    color: 'emerald'
  },
  {
    title: 'CI/CD Integration',
    description: 'GitHub Actions workflows and automated testing procedures.',
    icon: GitBranch,
    href: '/tutorials/github-integration',
    color: 'pink'
  },
  {
    title: 'Multi-Cloud Support',
    description: 'Terraform modules and Kubernetes manifests for any cloud provider.',
    icon: Cloud,
    href: '/deployment/kubernetes',
    color: 'amber'
  }
]

const colorClasses = {
  blue: 'bg-blue-100 text-blue-600',
  green: 'bg-green-100 text-green-600',
  purple: 'bg-purple-100 text-purple-600',
  orange: 'bg-orange-100 text-orange-600',
  indigo: 'bg-indigo-100 text-indigo-600',
  cyan: 'bg-cyan-100 text-cyan-600',
  emerald: 'bg-emerald-100 text-emerald-600',
  pink: 'bg-pink-100 text-pink-600',
  amber: 'bg-amber-100 text-amber-600'
}

export function FeatureGrid() {
  return (
    <div className="py-12">
      <div className="text-center mb-12">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">
          Everything You Need to Deploy AI Workflows
        </h2>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          From development to production, our comprehensive documentation covers every aspect 
          of the Codegen AI Workflow Platform.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((feature) => {
          const Icon = feature.icon
          return (
            <Link
              key={feature.title}
              href={feature.href}
              className="group bg-white p-6 rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-md transition-all duration-200"
            >
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-4 ${colorClasses[feature.color as keyof typeof colorClasses]}`}>
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
                {feature.title}
              </h3>
              <p className="text-gray-600 text-sm">
                {feature.description}
              </p>
            </Link>
          )
        })}
      </div>
    </div>
  )
}

