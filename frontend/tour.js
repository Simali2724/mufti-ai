// Welcome popup, arrow tour and translated directions (added 2026-11-17).
//
// The INTERFACE stays in English by default. Only the DIRECTIONS — the welcome popup, the arrow
// tour and the Guide dialog — follow the language the reader picks (English, Hinglish, Urdu,
// Hindi). The choice is stored per device in localStorage 'mufti-ui-lang' (read by dirLang() in
// app.js). The first visit opens the welcome popup; ?guide=0 suppresses it, ?guide=1 opens the Guide,
// ?tour=1 starts the tour.
//
// Every string here is set with textContent (see richText) — no HTML from translations is parsed.

const DIR_LANGS = [['English', 'English'], ['Hinglish', 'Hinglish'], ['Urdu', 'اردو'], ['Hindi', 'हिन्दी']];

const T = {
English: {
  dir: 'ltr',
  eyebrow: 'WELCOME',
  welcomeTitle: 'Welcome to Mufti AI',
  welcomeText: 'Ask questions about your own Islamic books. Every answer is explained clearly and respectfully, and every point links to its page in the book.',
  choose: 'Choose the language for directions',
  welcomeSmall: 'The app stays in English; directions, the tour and the guide use this language. Your questions can be in any language.',
  tourButton: 'Show me around ↗', skip: 'Skip',
  next: 'Next →', back: '← Back', done: 'Start asking ✓', skipTour: 'Skip tour', stepOf: 'Step {n} of {total}',
  tour: [
    {sel: '#chat-form', title: 'Start your conversation here', text: 'Type your question in English, Urdu, Hindi or Hinglish, then press Enter or the ↑ button.'},
    {sel: '#mic', title: 'Or speak your question', text: 'Tap the mic and speak. Tap it again (or press Stop) to finish. Your words appear in the box so you can check them before sending. Tapped by mistake? Press Cancel or Esc.'},
    {sel: '#attach', title: 'Or show a photo or file', text: '📷 Take a photo of a page, 📎 upload a photo/PDF/text, or simply drag a file onto the chat. The text is read on this computer; then Explain it from your books, or find which book and page it is from.'},
    {sel: '#style', title: 'Choose how you want the answer', text: 'Detailed, Short, Simple words or Study notes. Beside it is the reply language — Auto answers in the language of your question.'},
    {sel: '#new-chat', sidebar: true, title: 'Start a new conversation', text: 'Begin a fresh topic at any time. Your earlier conversations are listed below it.'},
    {sel: '#nav-library', sidebar: true, title: 'Your library is here', text: 'See your books, open the original PDF, and browse the chapters: Explain, Summary, or Focus your questions on one chapter.'},
    {sel: '#nav-topics', sidebar: true, title: 'Find any topic', text: 'Every chapter and section of your books, with pages, plus key concepts. Search in any language — “equality” also finds the Urdu sections.'},
    {sel: '#nav-saved', sidebar: true, title: 'Your saved answers', text: 'Press ☆ Save under an answer to keep it here with its references, even after the conversation is deleted.'},
    {sel: '#nav-models', sidebar: true, title: 'Choose the AI model', text: 'Gemini, Claude, OpenAI or the local model. If one is busy or out of quota, the next one answers automatically.'},
    {sel: '#guide', title: 'Help is always here', text: 'Open the Guide for full directions and a setup check of your computer. Change the directions language with the 🌐 button.'},
  ],
  guideTitle: 'How to use Mufti AI', tabUse: 'How to use', tabSetup: 'Setup check', tabKeys: 'Shortcuts',
  langLabel: 'Directions language', showTour: '▶ Show the tour', startAsking: 'Start asking ↗',
  guideSteps: [
    '**Ask in any language.** English, Urdu, Hindi or Hinglish. Example: “What was the Charter of Madinah? Explain in detail.” Keep the reply language on **Auto** or choose one.',
    '**Choose the answer style** (✎): **Detailed** a full lesson · **Short** a few lines · **Simple words** easy language · **Study notes** points to remember. Every style keeps the book references.',
    '**Speak instead of typing** (♩): tap the mic and speak, then tap again or press **Stop**. Your words appear in the question box — check them and press **Send**. **Cancel** or **Esc** throws away an accidental recording.',
    '**📷 Photo / 📎 file / drag & drop:** a photo of a page (Urdu, Arabic, English, Hindi), a PDF or a text file is read on this computer. Check the text, then **Explain this** (answered only from your books) or **🔍 Find in my books** (which book and page — no AI used). Ctrl+V pastes a screenshot.',
    '**Tap the [1] [2] chips** to open the exact page of the book. The **Sources** list shows each quotation and a link to the original page.',
    '**Badges:** “✓ Fact-checked against the book” means a second AI pass compared every sentence with the book. “◌ Sources linked” means the local model answered; the references are real but no separate fact-check ran.',
    '**Ask next:** under every answer there are suggested questions, and buttons to get the same answer in another style.',
    '**Explore chapters:** **My library → ☰ Chapters**. Every chapter has **Explain**, **Summary** and **Focus** (your next questions search only that chapter).',
    '**🧠 Quiz me:** a short multiple-choice quiz made only from the checked sentences of an answer, each question linked to its page. **👍 / 👎** tells us whether an answer helped; 👎 lets you say what was wrong (saved only on this computer).',
    '**▦ Topic index** lists every chapter and section with pages and the key concepts; **★ Saved answers** keeps answers you saved with ☆ Save.',
    '**Ask “Which book is this from?”** to get the title, author, publisher and the pages of the previous answer.',
    '**Save and share:** ⧉ Copy, ⤓ Download (.md) and ⎙ Print on every answer. ◖ Read aloud plays it.',
    '**Models & fallback:** with a Gemini, Claude or OpenAI key, answers are fast and fact-checked; without one, the local model answers slowly. Check the **Setup check** tab first.',
  ],
  guideNote: 'Mufti AI answers only from the books indexed on this computer. For a personal ruling, please consult a qualified scholar.',
  setupIntro: 'Checks your computer: books, search index, Ollama, models, cloud keys, OCR and storage. Each problem shows the exact fix.',
  checking: 'Checking your setup…', fixLabel: 'Fix:',
  setupSummary: {ok: 'Everything is ready.', warn: 'Usable — please look at the warnings below.', fail: 'Please fix the red (✕) items first.'},
  keys: ['Enter — send · Shift+Enter — new line', '/ — jump to the question box', 'Alt+N — new conversation', 'Alt+L — My library · Alt+G — this guide', 'Esc — close a dialog, or cancel a recording', 'Link options: ?session=<id> opens a saved conversation · ?theme=dark'],
},
Hinglish: {
  dir: 'ltr',
  eyebrow: 'KHUSH AMDEED',
  welcomeTitle: 'Mufti AI mein khush amdeed',
  welcomeText: 'Apni Islami kitabon ke baare mein sawal poochhiye. Har jawab saaf aur adab ke saath samjhaya jata hai, aur har baat kitab ke page se judi hoti hai.',
  choose: 'Directions ki zabaan chuniye',
  welcomeSmall: 'App English mein hi rahega; directions, tour aur guide is zabaan mein aayenge. Sawal aap kisi bhi zabaan mein poochh sakte hain.',
  tourButton: 'Mujhe dikhaiye ↗', skip: 'Abhi nahi',
  next: 'Aage →', back: '← Peeche', done: 'Shuru karein ✓', skipTour: 'Tour band karein', stepOf: 'Step {n} / {total}',
  tour: [
    {sel: '#chat-form', title: 'Baat-cheet yahan se shuru karein', text: 'Apna sawal English, Urdu, Hindi ya Hinglish mein likhiye, phir Enter ya ↑ button dabaiye.'},
    {sel: '#mic', title: 'Ya bol kar poochhiye', text: 'Mic dabaiye aur boliye. Khatam karne ke liye dobara dabaiye (ya Stop). Jo bola woh pehle box mein likha aayega — check karke Send kijiye. Galti se dab gaya? Cancel ya Esc dabaiye.'},
    {sel: '#attach', title: 'Ya photo / file dikhaiye', text: '📷 Page ki photo lijiye, 📎 photo/PDF/text upload kijiye, ya file seedha chat par drag kijiye. Text isi computer par padha jata hai; phir kitabon se samjhiye, ya dhoondiye ye kis kitab ke kis page ka hai.'},
    {sel: '#style', title: 'Jawab ka andaz chuniye', text: 'Detailed, Short, Simple words ya Study notes. Bagal mein jawab ki zabaan hai — Auto aapke sawal ki zabaan mein jawab deta hai.'},
    {sel: '#new-chat', sidebar: true, title: 'Nayi conversation', text: 'Kabhi bhi naya topic shuru kijiye. Purani conversations iske neeche milengi.'},
    {sel: '#nav-library', sidebar: true, title: 'Aapki library yahan hai', text: 'Apni kitabein dekhiye, asli PDF kholiye, aur chapters browse kijiye: Explain, Summary, ya kisi ek chapter par Focus.'},
    {sel: '#nav-topics', sidebar: true, title: 'Koi bhi topic dhoondiye', text: 'Kitabon ke saare chapters aur sections page numbers ke saath, aur key concepts. Kisi bhi zabaan mein search kijiye — “equality” Urdu sections bhi dhoond leta hai.'},
    {sel: '#nav-saved', sidebar: true, title: 'Aapke saved jawab', text: 'Jawab ke neeche ☆ Save dabaiye — woh hawalon ke saath yahan rehta hai, conversation delete hone ke baad bhi.'},
    {sel: '#nav-models', sidebar: true, title: 'AI model chuniye', text: 'Gemini, Claude, OpenAI ya local model. Ek busy ho ya limit khatam ho jaye to agla model khud jawab deta hai.'},
    {sel: '#guide', title: 'Madad hamesha yahan hai', text: 'Poori directions aur computer ka setup check Guide mein hai. Directions ki zabaan 🌐 button se badliye.'},
  ],
  guideTitle: 'Mufti AI kaise istemal karein', tabUse: 'Kaise istemal karein', tabSetup: 'Setup check', tabKeys: 'Shortcuts',
  langLabel: 'Directions ki zabaan', showTour: '▶ Tour dikhaiye', startAsking: 'Sawal poochhiye ↗',
  guideSteps: [
    '**Kisi bhi zabaan mein poochhiye.** English, Urdu, Hindi ya Hinglish. Misal: “Misaq-e-Madina kya tha? Tafseel se samjhao.” Jawab ki zabaan **Auto** rakhiye ya khud chuniye.',
    '**Jawab ka andaz chuniye** (✎): **Detailed** poora sabaq · **Short** chand lines · **Simple words** aasaan alfaaz · **Study notes** yaad rakhne wale points. Har andaz mein kitab ka hawala rehta hai.',
    '**Likhne ki jagah boliye** (♩): mic dabaiye, boliye, phir dobara dabaiye ya **Stop**. Jo bola woh sawal ke box mein aayega — check karke **Send** dabaiye. Galti se recording ho gayi to **Cancel** ya **Esc**.',
    '**📷 Photo / 📎 file / drag & drop:** page ki photo (Urdu, Arabi, English, Hindi), PDF ya text file isi computer par padhi jati hai. Text check kijiye, phir **Explain this** (jawab sirf aapki kitabon se) ya **🔍 Find in my books** (kaun si kitab, kaun sa page — bina AI). Ctrl+V se screenshot paste.',
    '**[1] [2] chips dabaiye** — kitab ka wahi page khulta hai. Neeche **Sources** mein har iqtibas aur asli page ka link hai.',
    '**Badges:** “✓ Fact-checked against the book” = doosre AI pass ne har jumla kitab se milaya. “◌ Sources linked” = local model ka jawab; hawale asli hain, par alag fact-check nahi hua.',
    '**Ask next:** har jawab ke neeche agle sawal, aur wahi jawab doosre andaz mein lene ke buttons.',
    '**Chapters dekhiye:** **My library → ☰ Chapters**. Har chapter mein **Explain**, **Summary** aur **Focus** (agle sawal sirf usi chapter se).',
    '**🧠 Quiz me:** jawab ki sirf check ki hui baaton se chhota MCQ quiz, har sawal page se juda. **👍 / 👎** se batayiye jawab kaam aaya ya nahi; 👎 par ghalti bataiye (sirf is computer par save hota hai).',
    '**▦ Topic index** mein saare chapters/sections pages ke saath aur key concepts; **★ Saved answers** mein ☆ Save kiye jawab.',
    '**“Which book is this from?” poochhiye** — kitab ka naam, musannif, publisher aur pichhle jawab ke pages.',
    '**Save aur share:** har jawab par ⧉ Copy, ⤓ Download (.md) aur ⎙ Print. ◖ Read aloud se suniye.',
    '**Models & fallback:** Gemini, Claude ya OpenAI key ho to jawab tez aur fact-checked; warna local model dheere jawab deta hai. Pehle **Setup check** tab dekhiye.',
  ],
  guideNote: 'Mufti AI sirf is computer par indexed kitabon se jawab deta hai. Zaati mas\'ale ke liye kisi mustanad alim se rujoo kijiye.',
  setupIntro: 'Aapke computer ko check karta hai: kitabein, search index, Ollama, models, cloud keys, OCR aur storage. Har masle ka hal saath likha hai.',
  checking: 'Setup check ho raha hai…', fixLabel: 'Hal:',
  setupSummary: {ok: 'Sab theek hai.', warn: 'Kaam karega — neeche ki warnings dekhiye.', fail: 'Pehle laal (✕) wale masle theek kijiye.'},
  keys: ['Enter — bhejiye · Shift+Enter — nayi line', '/ — sawal ke box par jaiye', 'Alt+N — nayi conversation', 'Alt+L — My library · Alt+G — ye guide', 'Esc — dialog band, ya recording cancel', 'Link: ?session=<id> purani conversation kholta hai · ?theme=dark'],
},
Urdu: {
  dir: 'rtl',
  eyebrow: 'خوش آمدید',
  welcomeTitle: 'مفتی اے آئی میں خوش آمدید',
  welcomeText: 'اپنی اسلامی کتابوں کے بارے میں سوال پوچھیے۔ ہر جواب وضاحت اور ادب کے ساتھ سمجھایا جاتا ہے، اور ہر بات کتاب کے صفحے سے جڑی ہوتی ہے۔',
  choose: 'ہدایات کی زبان منتخب کیجیے',
  welcomeSmall: 'ایپ انگریزی میں ہی رہے گی؛ ہدایات، ٹور اور گائیڈ اس زبان میں ہوں گے۔ سوال آپ کسی بھی زبان میں پوچھ سکتے ہیں۔',
  tourButton: 'مجھے دکھائیے ↖', skip: 'ابھی نہیں',
  next: '← آگے', back: 'پیچھے →', done: 'شروع کیجیے ✓', skipTour: 'ٹور بند کیجیے', stepOf: 'مرحلہ {n} از {total}',
  tour: [
    {sel: '#chat-form', title: 'گفتگو یہاں سے شروع کیجیے', text: 'اپنا سوال اردو، انگریزی، ہندی یا ہنگلش میں لکھیے، پھر Enter یا ↑ بٹن دبائیے۔'},
    {sel: '#mic', title: 'یا بول کر پوچھیے', text: 'مائیک دبا کر بولیے۔ ختم کرنے کے لیے دوبارہ دبائیے (یا Stop)۔ جو بولا وہ پہلے خانے میں لکھا آئے گا — دیکھ کر Send کیجیے۔ غلطی سے دب گیا؟ Cancel یا Esc دبائیے۔'},
    {sel: '#attach', title: 'یا تصویر / فائل دکھائیے', text: '📷 صفحے کی تصویر لیجیے، 📎 تصویر/PDF/متن اپلوڈ کیجیے، یا فائل سیدھی گفتگو پر کھینچ کر چھوڑیے۔ متن اسی کمپیوٹر پر پڑھا جاتا ہے؛ پھر کتابوں سے سمجھیے، یا معلوم کیجیے کہ یہ کس کتاب کے کس صفحے کا ہے۔'},
    {sel: '#style', title: 'جواب کا انداز منتخب کیجیے', text: 'Detailed، Short، Simple words یا Study notes۔ ساتھ ہی جواب کی زبان ہے — Auto آپ کے سوال کی زبان میں جواب دیتا ہے۔'},
    {sel: '#new-chat', sidebar: true, title: 'نئی گفتگو', text: 'کسی بھی وقت نیا موضوع شروع کیجیے۔ پچھلی گفتگوئیں اس کے نیچے ملیں گی۔'},
    {sel: '#nav-library', sidebar: true, title: 'آپ کی لائبریری یہاں ہے', text: 'اپنی کتابیں دیکھیے، اصل PDF کھولیے، اور ابواب دیکھیے: Explain، Summary، یا کسی ایک باب پر Focus۔'},
    {sel: '#nav-topics', sidebar: true, title: 'کوئی بھی موضوع تلاش کیجیے', text: 'کتابوں کے تمام ابواب اور حصے صفحات کے ساتھ، اور اہم تصورات۔ کسی بھی زبان میں تلاش کیجیے — ”equality“ اردو حصے بھی ڈھونڈ لیتا ہے۔'},
    {sel: '#nav-saved', sidebar: true, title: 'آپ کے محفوظ جوابات', text: 'جواب کے نیچے ☆ Save دبائیے — وہ حوالوں کے ساتھ یہاں رہتا ہے، گفتگو حذف ہونے کے بعد بھی۔'},
    {sel: '#nav-models', sidebar: true, title: 'اے آئی ماڈل منتخب کیجیے', text: 'Gemini، Claude، OpenAI یا مقامی ماڈل۔ ایک مصروف ہو یا حد ختم ہو جائے تو اگلا ماڈل خود جواب دیتا ہے۔'},
    {sel: '#guide', title: 'مدد ہمیشہ یہاں ہے', text: 'مکمل ہدایات اور کمپیوٹر کا سیٹ اپ چیک گائیڈ میں ہے۔ ہدایات کی زبان 🌐 بٹن سے بدلیے۔'},
  ],
  guideTitle: 'مفتی اے آئی کیسے استعمال کریں', tabUse: 'استعمال کا طریقہ', tabSetup: 'سیٹ اپ چیک', tabKeys: 'شارٹ کٹس',
  langLabel: 'ہدایات کی زبان', showTour: '▶ ٹور دکھائیے', startAsking: 'سوال پوچھیے ↖',
  guideSteps: [
    '**کسی بھی زبان میں پوچھیے۔** اردو، انگریزی، ہندی یا ہنگلش۔ مثال: ”میثاقِ مدینہ کیا تھا؟ تفصیل سے سمجھائیے۔“ جواب کی زبان **Auto** رکھیے یا خود منتخب کیجیے۔',
    '**جواب کا انداز منتخب کیجیے** (✎): **Detailed** مکمل سبق · **Short** چند سطریں · **Simple words** آسان الفاظ · **Study notes** یاد رکھنے کے نکات۔ ہر انداز میں کتاب کا حوالہ رہتا ہے۔',
    '**لکھنے کے بجائے بولیے** (♩): مائیک دبا کر بولیے، پھر دوبارہ دبائیے یا **Stop**۔ جو بولا وہ سوال کے خانے میں آئے گا — دیکھ کر **Send** دبائیے۔ غلطی کی ریکارڈنگ کے لیے **Cancel** یا **Esc**۔',
    '**📷 تصویر / 📎 فائل / ڈریگ اینڈ ڈراپ:** صفحے کی تصویر (اردو، عربی، انگریزی، ہندی)، PDF یا متن کی فائل اسی کمپیوٹر پر پڑھی جاتی ہے۔ متن دیکھیے، پھر **Explain this** (جواب صرف آپ کی کتابوں سے) یا **🔍 Find in my books** (کون سی کتاب، کون سا صفحہ — بغیر اے آئی)۔',
    '**[1] [2] نشانات دبائیے** — کتاب کا وہی صفحہ کھلتا ہے۔ نیچے **Sources** میں ہر اقتباس اور اصل صفحے کا لنک ہے۔',
    '**بیجز:** ”✓ Fact-checked against the book“ = دوسرے اے آئی مرحلے نے ہر جملہ کتاب سے ملایا۔ ”◌ Sources linked“ = مقامی ماڈل کا جواب؛ حوالے اصل ہیں مگر الگ جانچ نہیں ہوئی۔',
    '**Ask next:** ہر جواب کے نیچے اگلے سوالات، اور وہی جواب دوسرے انداز میں لینے کے بٹن۔',
    '**ابواب دیکھیے:** **My library ← ☰ Chapters**۔ ہر باب میں **Explain**، **Summary** اور **Focus** (اگلے سوال صرف اسی باب سے)۔',
    '**🧠 Quiz me:** جواب کے صرف جانچے ہوئے جملوں سے مختصر کوئز، ہر سوال صفحے سے جڑا۔ **👍 / 👎** سے بتائیے جواب مفید تھا یا نہیں؛ 👎 پر غلطی بتائیے (صرف اسی کمپیوٹر پر محفوظ)۔',
    '**▦ Topic index** میں تمام ابواب و حصے صفحات کے ساتھ اور اہم تصورات؛ **★ Saved answers** میں ☆ Save کیے گئے جوابات۔',
    '**”یہ کس کتاب سے ہے؟“ پوچھیے** — کتاب کا نام، مصنف، ناشر اور پچھلے جواب کے صفحات۔',
    '**محفوظ اور شیئر:** ہر جواب پر ⧉ Copy، ⤓ Download (.md) اور ⎙ Print۔ ◖ Read aloud سے سنیے۔',
    '**Models & fallback:** Gemini، Claude یا OpenAI کی کلید ہو تو جواب تیز اور جانچا ہوا؛ ورنہ مقامی ماڈل آہستہ جواب دیتا ہے۔ پہلے **سیٹ اپ چیک** دیکھیے۔',
  ],
  guideNote: 'مفتی اے آئی صرف اسی کمپیوٹر پر موجود کتابوں سے جواب دیتا ہے۔ ذاتی مسئلے کے لیے کسی مستند عالم سے رجوع کیجیے۔',
  setupIntro: 'آپ کے کمپیوٹر کی جانچ: کتابیں، سرچ انڈیکس، Ollama، ماڈلز، کلاؤڈ کلیدیں، OCR اور اسٹوریج۔ ہر مسئلے کا حل ساتھ لکھا ہے۔',
  checking: 'سیٹ اپ کی جانچ ہو رہی ہے…', fixLabel: 'حل:',
  setupSummary: {ok: 'سب کچھ تیار ہے۔', warn: 'کام کرے گا — نیچے کی تنبیہات دیکھیے۔', fail: 'پہلے سرخ (✕) مسائل حل کیجیے۔'},
  keys: ['Enter — بھیجیے · Shift+Enter — نئی سطر', '/ — سوال کے خانے پر جائیے', 'Alt+N — نئی گفتگو', 'Alt+L — لائبریری · Alt+G — یہ گائیڈ', 'Esc — ڈائیلاگ بند، یا ریکارڈنگ منسوخ', 'لنک: ?session=<id> پرانی گفتگو کھولتا ہے · ?theme=dark'],
},
Hindi: {
  dir: 'ltr',
  eyebrow: 'स्वागत है',
  welcomeTitle: 'मुफ़्ती AI में आपका स्वागत है',
  welcomeText: 'अपनी इस्लामी किताबों के बारे में सवाल पूछिए। हर जवाब साफ़ और अदब के साथ समझाया जाता है, और हर बात किताब के पेज से जुड़ी होती है।',
  choose: 'निर्देशों की भाषा चुनिए',
  welcomeSmall: 'ऐप अंग्रेज़ी में ही रहेगा; निर्देश, टूर और गाइड इस भाषा में आएँगे। सवाल आप किसी भी भाषा में पूछ सकते हैं।',
  tourButton: 'मुझे दिखाइए ↗', skip: 'अभी नहीं',
  next: 'आगे →', back: '← पीछे', done: 'शुरू करें ✓', skipTour: 'टूर बंद करें', stepOf: 'चरण {n} / {total}',
  tour: [
    {sel: '#chat-form', title: 'बातचीत यहाँ से शुरू करें', text: 'अपना सवाल हिंदी, उर्दू, अंग्रेज़ी या हिंग्लिश में लिखिए, फिर Enter या ↑ बटन दबाइए।'},
    {sel: '#mic', title: 'या बोलकर पूछिए', text: 'माइक दबाइए और बोलिए। ख़त्म करने के लिए दोबारा दबाइए (या Stop)। जो बोला वह पहले बॉक्स में लिखा आएगा — जाँचकर Send कीजिए। ग़लती से दब गया? Cancel या Esc दबाइए।'},
    {sel: '#attach', title: 'या फ़ोटो / फ़ाइल दिखाइए', text: '📷 पेज की फ़ोटो लीजिए, 📎 फ़ोटो/PDF/टेक्स्ट अपलोड कीजिए, या फ़ाइल सीधे चैट पर खींचकर छोड़िए। टेक्स्ट इसी कंप्यूटर पर पढ़ा जाता है; फिर किताबों से समझिए, या जानिए यह किस किताब के किस पेज का है।'},
    {sel: '#style', title: 'जवाब का अंदाज़ चुनिए', text: 'Detailed, Short, Simple words या Study notes। बगल में जवाब की भाषा है — Auto आपके सवाल की भाषा में जवाब देता है।'},
    {sel: '#new-chat', sidebar: true, title: 'नई बातचीत', text: 'कभी भी नया विषय शुरू कीजिए। पुरानी बातचीत इसके नीचे मिलेगी।'},
    {sel: '#nav-library', sidebar: true, title: 'आपकी लाइब्रेरी यहाँ है', text: 'अपनी किताबें देखिए, असली PDF खोलिए, और अध्याय देखिए: Explain, Summary, या किसी एक अध्याय पर Focus।'},
    {sel: '#nav-topics', sidebar: true, title: 'कोई भी विषय खोजिए', text: 'किताबों के सारे अध्याय और हिस्से पेज नंबर के साथ, और मुख्य अवधारणाएँ। किसी भी भाषा में खोजिए — “equality” उर्दू हिस्से भी ढूँढ लेता है।'},
    {sel: '#nav-saved', sidebar: true, title: 'आपके सेव किए जवाब', text: 'जवाब के नीचे ☆ Save दबाइए — वह हवालों के साथ यहाँ रहता है, बातचीत डिलीट होने के बाद भी।'},
    {sel: '#nav-models', sidebar: true, title: 'AI मॉडल चुनिए', text: 'Gemini, Claude, OpenAI या लोकल मॉडल। एक व्यस्त हो या सीमा ख़त्म हो जाए तो अगला मॉडल अपने आप जवाब देता है।'},
    {sel: '#guide', title: 'मदद हमेशा यहाँ है', text: 'पूरे निर्देश और कंप्यूटर का सेटअप चेक गाइड में है। निर्देशों की भाषा 🌐 बटन से बदलिए।'},
  ],
  guideTitle: 'मुफ़्ती AI का इस्तेमाल कैसे करें', tabUse: 'इस्तेमाल का तरीक़ा', tabSetup: 'सेटअप चेक', tabKeys: 'शॉर्टकट',
  langLabel: 'निर्देशों की भाषा', showTour: '▶ टूर दिखाइए', startAsking: 'सवाल पूछिए ↗',
  guideSteps: [
    '**किसी भी भाषा में पूछिए।** हिंदी, उर्दू, अंग्रेज़ी या हिंग्लिश। उदाहरण: “मीसाक़-ए-मदीना क्या था? विस्तार से समझाइए।” जवाब की भाषा **Auto** रखिए या ख़ुद चुनिए।',
    '**जवाब का अंदाज़ चुनिए** (✎): **Detailed** पूरा पाठ · **Short** कुछ पंक्तियाँ · **Simple words** आसान शब्द · **Study notes** याद रखने वाले बिंदु। हर अंदाज़ में किताब का हवाला रहता है।',
    '**लिखने की जगह बोलिए** (♩): माइक दबाकर बोलिए, फिर दोबारा दबाइए या **Stop**। जो बोला वह सवाल के बॉक्स में आएगा — जाँचकर **Send** दबाइए। ग़लती की रिकॉर्डिंग के लिए **Cancel** या **Esc**।',
    '**📷 फ़ोटो / 📎 फ़ाइल / ड्रैग एंड ड्रॉप:** पेज की फ़ोटो (उर्दू, अरबी, अंग्रेज़ी, हिंदी), PDF या टेक्स्ट फ़ाइल इसी कंप्यूटर पर पढ़ी जाती है। टेक्स्ट जाँचिए, फिर **Explain this** (जवाब सिर्फ़ आपकी किताबों से) या **🔍 Find in my books** (कौन सी किताब, कौन सा पेज — बिना AI)।',
    '**[1] [2] चिप्स दबाइए** — किताब का वही पेज खुलता है। नीचे **Sources** में हर उद्धरण और असली पेज का लिंक है।',
    '**बैज:** “✓ Fact-checked against the book” = दूसरे AI चरण ने हर वाक्य किताब से मिलाया। “◌ Sources linked” = लोकल मॉडल का जवाब; हवाले असली हैं, पर अलग जाँच नहीं हुई।',
    '**Ask next:** हर जवाब के नीचे अगले सवाल, और वही जवाब दूसरे अंदाज़ में पाने के बटन।',
    '**अध्याय देखिए:** **My library → ☰ Chapters**। हर अध्याय में **Explain**, **Summary** और **Focus** (अगले सवाल सिर्फ़ उसी अध्याय से)।',
    '**🧠 Quiz me:** जवाब के सिर्फ़ जाँचे हुए वाक्यों से छोटा क्विज़, हर सवाल पेज से जुड़ा। **👍 / 👎** से बताइए जवाब काम आया या नहीं; 👎 पर ग़लती बताइए (सिर्फ़ इसी कंप्यूटर पर सेव)।',
    '**▦ Topic index** में सारे अध्याय/हिस्से पेज के साथ और मुख्य अवधारणाएँ; **★ Saved answers** में ☆ Save किए जवाब।',
    '**“यह किस किताब से है?” पूछिए** — किताब का नाम, लेखक, प्रकाशक और पिछले जवाब के पेज।',
    '**सेव और शेयर:** हर जवाब पर ⧉ Copy, ⤓ Download (.md) और ⎙ Print। ◖ Read aloud से सुनिए।',
    '**Models & fallback:** Gemini, Claude या OpenAI की key हो तो जवाब तेज़ और जाँचा हुआ; वरना लोकल मॉडल धीरे जवाब देता है। पहले **सेटअप चेक** देखिए।',
  ],
  guideNote: 'मुफ़्ती AI सिर्फ़ इसी कंप्यूटर पर मौजूद किताबों से जवाब देता है। निजी मसले के लिए किसी योग्य आलिम से सलाह लें।',
  setupIntro: 'आपके कंप्यूटर की जाँच: किताबें, सर्च इंडेक्स, Ollama, मॉडल, क्लाउड keys, OCR और स्टोरेज। हर समस्या का हल साथ लिखा है।',
  checking: 'सेटअप की जाँच हो रही है…', fixLabel: 'हल:',
  setupSummary: {ok: 'सब कुछ तैयार है।', warn: 'काम करेगा — नीचे की चेतावनियाँ देखिए।', fail: 'पहले लाल (✕) समस्याएँ ठीक कीजिए।'},
  keys: ['Enter — भेजिए · Shift+Enter — नई पंक्ति', '/ — सवाल के बॉक्स पर जाइए', 'Alt+N — नई बातचीत', 'Alt+L — लाइब्रेरी · Alt+G — यह गाइड', 'Esc — डायलॉग बंद, या रिकॉर्डिंग रद्द', 'लिंक: ?session=<id> पुरानी बातचीत खोलता है · ?theme=dark'],
},
};

