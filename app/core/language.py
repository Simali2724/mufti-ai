import re
def detect(text, hint='auto'):
    if hint and hint != 'auto': return hint
    if re.search(r'[\u0900-\u097f]',text): return 'Hindi'
    if re.search(r'[\u0600-\u06ff]',text): return 'Urdu'
    words=set(re.findall(r'\w+',text.lower()))
    if words & {'who','what','when','where','how','explain','describe'} and not words & {'kya','kaise','hai','hain','mujhe','batao'}: return 'English'
    return 'Hinglish' if words & {'kya','kaise','hai','hain','mein','mujhe','batao','ki','ke','se','aur','namaz','roza','seerat','kitab'} else 'English'
NOT_FOUND = {
'English': 'I could not find sufficient verified evidence in the available books. Please consult a qualified scholar.',
'Hindi': 'उपलब्ध किताबों में इस सवाल का पर्याप्त प्रमाण नहीं मिला। कृपया किसी योग्य आलिम से सलाह लें।',
'Urdu': 'دستیاب کتابوں میں اس سوال کا کافی معتبر حوالہ نہیں ملا۔ براہ کرم کسی مستند عالم سے رجوع کریں۔',
'Hinglish': 'Maujooda kitabon mein is sawal ka kaafi mustanad hawala nahi mila. Barah-e-karam kisi qualified alim se mashwara karein.'}
GREETINGS = {'English':'Assalamu alaikum. Ask a question about your available books.', 'Hindi':'अस्सलामु अलैकुम। अपनी किताबों से संबंधित सवाल पूछिए।', 'Urdu':'السلام علیکم۔ اپنی دستیاب کتابوں سے متعلق سوال پوچھیے۔','Hinglish':'Assalamu alaikum. Apni kitabon se mutalliq sawal poochhiye.'}
REFUSALS = {'English':'I cannot provide instructions for harm, sectarian attacks, or settle life-and-death or legal disputes. Please consult a qualified local scholar and the appropriate professional.', 'Hindi':'नुकसान, फ़िरक़ावार हमलों या जान और कानूनी विवादों पर फ़ैसला नहीं दे सकता। योग्य आलिम और संबंधित विशेषज्ञ से सलाह लें।','Urdu':'نقصان، فرقہ وارانہ حملوں یا جان اور قانونی تنازعات پر فیصلہ نہیں دے سکتا۔ مستند عالم اور متعلقہ ماہر سے رجوع کریں۔','Hinglish':'Nuqsan, firqawarana hamlon ya jaan aur qanooni tanazaat par faisla nahi de sakta. Qualified alim aur mutalliq expert se mashwara karein.'}
DISCLAIMERS={'English':'For a personal ruling, confirm with a qualified local scholar.','Hindi':'व्यक्तिगत मसले की पुष्टि योग्य स्थानीय आलिम से करें।','Urdu':'ذاتی مسئلے کی تصدیق مستند مقامی عالم سے کریں۔','Hinglish':'Apne masle ki tasdeeq qualified local alim se karein.'}

# Coverage and service messages. A model or quota failure must never be phrased as an
# absence of evidence in the book.
PARTIAL_INTRO = {
 'English': 'The book covers part of this question:',
 'Hindi': 'इस सवाल का एक हिस्सा किताब में मिलता है:',
 'Urdu': 'اس سوال کا ایک حصہ کتاب میں موجود ہے:',
 'Hinglish': 'Is sawal ka ek hissa kitab mein milta hai:'}
MISSING_HEADING = {
 'English': 'Not covered in this book',
 'Hindi': 'इस किताब में शामिल नहीं',
 'Urdu': 'اس کتاب میں شامل نہیں',
 'Hinglish': 'Is kitab mein shamil nahi'}
