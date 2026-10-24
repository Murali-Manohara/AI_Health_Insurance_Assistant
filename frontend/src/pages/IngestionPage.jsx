import React, { useEffect, useState } from 'react';
import { uploadAndIngest, fetchHistory } from '../services/ingestionApi';
import { PlanSelector } from '../components/PlanSelector';
import { FileUpload } from '../components/FileUpload';
import { IngestionProgress } from '../components/IngestionProgress';
import { IngestionSummary } from '../components/IngestionSummary';
import { IngestionHistory } from '../components/IngestionHistory';
import { ChatInterface } from '../components/ChatInterface';
import { ErrorDisplay } from '../components/ErrorDisplay';

export function IngestionPage() {
  const [selectedCategory, setSelectedCategory] = useState('customer'); // 'customer' or 'employee'
  const [selectedFile, setSelectedFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentJob, setCurrentJob] = useState(null);
  const [history, setHistory] = useState([]);
  const [errors, setErrors] = useState([]);
  const [warnings, setWarnings] = useState([]);
  const [activeTab, setActiveTab] = useState('ingestion'); // 'ingestion' or 'chat'

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const historyList = await fetchHistory();
      setHistory(historyList);
    } catch (err) {
      // Backend may be initializing
    }
  };

  const handleStartIngestion = async () => {
    if (!selectedFile) {
      setErrors(['Please select a PDF document to upload.']);
      return;
    }

    setErrors([]);
    setWarnings([]);
    setIsProcessing(true);
    setCurrentJob(null);

    try {
      const jobResult = await uploadAndIngest(selectedFile, selectedCategory);
      setCurrentJob(jobResult);
      if (jobResult.warnings && jobResult.warnings.length > 0) {
        setWarnings(jobResult.warnings);
      }
      const updatedHistory = await fetchHistory();
      setHistory(updatedHistory);
    } catch (err) {
      setErrors(err.errors || [err.message || 'Document processing failed.']);
      if (err.warnings) setWarnings(err.warnings);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setCurrentJob(null);
    setErrors([]);
    setWarnings([]);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div>
          <h1 className="brand-title">Insurance Policy Assistant</h1>
          <p className="brand-subtitle">Policy Document Ingestion & Retrieval</p>
        </div>

        <nav className="tabs">
          <button
            className={`tab-btn ${activeTab === 'ingestion' ? 'active' : ''}`}
            onClick={() => setActiveTab('ingestion')}
          >
            Document Ingestion
          </button>
          <button
            className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            Policy Search
          </button>
        </nav>
      </header>

      <main>
        <ErrorDisplay
          errors={errors}
          warnings={warnings}
          onDismiss={() => {
            setErrors([]);
            setWarnings([]);
          }}
        />

        {activeTab === 'ingestion' ? (
          <div>
            {!currentJob ? (
              <div className="card">
                <h2 className="card-title">Upload Policy Document</h2>

                <PlanSelector
                  selectedCategory={selectedCategory}
                  onSelectCategory={setSelectedCategory}
                  disabled={isProcessing}
                />

                <FileUpload
                  onFileSelected={setSelectedFile}
                  selectedFile={selectedFile}
                  disabled={isProcessing}
                />

                {isProcessing && (
                  <IngestionProgress
                    currentStage="Extracting sections and generating embeddings..."
                    status="PENDING"
                  />
                )}

                <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end' }}>
                  <button
                    id="start-ingestion-btn"
                    className="btn btn-primary"
                    disabled={!selectedFile || isProcessing}
                    onClick={handleStartIngestion}
                  >
                    {isProcessing ? 'Processing Document...' : 'Process Document'}
                  </button>
                </div>
              </div>
            ) : (
              <IngestionSummary job={currentJob} onReset={handleReset} />
            )}

            <IngestionHistory history={history} onRefresh={loadHistory} />
          </div>
        ) : (
          <ChatInterface />
        )}
      </main>
    </div>
  );
}

export default IngestionPage;