function tr(key) { const lang = T[dirLang()] || T.English; return lang[key] !== undefined ? lang[key] : T.English[key]; }

// "**bold** text" -> text nodes and <strong>, nothing parsed as HTML.
function richText(parent, text) {
  parent.replaceChildren();
  String(text).split(/(\*\*[^*]+\*\*)/g).forEach(part => {
    if (!part) return;
    if (part.startsWith('**') && part.endsWith('**')) parent.append(element('strong', '', part.slice(2, -2)));
    else parent.append(document.createTextNode(part));
  });
  return parent;
}

function langButtons(box, onPick) {
  box.replaceChildren();
  for (const [code, label] of DIR_LANGS) {
    const b = element('button', 'dir-lang-option' + (code === dirLang() ? ' active' : ''), label);
    b.type = 'button'; b.setAttribute('role', 'radio'); b.setAttribute('aria-checked', String(code === dirLang()));
    b.lang = {English: 'en', Hinglish: 'en', Urdu: 'ur', Hindi: 'hi'}[code];
    b.onclick = () => { setDirLang(code); if (onPick) onPick(code); };
    box.append(b);
  }
}

function setDirLang(code) {
  try { localStorage.setItem('mufti-ui-lang', code); } catch {}
  $('#dir-lang-name').textContent = (DIR_LANGS.find(l => l[0] === code) || DIR_LANGS[0])[1];
  if ($('#welcome-dialog').open) renderWelcome();
  if ($('#guide-dialog').open) renderGuide();
  if (tourActive) showStep();
  if (typeof loadStarters === 'function') loadStarters();
}