RELATED_HEADING = {
 'English': 'Related passages (these do not directly answer the question)',
 'Hindi': 'संबंधित अंश (ये सीधे उत्तर नहीं देते)',
 'Urdu': 'متعلقہ اقتباسات (یہ براہِ راست جواب نہیں دیتے)',
 'Hinglish': 'Mutalliq iqtibasat (ye seedha jawab nahi dete)'}
SOURCES_HEADING = {
 'English': 'Sources', 'Hindi': 'स्रोत', 'Urdu': 'حوالہ جات', 'Hinglish': 'Hawale'}
NO_DIRECT_ANSWER = {
 'English': 'The indexed book does not directly answer this question. Related passages are listed below so you can check the original pages yourself.',
 'Hindi': 'इंडेक्स की गई किताब इस सवाल का सीधा जवाब नहीं देती। नीचे संबंधित अंश दिए गए हैं ताकि आप मूल पृष्ठ स्वयं देख सकें।',
 'Urdu': 'اشاریہ شدہ کتاب اس سوال کا براہِ راست جواب نہیں دیتی۔ ذیل میں متعلقہ اقتباسات دیے گئے ہیں تاکہ آپ اصل صفحات خود دیکھ سکیں۔',
 'Hinglish': 'Index ki gayi kitab is sawal ka seedha jawab nahi deti. Neeche mutalliq iqtibasat diye gaye hain taki aap asal safhat khud dekh sakein.'}
QUOTA_EXHAUSTED = {
 'English': 'Your cloud model quota is exhausted, so the answer was attempted on the local model. This is a model limit, not a statement about the book.',
 'Hindi': 'आपके क्लाउड मॉडल का कोटा समाप्त है, इसलिए उत्तर स्थानीय मॉडल से लिया गया। यह मॉडल की सीमा है, किताब के बारे में कथन नहीं।',
 'Urdu': 'آپ کے کلاؤڈ ماڈل کا کوٹا ختم ہو چکا ہے، اس لیے جواب مقامی ماڈل سے لیا گیا۔ یہ ماڈل کی حد ہے، کتاب کے بارے میں بیان نہیں۔',
 'Hinglish': 'Aapke cloud model ka quota khatam hai, is liye jawab local model se liya gaya. Yeh model ki limit hai, kitab ke baare mein bayan nahi.'}
PROVIDER_UNAVAILABLE = {
 'English': 'No answering model could be reached, so no answer was produced. This is a service failure, not an absence of evidence in the book. Check Ollama and your model settings, then try again.',
 'Hindi': 'कोई उत्तर देने वाला मॉडल उपलब्ध नहीं हुआ, इसलिए उत्तर नहीं बना। यह सेवा की विफलता है, किताब में प्रमाण की कमी नहीं। Ollama और मॉडल सेटिंग जाँचें।',
 'Urdu': 'کوئی جواب دینے والا ماڈل دستیاب نہ ہو سکا، اس لیے جواب تیار نہیں ہوا۔ یہ سروس کی خرابی ہے، کتاب میں شواہد کی کمی نہیں۔ Ollama اور ماڈل کی ترتیبات دیکھیں۔',
 'Hinglish': 'Koi jawab dene wala model available nahi hua, is liye jawab nahi bana. Yeh service failure hai, kitab mein saboot ki kami nahi. Ollama aur model settings check karein.'}
SEARCH_UNAVAILABLE = {
 'English': 'The book search service failed, so the book was not actually searched. Check that Ollama and the bge-m3 embedding model are running, then try again.',
 'Hindi': 'पुस्तक खोज सेवा विफल रही, इसलिए किताब वास्तव में खोजी ही नहीं गई। Ollama और bge-m3 एम्बेडिंग मॉडल जाँचकर फिर प्रयास करें।',
 'Urdu': 'کتاب کی تلاش کی سروس ناکام رہی، اس لیے کتاب میں تلاش ہوئی ہی نہیں۔ Ollama اور bge-m3 ایمبیڈنگ ماڈل دیکھ کر دوبارہ کوشش کریں۔',
 'Hinglish': 'Kitab search service fail ho gayi, is liye kitab mein talash hui hi nahi. Ollama aur bge-m3 embedding model check karke dobara try karein.'}

