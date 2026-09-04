import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight, CheckCircle2, Shield, Zap, Eye, Brain,
  Mail, BarChart3, ChevronDown, Play, AlertTriangle,
  Search, Clock, Bot, FileCheck, Lock, Activity,
  Database, Cpu, Globe, Layers, Server, GitBranch
} from 'lucide-react'
import './landing.css'

/* ─── Hooks ────────────────────────────────────────────────────────────── */

function useInView(threshold = 0.12) {
  const ref = useRef<HTMLDivElement>(null)
  const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setInView(true) }, { threshold, rootMargin: '0px 0px -60px 0px' })
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
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${scrolled ? 'bg-background/80 backdrop-blur-xl border-b border-border shadow-lg shadow-black/5' : 'bg-transparent'}`}>
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <img src="/image.png" alt="RecoverFlow" className="w-7 h-7 rounded-md" />
          <span className="text-sm font-semibold text-foreground">RecoverFlow</span>
        </div>
        <div className="hidden md:flex items-center gap-6">
          {['Problem', 'How It Works', 'Safety', 'Results', 'FAQ'].map(s => (
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
  const fullText = "Failed payments silently become lost revenue."
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
    <section className="relative min-h-[730px] overflow-hidden pt-32 pb-20 px-6">
      <video
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
        className="absolute inset-0 h-full w-full object-cover opacity-[0.35]"
      >
        <source src="/videos/video.mp4" type="video/mp4" />
      </video>
      <div className="absolute inset-0 bg-black/20" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,rgba(37,99,235,0.18),transparent_60%)]" />
      <div className="relative z-10 max-w-6xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <h1 className="text-5xl md:text-6xl font-bold text-foreground leading-tight tracking-tight">
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
                onClick={() => document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' })}
                className="px-6 py-3 rounded-md border border-border text-sm font-medium text-foreground hover:bg-secondary/50 transition-colors inline-flex items-center gap-2 backdrop-blur-sm"
              >
                <Play className="w-3.5 h-3.5" />
                Watch Recovery
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

/* ─── Trust / Metrics ──────────────────────────────────────────────── */

function TrustMetrics() {
  const { ref, inView } = useInView()
  const recovered = useCountUp(96, 1200, inView)
  const rate = useCountUp(72, 1200, inView)
  const payments = useCountUp(47, 1200, inView)
  const cost = useCountUp(2, 1200, inView)

  const metrics = [
    { label: 'Revenue Recovered', value: `₹${recovered},420`, color: 'text-emerald-400' },
    { label: 'Recovery Rate', value: `${rate}%`, color: 'text-blue-400' },
    { label: 'Failed Payments Handled', value: `${payments}`, color: 'text-amber-400' },
    { label: 'AI Cost Per Run', value: `₹0.0${cost}`, color: 'text-muted-foreground' },
  ]

  return (
    <section ref={ref} className="py-16 px-6 border-y border-border bg-secondary/20">
      <div className="max-w-6xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8">
        {metrics.map((m, i) => (
          <div
            key={i}
            className={`text-center transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
            style={{ transitionDelay: `${i * 100}ms` }}
          >
            <p className="text-3xl md:text-4xl font-bold font-mono mt-1">{m.value}</p>
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider mt-2">{m.label}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

/* ─── The Problem ──────────────────────────────────────────────────── */

