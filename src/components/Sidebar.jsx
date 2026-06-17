import {
  IconBookOpen, IconLayers, IconImage, IconBarChart, IconSettings,
  IconHelpCircle, IconHistory, IconArrowLeft
} from '../icons';

export default function Sidebar({ page, setPage }) {
  const navItems = [
    { id: 'design', icon: <IconBookOpen size={15} />, label: 'Course Design' },
    { id: 'curriculum', icon: <IconLayers size={15} />, label: 'Curriculum' },
    { id: 'modules', icon: <IconLayers size={15} />, label: 'Modules' },
    { id: 'assets', icon: <IconImage size={15} />, label: 'Assets' },
    { id: 'analytics', icon: <IconBarChart size={15} />, label: 'Analytics' },
  ];

  return (
    <aside className="sidebar">
      {(page === 'design' || page === 'history') && (
        <>

          <div className="sidebar-title">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px' }}>
              <div style={{ width: 32, height: 32, background: '#EEF3FF', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <IconBookOpen size={15} style={{ color: '#1E5EF3' }} />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 13 }}>Course Design</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Configuration</div>
              </div>
            </div>
          </div>
          <div className="sidebar-divider" />
          <div
            className={`sidebar-item${page === 'design' ? ' active' : ''}`}
            onClick={() => setPage('design')}
          >
            <IconLayers size={15}/> Curriculum
          </div>
          <div
            className={`sidebar-item${page === 'history' ? ' active' : ''}`}
            onClick={() => setPage('history')}
          >
            <IconHistory size={15}/> History
          </div>

        </>
      )}

      {page === 'generation' && (
        <>
          <div className="sidebar-title">
            <div style={{ padding: '8px 14px' }}>
              <div style={{ fontWeight: 700, fontSize: 13 }}>Course Structure</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Modular Design</div>
            </div>
          </div>
          <div className="sidebar-divider" />
          <div className="sidebar-item active">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            Generation
          </div>

        </>
      )}
    </aside>
  );
}
