import { useState, useEffect, useRef } from 'react';
import {
  IconSearch, IconBell, IconUser, IconShare, IconDownload, IconBookOpen
} from '../icons';

const API_BASE = import.meta.env.VITE_API_BASE || 
  (window.location.origin.includes('5173') ? 'http://localhost:8000/api/v1' : `${window.location.origin}/api/v1`);

export default function Topbar({ page, onSelectCourse, onGoHome }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [courses, setCourses] = useState([]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    fetch(`${API_BASE}/courses`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setCourses(data);
        } else {
          setCourses([]);
        }
      })
      .catch(err => {
        console.error(err);
        setCourses([]);
      });
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredCourses = courses.filter(c => 
    c.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value);
    setIsDropdownOpen(true);
  };
  
  const handleSelectCourse = (id) => {
    setSearchQuery('');
    setIsDropdownOpen(false);
    if (onSelectCourse) {
      onSelectCourse(id);
    }
  };

  return (
    <header className="topbar">
      <div className="topbar-logo" onClick={onGoHome}>
        {/* Logo mark */}
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <rect width="28" height="28" rx="7" fill="var(--brand)"/>
          <path d="M8 14c0-3.314 2.686-6 6-6s6 2.686 6 6" stroke="#fff" strokeWidth="2.5" strokeLinecap="round"/>
          <circle cx="14" cy="18" r="3" fill="#fff"/>
        </svg>
        Chapter's CourseStudio
      </div>

      <div className="topbar-search" ref={dropdownRef}>
        <span className="search-icon"><IconSearch size={14} /></span>
        <input 
          placeholder={page === 'viewer' ? "Search lessons..." : "Search courses..."}
          value={searchQuery}
          onChange={handleSearchChange}
          onFocus={() => setIsDropdownOpen(true)}
        />
        {isDropdownOpen && searchQuery.trim() !== '' && (
          <div className="search-dropdown" style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            background: 'var(--surface, #fff)',
            border: '1px solid var(--border, #eee)',
            borderRadius: 'var(--radius-md, 8px)',
            marginTop: '4px',
            maxHeight: '300px',
            overflowY: 'auto',
            zIndex: 100,
            boxShadow: 'var(--shadow-md, 0 4px 12px rgba(0,0,0,0.1))'
          }}>
            {filteredCourses.length > 0 ? (
              filteredCourses.map(course => (
                <div 
                  key={course.id} 
                  onClick={() => handleSelectCourse(course.id)}
                  style={{ 
                    padding: '12px 16px', 
                    borderBottom: '1px solid var(--border, #eee)', 
                    cursor: 'pointer', 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '12px',
                    transition: 'background 160ms ease'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--surface-2, #f5f5f5)'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <IconBookOpen size={16} style={{ color: 'var(--brand)', flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {course.title || 'Untitled Course'}
                    </div>
                    {course.description && (
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginTop: '2px' }}>
                        {course.description}
                      </div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div style={{ padding: '16px', fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center' }}>
                No courses found matching "{searchQuery}"
              </div>
            )}
          </div>
        )}
      </div>

      <div className="topbar-actions">
      </div>
    </header>
  );
}
