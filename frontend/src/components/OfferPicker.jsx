import React, { useEffect, useState } from 'react';
import { api } from '../api';

const SEARCH_DEBOUNCE_MS = 300;
const MAX_SUGGESTIONS = 15;

export default function OfferPicker({ onSelect, label = 'Find an offer by name or ID' }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!query.trim()) { setResults([]); return; }
    let current = true;
    const timer = setTimeout(() => api('/references/offers?q=' + encodeURIComponent(query)).then(x => { if (current) { setResults(x); setError(''); } }).catch(e => { if (current) setError(e.message); }), SEARCH_DEBOUNCE_MS);
    return () => { current = false; clearTimeout(timer); };
  }, [query]);
  return <div className="picker"><input value={query} placeholder={label} onChange={e => setQuery(e.target.value)}/>{error && <small className="error">{error}</small>}{results.length > 0 && <div className="suggestions">{results.slice(0, MAX_SUGGESTIONS).map(o => <button type="button" key={o.id} onClick={() => { onSelect(o); setQuery(''); setResults([]); }}><span>#{o.id}</span> {o.name}</button>)}</div>}</div>;
}
