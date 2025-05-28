import './globals.css'
import { Inter } from 'next/font/google'
import { Sidebar } from '../components/Sidebar'
import { Header } from '../components/Header'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Codegen AI Workflow Platform Documentation',
  description: 'Comprehensive documentation and deployment guides for the Codegen AI Workflow Platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          <Header />
          <div className="flex">
            <Sidebar />
            <main className="flex-1 ml-64 p-8">
              <div className="max-w-4xl mx-auto">
                {children}
              </div>
            </main>
          </div>
        </div>
      </body>
    </html>
  )
}

