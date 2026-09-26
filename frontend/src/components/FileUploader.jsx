// src/components/FileUploader.jsx
import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import {
  CloudUpload, FileText, X, Info, Sparkles, ArrowRight, LoaderCircle,
  Check, TriangleAlert, Trash2,
} from 'lucide-react';
import { API_BASE, SAMPLE_DOCUMENT } from '../api';
import './FileUploader.css';

const MAX_TOTAL_SIZE = 10 * 1024 * 1024; // 10MB total
const VALID_EXTENSIONS = ['.pdf', '.docx', '.txt'];

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const validateFiles = (files) => {
  const totalSize = files.reduce((sum, file) => sum + file.size, 0);
  if (totalSize > MAX_TOTAL_SIZE) {
    return 'Those files add up to more than 10 MB. Remove some and try again.';
  }
  for (const file of files) {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!VALID_EXTENSIONS.includes(ext)) {
      return `"${file.name}" isn't supported. Use PDF, DOCX or TXT files.`;
    }
  }
  return null;
};

// Pings the backend on load. The free Render instance sleeps when idle, so the
// first request can take up to a minute; this starts waking it straight away
// and lets the UI explain the wait instead of looking frozen.
const useServerStatus = () => {
  const [status, setStatus] = useState('checking'); // checking | waking | ready | offline

  useEffect(() => {
    let cancelled = false;
    const slowTimer = setTimeout(() => {
      if (!cancelled) setStatus((s) => (s === 'checking' ? 'waking' : s));
    }, 2500);

    axios.get(`${API_BASE}/api/health`, { timeout: 90000 })
      .then(() => { if (!cancelled) setStatus('ready'); })
      .catch(() => { if (!cancelled) setStatus('offline'); })
      .finally(() => clearTimeout(slowTimer));

    return () => {
      cancelled = true;
      clearTimeout(slowTimer);
    };
  }, []);

  return status;
};

const SERVER_STATUS_TEXT = {
  checking: 'Connecting to server…',
  waking: 'Waking up the server — this can take up to a minute on free hosting',
  ready: 'Server ready',
  offline: "Can't reach the server right now",
};

const UPLOAD_STEPS = [
  { key: 'uploading', label: 'Uploading' },
  { key: 'indexing', label: 'Reading & indexing' },
  { key: 'done', label: 'Ready' },
];

