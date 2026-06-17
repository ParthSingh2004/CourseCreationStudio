import { useState, useRef } from 'react';
import {
  IconUserPlus, IconShield, IconZap, IconUpload, IconCheck
} from '../icons';

const API_BASE = import.meta.env.VITE_API_BASE || 
  (window.location.origin.includes('5173') ? 'http://localhost:8000/api/v1' : `${window.location.origin}/api/v1`);

const blueprints = [
  {
    id: 'onboarding',
    icon: <IconUserPlus size={24} />,
    label: 'Onboarding',
    desc: 'New hire journey & culture',
  },
  {
    id: 'compliance',
    icon: <IconShield size={24} />,
    label: 'Compliance',
    desc: 'Legal standards & safety',
  },
  {
    id: 'skill-crash',
    icon: <IconZap size={24} />,
    label: 'Skill-Crash',
    desc: 'High-intensity technical training',
  },
];

const learningTimes = ['Quick Bite (5-10 mins)', 'Standard (15-20 mins)', 'Deep Dive (30+ mins)'];
const proficiencyLevels = ['Beginner', 'Intermediate', 'Advanced', 'Expert'];
const tones = ['Professional & Authoritative', 'Friendly & Conversational', 'Academic & Formal'];

const deliverables = [
  { id: 'text', label: 'Text Lessons', defaultChecked: true },
  { id: 'quizzes', label: 'Quizzes', defaultChecked: true },
  { id: 'flashcards', label: 'Flashcards', defaultChecked: false },
  { id: 'audio', label: 'Audio', defaultChecked: false },
];

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function FileIcon({ ext }) {
  const isPdf = ext === '.pdf';
  return (
    <svg width="28" height="34" viewBox="0 0 28 34" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="28" height="34" rx="4" fill={isPdf ? '#FEE2E2' : '#DBEAFE'} />
      <text x="14" y="22" textAnchor="middle" fontSize="9" fontWeight="700"
        fill={isPdf ? '#DC2626' : '#2563EB'} fontFamily="system-ui">
        {isPdf ? 'PDF' : 'DOC'}
      </text>
    </svg>
  );
}