# How a repaired claim credits the outside writer its span is quoted from. The code knows the
# names from the book's own citation line, so a small model that will not write them can still
# produce a correctly attributed sentence instead of losing the claim entirely.
ATTRIBUTION_PREFIX = {
 'English': 'As quoted from {names}: {claim}',
 'Hindi': '{names} के हवाले से: {claim}',
 'Urdu': '{names} کے حوالے سے: {claim}',
 'Hinglish': '{names} ke hawale se: {claim}'}
ATTRIBUTION_JOIN = {'English': ' and ', 'Hindi': ' और ', 'Urdu': ' اور ', 'Hinglish': ' aur '}
EXPLANATION_UNVERIFIED = {
 'English': 'A generated explanation could not be verified against the book, so the relevant passages are shown below in the book\'s own words. These are source excerpts, not an explanation.',
 'Hindi': 'तैयार की गई व्याख्या किताब से सत्यापित नहीं हो सकी, इसलिए संबंधित अंश किताब के अपने शब्दों में नीचे दिए गए हैं। ये स्रोत उद्धरण हैं, व्याख्या नहीं।',
 'Urdu': 'تیار کردہ وضاحت کتاب سے تصدیق نہ ہو سکی، اس لیے متعلقہ اقتباسات کتاب کے اپنے الفاظ میں ذیل میں دیے گئے ہیں۔ یہ ماخذ کے اقتباسات ہیں، وضاحت نہیں۔',
 'Hinglish': 'Tayyar ki gayi tashreeh kitab se verify nahi ho saki, is liye mutalliq iqtibasat kitab ke apne alfaz mein neeche diye gaye hain. Yeh source excerpts hain, tashreeh nahi.'}

# The matched pages exist but their extracted text is legacy-font OCR noise. This is an
# extraction problem, not an absence of evidence, and it must never be dressed up as a quote.
EXTRACTION_PROBLEM = {
 'English': 'The pages that matched this question did not extract into readable text, so there is nothing I can quote or explain from them. This is a problem with the scanned text of those pages, not a statement that the book is silent. Please open the pages listed below in the original PDF.',
 'Hindi': 'इस सवाल से मेल खाने वाले पृष्ठों का पाठ पढ़ने योग्य रूप में नहीं निकला, इसलिए उनसे कुछ उद्धृत या व्याख्या नहीं की जा सकती। यह उन पृष्ठों के स्कैन की समस्या है, किताब की चुप्पी नहीं। कृपया नीचे दिए पृष्ठ मूल PDF में देखें।',
 'Urdu': 'اس سوال سے مطابقت رکھنے والے صفحات کا متن قابلِ مطالعہ شکل میں حاصل نہیں ہوا، اس لیے ان سے کوئی اقتباس یا وضاحت پیش نہیں کی جا سکتی۔ یہ ان صفحات کے اسکین کا مسئلہ ہے، کتاب کی خاموشی نہیں۔ براہ کرم ذیل کے صفحات اصل PDF میں دیکھیے۔',
 'Hinglish': 'Is sawal se match karne wale safhat ka text padhne laayaq shakl mein nahi nikla, is liye un se kuch quote ya tashreeh nahi ki ja sakti. Yeh un pages ke scan ka masla hai, kitab ki khamoshi nahi. Neeche diye gaye pages asal PDF mein dekhiye.'}

