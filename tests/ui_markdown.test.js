// Headless test of the answer Markdown renderer in frontend/app.js. Run: node tests/ui_markdown.test.js
const fs = require('fs');
const src = fs.readFileSync(require('path').join(__dirname, '..', 'frontend', 'app.js'), 'utf8');
const start = src.indexOf('function inlineMarkdown'), end = src.indexOf('function plainAnswer');
class Node {
  constructor(tag) { this.tagName = tag.toUpperCase(); this.children = []; this.className = ''; this.attrs = {};
    this.classList = { add: c => this.className += ' ' + c, remove: () => {} }; }
  get lastChild() { return this.children[this.children.length - 1]; }
  append(...n) { this.children.push(...n); } replaceChildren() { this.children = []; }
  setAttribute(k, v) { this.attrs[k] = v; } set textContent(t) { this.children = [{ text: String(t) }]; }
}
global.document = { createElement: t => new Node(t), createTextNode: t => ({ text: t }) };
global.element = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };
global.source = () => {}; global.niceTitle = t => t;
eval(src.slice(start, end) + ';global.renderMarkdown=renderMarkdown;');
const show = (n, d = 0) => n.text !== undefined ? ' '.repeat(d) + JSON.stringify(n.text)
  : ' '.repeat(d) + n.tagName + (n.className ? '.' + n.className.trim() : '') + (n.start ? ' start=' + n.start : '') + '\n' + n.children.map(c => show(c, d + 2)).join('\n');
const cites = [{ id: 1, book_title: 'B', page: 50 }, { id: 2, book_title: 'B', page: 257 }];
const box = new Node('div');
renderMarkdown(box, '<<full>>\nIntro [1].\n\n1.  **One:**\n    first text [1]\n2.  **Two:**\n    second text [2]\n\nAfter <img src=x onerror=alert(1)> done.', cites);
console.log(show(box));
const ol = box.children.find(c => c.tagName === 'OL');
if (!ol || ol.children.length !== 2) throw new Error('numbered list was split');
if (box.children.filter(c => c.tagName === 'OL').length !== 1) throw new Error('more than one list');
if (!JSON.stringify(box).includes('<img src=x onerror=alert(1)>')) throw new Error('html not kept as text');
if (JSON.stringify(box).includes('<<full>>')) throw new Error('marker leaked');
// 2026-11-17: the follow-up marker (complete, or half-streamed in a live draft) never shows.
for (const md of ['Answer [1].\n<<next: What next? | And then?>>', 'Answer [1].\n<<next: What ne', 'Answer [1].\n<<ne']) {
  const b = new Node('div'); renderMarkdown(b, md, cites);
  const dump = JSON.stringify(b);
  if (dump.includes('<<') || dump.includes('What next')) throw new Error('follow-up marker leaked: ' + md);
}
console.log('OK');
