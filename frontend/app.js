const $=s=>document.querySelector(s);
// ?session=<id> opens a saved conversation (shareable on this device); ?theme=dark|light sets the theme.
const urlParams=new URLSearchParams(location.search),urlSession=urlParams.get('session');
if(urlSession&&/^[a-zA-Z0-9_-]{1,80}$/.test(urlSession))localStorage.setItem('mufti-session',urlSession);
if(['dark','light'].includes(urlParams.get('theme')))localStorage.setItem('mufti-dark',urlParams.get('theme')==='dark');
let session=localStorage.getItem('mufti-session')||crypto.randomUUID(),busy=false,books=[],recent=JSON.parse(localStorage.getItem('mufti-recents')||'[]');
localStorage.setItem('mufti-session',session);
function toast(text){$('#toast').textContent=text;$('#toast').style.display='block';setTimeout(()=>$('#toast').style.display='none',4500)}
// PDF file names end in edition digits ("Muqaddima Seerat ur Rasool 1 1"); show the readable title.
function bookName(b){return b.display_title||niceTitle(b.title)}
function niceTitle(t){return String(t||'').replace(/(?:[\s_-]+\d+)+$/,'').replace(/[_-]+/g,' ').trim()}
function element(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e}
// Safe Markdown for answers: headings, paragraphs, lists, quotes, **bold**, *italic* and [n]
// citation chips. Every piece of model or book text becomes a text node; nothing is parsed as HTML.
function inlineMarkdown(parent,text,cites){
 const re=/(\*\*[^*]+\*\*|\[\d{1,2}\]|\*[^*\s][^*]*\*)/g;let last=0,m;
 while((m=re.exec(text))){
  if(m.index>last)parent.append(document.createTextNode(text.slice(last,m.index)));
  const t=m[0];
  if(t.startsWith('**')){const b=element('strong');inlineMarkdown(b,t.slice(2,-2),cites);parent.append(b)}
  else if(t.startsWith('[')){const n=+t.slice(1,-1),c=cites&&cites.find(x=>x.id===n),chip=element('button','cite-chip',String(n));chip.type='button';
   if(c){chip.title=`${niceTitle(c.book_title)} · PDF page ${c.page}`;chip.setAttribute('aria-label',`Source ${n}, PDF page ${c.page}`);chip.onclick=()=>source(c)}else{chip.tabIndex=-1;chip.classList.add('pending')}
   parent.append(chip)}
  else parent.append(element('em','',t.slice(1,-1)));
  last=m.index+t.length}
 if(last<text.length)parent.append(document.createTextNode(text.slice(last)));
}
function renderMarkdown(box,md,cites){
 box.replaceChildren();box.classList.add('markdown');
 const lines=stripMarkers(md).split('\n');
 let list=null,para=[];
 const flush=()=>{if(para.length){const p=element('p');inlineMarkdown(p,para.join(' '),cites);box.append(p);para=[]}};
 for(const raw of lines){
  const t=raw.trim();let m;
  if(!t){flush();list=null;continue}
  if((m=t.match(/^(#{1,6})\s+(.*)$/))){flush();list=null;const h=element(m[1].length<=3?'h3':'h4');inlineMarkdown(h,m[2].replace(/\*\*/g,''),cites);box.append(h);continue}
  if((m=t.match(/^[-*•·]\s+(.*)$/))){flush();if(!list||list.tagName!=='UL'){list=element('ul');box.append(list)}const li=element('li');inlineMarkdown(li,m[1],cites);list.append(li);continue}
  if((m=t.match(/^(\d{1,2})[.)]\s+(.*)$/))){flush();if(!list||list.tagName!=='OL'){list=element('ol');list.start=+m[1];box.append(list)}const li=element('li');inlineMarkdown(li,m[2],cites);list.append(li);continue}
  // An indented line under a list item continues that item ("1. **Title:**" then its text).
  if(list&&/^\s{2,}\S/.test(raw)&&list.lastChild){flush();const more=element('p','li-more');inlineMarkdown(more,t,cites);list.lastChild.append(more);continue}
  if((m=t.match(/^>\s?(.*)$/))){flush();list=null;const q=element('blockquote','md-note');inlineMarkdown(q,m[1],cites);box.append(q);continue}
  if(/^(-{3,}|\*{3,}|_{3,})$/.test(t)){flush();list=null;box.append(element('hr'));continue}
  list=null;para.push(t)}
 flush();
}
// Hidden model markers (<<full>>, <<none: 2>>, <<next: …>>) never reach the reader, including a
// half-streamed one at the end of a live draft ("<<ne").
function stripMarkers(text){return String(text||'').replace(/<<\s*next\s*:[\s\S]*$/i,'').replace(/<<[^<>\n]{0,200}>>/g,'').replace(/<<[^<>]*$/,'')}
function plainAnswer(text){return stripMarkers(text).replace(/\[\d{1,2}\]/g,'').replace(/^#{1,6}\s+/gm,'').replace(/\*\*|^\s*[-*>]\s+/gm,'').trim()}
function showAnswer(m,data){
 if(data.answer_format==='markdown')renderMarkdown(m.content,data.answer,data.citations||[]);
 else{m.content.classList.remove('markdown');m.content.textContent=data.answer}
 m.content.dir=data.language==='Urdu'||/^[^a-zA-Z]*[\u0600-\u06ff]/.test(data.answer||'')?'rtl':'auto';
}
const taskLabels={explain:'Writing a detailed answer from the book',audit:'Checking every sentence against the book',answer:'Drafting from the book',verifier:'Verifying claims',repair:'Repairing claims',language:'Understanding your question',router:'Understanding your question',subtopics:'Searching related sections'};
function friendlyStatus(data){
 if(!data.task)return data.message||'';
 const label=taskLabels[data.task]||data.task,who=(providerNames[data.provider]||data.provider)+(data.model?' / '+data.model:'');
 if(String(data.state).startsWith('failed'))return `${who} is busy or unavailable — trying the next option…`;
 if(String(data.state).startsWith('skipped'))return data.message;
 return `${label} · ${who}`;
}
// One view at a time. Each entry: [section id, nav button id, breadcrumb title, loader called on open].
const views={chat:['#chat-view','#nav-chat','Ask the library'],library:['#library-view','#nav-library','My library'],saved:['#saved-view','#nav-saved','Saved answers',()=>typeof loadSaved==='function'&&loadSaved()],topics:['#topics-view','#nav-topics','Topic index',()=>typeof loadTopics==='function'&&loadTopics()]};
function view(name){for(const [key,[section,nav]] of Object.entries(views)){$(section).hidden=key!==name;$(nav).classList.toggle('active',key===name)}$('#view-name').textContent=views[name][2];$('#sidebar').classList.remove('open');if(views[name][3])views[name][3]()}
$('#nav-chat').onclick=()=>view('chat');$('#nav-library').onclick=$('#explore-book').onclick=()=>view('library');$('#menu').onclick=()=>$('#sidebar').classList.toggle('open');
function setTheme(dark){document.body.classList.toggle('dark',dark);$('#theme-label').textContent=dark?'Switch to light mode':'Switch to dark mode';localStorage.setItem('mufti-dark',dark)}
setTheme(localStorage.getItem('mufti-dark')==='true');$('#theme').onclick=()=>setTheme(!document.body.classList.contains('dark'));
$('#info').onclick=()=>{$('#source-title').textContent='About Mufti AI';const box=$('#source-content');box.replaceChildren(element('p','', 'Mufti AI searches only the books indexed on this device. Every statement in an answer links to the book page it comes from, and cloud answers are fact-checked sentence by sentence against those pages. It is an information assistant; personal rulings should be confirmed with a qualified scholar.'),element('p','','Choose your answering providers in Models & fallback. Cloud modes send questions, recent conversation context and selected PDF excerpts to configured providers; Ollama runs locally. The optional browser speech recognizer and web fonts may use online services. Use English, Hindi, Urdu or Hinglish. PDF page numbers count from the first page of the file.'));const label=element('label','','');const check=element('input');check.type='checkbox';check.checked=localStorage.getItem('mufti-browser-speech')==='true';check.onchange=()=>localStorage.setItem('mufti-browser-speech',check.checked);label.append(check,document.createTextNode(' Use browser speech recognition with live transcript (may send audio to the browser vendor). Default: local Whisper.'));box.append(label);$('#source-dialog').showModal()};
$('#close-dialog').onclick=()=>$('#source-dialog').close();$('#source-dialog').onclick=e=>{if(e.target===$('#source-dialog'))$('#source-dialog').close()};

const cloudProviders=['anthropic','openai','gemini'];
const providerNames={book_metadata:'Verified book details',anthropic:'Anthropic',openai:'OpenAI',gemini:'Gemini',ollama:'Ollama'};
let modelSettings=null,modelSaving=false,modelLoadVersion=0,priorityValues=[...cloudProviders];
const priorityControls=Array.from(document.querySelectorAll('.model-priority'));
for(const control of priorityControls){for(const provider of cloudProviders){const option=element('option','',providerNames[provider]);option.value=provider;control.append(option)}}
function modelErrorMessage(data,fallback){if(typeof data?.detail==='string')return data.detail;if(Array.isArray(data?.detail))return data.detail.map(item=>item.msg||'Invalid model setting').join('. ');return fallback}
async function modelRequest(method,payload){const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),20000);try{const response=await fetch('/settings/models',{method,signal:controller.signal,headers:payload?{'Content-Type':'application/json'}:undefined,body:payload?JSON.stringify(payload):undefined});let data;try{data=await response.json()}catch{if(method==='GET'&&response.ok)throw Error('The server returned an unreadable settings response.')}if(!response.ok)throw Error(modelErrorMessage(data,'Model settings are unavailable. Please try again.'));return data}catch(error){if(error.name==='AbortError')throw Error('The settings request timed out. Check that Mufti AI is running and try again.');throw error}finally{clearTimeout(timeout)}}
function modelFormStatus(text,error=false){$('#model-save-status').textContent=text;$('#model-save-status').classList.toggle('error',error)}
function updateModelRoute(){
  if(!modelSettings)return;
  const mode=$('#model-mode').value,localOnly=mode==='ollama';
  let order=priorityControls.map(control=>control.value);
  if(cloudProviders.includes(mode))order=[mode,...order.filter(provider=>provider!==mode)];
  const active=localOnly?[]:order.filter(provider=>modelSettings.configured?.[provider]);
  const route=$('#model-route');route.replaceChildren();
  for(const provider of [...active,'ollama']){if(route.childElementCount)route.append(element('span','model-route-arrow','→'));route.append(element('span','model-route-chip'+(provider==='ollama'?' local':''),provider==='ollama'?'Ollama · local':providerNames[provider]))}
  $('#model-mode-help').textContent=localOnly?'Answers use only the selected Ollama model on this device.':mode==='auto'?'Try configured cloud providers in your chosen order. Ollama answers when the cloud options cannot.':providerNames[mode]+' goes first, followed by the other configured clouds and finally Ollama.';
  $('#model-route-note').textContent=localOnly?'Cloud providers are skipped in this mode.':!active.length?'No cloud keys are configured, so Auto will go straight to Ollama.':cloudProviders.includes(mode)&&!modelSettings.configured?.[mode]?providerNames[mode]+' has no configured key and will be skipped.':'If cloud limits run out or providers are unavailable, continue through this route to Ollama.';
  $('#model-consent').textContent=localOnly?'Questions, recent conversation context and selected PDF excerpts are processed by Ollama on this device. These model settings do not send them to cloud providers.':'Cloud mode sends your questions, recent conversation context and selected PDF excerpts to the configured cloud providers shown above as needed. Saving these settings allows this cloud processing. The original PDF stays in your local library.';
  const save=$('#save-models');save.replaceChildren(document.createTextNode(localOnly?'Save local preferences':'Save & allow cloud'),element('span','','↗'));
  const installed=modelSettings.installed_ollama_models||[],selected=$('#model-ollama').value;
  $('#model-ollama').setCustomValidity(localOnly&&!installed.includes(selected)?'Choose an installed Ollama model. Install a local model and reopen these settings to refresh the list.':'');
  $('#model-local-help').textContent=!modelSettings.local_online?'Ollama is offline. Start Ollama before using local answers or local fallback.':!installed.length?'No installed models were found. Install a chat model in Ollama, then reopen these settings.':!installed.includes(selected)?'The saved model is not installed. Choose one of the installed local models for reliable fallback.':'Available models come from Ollama on this device. Gemma models run locally.';
  for(const control of priorityControls)control.disabled=localOnly;
}
function populateModelSettings(data){
  if(!data||!data.models||!data.configured||!Array.isArray(data.installed_ollama_models))throw Error('The model settings response is incomplete. Restart Mufti AI and try again.');
  modelSettings=data;
  showActiveModel(data);
  $('#model-mode').value=['auto',...cloudProviders,'ollama'].includes(data.mode)?data.mode:'auto';
  priorityValues=Array.isArray(data.cloud_order)&&data.cloud_order.length===3&&new Set(data.cloud_order).size===3&&data.cloud_order.every(provider=>cloudProviders.includes(provider))?[...data.cloud_order]:[...cloudProviders];
  priorityControls.forEach((control,index)=>control.value=priorityValues[index]);
  for(const provider of cloudProviders){$('#model-'+provider).value=data.models[provider]||'';const status=$('#model-status-'+provider),info=(data.provider_state||{})[provider],configured=!!data.configured[provider];status.textContent=info?info.label:(configured?'Key configured':'Key not configured');status.title=info&&info.detail?info.detail:'';status.classList.toggle('configured',info?!!info.available:configured)}
  const local=$('#model-ollama');local.replaceChildren();
  const installed=[...new Set(data.installed_ollama_models.filter(model=>typeof model==='string'&&model))];
  const current=data.models.ollama||'';
  if(current&&!installed.includes(current)){const missing=element('option','',current+' · not installed');missing.value=current;local.append(missing)}
  for(const model of installed){const option=element('option','',/^gemma/i.test(model)?model+' · Gemma, local':model);option.value=model;local.append(option)}
  if(!local.options.length){const empty=element('option','','No local models installed');empty.value='';local.append(empty)}
  local.value=current||installed[0]||'';
  const localStatus=$('#model-local-status'),localInfo=(data.provider_state||{}).ollama;localStatus.textContent=localInfo?localInfo.label:(data.local_online?'Ollama running':'Ollama offline');localStatus.classList.toggle('configured',!!data.local_online);
  updateModelRoute();
}
async function loadModelSettings(){
  const version=++modelLoadVersion;modelSettings=null;$('#model-form').hidden=true;$('#model-load-error').hidden=true;$('#model-loading').hidden=false;modelFormStatus('');
  try{const data=await modelRequest('GET');if(version!==modelLoadVersion)return;populateModelSettings(data);const ck=$('#custom-gemini-key');if(ck)ck.value=localStorage.getItem('mufti_custom_gemini_key')||'';$('#model-form').hidden=false}
  catch(error){if(version!==modelLoadVersion)return;$('#model-load-message').textContent=error.message||'Could not load model settings.';$('#model-load-error').hidden=false}
  finally{if(version===modelLoadVersion)$('#model-loading').hidden=true}
}
$('#nav-models').onclick=()=>{$('#sidebar').classList.remove('open');$('#model-dialog').showModal();loadModelSettings()};
$('#retry-models').onclick=loadModelSettings;
function closeModelSettings(){if(!modelSaving)$('#model-dialog').close()}
$('#close-models').onclick=$('#cancel-models').onclick=closeModelSettings;
$('#model-dialog').addEventListener('cancel',event=>{if(modelSaving)event.preventDefault()});
$('#model-dialog').addEventListener('click',event=>{if(event.target===$('#model-dialog')){const rect=event.target.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)closeModelSettings()}});
$('#model-mode').onchange=()=>{modelFormStatus('');updateModelRoute()};
$('#model-ollama').onchange=()=>{modelFormStatus('');updateModelRoute()};
priorityControls.forEach((control,index)=>control.onchange=()=>{const next=control.value,previous=priorityValues[index],duplicate=priorityValues.indexOf(next);if(duplicate!==index&&duplicate>=0)priorityValues[duplicate]=previous;priorityValues[index]=next;priorityControls.forEach((item,i)=>item.value=priorityValues[i]);modelFormStatus('');updateModelRoute()});
$('#model-form').onsubmit=async event=>{
  event.preventDefault();if(modelSaving||!modelSettings)return;
  const mode=$('#model-mode').value,cloud_order=priorityControls.map(control=>control.value),models={};
  if(new Set(cloud_order).size!==3){modelFormStatus('Choose each cloud provider once in the fallback order.',true);return}
  for(const provider of [...cloudProviders,'ollama'])models[provider]=$('#model-'+provider).value.trim();
  if(cloudProviders.some(provider=>!models[provider])){modelFormStatus('Enter a model ID for each cloud provider.',true);return}
  modelSaving=true;$('#model-fields').disabled=true;$('#save-models').disabled=true;$('#close-models').disabled=true;$('#cancel-models').disabled=true;modelFormStatus('Saving your answering preferences…');
  try{const saved=await modelRequest('PUT',{mode,cloud_order,models});populateModelSettings(saved);const ck=$('#custom-gemini-key');if(ck)localStorage.setItem('mufti_custom_gemini_key',ck.value.trim());toast(mode==='ollama'?'Ollama-only preferences saved.':'Cloud preferences saved. Ollama is the final fallback.');$('#nav-models').title=mode==='auto'?'Auto: configured clouds, then Ollama':mode==='ollama'?'Ollama only':providerNames[mode]+' preferred, Ollama fallback';$('#model-dialog').close()}
  catch(error){modelFormStatus(error.message||'Could not save preferences. Please retry.',true)}
  finally{modelSaving=false;$('#model-fields').disabled=false;$('#save-models').disabled=false;$('#close-models').disabled=false;$('#cancel-models').disabled=false;updateModelRoute()}
};
function renderRecent(){const box=$('#recents');box.replaceChildren();if(!recent.length)box.append(element('p','','Your conversations will appear here.'));recent.slice(0,7).forEach(r=>{const b=element('button','recent-link','◌  '+r.title);b.onclick=async()=>{if(busy)return;session=r.id;localStorage.setItem('mufti-session',session);await loadSession();view('chat')};box.append(b)})}renderRecent();
$('#new-chat').onclick=()=>{if(busy)return;session=crypto.randomUUID();localStorage.setItem('mufti-session',session);$('#messages').replaceChildren();$('#welcome').hidden=false;$('#question').value='';view('chat');$('#question').focus()};
function message(role,text){$('#welcome').hidden=true;const wrap=element('article','message '+role),avatar=element('div','bubble-avatar',role==='user'?'YOU':'۞'),body=element('div','message-body'),label=element('div','message-label',role==='user'?'You':'Mufti AI'),content=element('div','text',text);content.dir=/[\u0600-\u06ff]/.test(text)?'rtl':'auto';body.append(label,content);wrap.append(avatar,body);$('#messages').append(wrap);return {wrap,body,content}}
function scroll(){window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'})}
async function source(c){$('#source-title').textContent='From the source';const box=$('#source-content');box.replaceChildren(element('p','',`${niceTitle(c.book_title)} · PDF page ${c.page}`),element('p','','Loading page…'));$('#source-dialog').showModal();
 try{const r=await fetch(`/books/${c.book_id}/pages/${c.page}`);if(!r.ok)throw Error('Could not load page');const page=await r.json();box.lastChild.remove();
  if(page.printed_label&&page.printed_label!==c.page)box.append(element('p','ocr-note',`Physical PDF page ${c.page} · the scan prints page number ${page.printed_label}.`));
  if(c.transcription_reviewed){box.append(element('p','ocr-note','Visually verified title-page transcription (original OCR is shown below):'),element('blockquote','',c.excerpt))}
  if(page.corrected_text){box.append(element('p','ocr-note','Corrected text'+(page.correction_source?' · source: '+page.correction_source:'')+(page.correction_reviewer?' · reviewed by '+page.correction_reviewer:'')));const corrected=element('div','source-text',page.corrected_text);corrected.dir='rtl';box.append(corrected);const rawBox=element('details','full-support'),rawSummary=element('summary','','Raw OCR text (unchanged)');const raw=element('div','source-text',page.raw_text);raw.dir='rtl';rawBox.append(rawSummary,raw);box.append(rawBox)}
  else{if(page.ocr)box.append(element('p','ocr-note','Raw OCR text — no correction has been reviewed for this page. Check the original PDF for exact wording.'));const text=element('div','source-text',page.text);text.dir='rtl';box.append(text)}
  if(page.extraction_quality&&page.extraction_quality.flags&&page.extraction_quality.flags.length)box.append(element('p','ocr-note','Extraction warnings: '+page.extraction_quality.flags.join(', ')));
  const a=element('a','', 'Open original PDF ↗');a.href=`/books/${c.book_id}/pdf#page=${c.page}`;a.target='_blank';a.rel='noopener';box.append(a)}
 catch(e){box.replaceChildren(element('p','',`${niceTitle(c.book_title)} · PDF page ${c.page}`),element('p','',e.message||'Could not load this page.'))}}
function decorate(m,result){
 const meta=element('div','response-meta');
 const providerLabel=result.provider_used==='none'?(result.model_used?'Evidence checked with':'Library response'):(result.grounded?'Answered by: ':'Draft attempted with: ')+(providerNames[result.provider_used]||result.provider_used||'model');
 meta.append(element('span','provider-badge',providerLabel+(result.model_used?' · '+result.model_used:'')));
 const coverageText={full:'✓ Fully answered from the book',partial:'◑ Partly answered from the book',none:'No verified book answer'}[result.coverage||(result.grounded?'full':'none')];
 meta.append(element('span','coverage-badge '+(result.coverage||'none'),coverageText));
 if(result.fallback_used||result.execution?.some(step=>step.fallback))meta.append(element('span','fallback-badge','↳ Fallback used'));
 const speak=element('button','read-aloud','◖ Read aloud');
 speak.onclick=()=>{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(result.answer_format==='markdown'?plainAnswer(result.answer):result.answer.split('Sources')[0]);u.lang={Urdu:'ur-PK',Hindi:'hi-IN',Hinglish:'hi-IN',English:'en-US'}[result.language]||'en-US';speechSynthesis.speak(u)};
 const verified={audited:['verified','✓ Fact-checked against the book'],citations_checked:['linked','◌ Sources linked · not independently fact-checked'],claims_verified:['verified','✓ Each statement verified'],reviewed_metadata:['verified','✓ From the visually checked title page']}[result.verification];
 if(verified){const badge=element('span','verify-badge '+verified[0],verified[1]);badge.title=result.verification==='audited'?'A second model pass compared every sentence with the cited book passages and corrected or removed anything they did not support.':'The local model wrote this answer and every [n] links to a real book passage, but no separate fact-check ran. Open the sources to confirm.';meta.append(badge)}
 const copy=element('button','read-aloud','⧉ Copy');copy.onclick=async()=>{const pages=(result.citations||[]).map(c=>`[${c.id}] ${niceTitle(c.book_title)}, PDF page ${c.page}`).join('\n');try{await navigator.clipboard.writeText(plainAnswer(result.answer)+(pages?'\n\n'+pages:''));toast('Answer copied')}catch{toast('Copy is not available in this browser')}};
 const download=element('button','read-aloud','⤓ Download');download.title='Save this answer with its page references as a Markdown (.md) file';download.onclick=()=>downloadAnswer(m.question,result);
 const print=element('button','read-aloud','⎙ Print');print.title='Print or save as PDF';print.onclick=()=>printAnswer(m,result);
 meta.append(speak,copy,download,print);m.body.append(meta);
 if(m.question&&result.provider_used!=='none')feedbackControls(m,result,meta);
 if(m.question&&result.grounded)saveControl(m,result,meta);
 if(m.question&&result.grounded&&result.answer_format==='markdown'&&(result.citations||[]).length)quizControl(m,result,meta);
 if(result.scope){const s=result.scope;m.body.append(element('p','answer-reason scope-note',s.applied?'◎ Searched only in: '+(s.label||'the selected chapter'):'◎ Nothing in “'+(s.label||'the selected chapter')+'” matched this question, so the whole library was searched instead.'))}
 // Selected model, the model that actually answered, and why they differ are separate facts.
 if(result.selected_model||result.answering_model){
  const route=element('div','model-route-line');
  route.append(element('span','','Selected: '+(providerNames[result.selected_provider]||result.selected_provider||'—')+' / '+(result.selected_model||'—')));
  route.append(element('span','','Answered by: '+(result.answering_model?((providerNames[result.answering_provider]||result.answering_provider)+' / '+result.answering_model):'no model ran')));
  if(result.fallback_reason)route.append(element('span','fallback-reason','Fallback reason — '+result.fallback_reason));
  m.body.append(route);
 }
 if(result.provider_used==='book_metadata')m.body.append(element('p','answer-reason','Answered directly from visually checked title/publication pages. No model generation was needed.'));
 if(result.missing_aspects?.length){const box=element('div','missing-aspects');box.append(element('strong','','Not found in this book:'));const ul=element('ul','');result.missing_aspects.forEach(a=>ul.append(element('li','',a)));box.append(ul);m.body.append(box)}
 if(result.reason_code){const reasons={
  no_matching_passages:'No sufficiently relevant passage was retrieved. Try the book’s wording or a more specific topic.',
  insufficient_coverage:'Passages were found and read, but none directly answers this question. Related passages are listed so you can check the pages yourself.',
  unsupported_claims:'A draft was written but no claim survived checking against its source span, so it was withheld.',
  explanation_unverified:'The book does carry material on this topic, but no drafted sentence survived verification against its source. The book’s own excerpts are shown below instead of an explanation — this is not a statement that the book is silent.',
  insufficient_evidence_after_search:'The search finished and the passages it found do not cover this question.',
  extraction_problem:'The pages that matched did not extract into readable text, so nothing could be quoted from them. This is a scan/OCR problem on those pages, not a statement that the book is silent — open them in the original PDF.',
  needs_topic:'No subject was named, so nothing was searched. Name a topic from the book and it will be looked up.',
  search_incomplete:'The search budget ran out before the book had been searched enough. This is not an absence of evidence — try again or narrow the question.',
  partial_coverage:result.answer_format==='markdown'?'Only part of this question is covered by the book; the note at the end of the answer says what is not covered.':'Only part of this question is covered by the book. The uncovered parts are listed above.',
  provider_unavailable:'No answering model could be reached. This is a service problem, not an absence of evidence in the book.',
  provider_quota_exhausted:'The selected cloud provider refused with a quota or rate limit. This is a model limit, not an absence of evidence in the book.',
  retrieval_unavailable:'The book search service failed, so the book was not actually searched. Check Ollama and the bge-m3 embedding model.',
  out_of_scope:'This question is not about the books in your library, so nothing was searched or generated.',
  not_in_library:'The library was searched and nothing in it is about this subject, so no passages are shown.'};
  if(reasons[result.reason_code])m.body.append(element('p','answer-reason',reasons[result.reason_code]))}
 if(result.execution?.length){const details=element('details','execution-details'),summary=element('summary','','Models actually used');details.append(summary);for(const step of result.execution)details.append(element('p','',`${step.task}: ${providerNames[step.provider]||step.provider} / ${step.model}${step.fallback?' · fallback':''}`));m.body.append(details)}
 if(result.citations?.length){const list=element('div','citation-list');result.citations.forEach(c=>{const d=element('details','citation'),label=c.printed_label&&c.printed_label!==c.page?` · printed ${c.printed_label}`:'',sum=element('summary','',`[${c.id}] ${niceTitle(c.book_title)} · PDF page ${c.page}${label}`),quote=element('blockquote','',c.excerpt),button=element('button','','View original page ↗');quote.dir='auto';button.onclick=()=>source(c);d.append(sum,quote);if(c.full_support&&c.full_support!==c.excerpt){const full=element('details','full-support'),fs=element('summary','','Full verified span');full.append(fs,element('blockquote','',c.full_support));d.append(full)}d.append(button);if(c.transcription_reviewed)d.append(element('p','ocr-note','Title-page transcription visually checked against the original PDF.'));if(c.corrected)d.append(element('p','ocr-note','Corrected text'+(c.correction_source?' · '+c.correction_source:'')+' — raw OCR is kept and shown on the page view.'));else if(c.ocr)d.append(element('p','ocr-note','Raw OCR text · check the original PDF.'));list.append(d)});m.body.append(list)}
 if(result.related?.length){const box=element('div','related-list');box.append(element('p','related-heading','Related passages — shown for reference only, not a verified answer:'));result.related.forEach(r=>{const d=element('details','citation related'),sum=element('summary','',`${niceTitle(r.book_title)} · PDF page ${r.page}`),quote=element('blockquote','',r.excerpt),button=element('button','','View original page ↗');quote.dir='auto';button.onclick=()=>source(r);d.append(sum,quote,button);box.append(d)});m.body.append(box)}
 nextSteps(m,result);
}
// "What next?" — follow-up questions (model-written from the same sources, or built from the
// book's chapter titles) and one-click re-asks of the same question in another answer style.
const styleActions=[['detailed','＋ More detail'],['simple','◔ Simple words'],['short','≡ Short'],['points','✎ Study notes']];
function nextSteps(m,result){
 const followups=(result.followups||[]).filter(q=>typeof q==='string'&&q.trim());
 const canRestyle=result.grounded&&result.answer_format==='markdown'&&m.question;
 if(!followups.length&&!canRestyle)return;
 const box=element('div','next-steps');
 if(followups.length){box.append(element('p','next-heading','Ask next'));const list=element('div','followup-list');for(const q of followups.slice(0,4)){const b=element('button','followup-chip',q);b.type='button';b.dir='auto';b.onclick=()=>send(q);list.append(b)}box.append(list)}
 if(canRestyle){const row=element('div','restyle-row');row.append(element('span','restyle-label','Same question:'));for(const [style,label] of styleActions){if(style===(result.answer_style||'detailed'))continue;const b=element('button','restyle-chip',label);b.type='button';b.onclick=()=>send(m.question,{style,label:label.replace(/^\S+\s/,'')});row.append(b)}box.append(row)}
 m.body.append(box);
}
function answerMarkdown(question,result){
 const lines=['# '+(question||'Mufti AI answer'),'',stripMarkers(result.answer).trim(),''];
 if(result.citations?.length){lines.push('## Sources','');for(const c of result.citations)lines.push(`[${c.id}] ${niceTitle(c.book_title)}, PDF page ${c.page}${c.printed_label&&c.printed_label!==c.page?' (printed '+c.printed_label+')':''} — “${c.excerpt}”`);lines.push('')}
 lines.push('---',`Mufti AI · ${new Date().toLocaleString()} · ${result.verification==='audited'?'Fact-checked against the book':'Sources linked'}${result.answering_model?' · '+result.answering_model:''}`);
 return lines.join('\n');
}
function downloadAnswer(question,result){
 const blob=new Blob([answerMarkdown(question,result)],{type:'text/markdown;charset=utf-8'}),a=document.createElement('a');
 a.href=URL.createObjectURL(blob);a.download='mufti-ai-'+String(question||'answer').replace(/[^\p{L}\p{N}]+/gu,'-').slice(0,50).replace(/^-|-$/g,'')+'.md';
 document.body.append(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},500);toast('Answer downloaded');
}
function printAnswer(m,result){
 // The answer DOM was built from text nodes only, so cloning it carries no injected markup.
 const w=window.open('','_blank');if(!w){toast('Allow pop-ups to print this answer');return}
 const doc=w.document;doc.title='Mufti AI — '+(m.question||'answer');
 const style=doc.createElement('style');style.textContent='body{font:15px/1.8 Georgia,serif;max-width:760px;margin:30px auto;padding:0 20px;color:#1c2b25}h1{font-size:22px}h3{color:#1c5545;border-bottom:1px solid #ddd}.cite-chip{border:1px solid #c9a24a;border-radius:4px;padding:0 4px;font-size:11px;background:none}[dir=rtl]{font-family:"Noto Nastaliq Urdu",serif;line-height:2.6}.src{font-size:12px;color:#555;border-top:1px solid #ccc;margin-top:24px;padding-top:10px}';
 doc.head.append(style);const h=doc.createElement('h1');h.textContent=m.question||'Mufti AI answer';doc.body.append(h,m.content.cloneNode(true));
 if(result.citations?.length){const src=doc.createElement('div');src.className='src';for(const c of result.citations){const p=doc.createElement('p');p.textContent=`[${c.id}] ${niceTitle(c.book_title)} · PDF page ${c.page} — “${c.excerpt}”`;src.append(p)}doc.body.append(src)}
 setTimeout(()=>w.print(),300);
}
async function loadSession(){try{const r=await fetch('/sessions/'+session);if(!r.ok)return;const data=await r.json();$('#messages').replaceChildren();$('#welcome').hidden=!(!data.history?.length);for(const t of data.history||[]){message('user',t.question);const m=message('assistant','');m.question=t.question;showAnswer(m,t);if(t.provider_used!==undefined)decorate(m,t);const note=element('button','read-aloud','Delete this conversation');note.onclick=async()=>{if(!confirm('Delete this conversation and its saved history?'))return;const removed=await fetch('/sessions/'+session,{method:'DELETE'});if(!removed.ok){toast('History could not be cleared. Please retry.');return}recent=recent.filter(r=>r.id!==session);localStorage.setItem('mufti-recents',JSON.stringify(recent));renderRecent();$('#new-chat').click()};m.body.append(note)}}catch{}}
// opts.style overrides the Answer style box for one request (quick actions); opts.scope
// overrides the chapter focus (null = whole library).
async function send(question,opts={}){if(busy||!question.trim())return;busy=true;$('#send').disabled=true;$('#question').value='';view('chat');
const answerStyle=opts.style||$('#style').value||'detailed',useScope=opts.scope!==undefined?opts.scope:scope;
const shownQuestion=opts.label?opts.label+' · '+question:question;
message('user',shownQuestion);const m=message('assistant','');m.question=question;$('#activity').textContent=useScope?'Searching '+useScope.label+'…':'Searching the book…';scroll();
if(!recent.some(r=>r.id===session)){recent.unshift({id:session,title:question.slice(0,55)});recent=recent.slice(0,30);localStorage.setItem('mufti-recents',JSON.stringify(recent));renderRecent()}
try{const customKey=localStorage.getItem('mufti_custom_gemini_key')||'';const chatHeaders={'Content-Type':'application/json'};if(customKey)chatHeaders['X-Gemini-Key']=customKey;const r=await fetch('/chat',{method:'POST',headers:chatHeaders,body:JSON.stringify({question,session_id:session,language_hint:$('#language').value,stream:true,answer_style:answerStyle,scope:useScope?{book_id:useScope.book_id,page_start:useScope.page_start,page_end:useScope.page_end,label:useScope.label}:null})});if(!r.ok){const d=await r.json();throw Error(d.detail||'Server unavailable')}
const reader=r.body.getReader(),decoder=new TextDecoder();let buffer='',doneResult,draft='',draftTimer=null;
const paintDraft=()=>{draftTimer=null;if(doneResult)return;m.content.classList.add('drafting');m.content.dir=/[\u0600-\u06ff]/.test(draft.slice(0,300))?'rtl':'auto';renderMarkdown(m.content,draft,null);scroll()};
const scheduleDraft=()=>{if(!draftTimer)draftTimer=setTimeout(paintDraft,80)};
while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});let end;while((end=buffer.indexOf('\n\n'))>=0){const frame=buffer.slice(0,end);buffer=buffer.slice(end+2);const event=frame.match(/event: (.+)/)?.[1],raw=frame.match(/data: (.+)/)?.[1];if(!raw)continue;const data=JSON.parse(raw);if(event==='draft'){draft+=data.text;scheduleDraft()}else if(event==='draft_reset'){draft='';m.content.replaceChildren()}else if(event==='done'){doneResult=data;if(draftTimer)clearTimeout(draftTimer);m.content.classList.remove('drafting');m.body.querySelector('.message-label').textContent='Mufti AI';showAnswer(m,data);decorate(m,data)}else if(event==='status'){$('#activity').textContent=friendlyStatus(data);if(data.model&&data.state==='running')m.body.querySelector('.message-label').textContent='Mufti AI · '+data.provider+' / '+data.model+' · '+data.task;}else if(event==='error')throw Error(data.message)}}
if(!doneResult)throw Error('Connection ended before the verified answer was ready. Please try again.');
}catch(e){m.content.textContent=e.message;toast(e.message)}finally{busy=false;$('#send').disabled=false;$('#activity').textContent='';$('#question').focus();scroll()}}
$('#chat-form').onsubmit=e=>{e.preventDefault();send($('#question').value)};$('#question').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send($('#question').value)}};document.querySelectorAll('[data-question]').forEach(b=>b.onclick=()=>send(b.dataset.question));
// Voice input (rewritten 2026-11-17). Speak -> the text appears in the question box -> the reader
// checks or corrects it and presses Send. Nothing is sent automatically.
// The old version could not be stopped after an accidental tap: a second tap while the browser's
// permission prompt was open started a SECOND recorder, and the first one kept recording and then
// went straight into a minutes-long answer. Now there is one state machine:
//   idle -> starting (permission) -> recording -> transcribing -> idle
// Tap the mic again or press Stop to finish; Cancel or Esc discards at any stage; a tap shorter than
// 0.7 s is treated as accidental and discarded; recording stops by itself after 60 s.
const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
const voice={state:'idle',recorder:null,stream:null,chunks:[],started:0,timer:null,limit:null,discard:false,rec:null,before:'',abort:null};
const speechLocale={Hindi:'hi-IN',Urdu:'ur-PK',Hinglish:'hi-IN',English:'en-US'};
function voiceUI(state,label){
 voice.state=state;const bar=$('#voice-bar'),mic=$('#mic');bar.hidden=state==='idle';bar.dataset.state=state;
 mic.classList.toggle('recording',state==='recording');mic.setAttribute('aria-pressed',String(state==='recording'));
 mic.title=state==='recording'?'Stop recording':'Speak your question';
 $('#voice-label').textContent=label||'';$('#voice-stop').hidden=state!=='recording';$('#voice-cancel').hidden=state==='idle';
 $('#voice-time').hidden=state!=='recording';
 if(state!=='recording'){clearInterval(voice.timer);voice.timer=null}
}
function voiceClock(){const s=Math.floor((Date.now()-voice.started)/1000);$('#voice-time').textContent=Math.floor(s/60)+':'+String(s%60).padStart(2,'0')}
function insertTranscript(text){
 text=String(text||'').trim();if(!text){toast('No speech was recognised. Please try again.');return}
 const box=$('#question');box.value=(box.value.trim()?box.value.trim()+' ':'')+text;box.focus();box.setSelectionRange(box.value.length,box.value.length);
 toast('Check the text, then press Send ↑');
}
function releaseMic(){clearTimeout(voice.limit);voice.limit=null;if(voice.stream){voice.stream.getTracks().forEach(t=>t.stop());voice.stream=null}}
async function startVoice(){
 if(voice.state!=='idle'||busy)return;
 voice.discard=false;voiceUI('starting','Allow the microphone…');
 if(SpeechRecognition&&localStorage.getItem('mufti-browser-speech')==='true'){
  const rec=new SpeechRecognition();voice.rec=rec;voice.before=$('#question').value;
  const lang=$('#language').value;rec.lang=speechLocale[lang]||speechLocale[dirLang()]||'en-US';rec.interimResults=true;
  rec.onstart=()=>{voice.started=Date.now();voiceUI('recording','Listening — your words appear in the box');voiceClock();voice.timer=setInterval(voiceClock,500);voice.limit=setTimeout(stopVoice,60000)};
  rec.onresult=e=>{if(voice.discard)return;const said=Array.from(e.results).map(r=>r[0].transcript).join(' ');$('#question').value=(voice.before.trim()?voice.before.trim()+' ':'')+said};
  rec.onerror=e=>{if(e.error!=='aborted'&&e.error!=='no-speech')toast('Microphone: '+e.error)};
  rec.onend=()=>{clearTimeout(voice.limit);voice.rec=null;if(voice.discard){$('#question').value=voice.before;toast('Recording cancelled')}else if($('#question').value!==voice.before)toast('Check the text, then press Send ↑');voiceUI('idle');$('#question').focus()};
  try{rec.start()}catch(e){voice.rec=null;voiceUI('idle');toast('Microphone: '+e.message)}
  return;
 }
 try{voice.stream=await navigator.mediaDevices.getUserMedia({audio:true})}
 catch(e){voiceUI('idle');toast('Microphone access is unavailable: '+e.message);return}
 if(voice.state!=='starting'||voice.discard){releaseMic();voiceUI('idle');return}   // cancelled during the permission prompt
 voice.chunks=[];const recorder=new MediaRecorder(voice.stream);voice.recorder=recorder;
 recorder.ondataavailable=e=>{if(e.data&&e.data.size)voice.chunks.push(e.data)};
 recorder.onstop=()=>finishVoice(recorder);
 recorder.start();voice.started=Date.now();voiceUI('recording','Recording — speak now');voiceClock();voice.timer=setInterval(voiceClock,500);
 voice.limit=setTimeout(stopVoice,60000);
}
function stopVoice(){
 if(voice.state!=='recording')return;
 if(voice.rec){voice.rec.stop();return}
 if(voice.recorder&&voice.recorder.state==='recording')voice.recorder.stop();
}
function cancelVoice(){
 if(voice.state==='idle')return;
 voice.discard=true;
 if(voice.rec){voice.rec.abort();return}
 if(voice.state==='starting'){voiceUI('idle');toast('Recording cancelled');return}
 if(voice.state==='transcribing'){if(voice.abort)voice.abort.abort();return}
 if(voice.recorder&&voice.recorder.state==='recording')voice.recorder.stop();else{releaseMic();voiceUI('idle')}
}
async function finishVoice(recorder){
 releaseMic();const duration=Date.now()-voice.started;
 if(voice.discard){voiceUI('idle');toast('Recording cancelled');return}
 if(duration<700||!voice.chunks.length){voiceUI('idle');toast('Too short — nothing was recorded. Tap the mic and speak.');return}
 voiceUI('transcribing','Converting your voice to text…');
 const controller=new AbortController();voice.abort=controller;
 try{
  const form=new FormData();form.append('audio',new Blob(voice.chunks,{type:recorder.mimeType||'audio/webm'}),'recording.webm');form.append('language_hint',$('#language').value);
  const r=await fetch('/transcribe',{method:'POST',body:form,signal:controller.signal}),d=await r.json().catch(()=>({}));
  if(!r.ok)throw Error(d.detail||'Transcription failed. Please try again.');
  if(!voice.discard)insertTranscript(d.transcript);
 }catch(e){if(e.name==='AbortError')toast('Recording cancelled');else toast(e.message)}
 finally{voice.abort=null;voiceUI('idle')}
}
// A tap while recording finishes; a tap while the permission prompt is open cancels; a tap while
// converting to text is ignored (use Cancel), so a double-tap never throws a recording away.
$('#mic').onclick=()=>{if(voice.state==='recording')stopVoice();else if(voice.state==='idle')startVoice();else if(voice.state==='starting')cancelVoice()};
$('#voice-stop').onclick=stopVoice;$('#voice-cancel').onclick=cancelVoice;
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&voice.state!=='idle'&&!document.querySelector('dialog[open]')){e.preventDefault();cancelVoice()}});
let refreshBusy=false;async function refresh(){if(refreshBusy)return;refreshBusy=true;try{const [hr,br,pr]=await Promise.all([fetch('/health'),fetch('/books'),fetch('/settings/models')]);const h=await hr.json();books=await br.json();const p=await pr.json(),online=p.local_online;$('#connection').className='connection '+(online?'online':'');$('#connection').replaceChildren(element('i'),document.createTextNode(online?'Ollama connected':'Ollama offline'));$('#book-count').textContent=books.length;$('#current-book').textContent=books.length?books.map(bookName).join(' & '):'your local library';const box=$('#library-list');box.replaceChildren();if(!books.length)box.append(element('p','','Your PDF is being prepared. Indexing progress appears below.'));books.forEach(b=>{const card=element('article','book-card'),cover=element('div','book-cover');cover.append(element('span','','۞'),element('small','',bookName(b).toUpperCase()));const info=element('div','book-info');info.append(element("h3","",bookName(b)),element('p','',`${b.pages} pages · ${b.language||'Book'}\n${b.chunks} searchable passages`),element('p','',b.complete?'✓ Library ready':b.indexed?'◌ Indexed · some pages need review':'◌ OCR in progress'));const a=element('a','','Open book ↗');a.href=`/books/${b.id}/pdf`;a.target='_blank';a.rel='noopener';const chapters=element('button','chapters-button','☰ Chapters');chapters.type='button';chapters.onclick=()=>openOutline(b);info.append(a,chapters);card.append(cover,info);box.append(card)});const idx=h.index;if(!idx.running&&books.length&&books.every(b=>b.complete))idx.stage='Ready';$('#ingest').disabled=idx.running;$('#ingest-status').textContent=idx.running?idx.stage:idx.error||`${idx.stage}. ${books.reduce((total,b)=>total+(b.quality_warnings||0),0)} pages need review.`;if(!busy)showActiveModel(p);if(idx.running&&!busy)$('#activity').textContent='Preparing your library · '+idx.stage;else if(!busy)$('#activity').textContent='';}catch{$('#connection').textContent='Server offline'}finally{refreshBusy=false}}
$('#ingest').onclick=async()=>{try{const r=await fetch('/ingest',{method:'POST'});if(!r.ok)throw Error('Could not begin indexing');toast('Library indexing started');setTimeout(refresh,1000)}catch(e){toast(e.message)}};
refresh();loadSession();setInterval(refresh,15000);

