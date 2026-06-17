import { useState, useEffect } from 'react';
import { IconBookOpen } from '../icons';

const API_BASE = import.meta.env.VITE_API_BASE || 
  (window.location.origin.includes('5173') ? 'http://localhost:8000/api/v1' : `${window.location.origin}/api/v1`);

export default function HistoryPage({ onSelectCourse }) {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/courses`)
      .then(res => res.json())
      .then(data => {
        setCourses(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="page-content">
      <div className="page-header">
        <h1>Course History</h1>
        <p>View and access your previously generated courses.</p>
      </div>
      
      {loading ? (
        <div style={{ color: 'var(--text-muted)' }}>Loading courses...</div>
      ) : courses.length === 0 ? (
        <div style={{ color: 'var(--text-muted)' }}>No courses generated yet.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {courses.map(course => (
            <div 
              key={course.id} 
              className="card" 
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', padding: 24 }}
              onClick={() => onSelectCourse(course.id)}
            >
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <IconBookOpen size={18} style={{ color: 'var(--primary)' }} />
                  {course.title || 'Untitled Course'}
                </h3>
                <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>{course.description || 'No description available'}</p>
                <div style={{ fontSize: 12, color: '#888', marginTop: 12 }}>
                  Created on: {new Date(course.created_at).toLocaleString()}
                </div>
              </div>
              <button className="primary-btn" style={{ padding: '8px 16px', fontSize: 14, background: 'var(--primary)', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
                View Course
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