// ---------------------------------------------------------------- welcome popup
function renderWelcome() {
  const d = $('#welcome-dialog');
  d.dir = tr('dir');
  $('#welcome-eyebrow').textContent = tr('eyebrow');
  $('#welcome-title').textContent = tr('welcomeTitle');
  $('#welcome-text').textContent = tr('welcomeText');
  $('#welcome-choose').textContent = tr('choose');
  $('#welcome-small').textContent = tr('welcomeSmall');
  $('#welcome-tour').textContent = tr('tourButton');
  $('#welcome-skip').textContent = tr('skip');
  langButtons($('#welcome-langs'));
}
function showWelcome() {
  renderWelcome();
  if (!$('#welcome-dialog').open) $('#welcome-dialog').showModal();
}
function finishWelcome() { try { localStorage.setItem('mufti-welcomed', 'true'); } catch {} $('#welcome-dialog').close(); }
$('#welcome-skip').onclick = () => { finishWelcome(); $('#question').focus(); };
$('#welcome-tour').onclick = () => { finishWelcome(); startTour(); };
$('#welcome-dialog').addEventListener('cancel', () => { try { localStorage.setItem('mufti-welcomed', 'true'); } catch {} });
$('#dir-lang-button').onclick = () => showWelcome();

// ---------------------------------------------------------------- guide (translated)
function renderGuide() {
  const g = $('#guide-dialog');
  g.dir = tr('dir');
  $('#guide-eyebrow').textContent = tr('eyebrow');
  $('#guide-title').textContent = tr('guideTitle');
  $('#guide-lang-label').textContent = tr('langLabel');
  langButtons($('#guide-langs'));
  $('#guide-tab-use').textContent = tr('tabUse');
  $('#guide-tab-setup').textContent = tr('tabSetup');
  $('#guide-tab-keys').textContent = tr('tabKeys');
  const steps = $('#guide-steps'); steps.replaceChildren();
  for (const step of tr('guideSteps')) steps.append(richText(element('li'), step));
  $('#guide-note').textContent = tr('guideNote');
  $('#setup-intro').textContent = tr('setupIntro');
  const keys = $('#guide-keys'); keys.replaceChildren();
  for (const k of tr('keys')) { const li = element('li', '', k); li.dir = 'auto'; keys.append(li); }
  $('#guide-tour').textContent = tr('showTour');
  $('#guide-start').textContent = tr('startAsking');
  const setupOpen = !document.querySelector('.guide-panel[data-panel="setup"]').hidden;
  if (setupOpen && typeof loadSetup === 'function') loadSetup();
}
$('#guide-tour').onclick = () => { $('#guide-dialog').close(); startTour(); };