function showActiveModel(data){
 const order=data.mode==='ollama'?['ollama']:data.mode==='auto'?[...data.cloud_order,'ollama']:[data.mode,...data.cloud_order.filter(p=>p!==data.mode),'ollama'];
 const state=data.provider_state||{};
 const first=order.find(p=>p==='ollama'||data.configured[p]);
 const expected=order.find(p=>state[p]?state[p].available:(p==='ollama'||data.configured[p]))||first;
 const selected=data.mode==='auto'?'Auto':providerNames[data.mode]+' / '+data.models[data.mode];
 // Never claim a provider is "Ready" just because a key exists: say what is actually expected to run.
 const label=state[expected]&&state[expected].available?'Expected to answer: ':'Likely fallback: ';
 let note='';
 if(first&&first!==expected&&state[first])note=' · '+providerNames[first]+': '+state[first].label;
 $('#active-model').textContent='Selected: '+selected+' · '+label+providerNames[expected]+' / '+data.models[expected]+note+'  · Change ↗';
 $('#active-model').title=Object.keys(state).map(p=>providerNames[p]+': '+state[p].label+(state[p].detail?' — '+state[p].detail:'')).join(String.fromCharCode(10))+String.fromCharCode(10)+'The model that actually ran is shown on each answer.';
}
async function refreshActiveModel(){try{showActiveModel(await modelRequest('GET'))}catch{$('#active-model').textContent='Model status unavailable · Open settings ↗'}}
$('#active-model').onclick=()=>$('#nav-models').click();
refreshActiveModel();

