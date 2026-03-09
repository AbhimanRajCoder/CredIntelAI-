"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Chrome, Lock, CreditCard } from "lucide-react";

export default function LoginPage() {
    const [loading, setLoading] = useState(false);

    const handleGoogleLogin = async () => {
        try {
            setLoading(true);
            const { error } = await supabase.auth.signInWithOAuth({
                provider: 'google',
                options: {
                    redirectTo: `${window.location.origin}/dashboard`,
                }
            });
            if (error) throw error;
        } catch (error) {
            console.error("Login Error:", error);
            alert("Check if Supabase Google Provider is configured in your dashboard.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
            <Card className="max-w-md w-full shadow-xl border-slate-200">
                <CardHeader className="text-center space-y-1">
                    <div className="flex justify-center mb-4">
                        <div className="w-16 h-16 bg-[#0B3C5D] rounded-2xl flex items-center justify-center shadow-lg transform rotate-3 hover:rotate-0 transition-transform duration-300">
                            <CreditCard className="text-white w-10 h-10" />
                        </div>
                    </div>
                    <CardTitle className="text-3xl font-black tracking-tight text-[#0B3C5D]">Intelli-Credit</CardTitle>
                    <CardDescription className="text-slate-500 font-medium">
                        Secure Corporate Credit Appraisal Management
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4 pt-4">
                    <Button
                        onClick={handleGoogleLogin}
                        disabled={loading}
                        variant="outline"
                        className="w-full py-6 text-lg font-semibold hover:bg-slate-50 border-2 border-slate-200 transition-all active:scale-[0.98]"
                    >
                        {loading ? (
                            <div className="w-6 h-6 border-2 border-slate-400 border-t-transparent rounded-full animate-spin mr-2" />
                        ) : (
                            <Chrome className="mr-3 w-6 h-6 text-blue-600" />
                        )}
                        Sign in with Google
                    </Button>

                    <div className="flex items-center gap-2 text-xs text-slate-400 justify-center mt-6">
                        <Lock className="w-3 h-3" />
                        <span>Secure Enterprise Authentication via Supabase</span>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