function TheProblem() {
  const { ref, inView } = useInView()
  return (
    <section id="problem" ref={ref} className="py-24 px-6 landing-section">
      <div className="max-w-3xl mx-auto text-center">
        <div className={`transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight">
            "Failed payments silently become lost revenue."
          </h2>
          <p className="mt-6 text-lg text-muted-foreground leading-relaxed">
            Every failed transaction is a customer who wanted to pay you. Without automated recovery, those payments disappear — no retry, no follow-up, no revenue.
          </p>
          <div className="mt-10 grid md:grid-cols-3 gap-6">
            {[
              { stat: '23%', desc: 'of failed payments are never retried by customers' },
              { stat: '₹38K', desc: 'average monthly revenue lost per merchant to payment failures' },
              { stat: '4.2hrs', desc: 'average time before a manual team even notices a failure' },
            ].map((s, i) => (
              <div key={i} className="rounded-lg border border-border bg-card p-5" style={{ transitionDelay: `${i * 100}ms` }}>
                <p className="text-2xl font-bold font-mono text-red-400">{s.stat}</p>
                <p className="text-[13px] text-muted-foreground mt-2">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

/* ─── How RecoverFlow Works ────────────────────────────────────────── */

function HowItWorks() {
  const { ref, inView } = useInView()
  const steps = [
    { num: '01', title: 'Failure', desc: 'Payment fails at gateway', icon: AlertTriangle, color: 'text-red-400' },
    { num: '02', title: 'Detection', desc: 'Webhook triggers recovery pipeline', icon: Eye, color: 'text-amber-400' },
    { num: '03', title: 'Investigation', desc: 'AI analyzes payment, customer, and context', icon: Brain, color: 'text-blue-400' },
    { num: '04', title: 'Policy Check', desc: 'Deterministic firewall validates the action', icon: Shield, color: 'text-emerald-400' },
    { num: '05', title: 'Recovery', desc: 'Personalized email with payment link sent', icon: Mail, color: 'text-blue-400' },
  ]
  return (
    <section id="how-it-works" ref={ref} className="py-24 px-6 landing-section">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          How RecoverFlow works
        </h2>
        <p className="text-center text-muted-foreground mt-3 max-w-xl mx-auto">
          Five autonomous steps from failure to recovered revenue.
        </p>
        <div className="mt-14 flex flex-col md:flex-row items-start gap-4">
          {steps.map((s, i) => {
            const Icon = s.icon
            return (
              <div
                key={i}
                className={`flex-1 relative transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}
                style={{ transitionDelay: `${i * 120}ms` }}
              >
                <div className="rounded-lg border border-border bg-card p-5 h-full">
                  <span className="text-[10px] text-muted-foreground font-mono">{s.num}</span>
                  <div className="mt-3 flex items-center gap-2.5">
                    <div className={`w-9 h-9 rounded-md bg-secondary/50 flex items-center justify-center`}>
                      <Icon className={`w-4.5 h-4.5 ${s.color}`} />
                    </div>
                    <h3 className="text-sm font-semibold text-foreground">{s.title}</h3>
                  </div>
                  <p className="text-[13px] text-muted-foreground mt-2">{s.desc}</p>
                </div>
                {i < steps.length - 1 && (
                  <div className="hidden md:flex absolute top-1/2 -right-2 w-4 h-px bg-border items-center justify-center">
                    <div className="w-1 h-1 rounded-full bg-muted-foreground/40" />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

/* ─── Live Recovery Timeline ───────────────────────────────────────── */

function LiveTimeline() {
  const { ref, inView } = useInView()
  const [activeIdx, setActiveIdx] = useState(-1)

  useEffect(() => {
    if (!inView) return
    let idx = 0
    const iv = setInterval(() => {
      setActiveIdx(idx)
      idx++
      if (idx >= timelineEvents.length) {
        clearInterval(iv)
      }
    }, 600)
    return () => clearInterval(iv)
  }, [inView])

  const timelineEvents = [
    { time: '14:32:01', event: 'payment.failed', detail: 'order_8291 — ₹2,499 — UPI_TIMEOUT', icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10' },
    { time: '14:32:01', event: 'event.dispatched', detail: 'Razorpay webhook received, event persisted', icon: Zap, color: 'text-amber-400', bg: 'bg-amber-500/10' },
    { time: '14:32:02', event: 'worker.processing', detail: 'Event picked up by recovery worker', icon: Cpu, color: 'text-blue-400', bg: 'bg-blue-500/10' },
    { time: '14:32:03', event: 'consent.verified', detail: 'Customer has email consent — proceed', icon: Shield, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { time: '14:32:04', event: 'ai.diagnosis', detail: 'UPI timeout — confidence 91% — risk LOW', icon: Brain, color: 'text-blue-400', bg: 'bg-blue-500/10' },
    { time: '14:32:04', event: 'policy.evaluated', detail: 'ALLOW — max_auto: PASS, consent: PASS', icon: Shield, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { time: '14:32:05', event: 'email.sent', detail: 'Recovery email delivered via Resend', icon: Mail, color: 'text-blue-400', bg: 'bg-blue-500/10' },
    { time: '14:35:12', event: 'payment.recovered', detail: 'Customer retried — ₹2,499 captured', icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  ]

  return (
    <section ref={ref} className="py-24 px-6 landing-section bg-secondary/10">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          Live Recovery Timeline
        </h2>
        <p className="text-center text-muted-foreground mt-3 max-w-xl mx-auto">
          Actual event stream from a recovered payment — every step logged.
        </p>
        <div className={`mt-14 transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          <div className="bg-[#0c0c0e] border border-border rounded-lg overflow-hidden font-mono">
            <div className="px-4 py-3 border-b border-border flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[11px] text-muted-foreground">event_stream — pay_8291</span>
            </div>
            <div className="p-4 space-y-0">
              {timelineEvents.map((ev, i) => {
                const Icon = ev.icon
                const visible = i <= activeIdx
                return (
                  <div
                    key={i}
                    className={`flex items-start gap-3 py-2 transition-all duration-500 ${visible ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4'}`}
                  >
                    <span className="text-[10px] text-muted-foreground w-16 shrink-0 pt-0.5">{ev.time}</span>
                    <div className={`w-6 h-6 rounded-full ${ev.bg} flex items-center justify-center shrink-0`}>
                      <Icon className={`w-3 h-3 ${ev.color}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-[11px] font-medium ${ev.color}`}>{ev.event}</span>
                      </div>
                      <p className="text-[10px] text-muted-foreground mt-0.5 truncate">{ev.detail}</p>
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

/* ─── AI Investigation ─────────────────────────────────────────────── */

function AIInvestigation() {
  const { ref, inView } = useInView()
  const [expanded, setExpanded] = useState<number | null>(null)

  const steps = [
    { name: 'OBSERVE', tool: 'fetch_payment', args: '{ payment_id: "pay_8291" }', result: '{ status: "failed", amount: 249900, failure: "UPI_TIMEOUT" }', latency: '12ms' },
    { name: 'INVESTIGATE', tool: 'check_consent', args: '{ customer_id: "cust_041", channel: "email" }', result: '{ consented: true, previous_payments: 3 }', latency: '8ms' },
    { name: 'DIAGNOSE', tool: 'diagnose_failure', args: '{ failure_reason: "UPI_TIMEOUT", history: [...] }', result: '{ diagnosis: "upi_timeout", confidence: 0.91, risk: "LOW" }', latency: '890ms' },
    { name: 'PLAN', tool: 'recommend_action', args: '{ diagnosis: "upi_timeout", consent: true }', result: '{ action: "EMAIL_PAYMENT_LINK", reason: "Temporary failure, good history" }', latency: '45ms' },
    { name: 'EXECUTE', tool: 'send_recovery_email', args: '{ to: "rahul.sharma@...", template: "payment_failure" }', result: '{ message_id: "msg_8291", delivered: true }', latency: '230ms' },
  ]

  return (
    <section ref={ref} className="py-24 px-6 landing-section">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          AI Investigation
        </h2>
        <p className="text-center text-muted-foreground mt-3 max-w-xl mx-auto">
          Every diagnosis includes reasoning, confidence, and full tool trace.
        </p>
        <div className="mt-14 grid lg:grid-cols-2 gap-8 items-start">
          {/* Diagnosis Summary */}
          <div className={`transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
            <div className="bg-[#0c0c0e] border border-border rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4">
                <Brain className="w-4 h-4 text-blue-400" />
                <span className="text-[12px] font-mono text-foreground">diagnosis.summary</span>
              </div>
              <div className="space-y-3">
                {[
                  { label: 'Failure Type', value: 'UPI_TIMEOUT', color: 'text-amber-400' },
                  { label: 'Confidence', value: '91%', color: 'text-emerald-400' },
                  { label: 'Risk Level', value: 'LOW', color: 'text-emerald-400' },
                  { label: 'Root Cause', value: 'Temporary bank gateway timeout', color: 'text-foreground' },
                  { label: 'Customer History', value: '3 successful payments, 0 previous failures', color: 'text-foreground' },
                  { label: 'Recommendation', value: 'EMAIL_PAYMENT_LINK', color: 'text-blue-400' },
                  { label: 'Reasoning', value: 'Temporary failure with good payment history — email recovery appropriate', color: 'text-muted-foreground' },
                ].map((r, i) => (
                  <div key={i} className="flex items-start justify-between gap-4">
                    <span className="text-[11px] text-muted-foreground shrink-0">{r.label}</span>
                    <span className={`text-[11px] font-mono text-right ${r.color}`}>{r.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Agent Trace */}
          <div className={`transition-all duration-700 delay-200 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
            <div className="bg-[#0c0c0e] border border-border rounded-lg overflow-hidden">
              <div className="px-4 py-3 border-b border-border flex items-center gap-2">
                <Bot className="w-4 h-4 text-blue-400" />
                <span className="text-[12px] font-mono text-foreground">agent.trace</span>
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
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        <span className="text-[11px] font-mono font-medium text-foreground flex-1">{step.name}</span>
                        <span className="text-[10px] text-muted-foreground font-mono">{step.latency}</span>
                        <ChevronDown className={`w-3.5 h-3.5 text-muted-foreground transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                      </button>
                      {isExpanded && (
                        <div className="px-4 pb-3 ml-6 space-y-2 animate-slide-in">
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
      </div>
    </section>
  )
}

/* ─── Policy Firewall ───────────────────────────────────────────────── */

function PolicyFirewall() {
  const { ref, inView } = useInView()
  const controls = [
    { icon: Lock, title: 'Consent Required', desc: 'No recovery email without customer consent.' },
    { icon: Shield, title: 'Financial Limits', desc: 'High-value payments require human review.' },
    { icon: AlertTriangle, title: 'Kill Switch', desc: 'Stop automated recovery immediately.' },
    { icon: FileCheck, title: 'Complete Audit', desc: 'Record who, what, why, policy and result.' },
  ]
  return (
    <section id="safety" ref={ref} className="py-24 px-6 landing-section bg-secondary/10">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          Policy Firewall
        </h2>
        <p className="text-center text-muted-foreground mt-3 max-w-xl mx-auto">
          Autonomous doesn't mean uncontrolled. Every AI action passes through deterministic policy checks.
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

/* ─── Recovery Dashboard ───────────────────────────────────────────── */

function RecoveryDashboard() {
  const { ref, inView } = useInView()
  return (
    <section ref={ref} className="py-24 px-6 landing-section">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          Recovery Dashboard
        </h2>
        <p className="text-center text-muted-foreground mt-3 max-w-xl mx-auto">
          Real-time visibility into recovered revenue, attempts, and success rate.
        </p>
        <div className={`mt-14 transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          <div className="bg-[#0c0c0e] border border-border rounded-lg overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border">
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]" />
                <div className="w-2.5 h-2.5 rounded-full bg-[#febc2e]" />
                <div className="w-2.5 h-2.5 rounded-full bg-[#28c840]" />
              </div>
              <span className="text-[11px] text-muted-foreground ml-2 font-mono">RecoverFlow — Dashboard</span>
            </div>
            <div className="p-5">
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
                    { label: 'Action', value: 'EMAIL_PAYMENT_LINK', icon: Mail },
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

/* ─── Architecture ─────────────────────────────────────────────────── */

function Architecture() {
  const { ref, inView } = useInView()
  const layers = [
    { label: 'PostgreSQL', desc: 'Event store, payments, audit trail', icon: Database, color: 'text-blue-400' },
    { label: 'Redis', desc: 'Event queue, dedup, rate limiting', icon: Server, color: 'text-red-400' },
    { label: 'Workers', desc: 'Async event processing', icon: Cpu, color: 'text-amber-400' },
    { label: 'LangGraph', desc: 'AI agent orchestration', icon: Brain, color: 'text-blue-400' },
    { label: 'Razorpay', desc: 'Payment links & capture', icon: Zap, color: 'text-blue-500' },
    { label: 'Resend', desc: 'Transactional email delivery', icon: Mail, color: 'text-emerald-400' },
  ]
  return (
    <section ref={ref} className="py-24 px-6 landing-section bg-secondary/10">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          Architecture
        </h2>
        <p className="text-center text-muted-foreground mt-3 max-w-xl mx-auto">
          Event-driven, auditable, and built on proven infrastructure.
        </p>
        <div className={`mt-14 transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          <div className="bg-[#0c0c0e] border border-border rounded-lg p-6">
            <div className="flex flex-col items-center gap-0">
              {layers.map((l, i) => {
                const Icon = l.icon
                return (
                  <div key={i} className="w-full max-w-md">
                    <div className={`flex items-center gap-3 px-4 py-3 rounded-md border border-border bg-secondary/20 transition-all duration-500 ${inView ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4'}`} style={{ transitionDelay: `${i * 100}ms` }}>
                      <Icon className={`w-4 h-4 ${l.color} shrink-0`} />
                      <div className="flex-1">
                        <span className="text-[12px] font-mono font-medium text-foreground">{l.label}</span>
                        <span className="text-[11px] text-muted-foreground ml-2">{l.desc}</span>
                      </div>
                    </div>
                    {i < layers.length - 1 && (
                      <div className="flex justify-center py-1">
                        <div className="w-px h-4 bg-border" />
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

/* ─── Demo ─────────────────────────────────────────────────────────── */

function Demo() {
  const { ref, inView } = useInView()
  const [step, setStep] = useState(0)

  const demoSteps = [
    { label: 'Payment fails', detail: 'Razorpay webhook: order_8291, ₹2,499, UPI_TIMEOUT', icon: AlertTriangle, color: 'text-red-400' },
    { label: 'AI investigates', detail: 'Analyzing failure pattern, customer history, consent status', icon: Brain, color: 'text-blue-400' },
    { label: 'Policy approves', detail: 'Consent: PASS | Amount: PASS | Daily limit: PASS', icon: Shield, color: 'text-emerald-400' },
    { label: 'Email sent', detail: 'Personalized recovery email with Razorpay payment link', icon: Mail, color: 'text-blue-400' },
    { label: 'Customer pays', detail: 'Payment link clicked → ₹2,499 captured via Razorpay', icon: CheckCircle2, color: 'text-emerald-400' },
    { label: 'Revenue recovered', detail: '₹2,499 moved from "at risk" to "recovered"', icon: BarChart3, color: 'text-emerald-400' },
  ]

  useEffect(() => {
    if (!inView) return
    let i = 0
    const iv = setInterval(() => {
      setStep(i)
      i++
      if (i >= demoSteps.length) {
        setTimeout(() => { i = 0; setStep(0) }, 2000)
      }
    }, 1500)
    return () => clearInterval(iv)
  }, [inView])

  return (
    <section id="demo" ref={ref} className="py-24 px-6 landing-section">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          Watch a failed payment become recovered
        </h2>
        <div className={`mt-14 transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          <div className="bg-[#0c0c0e] border border-border rounded-lg p-6">
            <div className="space-y-0">
              {demoSteps.map((s, i) => {
                const Icon = s.icon
                const isActive = i === step
                const isPast = i < step
                return (
                  <div key={i} className={`flex items-center gap-4 py-2.5 transition-all duration-400 ${isActive ? 'opacity-100' : isPast ? 'opacity-50' : 'opacity-20'}`}>
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all duration-300 ${isActive ? 'bg-secondary border border-border scale-110' : isPast ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-secondary/30 border border-border'}`}>
                      {isPast ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Icon className={`w-4 h-4 ${isActive ? s.color : 'text-muted-foreground'}`} />}
                    </div>
                    <div className="flex-1">
                      <p className={`text-[13px] font-medium ${isActive ? 'text-foreground' : 'text-muted-foreground'}`}>{s.label}</p>
                      {isActive && <p className="text-[11px] text-muted-foreground mt-0.5 font-mono">{s.detail}</p>}
                    </div>
                    {isActive && <span className="text-[10px] text-emerald-400 font-mono animate-pulse">●</span>}
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

/* ─── Results / Evaluation ──────────────────────────────────────────── */

function Results() {
  const { ref, inView } = useInView()
  const control = useCountUp(12, 1200, inView)
  const rf = useCountUp(21, 1200, inView)
  const lift = useCountUp(75, 1200, inView)

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
        <p className="text-center text-[11px] text-muted-foreground mt-6">
          Measured using a control group and held-out recovery cases.
        </p>
      </div>
    </section>
  )
}

/* ─── FAQ ───────────────────────────────────────────────────────────── */

function FAQ() {
  const { ref, inView } = useInView()
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
    <section id="faq" ref={ref} className="py-24 px-6 landing-section">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-center">
          Frequently asked questions
        </h2>
        <div className={`mt-10 space-y-1 transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
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
  const { ref, inView } = useInView()
  return (
    <section ref={ref} className="py-24 px-6 landing-section">
      <div className={`max-w-3xl mx-auto text-center transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
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
            onClick={() => document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' })}
            className="px-7 py-3 rounded-md border border-border text-sm font-medium text-foreground hover:bg-secondary/50 transition-colors"
          >
            View Demo
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
          <img src="/image.png" alt="RecoverFlow" className="w-6 h-6 rounded" />
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
      <TrustMetrics />
      <TheProblem />
      <HowItWorks />
      <LiveTimeline />
      <AIInvestigation />
      <PolicyFirewall />
      <RecoveryDashboard />
      <Architecture />
      <Demo />
      <Results />
      <FAQ />
      <FinalCTA />
      <Footer />
    </div>
  )
}
