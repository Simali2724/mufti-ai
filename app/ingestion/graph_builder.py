import re,sqlite3
from app.core.config import INDEX
from app.ingestion.normalize import tokens
STOP={'اور','کے','کی','کا','ہے','ہیں','میں','سے','کو','نے','پر','یہ','اس','ان','بھی','ایک','وہ','تھا','تو','کہ','تھی','ہو','تھے'}
def build_graph(chunks):
    with sqlite3.connect(INDEX/'knowledge.sqlite') as db:
        db.execute('CREATE TABLE IF NOT EXISTS links(term TEXT,chunk_id TEXT,kind TEXT, PRIMARY KEY(term,chunk_id))')
        db.execute('DELETE FROM links')
        for c in chunks:
            terms={t for t in tokens(c['text']) if len(t)>3 and t not in STOP}
            terms|=set(re.findall(r'\b\d{1,3}:\d{1,3}\b',c['text']))
            db.executemany('INSERT OR IGNORE INTO links VALUES(?,?,?)',[(t,c['id'],'reference' if ':' in t else 'keyword') for t in terms])
def related(query,limit=30):
    if not (INDEX/'knowledge.sqlite').exists(): return []
    terms=tokens(query)
    if not terms: return []
    with sqlite3.connect(INDEX/'knowledge.sqlite') as db:
        rows=db.execute('SELECT chunk_id,COUNT(*) n FROM links WHERE term IN ('+','.join('?' for _ in terms)+') GROUP BY chunk_id ORDER BY n DESC LIMIT ?',[*terms,limit]).fetchall()
        return [r[0] for r in rows]
