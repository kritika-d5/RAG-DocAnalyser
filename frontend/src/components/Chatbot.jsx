// src/components/Chatbot.jsx
import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import jsPDF from 'jspdf';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  ArrowLeft, FileDown, FileText, Files, Send, Copy, Check, ChevronDown,
  MessageSquare, LoaderCircle, Quote,
} from 'lucide-react';
import DocumentSummary from './DocumentSummary';
import { API_BASE, SAMPLE_DOCUMENT } from '../api';
import './Chatbot.css';

const GENERIC_SUGGESTIONS = [
  'What is this document about?',
  'What are the key findings?',
  'List the important dates and figures',
  'What conclusions does it reach?',
];

// Strip emojis and markdown syntax so jsPDF (Latin-1 font) renders clean text
const stripForPdf = (text) => {
  if (!text) return '';
  return text
    .replace(/#{1,6}\s*/g, '')           // ## headings
    .replace(/\*\*(.+?)\*\*/g, '$1')     // **bold**
    .replace(/\*(.+?)\*/g, '$1')         // *italic*
    .replace(/^[-*+]\s+/gm, '  - ')      // bullet markers
    .replace(/[\u2018\u2019]/g, "'")     // smart quotes -> ASCII
    .replace(/[\u201C\u201D]/g, '"')
    .replace(/[\u2010-\u2015]/g, '-')    // hyphens / dashes
    .replace(/[\u00A0\u202F]/g, ' ')     // no-break spaces
    .replace(/\u2022/g, '-')             // bullets
    .replace(/\u2026/g, '...')           // ellipsis
    .replace(/[^\n\t -~]/g, '')          // drop remaining non-ASCII (emojis)
    .replace(/\n{3,}/g, '\n\n')          // collapse excess newlines
    .trim();
};

// Writes a titled PDF: a header block followed by [heading, body] sections
const writePdfReport = (title, documentNames, sections, fileName) => {
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 20;
  const textWidth = pageWidth - 2 * margin;
  let y = 20;

  const ensureSpace = () => {
    if (y > 270) {
      doc.addPage();
      y = 20;
    }
  };

  doc.setFontSize(18);
  doc.setFont(undefined, 'bold');
  doc.text(title, pageWidth / 2, y, { align: 'center' });
  y += 12;

  doc.setFontSize(10);
  doc.setFont(undefined, 'normal');
  doc.splitTextToSize(stripForPdf(`Documents: ${documentNames.join(', ')}`), textWidth).forEach((line) => {
    doc.text(line, margin, y);
    y += 5;
  });
  doc.text(`Generated: ${new Date().toLocaleString()}`, margin, y);
  y += 12;

  sections.forEach(([heading, body]) => {
    ensureSpace();
    doc.setFontSize(11);
    doc.setFont(undefined, 'bold');
    doc.text(stripForPdf(heading), margin, y);
    y += 6;
    doc.setFont(undefined, 'normal');
    doc.splitTextToSize(stripForPdf(body), textWidth).forEach((line) => {
      ensureSpace();
      doc.text(line, margin, y);
      y += 5;
    });
    y += 8;
  });

  doc.save(fileName);
};

const CopyButton = ({ text }) => {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  };

  return (
    <button type="button" className="message-action" onClick={copy} aria-label="Copy answer">
      {copied ? <Check size={14} /> : <Copy size={14} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
};

// Grounding citations: collapsed to a count, expandable to each passage.
const Sources = ({ sources }) => {
  const [open, setOpen] = useState(false);
  const items = (Array.isArray(sources) ? sources : [sources]).filter(Boolean);
  if (items.length === 0) return null;

  return (
    <>
      <button
        type="button"
        className={`message-action ${open ? 'is-open' : ''}`}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <Quote size={14} />
        {items.length} source{items.length !== 1 ? 's' : ''}
        <ChevronDown size={14} className="chevron" />
      </button>

      {open && (
        <ul className="sources-list">
          {items.map((s, i) => {
            if (typeof s === 'string') {
              return <li key={i} className="source-item"><span className="source-file">{s}</span></li>;
            }
            return (
              <li key={i} className="source-item">
                <details>
                  <summary>
                    <span className="source-file">
                      <FileText size={13} aria-hidden="true" />
                      {s.filename}
                    </span>
                    {typeof s.similarity === 'number' && (
                      <span className="source-match">{Math.round(s.similarity * 100)}% match</span>
                    )}
                    <span className="source-preview">{s.preview}</span>
                  </summary>
                  <blockquote className="source-passage">{s.text || s.preview}</blockquote>
                </details>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
};

const Chatbot = ({ documentNames, documentIds, onBackToUpload }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [documentSummaries, setDocumentSummaries] = useState([]);
  const chatboxRef = useRef(null);
  const inputRef = useRef(null);

  const isSample = documentNames?.includes(SAMPLE_DOCUMENT.filename);
  const suggestions = isSample ? SAMPLE_DOCUMENT.questions : GENERIC_SUGGESTIONS;

  // Auto-scroll to bottom when new messages arrive (not on the empty state,
  // where it would scroll the welcome content out of view on mount)
  useEffect(() => {
    if (messages.length > 0 && chatboxRef.current) {
      chatboxRef.current.scrollTop = chatboxRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendMessage = async (messageText = null) => {
    const userMessage = (messageText || input).trim();
    if (userMessage === '' || isLoading) return;

    setMessages((prev) => [...prev, { sender: 'user', text: userMessage, timestamp: new Date() }]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE}/api/query`, {
        message: userMessage,
        document_ids: documentIds || [],
      }, {
        timeout: 180000,
      });

      setMessages((prev) => [...prev, {
        sender: 'bot',
        text: response.data.answer || response.data.reply || "I couldn't generate an answer. Please try rephrasing your question.",
        sources: response.data.sources,
        timestamp: new Date(),
      }]);
    } catch (error) {
      console.error('Error sending message:', error);
      let errorMessage = 'Something went wrong while answering. Please try again.';
      if (error.code === 'ECONNABORTED') {
        errorMessage = 'That took too long to answer. Please try again.';
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
      } else if (!error.response) {
        errorMessage = "Couldn't reach the server. Check your connection and try again.";
      }
      setMessages((prev) => [...prev, { sender: 'bot', text: errorMessage, isError: true, timestamp: new Date() }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage();
  };

  const downloadChatReport = () => {
    try {
      writePdfReport(
        'Chat Conversation Report',
        documentNames,
        messages.map((msg) => [
          `${msg.sender === 'user' ? 'You' : 'Assistant'} (${msg.timestamp.toLocaleString()})`,
          msg.text,
        ]),
        `chat-report-${new Date().toISOString().split('T')[0]}.pdf`,
      );
    } catch (error) {
      console.error('Error generating PDF:', error);
      alert('Failed to generate the PDF. Please try again.');
    }
  };

  const downloadSummaryReport = () => {
    try {
      writePdfReport(
        'Document Summary Report',
        documentNames,
        documentSummaries.map((s) => [s.name, s.summary]),
        `summary-report-${new Date().toISOString().split('T')[0]}.pdf`,
      );
    } catch (error) {
      console.error('Error generating summary PDF:', error);
      alert('Failed to generate the PDF. Please try again.');
    }
  };

  const formatTime = (timestamp) =>
    timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="chatbot-page">
      <header className="chat-header">
        <div className="header-left">
          <button type="button" className="btn btn-ghost btn-sm" onClick={onBackToUpload}>
            <ArrowLeft size={16} />
            New document
          </button>
          <h1 className="chat-title">Document Intelligence Hub</h1>
        </div>

        <div className="header-right">
          {documentNames?.length > 0 && (
            <div className="document-chip" title={documentNames.join(', ')}>
              {documentNames.length === 1 ? <FileText size={15} /> : <Files size={15} />}
              <span>
                {documentNames.length === 1 ? documentNames[0] : `${documentNames.length} documents`}
              </span>
            </div>
          )}
          {documentSummaries.length > 0 && (
            <button type="button" className="btn btn-secondary btn-sm" onClick={downloadSummaryReport} aria-label="Download summary as PDF" title="Download summary as PDF">
              <FileDown size={15} />
              <span className="btn-label">Summary PDF</span>
            </button>
          )}
          {messages.length > 0 && (
            <button type="button" className="btn btn-secondary btn-sm" onClick={downloadChatReport} aria-label="Download chat as PDF" title="Download chat as PDF">
              <FileDown size={15} />
              <span className="btn-label">Chat PDF</span>
            </button>
          )}
        </div>
      </header>

      <div className="chatbot-main-container">
        <section className="chatbot-container glass" aria-label="Chat">
          <div className="chatbox" ref={chatboxRef} aria-live="polite">
            {messages.length === 0 ? (
              <div className="empty-chat-state">
                <div className="empty-icon" aria-hidden="true">
                  <MessageSquare size={24} strokeWidth={1.8} />
                </div>
                <h2 className="empty-title">Ask anything about {documentNames?.length > 1 ? 'your documents' : 'your document'}</h2>
                <p className="empty-description">
                  Answers are based only on the document, and each one shows the passages it came from.
                </p>
                <div className="suggestions-container">
                  {suggestions.map((suggestion) => (
                    <button
                      type="button"
                      key={suggestion}
                      className="suggestion-chip"
                      onClick={() => sendMessage(suggestion)}
                      disabled={isLoading}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg, idx) => (
                  <div key={idx} className={`message ${msg.sender} ${msg.isError ? 'is-error' : ''}`}>
                    <div className="message-content">
                      {msg.sender === 'bot' ? (
                        <div className="markdown-body">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                        </div>
                      ) : (
                        msg.text
                      )}
                    </div>
                    {msg.sender === 'bot' && !msg.isError ? (
                      <div className="message-footer">
                        <CopyButton text={msg.text} />
                        {msg.sources?.length > 0 && <Sources sources={msg.sources} />}
                        <span className="message-time">{formatTime(msg.timestamp)}</span>
                      </div>
                    ) : (
                      <div className="message-time">{formatTime(msg.timestamp)}</div>
                    )}
                  </div>
                ))}

                {isLoading && (
                  <div className="typing-message">
                    <div className="typing-indicator" aria-hidden="true">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                    <span>Reading the document…</span>
                  </div>
                )}
              </>
            )}
          </div>

          <form className="input-area" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              type="text"
              placeholder="Ask a question about your document…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
              maxLength={500}
              aria-label="Your question"
            />
            <button
              type="submit"
              className="btn btn-primary send-button"
              disabled={isLoading || input.trim() === ''}
              aria-label="Send"
            >
              {isLoading ? <LoaderCircle size={18} className="spin" /> : <Send size={18} />}
            </button>
          </form>
        </section>

        <aside className="document-summary-panel glass" aria-label="Summary">
          <DocumentSummary
            documentIds={documentIds}
            documentNames={documentNames}
            onSummariesUpdate={setDocumentSummaries}
          />
        </aside>
      </div>
    </div>
  );
};

export default Chatbot;