// ---------------------------------------------------------------- 2026-11-17: agent & GenAI upgrade
// Chapter focus ("scope"): the next questions search only inside one chapter/section.
let scope=null;
function setScope(next){scope=next;$('#scope-chip').hidden=!next;$('#scope-label').textContent=next?'Focus: '+next.label:'';if(next)toast('Next questions will search only in: '+next.label)}
$('#scope-clear').onclick=()=>{setScope(null);toast('Searching the whole library again')};

// Answer style is remembered on this device.
try{const saved=localStorage.getItem('mufti-style');if(saved&&[...$('#style').options].some(o=>o.value===saved))$('#style').value=saved}catch{}
$('#style').onchange=()=>{try{localStorage.setItem('mufti-style',$('#style').value)}catch{}};

// Question templates for the chapter explorer, in the reader's chosen language (Auto -> Hinglish).
const askTemplates={
 English:{explain:'Explain “{t}” in detail',summary:'Give a summary of “{t}”'},
 Hinglish:{explain:'“{t}” ko tafseel se samjhao',summary:'“{t}” ka khulasa batao'},
 Urdu:{explain:'«{t}» کو تفصیل سے سمجھائیے',summary:'«{t}» کا خلاصہ بیان کیجیے'},
 Hindi:{explain:'“{t}” को विस्तार से समझाइए',summary:'“{t}” का सारांश बताइए'}};
