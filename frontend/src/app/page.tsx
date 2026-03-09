"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import {
    ArrowRight, FileSearch, ShieldCheck, Zap, Activity, Cpu,
    Code2, LineChart, CheckCircle2, Globe, Landmark,
    BarChart3, MousePointer2, Sparkles, Building2, ShieldAlert
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const features = [
    {
        icon: <FileSearch className="h-6 w-6" />,
        color: "bg-blue-50 text-blue-600 border border-blue-200",
        title: "Intelligent Document Parsing",
        description: "Adaptive OCR and structural analysis extracted from hundreds of pages of financial artifacts with 99.4% accuracy."
    },
    {
        icon: <Cpu className="h-6 w-6" />,
        color: "bg-indigo-50 text-indigo-600 border border-indigo-200",
        title: "Automated Workflow Pipeline",
        description: "Orchestrated system modules segmenting extraction, web research, risk modeling, and memo generation."
    },
    {
        icon: <ShieldCheck className="h-6 w-6" />,
        color: "bg-emerald-50 text-emerald-600 border border-emerald-200",
        title: "Verifiable Risk Scoring",
        description: "Advanced modeling provides a mathematical and qualitative rationale for every credit recommendation."
    },
    {
        icon: <Globe className="h-6 w-6" />,
        color: "bg-amber-50 text-amber-600 border border-amber-200",
        title: "Autonomous Web Insight",
        description: "The system investigates real-time news, promoter background, and regulatory changes across the public web."
    }
];

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-[#FAFAFA] text-slate-900 selection:bg-blue-100 font-sans overflow-x-hidden">

            {/* Premium Header */}
            <nav className="border-b border-slate-200 bg-white/80 backdrop-blur-xl sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#0B3C5D] font-bold text-white shadow-sm">
                            IC
                        </div>
                        <span className="text-2xl font-black tracking-tighter text-[#0B3C5D]">Intelli-Credit</span>
                    </div>
                    <div className="flex items-center gap-6">
                        <Link href="/dashboard" className="text-sm font-bold text-slate-500 hover:text-slate-900 hidden md:block tracking-tight transition-colors">
                            Documentation
                        </Link>
                        <div className="flex items-center gap-3">
                            <Link href="/login">
                                <Button variant="ghost" className="font-bold text-slate-600 hover:text-slate-900">
                                    Sign In
                                </Button>
                            </Link>
                            <Link href="/dashboard">
                                <Button className="bg-[#0B3C5D] hover:bg-[#082a42] text-white h-11 px-6 rounded-full font-bold shadow-md transition-all hover:scale-105 active:scale-95">
                                    Get Started <ArrowRight className="ml-2 h-4 w-4" />
                                </Button>
                            </Link>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative pt-24 pb-32 overflow-hidden bg-white">
                {/* Abstract Visual Elements - Soft Background */}
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1200px] h-[600px] bg-gradient-to-b from-slate-50 to-transparent rounded-full blur-[120px] -z-10" />

                <div className="max-w-7xl mx-auto px-6">
                    <div className="grid lg:grid-cols-2 gap-20 items-center">

                        <motion.div
                            initial={{ opacity: 0, x: -30 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.8, ease: "easeOut" }}
                            className="space-y-8"
                        >
                            <div className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 rounded-full text-xs font-bold tracking-widest uppercase border border-emerald-200 shadow-sm">
                                <Sparkles className="w-3.5 h-3.5" />
                                High-Precision Automated Protocol
                            </div>

                            <h1 className="text-6xl lg:text-7xl font-black tracking-tighter text-slate-900 leading-[1.05]">
                                Intelli-Credit <br />
                                <span className="text-blue-600 text-4xl block mt-4 tracking-tight drop-shadow-sm">Corporate Appraisal Engine</span>
                            </h1>

                            <p className="text-xl text-slate-600 font-medium leading-relaxed max-w-xl">
                                Automate financial analysis, risk scoring, and credit appraisal. Our automated system reconstructs financial artifacts into actionable Credit Appraisal Memos (CAM).
                            </p>

                            <div className="flex flex-col sm:flex-row gap-5 pt-4">
                                <Link href="/login">
                                    <Button size="lg" className="h-16 px-10 rounded-3xl bg-[#0B3C5D] text-white hover:bg-[#082a42] text-lg font-black shadow-xl group transition-all">
                                        Start Appraisal <Zap className="ml-3 h-5 w-5 fill-current group-hover:scale-125 transition-transform" />
                                    </Button>
                                </Link>
                                <Link href="/dashboard">
                                    <Button size="lg" variant="outline" className="h-16 px-10 rounded-3xl border-slate-300 bg-white text-slate-700 hover:bg-slate-50 text-lg font-bold shadow-sm transition-all hover:border-slate-400">
                                        View Case Studies
                                    </Button>
                                </Link>
                            </div>

                            <div className="flex items-center gap-6 pt-8 border-t border-slate-200">
                                <div className="flex -space-x-3">
                                    {[1, 2, 3, 4].map(i => (
                                        <div key={i} className={`h-10 w-10 rounded-full border-2 border-white bg-slate-100 flex items-center justify-center overflow-hidden shadow-sm`}>
                                            <div className="bg-blue-100 h-full w-full" />
                                        </div>
                                    ))}
                                </div>
                                <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">
                                    Trusted by 50+ <br /> Leading IB & NBFC Teams
                                </p>
                            </div>
                        </motion.div>

                        {/* Interactive UI Mockup - Pipeline Trace */}
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ duration: 1, delay: 0.2 }}
                            className="relative"
                        >
                            <div className="absolute -inset-4 bg-gradient-to-tr from-blue-50 to-emerald-50 blur-3xl opacity-50 rounded-[60px]" />

                            <Card className="relative border border-slate-200 shadow-2xl rounded-[40px] bg-white overflow-hidden p-2">
                                <div className="rounded-[32px] border border-slate-100 bg-slate-50 overflow-hidden">
                                    {/* Fake Management Bar */}
                                    <div className="h-12 bg-slate-100 border-b border-slate-200 flex items-center px-6 justify-between gap-4">
                                        <div className="flex items-center gap-2">
                                            <div className="h-3 w-3 rounded-full bg-rose-400" />
                                            <div className="h-3 w-3 rounded-full bg-amber-400" />
                                            <div className="h-3 w-3 rounded-full bg-emerald-400" />
                                        </div>
                                        <div className="flex-1 max-w-sm h-7 bg-white border border-slate-200 rounded-lg flex items-center px-4 shadow-sm">
                                            <div className="h-1.5 w-32 bg-slate-300 rounded-full" />
                                        </div>
                                        <div className="h-8 w-8 rounded-full bg-slate-200 border border-slate-300" />
                                    </div>

                                    {/* Workflow Timeline Visualization */}
                                    <div className="p-8 space-y-8 bg-white">
                                        <div className="flex justify-between items-center mb-10">
                                            <div className="space-y-1">
                                                <p className="text-[10px] font-black uppercase tracking-widest text-[#00A8A8]">Analysis ID</p>
                                                <p className="text-lg font-bold text-slate-900">Tencent Holdings Ltd.</p>
                                            </div>
                                            <div className="h-10 px-4 bg-emerald-50 text-emerald-600 rounded-xl flex items-center gap-2 font-black text-sm border border-emerald-200 shadow-sm">
                                                <CheckCircle2 className="w-4 h-4" /> COMPLETED
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="bg-slate-50 p-5 rounded-2xl shadow-sm border border-slate-200">
                                                <div className="flex items-center justify-between mb-4">
                                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Risk Score</p>
                                                    <ShieldCheck className="w-5 h-5 text-emerald-500" />
                                                </div>
                                                <div className="flex items-baseline gap-1">
                                                    <span className="text-3xl font-black text-slate-900">88</span>
                                                    <span className="text-xs font-bold text-slate-400">/100</span>
                                                </div>
                                            </div>
                                            <div className="bg-[#0B3C5D] p-5 rounded-2xl shadow-lg border border-[#0B3C5D]">
                                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-300 mb-4">Grade</p>
                                                <div className="flex items-baseline gap-2">
                                                    <span className="text-3xl font-black text-white">AA+</span>
                                                    <span className="text-[8px] font-bold text-blue-300 uppercase tracking-widest">Superior</span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="space-y-4">
                                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Analysis Pipeline Trace</p>
                                            <div className="space-y-2 font-mono text-[11px] bg-slate-900 rounded-2xl p-5 text-slate-400 leading-relaxed overflow-hidden border border-slate-800 shadow-inner">
                                                <p className="text-emerald-400">&gt; Initializing Automated Research...</p>
                                                <p className="text-slate-500 italic">Exploring Bloomberg, Reuters and SEC filings...</p>
                                                <p className="text-slate-200 mt-2">[✓] Promoter Integrity Check: Passed</p>
                                                <p className="text-slate-200">[✓] Financial Ratio Computation: 18 Nodes</p>
                                                <p className="text-slate-200">[✓] Risk Sensitivity Stress Test: Applied</p>
                                                <p className="text-blue-400 mt-2">&gt; Generating Appraisal Summary...</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </Card>

                            {/* Floating Badges */}
                            <motion.div
                                animate={{ y: [0, -15, 0] }}
                                transition={{ repeat: Infinity, duration: 5, ease: "easeInOut" }}
                                className="absolute -right-10 top-20 bg-white shadow-xl rounded-3xl p-4 border border-slate-100 flex items-center gap-4 group backdrop-blur-xl"
                            >
                                <div className="bg-blue-50 p-3 rounded-2xl text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-colors border border-blue-100">
                                    <BarChart3 className="w-6 h-6" />
                                </div>
                                <div>
                                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">DSCR Projection</p>
                                    <p className="text-lg font-black text-slate-900">2.4x <span className="text-emerald-500 font-bold text-[10px] ml-1">+14%</span></p>
                                </div>
                            </motion.div>

                            <motion.div
                                animate={{ x: [0, 10, 0] }}
                                transition={{ repeat: Infinity, duration: 6, ease: "easeInOut" }}
                                className="absolute -left-12 bottom-20 bg-white shadow-xl rounded-3xl p-4 border border-slate-100 flex items-center gap-4 group backdrop-blur-xl"
                            >
                                <div className="bg-emerald-50 p-3 rounded-2xl text-emerald-600 group-hover:bg-emerald-600 group-hover:text-white transition-colors border border-emerald-100">
                                    <Building2 className="w-6 h-6" />
                                </div>
                                <div>
                                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Analysed Portfolio</p>
                                    <p className="text-lg font-black text-slate-900">₹14,500 Cr</p>
                                </div>
                            </motion.div>
                        </motion.div>
                    </div>
                </div>
            </section>

            {/* Features / Benefits */}
            <section className="bg-slate-50 py-32 border-y border-slate-200">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="text-center max-w-3xl mx-auto mb-20 space-y-4">
                        <h2 className="text-sm font-black text-blue-600 uppercase tracking-[0.3em]">The Architecture of Trust</h2>
                        <h3 className="text-5xl font-black text-slate-900 tracking-tighter drop-shadow-sm">Enterprise Intelligence Engineered at Scale.</h3>
                        <p className="text-lg text-slate-600 font-medium">Built from the ground up for the extreme complexities of modern corporate finance and institutional banking.</p>
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
                        {features.map((feature, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: i * 0.1 }}
                                className="group p-10 rounded-[40px] border border-slate-200 bg-white hover:shadow-xl hover:border-blue-200 transition-all cursor-default relative overflow-hidden"
                            >
                                <div className={`h-16 w-16 rounded-[24px] flex items-center justify-center mb-10 transition-transform group-hover:scale-110 shadow-sm relative z-10 ${feature.color}`}>
                                    {feature.icon}
                                </div>
                                <h4 className="text-xl font-black text-slate-900 mb-4 tracking-tight leading-none relative z-10">{feature.title}</h4>
                                <p className="text-slate-600 text-sm font-medium leading-relaxed relative z-10">
                                    {feature.description}
                                </p>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-32 relative bg-white">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="bg-[#0B3C5D] rounded-[60px] p-16 md:p-24 text-center space-y-12 relative overflow-hidden border border-[#082a42] shadow-2xl">
                        <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-[#00A8A8]/20 to-transparent pointer-events-none" />
                        <div className="relative z-10 space-y-6 max-w-3xl mx-auto">
                            <h2 className="text-5xl md:text-6xl font-black text-white tracking-tighter">Ready to Automate your Lending Alpha?</h2>
                            <p className="text-xl text-blue-100 font-medium leading-relaxed">Join 200+ credit analysts who have reduced their CAM generation time from 5 days to 5 minutes.</p>

                            <div className="flex flex-col sm:flex-row gap-4 justify-center pt-8">
                                <Link href="/login">
                                    <Button size="lg" className="h-16 px-12 rounded-[24px] bg-white hover:bg-slate-100 text-[#0B3C5D] font-black text-lg shadow-xl transition-all hover:-translate-y-1">
                                        Get Started Now
                                    </Button>
                                </Link>
                                <Button size="lg" variant="outline" className="h-16 px-12 rounded-[24px] border-white/20 bg-white/5 text-white hover:bg-white/10 text-lg font-bold backdrop-blur-sm transition-all hover:border-white/30">
                                    Request Demo
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Professional Footer */}
            <footer className="bg-slate-50 border-t border-slate-200 pt-24 pb-12">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-12 mb-20">
                        <div className="col-span-2">
                            <div className="flex items-center gap-3 mb-6">
                                <div className="h-8 w-8 rounded-lg bg-[#0B3C5D] shadow-sm flex items-center justify-center font-black text-white text-xs">IC</div>
                                <span className="text-xl font-black tracking-tighter text-slate-900">Intelli-Credit</span>
                            </div>
                            <p className="text-slate-600 text-sm font-medium leading-relaxed max-w-xs">
                                Next-generation autonomous credit appraisal platform for institutional lenders, banks and credit funds.
                            </p>
                        </div>
                        <div className="space-y-6">
                            <h5 className="text-[10px] font-black text-blue-600 uppercase tracking-widest">Platform</h5>
                            <ul className="space-y-4 text-sm font-bold text-slate-500">
                                <li><Link href="/" className="hover:text-slate-900 transition-colors">Market Intelligence</Link></li>
                                <li><Link href="/" className="hover:text-slate-900 transition-colors">Analysis Logic</Link></li>
                                <li><Link href="/" className="hover:text-slate-900 transition-colors">Risk Modeling</Link></li>
                            </ul>
                        </div>
                        <div className="space-y-6">
                            <h5 className="text-[10px] font-black text-blue-600 uppercase tracking-widest">Integrity</h5>
                            <ul className="space-y-4 text-sm font-bold text-slate-500">
                                <li><Link href="/" className="hover:text-slate-900 transition-colors">Compliance</Link></li>
                                <li><Link href="/" className="hover:text-slate-900 transition-colors">Security</Link></li>
                                <li><Link href="/" className="hover:text-slate-900 transition-colors">Privacy Policy</Link></li>
                            </ul>
                        </div>
                        <div className="space-y-6">
                            <h5 className="text-[10px] font-black text-blue-600 uppercase tracking-widest">Resources</h5>
                            <ul className="space-y-4 text-sm font-bold text-slate-500">
                                <li><Link href="/" className="hover:text-slate-900 transition-colors">API Docs</Link></li>
                                <li><Link href="/" className="hover:text-slate-900 transition-colors">Whitepapers</Link></li>
                                <li><Link href="/" className="hover:text-slate-900 transition-colors">Support</Link></li>
                            </ul>
                        </div>
                    </div>
                    <div className="flex flex-col md:flex-row items-center justify-between gap-6 pt-12 border-t border-slate-200">
                        <p className="text-[10px] font-black font-mono text-slate-400 uppercase tracking-widest">© 2026 Intelli-Credit Labs. Financial Research Systems.</p>
                        <div className="flex gap-8 text-[10px] font-black text-slate-500 uppercase tracking-widest underline decoration-slate-200 underline-offset-8">
                            <span className="hover:text-slate-900 cursor-pointer transition-colors">Twitter</span>
                            <span className="hover:text-slate-900 cursor-pointer transition-colors">Github</span>
                            <span className="hover:text-slate-900 cursor-pointer transition-colors">LinkedIn</span>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
}
