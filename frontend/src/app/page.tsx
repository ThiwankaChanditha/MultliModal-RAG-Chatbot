"use client"

import { useState, useRef, useEffect } from "react"
import styles from "./page.module.css"
import { Sparkles, Send, Menu, MessageSquare, Bot, User, Plus, Paperclip, Loader2, LogOut } from "lucide-react"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useAuth } from "@/contexts/AuthContext"
import { useRouter } from "next/navigation"

type Message = {
  role: "user" | "assistant"
  content: string
}

type UsageInfo = {
  queries_used: number | null
  queries_remaining: number | null
  is_owner: boolean
}

export default function Home() {
  const [query, setQuery] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [usage, setUsage] = useState<UsageInfo | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { user, loading: authLoading, logout, getToken } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login")
    }
  }, [user, authLoading, router])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  if (authLoading) {
    return (
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "center",
        height: "100vh", background: "var(--background)", color: "var(--foreground)"
      }}>
        Loading...
      </div>
    )
  }
  if (!user) return null

  const isLimitReached = usage !== null
    && !usage.is_owner
    && usage.queries_remaining !== null
    && usage.queries_remaining <= 0

  const send = async () => {
    if (!query.trim() || isLimitReached) return

    const userMessage: Message = { role: "user", content: query }
    setMessages(prev => [...prev, userMessage])
    setQuery("")
    setLoading(true)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const token = await getToken()
      const res = await fetch(`${apiUrl}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ query: userMessage.content }),
      })

      // Handle rate limit specifically
      if (res.status === 429) {
        const err = await res.json()
        const detail = err.detail || {}
        setUsage({
          queries_used: detail.queries_used ?? 5,
          queries_remaining: 0,
          is_owner: false,
        })
        setMessages(prev => [...prev, {
          role: "assistant",
          content: `⚠️ ${detail.message || "You have reached your free query limit."}`,
        }])
        return
      }

      if (!res.ok) throw new Error("Server error")

      const data = await res.json()
      setMessages(prev => [...prev, { role: "assistant", content: data.answer }])

      // Update usage counter from response
      if (data.usage) {
        setUsage(data.usage)
      }
    } catch {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Error connecting to backend.",
      }])
    } finally {
      setLoading(false)
    }
  }

  const uploadFile = async (file: File) => {
    setIsUploading(true)
    setMessages(prev => [...prev, { role: "user", content: `[Uploading: ${file.name}]` }])
    const formData = new FormData()
    formData.append("file", file)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const token = await getToken()
      const res = await fetch(`${apiUrl}/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Upload failed")
      setMessages(prev => [...prev, {
        role: "assistant",
        content: data.message || `Successfully processed ${file.name}`,
      }])
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error"
      setMessages(prev => [...prev, { role: "assistant", content: `Upload error: ${message}` }])
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) await uploadFile(file)
  }

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true) }
  const handleDragLeave = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(false) }
  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) await uploadFile(file)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <div className={styles.layout}>
      {/* Sidebar */}
      <aside className={`${styles.sidebar} ${sidebarOpen ? styles.sidebarOpen : ""}`}>
        <div className={styles.sidebarHeader}>
          <Sparkles className={styles.logoIcon} size={28} />
          <span className={styles.sidebarTitle}>InsightBot</span>
        </div>

        <button
          className={styles.newChatBtn}
          onClick={() => {
            setMessages([])
            if (window.innerWidth <= 768) setSidebarOpen(false)
          }}
        >
          <Plus size={18} />
          New Chat
        </button>

        <div className={styles.historyList}>
          <div className={`${styles.historyItem} ${styles.historyItemActive}`}>
            <MessageSquare size={16} />
            Current Session
          </div>
        </div>

        {/* Query usage counter */}
        {usage && !usage.is_owner && (
          <div style={{
            margin: "1rem 0",
            padding: "0.75rem",
            borderRadius: 8,
            background: isLimitReached
              ? "rgba(239,68,68,0.1)"
              : "rgba(59,130,246,0.1)",
            border: `1px solid ${isLimitReached ? "rgba(239,68,68,0.3)" : "rgba(59,130,246,0.3)"}`,
            fontSize: "0.8rem",
          }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              {isLimitReached ? "⚠️ Limit Reached" : "Free Queries"}
            </div>
            <div style={{ opacity: 0.8 }}>
              {usage.queries_used} / 5 used
            </div>
            {/* Progress bar */}
            <div style={{
              marginTop: 6, height: 4, borderRadius: 2,
              background: "rgba(150,150,150,0.2)",
            }}>
              <div style={{
                height: "100%",
                borderRadius: 2,
                width: `${Math.min(100, ((usage.queries_used ?? 0) / 5) * 100)}%`,
                background: isLimitReached ? "#ef4444" : "var(--primary)",
                transition: "width 0.3s ease",
              }} />
            </div>
            {isLimitReached && (
              <div style={{ marginTop: 6, opacity: 0.7, fontSize: "0.75rem" }}>
                Contact the owner for more access.
              </div>
            )}
          </div>
        )}

        {usage?.is_owner && (
          <div style={{
            margin: "1rem 0", padding: "0.5rem 0.75rem",
            borderRadius: 8, background: "rgba(139,92,246,0.1)",
            border: "1px solid rgba(139,92,246,0.3)",
            fontSize: "0.8rem", color: "var(--accent)",
          }}>
            ✦ Owner — unlimited queries
          </div>
        )}

        {/* Logout button */}
        <button
          onClick={logout}
          style={{
            marginTop: "auto",
            display: "flex", alignItems: "center", gap: 8,
            width: "100%", padding: "0.75rem 1rem",
            background: "transparent",
            border: "1px solid var(--panel-border)",
            borderRadius: 8, color: "var(--foreground)",
            fontSize: "0.875rem", cursor: "pointer", opacity: 0.7,
          }}
        >
          <LogOut size={16} />
          Sign Out
        </button>
      </aside>

      {/* Main Content */}
      <main
        className={styles.main}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {isDragging && (
          <div className={styles.dragOverlay}>
            <div style={{ marginBottom: "1rem" }}><Sparkles size={48} /></div>
            Drop your PDF, image, or text file here
          </div>
        )}

        <header className={styles.header}>
          <button className={styles.menuToggle} onClick={() => setSidebarOpen(!sidebarOpen)}>
            <Menu size={24} />
          </button>
          <span className={styles.headerTitle}>Multimodal RAG Agent</span>
          <span style={{
            marginLeft: "auto", fontSize: "0.8rem",
            opacity: 0.5, display: "flex", alignItems: "center",
          }}>
            {user.email}
          </span>
        </header>

        <div className={styles.chatContainer}>
          {messages.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIconWrapper}><Sparkles size={40} /></div>
              <h1 className={styles.emptyTitle}>How can I help you today?</h1>
              <p className={styles.emptySubtitle}>
                Ask me anything. I can leverage advanced RAG to answer your questions accurately.
              </p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className={`${styles.messageWrapper} ${styles[msg.role]}`}>
                <div className={styles.message}>
                  <div className={styles.messageRole}>
                    {msg.role === "assistant"
                      ? <Bot className={styles.botIcon} />
                      : <User className={styles.userIcon} />}
                    {msg.role}
                  </div>
                  <div className={styles.messageContent}>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        img: ({ node, ...props }) => {
                          let src = props.src
                          if (typeof src === "string" && src.startsWith("/temp_uploads")) {
                            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
                            src = `${apiUrl}${src}`
                          }
                          return <img {...props} src={src} className={styles.chatImage} alt={props.alt || "Chat Image"} />
                        },
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            ))
          )}

          {loading && (
            <div className={`${styles.messageWrapper} ${styles.assistant}`}>
              <div className={styles.message}>
                <div className={styles.messageRole}><Bot className={styles.botIcon} />assistant</div>
                <div className={styles.thinking}>
                  <div className={styles.dot} /><div className={styles.dot} /><div className={styles.dot} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Limit reached banner */}
        {isLimitReached && (
          <div style={{
            margin: "0 2rem 0.5rem",
            padding: "0.75rem 1rem",
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 8, fontSize: "0.875rem", color: "#ef4444",
            textAlign: "center",
          }}>
            You have used all 5 free queries. Contact the owner for more access.
          </div>
        )}

        <div className={styles.inputArea}>
          <div className={styles.inputContainer}>
            <input
              type="file" ref={fileInputRef}
              style={{ display: "none" }}
              onChange={handleFileChange}
              accept="image/*,.pdf,.txt"
            />
            <button
              className={styles.attachButton}
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading || loading}
              title="Attach file"
            >
              {isUploading ? <Loader2 size={20} className={styles.spinner} /> : <Paperclip size={20} />}
            </button>
            <input
              className={styles.inputField}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isLimitReached ? "Query limit reached" : "Ask me anything..."}
              disabled={loading || isUploading || isLimitReached}
            />
            <button
              onClick={send}
              className={styles.sendButton}
              disabled={!query.trim() || loading || isUploading || isLimitReached}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}