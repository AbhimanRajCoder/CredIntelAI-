"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import { supabase } from "@/lib/supabase";
import {
    ArrowLeft, Download, ShieldAlert, CheckCircle2, AlertTriangle,
    Building2, Briefcase, RefreshCw, XCircle, Info, Landmark, LineChart as LucideLineChart,
    Scale, Users, Globe, Newspaper, FileSearch, PieChart as LucidePieChart, ShieldBan, ShieldCheck,
    HelpCircle, TrendingUp, Code2, Clock, Loader2, Timer, FileOutput, Activity, ArrowUpRight, ArrowDownRight,
    Search, Zap, FileText
} from "lucide-react";
import dynamic from 'next/dynamic';

const PDFDownloadLink = dynamic(
    () => import('@react-pdf/renderer').then((mod) => mod.PDFDownloadLink),
    { ssr: false }
);

import { ReportPDF } from "@/components/ReportPDF";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
    PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
    CartesianGrid, Tooltip, LineChart, Line, AreaChart, Area
} from "recharts";

type ReportData = {
    analysis_id: string;
    status: string;
    created_at?: string;
    updated_at?: string;
    report?: any;
    docx_download_url?: string;
    pdf_download_url?: string;
    errors?: string[];
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const FINTECH_BLUE = "#0B3C5D";
const FINTECH_TEAL = "#00A8A8";

export default function ReportPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();

    const [data, setData] = useState<ReportData | null>(null);
    const [loading, setLoading] = useState(true);
    const [elapsed, setElapsed] = useState(0);

    const fetchReport = async () => {
        try {
            const res = await api.get(`/report/${id}`);
            setData(res.data);
        } catch (error) {
            console.error("Failed to fetch report:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const checkUser = async () => {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) {
                router.push("/login");
                return;
            }
        };
        checkUser();
        fetchReport();

        // Auto-refresh if not completed or failed
        let interval: NodeJS.Timeout;
        if (data && !["completed", "failed"].includes(data.status)) {
            interval = setInterval(fetchReport, 4000);
        }

        return () => clearInterval(interval);
    }, [id, data?.status]);

    // Elapsed time calculation effect
    useEffect(() => {
        if (!data) return;

        const isFinished = ["completed", "failed"].includes(data.status);
        if (isFinished && data.updated_at && data.created_at) {
            const duration = new Date(data.updated_at).getTime() - new Date(data.created_at).getTime();
            setElapsed(duration);
            return;
        }

        const baseTime = data.created_at ? new Date(data.created_at).getTime() : Date.now();

        const timer = setInterval(() => {
            setElapsed(Date.now() - baseTime);
        }, 1000);

        return () => clearInterval(timer);
    }, [data?.status, data?.created_at, data?.updated_at]);

    if (loading && !data) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen bg-[#FAFAFA]">
                <div className="relative">
                    <div className="w-16 h-16 border-[3px] border-slate-200 border-t-[#0B3C5D] rounded-full animate-spin" />
                    <div className="absolute inset-0 flex items-center justify-center">
                        <Activity className="w-6 h-6 text-[#0B3C5D]" />
                    </div>
                </div>
                <p className="mt-6 text-lg font-bold text-slate-900 tracking-tight">Accessing Appraisal System...</p>
                <p className="text-slate-500 mt-1 text-[14px]">Retrieving secure financial records.</p>
            </div>
        );
    }

    if (!data) {
        return (
            <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center">
                <Card className="max-w-md w-full p-8 text-center rounded-3xl border-none shadow-xl">
                    <XCircle className="w-16 h-16 text-rose-500 mx-auto mb-6" />
                    <h2 className="text-2xl font-black text-[#0B3C5D]">Record Not Found</h2>
                    <p className="text-slate-500 mt-2 mb-8">The requested credit report does not exist in our secure database.</p>
                    <Link href="/dashboard">
                        <Button className="bg-[#0B3C5D] rounded-full px-8">Return to Dashboard</Button>
                    </Link>
                </Card>
            </div>
        );
    }

    const { status, report, docx_download_url, pdf_download_url, errors } = data;
    const isFinished = ["completed", "failed"].includes(status);
    const isFailed = status === "failed";

    // ─── Pipeline Constants ───────────────────────────────────────────────
    const PIPELINE_STEPS = [
        { key: "parsing_documents", label: "Document Ingestion", icon: <FileSearch /> },
        { key: "extracting_financials", label: "Metrics Extraction", icon: <LucideLineChart /> },
        { key: "researching_company", label: "Intelligence Gathering", icon: <Globe /> },
        { key: "performing_risk_analysis", label: "Risk Computation", icon: <ShieldAlert /> },
        { key: "generating_cam", label: "Report Finalization", icon: <FileOutput /> },
    ];

    const STATUS_MAP: Record<string, number> = {
        queued: 0, pending: 0, processing: 0,
        parsing_documents: 1, ingesting: 1,
        extracting_financials: 2,
        researching: 3, researching_company: 3,
        performing_risk_analysis: 4, analyzing_risk: 4,
        generating_cam: 5,
        completed: 6
    };

    const currentStepIndex = STATUS_MAP[status] ?? 0;

    const formatElapsed = (ms: number) => {
        const totalSec = Math.max(0, Math.floor(ms / 1000));
        const min = Math.floor(totalSec / 60);
        const sec = totalSec % 60;
        return min > 0 ? `${min}m ${sec}s` : `${sec}s`;
    };

    // ─── Render Components ───────────────────────────────────────────────

    const renderProcessingState = () => (
        <div className="min-h-[80vh] flex flex-col items-center justify-center px-4 bg-[#FAFAFA]">
            <div className="max-w-3xl w-full space-y-10">
                <div className="text-center space-y-3">
                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-slate-100 text-slate-700 rounded-md text-[11px] font-bold tracking-wide uppercase border border-slate-200 mb-2">
                        <Activity className="w-3.5 h-3.5 animate-pulse text-emerald-500" /> Automated Pipeline Active
                    </div>
                    <h2 className="text-3xl font-black text-[#0B3C5D] tracking-tight">Credit Appraisal in Progress</h2>
                    <p className="text-slate-500 text-[15px] max-w-xl mx-auto font-medium">
                        Our automated system is currently processing documents, researching market signals, and computing risk coefficients.
                    </p>
                </div>

                <div className="relative py-8 px-6">
                    <div className="absolute top-[62px] left-10 right-10 h-[3px] bg-slate-200 z-0 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-[#0B3C5D] transition-all duration-1000"
                            style={{ width: `${(currentStepIndex / 5) * 100}%` }}
                        />
                    </div>

                    <div className="grid grid-cols-5 gap-4">
                        {PIPELINE_STEPS.map((step, idx) => {
                            const isActive = idx === currentStepIndex - 1;
                            const isCompleted = idx < currentStepIndex - 1;
                            return (
                                <div key={idx} className="flex flex-col items-center gap-4 relative z-10 bg-white shadow-sm ring-1 ring-slate-200 p-4 rounded-xl">
                                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-500 ${isCompleted ? "bg-emerald-50 text-emerald-600 ring-1 ring-emerald-200" :
                                        isActive ? "bg-[#0B3C5D] text-white shadow-md animate-pulse" :
                                            "bg-slate-50 text-slate-400 ring-1 ring-slate-200"
                                        }`}>
                                        {isCompleted ? <CheckCircle2 className="w-5 h-5" /> : step.icon}
                                    </div>
                                    <div className="text-center">
                                        <p className={`text-[10px] font-bold uppercase tracking-wider ${isActive ? "text-[#0B3C5D]" : isCompleted ? "text-emerald-700" : "text-slate-400"}`}>
                                            {step.label}
                                        </p>
                                        {isActive && <span className="text-[10px] font-semibold text-slate-500 mt-1 block italic text-blue-600">Running...</span>}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                    <Card className="bg-white border border-slate-200 shadow-sm rounded-xl p-6 flex items-center gap-5">
                        <div className="h-12 w-12 bg-slate-50 rounded-lg flex items-center justify-center border border-slate-200">
                            <Clock className="w-5 h-5 text-slate-600" />
                        </div>
                        <div>
                            <p className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">Execution Time</p>
                            <p className="text-2xl font-black text-slate-900 tracking-tight font-mono">{formatElapsed(elapsed)}</p>
                        </div>
                    </Card>
                    <Card className="bg-white border border-slate-200 shadow-sm rounded-xl p-6 flex items-center gap-5">
                        <div className="h-12 w-12 bg-slate-50 rounded-lg flex items-center justify-center border border-slate-200">
                            <Activity className="w-5 h-5 text-slate-600" />
                        </div>
                        <div>
                            <p className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">System Load</p>
                            <p className="text-xl font-black text-slate-900 tracking-tight">Optimal Performance</p>
                        </div>
                    </Card>
                </div>
                <p className="text-center text-slate-400 text-[12px] font-bold tracking-tight pt-4">
                    Automatic status synchronization active. No manual intervention required.
                </p>
            </div>
        </div>
    );

    const renderFailedState = () => (
        <div className="min-h-[80vh] flex flex-col items-center justify-center px-4 bg-[#FAFAFA]">
            <Card className="max-w-2xl w-full p-10 text-center rounded-xl border border-slate-200 shadow-sm bg-white space-y-6">
                <div className="w-16 h-16 bg-rose-50 text-rose-600 rounded-xl flex items-center justify-center mx-auto border border-rose-200">
                    <ShieldBan className="w-8 h-8" />
                </div>
                <div className="space-y-2">
                    <h2 className="text-2xl font-black text-[#0B3C5D] tracking-tight">Process Interrupted</h2>
                    <p className="text-slate-500 text-[15px] font-medium">The analysis pipeline encountered a formatting error or data inconsistency.</p>
                </div>

                {errors && errors.length > 0 && (
                    <div className="bg-[#FAFAFA] p-5 rounded-lg border border-slate-200 text-left overflow-hidden">
                        <p className="text-[11px] font-bold text-slate-700 uppercase tracking-widest mb-3">Diagnostic Logs</p>
                        <ScrollArea className="h-32 text-[12px] font-mono text-rose-600 space-y-1">
                            {errors.map((err, idx) => <p key={idx} className="border-b border-slate-100 pb-1.5 mb-1.5">{err}</p>)}
                        </ScrollArea>
                    </div>
                )}

                <div className="flex gap-3 justify-center pt-2">
                    <Link href="/dashboard">
                        <Button variant="outline" className="rounded-md h-10 px-6 font-bold border-slate-200 text-slate-700 shadow-sm">Back to Dashboard</Button>
                    </Link>
                    <Button onClick={() => window.location.reload()} className="bg-[#0B3C5D] text-white hover:bg-[#082a42] rounded-md h-10 px-6 font-bold shadow-sm">Restart Pipeline</Button>
                </div>
            </Card>
        </div>
    );

    if (!isFinished) return renderProcessingState();
    if (isFailed || !report) return renderFailedState();

    // ─── Report Content Processing ───────────────────────────────────────

    const {
        company_name, sector, risk_analysis, financial_metrics,
        research_signals, recommendation, company_overview, financial_analysis,
        risk_assessment, industry_outlook, promoter_background
    } = report;

    const score = risk_analysis?.risk_score || 0;
    const grade = risk_analysis?.risk_grade || "N/A";

    // Gauge Chart Data
    const gaugeData = [
        { name: 'score', value: score, fill: score > 60 ? '#22C55E' : score > 40 ? '#F59E0B' : '#EF4444' },
        { name: 'remainder', value: 100 - score, fill: '#F1F5F9' }
    ];

    const formatCurrency = (val: number | null | undefined) => {
        if (val === null || val === undefined) return "N/A";
        return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', notation: 'compact', maximumFractionDigits: 1 }).format(val);
    };

    const cleanMarkdown = (text: string) => {
        if (!text) return "";
        return text.replace(/\*\*(.*?)\*\*/g, '$1').replace(/\*(.*?)\*/g, '$1').trim();
    };

    return (
        <div className="min-h-screen bg-[#F8FAFC] pb-20">

            {/* Modern Header Row */}
            <div className="bg-white border-b border-slate-200 pt-8 pb-12">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div className="space-y-4">
                        <Link href="/dashboard" className="inline-flex items-center gap-2 text-slate-500 hover:text-slate-900 transition-colors font-medium text-[13px]">
                            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
                        </Link>
                        <div className="space-y-1.5">
                            <div className="flex items-center gap-3">
                                <h1 className="text-3xl font-bold text-slate-900 tracking-tight">{company_name}</h1>
                                <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 font-semibold text-[10px] uppercase tracking-widest shadow-sm">
                                    Verified Analysis
                                </Badge>
                            </div>
                            <p className="text-slate-500 text-[15px]">
                                Automated Appraisal Memo for <span className="text-slate-900 font-medium">{sector}</span>.
                                Generated on {new Date(data.created_at || '').toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })}.
                            </p>
                        </div>
                    </div>

                    <div className="flex flex-wrap gap-3">

                        {report && (
                            <PDFDownloadLink
                                document={<ReportPDF data={data} />}
                                fileName={`Appraisal_Report_${company_name?.replace(/\s+/g, '_')}_${id.substring(0, 8)}.pdf`}
                            >
                                {({ loading }) => (
                                    <Button
                                        disabled={loading}
                                        className="bg-[#0B3C5D] text-white hover:bg-[#082a42] h-10 rounded-md px-6 font-bold shadow-md transition-all hover:scale-105 active:scale-95"
                                    >
                                        <FileOutput className="w-4 h-4 mr-2" />
                                        {loading ? 'Compiling PDF...' : 'Download Premium PDF'}
                                    </Button>
                                )}
                            </PDFDownloadLink>
                        )}
                    </div>
                </div>
            </div>

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

                {/* ─── Top Analytics Strip ─── */}
                <div className="grid lg:grid-cols-12 gap-6">

                    {/* Score Gauge */}
                    <Card className="lg:col-span-4 border border-slate-200 shadow-sm rounded-xl overflow-hidden bg-white p-6 flex flex-col items-center justify-center relative">
                        <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-widest mb-2 z-10 w-full text-left">Composite Credit Risk</p>
                        <div className="relative w-full aspect-square max-h-56 flex items-center justify-center">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={gaugeData}
                                        cx="50%"
                                        cy="50%"
                                        startAngle={180}
                                        endAngle={0}
                                        innerRadius="75%"
                                        outerRadius="100%"
                                        paddingAngle={0}
                                        dataKey="value"
                                        stroke="none"
                                    >
                                        {gaugeData.map((entry, index) => <Cell key={index} fill={entry.fill} />)}
                                    </Pie>
                                </PieChart>
                            </ResponsiveContainer>
                            <div className="absolute inset-0 flex flex-col items-center justify-center pt-12">
                                <span className={`text-5xl font-bold tracking-tight ${score > 60 ? 'text-emerald-600' : score > 40 ? 'text-amber-600' : 'text-rose-600'}`}>
                                    {score}
                                </span>
                                <span className="text-[10px] font-medium text-slate-400 mt-1 uppercase tracking-widest">Score / 100</span>
                            </div>
                        </div>
                        <Badge className={`mt-2 px-4 py-1.5 rounded-md text-[13px] font-bold tracking-wide border-none ${grade.startsWith('A') ? 'bg-emerald-50 text-emerald-700' :
                            grade.startsWith('B') ? 'bg-amber-50 text-amber-700' :
                                'bg-rose-50 text-rose-700'
                            }`}>
                            GRADE: {grade}
                        </Badge>
                        <p className="mt-4 text-center text-[11px] font-medium text-slate-500 w-full">
                            Calculated using {research_signals?.sources?.length || 0} intelligence nodes.
                        </p>
                    </Card>

                    {/* Recommendation Panel */}
                    <Card className="lg:col-span-8 border border-slate-200 shadow-sm rounded-xl bg-white p-8">
                        <div className="flex flex-col h-full justify-between">
                            <div className="flex items-center gap-2.5 mb-6">
                                <div className="p-1.5 bg-slate-50 rounded-md ring-1 ring-slate-200/50">
                                    <ShieldCheck className="w-5 h-5 text-slate-700" />
                                </div>
                                <h2 className="text-lg font-bold text-slate-900 tracking-tight">Credit Lending Recommendation</h2>
                            </div>

                            <div className="flex flex-wrap gap-3 mb-6">
                                <div className={`px-4 py-2 flex items-center justify-center rounded-md font-bold text-[14px] ${recommendation?.decision === 'APPROVE' ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/50' :
                                    recommendation?.decision === 'REJECT' ? 'bg-rose-50 text-rose-700 ring-1 ring-rose-200/50' :
                                        'bg-amber-50 text-amber-700 ring-1 ring-amber-200/50'
                                    }`}>
                                    {recommendation?.decision?.replace('_', ' ')}
                                </div>

                                {recommendation?.suggested_loan_limit && (
                                    <div className="px-4 py-2 bg-slate-50 rounded-md flex flex-col justify-center ring-1 ring-slate-200/50">
                                        <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-500">Suggested Limit</span>
                                        <span className="text-[15px] font-bold text-slate-900">{formatCurrency(recommendation.suggested_loan_limit)}</span>
                                    </div>
                                )}

                                {recommendation?.suggested_interest_rate && (
                                    <div className="px-4 py-2 bg-slate-50 rounded-md flex flex-col justify-center ring-1 ring-slate-200/50">
                                        <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-500">Interest Rate</span>
                                        <span className="text-[15px] font-bold text-slate-900">{recommendation.suggested_interest_rate}%</span>
                                    </div>
                                )}
                            </div>

                            <div className="bg-slate-50 p-5 rounded-lg border border-slate-200/50 h-full">
                                <p className="text-[14px] text-slate-600 leading-relaxed">
                                    {recommendation?.explanation}
                                </p>

                                {recommendation?.conditions && recommendation.conditions.length > 0 && (
                                    <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {recommendation.conditions.map((c: string, i: number) => (
                                            <div key={i} className="flex gap-2.5 text-[13px] bg-white p-3 rounded-md border border-slate-200/50">
                                                <div className="h-1.5 w-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" />
                                                <span className="text-slate-600">{c}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </Card>
                </div>

                {/* ─── Financial KPIs ─── */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                    <MetricCard title="Revenue" value={formatCurrency(financial_metrics?.revenue)} icon={<LucideLineChart />} trend={8} />
                    <MetricCard title="Net Profit" value={formatCurrency(financial_metrics?.profit)} icon={<Activity />} trend={12} />
                    <MetricCard title="Debt/Equity" value={financial_metrics?.debt_to_equity_ratio?.toFixed(2)} icon={<Landmark />} isRed={financial_metrics?.debt_to_equity_ratio > 2} />
                    <MetricCard title="ROE" value={`${(financial_metrics?.return_on_equity || 0).toFixed(1)}%`} icon={<TrendingUp />} />
                </div>

                {/* ─── Main Content Tabs ─── */}
                <Tabs defaultValue="intelligence" className="w-full">
                    <TabsList className="bg-slate-100/50 p-1 flex w-fit rounded-lg mb-8">
                        <TabsTrigger value="intelligence" className="rounded-md px-5 py-1.5 text-[13px] font-medium data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm">Intelligence Summary</TabsTrigger>
                        <TabsTrigger value="financials" className="rounded-md px-5 py-1.5 text-[13px] font-medium data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm">Detailed Financials</TabsTrigger>
                        <TabsTrigger value="risks" className="rounded-md px-5 py-1.5 text-[13px] font-medium data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm">Risk Matrix</TabsTrigger>
                        <TabsTrigger value="ledger" className="rounded-md px-5 py-1.5 text-[13px] font-medium data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm">Intelligence Ledger</TabsTrigger>
                    </TabsList>

                    <TabsContent value="intelligence" className="grid lg:grid-cols-2 gap-6 focus:outline-none">
                        <IntelligenceCard title="Executive Overview" content={company_overview} icon={<Building2 />} />
                        <IntelligenceCard title="Promoter Background" content={promoter_background} icon={<Users />} />
                        <div className="lg:col-span-2">
                            <IntelligenceCard title="Industry Outlook" content={industry_outlook} icon={<Globe />} />
                        </div>
                    </TabsContent>

                    <TabsContent value="risks" className="space-y-6 focus:outline-none">
                        {/* ─── Risk Heatmap ─── */}
                        <div className="grid md:grid-cols-4 gap-4">
                            <RiskBlock title="Regulatory Risk" level={research_signals?.regulatory_risk || "Low"} description="Compliance and licensing history" />
                            <RiskBlock title="Promoter Risk" level={research_signals?.promoter_risk || "Low"} description="Integrity and reputation signals" />
                            <RiskBlock title="Market Risk" level={research_signals?.sector_risk || "Medium"} description="Sector volatility and trends" />
                            <RiskBlock title="Fraud Risk" level="Low" description="Internal automated fraud detection score" />
                        </div>

                        <div className="grid lg:grid-cols-2 gap-6">
                            <Card className="border border-slate-200 shadow-sm rounded-xl bg-white p-8">
                                <h3 className="text-[17px] font-bold text-slate-900 mb-6 flex items-center gap-2.5">
                                    <div className="p-1.5 bg-rose-50 rounded-md ring-1 ring-rose-200">
                                        <ShieldAlert className="w-4 h-4 text-rose-600" />
                                    </div>
                                    Primary Risks
                                </h3>
                                <div className="space-y-4">
                                    {risk_analysis?.key_risks?.map((r: string, i: number) => (
                                        <div key={i} className="flex gap-3 items-start">
                                            <div className="h-5 w-5 rounded bg-rose-50 text-rose-600 flex items-center justify-center shrink-0 font-bold text-[10px] ring-1 ring-rose-200">
                                                {i + 1}
                                            </div>
                                            <p className="text-slate-600 text-[14px] leading-relaxed">{r}</p>
                                        </div>
                                    ))}
                                </div>
                            </Card>

                            <Card className="border border-slate-200 shadow-sm rounded-xl bg-white p-8">
                                <h3 className="text-[17px] font-bold text-slate-900 mb-6 flex items-center gap-2.5">
                                    <div className="p-1.5 bg-emerald-50 rounded-md ring-1 ring-emerald-200">
                                        <ShieldCheck className="w-4 h-4 text-emerald-600" />
                                    </div>
                                    Key Mitigants
                                </h3>
                                <div className="space-y-4">
                                    {risk_analysis?.strengths?.map((s: string, i: number) => (
                                        <div key={i} className="flex gap-3 items-start">
                                            <div className="h-5 w-5 rounded bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0 ring-1 ring-emerald-200">
                                                <CheckCircle2 className="h-3 w-3" />
                                            </div>
                                            <p className="text-slate-600 text-[14px] leading-relaxed">{s}</p>
                                        </div>
                                    ))}
                                </div>
                            </Card>
                        </div>
                    </TabsContent>

                    <TabsContent value="financials" className="focus:outline-none">
                        <Card className="border border-slate-200 shadow-sm rounded-xl bg-white overflow-hidden">
                            <CardHeader className="p-6 border-b border-slate-100 bg-slate-50/50">
                                <CardTitle className="text-lg font-bold text-slate-900">Metrics Verification Ledger</CardTitle>
                                <CardDescription className="text-[13px] text-slate-500">Cross-referenced financial signatures from original documents.</CardDescription>
                            </CardHeader>
                            <CardContent className="p-0">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="border-slate-100 hover:bg-transparent">
                                            <TableHead className="px-6 h-10 font-semibold uppercase tracking-wider text-[10px] text-slate-500 bg-white">Metric Identifier</TableHead>
                                            <TableHead className="px-6 h-10 font-semibold uppercase tracking-wider text-[10px] text-slate-500 bg-white">Computational Value</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        <MetricRow label="Annualized Revenue" value={formatCurrency(financial_metrics?.revenue)} />
                                        <MetricRow label="Net Operating Profit" value={formatCurrency(financial_metrics?.profit)} />
                                        <MetricRow label="Aggregate Indebtedness" value={formatCurrency(financial_metrics?.debt)} />
                                        <MetricRow label="Operating Cash Velocity" value={formatCurrency(financial_metrics?.cashflow)} />
                                        <MetricRow label="External Banking Exposure" value={formatCurrency(financial_metrics?.bank_loans)} />
                                        <MetricRow label="Debt to Equity Multiplier" value={financial_metrics?.debt_to_equity_ratio?.toFixed(2)} isWarn={financial_metrics?.debt_to_equity_ratio > 2.5} />
                                        <MetricRow label="Liquidity Coverage Ratio" value={financial_metrics?.current_ratio?.toFixed(2)} />
                                        <MetricRow label="Return on Equity Yield" value={`${(financial_metrics?.return_on_equity || 0).toFixed(1)}%`} isPositive={financial_metrics?.return_on_equity > 15} />
                                    </TableBody>
                                </Table>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    <TabsContent value="ledger" className="space-y-6 focus:outline-none">
                        <div className="grid lg:grid-cols-12 gap-6">
                            {/* Market Sentiment column */}
                            <div className="lg:col-span-12">
                                <Card className="border border-slate-200 shadow-sm rounded-xl bg-white p-8">
                                    <div className="flex items-center gap-3 mb-8">
                                        <div className="p-2 bg-slate-50 rounded-lg ring-1 ring-slate-200">
                                            <Newspaper className="w-5 h-5 text-slate-900" />
                                        </div>
                                        <div>
                                            <h3 className="text-xl font-bold text-slate-900">Sentiment Analysis</h3>
                                            <p className="text-[13px] text-slate-500">Autonomous synthesis of global news and media signals.</p>
                                        </div>
                                    </div>

                                    <div className="grid md:grid-cols-2 gap-8">
                                        {/* Positive Signals */}
                                        <div className="space-y-5">
                                            <h4 className="flex items-center gap-2 text-[12px] font-bold text-emerald-700 uppercase tracking-widest">
                                                <Zap className="w-3.5 h-3.5" /> Bullish Signals
                                            </h4>
                                            <div className="space-y-3">
                                                {research_signals?.positive_news && research_signals.positive_news.length > 0 ? (
                                                    research_signals.positive_news.map((news: string, i: number) => (
                                                        <div key={i} className="bg-emerald-50/30 border border-emerald-100/50 p-4 rounded-xl flex gap-3">
                                                            <div className="h-5 w-5 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center shrink-0">
                                                                <ArrowUpRight className="w-3 h-3" />
                                                            </div>
                                                            <p className="text-[13px] text-slate-700 leading-relaxed">{news}</p>
                                                        </div>
                                                    ))
                                                ) : (
                                                    <div className="p-8 text-center border-2 border-dashed border-slate-100 rounded-xl">
                                                        <p className="text-slate-400 text-[11px] font-medium uppercase tracking-widest">No Significant Positive News</p>
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        {/* Negative Signals */}
                                        <div className="space-y-5">
                                            <h4 className="flex items-center gap-2 text-[12px] font-bold text-rose-700 uppercase tracking-widest">
                                                <AlertTriangle className="w-3.5 h-3.5" /> Adverse Alerts
                                            </h4>
                                            <div className="space-y-3">
                                                {research_signals?.negative_news && research_signals.negative_news.length > 0 ? (
                                                    research_signals.negative_news.map((news: string, i: number) => (
                                                        <div key={i} className="bg-rose-50/30 border border-rose-100/50 p-4 rounded-xl flex gap-3">
                                                            <div className="h-5 w-5 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center shrink-0">
                                                                <ArrowDownRight className="w-3 h-3" />
                                                            </div>
                                                            <p className="text-[13px] text-slate-700 leading-relaxed">{news}</p>
                                                        </div>
                                                    ))
                                                ) : (
                                                    <div className="p-8 text-center border-2 border-dashed border-slate-100 rounded-xl">
                                                        <p className="text-slate-400 text-[11px] font-medium uppercase tracking-widest">No Significant Adverse News</p>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </Card>
                            </div>

                            {/* Evidence Registry column */}
                            <div className="lg:col-span-12">
                                <Card className="border border-slate-200 shadow-sm rounded-xl bg-white overflow-hidden">
                                    <CardHeader className="p-8 border-b border-slate-100 bg-slate-50/50">
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <CardTitle className="text-xl font-bold text-slate-900">Source Documentation</CardTitle>
                                                <CardDescription className="text-[14px] text-slate-500 mt-1">
                                                    The underlying intelligence nodes utilized by the autonomous reasoning engine.
                                                </CardDescription>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-[28px] font-bold text-[#0B3C5D]">{research_signals?.sources?.length || 0}</div>
                                                <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Reference Nodes</div>
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardContent className="p-0">
                                        <ScrollArea className="h-[400px]">
                                            <div className="grid md:grid-cols-2 divide-x divide-y divide-slate-100">
                                                {research_signals?.sources?.map((source: string, i: number) => (
                                                    <div key={i} className="flex items-center justify-between p-5 hover:bg-slate-50/80 transition-colors group">
                                                        <div className="flex items-center gap-4 min-w-0 flex-1">
                                                            <div className="h-11 w-11 rounded-xl bg-white shadow-sm flex items-center justify-center shrink-0 border border-slate-200 group-hover:border-[#0B3C5D]/30 transition-all">
                                                                <Globe className="w-5 h-5 text-slate-400 group-hover:text-[#0B3C5D]" />
                                                            </div>
                                                            <div className="min-w-0 flex-1">
                                                                <p className="text-[13px] font-bold text-slate-900 truncate tracking-tight uppercase">
                                                                    {source.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}
                                                                </p>
                                                                <p className="text-[11px] text-slate-400 truncate font-mono mt-0.5 opacity-80">
                                                                    {source}
                                                                </p>
                                                            </div>
                                                        </div>
                                                        <div className="flex items-center gap-3 shrink-0 ml-4">
                                                            <Badge className="bg-slate-100 text-slate-600 border-none font-bold text-[8px] tracking-widest uppercase py-0.5 px-2">Verified</Badge>
                                                            <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full bg-white shadow-sm border border-slate-200 hover:border-[#0B3C5D]/20 transition-all" onClick={() => window.open(source, '_blank')}>
                                                                <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-[#0B3C5D]" />
                                                            </Button>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </ScrollArea>
                                    </CardContent>
                                    <CardFooter className="bg-white border-t border-slate-100 p-5 flex justify-center">
                                        <div className="flex items-center gap-2 text-[11px] text-slate-400 font-medium italic">
                                            <Scale className="w-3.5 h-3.5" />
                                            <span>Institutional disclosure: Sources are cross-verified for authenticity.</span>
                                        </div>
                                    </CardFooter>
                                </Card>
                            </div>
                        </div>
                    </TabsContent>
                </Tabs>
            </main>
        </div>
    );
}

// ─── Support Components ───────────────────────────────────────────────────

function MetricCard({ title, value, icon, trend, isRed }: any) {
    return (
        <Card className="border border-slate-200 shadow-sm rounded-xl p-5 bg-white transition-shadow hover:shadow-md">
            <div className="flex justify-between items-start mb-3">
                <div className="p-1.5 bg-slate-50 rounded-md ring-1 ring-slate-200/60">
                    <div className="w-4 h-4 text-slate-600 [&>svg]:w-full [&>svg]:h-full">{icon}</div>
                </div>
                {trend && (
                    <div className="flex items-center gap-0.5 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded flex-shrink-0">
                        <ArrowUpRight className="h-2.5 w-2.5" /> {trend}%
                    </div>
                )}
            </div>
            <div className="space-y-0.5">
                <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-widest">{title}</p>
                <p className={`text-xl font-bold ${isRed ? "text-rose-600" : "text-slate-900"} tracking-tight truncate`}>{value}</p>
            </div>
        </Card>
    );
}

function IntelligenceCard({ title, content, icon }: any) {
    return (
        <Card className="border border-slate-200 shadow-sm rounded-xl bg-white p-6">
            <div className="flex items-center gap-2.5 mb-5">
                <div className="p-1.5 bg-slate-50 border border-slate-200/60 rounded-md">
                    <div className="w-4 h-4 text-slate-600 [&>svg]:w-full [&>svg]:h-full">{icon}</div>
                </div>
                <h3 className="text-[16px] font-bold text-slate-900 tracking-tight">{title}</h3>
            </div>
            <p className="text-slate-600 text-[14px] leading-relaxed whitespace-pre-wrap">
                {content?.replace(/\*\*(.*?)\*\*/g, '$1').replace(/\*(.*?)\*/g, '$1')}
            </p>
        </Card>
    );
}

function RiskBlock({ title, level, description }: any) {
    const isHigh = level?.toLowerCase() === 'high';
    const isMed = level?.toLowerCase() === 'medium';
    return (
        <Card className="border border-slate-200 shadow-sm rounded-xl p-5 text-center bg-white">
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-1.5">{title}</p>
            <div className={`text-[15px] font-bold uppercase tracking-tight mb-1 ${isHigh ? 'text-rose-600' : isMed ? 'text-amber-600' : 'text-emerald-600'}`}>
                {level}
            </div>
            <p className="text-[11px] text-slate-400 font-medium">{description}</p>
        </Card>
    );
}

function MetricRow({ label, value, isPositive, isWarn }: any) {
    return (
        <TableRow className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
            <TableCell className="px-6 h-12 font-medium text-slate-600 text-[13px]">{label}</TableCell>
            <TableCell className="px-6 h-12">
                <span className={`font-mono text-[14px] font-semibold ${isPositive ? "text-emerald-600" : isWarn ? "text-rose-600" : "text-slate-900"}`}>
                    {value}
                </span>
            </TableCell>
        </TableRow>
    );
}
