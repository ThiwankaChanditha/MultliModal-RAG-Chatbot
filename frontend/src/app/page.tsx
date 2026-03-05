"use client"

import { useState, useRef, useEffect } from "react"
import styles from "./page.module.css"
import { Sparkles, Send, Menu, MessageSquare, Bot, User, Plus, Paperclip, Loader2 } from "lucide-react"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

type Message = {
  role: "user" | "assistant"
  content: string
}

export default function Home() {
  const [query, setQuery] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isDragging, setIsDragging] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  const send = async () => {
    if (!query.trim()) return

    const userMessage: Message = { role: "user", content: query }
    setMessages(prev => [...prev, userMessage])
    setQuery("")
    setLoading(true)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const res = await fetch(`${apiUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMessage.content })
      })

      if (!res.ok) {
        throw new Error("Server error")
      }

      const data = await res.json()
      setMessages(prev => [...prev, { role: "assistant", content: data.answer }])
    } catch (err) {
      setMessages(prev => [...prev, { role: "assistant", content: "Error connecting to backend." }])
    }

    setLoading(false)
  }

  const uploadFile = async (file: File) => {
    setIsUploading(true)
    setMessages(prev => [...prev, { role: "user", content: `[Attempting to upload: ${file.name}]` }])
    const formData = new FormData()
    formData.append("file", file)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const res = await fetch(`${apiUrl}/upload`, { method: "POST", body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Upload failed")
      setMessages(prev => [...prev, { role: "assistant", content: data.message || `Successfully processed ${file.name}` }])
    } catch (err: any) {
      setMessages(prev => [...prev, { role: "assistant", content: `Upload error: ${err.message}` }])
    }
    setIsUploading(false)
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) await uploadFile(file)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) {
      await uploadFile(file)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      send()
    }
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
            setMessages([]);
            if (window.innerWidth <= 768) setSidebarOpen(false);
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
      </aside>

      {/* Main Content */}
      <main className={styles.main} onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}>
        {isDragging && (
          <div className={styles.dragOverlay}>
            <div style={{ marginBottom: "1rem" }}>
              <Sparkles size={48} />
            </div>
            Drop your PDF, image, or text file here
          </div>
        )}
        <header className={styles.header}>
          <button
            className={styles.menuToggle}
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            <Menu size={24} />
          </button>
          <span className={styles.headerTitle}>Multimodal RAG Agent</span>
        </header>

        <div className={styles.chatContainer}>
          {messages.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIconWrapper}>
                <Sparkles size={40} />
              </div>
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
                    {msg.role === "assistant" ? <Bot className={styles.botIcon} /> : <User className={styles.userIcon} />}
                    {msg.role}
                  </div>
                  <div className={styles.messageContent}>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        img: ({ node, ...props }) => {
                          let src = props.src;
                          if (typeof src === "string" && src.startsWith("/temp_uploads")) {
                            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                            src = `${apiUrl}${src}`;
                          }
                          return <img {...props} src={src} className={styles.chatImage} alt={props.alt || "Chat Image"} />
                        }
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
                <div className={styles.messageRole}>
                  <Bot className={styles.botIcon} />
                  assistant
                </div>
                <div className={styles.thinking}>
                  <div className={styles.dot}></div>
                  <div className={styles.dot}></div>
                  <div className={styles.dot}></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className={styles.inputArea}>
          <div className={styles.inputContainer}>
            <input
              type="file"
              ref={fileInputRef}
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
              placeholder="Ask me anything..."
              disabled={loading || isUploading}
            />
            <button
              onClick={send}
              className={styles.sendButton}
              disabled={!query.trim() || loading || isUploading}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}