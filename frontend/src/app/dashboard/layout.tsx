import { Sidebar } from "@/components/Sidebar";

export const metadata = {
    title: "Intelli-Credit Dashboard",
    description: "Automated Corporate Credit Appraisal Engine",
};

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="flex h-screen w-full bg-[#FAFAFA] overflow-hidden">
            <Sidebar />
            <main className="flex-1 h-full overflow-y-auto w-full">
                {children}
            </main>
        </div>
    );
}