# The reader asked for "something" without naming a subject. Guessing one would be inventing
# their intent; searching for it matched OCR noise and wasted four minutes.
NEEDS_TOPIC = {
 'English': 'Which topic from the book would you like me to explain? For example: the study of the Seerah, the Charter of Madinah, the rights it guarantees, or the Prophet’s personal worship. Name a subject and I will find the relevant pages.',
 'Hindi': 'किताब का कौन सा विषय समझाऊं? जैसे: सीरत का अध्ययन, मदीना का संविधान, या उसमें दिए गए अधिकार। विषय बताइए, मैं संबंधित पृष्ठ ढूंढ दूंगा।',
 'Urdu': 'کتاب کا کون سا موضوع سمجھاؤں؟ مثلاً: مطالعہ سیرت، میثاق مدینہ، یا اس میں دیے گئے حقوق۔ موضوع بتائیے، میں متعلقہ صفحات تلاش کر دوں گا۔',
 'Hinglish': 'Kitab ka kaun sa topic samjhaun? Misal ke taur par: mutala-e-seerat, Meesaq-e-Madinah, ya us mein diye gaye huqooq. Topic bataiye, main mutalliq safhat dhoond kar samjhata hoon.'}

# The question is not about the books in the library at all (2026-11-16: a request for C code
# was answered with three unrelated "related passages"). Name the books; show no passages.
OUT_OF_LIBRARY = {
 'English': 'This question is outside the subject of the books in your library, so I have nothing from them to answer it with. I answer only from these books: {books}. Please ask about something they discuss — for example the Seerah, the Charter of Madinah, or the stages of human creation.',
 'Hinglish': 'Yeh sawal aapki library ki kitabon ke mauzu se bahar hai, is liye in kitabon mein iska jawab nahi hai. Main sirf in kitabon se jawab deta hoon: {books}. Inke kisi mauzu par sawal poochiye — jaise Seerat, Misaq-e-Madina, ya insaan ki takhleeq ke marahil.',
 'Urdu': 'یہ سوال آپ کی لائبریری کی کتابوں کے موضوع سے باہر ہے، اس لیے ان کتابوں میں اس کا جواب نہیں ہے۔ میں صرف ان کتابوں سے جواب دیتا ہوں: {books}۔ ان کے کسی موضوع پر سوال پوچھیے — جیسے سیرت، میثاقِ مدینہ، یا تخلیقِ انسان کے مراحل۔',
 'Hindi': 'यह सवाल आपकी लाइब्रेरी की किताबों के विषय से बाहर है, इसलिए इन किताबों में इसका जवाब नहीं है। मैं सिर्फ़ इन किताबों से जवाब देता हूँ: {books}। इनके किसी विषय पर सवाल पूछिए — जैसे सीरत, मीसाक़-ए-मदीना, या इंसान की तख़लीक़ के मराहिल।',
}

# The library WAS searched and no book discusses the subject (e.g. Karbala). Different from
# OUT_OF_LIBRARY, which is used when the question is not about these books at all.
NOT_IN_LIBRARY = {
 'English': 'I searched every book in your library ({books}) and none of them discusses this subject, so there is no passage I can explain or quote for it. Please ask about a topic these books cover.',
 'Hinglish': 'Maine aapki library ki sab kitabon ({books}) mein dhoonda — in mein se kisi mein bhi is mauzu par baat nahi ki gayi, is liye iska koi hissa main samjha ya quote nahi kar sakta. In kitabon ke kisi mauzu par sawal poochiye.',
 'Urdu': 'میں نے آپ کی لائبریری کی تمام کتابوں ({books}) میں تلاش کیا — ان میں سے کسی میں بھی اس موضوع پر بات نہیں کی گئی، اس لیے اس کا کوئی حصہ میں سمجھا یا نقل نہیں کر سکتا۔ ان کتابوں کے کسی موضوع پر سوال پوچھیے۔',
 'Hindi': 'मैंने आपकी लाइब्रेरी की सभी किताबों ({books}) में खोजा — इनमें से किसी में भी इस विषय पर बात नहीं की गई, इसलिए इसका कोई हिस्सा मैं समझा या उद्धृत नहीं कर सकता। इन किताबों के किसी विषय पर सवाल पूछिए।',
}
