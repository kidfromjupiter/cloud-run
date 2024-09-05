'use client'
import React, {createContext, useContext, useEffect, useState} from 'react';
import {createClient, SupabaseClient} from '@supabase/supabase-js';

// Initialize Supabase client
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNoZG9seXN4d3R2anN2enl0Y2ZyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjA5Njg3MDQsImV4cCI6MjAzNjU0NDcwNH0.ZXwTkBYKcqc4rhl2EMY88vS67wwtH9xluDP6dcte0KY"
const SUPABASE_URL = "https://chdolysxwtvjsvzytcfr.supabase.co"

// Create a context
interface SupabaseProviderProps {
    supabaseClient: SupabaseClient | null
}

const SupabaseContext = createContext<SupabaseProviderProps>({supabaseClient: null});

// Create a provider component
export const SupabaseProvider = ({children}: { children: React.ReactNode }) => {
    const [supabaseClient, setSupabaseClient] = useState<SupabaseClient | null>(null)
    useEffect(() => {
        const _supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
        setSupabaseClient(_supabase)
    }, []);
    return (
        <SupabaseContext.Provider value={{supabaseClient: supabaseClient}}>
            {children}
        </SupabaseContext.Provider>
    );
};

// Create a hook to use the Supabase context
export const useSupabase = () => {
    const context = useContext(SupabaseContext);
    if (context === undefined) {
        throw new Error('useSupabase must be used within a SupabaseProvider');
    }
    return context;
};
