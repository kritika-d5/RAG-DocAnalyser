import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ScrollText, FileText, GitCompare, ChevronDown, RefreshCw, TriangleAlert } from 'lucide-react';
import { API_BASE } from '../api';
import './DocumentSummary.css';

const SUMMARY_REQUEST = 'Provide a comprehensive summary of this document with detailed analysis, key points, and insights';
const COMPARISON_REQUEST = 'Create a comprehensive summary comparing all uploaded documents. Analyze similarities, differences, and provide insights across all documents.';

// Older answers may use "•" characters instead of markdown bullets
const normalizeMarkdown = (text) =>
  (text || '').replace(/^\s*•\s*/gm, '- ').replace(/\n{3,}/g, '\n\n').trim();

const fetchSummary = async (message, documentIds, signal) => {
  const response = await axios.post(`${API_BASE}/api/query`, {
    message,
    document_ids: documentIds,
  }, { timeout: 180000, signal });
  return response.data.answer || 'Summary not available.';
};

const SummarySkeleton = () => (
  <div className="summary-skeleton" aria-hidden="true">
    <div className="skeleton-line w-40" />
    <div className="skeleton-line" />
    <div className="skeleton-line" />
    <div className="skeleton-line w-80" />
    <div className="skeleton-line w-30 gap" />
    <div className="skeleton-line w-90" />
    <div className="skeleton-line w-70" />
  </div>
);

const DocumentSummary = ({ documentIds, documentNames, onSummariesUpdate }) => {
  const [summaries, setSummaries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(new Set());

  const loadSummaries = useCallback(async (signal) => {
    if (!documentIds?.length) return;
    setLoading(true);

    const summarizeOne = async (docId, index) => {
      const base = { id: docId, name: documentNames[index] || `Document ${index + 1}`, type: 'individual' };
      try {
        return { ...base, summary: await fetchSummary(SUMMARY_REQUEST, [docId], signal) };
      } catch (error) {
        if (axios.isCancel(error)) throw error;
        console.error(`Failed to load summary for document ${docId}:`, error);
        return { ...base, summary: '', error: true };
      }
    };

    try {
      const results = await Promise.all(documentIds.map(summarizeOne));

      // With several documents, add a cross-document comparison on top
      if (documentIds.length > 1) {
        try {
          results.unshift({
            id: 'comparison',
            name: `Comparison of ${documentIds.length} documents`,
            type: 'comparison',
            summary: await fetchSummary(COMPARISON_REQUEST, documentIds, signal),
          });
        } catch (error) {
          if (axios.isCancel(error)) throw error;
          console.error('Failed to load comparison summary:', error);
        }
      }

      setSummaries(results);
      setExpanded(new Set([results[0].id]));
    } catch (error) {
      if (!axios.isCancel(error)) console.error('Failed to load summaries:', error);
      return;
    }
    setLoading(false);
  }, [documentIds, documentNames]);

  useEffect(() => {
    const controller = new AbortController();
    loadSummaries(controller.signal);
    return () => controller.abort();
  }, [loadSummaries]);

  useEffect(() => {
    if (summaries.length > 0) {
      onSummariesUpdate?.(summaries.filter((s) => !s.error));
    }
  }, [summaries, onSummariesUpdate]);

  const toggle = (id) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const count = documentIds?.length || 0;

  return (
    <div className="document-summary-container">
      <div className="summary-header">
        <h2>
          <ScrollText size={18} aria-hidden="true" />
          Summary
        </h2>
        <span className="summary-count">
          {count} document{count !== 1 ? 's' : ''}
        </span>
      </div>

      {loading ? (
        <div className="summary-loading" role="status">
          <p>Reading the {count > 1 ? 'documents' : 'document'} and writing a summary…</p>
          <SummarySkeleton />
        </div>
      ) : (
        <div className="summaries-list">
          {summaries.map((summary) => {
            const isOpen = expanded.has(summary.id);
            const Icon = summary.type === 'comparison' ? GitCompare : FileText;
            return (
              <div key={summary.id} className={`summary-item ${isOpen ? 'expanded' : ''}`}>
                <button
                  type="button"
                  className="summary-toggle"
                  onClick={() => toggle(summary.id)}
                  aria-expanded={isOpen}
                >
                  <span className="summary-icon" aria-hidden="true"><Icon size={16} /></span>
                  <span className="document-name" title={summary.name}>{summary.name}</span>
                  {summary.error && <TriangleAlert size={15} className="error-indicator" aria-label="Failed" />}
                  <ChevronDown size={16} className="expand-icon" aria-hidden="true" />
                </button>

                {isOpen && (
                  <div className="summary-content">
                    {summary.error ? (
                      <div className="summary-error">
                        <p>This summary couldn't be generated.</p>
                        <button type="button" className="btn btn-secondary btn-sm" onClick={() => loadSummaries()}>
                          <RefreshCw size={14} />
                          Try again
                        </button>
                      </div>
                    ) : (
                      <div className="markdown-body">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {normalizeMarkdown(summary.summary)}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default DocumentSummary;
