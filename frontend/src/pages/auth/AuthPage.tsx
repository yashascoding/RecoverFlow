import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { login, register } from '@/api/auth'
import { ArrowRight, Eye, Brain, CheckCircle2, Shield, Zap, Mail } from 'lucide-react'

export function AuthPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuth()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'register') {
        const res = await register(email, password, name)
        setAuth(res.access_token, res.user)
      } else {
        const res = await login(email, password)
        setAuth(res.access_token, res.user)
      }
      navigate('/overview')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left: Branding */}
      <div className="hidden lg:flex flex-1 bg-card border-r border-border flex-col justify-between p-12 relative overflow-hidden">
        <div className="relative z-10">
          <Link to="/" className="flex items-center gap-2 mb-16">
            <div className="w-8 h-8 rounded-md bg-recovery flex items-center justify-center text-white text-sm font-bold">RF</div>
            <span className="text-base font-semibold text-foreground">RecoverFlow</span>
          </Link>

          <h1 className="text-3xl font-bold text-foreground leading-tight tracking-tight max-w-md">
            Turn failed payments into recovered revenue.
          </h1>
          <p className="mt-4 text-muted-foreground max-w-md leading-relaxed">
            Autonomous AI payment recovery for Indian D2C merchants. Detect, investigate, recover, and measure.
          </p>

          <div className="mt-12 space-y-4 max-w-sm">
            {[
              { icon: Eye, text: 'Detect failed payments automatically' },
              { icon: Brain, text: 'AI investigates root causes' },
              { icon: Shield, text: 'Policy firewall ensures safe recovery' },
              { icon: Mail, text: 'Contact customers with payment links' },
              { icon: CheckCircle2, text: 'Measure recovered revenue' },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-md bg-blue-500/10 flex items-center justify-center shrink-0">
                  <item.icon className="w-4 h-4 text-blue-400" />
                </div>
                <span className="text-[13px] text-muted-foreground">{item.text}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10">
          <div className="bg-secondary/30 border border-border rounded-lg p-4 max-w-sm">
            <div className="flex items-center gap-3 mb-2">
              <Zap className="w-4 h-4 text-amber-400" />
              <span className="text-[12px] font-medium text-foreground">Pipeline Active</span>
            </div>
            <div className="space-y-1.5 font-mono text-[11px]">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                <span className="text-muted-foreground">Payment failure detected</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                <span className="text-muted-foreground">AI investigation complete</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                <span className="text-muted-foreground">Recovery email sent</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full border border-blue-400/50" />
                <span className="text-blue-400">Awaiting customer action...</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right: Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <Link to="/" className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-md bg-recovery flex items-center justify-center text-white text-xs font-bold">RF</div>
              <span className="text-sm font-semibold text-foreground">RecoverFlow</span>
            </Link>
          </div>

          <h2 className="text-xl font-bold text-foreground">
            {mode === 'login' ? 'Welcome back' : 'Create your account'}
          </h2>
          <p className="text-[13px] text-muted-foreground mt-1.5">
            {mode === 'login'
              ? 'Sign in to access your merchant dashboard'
              : 'Get started with RecoverFlow'}
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4">
            {mode === 'register' && (
              <div>
                <label className="text-[12px] font-medium text-muted-foreground">Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="mt-1.5 h-10 w-full rounded-md border border-border bg-secondary/50 px-3 text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring transition-colors"
                  placeholder="Your name"
                />
              </div>
            )}
            <div>
              <label className="text-[12px] font-medium text-muted-foreground">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="mt-1.5 h-10 w-full rounded-md border border-border bg-secondary/50 px-3 text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring transition-colors"
                placeholder="merchant@example.com"
              />
            </div>
            <div>
              <label className="text-[12px] font-medium text-muted-foreground">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                className="mt-1.5 h-10 w-full rounded-md border border-border bg-secondary/50 px-3 text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring transition-colors"
                placeholder="At least 6 characters"
              />
            </div>

            {error && (
              <p className="text-[12px] text-red-400">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="h-10 w-full rounded-md bg-white text-black text-[13px] font-semibold hover:bg-white/90 transition-colors disabled:opacity-50 inline-flex items-center justify-center gap-2"
            >
              {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
              {!loading && <ArrowRight className="w-3.5 h-3.5" />}
            </button>
          </form>

          <p className="mt-6 text-center text-[13px] text-muted-foreground">
            {mode === 'login' ? "Don't have an account?" : 'Already have an account?'}{' '}
            <button
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
              className="text-foreground font-medium hover:underline"
            >
              {mode === 'login' ? 'Sign up' : 'Sign in'}
            </button>
          </p>

          <p className="mt-4 text-center">
            <Link to="/" className="text-[12px] text-muted-foreground hover:text-foreground transition-colors">
              Back to home
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