// ---------------------------------------------------------------- arrow tour
// The page keeps changing after load (starter topics, library refresh, sticky composer), so the
// spotlight is re-measured every 300 ms and on scroll instead of being placed once (measured
// 2026-11-17: a one-time placement drifted ~100 px off the question box in a screenshot).
let tourActive = false, tourIndex = 0, tourLayer = null, tourTarget = null, tourTimer = null;
function startTour() {
  clearInterval(tourTimer);
  tourTimer = setInterval(() => { if (tourTarget) placeTour(tourTarget); }, 300);
  document.querySelectorAll('dialog[open]').forEach(d => d.close());
  view('chat');
  tourActive = true; tourIndex = 0;
  tourLayer = element('div', 'tour-layer');
  tourLayer.setAttribute('role', 'dialog'); tourLayer.setAttribute('aria-modal', 'true'); tourLayer.setAttribute('aria-live', 'polite');
  const spot = element('div', 'tour-spot'), tip = element('div', 'tour-tip');
  tip.append(element('p', 'tour-count'), element('h3', 'tour-title'), element('p', 'tour-text'));
  const actions = element('div', 'tour-actions');
  const skip = element('button', 'tour-skip'), back = element('button', 'tour-back'), next = element('button', 'tour-next');
  [skip, back, next].forEach(b => b.type = 'button');
  skip.onclick = endTour; back.onclick = () => moveTour(-1); next.onclick = () => moveTour(1);
  actions.append(skip, element('span', 'tour-gap'), back, next);
  tip.append(actions);
  tourLayer.append(spot, tip);
  tourLayer.addEventListener('click', e => { if (e.target === tourLayer) moveTour(1); });
  document.body.append(tourLayer);
  showStep();
  next.focus();
}
function moveTour(delta) {
  const total = tr('tour').length;
  const nextIndex = tourIndex + delta;
  if (nextIndex >= total) { endTour(); return; }
  tourIndex = Math.max(0, nextIndex);
  showStep();
}
function endTour() {
  if (!tourActive) return;
  tourActive = false;
  clearInterval(tourTimer); tourTimer = null; tourTarget = null;
  if (tourLayer) tourLayer.remove();
  tourLayer = null;
  $('#sidebar').classList.remove('open');
  try { localStorage.setItem('mufti-toured', 'true'); } catch {}
  $('#question').focus();
}
function isMobile() { return matchMedia('(max-width: 760px)').matches; }
function showStep() {
  if (!tourActive || !tourLayer) return;
  const steps = tr('tour'), step = steps[tourIndex];
  $('#sidebar').classList.toggle('open', !!(step.sidebar && isMobile()));
  const tip = tourLayer.querySelector('.tour-tip');
  tip.dir = tr('dir');
  tip.querySelector('.tour-count').textContent = tr('stepOf').replace('{n}', tourIndex + 1).replace('{total}', steps.length);
  tip.querySelector('.tour-title').textContent = step.title;
  tip.querySelector('.tour-text').textContent = step.text;
  tip.querySelector('.tour-skip').textContent = tr('skipTour');
  const back = tip.querySelector('.tour-back');
  back.textContent = tr('back'); back.hidden = tourIndex === 0;
  tip.querySelector('.tour-next').textContent = tourIndex === steps.length - 1 ? tr('done') : tr('next');
  const target = document.querySelector(step.sel);
  if (!target) { moveTour(1); return; }
  tourTarget = target;
  // Scroll only when the target is off-screen: scrollIntoView on the sticky composer scrolled the
  // page ~100 px for no reason and left the spotlight above the question box.
  const box = target.getBoundingClientRect();
  if (box.top < 0 || box.bottom > innerHeight) target.scrollIntoView({block: 'center', inline: 'nearest'});
  placeTour(target);
  // The mobile sidebar slides in over 200 ms; measure again after it has arrived.
  setTimeout(() => placeTour(target), step.sidebar && isMobile() ? 260 : 40);
}
function placeTour(target) {
  if (!tourActive || !tourLayer || target !== tourTarget) return;
  const spot = tourLayer.querySelector('.tour-spot'), tip = tourLayer.querySelector('.tour-tip');
  const r = target.getBoundingClientRect(), pad = 8, gap = 18, margin = 12;
  spot.style.left = (r.left - pad) + 'px'; spot.style.top = (r.top - pad) + 'px';
  spot.style.width = (r.width + 2 * pad) + 'px'; spot.style.height = (r.height + 2 * pad) + 'px';
  const W = innerWidth, H = innerHeight;
  tip.style.maxWidth = Math.min(360, W - 2 * margin) + 'px';
  const tw = tip.offsetWidth, th = tip.offsetHeight;
  let side;
  // A target in the left sidebar (desktop) gets the bubble to its right, arrow pointing left.
  if (r.right + gap + tw + margin < W && r.left < W * 0.3 && r.width < W * 0.3) side = 'right';
  else if (r.bottom + gap + th + margin < H) side = 'below';
  else side = 'above';
  let left, top;
  if (side === 'right') {
    left = r.right + pad + gap;
    top = Math.min(Math.max(margin, r.top + r.height / 2 - th / 2), H - th - margin);
    tip.style.setProperty('--arrow-y', Math.min(Math.max(18, r.top + r.height / 2 - top), th - 18) + 'px');
  } else {
    left = Math.min(Math.max(margin, r.left + r.width / 2 - tw / 2), W - tw - margin);
    top = side === 'below' ? r.bottom + pad + gap : Math.max(margin, r.top - pad - gap - th);
    tip.style.setProperty('--arrow-x', Math.min(Math.max(18, r.left + r.width / 2 - left), tw - 18) + 'px');
  }
  tip.dataset.side = side;
  tip.style.left = left + 'px'; tip.style.top = top + 'px';
}
addEventListener('resize', () => { if (tourActive) showStep(); });
addEventListener('scroll', () => { if (tourTarget) placeTour(tourTarget); }, true);
document.addEventListener('keydown', e => {
  if (!tourActive) return;
  const rtl = tr('dir') === 'rtl';
  if (e.key === 'Escape') { e.preventDefault(); endTour(); }
  else if (e.key === 'Enter' || e.key === (rtl ? 'ArrowLeft' : 'ArrowRight')) { e.preventDefault(); moveTour(1); }
  else if (e.key === (rtl ? 'ArrowRight' : 'ArrowLeft')) { e.preventDefault(); moveTour(-1); }
}, true);

// ---------------------------------------------------------------- first visit
// ?lang=English|Hinglish|Urdu|Hindi sets the directions language; ?tour=N starts the tour at step N.
if (T[urlParams.get('lang')]) { try { localStorage.setItem('mufti-ui-lang', urlParams.get('lang')); } catch {} }
$('#dir-lang-name').textContent = (DIR_LANGS.find(l => l[0] === dirLang()) || DIR_LANGS[0])[1];
(() => {
  const guideParam = urlParams.get('guide');
  let welcomed = false;
  try { welcomed = localStorage.getItem('mufti-welcomed') === 'true'; } catch {}
  const tourStep = parseInt(urlParams.get('tour') || '', 10);
  if (tourStep >= 1) setTimeout(() => { startTour(); tourIndex = Math.min(tourStep, tr('tour').length) - 1; showStep(); }, 500);
  else if (guideParam === '1') setTimeout(() => openGuide(), 500);
  else if (guideParam !== '0' && !welcomed) setTimeout(showWelcome, 500);
})();
