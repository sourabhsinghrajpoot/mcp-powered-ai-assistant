'use client';

import { FormEvent, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';

const API = process.env.NEXT_PUBLIC_API_URL || '';
type Message = { role: 'user' | 'assistant'; content: string };
type ConversationSummary = { id: number; title: string };

async function readResponse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `Request failed (${response.status})`);
  }
  return data as T;
}

export default function Home() {
  const [token, setToken] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [tools, setTools] = useState<{ name: string; description: string }[]>([]);

  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    if (savedToken) setToken(savedToken);
  }, []);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    async function restoreLatestConversation() {
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const conversations = await readResponse<ConversationSummary[]>(
          await fetch(`${API}/api/conversations`, { headers }),
        );
        if (cancelled || conversations.length === 0) return;
        const latest = await readResponse<{ id: number; messages: Message[] }>(
          await fetch(`${API}/api/conversations/${conversations[0].id}`, { headers }),
        );
        if (!cancelled) {
          setConversationId(latest.id);
          setMessages(latest.messages);
        }
      } catch (cause) {
        if (!cancelled) setError(cause instanceof Error ? cause.message : 'Could not load conversation history.');
      }
    }
    void restoreLatestConversation();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    if (token) headers.set('Authorization', `Bearer ${token}`);
    return readResponse<T>(await fetch(`${API}${path}`, { ...init, headers }));
  }

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    try {
      const body = new URLSearchParams({ username: email, password });
      const response = await fetch(`${API}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      });
      const data = await readResponse<{ access_token: string }>(response);
      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Sign in failed.');
    }
  }

  async function startConversation() {
    setError('');
    try {
      const created = await apiRequest<{ id: number }>('/api/conversations', { method: 'POST' });
      setConversationId(created.id);
      setMessages([]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not start a conversation.');
    }
  }

  async function sendMessage() {
    const message = input.trim();
    if (!message || busy) return;

    setInput('');
    setMessages((current) => [...current, { role: 'user', content: message }]);
    setBusy(true);
    setError('');
    try {
      let id = conversationId;
      if (!id) {
        const created = await apiRequest<{ id: number }>('/api/conversations', { method: 'POST' });
        id = created.id;
        setConversationId(id);
      }
      const result = await apiRequest<{ answer: string }>('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: id, message }),
      });
      setMessages((current) => [...current, { role: 'assistant', content: result.answer }]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not send your message.');
    } finally {
      setBusy(false);
    }
  }

  async function discoverTools() {
    setError('');
    try {
      const result = await apiRequest<{ tools: { name: string; description: string }[] }>('/api/mcp/tools');
      setTools(result.tools);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not connect to MCP tools.');
    }
  }

  if (!token) {
    return (
      <main className="login">
        <form onSubmit={login}>
          <div className="mark">✳</div>
          <h1>Welcome back</h1>
          <p>Sign in to your assistant workspace.</p>
          <label>Email<input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Password<input type="password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          <button>Sign in</button>
          <small>New here? Create an account with POST /api/auth/register (OAuth form fields: username, password).</small>
          {error && <p className="error">{error}</p>}
        </form>
      </main>
    );
  }

  return (
    <div className="shell">
      <aside>
        <div className="brand"><span>✳</span> Orbit <small>AI WORKSPACE</small></div>
        <button className="new" onClick={() => void startConversation()}>＋　New conversation</button>
        <nav>
          <span className="active">◉　Chat</span>
          <a href="#docs">▤　Documents</a>
          <a href="#tools" onClick={() => void discoverTools()}>⌘　Tools</a>
          <a href="#settings">⚙　Settings</a>
        </nav>
        <div className="sidebottom">
          <span className="dot" /> API connected
          <button onClick={() => {
            localStorage.removeItem('token');
            setToken('');
            setConversationId(null);
            setMessages([]);
            setError('');
          }}>Log out</button>
        </div>
      </aside>
      <main className="main">
        <header>
          <div><b>Assistant</b><span className="sub">Ask questions or use connected tools</span></div>
          <span className="pill">●　Ready</span>
        </header>
        <section className="conversation">
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="mark">✳</div>
              <h1>How can I help?</h1>
              <p>Ask a question, explore a document, or connect a tool.</p>
              <div className="suggestions">
                <button onClick={() => setInput('What can you help me with?')}>✧　What can you help me with?</button>
                <button onClick={() => location.hash = 'tools'}>⌘　Explore MCP tools</button>
              </div>
            </div>
          ) : messages.map((message, index) => (
            <article key={index} className={`message ${message.role}`}>
              <div className="avatar">{message.role === 'user' ? 'S' : '✳'}</div>
              <div className="bubble">
                <b>{message.role === 'user' ? 'You' : 'Assistant'}</b>
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            </article>
          ))}
          {busy && <div className="typing">✳　Waiting for your AI provider…</div>}
          {error && <div className="error" role="alert">{error}</div>}
          {tools.length > 0 && (
            <div className="toolbox">
              <b>Connected MCP tools</b>
              {tools.map((tool) => <div key={tool.name}><code>{tool.name}</code> — {tool.description}</div>)}
            </div>
          )}
        </section>
        <form className="composer" onSubmit={(event) => { event.preventDefault(); void sendMessage(); }}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Message your assistant…"
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                void sendMessage();
              }
            }}
          />
          <div><span>Enter to send · Shift + Enter for new line</span><button disabled={busy || !input.trim()}>↑</button></div>
        </form>
        <footer>AI can make mistakes. Review important information.</footer>
      </main>
    </div>
  );
}
