import { Terminal, Copy, Check } from 'lucide-react'
import { useState } from 'react'

export function QuickStart() {
  const [copied, setCopied] = useState<string | null>(null)

  const handleCopy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(id)
    setTimeout(() => setCopied(null), 2000)
  }

  const steps = [
    {
      id: 'install',
      title: 'Install Dependencies',
      command: 'curl -sSL https://install.codegen.sh | bash',
      description: 'Download and install the Codegen CLI and dependencies'
    },
    {
      id: 'configure',
      title: 'Configure Environment',
      command: 'codegen init --template=ai-workflow',
      description: 'Initialize a new AI workflow project with default configuration'
    },
    {
      id: 'deploy',
      title: 'Deploy Locally',
      command: 'codegen deploy --env=local',
      description: 'Start the platform locally with Docker Compose'
    }
  ]

  return (
    <div className="bg-gray-900 rounded-lg p-8 text-white">
      <div className="flex items-center space-x-3 mb-6">
        <Terminal className="h-6 w-6 text-green-400" />
        <h2 className="text-2xl font-bold">Quick Start</h2>
      </div>
      
      <p className="text-gray-300 mb-8">
        Get the Codegen AI Workflow Platform running in under 5 minutes.
      </p>

      <div className="space-y-6">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-start space-x-4">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-sm font-bold">
              {index + 1}
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold mb-2">{step.title}</h3>
              <p className="text-gray-300 text-sm mb-3">{step.description}</p>
              <div className="bg-gray-800 rounded-lg p-3 flex items-center justify-between">
                <code className="text-green-400 font-mono text-sm flex-1">
                  {step.command}
                </code>
                <button
                  onClick={() => handleCopy(step.command, step.id)}
                  className="ml-3 p-1 hover:bg-gray-700 rounded transition-colors"
                  title="Copy command"
                >
                  {copied === step.id ? (
                    <Check className="h-4 w-4 text-green-400" />
                  ) : (
                    <Copy className="h-4 w-4 text-gray-400" />
                  )}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 p-4 bg-blue-900/50 rounded-lg border border-blue-800">
        <h4 className="font-semibold mb-2">What's Next?</h4>
        <ul className="text-sm text-gray-300 space-y-1">
          <li>• Configure your first AI agent workflow</li>
          <li>• Set up GitHub integration for automated code reviews</li>
          <li>• Deploy to production with our cloud deployment guides</li>
        </ul>
      </div>
    </div>
  )
}

