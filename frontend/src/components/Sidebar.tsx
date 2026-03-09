"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, FileText, PlusCircle, PieChart, Settings, LogOut, User } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { cn } from "@/lib/utils";

const navigation = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "New Analysis", href: "/dashboard/new", icon: PlusCircle },
    { name: "Reports", href: "/dashboard/reports", icon: FileText },
    { name: "Portfolio", href: "/dashboard/portfolio", icon: PieChart },
    { name: "Settings", href: "/dashboard/settings", icon: Settings },
];

export function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const [user, setUser] = useState<any>(null);

    useEffect(() => {
        const fetchUser = async () => {
            const { data: { session } } = await supabase.auth.getSession();
            if (session?.user) {
                setUser(session.user);
            }
        };
        fetchUser();
    }, []);

    const handleLogout = async () => {
        await supabase.auth.signOut();
        router.push("/");
    };

    const userName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || "User";

    return (
        <div className="flex h-full w-[260px] flex-col border-r border-slate-200 bg-[#FAFAFA] px-4 py-8 gap-8 shadow-[1px_0_5px_rgba(0,0,0,0.02)]">
            <div className="flex items-center gap-3 px-2">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#0B3C5D] font-bold text-white shadow-sm ring-1 ring-[#0B3C5D]/10 text-lg">
                    IC
                </div>
                <span className="text-[19px] font-black tracking-tight text-[#0B3C5D]">Intelli-Credit</span>
            </div>

            <nav className="flex-1 space-y-1.5 pt-2">
                {navigation.map((item) => {
                    const isActive = pathname === item.href || (pathname.startsWith("/dashboard/report") && item.name === "Reports");
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "group flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-[14px] font-semibold transition-all duration-200",
                                isActive
                                    ? "bg-white text-[#0B3C5D] shadow-sm ring-1 ring-slate-200/50"
                                    : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                            )}
                        >
                            <item.icon
                                className={cn(
                                    "h-4.5 w-4.5 flex-shrink-0",
                                    isActive ? "text-[#0B3C5D]" : "text-slate-400 group-hover:text-slate-600"
                                )}
                                aria-hidden="true"
                            />
                            {item.name}
                        </Link>
                    );
                })}
            </nav>

            <div className="mt-auto space-y-4">
                <div className="px-2 py-4 border-t border-slate-200 space-y-4">
                    <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-full bg-slate-200 flex items-center justify-center overflow-hidden border border-slate-300">
                            {user?.user_metadata?.avatar_url ? (
                                <img src={user.user_metadata.avatar_url} alt="Profile" className="h-full w-full object-cover" />
                            ) : (
                                <User className="h-5 w-5 text-slate-500" />
                            )}
                        </div>
                        <div className="flex-1 overflow-hidden">
                            <p className="text-sm font-bold text-slate-900 truncate">{userName}</p>
                            <p className="text-[11px] font-medium text-slate-500 truncate">{user?.email}</p>
                        </div>
                    </div>

                    <button
                        onClick={handleLogout}
                        className="flex w-full items-center gap-3 rounded-lg px-3.5 py-2.5 text-[14px] font-semibold text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-600 border border-transparent hover:border-rose-100 shadow-sm"
                    >
                        <LogOut className="h-4 w-4 flex-shrink-0" />
                        Sign Out
                    </button>
                </div>
            </div>
        </div>
    );
}