function askLanguage(){const v=$('#language').value;return askTemplates[v]?v:dirLang()}
// Language of the DIRECTIONS (welcome popup, tour, guide). The interface itself stays in English.
function dirLang(){try{const v=localStorage.getItem('mufti-ui-lang');return ['English','Hinglish','Urdu','Hindi'].includes(v)?v:'English'}catch{return 'English'}}
function askAbout(kind,title){return askTemplates[askLanguage()][kind].replace('{t}',title)}

async function openOutline(book){
 const panel=$('#outline-panel'),list=$('#outline-list');panel.hidden=false;$('#outline-title').textContent=bookName(book);list.replaceChildren(element('p','','Loading chapters…'));panel.scrollIntoView({behavior:'smooth',block:'start'});
 try{const r=await fetch(`/books/${book.id}/outline`);if(!r.ok)throw Error('Could not load the chapters');const data=await r.json();list.replaceChildren();
  if(!data.chapters.length){list.append(element('p','','This book has no chapter outline yet. Build it with: python -m app.ingestion.book_tree'));return}
  for(const ch of data.chapters){
   const d=element('details','outline-chapter'),sum=element('summary','');const t=element('span','outline-name',ch.title);t.dir='auto';sum.append(t,element('span','outline-pages',`PDF pages ${ch.page_start}–${ch.page_end}`+(ch.sections.length?` · ${ch.sections.length} sections`:'')));d.append(sum);
   const target={book_id:book.id,page_start:ch.page_start,page_end:ch.page_end,label:(ch.topic||ch.title)+' ('+bookName(book)+')'};
   if(ch.is_topic)d.append(outlineActions(ch.topic||ch.title,target));
   if(ch.sections.length){const ul=element('ul','outline-sections');for(const s of ch.sections){const li=element('li',''),name=element('span','outline-name',s.title);name.dir='auto';li.append(name,element('span','outline-pages',`p. ${s.page_start}–${s.page_end}`),outlineActions(s.topic||s.title,{book_id:book.id,page_start:s.page_start,page_end:s.page_end,label:(s.topic||s.title)+' ('+bookName(book)+')'}));ul.append(li)}d.append(ul)}
   list.append(d)}
 }catch(e){list.replaceChildren(element('p','',e.message||'Could not load the chapters.'))}
}
function outlineActions(title,target){
 const row=element('div','outline-actions');
 const explain=element('button','outline-btn','Explain');explain.type='button';explain.onclick=()=>{view('chat');send(askAbout('explain',title),{scope:target,style:'detailed'})};
 const summary=element('button','outline-btn','Summary');summary.type='button';summary.onclick=()=>{view('chat');send(askAbout('summary',title),{scope:target,style:'points'})};
 const focus=element('button','outline-btn ghost','◎ Focus');focus.type='button';focus.title='Keep your next questions inside this part of the book';focus.onclick=()=>{setScope(target);view('chat');$('#question').focus()};
 row.append(explain,summary,focus);return row;
}
$('#outline-close').onclick=()=>{$('#outline-panel').hidden=true};

