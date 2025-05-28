import { Hero } from '../components/Hero'
import { FeatureGrid } from '../components/FeatureGrid'
import { QuickStart } from '../components/QuickStart'

export default function HomePage() {
  return (
    <div className="space-y-12">
      <Hero />
      <FeatureGrid />
      <QuickStart />
    </div>
  )
}

