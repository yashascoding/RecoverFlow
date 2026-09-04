import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight, CheckCircle2, Shield, Zap, Eye, Brain,
  Mail, BarChart3, ChevronDown, Play, AlertTriangle,
  Search, Clock, Bot, FileCheck, Lock, Activity
} from 'lucide-react'
import './landing.css'

function useInView(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null)
  const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setInView(true) }, { threshold })
    obs.observe(el)
    return () => obs.disconnect()
  }, [threshold])
  return { ref, inView }
}

function useCountUp(end: number, duration = 1200, inView = false) {
  const [val, setVal] = useState(0)
  useEffect(() => {
    if (!inView) return
    let start = 0
    const step = (ts: number) => {
      if (!start) start = ts
      const progress = Math.min((ts - start) / duration, 1)
      setVal(Math.round(progress * end))
      if (progress < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }, [end, duration, inView])
  return val
}

/* ─── Navbar ────────────────────────────────────────────────────────── */

function LandingNavbar() {
  const navigate = useNavigate()
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', h, { passive: true })
    return () => window.removeEventListener('scroll', h)
  }, [])

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? 'bg-background/80 backdrop-blur-xl border-b border-border' : 'bg-transparent'}`}>
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-blue-500 flex items-center justify-center text-white text-xs font-bold">RF</div>
          <span className="text-sm font-semibold text-foreground">RecoverFlow</span>
        </div>
        <div className="hidden md:flex items-center gap-6">
          {['Product', 'How It Works', 'Safety', 'Results', 'FAQ'].map(s => (
            <a key={s} href={`#${s.toLowerCase().replace(/ /g, '-')}`} className="text-[13px] text-muted-foreground hover:text-foreground transition-colors">{s}</a>
          ))}
        </div>
        <button
          onClick={() => navigate('/login')}
          className="px-4 py-1.5 rounded-md bg-white text-black text-[13px] font-medium hover:bg-white/90 transition-colors"
        >
          Get Started
        </button>
      </div>
    </nav>
  )
}

/* ─── Hero ──────────────────────────────────────────────────────────── */

const pipelineSteps = [
  { label: 'PAYMENT FAILED', color: 'text-red-400', icon: AlertTriangle },
  { label: 'REVENUE SENTINEL', color: 'text-amber-400', icon: Eye },
  { label: 'AI INVESTIGATOR', color: 'text-blue-400', icon: Bot },
  { label: 'DIAGNOSIS', color: 'text-blue-400', icon: Brain },
  { label: 'POLICY FIREWALL', color: 'text-emerald-400', icon: Shield },
  { label: 'RECOVERY EMAIL', color: 'text-blue-400', icon: Mail },
  { label: 'RAZORPAY', color: 'text-blue-500', icon: Zap },
  { label: '₹2,499 RECOVERED', color: 'text-emerald-400', icon: CheckCircle2 },
]

function HeroPipeline() {
  const [active, setActive] = useState(0)

  useEffect(() => {
    const iv = setInterval(() => setActive(a => (a + 1) % pipelineSteps.length), 1800)
    return () => clearInterval(iv)
  }, [])

  return (
    <div className="relative bg-[#0c0c0e] border border-border rounded-lg p-6 font-mono text-[12px]">
      <div className="absolute top-3 right-3 flex items-center gap-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
        <span className="text-[10px] text-muted-foreground">LIVE</span>
      </div>
      <div className="space-y-1">
        {pipelineSteps.map((step, i) => {
          const Icon = step.icon
          const isActive = i === active
          const isPast = i < active
          return (
            <div key={i} className="flex items-center gap-3">
              <div className={`transition-all duration-300 ${isActive ? 'scale-110' : isPast ? 'opacity-60' : 'opacity-30'}`}>
                <Icon className={`w-3.5 h-3.5 ${step.color}`} />
              </div>
              <span className={`transition-all duration-300 ${isActive ? step.color + ' font-semibold' : isPast ? 'text-muted-foreground' : 'text-muted-foreground/40'}`}>
                {step.label}
              </span>
              {isActive && (
                <span className="ml-auto text-[10px] text-muted-foreground animate-pulse">●</span>
              )}
              {isPast && (
                <CheckCircle2 className="ml-auto w-3 h-3 text-emerald-500/50" />
              )}
            </div>
          )
        })}
      </div>
      <div className="mt-4 pt-3 border-t border-border flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground">pipeline.active</span>
        <span className="text-[10px] text-emerald-400">recovery.initiated</span>
      </div>
    </div>
  )
}