// Starter topics on the welcome screen, built from the books' own chapter titles.
async function loadStarters(){
 try{const r=await fetch('/suggestions?language='+askLanguage());if(!r.ok)return;const data=await r.json(),list=$('#starter-list');list.replaceChildren();
  for(const q of (data.questions||[]).slice(0,6)){const b=element('button','followup-chip',q);b.type='button';b.dir='auto';b.onclick=()=>send(q);list.append(b)}
  $('#starter-topics').hidden=!list.childElementCount}catch{}
}
$('#language').addEventListener('change',loadStarters);loadStarters();

// Guide: how to use + setup check + shortcuts. Opens by itself on the first visit.
function guideTab(name){document.querySelectorAll('.guide-tab').forEach(t=>{const on=t.dataset.tab===name;t.classList.toggle('active',on);t.setAttribute('aria-selected',on)});document.querySelectorAll('.guide-panel').forEach(p=>p.hidden=p.dataset.panel!==name);if(name==='setup')loadSetup()}
document.querySelectorAll('.guide-tab').forEach(t=>t.onclick=()=>guideTab(t.dataset.tab));
function openGuide(tab='use'){$('#sidebar').classList.remove('open');if(!$('#guide-dialog').open)$('#guide-dialog').showModal();renderGuide();guideTab(tab)}
$('#guide').onclick=()=>openGuide();$('#close-guide').onclick=()=>$('#guide-dialog').close();
$('#guide-start').onclick=()=>{$('#guide-dialog').close();$('#question').focus()};
$('#guide-dialog').addEventListener('click',e=>{if(e.target===$('#guide-dialog'))$('#guide-dialog').close()});
$('#setup-refresh').onclick=()=>loadSetup();
async function loadSetup(){
 const box=$('#setup-list');box.replaceChildren(element('p','',tr('checking')));
 try{const r=await fetch('/health/setup');if(!r.ok)throw Error('Setup check unavailable');const data=await r.json();box.replaceChildren();
  const icons={ok:'✓',warn:'!',fail:'✕'};
  box.append(element('p','setup-summary '+data.status,tr('setupSummary')[data.status]));
  for(const c of data.checks){const row=element('div','setup-item '+c.status);row.append(element('span','setup-icon',icons[c.status]||'•'));const text=element('div','');text.append(element('b','',c.label),element('p','',c.detail));if(c.status!=='ok'&&c.fix){const hinglish=dirLang()==='Hinglish'&&c.fix_hinglish;text.append(element('p','setup-fix',tr('fixLabel')+' '+(hinglish?c.fix_hinglish:c.fix)))}row.append(text);box.append(row)}
 }catch(e){box.replaceChildren(element('p','',(e.message||'Setup check unavailable')+'. Is the server running? Run .\\doctor.ps1 in PowerShell for the same check.'))}
}
// First visit: welcome popup with directions-language choice and the arrow tour (frontend/tour.js).