const FileUploader = ({ onUploadSuccess }) => {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [error, setError] = useState('');
  const [stage, setStage] = useState(null); // null | uploading | indexing | done
  const [uploadPct, setUploadPct] = useState(0);
  const [slowIndexing, setSlowIndexing] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);
  const serverStatus = useServerStatus();

  const isBusy = stage !== null;

  // After a while in the indexing step, reassure the user it's still working
  useEffect(() => {
    if (stage !== 'indexing') {
      setSlowIndexing(false);
      return;
    }
    const t = setTimeout(() => setSlowIndexing(true), 12000);
    return () => clearTimeout(t);
  }, [stage]);

  const addFiles = (newFiles) => {
    if (!newFiles || newFiles.length === 0) return;
    const allFiles = [...selectedFiles, ...newFiles];
    const problem = validateFiles(allFiles);
    if (problem) {
      setError(problem);
      return;
    }
    setSelectedFiles(allFiles);
    setError('');
  };

  const openFilePicker = () => {
    if (!isBusy) fileInputRef.current?.click();
  };

  const handleFileChange = (e) => {
    addFiles(Array.from(e.target.files));
    // Allow re-selecting the same file after removing it
    e.target.value = '';
  };

  const handleZoneKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      openFilePicker();
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!isBusy) setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    // Ignore drag-leave events fired when moving over child elements
    if (!e.currentTarget.contains(e.relatedTarget)) setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (!isBusy) addFiles(Array.from(e.dataTransfer.files));
  };

  const uploadFiles = async (files) => {
    setError('');
    setStage('uploading');
    setUploadPct(0);

    const formData = new FormData();
    files.forEach((file, index) => formData.append(`file${index}`, file));

    try {
      const response = await axios.post(`${API_BASE}/api/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 180000,
        onUploadProgress: (e) => {
          if (!e.total) return;
          const pct = Math.round((e.loaded * 100) / e.total);
          setUploadPct(pct);
          // Bytes are all sent: the server is now extracting and embedding
          if (pct >= 100) setStage('indexing');
        },
      });

      setStage('done');
      setTimeout(() => onUploadSuccess?.(response.data), 700);
    } catch (err) {
      console.error('Upload failed:', err);
      let message = 'Upload failed. Please try again.';
      if (err.code === 'ECONNABORTED') {
        message = 'The upload took too long. Check your connection and try again.';
      } else if (err.response?.data?.details?.[0]?.error) {
        message = err.response.data.details[0].error;
      } else if (err.response?.data?.error) {
        message = err.response.data.error;
      } else if (!err.response) {
        message = "Couldn't reach the server. It may still be waking up — try again in a moment.";
      }
      setError(message);
      setStage(null);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (selectedFiles.length > 0) uploadFiles(selectedFiles);
  };

  const trySampleDocument = async () => {
    try {
      const res = await fetch(SAMPLE_DOCUMENT.url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const file = new File([blob], SAMPLE_DOCUMENT.filename, { type: 'text/plain' });
      setSelectedFiles([file]);
      uploadFiles([file]);
    } catch (err) {
      console.error('Could not load sample document:', err);
      setError("Couldn't load the sample document. Please try again.");
    }
  };

  const removeFile = (index) => {
    setSelectedFiles((files) => files.filter((_, i) => i !== index));
    setError('');
  };

  const totalSize = selectedFiles.reduce((sum, f) => sum + f.size, 0);
  const currentStepIndex = UPLOAD_STEPS.findIndex((s) => s.key === stage);

  return (
    <div className="file-uploader-container">
      <main className="main-container">
        <div className={`server-status ${serverStatus}`} role="status">
          {serverStatus === 'ready' ? (
            <span className="status-dot" aria-hidden="true" />
          ) : serverStatus === 'offline' ? (
            <TriangleAlert size={14} aria-hidden="true" />
          ) : (
            <LoaderCircle size={14} className="spin" aria-hidden="true" />
          )}
          {SERVER_STATUS_TEXT[serverStatus]}
        </div>

        <header className="page-header">
          <h1 className="main-title">Document Intelligence Hub</h1>
          <p className="subtitle">
            Ask questions about your PDFs, Word and text files — every answer comes with its sources.
          </p>
        </header>

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt"
          onChange={handleFileChange}
          disabled={isBusy}
          className="visually-hidden"
          tabIndex={-1}
          aria-hidden="true"
        />

        <section className="upload-section">
          <div
            className={`drag-drop-zone glass ${isDragOver ? 'drag-over' : ''} ${isBusy ? 'is-busy' : ''}`}
            role="button"
            tabIndex={isBusy ? -1 : 0}
            aria-label="Choose files to upload"
            aria-disabled={isBusy}
            onClick={openFilePicker}
            onKeyDown={handleZoneKeyDown}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="upload-icon" aria-hidden="true">
              <CloudUpload size={26} strokeWidth={1.8} />
            </div>
            <h2 className="upload-title">
              {isDragOver ? 'Drop to add your files' : 'Drag and drop your documents'}
            </h2>
            <p className="upload-description">or click anywhere in this box</p>
            <span className="btn btn-secondary browse-button" aria-hidden="true">
              <FileText size={17} />
              {selectedFiles.length > 0 ? 'Add more files' : 'Browse files'}
            </span>
            <p className="supported-formats">
              <Info size={14} aria-hidden="true" />
              PDF, DOCX or TXT · up to 10 MB in total
            </p>
          </div>

          {selectedFiles.length === 0 && !isBusy && (
            <div className="sample-cta">
              <div className="divider"><span>or</span></div>
              <button type="button" className="btn btn-secondary" onClick={trySampleDocument}>
                <Sparkles size={17} />
                Try a sample document
              </button>
              <p className="sample-hint">A short fictional annual report, with suggested questions.</p>
            </div>
          )}

          {selectedFiles.length > 0 && (
            <form className="selected-files glass" onSubmit={handleSubmit}>
              <div className="files-header">
                <span>Selected files ({selectedFiles.length})</span>
                <span className="total-size">{formatFileSize(totalSize)} total</span>
              </div>

              <ul className="file-list">
                {selectedFiles.map((file, idx) => (
                  <li key={`${file.name}-${idx}`} className="selected-file">
                    <span className="file-icon" aria-hidden="true"><FileText size={18} /></span>
                    <span className="file-info">
                      <span className="file-name" title={file.name}>{file.name}</span>
                      <span className="file-size">{formatFileSize(file.size)}</span>
                    </span>
                    <button
                      type="button"
                      className="icon-btn"
                      onClick={() => removeFile(idx)}
                      disabled={isBusy}
                      aria-label={`Remove ${file.name}`}
                      title="Remove file"
                    >
                      <X size={16} />
                    </button>
                  </li>
                ))}
              </ul>

              {isBusy ? (
                <div className="upload-progress" aria-live="polite">
                  <ol className="progress-steps">
                    {UPLOAD_STEPS.map((step, i) => {
                      const state = i < currentStepIndex ? 'complete' : i === currentStepIndex ? 'active' : 'pending';
                      return (
                        <li key={step.key} className={`progress-step ${state}`}>
                          <span className="step-marker" aria-hidden="true">
                            {state === 'complete' || (state === 'active' && step.key === 'done') ? (
                              <Check size={13} strokeWidth={3} />
                            ) : state === 'active' ? (
                              <LoaderCircle size={13} className="spin" />
                            ) : (
                              i + 1
                            )}
                          </span>
                          <span className="step-label">
                            {step.label}
                            {step.key === 'uploading' && state === 'active' && ` ${uploadPct}%`}
                          </span>
                        </li>
                      );
                    })}
                  </ol>
                  <div className="progress-bar" aria-hidden="true">
                    <div
                      className={`progress-fill ${stage === 'indexing' ? 'indeterminate' : ''}`}
                      style={{ width: stage === 'uploading' ? `${Math.max(uploadPct, 4) * 0.4}%` : stage === 'done' ? '100%' : undefined }}
                    />
                  </div>
                  {(serverStatus === 'waking' || serverStatus === 'checking') && stage !== 'done' && (
                    <p className="progress-note">The server is waking up from sleep, so this first upload can take up to a minute.</p>
                  )}
                  {slowIndexing && serverStatus === 'ready' && (
                    <p className="progress-note">Still working — longer documents take a little more time to index.</p>
                  )}
                </div>
              ) : (
                <div className="upload-actions">
                  <button type="button" className="btn btn-ghost" onClick={() => { setSelectedFiles([]); setError(''); }}>
                    <Trash2 size={16} />
                    Clear all
                  </button>
                  <button type="submit" className="btn btn-primary upload-button">
                    Upload & start chatting
                    <ArrowRight size={17} />
                  </button>
                </div>
              )}
            </form>
          )}

          {error && (
            <div className="upload-error" role="alert">
              <TriangleAlert size={18} aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default FileUploader;