function Typewriter() {
  const fullText = "Failed payments don't have to become lost revenue."
  const [displayed, setDisplayed] = useState('')
  const [done, setDone] = useState(false)

  useEffect(() => {
    let i = 0
    const iv = setInterval(() => {
      i++
      setDisplayed(fullText.slice(0, i))
      if (i >= fullText.length) {
        clearInterval(iv)
        setDone(true)
      }
    }, 50)
    return () => clearInterval(iv)
  }, [])

  return (
    <span>
      {displayed}
      <span className={`inline-block w-[3px] h-[1em] bg-blue-500 ml-0.5 align-middle ${done ? 'animate-pulse' : ''}`} />
    </span>
  )
}

function Hero() {
  const navigate = useNavigate()
  return (
    <section className="relative min-h-[650px] overflow-hidden pt-32 pb-20 px-6">
      {/* Background video */}
      <video
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
        className="absolute inset-0 h-full w-full object-cover opacity-[0.35]"
      >
        <source src="/videos/payment.mp4" type="video/mp4" />
      </video>

      {/* Darkening layer */}
      <div className="absolute inset-0 bg-black/20" />

      {/* Blue atmospheric glow */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,rgba(37,99,235,0.18),transparent_60%)]" />

      {/* Existing UI */}
      <div className="relative z-10 max-w-6xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-border bg-secondary/30 text-[11px] text-muted-foreground mb-6 backdrop-blur-sm">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Autonomous payment recovery
            </div>
            <h1 className="text-4xl md:text-5xl font-bold text-foreground leading-tight tracking-tight">
              <Typewriter />
            </h1>
            <p className="mt-5 text-lg text-muted-foreground leading-relaxed max-w-xl">
              RecoverFlow autonomously investigates payment failures, makes policy-safe recovery decisions, contacts customers, and measures the revenue recovered.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <button
                onClick={() => navigate('/login')}
                className="px-6 py-3 rounded-md bg-white text-black text-sm font-semibold hover:bg-white/90 transition-colors inline-flex items-center gap-2"
              >
                Get Started
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => document.getElementById('real-recovery-story')?.scrollIntoView({ behavior: 'smooth' })}
                className="px-6 py-3 rounded-md border border-border text-sm font-medium text-foreground hover:bg-secondary/50 transition-colors inline-flex items-center gap-2 backdrop-blur-sm"
              >
                <Play className="w-3.5 h-3.5" />
                Watch Recovery Flow
              </button>
            </div>
          </div>
          <div className="hidden lg:block">
            <HeroPipeline />
          </div>
        </div>
      </div>
    </section>
  )
}

/* ─── Problem / Solution ────────────────────────────────────────────── */

