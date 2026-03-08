"use client"

import { useState } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { useRouter } from "next/navigation"
import { Sparkles } from "lucide-react"

export default function LoginPage() {
    const { signIn, signUp, signInWithGoogle } = useAuth()
    const router = useRouter()
    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [isSignUp, setIsSignUp] = useState(false)
    const [error, setError] = useState("")
    const [loading, setLoading] = useState(false)

    const handleSubmit = async () => {
        setError("")
        setLoading(true)
        try {
            if (isSignUp) {
                await signUp(email, password)
            } else {
                await signIn(email, password)
            }
            router.push("/")
        } catch (err: any) {
            setError(err.message || "Authentication failed")
        } finally {
            setLoading(false)
        }
    }

    const handleGoogle = async () => {
        try {
            await signInWithGoogle()
            router.push("/")
        } catch (err: any) {
            setError(err.message)
        }
    }

    return (
        <div style={{
            minHeight: "100vh", display: "flex", alignItems: "center",
            justifyContent: "center", background: "var(--background)"
        }}>
            <div style={{
                width: 400, padding: "2rem", background: "var(--panel)",
                borderRadius: 16, border: "1px solid var(--panel-border)",
                backdropFilter: "blur(12px)", display: "flex",
                flexDirection: "column", gap: "1rem"
            }}>
                <div style={{ textAlign: "center", marginBottom: "1rem" }}>
                    <Sparkles size={40} color="var(--primary)" />
                    <h1 style={{ marginTop: 8, fontSize: "1.5rem", fontWeight: 700 }}>
                        {isSignUp ? "Create Account" : "Sign In"}
                    </h1>
                </div>

                {error && (
                    <p style={{ color: "#ef4444", fontSize: "0.875rem", textAlign: "center" }}>
                        {error}
                    </p>
                )}

                <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    style={{
                        padding: "0.75rem 1rem", borderRadius: 8, border: "1px solid var(--panel-border)",
                        background: "transparent", color: "var(--foreground)", fontSize: "1rem", outline: "none"
                    }}
                />
                <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleSubmit()}
                    style={{
                        padding: "0.75rem 1rem", borderRadius: 8, border: "1px solid var(--panel-border)",
                        background: "transparent", color: "var(--foreground)", fontSize: "1rem", outline: "none"
                    }}
                />

                <button
                    onClick={handleSubmit}
                    disabled={loading}
                    style={{
                        padding: "0.75rem", background: "var(--primary)", color: "white",
                        border: "none", borderRadius: 8, fontSize: "1rem", fontWeight: 600,
                        cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1
                    }}
                >
                    {loading ? "Please wait..." : isSignUp ? "Create Account" : "Sign In"}
                </button>

                <button
                    onClick={handleGoogle}
                    style={{
                        padding: "0.75rem", background: "transparent",
                        border: "1px solid var(--panel-border)", borderRadius: 8,
                        color: "var(--foreground)", fontSize: "1rem", cursor: "pointer"
                    }}
                >
                    Continue with Google
                </button>

                <p style={{ textAlign: "center", fontSize: "0.875rem", opacity: 0.7 }}>
                    {isSignUp ? "Already have an account?" : "Don't have an account?"}{" "}
                    <span
                        onClick={() => setIsSignUp(!isSignUp)}
                        style={{ color: "var(--primary)", cursor: "pointer", fontWeight: 600 }}
                    >
                        {isSignUp ? "Sign In" : "Sign Up"}
                    </span>
                </p>
            </div>
        </div>
    )
}