export default function CourseDesignPage({ onGenerate }) {
  const [selected, setSelected] = useState('onboarding');
  const [learningTime, setLearningTime] = useState('Deep Dive (30+ mins)');
  const [proficiency, setProficiency] = useState('Intermediate');
  const [tone, setTone] = useState('Professional & Authoritative');
  const [checkedDeliverables, setCheckedDeliverables] = useState(
    Object.fromEntries(deliverables.map(d => [d.id, d.defaultChecked]))
  );

  // Upload state
  const [uploadedFiles, setUploadedFiles] = useState([]);   // { storedName, originalName, sizeBytes, extension, status }
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [enhancing, setEnhancing] = useState(false);
  const fileInputRef = useRef(null);
  const [prompt, setPrompt] = useState('');
  const [voice, setVoice] = useState('en-US-JennyNeural');
  const [audience, setAudience] = useState('');

  const toggleDeliverable = (id) => {
    setCheckedDeliverables(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleUploadClick = () => {
    setUploadError('');
    fileInputRef.current?.click();
  };

  const handleFilesSelected = async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    // Reset input so the same file can be re-selected
    e.target.value = '';

    // Client-side validation
    const invalid = files.filter(f => {
      const ext = f.name.split('.').pop().toLowerCase();
      return !['pdf', 'docx'].includes(ext);
    });
    if (invalid.length) {
      setUploadError(`Unsupported file type(s): ${invalid.map(f => f.name).join(', ')}. Only PDF and DOCX are allowed.`);
      return;
    }

    setUploading(true);
    setUploadError('');

    try {
      const formData = new FormData();
      formData.append('file', files[0]); // Backend takes a single file named 'file'

      const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Server error ${res.status}`);
      }

      const data = await res.json();
      if (data.file_id) {
        setUploadedFiles([{
          storedName: data.file_id,
          originalName: data.filename,
          sizeBytes: files[0].size,
          extension: files[0].name.split('.').pop(),
        }]);
      }
    } catch (err) {
      setUploadError(err.message || 'Upload failed. Is the server running?');
    } finally {
      setUploading(false);
    }
  };

  const handleRemoveFile = async (storedName) => {
    try {
      await fetch(`${API_BASE}/uploads/${encodeURIComponent(storedName)}`, {
        method: 'DELETE',
      });
    } catch {
      // Best effort — remove from UI regardless
    }
    setUploadedFiles(prev => prev.filter(f => f.storedName !== storedName));
  };

  const handleEnhanceClick = async () => {
    if (!prompt.trim()) {
      alert("Please enter a short topic first!");
      return;
    }
    
    setEnhancing(true);
    try {
      const res = await fetch(`${API_BASE}/enhance-prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt })
      });
      const data = await res.json();
      if (data.enhanced_prompt) {
        setPrompt(data.enhanced_prompt);
      } else {
        alert("Enhancement failed, no prompt returned.");
      }
    } catch (err) {
      alert("Failed to enhance prompt: " + err.message);
    } finally {
      setEnhancing(false);
    }
  };

  const handleGenerateClick = async () => {
    if (!prompt.trim()) {
      alert("Please enter a course topic/prompt first.");
      return;
    }
    
    const selectedContentTypes = Object.keys(checkedDeliverables).filter(k => checkedDeliverables[k]);
    if (selectedContentTypes.length === 0) {
      alert("Please select at least one deliverable content type.");
      return;
    }

    const fileId = uploadedFiles.length > 0 ? uploadedFiles[0].storedName : null;
    const req = {
      prompt: prompt || '',
      audience: audience || '',
      voice: voice,
      blueprint: selected,
      duration: learningTime,
      level: proficiency,
      tone: tone,
      content_types: selectedContentTypes,
      file_id: fileId
    };

    try {
      const res = await fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req)
      });
      const data = await res.json();
      if (!res.ok) {
        alert(`Failed to start generation: ${data.detail || 'Unknown error'}`);
        return;
      }
      if (data.job_id) {
        onGenerate(data.job_id);
      }
    } catch (err) {
      alert("Failed to start generation: " + err.message);
    }
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <h1>Create New Course</h1>
        <p>Define your curriculum parameters and let CourseEngine AI handle the structural heavy lifting.</p>
      </div>

      <div className="design-grid">
        {/* Left column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Section 1: Blueprint */}
          <div className="card">
            <div className="card-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              1. Course Objective / Blueprint Type
            </div>
            <div className="blueprint-grid">
              {blueprints.map(bp => (
                <div
                  key={bp.id}
                  className={`blueprint-card${selected === bp.id ? ' selected' : ''}`}
                  onClick={() => setSelected(bp.id)}
                >
                  {bp.icon}
                  <h4>{bp.label}</h4>
                  <p>{bp.desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Section 2: Core Context */}
          <div className="card">
            <div className="card-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="17" y1="10" x2="3" y2="10"/><line x1="21" y1="6" x2="3" y2="6"/><line x1="21" y1="14" x2="3" y2="14"/><line x1="13" y1="18" x2="3" y2="18"/></svg>
              2. Core Context
            </div>

            <div className="form-group">
              <label className="form-label">Who is this course for?</label>
              <input 
                className="form-input" 
                placeholder="e.g., Onboarding Frontend Engineers" 
                value={audience}
                onChange={e => setAudience(e.target.value)}
              />
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <div className="upload-row">
                <label className="form-label" style={{ margin: 0 }}>What are the core topics or source documentation?</label>

                {/* Hidden file input */}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx"
                  multiple
                  style={{ display: 'none' }}
                  onChange={handleFilesSelected}
                />

                <button
                  className={`upload-btn${uploading ? ' uploading' : ''}`}
                  onClick={handleUploadClick}
                  disabled={uploading}
                  id="upload-files-btn"
                >
                  {uploading ? (
                    <>
                      <span className="upload-spinner" />
                      Uploading…
                    </>
                  ) : (
                    <>
                      <IconUpload size={12} /> UPLOAD FILES/DOCS
                    </>
                  )}
                </button>
              </div>

              {/* Error message */}
              {uploadError && (
                <div className="upload-error">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                  {uploadError}
                </div>
              )}

              {/* Uploaded files list */}
              {uploadedFiles.length > 0 && (
                <div className="uploaded-files-list">
                  {uploadedFiles.map(file => (
                    <div key={file.storedName} className="uploaded-file-item">
                      <FileIcon ext={file.extension} />
                      <div className="uploaded-file-info">
                        <span className="uploaded-file-name" title={file.originalName}>{file.originalName}</span>
                        <span className="uploaded-file-meta">{formatBytes(file.sizeBytes)}</span>
                      </div>
                      <div className="uploaded-file-badge">
                        <IconCheck size={10} />
                        Uploaded
                      </div>
                      <button
                        className="uploaded-file-remove"
                        onClick={() => handleRemoveFile(file.storedName)}
                        title="Remove file"
                        aria-label={`Remove ${file.originalName}`}
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <textarea
                className="form-textarea"
                style={{ marginTop: uploadedFiles.length > 0 ? 8 : 8 }}
                placeholder="List the specific workflows, tools, or skills this course must cover or paste relevant documentation content..."
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
              />
              <div style={{display: 'flex', justifyContent: 'flex-end', marginTop: 10}}>
                <button 
                  type="button" 
                  onClick={handleEnhanceClick} 
                  disabled={enhancing} 
                  style={{
                    background: '#f8fafc', 
                    border: '1px solid #e2e8f0', 
                    padding: '6px 12px', 
                    borderRadius: 4, 
                    cursor: enhancing ? 'wait' : 'pointer', 
                    fontSize: 13, 
                    color: 'var(--brand)', 
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6
                  }}
                >
                  <IconZap size={14} />
                  {enhancing ? 'Enhancing...' : 'Enhance with AI'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right column */}
        <div className="side-column">
          {/* Section 3: Parameters */}
          <div className="card">
            <div className="card-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg>
              3. Parameters
            </div>

            <div className="param-group">
              <div className="card-subtitle">Target Learning Time</div>
              <select className="form-select" value={learningTime} onChange={e => setLearningTime(e.target.value)}>
                {learningTimes.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>

            <div className="param-group">
              <div className="card-subtitle">Target Proficiency Level</div>
              <select className="form-select" value={proficiency} onChange={e => setProficiency(e.target.value)}>
                {proficiencyLevels.map(l => <option key={l}>{l}</option>)}
              </select>
            </div>

            <div className="param-group">
              <div className="card-subtitle">Instructional Tone</div>
              <select className="form-select" value={tone} onChange={e => setTone(e.target.value)}>
                {tones.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>

            <div className="param-group" style={{ marginBottom: 0 }}>
              <div className="card-subtitle">TTS Voice</div>
              <select className="form-select" value={voice} onChange={e => setVoice(e.target.value)}>
                <option value="en-US-JennyNeural">US Female (Jenny)</option>
                <option value="en-US-GuyNeural">US Male (Guy)</option>
                <option value="en-GB-SoniaNeural">UK Female (Sonia)</option>
                <option value="en-GB-RyanNeural">UK Male (Ryan)</option>
              </select>
            </div>
          </div>

          {/* Section 4: Deliverables */}
          <div className="card">
            <div className="card-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
              4. Deliverables
            </div>
            {deliverables.map(d => (
              <div key={d.id} className="checkbox-item" onClick={() => toggleDeliverable(d.id)}>
                <div className={`checkbox-custom${checkedDeliverables[d.id] ? ' checked' : ''}`}>
                  {checkedDeliverables[d.id] && <IconCheck size={10} />}
                </div>
                <label>{d.label}</label>
              </div>
            ))}
          </div>

          {/* Generate CTA */}
          <div>
            <button className="generate-btn" onClick={handleGenerateClick}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
              </svg>
              Generate Course
            </button>
            <p className="generate-note">
              AI generation may take up to 60 seconds<br />depending on content scope.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
