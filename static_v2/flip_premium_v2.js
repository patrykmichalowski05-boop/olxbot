/* FLIPRADAR_PREMIUM_UI_V2 */
(() => {
  'use strict';
  const formatPLN = v => v == null || v === '' || !Number.isFinite(Number(v))
    ? '—' : new Intl.NumberFormat('pl-PL',{maximumFractionDigits:0}).format(Number(v)) + ' zł';
  const block = (tag, className, text) => {
    const n = document.createElement(tag);
    if (className) n.className = className;
    if (text !== undefined) n.textContent = String(text);
    return n;
  };
  const sourceLabel = v => String(v).toLowerCase()==='facebook' ? 'Facebook' : 'OLX';
  const safeExternal = v => {
    try {
      const url = new URL(v);
      return url.protocol==='https:' && (
        url.hostname === 'olx.pl' || url.hostname.endsWith('.olx.pl') ||
        url.hostname === 'facebook.com' || url.hostname.endsWith('.facebook.com')
      ) ? url.href : null;
    } catch { return null; }
  };

  function renderItem(item){
    const row=block('div','fr-offer-row');
    const left=block('div','fr-offer-details');
    const name=block('a','fr-offer-title',item.title||'Bez nazwy');
    const url=safeExternal(item.url);
    if (url){ name.href=url;name.target='_blank';name.rel='noopener noreferrer'; }
    else {name.removeAttribute('href');}
    left.appendChild(name);
    const meta=block('div','fr-offer-meta');
    const src=block('span','fr-source-label'+(item.source==='facebook'?' fb':''),sourceLabel(item.source));
    meta.appendChild(src);
    const specs=[item.cpu,item.gpu,item.ram_gb!=null?item.ram_gb+' GB RAM':''].filter(Boolean).join(' · ');
    meta.appendChild(block('span','',specs||'Specyfikacja do weryfikacji'));
    left.appendChild(meta);
    const right=block('div','fr-offer-values');
    right.appendChild(block('strong','',formatPLN(item.price_zl)));
    right.appendChild(block('small','',item.minimum_resale_needed_zl==null?'Brak progu odsprzedaży':'Min. odsprzedaż '+formatPLN(item.minimum_resale_needed_zl)));
    row.append(left,right);
    return row;
  }

  document.querySelectorAll('[data-fr-radar]').forEach(widget=>{
    const form=widget.querySelector('[data-fr-form]');
    const list=widget.querySelector('[data-fr-list]');
    const status=widget.querySelector('[data-fr-result-status]');
    const pageText=widget.querySelector('[data-fr-page]');
    const prev=widget.querySelector('[data-fr-prev]');
    const next=widget.querySelector('[data-fr-next]');
    let page=1,pages=1,controller=null;
    const count=Math.max(1,Math.min(40,Number(widget.dataset.size)||12));
    const get = name => form.elements.namedItem(name)?.value || '';

    async function load(){
      if (controller) controller.abort();
      controller=new AbortController();
      const signal=controller.signal;
      const params=new URLSearchParams({
        q:get('q'),source:get('source'),sort:get('sort'),
        min_price:get('min_price'),max_price:get('max_price'),
        page:String(page),page_size:String(count)
      });
      status.textContent='Wczytuję oferty…';
      prev.disabled=next.disabled=true;
      try {
        const response=await fetch('/premium-radar/api/offers?'+params.toString(),{
          credentials:'same-origin',headers:{Accept:'application/json'},cache:'no-store',signal
        });
        let data;
        try {data=await response.json();} catch {throw new Error('Serwer nie zwrócił poprawnego JSON');}
        if(!response.ok) throw new Error(data.error||('HTTP '+response.status));
        if(signal.aborted)return;
        pages=Math.max(1,Number(data.pages)||1);
        const items=Array.isArray(data.items)?data.items:[];
        const fragment=document.createDocumentFragment();
        if (!items.length)fragment.appendChild(block('div','fr-radar-empty','Brak dopasowań. Zmień frazę, platformę lub zakres cen.'));
        else items.forEach(item=>fragment.appendChild(renderItem(item)));
        list.replaceChildren(fragment);
        status.textContent='Znaleziono '+new Intl.NumberFormat('pl-PL').format(data.total||0)+' ofert';
        pageText.textContent='Strona '+page+' / '+pages;
        prev.disabled=page<=1;next.disabled=page>=pages;
      }catch(e){
        if(signal.aborted)return;
        list.replaceChildren(block('div','fr-radar-empty',e.message||'Nie udało się wczytać ofert'));
        status.textContent='Nie udało się pobrać wyników';
        pageText.textContent='—';
      }
    }
    form.addEventListener('submit',e=>{e.preventDefault();page=1;load();});
    widget.querySelector('[data-fr-clear]').addEventListener('click',()=>{form.reset();page=1;load();});
    widget.querySelectorAll('[data-fr-preset]').forEach(button=>button.addEventListener('click',()=>{
      form.elements.namedItem('q').value=button.dataset.frPreset;page=1;load();
    }));
    prev.addEventListener('click',()=>{if(page>1){page--;load();}});
    next.addEventListener('click',()=>{if(page<pages){page++;load();}});
    load();
  });
  const stats=document.querySelector('[data-fr-summary]');
  if(stats){
    fetch('/flip-radar/api/summary',{credentials:'same-origin',cache:'no-store'})
      .then(r=>{if(!r.ok)throw new Error('No summary');return r.json();})
      .then(d=>{
        stats.querySelector('[data-fr-total]').textContent=Number(d.total||0).toLocaleString('pl-PL');
        stats.querySelector('[data-fr-olx]').textContent=Number(d.olx||0).toLocaleString('pl-PL');
        stats.querySelector('[data-fr-facebook]').textContent=Number(d.facebook||0).toLocaleString('pl-PL');
        stats.querySelector('[data-fr-updated]').textContent=d.last_import_utc||'Brak danych';
      }).catch(()=>{stats.querySelector('[data-fr-updated]').textContent='Brak danych';});
  }
})();
