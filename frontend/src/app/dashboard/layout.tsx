import {SupabaseProvider} from "@/components/SupabaseProvider";

export default function RootLayout({
                                       children,
                                   }: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <div className={'h-screen w-screen'}>
            <SupabaseProvider>
                {children}
            </SupabaseProvider>
        </div>
    );
}
