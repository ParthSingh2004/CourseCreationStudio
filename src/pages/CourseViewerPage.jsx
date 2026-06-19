import { useState, useEffect } from 'react';
import {
  IconPlay, IconChevronDown, IconDownload, IconArrowLeft, IconArrowRight
} from '../icons';

const API_BASE = import.meta.env.VITE_API_BASE || 
  (window.location.origin.includes('5173') ? 'http://localhost:8000/api/v1' : `${window.location.origin}/api/v1`);

export default function CourseViewerPage({ jobId, onBack }) {
  const [courseData, setCourseData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Navigation state
  const [activeModuleIndex, setActiveModuleIndex] = useState(null);
  const [activeLessonIndex, setActiveLessonIndex] = useState(null);
  const [openModules, setOpenModules] = useState({});
  const [activeTab, setActiveTab] = useState('lesson'); // 'lesson' | 'quiz'
  
  const [activeSegmentIndex, setActiveSegmentIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);

  const [leftTab, setLeftTab] = useState('slides');
  const [activeFlashcardIndex, setActiveFlashcardIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    if (!jobId) {
      setLoading(false);
      return;
    }
    
    fetch(`${API_BASE}/course/${jobId}`)
      .then(res => res.json())
      .then(data => {
        setCourseData(data);
        if (data.outline && data.outline.modules.length > 0) {
          const firstMod = data.outline.modules[0];
          setOpenModules({ [firstMod.index]: true });
          setActiveModuleIndex(firstMod.index);
          
          if (data.content && data.content.lessons) {
             const firstLesson = data.content.lessons.find(l => l.module_index === firstMod.index);
             if (firstLesson) setActiveLessonIndex(firstLesson.lesson_index);
          }
        }
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [jobId]);
  
  useEffect(() => {
    setActiveSegmentIndex(0);
  }, [activeLessonIndex, activeModuleIndex]);

  useEffect(() => {
    setImageFailed(false);
  }, [activeSegmentIndex, activeLessonIndex, activeModuleIndex]);

  useEffect(() => {
    setLeftTab('slides');
    setActiveFlashcardIndex(0);
    setIsFlipped(false);
  }, [activeModuleIndex]);

  useEffect(() => {
    setIsFlipped(false);
  }, [activeFlashcardIndex]);
  
  useEffect(() => {
    setSelectedAnswers({});
    setQuizSubmitted(false);
  }, [activeModuleIndex, activeTab]);

  if (loading) return <div style={{padding: 40}}>Loading course data...</div>;
  if (!courseData) return <div style={{padding: 40}}>Course data not found. Please start a new generation.</div>;

  const outline = courseData.outline;
  const content = courseData.content || { lessons: [], quizzes: [], flashcards: [] };
  
  const currentModule = outline.modules.find(m => m.index === activeModuleIndex);
  const currentLesson = content.lessons.find(l => l.module_index === activeModuleIndex && l.lesson_index === activeLessonIndex);
  const currentQuiz = content.quizzes?.find(q => q.module_index === activeModuleIndex);
  const currentFlashcards = content.flashcards?.find(f => f.module_index === activeModuleIndex);
  
  const segments = currentLesson?.segments || [];
  const currentSegment = segments[activeSegmentIndex] || segments[0] || { slide_title: '', slide_bullets: [], narration: '' };
  const hasAudio = Array.isArray(courseData.audio) && courseData.audio.length > 0;
  const hasNarration = !!currentSegment.narration;
  
  const score = currentQuiz ? currentQuiz.questions.reduce((acc, q, idx) => {
    return acc + (selectedAnswers[idx] === q.correct_index ? 1 : 0);
  }, 0) : 0;

  const toggleModule = (idx) => {
    setOpenModules(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handleLessonClick = (modIndex, lessIndex) => {
    setActiveModuleIndex(modIndex);
    setActiveLessonIndex(lessIndex);
    setActiveTab('lesson');
  };

  const downloadFile = (url) => {
    window.open(url, '_blank');
  };

  return (
    <div className="viewer-layout">
      {/* Sidebar */}
      <aside className="sidebar" style={{ width: 260 }}>
        <div style={{ padding: '12px 14px 6px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '.06em', textTransform: 'uppercase', marginBottom: 2 }}>Course</div>
          <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.4 }}>{outline.title}</div>
        </div>
        <div className="sidebar-divider" />

        {outline.modules.map(mod => {
          const modLessons = content.lessons.filter(l => l.module_index === mod.index);
          return (
            <div key={mod.index} className="sidebar-module-group">
              <div
                className={`sidebar-module-header${openModules[mod.index] ? ' open' : ''}`}
                onClick={() => toggleModule(mod.index)}
              >
                <span className="label" style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Module {mod.index}: {mod.title}</span>
                <span className="chevron"><IconChevronDown size={12} /></span>
              </div>
              
              {openModules[mod.index] && (
                <>
                  {modLessons.map(lesson => {
                    const isCurrent = lesson.module_index === activeModuleIndex && lesson.lesson_index === activeLessonIndex && activeTab === 'lesson';
                    return (
                      <div
                        key={lesson.lesson_index}
                        className={`sidebar-lesson-item${isCurrent ? ' current' : ''}`}
                        onClick={() => handleLessonClick(lesson.module_index, lesson.lesson_index)}
                        style={{ cursor: 'pointer' }}
                      >
                        <span className="sidebar-lesson-icon">
                          {isCurrent ? (
                            <IconPlay size={11} fill="var(--brand)" color="var(--brand)" />
                          ) : (
                            <IconPlay size={11} />
                          )}
                        </span>
                        <span style={{ fontSize: 12 }}>Lesson {lesson.lesson_index}: {lesson.title}</span>
                      </div>
                    )
                  })}
                  
                  {/* Link to Quiz if exists */}
                  {content.quizzes.some(q => q.module_index === mod.index) && (
                    <div
                      className={`sidebar-lesson-item${activeTab === 'quiz' && activeModuleIndex === mod.index ? ' current' : ''}`}
                      onClick={() => { setActiveModuleIndex(mod.index); setActiveTab('quiz'); }}
                      style={{ cursor: 'pointer', paddingLeft: 30 }}
                    >
                      <span style={{ fontSize: 12, color: 'var(--brand)' }}>Take Module Quiz</span>
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}

        <div className="sidebar-divider" />
        <div className="sidebar-bottom" style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: 14 }}>
          <div className="sidebar-item" style={{ fontSize: 12, color: 'var(--brand)', fontWeight: 600, cursor: 'pointer' }} onClick={() => downloadFile(`${API_BASE}/export/${jobId}/slides`)}>
            <IconDownload size={14} /> Download PPTX Slides
          </div>
          <div className="sidebar-item" style={{ fontSize: 12, color: 'var(--brand)', fontWeight: 600, cursor: 'pointer' }} onClick={() => downloadFile(`${API_BASE}/export/${jobId}/quiz-pdf`)}>
            <IconDownload size={14} /> Download Quiz PDF
          </div>
          <div className="sidebar-item" style={{ fontSize: 12, color: 'var(--brand)', fontWeight: 600, cursor: 'pointer' }} onClick={() => downloadFile(`${API_BASE}/export/${jobId}/summary-pdf`)}>
            <IconDownload size={14} /> Download Summary PDF
          </div>
          <div className="sidebar-divider" style={{ margin: '10px 0' }}/>
          <button onClick={onBack} style={{ background: 'transparent', border: '1px solid #e2e8f0', padding: '8px', borderRadius: '4px', cursor: 'pointer', fontSize: 12, width: '100%' }}>
            Start New Course
          </button>
        </div>
      </aside>

      {/* Main viewer */}
      <div className="viewer-main" style={{ padding: 40, overflowY: 'auto' }}>
        <div className="breadcrumb" style={{ marginBottom: 20 }}>
          <div className="module-label">Module {currentModule?.index}</div>
          <div className="lesson-title">{currentLesson ? currentLesson.title : 'Module Resources'}</div>
        </div>

        {activeTab === 'lesson' && currentLesson && (
          <div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24, marginBottom: 24 }}>
              {/* Slide Deck Area */}
              <div className="slide-deck-container" style={{ width: '100%', aspectRatio: '16/9', maxHeight: '75vh', background: '#FFEDD5', borderRadius: 12, padding: 40, color: '#0F1728', display: 'flex', flexDirection: 'column', position: 'relative', border: '1px solid #FED7AA', boxShadow: '0 10px 30px rgba(249,115,22,0.1)', overflow: 'hidden' }}>
                {currentFlashcards && currentFlashcards.cards?.length > 0 && (
                  <div style={{ display: 'flex', gap: 10, marginBottom: 20, zIndex: 20, position: 'relative' }}>
                    <button 
                      onClick={() => setLeftTab('slides')}
                      style={{ background: leftTab === 'slides' ? '#F97316' : 'transparent', color: leftTab === 'slides' ? '#fff' : '#5C6B85', border: '1px solid #F97316', padding: '6px 12px', borderRadius: 20, cursor: 'pointer', fontSize: 13, fontWeight: 600 }}
                    >
                      Slides
                    </button>
                    <button 
                      onClick={() => setLeftTab('flashcards')}
                      style={{ background: leftTab === 'flashcards' ? '#F97316' : 'transparent', color: leftTab === 'flashcards' ? '#fff' : '#5C6B85', border: '1px solid #F97316', padding: '6px 12px', borderRadius: 20, cursor: 'pointer', fontSize: 13, fontWeight: 600 }}
                    >
                      Flashcards
                    </button>
                  </div>
                )}

                {leftTab === 'slides' ? (
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>

                    {/* ── TEXT slide ──────────────────────────────────────── */}
                    {(!currentSegment.slide_type || currentSegment.slide_type === 'text' || (currentSegment.slide_type === 'photo' && (!currentSegment.image_query || imageFailed))) && (
                      <>
                        <h2 style={{color: '#0F1728', fontSize: '2.4rem', fontWeight: 800}}>{currentSegment.slide_title || currentLesson.title}</h2>
                        <ul style={{ paddingLeft: 24, marginTop: 30, fontSize: '1.25rem', lineHeight: 1.8 }}>
                          {currentSegment.slide_bullets?.map((b, i) => <li key={i} style={{marginBottom: 16}}>{b}</li>)}
                        </ul>
                      </>
                    )}

                    {/* ── PHOTO slide ─────────────────────────────────────── */}
                    {currentSegment.slide_type === 'photo' && currentSegment.image_query && !imageFailed && (
                      <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start', height: '100%' }}>
                        {/* Left: title + bullets */}
                        <div style={{ flex: '0 0 52%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                          <h2 style={{ color: '#0F1728', fontSize: '2rem', fontWeight: 800, marginBottom: 20 }}>
                            {currentSegment.slide_title || currentLesson.title}
                          </h2>
                          <ul style={{ paddingLeft: 20, fontSize: '1.1rem', lineHeight: 1.8 }}>
                            {currentSegment.slide_bullets?.map((b, i) => (
                              <li key={i} style={{ marginBottom: 12 }}>{b}</li>
                            ))}
                          </ul>
                        </div>
                        {/* Right: Unsplash image via proxy */}
                        <div style={{ flex: '0 0 45%', display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', borderRadius: 10, overflow: 'hidden', background: 'rgba(255,255,255,0.25)', minHeight: 220 }}>
                          <img
                            key={currentSegment.image_query}
                            src={`${API_BASE}/export/image/${jobId}/${currentModule.index}/${currentLesson.lesson_index}/${currentSegment.slide_index}`}
                            alt={currentSegment.image_query}
                            style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 10, display: 'block' }}
                            onError={() => setImageFailed(true)}
                          />
                        </div>
                      </div>
                    )}

                    {/* ── TABLE slide ─────────────────────────────────────── */}
                    {currentSegment.slide_type === 'table' && (
                      <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
                        <h2 style={{ color: '#0F1728', fontSize: '2rem', fontWeight: 800, marginBottom: 20 }}>
                          {currentSegment.slide_title || currentLesson.title}
                        </h2>
                        {currentSegment.table_data?.headers?.length > 0 ? (
                          <div style={{ overflowX: 'auto', borderRadius: 10, boxShadow: '0 2px 12px rgba(249,115,22,0.12)' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '1rem' }}>
                              <thead>
                                <tr>
                                  {currentSegment.table_data.headers.map((h, i) => (
                                    <th key={i} style={{
                                      background: '#9A3412',
                                      color: '#fff',
                                      padding: '12px 16px',
                                      textAlign: 'left',
                                      fontWeight: 700,
                                      fontSize: '0.95rem',
                                      letterSpacing: '0.03em',
                                      borderRight: i < currentSegment.table_data.headers.length - 1 ? '1px solid rgba(255,255,255,0.15)' : 'none'
                                    }}>
                                      {h}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {currentSegment.table_data.rows.map((row, ri) => (
                                  <tr key={ri} style={{ background: ri % 2 === 0 ? 'rgba(255,255,255,0.55)' : 'rgba(219,234,254,0.45)' }}>
                                    {row.map((cell, ci) => (
                                      <td key={ci} style={{
                                        padding: '10px 16px',
                                        color: '#0F1728',
                                        borderBottom: '1px solid rgba(249,115,22,0.08)',
                                        borderRight: ci < row.length - 1 ? '1px solid rgba(249,115,22,0.08)' : 'none',
                                        fontSize: '0.95rem',
                                        lineHeight: 1.5
                                      }}>
                                        {cell}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <p style={{ color: '#5C6B85', fontSize: '1rem', marginTop: 12 }}>No table data available for this slide.</p>
                        )}
                      </div>
                    )}

                    {/* Slide navigation arrows + counter (shared across all types) */}
                    {segments.length > 1 && (
                      <>
                        <button 
                          className="slide-nav-btn left"
                          disabled={activeSegmentIndex === 0} 
                          onClick={() => setActiveSegmentIndex(prev => prev - 1)}
                        >
                          <IconArrowLeft size={32} />
                        </button>
                        <button 
                          className="slide-nav-btn right"
                          disabled={activeSegmentIndex === segments.length - 1} 
                          onClick={() => setActiveSegmentIndex(prev => prev + 1)}
                        >
                          <IconArrowRight size={32} />
                        </button>
                        <div style={{ position: 'absolute', bottom: 20, right: 20, fontSize: 14, color: '#5C6B85', fontWeight: 600 }}>
                          {activeSegmentIndex + 1} / {segments.length}
                        </div>
                      </>
                    )}
                  </div>
                ) : (
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
                    <div 
                      className={`flashcard-scene ${isFlipped ? 'is-flipped' : ''}`}
                      onClick={() => setIsFlipped(!isFlipped)}
                      style={{ width: '100%', maxWidth: 600, height: 300 }}
                    >
                      <div className="flashcard-inner">
                        <div className="flashcard-face flashcard-front" style={{ fontSize: 24 }}>
                          <span className="flashcard-text">
                            {currentFlashcards.cards[activeFlashcardIndex].front}
                          </span>
                        </div>
                        <div className="flashcard-face flashcard-back" style={{ fontSize: 24 }}>
                          <span className="flashcard-text">
                            {currentFlashcards.cards[activeFlashcardIndex].back}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <div style={{ marginTop: 24, fontSize: 14, color: '#94a3b8' }}>
                      Click card to flip
                    </div>

                    <div style={{ position: 'absolute', bottom: 20, right: 20, display: 'flex', gap: 12 }}>
                      <button 
                        disabled={activeFlashcardIndex === 0} 
                        onClick={() => setActiveFlashcardIndex(prev => prev - 1)}
                        style={{ background: '#334155', border: 'none', color: '#fff', padding: '6px 12px', borderRadius: 6, cursor: activeFlashcardIndex === 0 ? 'not-allowed' : 'pointer', opacity: activeFlashcardIndex === 0 ? 0.4 : 1 }}
                      >
                        <IconArrowLeft size={16} />
                      </button>
                      <span style={{ fontSize: 14, alignSelf: 'center', color: '#cbd5e1', fontWeight: 600 }}>
                        {activeFlashcardIndex + 1} / {currentFlashcards.cards.length}
                      </span>
                      <button 
                        disabled={activeFlashcardIndex === currentFlashcards.cards.length - 1} 
                        onClick={() => setActiveFlashcardIndex(prev => prev + 1)}
                        style={{ background: '#334155', border: 'none', color: '#fff', padding: '6px 12px', borderRadius: 6, cursor: activeFlashcardIndex === currentFlashcards.cards.length - 1 ? 'not-allowed' : 'pointer', opacity: activeFlashcardIndex === currentFlashcards.cards.length - 1 ? 0.4 : 1 }}
                      >
                        <IconArrowRight size={16} />
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Narration and Audio Track — only shown when relevant */}
              {(hasNarration || hasAudio) && (
                <div style={{ display: 'grid', gridTemplateColumns: hasNarration && hasAudio ? '1fr 1fr' : '1fr', gap: 24 }}>
                  {hasNarration && (
                    <div style={{ background: '#f8fafc', padding: 24, borderRadius: 12, border: '1px solid #e2e8f0' }}>
                       <h4 style={{marginBottom: 12, color: '#0f172a', fontSize: 16, fontWeight: 700}}>Lesson Narration (Slide {activeSegmentIndex + 1})</h4>
                       <p style={{fontSize: 15, color: '#475569', lineHeight: 1.6, minHeight: 80}}>
                         {currentSegment.narration}
                       </p>
                    </div>
                  )}
                  {hasAudio && (
                    <div style={{ background: '#f8fafc', padding: 24, borderRadius: 12, border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                       <h4 style={{marginBottom: 16, color: '#0f172a', fontSize: 16, fontWeight: 700}}>Audio Track</h4>
                       <audio controls src={`${API_BASE}/export/audio/${jobId}_m${currentModule.index}_l${currentLesson.lesson_index}`} style={{width: '100%'}} />
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {/* Lesson Essay — rich prose below the slide deck */}
            {currentLesson.lesson_essay ? (
              <div style={{ marginTop: 8, background: '#fff', borderRadius: 12, border: '1px solid #e2e8f0', padding: '28px 32px', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                  <div style={{ width: 4, height: 24, borderRadius: 2, background: 'var(--brand, #F97316)' }} />
                  <h4 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.01em' }}>
                    Lesson Deep-Dive
                  </h4>
                </div>
                {currentLesson.lesson_essay.split('\n').filter(p => p.trim()).map((para, i) => (
                  <p key={i} style={{ fontSize: 15, color: '#334155', lineHeight: 1.8, marginBottom: 14, margin: i > 0 ? '14px 0 0' : 0 }}>
                    {para}
                  </p>
                ))}
              </div>
            ) : currentLesson.key_takeaways?.length > 0 ? (
              /* Fallback for older courses that have no lesson_essay yet */
              <div className="key-takeaways" style={{ background: '#FFF7ED', padding: 20, borderRadius: 8 }}>
                <h4>Key Takeaways</h4>
                <ul style={{ marginTop: 10, paddingLeft: 20 }}>
                  {currentLesson.key_takeaways.map((tk, i) => <li key={i} style={{marginBottom: 5}}>{tk}</li>)}
                </ul>
              </div>
            ) : null}
          </div>
        )}

        {activeTab === 'quiz' && currentQuiz && (
          <div className="quiz-container" style={{ maxWidth: 600 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2>Module {currentModule?.index} Quiz</h2>
              {quizSubmitted && (
                <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--brand)' }}>
                  Score: {score} / {currentQuiz.questions.length} ({Math.round((score / currentQuiz.questions.length) * 100)}%)
                </div>
              )}
            </div>
            
            {currentQuiz.questions.map((q, i) => {
              const selectedOpt = selectedAnswers[i];
              
              return (
                <div key={i} style={{ background: '#fff', border: '1px solid #e2e8f0', padding: 20, borderRadius: 8, marginBottom: 20 }}>
                  <p style={{ fontWeight: 600, marginBottom: 15 }}>{i+1}. {q.question}</p>
                  {q.options.map((opt, oi) => {
                    const isSelected = selectedOpt === oi;
                    
                    let bg = '#f8fafc';
                    let border = '1px solid #e2e8f0';
                    
                    if (quizSubmitted) {
                      if (oi === q.correct_index) {
                        bg = '#dcfce7'; // correct option is green
                        border = '1px solid #10b981';
                      } else if (isSelected) {
                        bg = '#fee2e2'; // user selected wrong option is red
                        border = '1px solid #f87171';
                      }
                    } else if (isSelected) {
                      bg = '#FFF7ED'; // selected option before submit is blue
                      border = '1px solid #F97316';
                    }
                    
                    return (
                      <div 
                        key={oi} 
                        onClick={() => {
                          if (!quizSubmitted) {
                            setSelectedAnswers(prev => ({ ...prev, [i]: oi }));
                          }
                        }}
                        style={{ 
                          padding: '10px 15px', 
                          border: border, 
                          borderRadius: 6, 
                          marginBottom: 10, 
                          background: bg,
                          cursor: quizSubmitted ? 'default' : 'pointer',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center'
                        }}
                      >
                        <span>{String.fromCharCode(65+oi)}. {opt}</span>
                        {quizSubmitted && oi === q.correct_index && (
                          <span style={{color: '#166534', fontWeight: 600, fontSize: 12}}>✓ Correct</span>
                        )}
                        {quizSubmitted && isSelected && oi !== q.correct_index && (
                          <span style={{color: '#991b1b', fontWeight: 600, fontSize: 12}}>✗ Incorrect</span>
                        )}
                      </div>
                    );
                  })}
                  
                  {quizSubmitted && (
                    <p style={{ fontSize: 13, color: '#64748b', marginTop: 12, padding: '10px', background: '#f8fafc', borderRadius: 4, borderLeft: '3px solid #64748b' }}>
                      <strong>Explanation:</strong> {q.explanation}
                    </p>
                  )}
                </div>
              );
            })}
            
            <div style={{ marginTop: 20, display: 'flex', gap: 15 }}>
              {!quizSubmitted ? (
                <button 
                  onClick={() => setQuizSubmitted(true)}
                  disabled={Object.keys(selectedAnswers).length < currentQuiz.questions.length}
                  className="generate-btn"
                  style={{ width: 'auto', padding: '10px 24px', opacity: Object.keys(selectedAnswers).length < currentQuiz.questions.length ? 0.5 : 1, cursor: Object.keys(selectedAnswers).length < currentQuiz.questions.length ? 'not-allowed' : 'pointer' }}
                >
                  Submit Quiz
                </button>
              ) : (
                <button 
                  onClick={() => {
                    setSelectedAnswers({});
                    setQuizSubmitted(false);
                  }}
                  className="generate-btn"
                  style={{ width: 'auto', padding: '10px 24px', background: '#64748b' }}
                >
                  Retry Quiz
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

