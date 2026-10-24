import React, { useRef, useState } from 'react';

export function FileUpload({ onFileSelected, selectedFile, disabled = false }) {
  const fileInputRef = useRef(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [fileError, setFileError] = useState(null);

  const validateAndSelect = (file) => {
    setFileError(null);
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setFileError('Please select a valid PDF file (.pdf).');
      return;
    }
    if (file.size > 25 * 1024 * 1024) {
      setFileError('File exceeds the 25 MB size limit.');
      return;
    }
    onFileSelected(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSelect(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSelect(e.target.files[0]);
    }
  };

  return (
    <div className="form-group">
      <label className="form-label">Policy Document</label>
      <div
        className={`file-drop-area ${isDragOver ? 'active' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleChange}
          accept="application/pdf"
          style={{ display: 'none' }}
          disabled={disabled}
        />

        {selectedFile ? (
          <div>
            <div className="selected-file-name">{selectedFile.name}</div>
            <div className="file-drop-hint">
              {(selectedFile.size / 1024).toFixed(1)} KB — Click to change file
            </div>
          </div>
        ) : (
          <div>
            <div className="file-drop-text">Click or drag a PDF file here to upload</div>
            <div className="file-drop-hint">PDF format only, up to 25 MB</div>
          </div>
        )}
      </div>

      {fileError && <div className="alert alert-error" style={{ marginTop: '10px' }}>{fileError}</div>}
    </div>
  );
}
