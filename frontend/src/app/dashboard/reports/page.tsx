"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { formatDistanceToNow, format } from "date-fns";
import {
    FileText, CheckCircle2, Clock, XCircle, BarChart3,
    AlertTriangle, Loader2, FileSearch, Search, ShieldAlert,
    FileOutput, Timer, Plus, Filter, ArrowUpRight, ArrowRight,
    ArrowLeft, Download, Building2, ExternalLink
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { supabase } from "@/lib/supabase";
import api from "@/lib/api";
import { useRouter } from "next/navigation";

const STATUS_CONFIG: Record<string, {
    label: string;
    icon: React.ReactNode;
    color: string;
}> = {
    queued: { label: "Queued", icon: <Clock className="mr-1.5 h-3 w-3" />, color: "bg-slate-100 text-slate-700 border-slate-200" },
    pending: { label: "Pending", icon: <Clock className="mr-1.5 h-3 w-3" />, color: "bg-slate-100 text-slate-700 border-slate-200" },
    processing: { label: "Processing", icon: <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />, color: "bg-blue-50 text-blue-700 border-blue-100" },
    parsing_documents: { label: "Parsing", icon: <FileSearch className="mr-1.5 h-3 w-3 animate-pulse" />, color: "bg-indigo-50 text-indigo-700 border-indigo-100" },
    extracting_financials: { label: "Extracting", icon: <BarChart3 className="mr-1.5 h-3 w-3 animate-pulse" />, color: "bg-violet-50 text-violet-700 border-violet-100" },
    ingesting: { label: "Ingesting", icon: <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />, color: "bg-blue-50 text-blue-700 border-blue-100" },
    researching: { label: "Researching", icon: <Search className="mr-1.5 h-3 w-3 animate-pulse" />, color: "bg-cyan-50 text-cyan-700 border-cyan-100" },
    performing_risk_analysis: { label: "Risk Analysis", icon: <ShieldAlert className="mr-1.5 h-3 w-3 animate-pulse" />, color: "bg-amber-50 text-amber-700 border-amber-100" },
    generating_cam: { label: "Generating", icon: <FileOutput className="mr-1.5 h-3 w-3 animate-pulse" />, color: "bg-purple-50 text-purple-700 border-purple-100" },
    completed: { label: "Completed", icon: <CheckCircle2 className="mr-1.5 h-3 w-3" />, color: "bg-emerald-50 text-emerald-700 border-emerald-100" },
    failed: { label: "Failed", icon: <XCircle className="mr-1.5 h-3 w-3" />, color: "bg-rose-50 text-rose-700 border-rose-100" },
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ReportsPage() {
    const [analyses, setAnalyses] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const router = useRouter();

    useEffect(() => {
        const checkUser = async () => {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) {
                router.push("/login");
                return;
            }
        };

        checkUser();
        fetchAnalyses();
        const interval = setInterval(fetchAnalyses, 5000);
        return () => clearInterval(interval);
    }, []);

    const fetchAnalyses = async () => {
        try {
            const res = await api.get(`/analyses`);
            if (res.data?.analyses) {
                setAnalyses(res.data.analyses);
            }
        } catch (error) {
            console.error("Failed to fetch analyses:", error);
        } finally {
            setLoading(false);
        }
    };

    const filteredAnalyses = useMemo(() => {
        return analyses.filter(a =>
            a.company_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            a.sector?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            a.analysis_id?.toLowerCase().includes(searchQuery.toLowerCase())
        ).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    }, [analyses, searchQuery]);

    const getStatusStyle = (status: string) => {
        return STATUS_CONFIG[status] || {
            label: status.replace(/_/g, " "),
            icon: <Clock className="mr-1.5 h-3 w-3" />,
            color: "bg-slate-100 text-slate-600 border-slate-200"
        };
    };

    const formatTime = (dateStr?: string) => {
        if (!dateStr) return "N/A";
        try {
            return format(new Date(dateStr), "MMM dd, yyyy");
        } catch {
            return "N/A";
        }
    };

    return (
        <div className="min-h-screen bg-[#F8FAFC]">
            {/* Header Content */}
            <div className="bg-white border-b border-slate-200 pt-8 pb-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                        <div className="space-y-4">
                            <div className="space-y-1.5">
                                <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Reports Repository</h1>
                                <p className="text-slate-500 text-[15px]">
                                    Access and manage all generated credit appraisal memos.
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center gap-3">
                            <Link href="/dashboard/new">
                                <Button className="bg-[#0B3C5D] hover:bg-[#082a42] text-white h-11 px-6 rounded-md font-bold shadow-md transition-all">
                                    <Plus className="w-4 h-4 mr-2" /> New Analysis
                                </Button>
                            </Link>
                        </div>
                    </div>
                </div>
            </div>

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-6">

                {/* Search & Filter Bar */}
                <div className="flex flex-col md:flex-row gap-4">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                        <Input
                            placeholder="Search by company, sector, or ID..."
                            className="pl-10 h-11 bg-white border-slate-200 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                    <Button variant="outline" className="h-11 border-slate-200 bg-white text-slate-600 font-medium px-5">
                        <Filter className="w-4 h-4 mr-2" /> Filter Table
                    </Button>
                    <Button variant="outline" className="h-11 border-slate-200 bg-white text-slate-600 font-medium px-5">
                        <Download className="w-4 h-4 mr-2" /> Export CSV
                    </Button>
                </div>

                {/* Table View */}
                <Card className="border border-slate-200 shadow-sm rounded-xl bg-white overflow-hidden">
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-slate-50/50 hover:bg-slate-50/50">
                                <TableHead className="w-[300px] font-semibold text-slate-900">Company Details</TableHead>
                                <TableHead className="font-semibold text-slate-900">Sector</TableHead>
                                <TableHead className="font-semibold text-slate-900">Status</TableHead>
                                <TableHead className="font-semibold text-slate-900">Risk Score</TableHead>
                                <TableHead className="font-semibold text-slate-900">Date Generated</TableHead>
                                <TableHead className="text-right font-semibold text-slate-900">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {loading ? (
                                Array.from({ length: 5 }).map((_, i) => (
                                    <TableRow key={i}>
                                        <TableCell colSpan={6}>
                                            <div className="h-12 w-full animate-pulse bg-slate-100 rounded-md" />
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : filteredAnalyses.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="h-64 text-center">
                                        <div className="flex flex-col items-center justify-center space-y-3">
                                            <div className="p-4 bg-slate-50 rounded-full">
                                                <FileSearch className="h-10 w-10 text-slate-200" />
                                            </div>
                                            <p className="text-slate-500 font-medium">No analyses found matching your search.</p>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ) : (
                                filteredAnalyses.map((analysis) => {
                                    const status = getStatusStyle(analysis.status);
                                    return (
                                        <TableRow key={analysis.analysis_id} className="hover:bg-slate-50/50 transition-colors cursor-pointer group" onClick={() => router.push(`/dashboard/report/${analysis.analysis_id}`)}>
                                            <TableCell className="py-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="h-9 w-9 flex items-center justify-center rounded-lg bg-slate-100 border border-slate-200/60 font-semibold text-slate-700 text-[13px]">
                                                        {analysis.company_name?.substring(0, 1) || "C"}
                                                    </div>
                                                    <div>
                                                        <p className="font-bold text-slate-900 leading-none">{analysis.company_name || "Enterprise Analysis"}</p>
                                                        <p className="text-[11px] font-medium text-slate-400 mt-1 uppercase tracking-wider font-mono">ID: {analysis.analysis_id.substring(0, 8)}</p>
                                                    </div>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant="outline" className="bg-white border-slate-200 text-slate-600 font-medium rounded-md px-2 py-0.5 text-[11px]">
                                                    {analysis.sector || "N/A"}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>
                                                <Badge className={`px-2.5 py-1 rounded-md text-[11px] font-bold tracking-tight border shadow-none ${status.color}`}>
                                                    <span className="flex items-center gap-1.5 break-normal whitespace-nowrap">
                                                        {status.icon}
                                                        {status.label.toUpperCase()}
                                                    </span>
                                                </Badge>
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex items-center gap-2">
                                                    <span className={`text-[15px] font-bold ${analysis.risk_score ? (analysis.risk_score > 60 ? 'text-emerald-600' : analysis.risk_score > 40 ? 'text-amber-600' : 'text-rose-600') : 'text-slate-300'}`}>
                                                        {analysis.risk_score != null ? Math.round(analysis.risk_score) : "--"}
                                                    </span>
                                                    {analysis.risk_score != null && (
                                                        <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                                            <div
                                                                className={`h-full ${analysis.risk_score > 60 ? 'bg-emerald-500' : analysis.risk_score > 40 ? 'bg-amber-500' : 'bg-rose-500'}`}
                                                                style={{ width: `${analysis.risk_score}%` }}
                                                            />
                                                        </div>
                                                    )}
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <p className="text-[13px] text-slate-600 font-medium">{formatTime(analysis.created_at)}</p>
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <div className="flex justify-end gap-2">
                                                    {analysis.status === "completed" && (
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            className="h-8 w-8 p-0 rounded-md text-slate-400 hover:text-[#0B3C5D] transition-colors"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                window.open(`${API_URL}/download-pdf/${analysis.analysis_id}`, '_blank');
                                                            }}
                                                            title="Download PDF Report"
                                                        >
                                                            <FileOutput className="h-4 w-4" />
                                                        </Button>
                                                    )}
                                                    <Link href={`/dashboard/report/${analysis.analysis_id}`} onClick={(e) => e.stopPropagation()}>
                                                        <Button variant="ghost" size="sm" className="h-8 group-hover:bg-slate-900 group-hover:text-white rounded-md text-[12px] font-bold transition-all">
                                                            View Report <ExternalLink className="ml-1.5 h-3 w-3" />
                                                        </Button>
                                                    </Link>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })
                            )}
                        </TableBody>
                    </Table>
                </Card>
            </main>
        </div>
    );
}
