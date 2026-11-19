import React, { useEffect, useRef, useState } from 'react';
import { api } from './api';
import CreateCampaign from './components/CreateCampaign';
import Stream from './components/Stream';

const SELECTED_CAMPAIGN = 'adrobot.selectedCampaign';

export default function App() {
  const [campaigns, setCampaigns] = useState([]);
  const [campaign, setCampaign] = useState(null);
  const [streams, setStreams] = useState([]);
  const [page, setPage] = useState('streams');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [tracker, setTracker] = useState('');
  const [allOffers, setAllOffers] = useState(null);
  const [search, setSearch] = useState('');
  const requestId = useRef(0);
  const onError = e => setError(e.message);

  async function fetchStreams(selected) {
    if (!selected) return;
    const request = ++requestId.current;
    setLoading(true);
    try {
      const result = await api(`/campaigns/${selected.id}/streams`);
      if (request === requestId.current) setStreams(result);
    } catch (e) { if (request === requestId.current) onError(e); }
    finally { if (request === requestId.current) setLoading(false); }
  }
  function choose(selected) {
    localStorage.setItem(SELECTED_CAMPAIGN, String(selected.id));
    setCampaign(selected);
    setStreams([]);
    setAllOffers(null);
    setPage('streams');
    fetchStreams(selected);
  }
  async function loadCampaigns(restore = false) {
    try {
      const result = await api('/campaigns');
      setCampaigns(result);
      if (restore) {
        const selectedId = localStorage.getItem(SELECTED_CAMPAIGN);
        const selected = result.find(c => String(c.id) === selectedId);
        if (selected) choose(selected);
      }
    } catch (e) { onError(e); }
  }
  useEffect(() => { loadCampaigns(true); api('/tracker').then(x => setTracker(x.url)).catch(onError); }, []);
  async function showOffers() {
    if (allOffers !== null) { setAllOffers(null); return; }
    try { setAllOffers(await api('/references/offers')); } catch (e) { onError(e); }
  }
  const offerStreams = streams.filter(s => s.schema === 'landings' || (!s.schema && s.offers.length > 0));
  const otherStreams = streams.filter(s => !offerStreams.includes(s));
  const filteredCampaigns = campaigns.filter(c => `${c.name} ${c.id}`.toLowerCase().includes(search.toLowerCase()));
  return <>
    <header><div className="brand">AdRobot</div><span>Campaigns</span></header>
    <main>
      {error && <div className="alert"><span>{error}</span><button onClick={() => setError('')}>×</button></div>}
      <div className="workspace">
        <aside className="campaign-sidebar">
          <div className="sidebar-title"><strong>Campaigns</strong><button title="Refresh list" onClick={() => loadCampaigns()}>↻</button></div>
          <input aria-label="Search campaigns" placeholder="Search by name or ID" value={search} onChange={e => setSearch(e.target.value)}/>
          <button className="create-button" onClick={() => setPage('create')}>Create campaign</button>
          <div className="campaign-list">{filteredCampaigns.map(c => <button className={'campaign-item' + (page === 'streams' && campaign?.id === c.id ? ' selected' : '')} key={c.id} onClick={() => choose(c)}><span>{c.name}</span><small>#{c.id}</small></button>)}</div>
        </aside>
        <div className="workspace-content">
          {page === 'create' && <><div className="breadcrumb">Campaigns / New campaign</div><CreateCampaign onError={onError} onCreated={c => { loadCampaigns(); choose(c); }}/></>}
          {page === 'streams' && campaign && <section className="editor">
            <div className="breadcrumb">Campaigns / <span>{campaign.name}</span> / Keitaro Streams</div>
            <div className="actions"><div><button onClick={() => fetchStreams(campaign)} disabled={loading}>{loading ? 'LOADING…' : 'FETCH STREAMS FROM KT ⤓'}</button>{tracker && <a className="button-link" href={`${tracker}/admin/#!/campaign/${campaign.id}/main`} target="_blank" rel="noreferrer">VIEW IN KT ↗</a>}</div><button onClick={showOffers}>{allOffers === null ? 'SHOW ALL OFFERS' : 'HIDE OFFERS'}</button></div>
            {allOffers !== null && <div className="all-offers"><strong>Offers</strong><ul>{allOffers.map(o => <li key={o.id}>[{o.id}] {o.name}</li>)}</ul></div>}
            <div className="table-head"><span></span><span>Share</span><span>Stats</span><span>Trends</span><span>Actions</span></div>
            {offerStreams.map(s => <Stream key={s.stream_id} stream={s} onError={onError} change={next => setStreams(old => old.map(x => x.stream_id === next.stream_id ? {...x, ...next} : x))}/>)}
            {otherStreams.map(s => <div className="other-stream" key={s.stream_id}><strong>Stream: {s.name}</strong> <span>(#{s.stream_id})</span></div>)}
            {!loading && streams.length === 0 && <p className="empty">This campaign has no streams</p>}
          </section>}
          {page === 'streams' && !campaign && <p className="empty">Select a campaign from the list</p>}
        </div>
      </div>
    </main>
  </>;
}

