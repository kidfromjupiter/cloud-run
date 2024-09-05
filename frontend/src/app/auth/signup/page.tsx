'use client'
import Link from "next/link"

import {Button} from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import {Input} from "@/components/ui/input"
import {Label} from "@/components/ui/label"
import {useSupabase} from "@/components/SupabaseProvider";
import {useState} from "react";

const description: string =
    "A sign up form with first name, last name, email and password inside a card. There's an option to sign up with GitHub and a link to login if you already have an account"

export default function SignUp() {
    const {supabaseClient} = useSupabase()
    const [email, setEmail] = useState("")
    const [pw, setPw] = useState("")

    return (
        <div className={'h-full flex justify-center items-center bg-black'}>

            <Card className="mx-auto max-w-sm">
                <CardHeader>
                    <CardTitle className="text-xl">Sign Up</CardTitle>
                    <CardDescription>
                        Enter your information to create an account
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-4">

                        <div className="grid gap-2">
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="m@example.com"
                                required
                                onChange={(e) => setEmail(e.target.value)}
                                value={email}
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="password">Password</Label>
                            <Input id="password" type="password"
                                   onChange={(e) => setPw(e.target.value)} value={pw}
                            />
                        </div>
                        <Button type="submit" className="w-full" onClick={()=> supabaseClient?.auth.signUp(
                            {email, password: pw},
                        )}>
                            Create an account
                        </Button>
                        {/*<Button variant="outline" className="w-full">*/}
                        {/*    Sign up with GitHub*/}
                        {/*</Button>*/}
                    </div>
                    <div className="mt-4 text-center text-sm">
                        Already have an account?{" "}
                        <Link href="/auth/login" className="underline">
                            Sign in
                        </Link>
                    </div>
                </CardContent>
            </Card>
        </div>

    )
}
