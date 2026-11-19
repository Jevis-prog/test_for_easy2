import React, { useState } from 'react';
import { post } from '../api';
import OfferPicker from './OfferPicker';

export default function Stream({ stream, change, onError }) {
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  async function run(operation, id) {
    setBusy(true);
    try {
      const updated = await post(`/streams/${stream.stream_id}/${operation}`, id ? {offer_id: id} : undefined);
      change(updated);
      if (operation === 'offers/add') setSelected(null);
    } catch (e) { onError(e); }
    finally { setBusy(false); }
  }
  return <article className={'stream' + (stream.dirty ? ' dirty' : '')}>
    <div className="stream-header"><strong>Stream: {stream.name}</strong> <span className="muted">(#{stream.stream_id})</span>
      {stream.dirty && <div className="stream-actions"><button className="primary" disabled={busy || stream.conflict} onClick={() => run('publish')}>PUSH TO KT</button> <button disabled={busy} onClick={() => run('cancel')}>CANCEL</button></div>}
    </div>
    {stream.conflict && <div className="conflict">The stream changed in Keitaro. Cancel the draft, refresh the streams, and apply your changes again.</div>}
    {stream.offers.map(o => <div className={'offer-row' + (o.removed ? ' removed' : '')} key={o.offer_id}>
      <div>[{o.offer_id}] {o.name}</div>
      <div className="share">{o.share}% {!o.removed && <button className={'pin' + (o.pinned ? ' pinned' : '')} title={o.pinned ? 'Unpin share' : 'Pin share'} aria-label={o.pinned ? 'Unpin share' : 'Pin share'} disabled={busy} onClick={() => run('offers/pin', o.offer_id)}>📌</button>}</div>
      <div className="stats"></div><div className="trends"></div>
      <div className="offer-actions"><button disabled={busy} onClick={() => run(o.removed ? 'offers/restore' : 'offers/remove', o.offer_id)}>{o.removed ? '↶ BRING BACK' : '▣ REMOVE'}</button></div>
    </div>)}
    <div className="add-offer"><OfferPicker onSelect={setSelected}/><button disabled={!selected || busy} onClick={() => run('offers/add', selected.id)}>ADD</button>{selected && <small>Selected: [{selected.id}] {selected.name}</small>}</div>
  </article>;
}
