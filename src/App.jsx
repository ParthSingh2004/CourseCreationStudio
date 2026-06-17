import { useState } from 'react';
import Topbar from './components/Topbar';
import Sidebar from './components/Sidebar';
import CourseDesignPage from './pages/CourseDesignPage';
import GenerationPage from './pages/GenerationPage';
import CourseViewerPage from './pages/CourseViewerPage';
import HistoryPage from './pages/HistoryPage';


export default function App() {
  // page: 'design' | 'generation' | 'viewer'
  const [page, setPage] = useState('design');

  const [jobId, setJobId] = useState(null);

  return (
    <div className="app-shell">
      <Topbar page={page} onSelectCourse={(id) => {
        setJobId(id);
        setPage('viewer');
      }} />

      <div className="main-body">
        {page === 'viewer' ? (
          <CourseViewerPage jobId={jobId} onBack={() => setPage('design')} />
        ) : (
          <>
            <Sidebar page={page} setPage={setPage} />
            {page === 'design' && (
              <CourseDesignPage onGenerate={(id) => {
                setJobId(id);
                setPage('generation');
              }} />
            )}
            {page === 'generation' && (
              <GenerationPage 
                jobId={jobId} 
                onComplete={() => setPage('viewer')} 
                onBack={() => setPage('design')} 
              />
            )}
            {page === 'history' && (
              <HistoryPage 
                onSelectCourse={(id) => {
                  setJobId(id);
                  setPage('viewer');
                }} 
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