// Keyboard shortcuts (ignored while typing, except Alt combinations).
document.addEventListener('keydown',e=>{
 const typing=/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName||'');
 if(e.altKey&&!e.ctrlKey&&!e.metaKey){const k=e.key.toLowerCase();if(k==='n'){e.preventDefault();$('#new-chat').click()}else if(k==='l'){e.preventDefault();view('library')}else if(k==='g'){e.preventDefault();openGuide()}return}
 if(!typing&&e.key==='/'&&!document.querySelector('dialog[open]')){e.preventDefault();view('chat');$('#question').focus()}
});

// ---------------------------------------------------------------- loop 1 (2026-11-17): answer feedback
// 👍 / 👎 on every answer. 👎 asks why (chips + optional note). Stored locally in
// data/feedback/feedback.jsonl; eval/feedback_to_cases.py turns 👎 into draft benchmark cases.
const feedbackReasons=[['wrong','Wrong information'],['incomplete','Incomplete'],['not_found_but_in_book','Book has it, but not found'],['bad_reference','Wrong page / reference'],['wrong_language','Wrong language'],['too_long','Too long'],['too_short','Too short'],['other','Other']];
function feedbackPayload(m,result,rating,reasons=[],note=''){
 return {session_id:session,rating,question:m.question,answer:stripMarkers(result.answer||'').slice(0,1500),reasons,note,
  pages:(result.citations||[]).map(c=>c.page).slice(0,40),book_ids:[...new Set((result.citations||[]).map(c=>c.book_id))].slice(0,10),
  language:result.language||'',answer_style:result.answer_style||'',reason_code:result.reason_code||'',answering_model:result.answering_model||result.model_used||'',verification:result.verification||''};
}
async function sendFeedback(payload){const r=await fetch('/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!r.ok)throw Error('Feedback could not be saved');return r.json()}
function feedbackControls(m,result,meta){
 const up=element('button','read-aloud feedback-btn','👍'),down=element('button','read-aloud feedback-btn','👎');
 up.type=down.type='button';up.title='Helpful answer';down.title='Something is wrong — tell us what';up.setAttribute('aria-label','Helpful answer');down.setAttribute('aria-label','Report a problem with this answer');
 const done=text=>{up.disabled=down.disabled=true;meta.querySelector('.feedback-done')?.remove();meta.append(element('span','feedback-done',text))};
 up.onclick=async()=>{try{await sendFeedback(feedbackPayload(m,result,'up'));up.classList.add('chosen');done('Thanks!')}catch(e){toast(e.message)}};
 down.onclick=()=>{
  if(m.body.querySelector('.feedback-form'))return;
  down.classList.add('chosen');
  const form=element('div','feedback-form');form.append(element('p','feedback-title','What was wrong? (choose one or more)'));
  const chips=element('div','feedback-reasons'),chosen=new Set();
  for(const [code,label] of feedbackReasons){const b=element('button','feedback-reason',label);b.type='button';b.onclick=()=>{chosen.has(code)?chosen.delete(code):chosen.add(code);b.classList.toggle('active',chosen.has(code))};chips.append(b)}
  const note=element('textarea','feedback-note');note.maxLength=1000;note.rows=2;note.placeholder='Optional: what should the answer say, or which page has it?';
  const row=element('div','feedback-actions'),cancel=element('button','model-secondary','Cancel'),save=element('button','model-save','Send feedback');cancel.type=save.type='button';
  cancel.onclick=()=>{form.remove();down.classList.remove('chosen')};
  save.onclick=async()=>{save.disabled=true;try{await sendFeedback(feedbackPayload(m,result,'down',[...chosen],note.value.trim()));form.remove();done('Thanks — this will be used to improve answers.')}catch(e){save.disabled=false;toast(e.message)}};
  row.append(cancel,save);form.append(chips,note,row);meta.after(form);note.focus();
 };
 meta.append(up,down);
}

// ---------------------------------------------------------------- loop 2 (2026-11-17): saved answers
// ☆ Save keeps an answer with its citations in data/saved/saved.json (this computer only), so it
// survives "Delete this conversation". The Saved answers view lists, searches, opens and removes them.
let savedItems=[];
function saveControl(m,result,meta){
 const b=element('button','read-aloud save-btn','☆ Save');b.type='button';b.title='Keep this answer in Saved answers';
 b.onclick=async()=>{
  if(b.dataset.id){view('saved');return}
  b.disabled=true;
  try{
   const payload={question:m.question,answer:stripMarkers(result.answer||''),answer_format:result.answer_format||'text',
    citations:(result.citations||[]).slice(0,60).map(c=>({id:c.id,book_id:c.book_id,book_title:c.book_title||'',page:c.page,printed_label:c.printed_label??null,excerpt:String(c.excerpt||'').slice(0,2000)})),
    language:result.language||'',verification:result.verification||'',answering_model:result.answering_model||result.model_used||'',answer_style:result.answer_style||'',session_id:session};
   const r=await fetch('/saved',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
   const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'Could not save this answer');
   b.dataset.id=d.id;b.textContent='★ Saved';b.classList.add('chosen');b.title='Open Saved answers';
   toast(d.created?'Saved — find it under ★ Saved answers':'Already in Saved answers');refreshSavedCount();
  }catch(e){toast(e.message)}finally{b.disabled=false}
 };
 meta.append(b);
}
async function refreshSavedCount(){try{const r=await fetch('/saved');if(!r.ok)return;savedItems=await r.json();$('#saved-count').textContent=savedItems.length}catch{}}
async function loadSaved(){
 const list=$('#saved-list');list.replaceChildren(element('p','','Loading…'));
 try{const r=await fetch('/saved');if(!r.ok)throw Error('Saved answers are unavailable');savedItems=await r.json();$('#saved-count').textContent=savedItems.length;renderSaved()}
 catch(e){list.replaceChildren(element('p','',e.message))}
}
function renderSaved(){
 const list=$('#saved-list'),q=$('#saved-search').value.trim().toLowerCase();list.replaceChildren();
 const items=savedItems.filter(i=>!q||(i.question+' '+i.preview).toLowerCase().includes(q));
 if(!savedItems.length){list.append(element('p','saved-empty','Nothing saved yet. Press ☆ Save under any answer to keep it here.'));return}
 if(!items.length){list.append(element('p','saved-empty','No saved answer matches your search.'));return}
 for(const item of items){
  const card=element('article','saved-card'),title=element('h3','',item.question);title.dir='auto';
  const meta=element('p','saved-meta',new Date(item.saved_at).toLocaleString()+(item.pages?.length?' · pages '+item.pages.join(', '):'')+(item.verification==='audited'?' · ✓ fact-checked':''));
  const preview=element('p','saved-preview',item.preview+(item.preview.length>=220?'…':''));preview.dir='auto';
  const actions=element('div','saved-actions'),open=element('button','outline-btn','Open'),del=element('button','outline-btn ghost','Delete');open.type=del.type='button';
  open.onclick=()=>openSaved(item.id);
  // Two-step delete instead of confirm(): the first click asks, the second removes.
  del.onclick=async()=>{if(del.dataset.armed!=='1'){del.dataset.armed='1';del.textContent='Click again to delete';setTimeout(()=>{if(del.isConnected){del.dataset.armed='';del.textContent='Delete'}},4000);return}
   try{const r=await fetch('/saved/'+item.id,{method:'DELETE'});if(!r.ok)throw Error('Could not delete');savedItems=savedItems.filter(i=>i.id!==item.id);$('#saved-count').textContent=savedItems.length;renderSaved();toast('Removed from Saved answers')}catch(e){toast(e.message)}};
  actions.append(open,del);card.append(title,meta,preview,actions);list.append(card);
 }
}
async function openSaved(id){
 $('#source-title').textContent='Saved answer';const box=$('#source-content');box.replaceChildren(element('p','','Loading…'));$('#source-dialog').showModal();
 try{const r=await fetch('/saved/'+id);if(!r.ok)throw Error('Saved answer not found');const item=await r.json();box.replaceChildren();
  const h=element('h3','saved-open-title',item.question);h.dir='auto';const body=element('div','text');
  if(item.answer_format==='markdown')renderMarkdown(body,item.answer,item.citations||[]);else body.textContent=item.answer;
  body.dir=item.language==='Urdu'?'rtl':'auto';box.append(h,body);
  if(item.citations?.length){const list=element('div','citation-list');for(const c of item.citations){const d=element('details','citation'),s=element('summary','',`[${c.id}] ${niceTitle(c.book_title)} · PDF page ${c.page}`),qq=element('blockquote','',c.excerpt),btn=element('button','','View original page ↗');qq.dir='auto';btn.onclick=()=>source(c);d.append(s,qq,btn);list.append(d)}box.append(list)}
  const actions=element('div','saved-actions'),dl=element('button','outline-btn','⤓ Download');dl.type='button';dl.onclick=()=>downloadAnswer(item.question,{...item,answer:item.answer});actions.append(dl);box.append(actions);
 }catch(e){box.replaceChildren(element('p','',e.message))}
}
$('#nav-saved').onclick=()=>view('saved');$('#saved-search').oninput=renderSaved;refreshSavedCount();

// ---------------------------------------------------------------- loop 3 (2026-11-17): Quiz me
// A few multiple-choice questions built by the server from THIS answer's checked, cited sentences
// (app/agents/quiz_agent.py). Each question links to the book page of the statement it tests.
const quizText={English:{title:'Test yourself',loading:'Making a short quiz from this answer…',right:'✓ Correct',wrong:'✗ Not quite — the answer is: ',score:'Score',again:'New quiz',close:'Close',why:'Why',source:'Source'},
 Hinglish:{title:'Khud ko test karein',loading:'Is jawab se chhota quiz ban raha hai…',right:'✓ Sahi',wrong:'✗ Sahi jawab: ',score:'Score',again:'Naya quiz',close:'Band karein',why:'Kyun',source:'Hawala'},
 Urdu:{title:'اپنا امتحان لیجیے',loading:'اس جواب سے مختصر کوئز بن رہا ہے…',right:'✓ درست',wrong:'✗ درست جواب: ',score:'نتیجہ',again:'نیا کوئز',close:'بند کیجیے',why:'وجہ',source:'حوالہ'},
 Hindi:{title:'ख़ुद को परखिए',loading:'इस जवाब से छोटा क्विज़ बन रहा है…',right:'✓ सही',wrong:'✗ सही जवाब: ',score:'स्कोर',again:'नया क्विज़',close:'बंद करें',why:'क्यों',source:'हवाला'}};
function quizControl(m,result,meta){
 const b=element('button','read-aloud quiz-btn','🧠 Quiz me');b.type='button';b.title='A short multiple-choice quiz from this answer (uses one AI call)';
 b.onclick=()=>runQuiz(m,result,b);meta.append(b);
}
async function runQuiz(m,result,button){
 const words=quizText[result.language]||quizText.English;
 m.body.querySelector('.quiz-card')?.remove();
 const card=element('section','quiz-card');card.dir=result.language==='Urdu'?'rtl':'auto';
 card.append(element('h4','quiz-title','🧠 '+words.title),element('p','quiz-status',words.loading));
 m.body.querySelector('.response-meta').after(card);card.scrollIntoView({behavior:'smooth',block:'nearest'});button.disabled=true;
 try{
  const r=await fetch('/quiz',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:session,question:m.question,count:4})});
  const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'The quiz could not be made.');
  card.querySelector('.quiz-status').remove();
  let answered=0,correctCount=0;const score=element('p','quiz-score');
  d.questions.forEach((q,qi)=>{
   const block=element('div','quiz-q'),title=element('p','quiz-question',(qi+1)+'. '+q.question),opts=element('div','quiz-options'),feedback=element('div','quiz-feedback');
   q.options.forEach((o,oi)=>{const ob=element('button','quiz-option',o);ob.type='button';ob.onclick=()=>{
     if(block.dataset.done)return;block.dataset.done='1';answered++;const ok=oi===q.correct;if(ok)correctCount++;
     ob.classList.add(ok?'right':'wrong');opts.children[q.correct].classList.add('right');[...opts.children].forEach(x=>x.disabled=true);
     feedback.append(element('p',ok?'quiz-ok':'quiz-no',ok?words.right:words.wrong+q.options[q.correct]),element('p','quiz-why',words.why+': '+q.explanation));
     const src=element('div','quiz-sources');for(const s of q.sources||[]){const chip=element('button','cite-chip',String(s.id));chip.type='button';chip.title=`${niceTitle(s.book_title)} · PDF page ${s.page}`;chip.onclick=()=>source({...s,excerpt:q.statement});src.append(chip)}
     if(src.childElementCount)feedback.append(element('span','quiz-src-label',words.source+': '),src);
     score.textContent=`${words.score}: ${correctCount} / ${answered}`+(answered===d.questions.length?` (${d.questions.length})`:'');
    };opts.append(ob)});
   block.append(title,opts,feedback);card.append(block);
  });
  const actions=element('div','quiz-actions'),again=element('button','outline-btn',words.again),close=element('button','outline-btn ghost',words.close);again.type=close.type='button';
  again.onclick=()=>runQuiz(m,result,button);close.onclick=()=>card.remove();actions.append(score,again,close);card.append(actions);
 }catch(e){card.querySelector('.quiz-status').textContent=e.message}finally{button.disabled=false}
}

