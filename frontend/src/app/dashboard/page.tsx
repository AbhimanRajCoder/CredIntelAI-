"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { formatDistanceToNow, format, parseISO, startOfDay } from "date-fns";
import {
  ArrowRight, FileText, CheckCircle2, Clock, XCircle, BarChart3,
  AlertTriangle, Loader2, FileSearch, Search, ShieldAlert, FileOutput, Timer,
  Plus, LogOut, TrendingUp, Users, PieChart as PieChartIcon, Activity,
  Download, Filter, ArrowUpRight, ArrowDownRight
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress, ProgressTrack, ProgressIndicator } from "@/components/ui/progress";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, AreaChart, Area, Legend
} from "recharts";
import { supabase } from "@/lib/supabase";
import api from "@/lib/api";
import { useRouter } from "next/navigation";

type Analysis = {
  analysis_id: string;
  status: string;
  company_name: string;
  sector?: string;
  risk_score?: number | null;
  credit_grade?: string | null;
  created_at?: string;
  has_report: boolean;
};

const STATUS_CONFIG: Record<string, {
  label: string;
  icon: React.ReactNode;
  color: string;
  progress: number;
}> = {
  queued: {
    label: "Queued",
    icon: <Clock className="mr-1.5 h-3 w-3" />,
    color: "bg-slate-100 text-slate-700 border-slate-200",
    progress: 5,
  },
  pending: {
    label: "Pending",
    icon: <Clock className="mr-1.5 h-3 w-3" />,
    color: "bg-slate-100 text-slate-700 border-slate-200",
    progress: 5,
  },
  processing: {
    label: "Processing",
    icon: <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />,
    color: "bg-blue-50 text-blue-700 border-blue-100",
    progress: 10,
  },
  parsing_documents: {
    label: "Parsing Documents",
    icon: <FileSearch className="mr-1.5 h-3 w-3 animate-pulse" />,
    color: "bg-indigo-50 text-indigo-700 border-indigo-100",
    progress: 20,
  },
  extracting_financials: {
    label: "Extracting Financials",
    icon: <BarChart3 className="mr-1.5 h-3 w-3 animate-pulse" />,
    color: "bg-violet-50 text-violet-700 border-violet-100",
    progress: 35,
  },
  ingesting: {
    label: "Ingesting Data",
    icon: <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />,
    color: "bg-blue-50 text-blue-700 border-blue-100",
    progress: 25,
  },
  researching: {
    label: "Researching",
    icon: <Search className="mr-1.5 h-3 w-3 animate-pulse" />,
    color: "bg-cyan-50 text-cyan-700 border-cyan-100",
    progress: 50,
  },
  researching_company: {
    label: "Researching Company",
    icon: <Search className="mr-1.5 h-3 w-3 animate-pulse" />,
    color: "bg-cyan-50 text-cyan-700 border-cyan-100",
    progress: 50,
  },
  performing_risk_analysis: {
    label: "Risk Analysis",
    icon: <ShieldAlert className="mr-1.5 h-3 w-3 animate-pulse" />,
    color: "bg-amber-50 text-amber-700 border-amber-100",
    progress: 70,
  },
  analyzing_risk: {
    label: "Analyzing Risk",
    icon: <ShieldAlert className="mr-1.5 h-3 w-3 animate-pulse" />,
    color: "bg-amber-50 text-amber-700 border-amber-100",
    progress: 70,
  },
  generating_cam: {
    label: "Generating CAM",
    icon: <FileOutput className="mr-1.5 h-3 w-3 animate-pulse" />,
    color: "bg-purple-50 text-purple-700 border-purple-100",
    progress: 90,
  },
  completed: {
    label: "Completed",
    icon: <CheckCircle2 className="mr-1.5 h-3 w-3" />,
    color: "bg-emerald-50 text-emerald-700 border-emerald-100",
    progress: 100,
  },
  failed: {
    label: "Failed",
    icon: <XCircle className="mr-1.5 h-3 w-3" />,
    color: "bg-rose-50 text-rose-700 border-rose-100",
    progress: 100,
  },
  needs_review: {
    label: "Needs Review",
    icon: <AlertTriangle className="mr-1.5 h-3 w-3" />,
    color: "bg-orange-50 text-orange-700 border-orange-100",
    progress: 100,
  },
};

