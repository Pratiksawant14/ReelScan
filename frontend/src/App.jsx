import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import { Send, Loader2, Video, MessageSquare } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Adjust this URL if your FastAPI runs on a different host/port
const API_BASE_URL = 'http://localhost:8000/api'

function App() {
  const [url, setUrl] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [reelData, setReelData] = useState(null)

  // Chat state
  const [messages, setMessages] = useState([])
  const [currentMessage, setCurrentMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)

  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  const handleAnalyze = async (e) => {
    e.preventDefault()
    if (!url) return

    setIsAnalyzing(true)
    setReelData(null)
    setMessages([])

    try {
      const response = await axios.post(`${API_BASE_URL}/analyze`, { url })
      setReelData(response.data)
      setMessages([{
        role: 'assistant',
        content: "I've analyzed the reel! Ask me anything about its visual content, audio, or text."
      }])
    } catch (error) {
      console.error(error)
      alert('Error analyzing reel. Please check the backend or try another URL.')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleSendMessage = async (e) => {
    e.preventDefault()
    if (!currentMessage.trim() || !reelData) return

    const userMsg = currentMessage
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setCurrentMessage('')
    setIsTyping(true)

    // Add a temporary empty assistant message
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reel_id: reelData.reel_id,
          message: userMsg
        })
      })

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`)
      }

      if (!response.body) throw new Error('No response body')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        // Append chunk to the last assistant message immutably
        setMessages(prev => {
          const newMessages = [...prev]
          const lastIndex = newMessages.length - 1
          newMessages[lastIndex] = {
            ...newMessages[lastIndex],
            content: newMessages[lastIndex].content + chunk
          }
          return newMessages
        })
      }
    } catch (error) {
      console.error(error)
      setMessages(prev => {
        const newMessages = [...prev]
        newMessages[newMessages.length - 1].content = "Sorry, I encountered an error while typing."
        return newMessages
      })
    } finally {
      setIsTyping(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-slate-100 flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-900/50 py-4 px-6 md:px-12 flex items-center gap-3 shrink-0">
        <Video className="w-8 h-8 text-indigo-500" />
        <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
          ReelInsights
        </h1>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 flex flex-col gap-6">

        {/* Input Section */}
        {!reelData && (
          <div className="flex-1 flex flex-col items-center justify-center max-w-2xl mx-auto w-full">
            <div className="text-center mb-10 space-y-4">
              <h2 className="text-4xl md:text-5xl font-extrabold tracking-tight">
                Analyze Any <span className="text-indigo-500">Instagram Reel</span>
              </h2>
              <p className="text-zinc-400 text-lg">
                Paste a URL below to download the video, extract insights using AI, and ask questions about it in real-time.
              </p>
            </div>

            <form onSubmit={handleAnalyze} className="w-full relative flex items-center shadow-2xl rounded-2xl overflow-hidden ring-1 ring-zinc-800 focus-within:ring-indigo-500 transition-shadow">
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://www.instagram.com/reel/..."
                className="w-full bg-zinc-900 py-5 pl-6 pr-24 outline-none text-lg"
                disabled={isAnalyzing}
                required
              />
              <button
                type="submit"
                disabled={isAnalyzing || !url}
                className="absolute right-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-500 rounded-xl font-medium transition-colors flex items-center gap-2"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Analyzing
                  </>
                ) : (
                  'Analyze'
                )}
              </button>
            </form>

            {isAnalyzing && (
              <div className="mt-12 text-zinc-400 flex flex-col items-center gap-4">
                <div className="w-16 h-16 border-4 border-zinc-800 border-t-indigo-500 rounded-full animate-spin"></div>
                <p className="animate-pulse">Downloading, vectorizing, and analyzing via Gemini Flash...</p>
              </div>
            )}
          </div>
        )}

        {/* Dashboard Section */}
        {reelData && (
          <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-8 h-full min-h-[600px] pb-10">

            {/* Left: Video & Analysis Summary */}
            <div className="flex flex-col gap-6 h-full">
              <div className="bg-zinc-900 rounded-3xl overflow-hidden ring-1 ring-zinc-800 aspect-[9/16] max-h-[60vh] mx-auto flex shrink-0 shadow-xl">
                {/* Video Player pointing to Supabase Storage URL */}
                <video
                  src={reelData.storage_url}
                  controls
                  className="w-full h-full object-contain bg-black"
                  autoPlay
                  loop
                />
              </div>

              {/* Collapsible raw analysis text or short summary could go here */}
              <div className="bg-zinc-900/50 rounded-2xl p-6 ring-1 ring-zinc-800/50 overflow-y-auto max-h-48 text-sm text-zinc-300">
                <h3 className="font-semibold text-zinc-100 mb-2 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-indigo-400" />
                  Initial AI summary
                </h3>
                <div className="prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {reelData.analysis}
                  </ReactMarkdown>
                </div>
              </div>
            </div>

            {/* Right: RAG Chat */}
            <div className="bg-zinc-900 rounded-3xl ring-1 ring-zinc-800 flex flex-col h-full lg:max-h-[80vh] shadow-xl overflow-hidden">
              <div className="p-5 border-b border-zinc-800 bg-zinc-900/80 backdrop-blur-md">
                <h3 className="font-semibold text-lg">Ask about this Reel</h3>
                <p className="text-zinc-400 text-sm">Powered by Gemini 2.5 Flash + Supabase Vector</p>
              </div>

              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto p-5 space-y-6">
                {messages.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className={`max-w-[85%] rounded-2xl px-5 py-3 ${msg.role === 'user'
                        ? 'bg-indigo-600 text-white rounded-br-sm'
                        : 'bg-zinc-800 text-slate-200 rounded-bl-sm border border-zinc-700/50'
                        }`}
                    >
                      {msg.content ? (
                        <div className={`prose ${msg.role === 'user' ? 'prose-invert prose-p:text-white' : 'prose-invert'} max-w-none leading-relaxed text-sm`}>
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <div className="flex gap-1 py-1">
                          <div className="w-2 h-2 rounded-full bg-zinc-500 animate-bounce"></div>
                          <div className="w-2 h-2 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-2 h-2 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              {/* Chat Input */}
              <div className="p-4 bg-zinc-900 border-t border-zinc-800">
                <form onSubmit={handleSendMessage} className="relative flex items-center">
                  <input
                    type="text"
                    value={currentMessage}
                    onChange={(e) => setCurrentMessage(e.target.value)}
                    placeholder="E.g., What is the person wearing?"
                    disabled={isTyping}
                    className="w-full bg-zinc-950 ring-1 ring-zinc-800 focus:ring-indigo-500 rounded-xl py-4 pl-5 pr-14 outline-none transition-shadow disabled:opacity-50"
                  />
                  <button
                    type="submit"
                    disabled={isTyping || !currentMessage.trim()}
                    className="absolute right-2 p-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:bg-zinc-800 rounded-lg transition-colors"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </form>
              </div>
            </div>

          </div>
        )}
      </main>
    </div>
  )
}

export default App