function ProblemSolution() {
  const { ref, inView } = useInView()
  const cards = [
    { icon: Eye, title: 'Detect', desc: 'Automatically detect failed payment events and identify revenue at risk.' },
    { icon: Brain, title: 'Understand', desc: 'Investigate customer, payment, history, gateway, bank, region and failure context.' },
    { icon: CheckCircle2, title: 'Recover', desc: 'Select a policy-approved recovery strategy, communicate with the customer, and verify successful payment.' },
  ]
  return (
    <section id="product" ref={ref} className="py-24 px-6 landing-section">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight max-w-2xl">
          A failed payment is more than an error. It's revenue at risk.
        </h2>
        <div className="mt-14 grid md:grid-cols-3 gap-6">
          {cards.map((c, i) => {
            const Icon = c.icon
            return (
              <div
                key={i}
                className={`rounded-lg border border-border bg-card p-6 transition-all duration-500 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
                style={{ transitionDelay: `${i * 100}ms` }}
              >
                <div className="w-9 h-9 rounded-md bg-blue-500/10 flex items-center justify-center mb-4">
                  <Icon className="w-4.5 h-4.5 text-blue-400" />
                </div>
                <h3 className="text-sm font-semibold text-foreground mb-2">{c.title}</h3>
                <p className="text-[13px] text-muted-foreground leading-relaxed">{c.desc}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

/* ─── Product Showcase ──────────────────────────────────────────────── */

function ProductShowcase() {
  const { ref, inView } = useInView()
  return (
    <section id="showcase" ref={ref} className="py-24 px-6 landing-section">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          See recovery happen in real time.
        </h2>
        <div className={`mt-14 transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          {/* Dashboard mockup */}
          <div className="bg-[#0c0c0e] border border-border rounded-lg overflow-hidden">
            {/* Title bar */}
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border">
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]" />
                <div className="w-2.5 h-2.5 rounded-full bg-[#febc2e]" />
                <div className="w-2.5 h-2.5 rounded-full bg-[#28c840]" />
              </div>
              <span className="text-[11px] text-muted-foreground ml-2 font-mono">RecoverFlow — Dashboard</span>
            </div>
            {/* Content */}
            <div className="p-5">
              {/* Metrics row */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                {[
                  { label: 'Revenue At Risk', value: '₹38,520', color: 'text-amber-400' },
                  { label: 'Recovered Revenue', value: '₹96,420', color: 'text-emerald-400' },
                  { label: 'Failed Payments', value: '47', color: 'text-red-400' },
                  { label: 'Recovery Rate', value: '72.3%', color: 'text-blue-400' },
                ].map((m, i) => (
                  <div key={i} className="bg-secondary/30 rounded-md p-3">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{m.label}</p>
                    <p className={`text-lg font-bold font-mono mt-1 ${m.color}`}>{m.value}</p>
                  </div>
                ))}
              </div>
              {/* Payment detail */}
              <div className="bg-secondary/20 rounded-md p-4 border border-border">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[12px] font-mono text-muted-foreground">pay_8291</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-red-500/15 text-red-400 border border-red-500/20">FAILED</span>
                    </div>
                    <p className="text-sm font-medium text-foreground mt-1">Rahul Sharma — ₹2,499</p>
                  </div>
                  <span className="text-[10px] text-muted-foreground font-mono">UPI_TIMEOUT</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { label: 'AI Diagnosis', value: 'UPI timeout detected', icon: Brain },
                    { label: 'Confidence', value: '91%', icon: Activity },
                    { label: 'Recommended Action', value: 'EMAIL_PAYMENT_LINK', icon: Mail },
                    { label: 'Recovery', value: 'RECOVERED', icon: CheckCircle2, color: 'text-emerald-400' },
                  ].map((d, i) => {
                    const Icon = d.icon
                    return (
                      <div key={i} className="bg-background/50 rounded-md p-2.5">
                        <div className="flex items-center gap-1.5 mb-1">
                          <Icon className="w-3 h-3 text-muted-foreground" />
                          <span className="text-[10px] text-muted-foreground uppercase">{d.label}</span>
                        </div>
                        <p className={`text-[12px] font-mono font-medium ${d.color || 'text-foreground'}`}>{d.value}</p>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ─── Agent Trace ───────────────────────────────────────────────────── */

function AgentTrace() {
  const { ref, inView } = useInView()
  const [expanded, setExpanded] = useState<number | null>(null)

  const steps = [
    { name: 'OBSERVE', status: 'completed', tool: 'fetch_payment', args: '{ payment_id: "pay_8291" }', result: '{ status: "failed", amount: 249900, failure: "UPI_TIMEOUT" }', latency: '12ms' },
    { name: 'INVESTIGATE', status: 'completed', tool: 'check_consent', args: '{ customer_id: "cust_041", channel: "email" }', result: '{ consented: true, previous_payments: 3 }', latency: '8ms' },
    { name: 'DIAGNOSE', status: 'completed', tool: 'diagnose_failure', args: '{ failure_reason: "UPI_TIMEOUT", history: [...] }', result: '{ diagnosis: "upi_timeout", confidence: 0.91, risk: "LOW" }', latency: '890ms' },
    { name: 'PLAN', status: 'completed', tool: 'recommend_action', args: '{ diagnosis: "upi_timeout", consent: true }', result: '{ action: "EMAIL_PAYMENT_LINK", reason: "Temporary failure, good history" }', latency: '45ms' },
    { name: 'POLICY', status: 'completed', tool: 'evaluate_policy', args: '{ action: "EMAIL_PAYMENT_LINK", amount: 249900 }', result: '{ max_auto: PASS, consent: PASS, daily_limit: PASS }', latency: '3ms' },
    { name: 'EXECUTE', status: 'completed', tool: 'send_recovery_email', args: '{ to: "rahul.sharma@...", template: "payment_failure" }', result: '{ message_id: "msg_8291", provider: "resend", delivered: true }', latency: '230ms' },
    { name: 'VERIFY', status: 'completed', tool: 'check_payment_status', args: '{ order_id: "order_8291" }', result: '{ status: "recovered", amount: 249900, recovered_at: "..." }', latency: '15ms' },
  ]

  return (
    <section id="how-it-works" ref={ref} className="py-24 px-6 landing-section">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          Every AI decision is observable.
        </h2>
        <p className="text-center text-muted-foreground mt-3 max-w-xl mx-auto">
          Full agent trace with tool calls, arguments, results, and timing for every recovery decision.
        </p>
        <div className={`mt-14 max-w-2xl mx-auto transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          <div className="bg-[#0c0c0e] border border-border rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-border flex items-center gap-2">
              <Bot className="w-4 h-4 text-blue-400" />
              <span className="text-[12px] font-mono text-foreground">Agent Trace — pay_8291</span>
              <span className="ml-auto text-[10px] text-emerald-400 font-mono">COMPLETED</span>
            </div>
            <div className="divide-y divide-border">
              {steps.map((step, i) => {
                const isExpanded = expanded === i
                return (
                  <div key={i}>
                    <button
                      onClick={() => setExpanded(isExpanded ? null : i)}
                      className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-secondary/20 transition-colors"
                    >
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span className="text-[12px] font-mono font-medium text-foreground flex-1">{step.name}</span>
                      <span className="text-[10px] text-muted-foreground font-mono">{step.latency}</span>
                      <ChevronDown className={`w-3.5 h-3.5 text-muted-foreground transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                    </button>
                    {isExpanded && (
                      <div className="px-4 pb-3 ml-7 space-y-2 animate-slide-in">
                        <div>
                          <span className="text-[9px] text-muted-foreground uppercase tracking-wider">Tool</span>
                          <p className="text-[11px] font-mono text-foreground">{step.tool}</p>
                        </div>
                        <div>
                          <span className="text-[9px] text-muted-foreground uppercase tracking-wider">Arguments</span>
                          <p className="text-[11px] font-mono text-muted-foreground">{step.args}</p>
                        </div>
                        <div>
                          <span className="text-[9px] text-muted-foreground uppercase tracking-wider">Result</span>
                          <p className="text-[11px] font-mono text-emerald-400/80">{step.result}</p>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ─── How It Works ──────────────────────────────────────────────────── */

function HowItWorks() {
  const { ref, inView } = useInView()
  const steps = [
    { num: '01', title: 'Detect', desc: 'Payment failure arrives', icon: AlertTriangle },
    { num: '02', title: 'Investigate', desc: 'Analyze payment and customer context', icon: Search },
    { num: '03', title: 'Diagnose', desc: 'Determine likely failure cause', icon: Brain },
    { num: '04', title: 'Decide', desc: 'Select recovery strategy', icon: Zap },
    { num: '05', title: 'Protect', desc: 'Policy Firewall validates the action', icon: Shield },
    { num: '06', title: 'Recover', desc: 'Send secure payment link', icon: Mail },
    { num: '07', title: 'Verify', desc: 'Confirm successful payment', icon: CheckCircle2 },
    { num: '08', title: 'Measure', desc: 'Calculate recovered revenue', icon: BarChart3 },
  ]
  return (
    <section ref={ref} className="py-24 px-6 landing-section">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          From payment failure to recovered revenue.
        </h2>
        <div className="mt-14 grid md:grid-cols-4 gap-4">
          {steps.map((s, i) => {
            const Icon = s.icon
            return (
              <div
                key={i}
                className={`relative rounded-lg border border-border bg-card p-5 transition-all duration-500 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
                style={{ transitionDelay: `${i * 80}ms` }}
              >
                <span className="text-[10px] text-muted-foreground font-mono">{s.num}</span>
                <div className="mt-2 flex items-center gap-2">
                  <Icon className="w-4 h-4 text-blue-400" />
                  <h3 className="text-sm font-semibold text-foreground">{s.title}</h3>
                </div>
                <p className="text-[13px] text-muted-foreground mt-1.5">{s.desc}</p>
                {i < steps.length - 1 && (
                  <div className="hidden md:block absolute top-1/2 -right-2 w-4 h-px bg-border" />
                )}
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

/* ─── Differentiation ───────────────────────────────────────────────── */

function Differentiation() {
  const { ref, inView } = useInView()
  const rows = [
    { traditional: 'Blad retries', rf: 'Context-aware recovery' },
    { traditional: 'Manual investigation', rf: 'AI investigation' },
    { traditional: 'Static rules', rf: 'AI + deterministic policy' },
    { traditional: 'Limited visibility', rf: 'Full agent trace' },
    { traditional: 'No recovery attribution', rf: 'Recovered revenue metrics' },
    { traditional: 'Hard to audit', rf: 'Complete audit trail' },
  ]
  return (
    <section ref={ref} className="py-24 px-6 landing-section">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          Not just retry. Recover intelligently.
        </h2>
        <div className={`mt-14 rounded-lg border border-border bg-card overflow-hidden transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          <div className="grid grid-cols-2 border-b border-border">
            <div className="px-5 py-3 text-[11px] text-muted-foreground uppercase tracking-wider font-medium">Traditional Recovery</div>
            <div className="px-5 py-3 text-[11px] text-blue-400 uppercase tracking-wider font-medium">RecoverFlow</div>
          </div>
          {rows.map((r, i) => (
            <div key={i} className={`grid grid-cols-2 ${i < rows.length - 1 ? 'border-b border-border' : ''}`}>
              <div className="px-5 py-3 text-[13px] text-muted-foreground">{r.traditional}</div>
              <div className="px-5 py-3 text-[13px] text-foreground font-medium flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                {r.rf}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── Policy Firewall ───────────────────────────────────────────────── */

function PolicyFirewall() {
  const { ref, inView } = useInView()
  const controls = [
    { icon: Lock, title: 'Consent Required', desc: 'No recovery email without customer consent.' },
    { icon: Shield, title: 'Financial Limits', desc: 'High-value payments can require human review.' },
    { icon: AlertTriangle, title: 'Kill Switch', desc: 'Stop automated recovery immediately.' },
    { icon: FileCheck, title: 'Complete Audit', desc: 'Record who, what, why, policy and result.' },
  ]
  return (
    <section id="safety" ref={ref} className="py-24 px-6 landing-section">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          Autonomous doesn't mean uncontrolled.
        </h2>
        <p className="text-center text-muted-foreground mt-3 max-w-xl mx-auto">
          Every AI action passes through a deterministic policy firewall before execution.
        </p>

        {/* Visual diagram */}
        <div className={`mt-14 flex flex-col items-center transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          <div className="bg-[#0c0c0e] border border-border rounded-lg p-6 w-full max-w-lg">
            <div className="text-center mb-4">
              <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-blue-500/10 border border-blue-500/20 text-[12px] font-mono text-blue-400">
                <Bot className="w-3.5 h-3.5" />
                AI AGENT
              </span>
            </div>
            <div className="flex justify-center mb-4">
              <div className="w-px h-6 bg-border" />
            </div>
            <div className="text-center mb-4">
              <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-[12px] font-mono text-amber-400">
                <Shield className="w-3.5 h-3.5" />
                POLICY FIREWALL
              </span>
            </div>
            <div className="flex justify-center mb-4">
              <div className="w-px h-6 bg-border" />
            </div>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'ALLOW', color: 'emerald' },
                { label: 'BLOCK', color: 'red' },
                { label: 'REVIEW', color: 'amber' },
              ].map((r) => (
                <div key={r.label} className={`text-center px-3 py-2 rounded-md bg-${r.color}-500/10 border border-${r.color}-500/20`}>
                  <span className={`text-[11px] font-mono text-${r.color}-400`}>{r.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="mt-10 grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {controls.map((c, i) => {
            const Icon = c.icon
            return (
              <div
                key={i}
                className={`rounded-lg border border-border bg-card p-5 transition-all duration-500 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
                style={{ transitionDelay: `${200 + i * 80}ms` }}
              >
                <Icon className="w-5 h-5 text-muted-foreground mb-3" />
                <h3 className="text-sm font-semibold text-foreground mb-1">{c.title}</h3>
                <p className="text-[13px] text-muted-foreground">{c.desc}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

/* ─── Results / Evaluation ──────────────────────────────────────────── */

function Results() {
  const { ref, inView } = useInView()
  const control = useCountUp(12, 1200, inView)
  const rf = useCountUp(21, 1200, inView)
  const lift = useCountUp(75, 1200, inView)
  const revenue = useCountUp(96, 1200, inView)

  return (
    <section id="results" ref={ref} className="py-24 px-6 landing-section">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          Does RecoverFlow actually recover more money?
        </h2>
        <div className={`mt-14 grid md:grid-cols-3 gap-6 transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          <div className="rounded-lg border border-border bg-card p-6 text-center">
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Control Recovery Rate</p>
            <p className="text-4xl font-bold text-muted-foreground font-mono mt-3">{control}%</p>
          </div>
          <div className="rounded-lg border border-blue-500/30 bg-blue-500/5 p-6 text-center">
            <p className="text-[11px] text-blue-400 uppercase tracking-wider">RecoverFlow Recovery Rate</p>
            <p className="text-4xl font-bold text-blue-400 font-mono mt-3">{rf}%</p>
          </div>
          <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-6 text-center">
            <p className="text-[11px] text-emerald-400 uppercase tracking-wider">Recovery Lift</p>
            <p className="text-4xl font-bold text-emerald-400 font-mono mt-3">+{lift}%</p>
          </div>
        </div>
        <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Recovered Revenue', value: `₹${revenue},420` },
            { label: 'Revenue At Risk', value: '₹38,520' },
            { label: 'AI Cost', value: '₹0.02/run' },
            { label: 'Net Recovered', value: `₹${revenue},418` },
          ].map((m, i) => (
            <div key={i} className="rounded-lg border border-border bg-card p-4 text-center">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{m.label}</p>
              <p className="text-lg font-bold font-mono text-foreground mt-1">{m.value}</p>
            </div>
          ))}
        </div>
        <p className="text-center text-[11px] text-muted-foreground mt-6">
          Measured using a control group and held-out recovery cases.
        </p>
      </div>
    </section>
  )
}

/* ─── Real Recovery Story ───────────────────────────────────────────── */

function RealRecoveryStory() {
  const { ref, inView } = useInView()
  const steps = [
    { label: '₹2,499 PAYMENT', icon: AlertTriangle, color: 'text-amber-400' },
    { label: 'UPI TIMEOUT', icon: Clock, color: 'text-red-400' },
    { label: 'AI DIAGNOSIS', sub: '91% CONFIDENCE', icon: Brain, color: 'text-blue-400' },
    { label: 'POLICY ALLOWED', icon: Shield, color: 'text-emerald-400' },
    { label: 'RECOVERY EMAIL SENT', icon: Mail, color: 'text-blue-400' },
    { label: 'CUSTOMER RETRIES', icon: Zap, color: 'text-blue-400' },
    { label: 'RAZORPAY PAYMENT CAPTURED', icon: CheckCircle2, color: 'text-emerald-400' },
    { label: '₹2,499 RECOVERED', icon: CheckCircle2, color: 'text-emerald-400' },
  ]

  return (
    <section id="real-recovery-story" ref={ref} className="py-24 px-6 landing-section">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          One real recovery, start to finish.
        </h2>
        <div className={`mt-14 transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          <div className="bg-[#0c0c0e] border border-border rounded-lg p-6">
            <div className="space-y-0">
              {steps.map((s, i) => {
                const Icon = s.icon
                const isLast = i === steps.length - 1
                return (
                  <div key={i} className="relative">
                    <div className="flex items-center gap-4">
                      <div className="flex flex-col items-center">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${isLast ? 'bg-emerald-500/15 border border-emerald-500/30' : 'bg-secondary/50 border border-border'}`}>
                          <Icon className={`w-4 h-4 ${s.color}`} />
                        </div>
                        {!isLast && <div className="w-px h-8 bg-border" />}
                      </div>
                      <div className="flex-1 pb-6">
                        <p className={`text-[13px] font-mono font-medium ${isLast ? 'text-emerald-400 text-base font-bold' : 'text-foreground'}`}>
                          {s.label}
                        </p>
                        {s.sub && <p className="text-[11px] text-muted-foreground font-mono mt-0.5">{s.sub}</p>}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ─── FAQ ───────────────────────────────────────────────────────────── */

function FAQ() {
  const [open, setOpen] = useState<number | null>(null)
  const faqs = [
    { q: 'Does RecoverFlow control payments directly?', a: 'No. Recovery actions are constrained by the policy layer and payment state machine.' },
    { q: 'What happens without customer consent?', a: 'Recovery communication is blocked. The pipeline stops before sending any email.' },
    { q: 'What happens with high-value payments?', a: 'They can be routed for human review according to configured policy thresholds.' },
    { q: 'Can decisions be replayed?', a: 'Yes. Events and agent actions are recorded for replay and investigation.' },
    { q: 'What happens if a webhook arrives twice?', a: 'Idempotency prevents duplicate side effects.' },
    { q: 'Can automation be stopped?', a: 'Yes. The global kill switch can block all automated recovery immediately.' },
  ]
  return (
    <section id="faq" className="py-24 px-6 landing-section">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          Frequently asked questions
        </h2>
        <div className="mt-10 space-y-1">
          {faqs.map((f, i) => (
            <div key={i} className="rounded-lg border border-border bg-card overflow-hidden">
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="w-full flex items-center justify-between px-5 py-4 text-left"
              >
                <span className="text-[13px] font-medium text-foreground pr-4">{f.q}</span>
                <ChevronDown className={`w-4 h-4 text-muted-foreground shrink-0 transition-transform ${open === i ? 'rotate-180' : ''}`} />
              </button>
              {open === i && (
                <div className="px-5 pb-4">
                  <p className="text-[13px] text-muted-foreground leading-relaxed">{f.a}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── Final CTA ─────────────────────────────────────────────────────── */

function FinalCTA() {
  const navigate = useNavigate()
  return (
    <section className="py-24 px-6 landing-section">
      <div className="max-w-3xl mx-auto text-center">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight">
          Turn failed payments into recovered revenue.
        </h2>
        <p className="mt-4 text-lg text-muted-foreground">
          See RecoverFlow detect, investigate, decide, recover, and measure a failed payment automatically.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <button
            onClick={() => navigate('/login')}
            className="px-7 py-3 rounded-md bg-white text-black text-sm font-semibold hover:bg-white/90 transition-colors inline-flex items-center gap-2"
          >
            Get Started
            <ArrowRight className="w-4 h-4" />
          </button>
          <button
            onClick={() => window.open('https://github.com', '_blank')}
            className="px-7 py-3 rounded-md border border-border text-sm font-medium text-foreground hover:bg-secondary/50 transition-colors"
          >
            View Architecture
          </button>
        </div>
      </div>
    </section>
  )
}

/* ─── Footer ────────────────────────────────────────────────────────── */

function Footer() {
  return (
    <footer className="border-t border-border py-10 px-6">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-blue-500 flex items-center justify-center text-white text-[10px] font-bold">RF</div>
          <span className="text-[13px] font-medium text-foreground">RecoverFlow</span>
        </div>
        <div className="flex items-center gap-6">
          {['Product', 'Architecture', 'GitHub', 'Documentation'].map(l => (
            <a key={l} href="#" className="text-[12px] text-muted-foreground hover:text-foreground transition-colors">{l}</a>
          ))}
        </div>
        <p className="text-[11px] text-muted-foreground">Built for autonomous payment recovery.</p>
      </div>
    </footer>
  )
}

/* ─── Landing Page ──────────────────────────────────────────────────── */

export function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <LandingNavbar />
      <Hero />
      <ProblemSolution />
      <ProductShowcase />
      <AgentTrace />
      <HowItWorks />
      <Differentiation />
      <PolicyFirewall />
      <Results />
      <RealRecoveryStory />
      <FAQ />
      <FinalCTA />
      <Footer />
    </div>
  )
}