const COLORS = ["#0F172A", "#2563EB", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899"];

const getStatusConfig = (status: string) => {
  return STATUS_CONFIG[status] || {
    label: status.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
    icon: <Clock className="mr-1.5 h-3 w-3" />,
    color: "bg-slate-100 text-slate-600 border-slate-200",
    progress: 50,
  };
};

const isProcessing = (status: string) => {
  return !["completed", "failed", "needs_review", "queued", "pending"].includes(status);
};

const getGradeColor = (grade: string | null | undefined) => {
  if (!grade) return "bg-slate-100 text-slate-400";
  if (grade.startsWith("A")) return "bg-emerald-50 text-emerald-700 border-emerald-100";
  if (grade.startsWith("B")) return "bg-amber-50 text-amber-700 border-amber-100";
  return "bg-rose-50 text-rose-700 border-rose-100";
};

export default function DashboardPage() {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  const router = useRouter();

  useEffect(() => {
    const checkUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push("/login");
        return;
      }
      setUser(session.user);
    };

    checkUser();
    fetchAnalyses();
    const interval = setInterval(fetchAnalyses, 4000);
    return () => clearInterval(interval);
  }, []);

  const fetchAnalyses = async () => {
    try {
      const res = await api.get(`/analyses`);
      if (res.data?.analyses) {
        setAnalyses(res.data.analyses);
      } else {
        setAnalyses([]);
      }
    } catch (error) {
      console.error("Failed to fetch analyses:", error);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (dateStr?: string) => {
    if (!dateStr) return null;
    try {
      return formatDistanceToNow(new Date(dateStr), { addSuffix: true });
    } catch {
      return null;
    }
  };

  const userName = user?.user_metadata?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || "User";

  // ─── Visual Analytics Data Preparation ──────────────────────────────────────

  const analyticsData = useMemo(() => {
    if (analyses.length === 0) return null;

    // 1. Credit Score Distribution
    const scoreCounts: Record<string, number> = { "A": 0, "B": 0, "C": 0, "D": 0 };
    analyses.forEach(a => {
      if (a.credit_grade) {
        const grade = a.credit_grade.substring(0, 1);
        if (scoreCounts[grade] !== undefined) scoreCounts[grade]++;
      }
    });
    const creditDist = Object.entries(scoreCounts).map(([name, value]) => ({ name, value }));

    // 2. Risk Score Histogram (Groups of 10)
    const riskBuckets: Record<string, number> = {};
    for (let i = 0; i < 100; i += 20) riskBuckets[`${i}-${i + 19}`] = 0;
    analyses.forEach(a => {
      if (a.risk_score != null) {
        const bucket = Math.floor(a.risk_score / 20) * 20;
        const key = `${bucket}-${bucket + 19}`;
        if (riskBuckets[key] !== undefined) riskBuckets[key]++;
      }
    });
    const riskHistogram = Object.entries(riskBuckets).map(([name, value]) => ({ name, value }));

    // 3. Industry Analysis
    const sectorCounts: Record<string, number> = {};
    analyses.forEach(a => {
      const sector = a.sector || "Other";
      sectorCounts[sector] = (sectorCounts[sector] || 0) + 1;
    });
    const industryData = Object.entries(sectorCounts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 5);

    // 4. Timeline (Last 7 days)
    const timelineCounts: Record<string, number> = {};
    const last7Days = Array.from({ length: 7 }, (_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - i);
      return format(d, "MMM dd");
    }).reverse();

    last7Days.forEach(day => timelineCounts[day] = 0);
    analyses.forEach(a => {
      if (a.created_at) {
        const day = format(new Date(a.created_at), "MMM dd");
        if (timelineCounts[day] !== undefined) timelineCounts[day]++;
      }
    });
    const timelineData = Object.entries(timelineCounts).map(([name, value]) => ({ name, value }));

    // 5. Loan Recommendations
    const recs = { "Approved": 0, "Conditional": 0, "Rejected": 0 };
    analyses.forEach(a => {
      if (a.credit_grade) {
        if (a.credit_grade.startsWith("A")) recs.Approved++;
        else if (a.credit_grade.startsWith("B")) recs.Conditional++;
        else recs.Rejected++;
      }
    });
    const recommendationData = Object.entries(recs).map(([name, value]) => ({ name, value }));

    // Average Risk Score
    const completedWithRisk = analyses.filter(a => a.risk_score != null);
    const avgRisk = completedWithRisk.length > 0
      ? Math.round(completedWithRisk.reduce((acc, a) => acc + (a.risk_score || 0), 0) / completedWithRisk.length)
      : 0;

    return {
      creditDist,
      riskHistogram,
      industryData,
      timelineData,
      recommendationData,
      avgRisk
    };
  }, [analyses]);

  return (
    <div className="min-h-screen bg-[#F8FAFC]">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 lg:hidden">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#0B3C5D] font-bold text-white shadow-sm">
                IC
              </div>
              <span className="text-[15px] font-bold tracking-tight text-[#0B3C5D]">Intelli-Credit</span>
            </div>
            <div className="hidden lg:flex flex-col">
              <span className="text-[13px] text-slate-500 font-medium">Hello there, {userName}</span>
              <span className="text-[14px] font-bold text-slate-900 flex items-center gap-2">Management Console <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" /></span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/dashboard/new">
              <Button size="sm" className="bg-[#0B3C5D] hover:bg-[#082a42] text-white rounded-md px-4 shadow-sm transition-all text-[13px] font-bold h-9">
                <Plus className="w-4 h-4 mr-1.5" /> New Appraisal
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">

        {/* ─── Page Title ─── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
          <div>
            <h1 className="text-2xl font-black text-[#0B3C5D] tracking-tight">Portfolio Overview</h1>
            <p className="text-slate-500 mt-1 text-[14px]">
              Real-time monitoring of corporate credit appraisals.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="bg-white border-slate-200 text-slate-600 font-bold shadow-sm rounded-md px-2.5 py-1 text-[11px] uppercase tracking-wider">
              <Activity className="w-3.5 h-3.5 mr-1.5 text-emerald-500" /> Live Data
            </Badge>
            <Button variant="outline" size="sm" className="rounded-md h-8 border-slate-200 hover:bg-slate-50 shadow-sm text-[12px] text-slate-600 font-bold uppercase tracking-wider">
              <Filter className="w-3.5 h-3.5 mr-1.5" /> Filter
            </Button>
          </div>
        </div>

        {/* ─── KPI Row ─── */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          <StatCard
            title="Total Analyses"
            value={analyses.length}
            icon={<FileText className="h-4 w-4" />}
            description="Appraisals initiated"
          />
          <StatCard
            title="Completed"
            value={analyses.filter(a => a.status === "completed").length}
            icon={<CheckCircle2 className="h-4 w-4" />}
            description="Reports ready"
            trend="+12%"
          />
          <StatCard
            title="In Progress"
            value={analyses.filter(a => isProcessing(a.status)).length}
            icon={<Loader2 className="h-4 w-4 animate-spin" />}
            description="Pipeline active"
          />
          <StatCard
            title="Avg Risk Score"
            value={analyticsData?.avgRisk || 0}
            suffix="/100"
            icon={<ShieldAlert className="h-4 w-4" />}
            description="Portfolio health"
            isScore
          />
          <StatCard
            title="Failed"
            value={analyses.filter(a => a.status === "failed").length}
            icon={<AlertTriangle className="h-4 w-4" />}
            description="Requires review"
          />
        </div>

        {/* ─── Visual Analytics Grid ─── */}
        <div className="grid gap-6 lg:grid-cols-3">

          {/* Credit Score Distribution */}
          <Card className="lg:col-span-2 border border-slate-200 shadow-sm rounded-xl overflow-hidden bg-white hover:shadow-md transition-shadow">
            <CardHeader className="border-b border-slate-100 pb-4">
              <CardTitle className="text-sm font-semibold text-slate-900">Portfolio Credit Rating</CardTitle>
              <CardDescription className="text-xs">Distribution of companies by credit grade</CardDescription>
            </CardHeader>
            <CardContent className="pt-6 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analyticsData?.creditDist}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94A3B8', fontSize: 11 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94A3B8', fontSize: 11 }} />
                  <Tooltip
                    cursor={{ fill: '#F8FAFC' }}
                    contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Bar dataKey="value" fill="#0F172A" radius={[4, 4, 0, 0]} barSize={32} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Industry Analysis */}
          <Card className="border border-slate-200 shadow-sm rounded-xl overflow-hidden bg-white hover:shadow-md transition-shadow">
            <CardHeader className="border-b border-slate-100 pb-4">
              <CardTitle className="text-sm font-semibold text-slate-900">Sector Exposure</CardTitle>
              <CardDescription className="text-xs">Top industries analyzed</CardDescription>
            </CardHeader>
            <CardContent className="pt-6 h-72 flex flex-col justify-center">
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={analyticsData?.industryData}
                    innerRadius={50}
                    outerRadius={70}
                    paddingAngle={2}
                    dataKey="value"
                    stroke="none"
                  >
                    {analyticsData?.industryData?.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-4 space-y-2 px-2 overflow-y-auto max-h-32">
                {analyticsData?.industryData?.map((entry, index) => (
                  <div key={index} className="flex items-center justify-between text-[11px] font-medium">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                      <span className="text-slate-600 truncate max-w-[120px]">{entry.name}</span>
                    </div>
                    <span className="text-slate-900 font-semibold">{entry.value}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Analysis Timeline */}
          <Card className="lg:col-span-2 border border-slate-200 shadow-sm rounded-xl overflow-hidden bg-white hover:shadow-md transition-shadow">
            <CardHeader className="border-b border-slate-100 pb-4">
              <CardTitle className="text-sm font-semibold text-slate-900">Analysis Velocity</CardTitle>
              <CardDescription className="text-xs">Appraisals triggered over the past 7 days</CardDescription>
            </CardHeader>
            <CardContent className="pt-6 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={analyticsData?.timelineData}>
                  <defs>
                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0F172A" stopOpacity={0.1} />
                      <stop offset="95%" stopColor="#0F172A" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94A3B8', fontSize: 11 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94A3B8', fontSize: 11 }} />
                  <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                  <Area type="monotone" dataKey="value" stroke="#0F172A" strokeWidth={2} fillOpacity={1} fill="url(#colorValue)" />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Risk Score Histogram */}
          <Card className="border border-slate-200 shadow-sm rounded-xl overflow-hidden bg-white hover:shadow-md transition-shadow">
            <CardHeader className="border-b border-slate-100 pb-4">
              <CardTitle className="text-sm font-semibold text-slate-900">Risk Profile Score</CardTitle>
              <CardDescription className="text-xs">Histogram of company risk scores</CardDescription>
            </CardHeader>
            <CardContent className="pt-6 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analyticsData?.riskHistogram}>
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94A3B8', fontSize: 10 }} />
                  <YAxis hide />
                  <Tooltip cursor={{ fill: '#F8FAFC' }} contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                  <Bar dataKey="value" fill="#64748B" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

        </div>

        {/* ─── Recent Appraisals Table/Grid ─── */}
        <div className="space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <h2 className="text-2xl font-bold text-[#0B3C5D] tracking-tight">Enterprise Portfolio</h2>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" className="text-slate-500 hover:bg-slate-100 rounded-lg">View All</Button>
              <Button variant="ghost" size="sm" className="text-slate-500 hover:bg-slate-100 rounded-lg">
                <Download className="w-4 h-4 mr-2" /> Export
              </Button>
            </div>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 bg-white rounded-3xl border border-dashed border-slate-300">
              <Loader2 className="h-10 w-10 animate-spin text-[#00A8A8] mb-4" />
              <p className="text-slate-500 font-medium">Synchronizing with automated pipeline...</p>
            </div>
          ) : analyses.length === 0 ? (
            <div className="text-center py-24 bg-white rounded-3xl border border-dashed border-slate-200 shadow-inner flex flex-col items-center">
              <div className="p-6 bg-slate-50 rounded-full mb-6">
                <FileText className="h-16 w-16 text-slate-200" />
              </div>
              <h3 className="text-2xl font-bold text-slate-900 tracking-tight">No Active Appraisals</h3>
              <p className="text-slate-500 mt-2 mb-8 max-w-sm mx-auto">Upload corporate financial documents to initiate your first Automated Credit Appraisal Memo.</p>
              <Link href="/dashboard/new">
                <Button size="lg" className="bg-[#0B3C5D] rounded-full px-10 shadow-lg shadow-[#0B3C5D]/20">
                  New Credit Appraisal
                </Button>
              </Link>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {analyses.map((analysis) => (
                <AnalysisCard key={analysis.analysis_id} analysis={analysis} formatTime={formatTime} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

// ─── Stat Card Component ───────────────────────────────────────────────────

function StatCard({ title, value, icon, description, trend, suffix, isScore }: any) {
  return (
    <Card className="border border-slate-200 shadow-sm rounded-xl bg-white hover:shadow-md transition-all">
      <CardContent className="p-5">
        <div className="flex justify-between items-start mb-4">
          <div className={`p-2 rounded-lg bg-slate-50 text-slate-600 ring-1 ring-slate-200/50`}>
            {icon}
          </div>
          {trend && (
            <div className="flex items-center text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full ring-1 ring-emerald-600/10">
              <ArrowUpRight className="w-3 h-3 mr-0.5" /> {trend}
            </div>
          )}
        </div>
        <div className="space-y-1">
          <p className="text-[13px] font-medium text-slate-500">{title}</p>
          <div className="flex items-baseline gap-1">
            <h3 className="text-2xl font-bold text-slate-900 tracking-tight">{value}</h3>
            {suffix && <span className="text-slate-400 font-medium text-sm">{suffix}</span>}
          </div>
          <p className="text-[12px] text-slate-400 mt-1">{description}</p>
        </div>
      </CardContent>
      {isScore && (
        <div className="h-1 w-full bg-slate-100 mt-2">
          <div
            className="h-full bg-slate-900"
            style={{ width: `${value}%` }}
          />
        </div>
      )}
    </Card>
  );
}

function AnalysisCard({ analysis, formatTime }: any) {
  const config = getStatusConfig(analysis.status);
  const timeAgo = formatTime(analysis.created_at);
  const processing = isProcessing(analysis.status);

  return (
    <Card className="flex flex-col border border-slate-200 shadow-sm rounded-xl overflow-hidden bg-white hover:shadow-md transition-all">
      <CardHeader className="pb-4 pt-5 px-5 relative">
        <div className="absolute top-0 right-0 p-4">
          <Badge className={`text-[10px] font-semibold tracking-wide border border-slate-200 py-0.5 px-2 rounded-md ${config.color.split(' ')[1]} ${config.color.split(' ')[0]} bg-opacity-50`}>
            <span className="flex items-center gap-1 focus:outline-none">{config.icon}{config.label}</span>
          </Badge>
        </div>
        <div className="flex items-center gap-3 mb-1 mt-1">
          <div className="h-9 w-9 flex items-center justify-center rounded-lg bg-slate-100 border border-slate-200/60 shadow-sm font-semibold text-slate-700 text-[13px]">
            {analysis.company_name?.substring(0, 1) || "C"}
          </div>
          <div className="overflow-hidden">
            <CardTitle className="text-[15px] font-semibold text-slate-900 truncate leading-tight" title={analysis.company_name}>
              {analysis.company_name || "Enterprise Analysis"}
            </CardTitle>
            {analysis.sector && (
              <p className="text-[11px] font-medium text-slate-500 mt-0.5">{analysis.sector}</p>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 px-5 pb-5 pt-0 space-y-5">
        {processing ? (
          <div className="space-y-3 bg-slate-50 p-3 rounded-lg border border-slate-200/60">
            <div className="flex justify-between text-[11px] font-semibold tracking-tight text-slate-500">
              <span>{config.label} Stage</span>
              <span className="text-slate-900 font-mono">{config.progress}%</span>
            </div>
            <Progress value={config.progress} className="h-1.5 bg-slate-200">
              <ProgressIndicator className="bg-slate-900" />
            </Progress>
            <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-medium">
              <Activity className="h-3 w-3 animate-pulse text-slate-700" />
              Processing...
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200/60">
              <span className="text-[10px] font-medium text-slate-500 block mb-0.5">Risk Grade</span>
              {analysis.credit_grade ? (
                <div className="flex items-center justify-between">
                  <span className={`text-[15px] font-bold ${getGradeColor(analysis.credit_grade).split(' ')[1]}`}>
                    {analysis.credit_grade}
                  </span>
                  <div className={`h-1.5 w-1.5 rounded-full ${getGradeColor(analysis.credit_grade).split(' ')[0].replace('bg-', 'bg-')}`} />
                </div>
              ) : (
                <span className="text-slate-400 font-bold">—</span>
              )}
            </div>
            <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200/60">
              <span className="text-[10px] font-medium text-slate-500 block mb-0.5">Risk Score</span>
              <div className="flex items-center justify-between">
                <span className="text-[15px] font-bold text-slate-900">
                  {analysis.risk_score != null ? Math.round(analysis.risk_score) : "—"}
                </span>
                {analysis.risk_score != null && (
                  <span className="text-[10px] font-medium text-slate-400">/100</span>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between pt-3 border-t border-slate-100 mt-auto">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500 font-medium">
            <Clock className="h-3 w-3" />
            <span>{timeAgo}</span>
          </div>
          <div className="flex items-center gap-1 text-[10px] font-medium text-slate-500">
            ID: <span className="font-mono text-slate-700">{analysis.analysis_id.substring(0, 6)}</span>
          </div>
        </div>
      </CardContent>

      <CardFooter className="p-0 border-t border-slate-100">
        <Link href={`/dashboard/report/${analysis.analysis_id}`} className="w-full">
          <Button
            className="w-full h-10 rounded-none bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium shadow-none transition-colors text-[13px]"
            disabled={!analysis.has_report && !["failed", "completed", "needs_review"].includes(analysis.status) && !processing}
            variant="ghost"
          >
            <span className="flex items-center gap-2">View Report <ArrowRight className="w-3.5 h-3.5" /></span>
          </Button>
        </Link>
      </CardFooter>
    </Card>
  );
}