// ---------------------------------------------------------------- loop 5 (2026-11-18): Topic index
// Reviewed key concepts (data/concept-lexicon.json, four scripts) + every chapter/section of every
// book with page ranges (GET /topics). Search runs in the browser across titles and concept forms;
// nothing is generated here — Explain/Summary/Focus ask the book through the normal pipeline.
let topicData=null;
const fold=t=>String(t||'').toLowerCase().normalize('NFKD').replace(/[̀-ًͯ-ٰٟ]/g,'');
async function loadTopics(){
 if(!topicData){$('#topics-list').replaceChildren(element('p','','Loading topics…'));
  try{const r=await fetch('/topics');if(!r.ok)throw Error('Topic index unavailable');topicData=await r.json()}catch(e){$('#topics-list').replaceChildren(element('p','',e.message));return}}
 renderTopics();
}
function conceptLabel(c){const lang=askLanguage();return (c.forms[lang]||c.forms.English||Object.values(c.forms)[0]||[c.id])[0]}
function renderTopics(){
 if(!topicData)return;const q=fold($('#topics-search').value.trim());
 const conceptBox=$('#topics-concepts');conceptBox.replaceChildren();
 const concepts=topicData.concepts.filter(c=>!q||fold(Object.values(c.forms).flat().join(' ')+' '+c.id.replace(/_/g,' ')).includes(q));
 for(const c of concepts){
  const card=element('div','topic-concept'),label=conceptLabel(c),name=element('b','',label);name.dir='auto';
  const other=Object.entries(c.forms).filter(([l])=>l!==askLanguage()).map(([,f])=>f[0]).filter(Boolean).slice(0,3).join(' · ');
  const alt=element('small','',other);alt.dir='auto';
  const ask=element('button','outline-btn','Explain');ask.type='button';ask.onclick=()=>{view('chat');send(askAbout('explain',label),{scope:null,style:'detailed'})};
  card.append(name,alt,ask);conceptBox.append(card);
 }
 if(!concepts.length)conceptBox.append(element('p','saved-empty','No key concept matches.'));
 const list=$('#topics-list');list.replaceChildren();
 // Cross-script search: a matched concept contributes all its reviewed forms, so "equality" also finds
 // the Urdu section titles that say مساوات (book 1's outline is in Urdu).
 const terms=q?[q,...concepts.flatMap(c=>Object.values(c.forms).flat()).map(fold).filter(t=>t.length>2)]:[];
 const sections=topicData.sections.filter(s=>{if(!q)return true;const hay=fold(s.title+' '+s.chapter+' '+s.book_title);return terms.some(t=>hay.includes(t))});
 $('#topics-count').textContent=`(${sections.length})`;
 let currentBook='';
 for(const s of sections.slice(0,250)){
  if(s.book_id!==currentBook){currentBook=s.book_id;list.append(element('h3','topics-book',s.book_title))}
  const row=element('div','topic-row'+(s.kind==='chapter'?' chapter':'')),info=element('div','topic-info'),name=element('span','outline-name',s.topic);name.dir='auto';
  info.append(name,element('span','outline-pages',`${s.kind==='chapter'?'Chapter · ':''}PDF pages ${s.page_start}–${s.page_end}`));
  if(s.chapter){const ch=element('small','topic-chapter',s.chapter);ch.dir='auto';info.append(ch)}
  row.append(info,outlineActions(s.topic,{book_id:s.book_id,page_start:s.page_start,page_end:s.page_end,label:s.topic+' ('+s.book_title+')'}));list.append(row);
 }
 if(sections.length>250)list.append(element('p','saved-empty',`Showing 250 of ${sections.length} — type to narrow the list.`));
 if(!sections.length)list.append(element('p','saved-empty','No chapter or section title matches. Try another word, or ask the question directly — the search reads the full text of the books.'));
}
$('#nav-topics').onclick=()=>view('topics');$('#topics-search').oninput=renderTopics;

