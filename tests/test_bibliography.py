import pytest
from app.agents import bibliography as b
from app.agents.graph import build_graph,ask
from app.core.schemas import ChatRequest
from langgraph.checkpoint.memory import InMemorySaver

@pytest.mark.parametrize('question,field',[
 ('Who is author of Muaddima seerat ur Rasool','author'),
 ('Who wrote this book?','author'),('Is kitab kisne likhi?','author'),
 ('اس کتاب کا مصنف کون ہے؟','author'),('इस किताब के लेखक कौन हैं?','author'),
 ('Who published this book?','publisher'),('What is the ISBN of this book?','isbn'),
 ('When was this book first published?','first_published')])
def test_metadata_intents(question,field):assert b.identify(question)[0]==field

@pytest.mark.parametrize('q',['What does the author say about prayer?','Who is Muhammad?','Explain gender equality','Who wrote this book and explain its theology'])
def test_does_not_replace_substantive_answers(q):
 field,title=b.identify(q)
 assert field is None or not b.title_matches(title,{'title':'Muqaddima Seerat ur Rasool'},{'aliases':[]})

def test_wrong_book_is_not_mapped():
 assert not b.title_matches('Harry Potter',{'title':'Muqaddima Seerat ur Rasool'},{'aliases':[]})
 assert b.title_matches('Muaddima seerat ur Rasool',{'title':'Muqaddima Seerat ur Rasool'},{'aliases':[]})

@pytest.mark.asyncio
@pytest.mark.parametrize('language,name',[('English','Dr. Muhammad'),('Urdu','محمد طاہر'),('Hindi','मुहम्मद')])
async def test_fact_is_cited_without_model_and_survives_history(monkeypatch,language,name):
 book={'id':'test','title':'Test book'}
 fact={'page':3,'quote':'تصنیف : ڈاکٹر محمد طاہر القادری','values':{'English':'Dr. Muhammad Tahir-ul-Qadri','Urdu':'ڈاکٹر محمد طاہر القادری','Hindi':'डॉ. मुहम्मद ताहिर-उल-क़ादरी'}}
 monkeypatch.setattr(b,'lookup',lambda q:(book,'author',fact))
 from app.agents import language_agent
 async def forbidden(*a):raise AssertionError('Bibliographic fact must not invoke generation')
 monkeypatch.setattr(language_agent,'run',forbidden)
 graph=build_graph(InMemorySaver())
 response=await ask(graph,ChatRequest(question='Who wrote this book?',language_hint=language,session_id='metadata-test'))
 assert response.grounded and name in response.answer and response.citations[0].page==3
 assert response.citations[0].transcription_reviewed and response.execution==[] and response.model_used==''
 state=await graph.aget_state({'configurable':{'thread_id':'metadata-test'}})
 assert state.values['history'][-1]['provider_used']=='book_metadata'

def test_changed_pdf_invalidates_review(monkeypatch,tmp_path):
 import hashlib,json
 path=tmp_path/'book.pdf';path.write_bytes(b'original')
 digest=hashlib.sha256(b'original').hexdigest()
 (tmp_path/'book.json').write_text(json.dumps({'review_status':'visually_verified','pdf_sha256':digest}))
 monkeypatch.setattr(b,'METADATA_DIR',tmp_path);monkeypatch.setattr(b,'BOOKS',tmp_path)
 book={'id':'book','filename':'book.pdf','hash':digest}
 assert b.read_reviewed(book)
 path.write_bytes(b'changed PDF')
 assert b.read_reviewed(book) is None


def test_english_question_with_urdu_book_title_stays_english():
    from app.core.language import detect
    assert detect("Who is author of Muaddima seerat ur Rasool")=="English"
    assert detect("What does the kitab say about namaz?")=="English"
    assert detect("Namaz kya hai?")=="Hinglish"
