// src/App.jsx
import React, { useState } from 'react';
import FileUploader from './components/FileUploader';
import Chatbot from './components/Chatbot';
import DocumentSummary from './components/DocumentSummary';
import './App.css';

function App() {
  const [currentPage, setCurrentPage] = useState('upload'); // 'upload' or 'chat'
  const [uploadedDocuments, setUploadedDocuments] = useState([]);

  const handleUploadSuccess = (uploadResponse) => {
    console.log('📤 Upload response received:', uploadResponse);
    
    // Handle multiple documents
    if (uploadResponse.documentIds && uploadResponse.filenames) {
      // Multiple documents uploaded
      const newDocuments = uploadResponse.documentIds.map((docId, index) => ({
        name: uploadResponse.filenames[index] || `Document ${index + 1}`,
        id: docId,
        uploadTime: new Date().toISOString()
      }));
      
      console.log('📋 Setting multiple documents:', newDocuments);
      setUploadedDocuments(prev => {
        // Add new documents, avoiding duplicates
        const existingIds = new Set(prev.map(doc => doc.id));
        const uniqueNewDocs = newDocuments.filter(doc => !existingIds.has(doc.id));
        return [...prev, ...uniqueNewDocs];
      });
    } else {
      // Single document uploaded (backward compatibility)
      const documentInfo = {
        name: uploadResponse.filename || 'Document',
        id: uploadResponse.documentId || 'unknown',
        uploadTime: new Date().toISOString()
      };
      
      console.log('📋 Setting single document info:', documentInfo);
      
      // Add to existing documents or create new array
      setUploadedDocuments(prev => {
        // Check if document already exists
        const exists = prev.find(doc => doc.id === documentInfo.id);
        if (exists) {
          return prev; // Don't add duplicate
        }
        return [...prev, documentInfo];
      });
    }
    
    // Navigate to chat page
    setCurrentPage('chat');
  };

  const handleBackToUpload = () => {
    // Reset state and go back to upload page
    setUploadedDocuments([]);
    setCurrentPage('upload');
  };

  // Extract document IDs and names for the summary component
  const documentIds = uploadedDocuments.map(doc => doc.id);
  const documentNames = uploadedDocuments.map(doc => doc.name);

  return (
    <div className="App">
      {currentPage === 'upload' ? (
        <div className="upload-page">
          <FileUploader onUploadSuccess={handleUploadSuccess} />
        </div>
      ) : (
        <div className="chat-layout">
          <div className="chat-section">
            <Chatbot 
              documentNames={documentNames}
              documentIds={documentIds}
              onBackToUpload={handleBackToUpload}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default App;