// ---------------------------------------------------------------- loop 8 (2026-11-18): photo & file input
// 📷 camera, 📎 upload, drag & drop or Ctrl+V paste → POST /extract (text read ON THIS COMPUTER) →
// the reader checks the text, then: Explain this (normal grounded answer, only from the books),
// Find in my books (POST /find, no model call: which book & page), or Put in question box.
const attachText={
 English:{explain:'Explain this passage in the light of my books:',find:'🔍 Find in my books',ask:'✎ Explain this',box:'Put in question box',reading:'Reading the text on this computer…',found:'Found in your books',none:'This text was not found in your books. The answers here come only from your library.',explainPage:'Explain this page',view:'View page',strong:'Strong match',possible:'Possible match',weak:'Weak match'},
 Hinglish:{explain:'Is ibarat ko meri kitabon ki roshni mein samjhao:',find:'🔍 Kitab mein dhoondo',ask:'✎ Samjhao',box:'Sawal box mein daalo',reading:'Text is computer par padha ja raha hai…',found:'Aapki kitabon mein mila',none:'Ye ibarat aapki kitabon mein nahi mili. Jawab sirf aapki library se aate hain.',explainPage:'Ye page samjhao',view:'Page dekho',strong:'Pakka match',possible:'Mumkin match',weak:'Kamzor match'},
 Urdu:{explain:'اس عبارت کو میری کتابوں کی روشنی میں سمجھائیے:',find:'🔍 کتاب میں تلاش',ask:'✎ سمجھائیے',box:'سوال کے خانے میں',reading:'متن اسی کمپیوٹر پر پڑھا جا رہا ہے…',found:'آپ کی کتابوں میں ملا',none:'یہ عبارت آپ کی کتابوں میں نہیں ملی۔ جوابات صرف آپ کی لائبریری سے آتے ہیں۔',explainPage:'یہ صفحہ سمجھائیے',view:'صفحہ دیکھیے',strong:'مضبوط مطابقت',possible:'ممکنہ مطابقت',weak:'کمزور مطابقت'},
 Hindi:{explain:'इस इबारत को मेरी किताबों की रोशनी में समझाइए:',find:'🔍 किताब में खोजें',ask:'✎ समझाइए',box:'सवाल बॉक्स में डालें',reading:'टेक्स्ट इसी कंप्यूटर पर पढ़ा जा रहा है…',found:'आपकी किताबों में मिला',none:'यह इबारत आपकी किताबों में नहीं मिली। जवाब सिर्फ़ आपकी लाइब्रेरी से आते हैं।',explainPage:'यह पेज समझाइए',view:'पेज देखें',strong:'पक्का मेल',possible:'संभावित मेल',weak:'कमज़ोर मेल'}};
function aw(){return attachText[askLanguage()]||attachText.English}
const MAX_UPLOAD=15*1024*1024;let attachObjectUrl=null;
function closeAttach(){$('#attach-card').hidden=true;$('#attach-card').replaceChildren();if(attachObjectUrl){URL.revokeObjectURL(attachObjectUrl);attachObjectUrl=null}}
async function handleFile(file,ocrLanguage='auto'){
 if(!file)return;
 const ok=/^image\//.test(file.type)||/\.(pdf|txt|md|png|jpe?g|webp|bmp|gif|tiff?)$/i.test(file.name);
 if(!ok){toast('Use a photo (JPG/PNG), a PDF, or a .txt/.md file');return}
 if(file.size>MAX_UPLOAD){toast('The file is larger than 15 MB');return}
 view('chat');closeAttach();const card=$('#attach-card');card.hidden=false;
 const head=element('div','attach-head');
 if(/^image\//.test(file.type)){attachObjectUrl=URL.createObjectURL(file);const img=element('img','attach-thumb');img.src=attachObjectUrl;img.alt='Your photo';head.append(img)}
 else head.append(element('span','attach-icon',file.name.toLowerCase().endsWith('.pdf')?'📕':'📄'));
 const meta=element('div','attach-meta');meta.append(element('b','',file.name||'photo'),element('small','',aw().reading));head.append(meta);
 const close=element('button','icon-button','×');close.type='button';close.setAttribute('aria-label','Remove attachment');close.onclick=closeAttach;head.append(close);
 card.append(head);
 try{
  const form=new FormData();form.append('file',file,file.name||'photo.jpg');form.append('language',ocrLanguage);
  const r=await fetch('/extract',{method:'POST',body:form});const d=await r.json().catch(()=>({}));
  if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'The text could not be read.');
  meta.querySelector('small').textContent=`${d.chars} characters${d.ocr?' · read with OCR':''}${d.pages>1?' · '+d.pages+' pages':''}${d.truncated?' · shortened':''} · ${d.seconds}s — check and correct the text if needed`;
  const area=element('textarea','attach-text');area.value=d.text;area.rows=5;area.dir='auto';area.setAttribute('aria-label','Text read from your file');
  const langRow=element('div','attach-lang');langRow.append(element('small','','Text language:'));
  for(const [code,label] of [['auto','Auto'],['Urdu','اردو'],['Arabic','عربی'],['English','English'],['Hindi','हिन्दी']]){const b=element('button','dir-lang-option'+(code===ocrLanguage?' active':''),label);b.type='button';b.title='Read the photo again as '+label;b.onclick=()=>handleFile(file,code);langRow.append(b)}
  const actions=element('div','attach-actions'),explain=element('button','model-save',aw().ask),find=element('button','model-secondary',aw().find),box=element('button','model-secondary',aw().box);
  [explain,find,box].forEach(b=>b.type='button');
  const text=()=>area.value.trim();
  explain.onclick=()=>{if(!text())return;const q=aw().explain+'\n\n“'+text().slice(0,1500)+'”';closeAttach();send(q,{label:'📎'})};
  find.onclick=()=>{if(text())findInBooks(text())};
  box.onclick=()=>{const q=$('#question');q.value=(q.value.trim()?q.value.trim()+'\n':'')+text().slice(0,3000);closeAttach();q.focus()};
  actions.append(explain,find,box);card.append(area,langRow,actions);
 }catch(e){meta.querySelector('small').textContent=e.message;meta.querySelector('small').classList.add('attach-error')}
}
async function findInBooks(text){
 const words=aw();closeAttach();message('user','🔍 '+text.slice(0,240)+(text.length>240?'…':''));const m=message('assistant',words.reading);scroll();
 try{const r=await fetch('/find',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,limit:5})});const d=await r.json().catch(()=>({}));
  if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'Search failed');
  m.content.replaceChildren();
  if(!d.results.length){m.content.textContent=words.none;return}
  m.content.append(element('p','find-title',words.found+' — '+d.results.length));
  const list=element('div','citation-list');
  for(const hit of d.results){
   const row=element('div','citation find-hit'),title=element('div','find-head');
   title.append(element('b','',`${niceTitle(hit.book_title)} · PDF page ${hit.page}${hit.printed_label&&hit.printed_label!==hit.page?' (printed '+hit.printed_label+')':''}`),element('span','find-strength '+hit.strength,words[hit.strength]||hit.strength));
   const quote=element('blockquote','',hit.excerpt);quote.dir='auto';
   const actions=element('div','saved-actions'),viewPage=element('button','outline-btn ghost',words.view),explainPage=element('button','outline-btn',words.explainPage);viewPage.type=explainPage.type='button';
   viewPage.onclick=()=>source({...hit,excerpt:hit.excerpt});
   explainPage.onclick=()=>send(aw().explain+'\n\n“'+text.slice(0,600)+'”',{scope:{book_id:hit.book_id,page_start:Math.max(1,hit.page-1),page_end:hit.page+1,label:`PDF page ${hit.page} (${niceTitle(hit.book_title)})`},label:'📎'});
   actions.append(viewPage,explainPage);row.append(title,quote,actions);list.append(row);
  }
  m.content.append(list);m.content.append(element('p','answer-reason','No AI was used for this search — it is the same book search the answers use.'));
 }catch(e){m.content.textContent=e.message}
 scroll();
}
$('#attach').onclick=()=>$('#attach-input').click();
$('#attach-input').onchange=e=>{const f=e.target.files[0];e.target.value='';handleFile(f)};
// Drag & drop anywhere on the chat; paste an image with Ctrl+V into the question box.
let dragDepth=0;
const chatView=$('#chat-view');
chatView.addEventListener('dragenter',e=>{if([...e.dataTransfer.types].includes('Files')){e.preventDefault();dragDepth++;$('#drop-overlay').hidden=false}});
chatView.addEventListener('dragover',e=>{if([...e.dataTransfer.types].includes('Files'))e.preventDefault()});
chatView.addEventListener('dragleave',()=>{dragDepth=Math.max(0,dragDepth-1);if(!dragDepth)$('#drop-overlay').hidden=true});
chatView.addEventListener('drop',e=>{e.preventDefault();dragDepth=0;$('#drop-overlay').hidden=true;const f=e.dataTransfer.files[0];if(f)handleFile(f)});
$('#question').addEventListener('paste',e=>{const item=[...(e.clipboardData?.items||[])].find(i=>i.type.startsWith('image/'));if(item){e.preventDefault();const f=item.getAsFile();handleFile(new File([f],'pasted-image.png',{type:f.type}))}});
// Camera: live preview, front/back switch, capture a frame as a JPEG.
let cameraStream=null,cameraFacing='environment';
async function openCamera(){
 if(!navigator.mediaDevices?.getUserMedia){toast('This browser cannot use the camera — use 📎 to upload a photo');return}
 try{cameraStream?.getTracks().forEach(t=>t.stop());cameraStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:cameraFacing,width:{ideal:1920},height:{ideal:1080}},audio:false});
  $('#camera-video').srcObject=cameraStream;if(!$('#camera-dialog').open)$('#camera-dialog').showModal()}
 catch(e){toast('Camera unavailable: '+e.message)}
}
function closeCamera(){cameraStream?.getTracks().forEach(t=>t.stop());cameraStream=null;$('#camera-video').srcObject=null;if($('#camera-dialog').open)$('#camera-dialog').close()}
$('#camera').onclick=openCamera;$('#camera-close').onclick=closeCamera;$('#camera-dialog').addEventListener('close',()=>{cameraStream?.getTracks().forEach(t=>t.stop());cameraStream=null});
$('#camera-switch').onclick=()=>{cameraFacing=cameraFacing==='environment'?'user':'environment';openCamera()};
$('#camera-capture').onclick=()=>{const v=$('#camera-video');if(!v.videoWidth){toast('The camera is not ready yet');return}
 const c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);
 c.toBlob(b=>{closeCamera();if(b)handleFile(new File([b],'camera-photo.jpg',{type:'image/jpeg'}))},'image/jpeg',.92)};
