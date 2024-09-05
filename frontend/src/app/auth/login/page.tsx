'use client'
import {LoginForm} from "@/components/login-form"
import {useEffect, useState} from "react";
import {createClient, SupabaseClient} from '@supabase/supabase-js'
import {useSupabase} from "@/components/SupabaseProvider";

export default function Page() {
    const {supabaseClient} = useSupabase()
    return (
        <div className="flex h-screen w-full items-center justify-center px-4 bg-black">
            <LoginForm
                onLoginClick={(email, pw) => supabaseClient?.auth.signInWithPassword({email: email, password: pw})}/>
        </div>
    )
}
