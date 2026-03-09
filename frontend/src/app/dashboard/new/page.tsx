"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import api from "@/lib/api";
import { supabase } from "@/lib/supabase";
import {
    Upload, File as LucideFile, X, Info, Rocket, Building2,
    ChevronRight, ArrowLeft, ShieldCheck, FileText, CheckCircle2,
    AlertCircle, Briefcase, Landmark, Zap, Activity
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import Link from "next/link";

export default function NewAnalysisPage() {
    const router = useRouter();

    useEffect(() => {
        const checkUser = async () => {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) {
                router.push("/login");
            }
        };
        checkUser();
    }, []);

    const [formData, setFormData] = useState({
        company_name: "",
        sector: "",
        loan_amount_requested: "",
        due_diligence_notes: "",
    });

    const [files, setFiles] = useState<File[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const selectedFiles = Array.from(e.target.files).filter(
                file => file.type === "application/pdf"
            );

            if (selectedFiles.length !== e.target.files.length) {
                toast.warning("Only PDF files are supported. Some files were ignored.");
            }

            setFiles(prev => [...prev, ...selectedFiles]);
        }
    };

    const removeFile = (index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value,
        });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.company_name || !formData.sector) {
            toast.error("Company name and sector are required.");
            return;
        }

        setIsSubmitting(true);
        let analysisId = null;

        try {
            // Step 1: Upload Documents if any
            if (files.length > 0) {
                toast.info(`Uploading ${files.length} document(s)...`);

                const uploadData = new FormData();
                files.forEach(file => {
                    uploadData.append("files", file);
                });

                const uploadRes = await api.post(`/upload-documents`, uploadData, {
                    headers: {
                        "Content-Type": "multipart/form-data",
                    },
                    onUploadProgress: (progressEvent) => {
                        const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
                        setUploadProgress(percentCompleted);
                    }
                });

                analysisId = uploadRes.data.analysis_id;
            }

            // Step 2: Trigger Analysis
            toast.info("Starting credit appraisal analysis pipeline...");

            const analysisPayload = {
                company_name: formData.company_name,
                sector: formData.sector,
                due_diligence_notes: formData.due_diligence_notes || null,
                loan_amount_requested: formData.loan_amount_requested ? parseFloat(formData.loan_amount_requested) : null,
            };

            const endpoint = analysisId
                ? `/analyze-company?analysis_id=${analysisId}`
                : `/analyze-company`;

            const analysisRes = await api.post(endpoint, analysisPayload);

            toast.success("Analysis started successfully!");
            router.push("/dashboard");

        } catch (error: any) {
            console.error("Analysis failed:", error);
            toast.error(error.response?.data?.detail || "An error occurred while starting the analysis.");
        } finally {
            setIsSubmitting(false);
            setUploadProgress(0);
        }
    };

    return (
        <div className="min-h-screen bg-[#F8FAFC]">
            {/* Header / Breadcrumb */}
            <div className="bg-white border-b border-slate-200">
                <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/dashboard">
                            <Button variant="ghost" size="sm" className="rounded-full h-10 w-10 p-0 text-slate-400 hover:text-[#0B3C5D]">
                                <ArrowLeft className="w-5 h-5" />
                            </Button>
                        </Link>
                        <div className="h-6 w-0.5 bg-slate-200" />
                        <h1 className="text-xl font-black text-[#0B3C5D] tracking-tight">Initiate New Appraisal</h1>
                    </div>
                    <div className="hidden md:flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-slate-400">
                        <span>Management Console</span>
                        <ChevronRight className="w-3 h-3" />
                        <span className="text-[#0B3C5D]">Appraisal Pipeline</span>
                    </div>
                </div>
            </div>

            <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <div className="grid lg:grid-cols-12 gap-10">

                    {/* Left Column - Form */}
                    <div className="lg:col-span-7 space-y-8">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5 }}
                        >
                            <Card className="border-none shadow-2xl rounded-[40px] overflow-hidden bg-white">
                                <CardHeader className="p-10 pb-6">
                                    <div className="flex items-center gap-3 mb-2">
                                        <div className="h-10 w-10 bg-blue-50 text-[#0B3C5D] rounded-xl flex items-center justify-center">
                                            <Building2 className="w-5 h-5" />
                                        </div>
                                        <CardTitle className="text-2xl font-black text-[#0B3C5D] tracking-tight">Entity Identification</CardTitle>
                                    </div>
                                    <CardDescription className="text-slate-400 font-medium text-lg">Provide key metadata for the credit risk model.</CardDescription>
                                </CardHeader>

                                <CardContent className="p-10 pt-0 space-y-8">
                                    <form id="appraisal-form" onSubmit={handleSubmit} className="space-y-6">
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                            <div className="space-y-2">
                                                <Label htmlFor="company_name" className="text-xs font-black uppercase tracking-widest text-slate-500 ml-1">Company Name *</Label>
                                                <Input
                                                    id="company_name"
                                                    name="company_name"
                                                    required
                                                    placeholder="Legal Entity Name"
                                                    className="h-14 rounded-2xl border-slate-100 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-[#0B3C5D]/10 text-lg font-bold text-[#0B3C5D] transition-all"
                                                    value={formData.company_name}
                                                    onChange={handleChange}
                                                />
                                            </div>
                                            <div className="space-y-2">
                                                <Label htmlFor="sector" className="text-xs font-black uppercase tracking-widest text-slate-500 ml-1">Economic Sector *</Label>
                                                <Input
                                                    id="sector"
                                                    name="sector"
                                                    required
                                                    placeholder="Industry Classification"
                                                    className="h-14 rounded-2xl border-slate-100 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-[#0B3C5D]/10 text-lg font-bold text-[#0B3C5D] transition-all"
                                                    value={formData.sector}
                                                    onChange={handleChange}
                                                />
                                            </div>
                                        </div>

                                        <div className="space-y-2">
                                            <Label htmlFor="loan_amount_requested" className="text-xs font-black uppercase tracking-widest text-slate-500 ml-1">Exposure Required (INR)</Label>
                                            <div className="relative">
                                                <Input
                                                    id="loan_amount_requested"
                                                    name="loan_amount_requested"
                                                    type="number"
                                                    placeholder="Expected Loan Amount"
                                                    className="h-14 pl-12 rounded-2xl border-slate-100 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-[#0B3C5D]/10 text-lg font-bold text-[#0B3C5D] transition-all"
                                                    value={formData.loan_amount_requested}
                                                    onChange={handleChange}
                                                />
                                                <Landmark className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300" />
                                            </div>
                                        </div>

                                        <div className="space-y-2">
                                            <Label htmlFor="due_diligence_notes" className="text-xs font-black uppercase tracking-widest text-slate-500 ml-1">Analyst Context / Hypotheses</Label>
                                            <Textarea
                                                id="due_diligence_notes"
                                                name="due_diligence_notes"
                                                className="min-h-[160px] rounded-3xl border-slate-100 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-[#0B3C5D]/10 p-6 text-slate-700 font-medium text-lg leading-relaxed transition-all resize-none"
                                                placeholder="Enter specific risk vectors or observations for the system to prioritize..."
                                                value={formData.due_diligence_notes}
                                                onChange={handleChange}
                                            />
                                            <p className="px-2 text-[11px] font-bold text-slate-400 flex items-center gap-1.5 uppercase tracking-wider">
                                                <Info className="h-3 w-3" /> The automated system will prioritize these notes during the Risk Assessment stage.
                                            </p>
                                        </div>
                                    </form>
                                </CardContent>
                            </Card>
                        </motion.div>
                    </div>

                    {/* Right Column - Files */}
                    <div className="lg:col-span-5 space-y-8">
                        <motion.div
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.5, delay: 0.2 }}
                        >
                            <Card className="border-none shadow-2xl rounded-[40px] overflow-hidden bg-white p-10 space-y-8">
                                <div className="flex items-center gap-3">
                                    <div className="h-10 w-10 bg-amber-50 text-amber-600 rounded-xl flex items-center justify-center">
                                        <FileText className="w-5 h-5" />
                                    </div>
                                    <h3 className="text-2xl font-black text-[#0B3C5D] tracking-tight">Financial Artifacts</h3>
                                </div>

                                {/* Custom Dropzone */}
                                <div className="relative">
                                    <input
                                        type="file"
                                        multiple
                                        accept=".pdf"
                                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                                        onChange={handleFileChange}
                                        disabled={isSubmitting}
                                    />
                                    <div className="border-2 border-dashed border-slate-200 rounded-[32px] p-10 flex flex-col items-center justify-center text-center bg-[#F8FAFC] group-hover:bg-slate-50 transition-all group border-spacing-4">
                                        <div className="h-16 w-16 bg-white rounded-2xl shadow-sm flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                            <Upload className="w-8 h-8 text-[#0B3C5D]" />
                                        </div>
                                        <p className="text-lg font-bold text-[#0B3C5D] mb-1">Click to browse or drop</p>
                                        <p className="text-sm font-medium text-slate-400">PDF Financial Statements only.</p>
                                    </div>
                                </div>

                                {/* File List */}
                                <AnimatePresence>
                                    {files.length > 0 && (
                                        <motion.div
                                            initial={{ height: 0, opacity: 0 }}
                                            animate={{ height: 'auto', opacity: 1 }}
                                            exit={{ height: 0, opacity: 0 }}
                                            className="space-y-3"
                                        >
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-xs font-black uppercase tracking-widest text-[#0B3C5D]">Queued Assets</span>
                                                <Badge className="bg-[#0B3C5D] text-white rounded-full">{files.length} Files</Badge>
                                            </div>
                                            <div className="space-y-3 max-h-[240px] overflow-y-auto pr-2 custom-scrollbar">
                                                {files.map((file, idx) => (
                                                    <motion.div
                                                        key={idx}
                                                        initial={{ x: -10, opacity: 0 }}
                                                        animate={{ x: 0, opacity: 1 }}
                                                        className="flex items-center justify-between p-4 rounded-2xl bg-slate-50 border border-slate-100"
                                                    >
                                                        <div className="flex items-center gap-3 overflow-hidden">
                                                            <LucideFile className="w-5 h-5 text-amber-500 shrink-0" />
                                                            <div className="flex flex-col">
                                                                <span className="text-sm font-bold text-[#0B3C5D] truncate max-w-[180px]">{file.name}</span>
                                                                <span className="text-[10px] font-bold text-slate-400">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                                                            </div>
                                                        </div>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => removeFile(idx)}
                                                            className="h-8 w-8 p-0 rounded-full text-slate-300 hover:text-rose-500 hover:bg-rose-50"
                                                            disabled={isSubmitting}
                                                        >
                                                            <X className="w-4 h-4" />
                                                        </Button>
                                                    </motion.div>
                                                ))}
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>

                                {/* Instructions */}
                                {!isSubmitting && (
                                    <div className="p-6 bg-blue-50/50 rounded-3xl border border-blue-100 flex gap-4">
                                        <Zap className="w-6 h-6 text-[#00A8A8] shrink-0" />
                                        <div className="space-y-1">
                                            <p className="text-xs font-black uppercase tracking-widest text-[#0B3C5D]">Automated Appraisal Protocol</p>
                                            <p className="text-[11px] font-medium text-slate-500 leading-relaxed">
                                                The automated system will execute parallel extraction. Expected turnaround: 120-180 seconds based on document density.
                                            </p>
                                        </div>
                                    </div>
                                )}

                                {/* Progress & Submit */}
                                <div className="pt-2">
                                    {isSubmitting ? (
                                        <div className="space-y-4">
                                            <div className="flex items-center justify-between text-xs font-black uppercase tracking-widest text-[#0B3C5D]">
                                                <span>{uploadProgress < 100 ? "Uploading to Secure Storage" : "Initializing Analysis"}</span>
                                                <span>{uploadProgress}%</span>
                                            </div>
                                            <Progress value={uploadProgress} className="h-3 bg-slate-100 [&>div]:bg-[#0B3C5D] rounded-full" />
                                            <div className="flex items-center justify-center gap-3 py-4 text-[#0B3C5D] font-bold italic animate-pulse">
                                                <Activity className="h-4 w-4 animate-bounce" /> Processing Appraisal...
                                            </div>
                                        </div>
                                    ) : (
                                        <Button
                                            form="appraisal-form"
                                            type="submit"
                                            className="w-full h-16 rounded-[24px] bg-[#0B3C5D] hover:bg-[#002b4d] text-white font-black text-lg shadow-xl shadow-[#0B3C5D]/20 transition-all hover:shadow-2xl hover:-translate-y-1 group"
                                        >
                                            Start Appraisal <Rocket className="w-6 h-6 ml-3 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
                                        </Button>
                                    )}
                                </div>
                            </Card>
                        </motion.div>
                    </div>
                </div>
            </main>
        </div>
    );
}
