import React, { useEffect, useState } from 'react';
import { api, post } from '../api';
import OfferPicker from './OfferPicker';

export default function CreateCampaign({ onCreated, onError }) {
  const [refs, setRefs] = useState({ domains: [], groups: [], sources: [] });
  const [form, setForm] = useState({ name: '', geo: '', domain_id: '', group_id: '', traffic_source_id: '' });
  const [offer, setOffer] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    Promise.all(['domains', 'groups', 'sources'].map(kind => api('/references/' + kind)))
      .then(([domains, groups, sources]) => setRefs({ domains, groups, sources }))
      .catch(onError);
  }, []);
  const selectField = (key, label, items) => <label className="create-row"><span>{label}</span><select required value={form[key]} onChange={e => setForm({ ...form, [key]: e.target.value })}><option value="">Select {label.toLowerCase()}</option>{items.map(item => <option key={item.id} value={item.id}>{item.name || item.domain || item.hostname || `#${item.id}`}</option>)}</select></label>;
  async function submit(event) {
    event.preventDefault();
    if (!offer) return onError(new Error('Select an offer'));
    setBusy(true);
    try {
      const campaign = await post('/campaigns', { ...form, domain_id: Number(form.domain_id), group_id: Number(form.group_id), traffic_source_id: Number(form.traffic_source_id), offer_id: offer.id });
      onCreated(campaign);
    } catch (error) { onError(error); }
    finally { setBusy(false); }
  }
  return <section className="panel create campaign-form">
    <h2>New campaign</h2>
    <form onSubmit={submit}>
      <label className="create-row"><span>Name</span><input required maxLength={255} placeholder="Campaign name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}/></label>
      <label className="create-row"><span>Geo</span><input required minLength={2} maxLength={2} placeholder="MX, AU, RO..." value={form.geo} onChange={e => setForm({ ...form, geo: e.target.value.toUpperCase() })}/></label>
      <div className="create-row"><span>Offer</span><div><OfferPicker onSelect={setOffer}/>{offer && <small className="selected-offer">Selected: [{offer.id}] {offer.name}</small>}</div></div>
      <div className="create-settings">Campaign settings</div>
      {selectField('domain_id', 'Domain', refs.domains)}
      {selectField('group_id', 'Group', refs.groups)}
      {selectField('traffic_source_id', 'Traffic source', refs.sources)}
      <button className="primary create-submit" disabled={busy}>{busy ? 'Creating…' : 'Create'}</button>
    </form>
  </section>;
}
